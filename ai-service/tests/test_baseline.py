"""Regression coverage for the keyword/rule baseline (used as fallback)."""

from app.schemas import (
    CalculateMatchRequest,
    ClassifyItemRequest,
    DetectSensitiveRequest,
    MatchItem,
)
from app.services import _baseline


def test_classify_item_cert() -> None:
    resp = _baseline.classify_item(ClassifyItemRequest(itemName="校园卡"))
    assert resp.category == "CERT"
    assert resp.confidence > 50


def test_classify_item_other_when_unknown() -> None:
    resp = _baseline.classify_item(ClassifyItemRequest(itemName="奇怪的东西"))
    assert resp.category == "OTHER"
    assert resp.confidence == 50.0


def test_detect_sensitive_card() -> None:
    resp = _baseline.detect_sensitive(
        DetectSensitiveRequest(imageUrl="https://example.com/campus-card.jpg")
    )
    assert resp.is_sensitive is True
    assert resp.masked_image_url is None
    assert resp.sensitive_type == "CAMPUS_CARD"
    assert resp.degraded is True
    assert resp.needs_review is True


def test_detect_sensitive_negative() -> None:
    resp = _baseline.detect_sensitive(
        DetectSensitiveRequest(imageUrl="https://example.com/umbrella.jpg")
    )
    assert resp.is_sensitive is True
    assert resp.masked_image_url is None
    assert resp.sensitive_type is None
    assert resp.degraded is True
    assert resp.needs_review is True


def test_calculate_match_score() -> None:
    resp = _baseline.calculate_match(
        CalculateMatchRequest(
            lostItem=MatchItem(name="黑色雨伞", description="蓝色贴纸", location="图书馆"),
            foundItem=MatchItem(name="黑色雨伞", description="蓝色贴纸", location="图书馆"),
        )
    )
    assert resp.total_score > 0
    assert resp.location_score == 100


def test_calculate_match_uses_backend_fallback_scores() -> None:
    resp = _baseline.calculate_match(
        CalculateMatchRequest(
            lostItem=MatchItem(
                name="black umbrella",
                location="library",
                time="2026-04-30T08:00:00",
                timeEnd="2026-04-30T10:00:00",
                imageUrls=["https://example.com/lost.jpg"],
            ),
            foundItem=MatchItem(
                name="black umbrella",
                location="library",
                time="2026-04-30T09:00:00",
                imageUrls=["https://example.com/found.jpg"],
            ),
        )
    )
    assert resp.image_score == 0.0
    assert resp.image_available is False
    assert resp.degraded is True
    assert resp.score_source == "RULE_BASED"
    assert resp.text_score == 100.0
    assert resp.location_score == 100.0
    assert resp.time_score == 100.0
    assert resp.total_score == 100.0


def test_time_score_uses_interval_and_decays_by_hour() -> None:
    inside = _baseline.time_score_value(
        "2026-04-30T08:00:00",
        "2026-04-30T09:00:00",
        "2026-04-30T10:00:00",
    )
    after = _baseline.time_score_value(
        "2026-04-30T08:00:00",
        "2026-04-30T13:00:00",
        "2026-04-30T10:00:00",
    )
    assert inside == 100.0
    assert after == 94.0


def test_time_score_zero_when_one_missing() -> None:
    assert _baseline.time_score_value(None, "2026-04-30T09:00:00") == 0.0


def test_keyword_overlap_supports_cjk_bigrams() -> None:
    score = _baseline.keyword_overlap(["雨伞", "黑色雨伞"], ["黑色伞", "黑色雨伞"])

    assert score >= 70
