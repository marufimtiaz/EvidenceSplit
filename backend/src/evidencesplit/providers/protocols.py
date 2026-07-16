from typing import TYPE_CHECKING, Protocol, Sequence

if TYPE_CHECKING:
    from evidencesplit.evidence.schemas import EvidenceFindingOutput
    from evidencesplit.retrieval.schemas import RetrievedPassage


class EmbeddingService(Protocol):
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class EvidenceAnalysisService(Protocol):
    async def analyze_passages(
        self,
        *,
        claim: str,
        passages: Sequence["RetrievedPassage"],
    ) -> list["EvidenceFindingOutput"]: ...
