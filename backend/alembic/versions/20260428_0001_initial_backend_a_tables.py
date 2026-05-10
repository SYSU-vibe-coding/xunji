"""initial backend A tables

Revision ID: 20260428_0001
Revises:
Create Date: 2026-04-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260428_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("nickname", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("avatar_url", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="USER"),
        sa.Column("cert_status", sa.String(length=20), nullable=False, server_default="UNVERIFIED"),
        sa.Column("campus_id", sa.String(length=64), nullable=True),
        sa.Column("real_name", sa.String(length=64), nullable=True),
        sa.Column("credit_score", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone", name="uk_users_phone"),
    )
    op.create_index("idx_users_role", "users", ["role"])
    op.create_index("idx_users_cert_status", "users", ["cert_status"])

    op.create_table(
        "user_cert_requests",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("campus_id", sa.String(length=64), nullable=False),
        sa.Column("document_image_url", sa.String(length=255), nullable=False),
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("review_comment", sa.String(length=255), nullable=True),
        sa.Column("reviewer_id", sa.String(length=26), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cert_user_id", "user_cert_requests", ["user_id"])
    op.create_index("idx_cert_status", "user_cert_requests", ["review_status"])

    op.create_table(
        "lost_items",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("item_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("lost_time_start", sa.DateTime(), nullable=False),
        sa.Column("lost_time_end", sa.DateTime(), nullable=False),
        sa.Column("lost_location", sa.String(length=255), nullable=False),
        sa.Column("subscribe_match", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="SEARCHING"),
        sa.Column("ai_tags", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_lost_items_user_id", "lost_items", ["user_id"])
    op.create_index("idx_lost_items_category_status", "lost_items", ["category", "status"])
    op.create_index("idx_lost_items_location", "lost_items", ["lost_location"])

    op.create_table(
        "found_items",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("item_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("found_time", sa.DateTime(), nullable=False),
        sa.Column("found_location", sa.String(length=255), nullable=False),
        sa.Column("is_sensitive", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("custody_type", sa.String(length=30), nullable=False),
        sa.Column("contact_preference", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("ai_tags", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_found_items_user_id", "found_items", ["user_id"])
    op.create_index("idx_found_items_category_status", "found_items", ["category", "status"])
    op.create_index("idx_found_items_location", "found_items", ["found_location"])

    op.create_table(
        "item_images",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("biz_type", sa.String(length=20), nullable=False),
        sa.Column("biz_id", sa.String(length=26), nullable=False),
        sa.Column("image_url", sa.String(length=255), nullable=False),
        sa.Column("masked_image_url", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_item_images_biz", "item_images", ["biz_type", "biz_id"])

    op.create_table(
        "verify_questions",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("found_item_id", sa.String(length=26), nullable=False),
        sa.Column("question_text", sa.String(length=255), nullable=False),
        sa.Column("answer_keywords", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_verify_found_item", "verify_questions", ["found_item_id"])

    op.create_table(
        "operation_logs",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("operator_id", sa.String(length=26), nullable=False),
        sa.Column("operator_role", sa.String(length=20), nullable=False),
        sa.Column("biz_type", sa.String(length=30), nullable=False),
        sa.Column("biz_id", sa.String(length=26), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_oplog_operator", "operation_logs", ["operator_id"])
    op.create_index("idx_oplog_biz", "operation_logs", ["biz_type", "biz_id"])


def downgrade() -> None:
    op.drop_index("idx_oplog_biz", table_name="operation_logs")
    op.drop_index("idx_oplog_operator", table_name="operation_logs")
    op.drop_table("operation_logs")

    op.drop_index("idx_verify_found_item", table_name="verify_questions")
    op.drop_table("verify_questions")

    op.drop_index("idx_item_images_biz", table_name="item_images")
    op.drop_table("item_images")

    op.drop_index("idx_found_items_location", table_name="found_items")
    op.drop_index("idx_found_items_category_status", table_name="found_items")
    op.drop_index("idx_found_items_user_id", table_name="found_items")
    op.drop_table("found_items")

    op.drop_index("idx_lost_items_location", table_name="lost_items")
    op.drop_index("idx_lost_items_category_status", table_name="lost_items")
    op.drop_index("idx_lost_items_user_id", table_name="lost_items")
    op.drop_table("lost_items")

    op.drop_index("idx_cert_status", table_name="user_cert_requests")
    op.drop_index("idx_cert_user_id", table_name="user_cert_requests")
    op.drop_table("user_cert_requests")

    op.drop_index("idx_users_cert_status", table_name="users")
    op.drop_index("idx_users_role", table_name="users")
    op.drop_table("users")
