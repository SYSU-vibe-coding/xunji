from app.main import create_app
from app.schemas import (
    CalculateMatchRequest,
    ClassifyItemRequest,
    DetectSensitiveRequest,
    MatchItem,
)
from app.service import calculate_match, classify_item, detect_sensitive
from fastapi.testclient import TestClient


def test_classify_item_cert() -> None:
    resp = classify_item(ClassifyItemRequest(itemName="校园卡"))
    assert resp.category == "CERT"
    assert resp.confidence > 50


def test_detect_sensitive_card() -> None:
    resp = detect_sensitive(DetectSensitiveRequest(imageUrl="https://example.com/campus-card.jpg"))
    assert resp.is_sensitive is True
    assert resp.masked_image_url is not None


def test_calculate_match_score() -> None:
    resp = calculate_match(
        CalculateMatchRequest(
            lostItem=MatchItem(name="黑色雨伞", description="蓝色贴纸", location="图书馆"),
            foundItem=MatchItem(name="黑色雨伞", description="蓝色贴纸", location="图书馆"),
        )
    )
    assert resp.total_score > 0
    assert resp.location_score == 100


def test_internal_routes() -> None:
    client = TestClient(create_app())
    health = client.get("/health")
    assert health.status_code == 200
    resp = client.post("/internal/ai/classify-item", json={"itemName": "手机"})
    assert resp.status_code == 200
    assert resp.json()["category"] == "ELECTRONIC"
