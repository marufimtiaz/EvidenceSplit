import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from evidencesplit.evidence.models import EvidenceFinding, PaperAssessment


class AssessmentRepository:
    @staticmethod
    async def get_findings(
        db: AsyncSession,
        analysis_id: uuid.UUID,
    ) -> list[EvidenceFinding]:
        result = await db.execute(
            select(EvidenceFinding)
            .where(EvidenceFinding.analysis_id == analysis_id)
            .order_by(EvidenceFinding.document_id, EvidenceFinding.id)
        )
        return list(result.scalars())

    @staticmethod
    async def replace_assessments(
        db: AsyncSession,
        analysis_id: uuid.UUID,
        assessments: list[PaperAssessment],
    ) -> list[PaperAssessment]:
        await db.execute(delete(PaperAssessment).where(PaperAssessment.analysis_id == analysis_id))
        db.add_all(assessments)
        await db.commit()
        return assessments
