import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from evidencesplit.documents.models import Document, Chunk
from evidencesplit.shared.types import SourceType


class DocumentRepository:
    @staticmethod
    async def create_document(
        db: AsyncSession,
        analysis_id: uuid.UUID,
        source_type: SourceType,
        title: str,
        authors: list[str],
        year: int | None,
        doi: str | None,
        source_url: str | None,
        page_count: int | None,
        processing_status: str,
    ) -> Document:
        doc = Document(
            analysis_id=analysis_id,
            source_type=source_type,
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            source_url=source_url,
            page_count=page_count,
            processing_status=processing_status,
        )
        db.add(doc)
        await db.flush()
        return doc

    @staticmethod
    async def get_document(db: AsyncSession, document_id: uuid.UUID) -> Document | None:
        result = await db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_document_status(db: AsyncSession, document_id: uuid.UUID, status: str) -> Document | None:
        doc = await DocumentRepository.get_document(db, document_id)
        if not doc:
            return None
        doc.processing_status = status
        await db.commit()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def get_documents_by_analysis(db: AsyncSession, analysis_id: uuid.UUID) -> list[Document]:
        result = await db.execute(select(Document).where(Document.analysis_id == analysis_id))
        return list(result.scalars().all())


class ChunkRepository:
    @staticmethod
    async def create_chunk(
        db: AsyncSession,
        document_id: uuid.UUID,
        content: str,
        page_start: int,
        page_end: int,
        section: str | None,
        chunk_index: int,
        embedding: list[float] | None = None,
        search_vector: str | None = None,
    ) -> Chunk:
        chunk = Chunk(
            document_id=document_id,
            content=content,
            page_start=page_start,
            page_end=page_end,
            section=section,
            chunk_index=chunk_index,
            embedding=embedding,
            search_vector=search_vector,
        )
        db.add(chunk)
        await db.flush()
        return chunk
