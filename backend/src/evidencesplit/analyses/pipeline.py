import asyncio
import logging
import uuid
import os

from sqlalchemy.ext.asyncio import AsyncSession
from evidencesplit.database import async_session
from evidencesplit.analyses.repository import AnalysisRepository
from evidencesplit.shared.types import AnalysisStatus
from evidencesplit.documents.service import DocumentService
from evidencesplit.discovery.service import DiscoveryService
from evidencesplit.evidence.analyzer import analyze_and_store_evidence
from evidencesplit.evidence.aggregator import aggregate_and_store_assessments
from evidencesplit.evidence.models import EvidenceFinding
from evidencesplit.providers.factory import (
    get_embedding_service,
    get_evidence_analysis_service,
    get_synthesis_service,
)
from evidencesplit.retrieval.embeddings import index_analysis_chunks
from evidencesplit.retrieval.hybrid import hybrid_retrieve
from evidencesplit.retrieval.schemas import RetrievedPassage
from evidencesplit.synthesis.service import synthesize_and_store_report
from evidencesplit.shared.http_errors import ProviderHTTPError

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
    logger.info(
        "pipeline_start analysis_id=%s uploaded_files=%s staging_warnings=%s",
        analysis_id,
        len(uploaded_files),
        len(warnings),
    )
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
        async with async_session() as session:
            await AnalysisRepository.update(session, analysis_id, status=AnalysisStatus.SEARCHING, progress=25)
        await asyncio.sleep(0.2)
        async with async_session() as session:
            await AnalysisRepository.update(session, analysis_id, status=AnalysisStatus.FETCHING_FULL_TEXT, progress=40)
            discovery_warnings = await DiscoveryService().discover_and_store(
                session,
                analysis_id,
                await _get_claim(session, analysis_id),
            )
            warnings.extend(discovery_warnings)
            if warnings:
                await AnalysisRepository.update(
                    session,
                    analysis_id,
                    status=AnalysisStatus.FETCHING_FULL_TEXT,
                    progress=40,
                    warning_message="; ".join(warnings),
                )

        embedding_service = get_embedding_service()
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

        async with async_session() as session:
            await AnalysisRepository.update(
                session,
                analysis_id,
                status=AnalysisStatus.ANALYZING_EVIDENCE,
                progress=82,
            )
            evidence_findings = await _analyze_with_retry(
                session,
                analysis_id,
                await _get_claim(session, analysis_id),
                passages,
            )
        logger.info(
            "Stored %s evidence findings for analysis %s",
            len(evidence_findings),
            analysis_id,
        )

        async with async_session() as session:
            paper_assessments = await aggregate_and_store_assessments(session, analysis_id)
        logger.info(
            "Stored %s paper assessments for analysis %s",
            len(paper_assessments),
            analysis_id,
        )

        async with async_session() as session:
            await AnalysisRepository.update(
                session,
                analysis_id,
                status=AnalysisStatus.SYNTHESIZING,
                progress=96,
            )
            try:
                report = await synthesize_and_store_report(
                    session,
                    analysis_id,
                    await _get_claim(session, analysis_id),
                    get_synthesis_service(),
                )
                logger.info(
                    "Stored %s comparison report for analysis %s",
                    report.overall_assessment,
                    analysis_id,
                )
            except Exception:
                logger.exception("Synthesis failed for analysis %s", analysis_id)
                warnings.append("The evidence was grouped, but the synthesized overview was unavailable.")
                await AnalysisRepository.update(
                    session,
                    analysis_id,
                    status=AnalysisStatus.SYNTHESIZING,
                    progress=96,
                    warning_message="; ".join(warnings),
                )

        async with async_session() as session:
            terminal_status = completion_status(warnings)
            await AnalysisRepository.update(
                session,
                analysis_id,
                status=terminal_status,
                progress=100,
                completed=True,
            )
        logger.info(
            "pipeline_complete analysis_id=%s status=%s warnings=%s",
            analysis_id,
            terminal_status.value,
            len(warnings),
        )
    except Exception as exc:
        logger.exception("Failed to analyze evidence for analysis %s", analysis_id)
        error_message = "Pipeline failed."
        if isinstance(exc, ProviderHTTPError):
            logger.error(
                "pipeline_external_failure analysis_id=%s provider=%s operation=%s status=%s detail=%s",
                analysis_id,
                exc.provider,
                exc.operation,
                exc.status_code,
                exc.detail,
            )
            if exc.status_code == 429:
                error_message = f"{exc.provider.title()} rate limit reached. Wait a minute and try again."
        async with async_session() as session:
            try:
                await AnalysisRepository.update(
                    session,
                    analysis_id,
                    status=AnalysisStatus.FAILED,
                    progress=100,
                    error_message=error_message,
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


async def _analyze_with_retry(
    session: AsyncSession,
    analysis_id: uuid.UUID,
    claim: str,
    passages: list[RetrievedPassage],
) -> list[EvidenceFinding]:
    service = get_evidence_analysis_service()
    for attempt in range(2):
        try:
            return await analyze_and_store_evidence(
                session,
                analysis_id,
                claim,
                passages,
                service,
            )
        except Exception:
            if attempt == 1:
                raise
            logger.warning("Retrying evidence analysis for %s", analysis_id)
    return []
