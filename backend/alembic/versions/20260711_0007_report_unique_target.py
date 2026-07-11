"""enforce one report per reporter and target

Revision ID: 20260711_0007
Revises: 20260711_0006
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260711_0007"
down_revision: str | None = "20260711_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE duplicate_report
              FROM reports AS duplicate_report
              JOIN reports AS retained_report
                ON duplicate_report.reporter_id = retained_report.reporter_id
               AND duplicate_report.target_type = retained_report.target_type
               AND duplicate_report.target_id = retained_report.target_id
               AND (
                    duplicate_report.created_at > retained_report.created_at
                    OR (
                        duplicate_report.created_at = retained_report.created_at
                        AND duplicate_report.id > retained_report.id
                    )
               )
            """
        )
    )
    op.create_unique_constraint(
        "uk_report_reporter_target",
        "reports",
        ["reporter_id", "target_type", "target_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uk_report_reporter_target", "reports", type_="unique")
