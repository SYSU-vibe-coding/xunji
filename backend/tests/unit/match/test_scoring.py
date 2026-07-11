"""Rule-based fallback scoring (matching-rules.md §2)."""

from app.match.scoring import rule_based_score


def test_identical_pair_high_total() -> None:
    payload = {
        "name": "黑色雨伞",
        "description": "蓝色贴纸",
        "location": "图书馆",
        "time": "2026-04-30T08:00:00",
        "timeEnd": "2026-04-30T10:00:00",
        "imageUrls": ["http://x"],
    }
    scores = rule_based_score(payload, payload)
    assert scores["locationScore"] == 100
    assert scores["textScore"] == 100
    assert scores["imageScore"] == 0
    assert scores["imageAvailable"] is False
    assert scores["totalScore"] == 100


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


def test_time_inside_lost_interval_scores_100() -> None:
    a = {
        "name": "x",
        "time": "2026-04-30T08:00:00",
        "timeEnd": "2026-04-30T10:00:00",
    }
    b = {"name": "x", "time": "2026-04-30T09:00:00"}
    scores = rule_based_score(a, b)
    assert scores["timeScore"] == 100.0


def test_time_decay_uses_minimum_interval_distance_in_hours() -> None:
    a = {
        "name": "x",
        "time": "2026-04-30T08:00:00",
        "timeEnd": "2026-04-30T10:00:00",
    }
    b = {"name": "x", "time": "2026-04-30T13:00:00"}
    scores = rule_based_score(a, b)
    assert scores["timeScore"] == 94.0
