import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from evidencesplit.config import settings
from evidencesplit.documents.models import Chunk, Document
from evidencesplit.providers.protocols import EmbeddingService
from evidencesplit.retrieval.schemas import RetrievedPassage


@dataclass
class _Candidate:
    chunk: Chunk
    document: Document
    semantic: float | None = None
    keyword: float | None = None


def _normalize(values: dict[uuid.UUID, float]) -> dict[uuid.UUID, float]:
    if not values:
        return {}
    low, high = min(values.values()), max(values.values())
    if high == low:
        return {key: 1.0 for key in values}
    return {key: (value - low) / (high - low) for key, value in values.items()}


async def hybrid_retrieve(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    claim: str,
    embedding_service: EmbeddingService,
) -> list[RetrievedPassage]:
    indexed = await db.scalar(
        select(func.count(Chunk.id))
        .join(Document, Document.id == Chunk.document_id)
        .where(Document.analysis_id == analysis_id, Chunk.embedding.is_not(None))
    )
    if not indexed:
        return []

    query_vector = await embedding_service.embed_query(claim)
    pool_size = settings.MAX_TOTAL_PASSAGES * 5
    distance = Chunk.embedding.cosine_distance(query_vector)
    semantic_rows = (
        await db.execute(
            select(Chunk, Document, (1 - distance).label("score"))
            .join(Document, Document.id == Chunk.document_id)
            .where(Document.analysis_id == analysis_id, Chunk.embedding.is_not(None))
            .order_by(distance)
            .limit(pool_size)
        )
    ).all()

    query = func.websearch_to_tsquery(claim)
    keyword_rank = func.ts_rank_cd(Chunk.search_vector, query)
    keyword_rows = (
        await db.execute(
            select(Chunk, Document, keyword_rank.label("score"))
            .join(Document, Document.id == Chunk.document_id)
            .where(
                Document.analysis_id == analysis_id,
                Chunk.search_vector.is_not(None),
                keyword_rank > 0,
            )
            .order_by(keyword_rank.desc())
            .limit(pool_size)
        )
    ).all()

    candidates: dict[uuid.UUID, _Candidate] = {}
    for chunk, document, score in semantic_rows:
        candidates[chunk.id] = _Candidate(chunk, document, semantic=float(score))
    for chunk, document, score in keyword_rows:
        candidate = candidates.setdefault(chunk.id, _Candidate(chunk, document))
        candidate.keyword = float(score)

    semantic = _normalize({key: item.semantic for key, item in candidates.items() if item.semantic is not None})
    keyword = _normalize({key: item.keyword for key, item in candidates.items() if item.keyword is not None})
    ranked = sorted(
        candidates.items(),
        key=lambda item: 0.65 * semantic.get(item[0], 0.0) + 0.35 * keyword.get(item[0], 0.0),
        reverse=True,
    )

    passages: list[RetrievedPassage] = []
    per_document: dict[uuid.UUID, int] = {}
    for chunk_id, candidate in ranked:
        document_id = candidate.document.id
        if per_document.get(document_id, 0) >= settings.MAX_PASSAGES_PER_DOCUMENT:
            continue
        passages.append(
            RetrievedPassage(
                chunk_id=chunk_id,
                document_id=document_id,
                title=candidate.document.title,
                source_type=candidate.document.source_type,
                content=candidate.chunk.content,
                page_start=candidate.chunk.page_start,
                page_end=candidate.chunk.page_end,
                section=candidate.chunk.section,
                semantic_score=semantic.get(chunk_id, 0.0),
                keyword_score=keyword.get(chunk_id, 0.0),
                combined_score=0.65 * semantic.get(chunk_id, 0.0) + 0.35 * keyword.get(chunk_id, 0.0),
            )
        )
        per_document[document_id] = per_document.get(document_id, 0) + 1
        if len(passages) >= settings.MAX_TOTAL_PASSAGES:
            break

    return passages
