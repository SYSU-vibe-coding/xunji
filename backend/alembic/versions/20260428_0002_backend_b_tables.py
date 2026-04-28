"""backend B tables

Revision ID: 20260428_0002
Revises: 20260428_0001
Create Date: 2026-04-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260428_0002"
down_revision: str | None = "20260428_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "match_results",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("lost_item_id", sa.String(length=26), nullable=False),
        sa.Column("found_item_id", sa.String(length=26), nullable=False),
        sa.Column("image_score", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("text_score", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("location_score", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("time_score", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("total_score", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("match_status", sa.String(length=20), nullable=False, server_default="NEW"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_match_lost_item", "match_results", ["lost_item_id"])
    op.create_index("idx_match_found_item", "match_results", ["found_item_id"])
    op.create_index("idx_match_total_score", "match_results", ["total_score"])

    op.create_table(
        "claim_requests",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("match_id", sa.String(length=26), nullable=True),
        sa.Column("found_item_id", sa.String(length=26), nullable=False),
        sa.Column("claimant_id", sa.String(length=26), nullable=False),
        sa.Column("verify_level", sa.String(length=20), nullable=False),
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("reject_reason", sa.String(length=255), nullable=True),
        sa.Column("proof_text", sa.String(length=500), nullable=True),
        sa.Column("appeal_reason", sa.String(length=500), nullable=True),
        sa.Column("claimed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_claim_match", "claim_requests", ["match_id"])
    op.create_index("idx_claim_found_item", "claim_requests", ["found_item_id"])
    op.create_index("idx_claim_claimant", "claim_requests", ["claimant_id"])
    op.create_index("idx_claim_status", "claim_requests", ["review_status"])

    op.create_table(
        "claim_answers",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("claim_id", sa.String(length=26), nullable=False),
        sa.Column("question_id", sa.String(length=26), nullable=False),
        sa.Column("question_text", sa.String(length=255), nullable=False),
        sa.Column("answer_text", sa.String(length=255), nullable=False),
        sa.Column("match_score", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_answer_claim", "claim_answers", ["claim_id"])

    op.create_table(
        "handover_records",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("claim_id", sa.String(length=26), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("handover_location", sa.String(length=255), nullable=False),
        sa.Column("handover_time", sa.DateTime(), nullable=False),
        sa.Column("owner_confirmed", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("finder_confirmed", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_id", name="uk_handover_claim"),
    )
    op.create_index("idx_handover_claim", "handover_records", ["claim_id"])

    op.create_table(
        "credit_logs",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("delta_score", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.String(length=50), nullable=False),
        sa.Column("reason_text", sa.String(length=255), nullable=True),
        sa.Column("biz_type", sa.String(length=30), nullable=False),
        sa.Column("biz_id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "biz_type", "biz_id", "reason_code", name="uk_credit_dedup"),
    )
    op.create_index("idx_credit_user", "credit_logs", ["user_id"])
    op.create_index("idx_credit_reason", "credit_logs", ["reason_code"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("notice_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("content", sa.String(length=500), nullable=True),
        sa.Column("is_read", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("related_type", sa.String(length=30), nullable=True),
        sa.Column("related_id", sa.String(length=26), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="NORMAL"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_notif_user_read", "notifications", ["user_id", "is_read"])
    op.create_index("idx_notif_type", "notifications", ["notice_type"])
    op.create_index("idx_notif_related", "notifications", ["related_type", "related_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("reporter_id", sa.String(length=26), nullable=False),
        sa.Column("reported_user_id", sa.String(length=26), nullable=True),
        sa.Column("target_type", sa.String(length=30), nullable=False),
        sa.Column("target_id", sa.String(length=26), nullable=False),
        sa.Column("reason", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("handle_status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("handle_result", sa.String(length=255), nullable=True),
        sa.Column("handler_id", sa.String(length=26), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_report_reporter", "reports", ["reporter_id"])
    op.create_index("idx_report_reported_user", "reports", ["reported_user_id"])
    op.create_index("idx_report_status", "reports", ["handle_status"])
    op.create_index("idx_report_target", "reports", ["target_type", "target_id"])

    op.create_table(
        "announcements",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("published_by", sa.String(length=26), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_announce_status", "announcements", ["status"])


def downgrade() -> None:
    op.drop_index("idx_announce_status", table_name="announcements")
    op.drop_table("announcements")

    op.drop_index("idx_report_target", table_name="reports")
    op.drop_index("idx_report_status", table_name="reports")
    op.drop_index("idx_report_reported_user", table_name="reports")
    op.drop_index("idx_report_reporter", table_name="reports")
    op.drop_table("reports")

    op.drop_index("idx_notif_related", table_name="notifications")
    op.drop_index("idx_notif_type", table_name="notifications")
    op.drop_index("idx_notif_user_read", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("idx_credit_reason", table_name="credit_logs")
    op.drop_index("idx_credit_user", table_name="credit_logs")
    op.drop_table("credit_logs")

    op.drop_index("idx_handover_claim", table_name="handover_records")
    op.drop_table("handover_records")

    op.drop_index("idx_answer_claim", table_name="claim_answers")
    op.drop_table("claim_answers")

    op.drop_index("idx_claim_status", table_name="claim_requests")
    op.drop_index("idx_claim_claimant", table_name="claim_requests")
    op.drop_index("idx_claim_found_item", table_name="claim_requests")
    op.drop_index("idx_claim_match", table_name="claim_requests")
    op.drop_table("claim_requests")

    op.drop_index("idx_match_total_score", table_name="match_results")
    op.drop_index("idx_match_found_item", table_name="match_results")
    op.drop_index("idx_match_lost_item", table_name="match_results")
    op.drop_table("match_results")
