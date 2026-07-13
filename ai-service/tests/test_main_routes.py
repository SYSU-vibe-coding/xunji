"""End-to-end smoke through the FastAPI ASGI app (no real DashScope traffic)."""

from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient

SERVICE_TOKEN = "test-service-token-with-at-least-32-characters"


def _secure_settings() -> Settings:
    return Settings(
        AI_SERVICE_TOKEN=SERVICE_TOKEN,
        AI_LOCAL_DEV_MODE=False,
        AI_ALLOWED_IMAGE_HOSTS="example.com",
        _env_file=None,
    )


def test_health() -> None:
    with TestClient(create_app(_secure_settings())) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        # Without an API key configured the field is False; CI default.
        assert body["dashscope"] is False


def test_health_does_not_require_service_token() -> None:
    with TestClient(create_app(_secure_settings())) as client:
        assert client.get("/health").status_code == 200


def test_internal_route_requires_service_token() -> None:
    with TestClient(create_app(_secure_settings())) as client:
        missing = client.post("/internal/ai/classify-item", json={"itemName": "手机"})
        invalid = client.post(
            "/internal/ai/classify-item",
            headers={"X-Service-Token": "wrong"},
            json={"itemName": "手机"},
        )
        assert missing.status_code == 401
        assert invalid.status_code == 401


def test_internal_route_accepts_service_token() -> None:
    with TestClient(create_app(_secure_settings())) as client:
        resp = client.post(
            "/internal/ai/classify-item",
            headers={"X-Service-Token": SERVICE_TOKEN},
            json={"itemName": "手机"},
        )
        assert resp.status_code == 200


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
        assert body["imageScore"] == 0
        assert body["imageAvailable"] is False
        assert body["scoreSource"] == "RULE_BASED"


def test_verify_claim_answers_route_runs_baseline() -> None:
    with TestClient(create_app()) as client:
        resp = client.post(
            "/internal/ai/verify-claim-answers",
            json={
                "answers": [
                    {
                        "questionText": "伞柄上有什么特征",
                        "referenceAnswers": ["蓝色星星贴纸"],
                        "answerText": "有蓝色星星贴纸",
                    }
                ]
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["scores"] == [100]
        assert body["passed"] is True
        assert body["degraded"] is True
        assert body["source"] == "KEYWORD_RULES"


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
        assert body["maskedImageUrl"] is None
        assert body["degraded"] is True
        assert body["needsReview"] is True
