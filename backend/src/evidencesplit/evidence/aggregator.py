import uuid
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from evidencesplit.evidence.assessment_repository import AssessmentRepository
from evidencesplit.evidence.models import EvidenceFinding, PaperAssessment
from evidencesplit.shared.types import Stance


def aggregate_paper_stance(findings: list[EvidenceFinding]) -> Stance:
    stances = {finding.stance for finding in findings}
    has_conditions = any(finding.conditions and finding.conditions.strip() for finding in findings)

    if has_conditions or Stance.QUALIFYING in stances:
        return Stance.QUALIFYING
    if Stance.SUPPORTING in stances and Stance.CONTRADICTING in stances:
        return Stance.QUALIFYING
    if stances == {Stance.SUPPORTING}:
        return Stance.SUPPORTING
    if stances == {Stance.CONTRADICTING}:
        return Stance.CONTRADICTING
    return Stance.QUALIFYING


def summarize_findings(findings: list[EvidenceFinding], stance: Stance) -> str:
    explanations: list[str] = []
    for finding in findings:
        explanation = finding.explanation.strip()
        if explanation and explanation not in explanations:
            explanations.append(explanation)

    label = stance.value.lower().replace("_", " ")
    detail = " ".join(explanations[:3])
    return f"This paper provides {label} evidence relative to the claim. {detail}".strip()


async def aggregate_and_store_assessments(
    db: AsyncSession,
    analysis_id: uuid.UUID,
) -> list[PaperAssessment]:
    findings = await AssessmentRepository.get_findings(db, analysis_id)
    grouped: dict[uuid.UUID, list[EvidenceFinding]] = defaultdict(list)
    for finding in findings:
        grouped[finding.document_id].append(finding)

    assessments = []
    for document_id, paper_findings in grouped.items():
        stance = aggregate_paper_stance(paper_findings)
        assessments.append(
            PaperAssessment(
                analysis_id=analysis_id,
                document_id=document_id,
                stance=stance,
                summary=summarize_findings(paper_findings, stance),
                finding_ids=[str(finding.id) for finding in paper_findings],
            )
        )

    return await AssessmentRepository.replace_assessments(db, analysis_id, assessments)
