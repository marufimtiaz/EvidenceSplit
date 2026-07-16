"""create paper assessments table

Revision ID: d8ef625f9c42
Revises: c73a6a535f31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8ef625f9c42"
down_revision: Union[str, Sequence[str], None] = "c73a6a535f31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "paper_assessments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("stance", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("finding_ids", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", "document_id"),
    )


def downgrade() -> None:
    op.drop_table("paper_assessments")
