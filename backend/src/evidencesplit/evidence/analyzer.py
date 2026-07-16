import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from evidencesplit.evidence.models import EvidenceFinding
from evidencesplit.evidence.repository import EvidenceRepository
from evidencesplit.evidence.schemas import EvidenceFindingOutput
from evidencesplit.providers.protocols import EvidenceAnalysisService
from evidencesplit.retrieval.schemas import RetrievedPassage
from evidencesplit.shared.types import Stance


async def analyze_and_store_evidence(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    claim: str,
    passages: list[RetrievedPassage],
    analysis_service: EvidenceAnalysisService,
) -> list[EvidenceFinding]:
    outputs = await analysis_service.analyze_passages(claim=claim, passages=passages)
    passage_by_id = {passage.chunk_id: passage for passage in passages}
    valid: dict[uuid.UUID, tuple[RetrievedPassage, EvidenceFindingOutput]] = {}

    for output in outputs:
        passage = passage_by_id.get(output.chunk_id)
        if passage is None or not output.relevant or output.stance == Stance.IRRELEVANT:
            continue
        if not output.evidence_quote or output.evidence_quote not in passage.content:
            continue
        valid[passage.chunk_id] = (passage, output)

    return await EvidenceRepository.replace_findings(
        db,
        analysis_id,
        list(valid.values()),
    )
