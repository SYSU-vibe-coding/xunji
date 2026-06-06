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
    assert resp.masked_image_url is not None
    assert resp.sensitive_type == "CAMPUS_CARD"


def test_detect_sensitive_negative() -> None:
    resp = _baseline.detect_sensitive(
        DetectSensitiveRequest(imageUrl="https://example.com/umbrella.jpg")
    )
    assert resp.is_sensitive is False
    assert resp.masked_image_url is None


def test_calculate_match_score() -> None:
    resp = _baseline.calculate_match(
        CalculateMatchRequest(
            lostItem=MatchItem(name="黑色雨伞", description="蓝色贴纸", location="图书馆"),
            foundItem=MatchItem(name="黑色雨伞", description="蓝色贴纸", location="图书馆"),
        )
    )
    assert resp.total_score > 0
    assert resp.location_score == 100


def test_time_score_decays_with_hours() -> None:
    near = _baseline.time_score_value("2026-04-30T08:00:00", "2026-04-30T09:00:00")
    far = _baseline.time_score_value("2026-04-30T08:00:00", "2026-05-03T08:00:00")
    assert near > far
    assert far == 0.0  # 72h * 2 = 144 → clamped to 0


def test_time_score_zero_when_one_missing() -> None:
    assert _baseline.time_score_value(None, "2026-04-30T09:00:00") == 0.0
