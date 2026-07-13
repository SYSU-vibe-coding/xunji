"""snapshot claim verification reference answers

Revision ID: 20260713_0009
Revises: 20260711_0008
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260713_0009"
down_revision: str | None = "20260711_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    claim_columns = {column["name"] for column in sa.inspect(bind).get_columns("claim_requests")}
    answer_columns = {column["name"] for column in sa.inspect(bind).get_columns("claim_answers")}
    if "verification_source" not in claim_columns:
        op.add_column(
            "claim_requests",
            sa.Column(
                "verification_source",
                sa.String(length=32),
                nullable=False,
                server_default="LEGACY_UNKNOWN",
            ),
        )
    if "verification_degraded" not in claim_columns:
        op.add_column(
            "claim_requests",
            sa.Column(
                "verification_degraded",
                sa.SmallInteger(),
                nullable=False,
                server_default="1",
            ),
        )
    if "reference_answers" not in answer_columns:
        op.add_column(
            "claim_answers",
            sa.Column(
                "reference_answers",
                sa.String(length=1000),
                nullable=False,
                server_default="[]",
            ),
        )
    op.execute(
        sa.text(
            """
            UPDATE claim_answers AS ca
            LEFT JOIN verify_questions AS vq
              ON vq.id = ca.question_id
               SET ca.reference_answers = COALESCE(vq.answer_keywords, '[]')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE claim_requests AS cr
               SET cr.verification_source = 'NOT_REQUIRED',
                   cr.verification_degraded = 0
             WHERE NOT EXISTS (
                   SELECT 1
                     FROM claim_answers AS ca
                    WHERE ca.claim_id = cr.id
             )
            """
        )
    )


def downgrade() -> None:
    op.drop_column("claim_answers", "reference_answers")
    op.drop_column("claim_requests", "verification_degraded")
    op.drop_column("claim_requests", "verification_source")
