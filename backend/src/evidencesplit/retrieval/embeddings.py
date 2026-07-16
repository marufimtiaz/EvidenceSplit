import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from evidencesplit.documents.models import Chunk, Document
from evidencesplit.providers.protocols import EmbeddingService


async def index_analysis_chunks(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    embedding_service: EmbeddingService,
) -> int:
    result = await db.execute(
        select(Chunk)
        .join(Document, Document.id == Chunk.document_id)
        .where(Document.analysis_id == analysis_id)
        .order_by(Chunk.document_id, Chunk.chunk_index)
    )
    chunks = list(result.scalars())

    for start in range(0, len(chunks), 20):
        batch = chunks[start : start + 20]
        vectors = await embedding_service.embed_documents([chunk.content for chunk in batch])
        for chunk, vector in zip(batch, vectors, strict=True):
            await db.execute(
                update(Chunk)
                .where(Chunk.id == chunk.id)
                .values(
                    embedding=vector,
                    search_vector=func.to_tsvector(chunk.content),
                )
            )
        await db.commit()

    return len(chunks)
