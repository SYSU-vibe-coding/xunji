"""End-to-end smoke through the FastAPI ASGI app (no real DashScope traffic)."""

from app.main import create_app
from fastapi.testclient import TestClient


def test_health() -> None:
    with TestClient(create_app()) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        # Without an API key configured the field is False; CI default.
        assert body["dashscope"] is False


def test_classify_route_runs_baseline() -> None:
    with TestClient(create_app()) as client:
        resp = client.post("/internal/ai/classify-item", json={"itemName": "手机"})
        assert resp.status_code == 200
        assert resp.json()["category"] == "ELECTRONIC"


def test_calculate_match_route_runs_baseline() -> None:
    with TestClient(create_app()) as client:
        resp = client.post(
            "/internal/ai/calculate-match",
            json={
                "lostItem": {
                    "name": "黑色雨伞",
                    "description": "蓝色贴纸",
                    "location": "图书馆",
                },
                "foundItem": {
                    "name": "黑色雨伞",
                    "description": "蓝色贴纸",
                    "location": "图书馆",
                },
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["locationScore"] == 100
        assert body["totalScore"] > 0


def test_detect_sensitive_route() -> None:
    with TestClient(create_app()) as client:
        resp = client.post(
            "/internal/ai/detect-sensitive",
            json={"imageUrl": "https://example.com/id-card.jpg"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["isSensitive"] is True
        assert body["sensitiveType"] == "ID_CARD"
