import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from evidencesplit.evidence.models import EvidenceFinding
from evidencesplit.evidence.schemas import EvidenceFindingOutput
from evidencesplit.retrieval.schemas import RetrievedPassage


class EvidenceRepository:
    @staticmethod
    async def replace_findings(
        db: AsyncSession,
        analysis_id: uuid.UUID,
        findings: list[tuple[RetrievedPassage, EvidenceFindingOutput]],
    ) -> list[EvidenceFinding]:
        await db.execute(delete(EvidenceFinding).where(EvidenceFinding.analysis_id == analysis_id))
        records = [
            EvidenceFinding(
                analysis_id=analysis_id,
                document_id=passage.document_id,
                chunk_id=passage.chunk_id,
                stance=finding.stance,
                evidence_quote=finding.evidence_quote,
                explanation=finding.explanation,
                conditions=finding.conditions,
                confidence=finding.confidence,
            )
            for passage, finding in findings
            if finding.evidence_quote is not None and finding.explanation is not None
        ]
        db.add_all(records)
        await db.commit()
        return records
