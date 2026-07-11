"""persist content review comments

Revision ID: 20260711_0005
Revises: 20260711_0004
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260711_0005"
down_revision: str | None = "20260711_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lost_items",
        sa.Column("review_comment", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "found_items",
        sa.Column("review_comment", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("found_items", "review_comment")
    op.drop_column("lost_items", "review_comment")
