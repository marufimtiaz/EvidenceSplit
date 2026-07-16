import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from evidencesplit.shared.types import AnalysisStatus, SourceType, Stance
from evidencesplit.synthesis.schemas import OverallAssessment


class AnalysisCreate(BaseModel):
    claim: str


class AnalysisRead(BaseModel):
    id: uuid.UUID
    claim: str
    status: AnalysisStatus
    progress: int
    warning_message: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceFindingRead(BaseModel):
    id: uuid.UUID
    evidence_quote: str
    explanation: str
    conditions: str | None
    confidence: float
    page_start: int | None
    page_end: int | None


class EvidenceCardRead(BaseModel):
    document_id: uuid.UUID
    title: str
    authors: list[str]
    year: int | None
    doi: str | None
    source_url: str | None
    source_type: SourceType
    paper_stance: Stance
    paper_summary: str
    findings: list[EvidenceFindingRead]


class AnalysisResult(AnalysisRead):
    overall_assessment: OverallAssessment | None = None
    summary: str | None = None
    supporting_summary: str | None = None
    contradicting_summary: str | None = None
    qualifying_summary: str | None = None
    retrieved_paper_count: int = 0
    supporting: list[EvidenceCardRead] = Field(default_factory=list)
    contradicting: list[EvidenceCardRead] = Field(default_factory=list)
    qualifying: list[EvidenceCardRead] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
