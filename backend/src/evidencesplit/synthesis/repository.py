import uuid
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from evidencesplit.documents.models import Document
from evidencesplit.evidence.models import EvidenceFinding, PaperAssessment
from evidencesplit.synthesis.models import ComparisonReportRecord
from evidencesplit.synthesis.schemas import (
    ComparisonReport,
    FindingForSynthesis,
    PaperForSynthesis,
)


class SynthesisRepository:
    @staticmethod
    async def load_papers(
        db: AsyncSession,
        analysis_id: uuid.UUID,
    ) -> list[PaperForSynthesis]:
        assessment_rows = (
            await db.execute(
                select(PaperAssessment, Document)
                .join(Document, Document.id == PaperAssessment.document_id)
                .where(PaperAssessment.analysis_id == analysis_id)
            )
        ).all()
        findings = list(
            (await db.execute(select(EvidenceFinding).where(EvidenceFinding.analysis_id == analysis_id))).scalars()
        )
        by_document: dict[uuid.UUID, list[EvidenceFinding]] = defaultdict(list)
        for finding in findings:
            by_document[finding.document_id].append(finding)

        return [
            PaperForSynthesis(
                document_id=document.id,
                title=document.title,
                source_type=document.source_type,
                stance=assessment.stance,
                summary=assessment.summary,
                findings=[
                    FindingForSynthesis(
                        id=finding.id,
                        stance=finding.stance,
                        evidence_quote=finding.evidence_quote,
                        explanation=finding.explanation,
                        conditions=finding.conditions,
                        confidence=finding.confidence,
                    )
                    for finding in by_document[document.id]
                ],
            )
            for assessment, document in assessment_rows
        ]

    @staticmethod
    async def save_report(
        db: AsyncSession,
        analysis_id: uuid.UUID,
        report: ComparisonReport,
    ) -> ComparisonReportRecord:
        await db.execute(delete(ComparisonReportRecord).where(ComparisonReportRecord.analysis_id == analysis_id))
        record = ComparisonReportRecord(
            analysis_id=analysis_id,
            overall_assessment=report.overall_assessment,
            summary=report.summary,
            limitations=report.limitations,
            report_json=report.model_dump(mode="json"),
        )
        db.add(record)
        await db.commit()
        return record
