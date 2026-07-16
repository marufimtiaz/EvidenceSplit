import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from evidencesplit.analyses.models import Analysis
from evidencesplit.analyses.schemas import (
    AnalysisResult,
    EvidenceCardRead,
    EvidenceFindingRead,
)
from evidencesplit.documents.models import Chunk, Document
from evidencesplit.evidence.models import EvidenceFinding, PaperAssessment
from evidencesplit.shared.types import Stance
from evidencesplit.synthesis.models import ComparisonReportRecord
from evidencesplit.synthesis.schemas import ComparisonReport


async def build_analysis_result(db: AsyncSession, analysis: Analysis) -> AnalysisResult:
    report_record = await db.get(ComparisonReportRecord, analysis.id)
    report = ComparisonReport.model_validate(report_record.report_json) if report_record is not None else None
    assessment_rows = (
        await db.execute(
            select(PaperAssessment, Document)
            .join(Document, Document.id == PaperAssessment.document_id)
            .where(PaperAssessment.analysis_id == analysis.id)
            .order_by(Document.title)
        )
    ).all()
    finding_rows = (
        await db.execute(
            select(EvidenceFinding, Chunk)
            .join(Chunk, Chunk.id == EvidenceFinding.chunk_id)
            .where(EvidenceFinding.analysis_id == analysis.id)
            .order_by(EvidenceFinding.document_id, Chunk.chunk_index)
        )
    ).all()
    findings_by_document: dict[uuid.UUID, list[EvidenceFindingRead]] = defaultdict(list)
    for finding, chunk in finding_rows:
        findings_by_document[finding.document_id].append(
            EvidenceFindingRead(
                id=finding.id,
                evidence_quote=finding.evidence_quote,
                explanation=finding.explanation,
                conditions=finding.conditions,
                confidence=finding.confidence,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
            )
        )

    grouped: dict[Stance, list[EvidenceCardRead]] = defaultdict(list)
    for assessment, document in assessment_rows:
        stance = Stance(assessment.stance)
        grouped[stance].append(
            EvidenceCardRead(
                document_id=document.id,
                title=document.title,
                authors=document.authors,
                year=document.year,
                doi=document.doi,
                source_url=document.source_url,
                source_type=document.source_type,
                paper_stance=stance,
                paper_summary=assessment.summary,
                findings=findings_by_document[document.id],
            )
        )

    return AnalysisResult(
        id=analysis.id,
        claim=analysis.claim,
        status=analysis.status,
        progress=analysis.progress,
        warning_message=analysis.warning_message,
        error_message=analysis.error_message,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
        overall_assessment=report.overall_assessment if report else None,
        summary=report.summary if report else None,
        supporting_summary=report.supporting_summary if report else None,
        contradicting_summary=report.contradicting_summary if report else None,
        qualifying_summary=report.qualifying_summary if report else None,
        retrieved_paper_count=len(assessment_rows),
        supporting=grouped[Stance.SUPPORTING],
        contradicting=grouped[Stance.CONTRADICTING],
        qualifying=grouped[Stance.QUALIFYING],
        limitations=report.limitations if report else [],
    )
