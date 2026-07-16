"""allow abstract chunks without pages

Revision ID: f31d9c5e8a12
Revises: eb5fb664e8c0
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f31d9c5e8a12"
down_revision: Union[str, Sequence[str], None] = "eb5fb664e8c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("chunks", "page_start", nullable=True)
    op.alter_column("chunks", "page_end", nullable=True)


def downgrade() -> None:
    op.execute("UPDATE chunks SET page_start = 1 WHERE page_start IS NULL")
    op.execute("UPDATE chunks SET page_end = 1 WHERE page_end IS NULL")
    op.alter_column("chunks", "page_start", nullable=False)
    op.alter_column("chunks", "page_end", nullable=False)
