import uuid
from sqlalchemy import String, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from evidencesplit.database import Base
from evidencesplit.shared.types import SourceType


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[SourceType] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    authors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doi: Mapped[str | None] = mapped_column(String, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_status: Mapped[str] = mapped_column(String, nullable=False)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(String, nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(String, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
