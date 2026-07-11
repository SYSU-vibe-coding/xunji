"""AIClient unit tests using httpx.MockTransport (no real AI service)."""

import json

import httpx
import pytest
from app.core.ai_client import AIClient
from app.core.config import settings


def _ok(body: dict) -> httpx.Response:
    return httpx.Response(200, content=json.dumps(body))


@pytest.mark.asyncio
async def test_calculate_match_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_SERVICE_TOKEN", "test-service-token")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/internal/ai/calculate-match"
        assert request.headers["X-Service-Token"] == "test-service-token"
        return _ok(
            {
                "imageScore": 0,
                "textScore": 80,
                "locationScore": 100,
                "timeScore": 50,
                "totalScore": 75,
                "imageAvailable": False,
                "degraded": True,
                "scoreSource": "TEXT_MODEL_RULES",
            }
        )

    client = AIClient(transport=httpx.MockTransport(handler))
    try:
        data = await client.calculate_match(
            lost={"name": "x", "location": "A", "time": "2026-01-01T00:00:00"},
            found={"name": "x", "location": "A", "time": "2026-01-01T01:00:00"},
        )
        assert data is not None
        assert data["totalScore"] == 81.67
        assert data["imageAvailable"] is False
        assert data["scoreSource"] == "TEXT_MODEL_RULES"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_calculate_match_5xx_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content="boom")

    client = AIClient(transport=httpx.MockTransport(handler))
    try:
        assert await client.calculate_match(lost={}, found={}) is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_calculate_match_timeout_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("simulated", request=request)

    client = AIClient(transport=httpx.MockTransport(handler))
    try:
        assert await client.calculate_match(lost={}, found={}) is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_calculate_match_bad_shape_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _ok({"oops": True})

    client = AIClient(transport=httpx.MockTransport(handler))
    try:
        assert await client.calculate_match(lost={}, found={}) is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_score", [float("nan"), float("inf"), -1, 101, True, "90"])
async def test_calculate_match_rejects_invalid_scores(bad_score: object) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _ok(
            {
                "imageScore": bad_score,
                "textScore": 80,
                "locationScore": 100,
                "timeScore": 50,
                "totalScore": 75,
                "imageAvailable": False,
                "degraded": True,
                "scoreSource": "RULE_BASED",
            }
        )

    client = AIClient(transport=httpx.MockTransport(handler))
    try:
        assert await client.calculate_match(lost={}, found={}) is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_calculate_match_rejects_fake_image_score_when_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _ok(
            {
                "imageScore": 60,
                "textScore": 80,
                "locationScore": 100,
                "timeScore": 50,
                "totalScore": 75,
                "imageAvailable": False,
                "degraded": True,
                "scoreSource": "RULE_BASED",
            }
        )

    client = AIClient(transport=httpx.MockTransport(handler))
    try:
        assert await client.calculate_match(lost={"name": "x"}, found={"name": "x"}) is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_classify_item_skips_when_no_signal() -> None:
    client = AIClient()
    try:
        # No image_urls and no item_name → don't bother making a call.
        assert await client.classify_item() is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_detect_sensitive_returns_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/internal/ai/detect-sensitive"
        return _ok(
            {
                "isSensitive": True,
                "sensitiveType": "ID_CARD",
                "maskedImageUrl": "https://x?masked=1",
            }
        )

    client = AIClient(transport=httpx.MockTransport(handler))
    try:
        data = await client.detect_sensitive("https://x")
        assert data is not None
        assert data["isSensitive"] is True
        assert data["maskedImageUrl"].endswith("masked=1")
    finally:
        await client.aclose()
