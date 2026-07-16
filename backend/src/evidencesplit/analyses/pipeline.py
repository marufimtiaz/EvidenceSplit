import asyncio
import logging
import uuid
import os
from evidencesplit.database import async_session
from evidencesplit.analyses.repository import AnalysisRepository
from evidencesplit.shared.types import AnalysisStatus
from evidencesplit.documents.service import DocumentService

logger = logging.getLogger(__name__)


def cleanup_temp_files(uploaded_files: list[tuple[str, str]]) -> None:
    for file_path, _ in uploaded_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete temporary file {file_path}: {e}")


async def run_analysis_pipeline(analysis_id: uuid.UUID, uploaded_files: list[tuple[str, str]]) -> None:
    # 1. Processing Uploaded Documents
    async with async_session() as session:
        await AnalysisRepository.update(session, analysis_id, status=AnalysisStatus.PROCESSING_UPLOADS, progress=10)

    async with async_session() as session:
        try:
            warnings = await DocumentService.process_uploads(session, analysis_id, uploaded_files)
            warning_msg = "; ".join(warnings) if warnings else None
            await AnalysisRepository.update(
                session, analysis_id, status=AnalysisStatus.PROCESSING_UPLOADS, progress=20, warning_message=warning_msg
            )
        except Exception as e:
            logger.error(f"Failed to process uploads for analysis {analysis_id}: {e}")
            await AnalysisRepository.update(
                session,
                analysis_id,
                status=AnalysisStatus.FAILED,
                progress=100,
                error_message=f"Upload processing failed: {str(e)}",
                completed=True,
            )
            cleanup_temp_files(uploaded_files)
            return

    # 2. Simulated Stages for remaining steps
    stages = [
        (AnalysisStatus.SEARCHING, 25),
        (AnalysisStatus.FETCHING_FULL_TEXT, 40),
        (AnalysisStatus.INDEXING, 55),
        (AnalysisStatus.RETRIEVING, 70),
        (AnalysisStatus.ANALYZING_EVIDENCE, 82),
        (AnalysisStatus.SYNTHESIZING, 90),
        (AnalysisStatus.COMPLETED, 100),
    ]

    for status, progress in stages:
        await asyncio.sleep(0.5)  # Simulate pipeline steps
        async with async_session() as session:
            try:
                completed = status == AnalysisStatus.COMPLETED
                await AnalysisRepository.update(
                    session,
                    analysis_id,
                    status=status,
                    progress=progress,
                    completed=completed,
                )
                logger.info(f"Analysis {analysis_id} progressed to {status} ({progress}%)")
            except Exception as e:
                logger.error(f"Failed to update analysis {analysis_id} progress: {e}")
                await AnalysisRepository.update(
                    session,
                    analysis_id,
                    status=AnalysisStatus.FAILED,
                    progress=100,
                    error_message=f"Pipeline error: {str(e)}",
                    completed=True,
                )
                break

    cleanup_temp_files(uploaded_files)
