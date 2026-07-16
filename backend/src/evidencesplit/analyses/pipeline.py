import asyncio
import logging
import uuid
from evidencesplit.database import async_session
from evidencesplit.analyses.repository import AnalysisRepository
from evidencesplit.shared.types import AnalysisStatus

logger = logging.getLogger(__name__)


async def run_analysis_pipeline(analysis_id: uuid.UUID) -> None:
    stages = [
        (AnalysisStatus.PROCESSING_UPLOADS, 10),
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
