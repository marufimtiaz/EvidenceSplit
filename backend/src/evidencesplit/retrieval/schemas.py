import uuid

from pydantic import BaseModel

from evidencesplit.shared.types import SourceType


class RetrievedPassage(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    title: str
    source_type: SourceType
    content: str
    page_start: int | None
    page_end: int | None
    section: str | None
    semantic_score: float
    keyword_score: float
    combined_score: float
