"""create comparison reports table

Revision ID: eb5fb664e8c0
Revises: d8ef625f9c42
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "eb5fb664e8c0"
down_revision: Union[str, Sequence[str], None] = "d8ef625f9c42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "comparison_reports",
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("overall_assessment", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("analysis_id"),
    )


def downgrade() -> None:
    op.drop_table("comparison_reports")
