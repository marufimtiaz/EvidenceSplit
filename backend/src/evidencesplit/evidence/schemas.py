import uuid

from pydantic import BaseModel, Field, model_validator

from evidencesplit.shared.types import Stance


class EvidenceFindingOutput(BaseModel):
    chunk_id: uuid.UUID
    relevant: bool
    stance: Stance
    evidence_quote: str | None = None
    explanation: str | None = None
    conditions: str | None = None
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_relevant_finding(self) -> "EvidenceFindingOutput":
        if self.relevant and self.stance != Stance.IRRELEVANT:
            if not self.evidence_quote or not self.explanation:
                raise ValueError("Relevant evidence requires a quote and explanation.")
        return self


class EvidenceBatchOutput(BaseModel):
    findings: list[EvidenceFindingOutput]
