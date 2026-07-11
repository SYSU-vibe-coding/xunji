from pathlib import Path


def test_match_dedup_rewrites_references_before_delete() -> None:
    migration = (
        Path(__file__).parents[2] / "alembic" / "versions" / "20260711_0004_core_state_machine.py"
    ).read_text(encoding="utf-8")

    create_map = migration.index("CREATE TEMPORARY TABLE match_result_dedup_map")
    populate_map = migration.index("INSERT INTO match_result_dedup_map")
    update_claims = migration.index("UPDATE claim_requests AS claims")
    update_notices = migration.index("UPDATE notifications AS notices")
    delete_duplicates = migration.index("DELETE matches_to_remove")
    unique_constraint = migration.index('"uk_match_lost_found"')

    assert create_map < populate_map < update_claims < update_notices
    assert update_notices < delete_duplicates < unique_constraint
    assert "FIRST_VALUE(id) OVER" in migration
    assert "WHERE notices.related_type = 'MATCH'" in migration
    assert "SET claims.match_id = dedup.keeper_id" in migration
