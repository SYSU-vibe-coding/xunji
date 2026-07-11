"""enforce one match row per lost/found pair

Revision ID: 20260711_0004
Revises: 20260428_0003
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260711_0004"
down_revision: str | None = "20260428_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Preserve references while collapsing each pair to its highest-priority row.
    op.execute(
        sa.text(
            """
            CREATE TEMPORARY TABLE match_result_dedup_map (
              old_id VARCHAR(26) NOT NULL PRIMARY KEY,
              keeper_id VARCHAR(26) NOT NULL,
              INDEX idx_match_result_dedup_keeper (keeper_id)
            ) ENGINE=InnoDB
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO match_result_dedup_map (old_id, keeper_id)
            SELECT id, keeper_id
            FROM (
              SELECT
                id,
                FIRST_VALUE(id) OVER (
                  PARTITION BY lost_item_id, found_item_id
                  ORDER BY
                    CASE match_status
                      WHEN 'CLAIMED' THEN 4 WHEN 'READ' THEN 3
                      WHEN 'NEW' THEN 2 ELSE 1
                    END DESC,
                    created_at DESC,
                    id DESC
                ) AS keeper_id,
                ROW_NUMBER() OVER (
                  PARTITION BY lost_item_id, found_item_id
                  ORDER BY
                    CASE match_status
                      WHEN 'CLAIMED' THEN 4 WHEN 'READ' THEN 3
                      WHEN 'NEW' THEN 2 ELSE 1
                    END DESC,
                    created_at DESC,
                    id DESC
                ) AS row_num
              FROM match_results
            ) AS ranked
            WHERE row_num > 1
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE claim_requests AS claims
            INNER JOIN match_result_dedup_map AS dedup
              ON claims.match_id = dedup.old_id
            SET claims.match_id = dedup.keeper_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE notifications AS notices
            INNER JOIN match_result_dedup_map AS dedup
              ON notices.related_id = dedup.old_id
            SET notices.related_id = dedup.keeper_id
            WHERE notices.related_type = 'MATCH'
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE matches_to_remove
            FROM match_results AS matches_to_remove
            INNER JOIN match_result_dedup_map AS dedup
              ON matches_to_remove.id = dedup.old_id
            """
        )
    )
    op.execute(sa.text("DROP TEMPORARY TABLE match_result_dedup_map"))
    op.create_unique_constraint(
        "uk_match_lost_found",
        "match_results",
        ["lost_item_id", "found_item_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uk_match_lost_found", "match_results", type_="unique")
