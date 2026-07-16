from pydantic import BaseModel


class CandidatePaper(BaseModel):
    openalex_id: str
    title: str
    authors: list[str]
    year: int | None
    doi: str | None
    abstract: str | None
    source_url: str | None
    relevance_score: float
