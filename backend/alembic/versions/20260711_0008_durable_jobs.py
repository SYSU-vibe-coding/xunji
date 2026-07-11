"""add durable item outbox jobs

Revision ID: 20260711_0008
Revises: 20260711_0007
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260711_0008"
down_revision: str | None = "20260711_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "durable_jobs",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("job_type", sa.String(length=20), nullable=False),
        sa.Column("biz_type", sa.String(length=20), nullable=False),
        sa.Column("biz_id", sa.String(length=26), nullable=False),
        sa.Column("biz_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_after", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "job_type IN ('MATCH', 'CLASSIFY', 'SENSITIVE')",
            name="ck_durable_jobs_job_type",
        ),
        sa.CheckConstraint(
            "biz_type IN ('LOST', 'FOUND')",
            name="ck_durable_jobs_biz_type",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_durable_jobs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_type",
            "biz_type",
            "biz_id",
            "biz_version",
            name="uk_durable_job_type_biz_version",
        ),
    )
    op.create_index(
        "idx_durable_jobs_claim",
        "durable_jobs",
        ["status", "run_after", "created_at"],
    )
    op.create_index(
        "idx_durable_jobs_biz",
        "durable_jobs",
        ["biz_type", "biz_id", "biz_version"],
    )


def downgrade() -> None:
    op.drop_index("idx_durable_jobs_biz", table_name="durable_jobs")
    op.drop_index("idx_durable_jobs_claim", table_name="durable_jobs")
    op.drop_table("durable_jobs")
