from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from evidencesplit.analyses.repository import AnalysisRepository
from evidencesplit.analyses.pipeline import run_analysis_pipeline
from evidencesplit.analyses.models import Analysis


class AnalysisService:
    @staticmethod
    async def trigger_analysis(
        db: AsyncSession,
        claim: str,
        uploaded_files: list[tuple[str, str]],
        background_tasks: BackgroundTasks,
    ) -> Analysis:
        analysis = await AnalysisRepository.create(db, claim)
        background_tasks.add_task(run_analysis_pipeline, analysis.id, uploaded_files)
        return analysis
