"""Add document indexing status fields

Revision ID: 002
Revises: 001
Create Date: 2026-05-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("indexing_status", sa.String(length=20), nullable=True),
    )
    op.add_column("documents", sa.Column("indexing_error", sa.Text(), nullable=True))
    op.execute(
        "UPDATE documents SET indexing_status = CASE WHEN is_indexed THEN 'indexed' ELSE 'pending' END"
    )


def downgrade() -> None:
    op.drop_column("documents", "indexing_error")
    op.drop_column("documents", "indexing_status")
