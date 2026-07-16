import uuid

from pydantic import BaseModel, ConfigDict

from evidencesplit.shared.types import Stance


class PaperAssessmentRead(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    document_id: uuid.UUID
    stance: Stance
    summary: str
    finding_ids: list[str]

    model_config = ConfigDict(from_attributes=True)
