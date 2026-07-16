from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from evidencesplit.analyses.repository import AnalysisRepository
from evidencesplit.analyses.pipeline import run_analysis_pipeline
from evidencesplit.analyses.demo import run_demo_pipeline
from evidencesplit.analyses.models import Analysis


class AnalysisService:
    @staticmethod
    async def trigger_analysis(
        db: AsyncSession,
        claim: str,
        uploaded_files: list[tuple[str, str, str]],
        staging_warnings: list[str],
        background_tasks: BackgroundTasks,
        *,
        demo_mode: bool = False,
    ) -> Analysis:
        analysis = await AnalysisRepository.create(db, claim)
        if demo_mode:
            background_tasks.add_task(run_demo_pipeline, analysis.id, uploaded_files)
        else:
            background_tasks.add_task(run_analysis_pipeline, analysis.id, uploaded_files, staging_warnings)
        return analysis
