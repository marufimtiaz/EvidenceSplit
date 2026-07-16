import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from evidencesplit.shared.types import AnalysisStatus


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
