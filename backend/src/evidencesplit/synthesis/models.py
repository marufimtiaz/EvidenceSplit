import uuid

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from evidencesplit.database import Base
from evidencesplit.synthesis.schemas import OverallAssessment


class ComparisonReportRecord(Base):
    __tablename__ = "comparison_reports"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    overall_assessment: Mapped[OverallAssessment] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    report_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
