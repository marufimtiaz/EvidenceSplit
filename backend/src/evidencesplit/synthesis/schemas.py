import uuid
from enum import StrEnum

from pydantic import BaseModel, Field

from evidencesplit.shared.types import SourceType, Stance


class OverallAssessment(StrEnum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    MIXED = "MIXED"
    CONDITIONAL = "CONDITIONAL"
    INSUFFICIENT = "INSUFFICIENT"


class FindingForSynthesis(BaseModel):
    id: uuid.UUID
    stance: Stance
    evidence_quote: str
    explanation: str
    conditions: str | None
    confidence: float


class PaperForSynthesis(BaseModel):
    document_id: uuid.UUID
    title: str
    source_type: SourceType
    stance: Stance
    summary: str
    findings: list[FindingForSynthesis]


class CitedStatement(BaseModel):
    text: str
    citation_ids: list[uuid.UUID] = Field(min_length=1)


class GeminiComparisonOutput(BaseModel):
    overall_assessment: OverallAssessment
    summary: list[CitedStatement]
    supporting_summary: list[CitedStatement]
    contradicting_summary: list[CitedStatement]
    qualifying_summary: list[CitedStatement]
    limitations: list[CitedStatement]


class ComparisonReport(BaseModel):
    overall_assessment: OverallAssessment
    summary: str
    supporting_summary: str | None
    contradicting_summary: str | None
    qualifying_summary: str | None
    limitations: list[str]
    citation_ids: list[str]
