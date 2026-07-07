"""Rule-based fallback scoring (matching-rules.md §2)."""

from app.match.scoring import rule_based_score


def test_identical_pair_high_total() -> None:
    payload = {
        "name": "黑色雨伞",
        "description": "蓝色贴纸",
        "location": "图书馆",
        "time": "2026-04-30T08:00:00",
        "imageUrls": ["http://x"],
    }
    scores = rule_based_score(payload, payload)
    assert scores["locationScore"] == 100
    assert scores["textScore"] == 100
    assert scores["totalScore"] > 70


def test_no_overlap_low_total() -> None:
    a = {"name": "黑色雨伞", "location": "图书馆", "time": "2026-04-30T08:00:00"}
    b = {"name": "白色钱包", "location": "操场", "time": "2026-05-30T08:00:00"}
    scores = rule_based_score(a, b)
    assert scores["totalScore"] < 30


def test_partial_location_match_returns_60() -> None:
    a = {"name": "x", "location": "图书馆三楼"}
    b = {"name": "x", "location": "图书馆二楼"}
    scores = rule_based_score(a, b)
    assert scores["locationScore"] == 60.0


def test_time_decay_with_day_based_formula() -> None:
    # New formula: max(0, 100 - days_diff * 2). 3 days apart -> 94.
    a = {"name": "x", "time": "2026-04-30T00:00:00"}
    b = {"name": "x", "time": "2026-05-03T00:00:00"}  # 3 days apart
    scores = rule_based_score(a, b)
    assert scores["timeScore"] == 94.0


def test_time_decay_to_zero_beyond_50_days() -> None:
    a = {"name": "x", "time": "2026-04-30T00:00:00"}
    b = {"name": "x", "time": "2026-07-01T00:00:00"}  # ~62 days apart
    scores = rule_based_score(a, b)
    assert scores["timeScore"] == 0.0
