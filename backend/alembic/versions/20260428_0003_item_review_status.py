"""add item review status

Revision ID: 20260428_0003
Revises: 20260428_0002
Create Date: 2026-04-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260428_0003"
down_revision: str | None = "20260428_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lost_items",
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="APPROVED"),
    )
    op.add_column(
        "found_items",
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="APPROVED"),
    )
    op.create_index("idx_lost_items_review_status", "lost_items", ["review_status"])
    op.create_index("idx_found_items_review_status", "found_items", ["review_status"])


def downgrade() -> None:
    op.drop_index("idx_found_items_review_status", table_name="found_items")
    op.drop_index("idx_lost_items_review_status", table_name="lost_items")
    op.drop_column("found_items", "review_status")
    op.drop_column("lost_items", "review_status")
