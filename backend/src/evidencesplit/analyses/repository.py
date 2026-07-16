import uuid
from datetime import datetime, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from evidencesplit.analyses.models import Analysis
from evidencesplit.shared.types import AnalysisStatus


class AnalysisRepository:
    @staticmethod
    async def create(db: AsyncSession, claim: str) -> Analysis:
        analysis = Analysis(claim=claim, status=AnalysisStatus.QUEUED, progress=0)
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
        return analysis

    @staticmethod
    async def get(db: AsyncSession, id: uuid.UUID) -> Analysis | None:
        result = await db.execute(select(Analysis).where(Analysis.id == id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update(
        db: AsyncSession,
        id: uuid.UUID,
        status: AnalysisStatus,
        progress: int,
        warning_message: str | None = None,
        error_message: str | None = None,
        completed: bool = False,
    ) -> Analysis | None:
        analysis = await AnalysisRepository.get(db, id)
        if not analysis:
            return None
        analysis.status = status
        analysis.progress = progress
        if warning_message is not None:
            analysis.warning_message = warning_message
        if error_message is not None:
            analysis.error_message = error_message
        if completed:
            analysis.completed_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(analysis)
        return analysis
