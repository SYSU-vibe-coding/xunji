"""AIClient unit tests using httpx.MockTransport (no real AI service)."""

import json

import httpx
import pytest
from app.core.ai_client import AIClient


def _ok(body: dict) -> httpx.Response:
    return httpx.Response(200, content=json.dumps(body))


@pytest.mark.asyncio
async def test_calculate_match_returns_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/internal/ai/calculate-match"
        return _ok(
            {
                "imageScore": 60,
                "textScore": 80,
                "locationScore": 100,
                "timeScore": 50,
                "totalScore": 75,
            }
        )

    client = AIClient(transport=httpx.MockTransport(handler))
    try:
        data = await client.calculate_match(lost={"name": "x"}, found={"name": "x"})
        assert data is not None
        assert data["totalScore"] == 75
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
