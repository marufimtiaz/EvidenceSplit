import asyncio
import logging
import uuid
import os
from sqlalchemy.ext.asyncio import AsyncSession
from evidencesplit.database import async_session
from evidencesplit.analyses.repository import AnalysisRepository
from evidencesplit.shared.types import AnalysisStatus
from evidencesplit.documents.service import DocumentService
from evidencesplit.providers.gemini_embeddings import GeminiEmbeddingService
from evidencesplit.retrieval.embeddings import index_analysis_chunks
from evidencesplit.retrieval.hybrid import hybrid_retrieve

logger = logging.getLogger(__name__)


def completion_status(warnings: list[str]) -> AnalysisStatus:
    return AnalysisStatus.COMPLETED_WITH_WARNINGS if warnings else AnalysisStatus.COMPLETED


def cleanup_temp_files(uploaded_files: list[tuple[str, str, str]]) -> None:
    for file_path, _, _ in uploaded_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete temporary file {file_path}: {e}")


async def run_analysis_pipeline(
    analysis_id: uuid.UUID,
    uploaded_files: list[tuple[str, str, str]],
    staging_warnings: list[str] | None = None,
) -> None:
    warnings = list(staging_warnings or [])
    try:
        async with async_session() as session:
            await AnalysisRepository.update(session, analysis_id, status=AnalysisStatus.PROCESSING_UPLOADS, progress=10)

        async with async_session() as session:
            warnings = await DocumentService.process_uploads(session, analysis_id, uploaded_files)
            warnings = [*(staging_warnings or []), *warnings]
            warning_msg = "; ".join(warnings) if warnings else None
            await AnalysisRepository.update(
                session, analysis_id, status=AnalysisStatus.PROCESSING_UPLOADS, progress=20, warning_message=warning_msg
            )
    except Exception:
        logger.exception("Failed to process uploads for analysis %s", analysis_id)
        async with async_session() as session:
            await AnalysisRepository.update(
                session,
                analysis_id,
                status=AnalysisStatus.FAILED,
                progress=100,
                error_message="Upload processing failed.",
                completed=True,
            )
        cleanup_temp_files(uploaded_files)
        return

    try:
        for status, progress in [
            (AnalysisStatus.SEARCHING, 25),
            (AnalysisStatus.FETCHING_FULL_TEXT, 40),
        ]:
            await asyncio.sleep(0.5)
            async with async_session() as session:
                completed = status in {
                    AnalysisStatus.COMPLETED,
                    AnalysisStatus.COMPLETED_WITH_WARNINGS,
                }
                await AnalysisRepository.update(
                    session,
                    analysis_id,
                    status=status,
                    progress=progress,
                    completed=completed,
                )

        embedding_service = GeminiEmbeddingService()
        async with async_session() as session:
            await AnalysisRepository.update(session, analysis_id, status=AnalysisStatus.INDEXING, progress=55)
            indexed_count = await index_analysis_chunks(session, analysis_id, embedding_service)

        async with async_session() as session:
            await AnalysisRepository.update(session, analysis_id, status=AnalysisStatus.RETRIEVING, progress=70)
            passages = await hybrid_retrieve(
                session,
                analysis_id,
                claim=await _get_claim(session, analysis_id),
                embedding_service=embedding_service,
            )
        logger.info(
            "Indexed %s chunks and retrieved %s passages for analysis %s",
            indexed_count,
            len(passages),
            analysis_id,
        )

        for status, progress in [
            (AnalysisStatus.ANALYZING_EVIDENCE, 82),
            (AnalysisStatus.SYNTHESIZING, 90),
            (completion_status(warnings), 100),
        ]:
            await asyncio.sleep(0.5)
            async with async_session() as session:
                await AnalysisRepository.update(
                    session,
                    analysis_id,
                    status=status,
                    progress=progress,
                    completed=status in {AnalysisStatus.COMPLETED, AnalysisStatus.COMPLETED_WITH_WARNINGS},
                )
    except Exception:
        logger.exception("Failed to index or retrieve evidence for analysis %s", analysis_id)
        async with async_session() as session:
            try:
                await AnalysisRepository.update(
                    session,
                    analysis_id,
                    status=AnalysisStatus.FAILED,
                    progress=100,
                    error_message="Pipeline failed.",
                    completed=True,
                )
            except Exception:
                logger.exception("Failed to persist failure state for analysis %s", analysis_id)

    cleanup_temp_files(uploaded_files)


async def _get_claim(session: AsyncSession, analysis_id: uuid.UUID) -> str:
    analysis = await AnalysisRepository.get(session, analysis_id)
    if analysis is None:
        raise RuntimeError("Analysis not found.")
    return analysis.claim
