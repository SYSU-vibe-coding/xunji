"""persist match score availability and provenance

Revision ID: 20260711_0006
Revises: 20260711_0005
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260711_0006"
down_revision: str | None = "20260711_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "match_results",
        sa.Column("image_available", sa.SmallInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "match_results",
        sa.Column("degraded", sa.SmallInteger(), nullable=False, server_default="1"),
    )
    op.add_column(
        "match_results",
        sa.Column(
            "score_source",
            sa.String(length=32),
            nullable=False,
            server_default="RULE_BASED",
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE match_results
               SET image_score = 0,
                   total_score = LEAST(
                       100,
                       (text_score * 0.3 + location_score * 0.2 + time_score * 0.1) / 0.6
                   ),
                   image_available = 0,
                   degraded = 1,
                   score_source = 'LEGACY_RENORMALIZED'
            """
        )
    )


def downgrade() -> None:
    op.drop_column("match_results", "score_source")
    op.drop_column("match_results", "degraded")
    op.drop_column("match_results", "image_available")
