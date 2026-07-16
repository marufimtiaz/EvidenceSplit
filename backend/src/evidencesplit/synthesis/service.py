import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from evidencesplit.providers.protocols import SynthesisService
from evidencesplit.synthesis.models import ComparisonReportRecord
from evidencesplit.synthesis.repository import SynthesisRepository
from evidencesplit.synthesis.schemas import ComparisonReport, OverallAssessment


async def synthesize_and_store_report(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    claim: str,
    synthesis_service: SynthesisService,
) -> ComparisonReportRecord:
    papers = await SynthesisRepository.load_papers(db, analysis_id)
    if not papers:
        report = ComparisonReport(
            overall_assessment=OverallAssessment.INSUFFICIENT,
            summary="Insufficient relevant evidence was retrieved for this claim.",
            supporting_summary=None,
            contradicting_summary=None,
            qualifying_summary=None,
            limitations=["No relevant paper-level assessments were available."],
            citation_ids=[],
        )
    else:
        report = await synthesis_service.synthesize(claim=claim, papers=papers)
    return await SynthesisRepository.save_report(db, analysis_id, report)
