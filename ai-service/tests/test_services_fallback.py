"""Service-layer behavior: DashScope path vs. fallback to baseline.

We don't mock the transport here — instead we rely on the *no-key* branch of
the client, which is exactly the path CI takes by default. The DashScope
happy-path is verified in ``test_clients_dashscope.py``.
"""

import pytest
from app.clients.dashscope import DashScopeClient
from app.schemas import (
    CalculateMatchRequest,
    ClassifyItemRequest,
    DetectSensitiveRequest,
    MatchItem,
)
from app.services import classify, match, sensitive


@pytest.fixture
def disabled_client() -> DashScopeClient:
    return DashScopeClient(api_key="")


@pytest.mark.asyncio
async def test_classify_falls_back_when_disabled(disabled_client: DashScopeClient) -> None:
    try:
        resp = await classify.classify_item(ClassifyItemRequest(itemName="校园卡"), disabled_client)
        assert resp.category == "CERT"
    finally:
        await disabled_client.aclose()


@pytest.mark.asyncio
async def test_classify_falls_back_when_no_image() -> None:
    """Even with key, no image → no signal for VL → fallback path."""
    client = DashScopeClient(api_key="fake")  # transport never hit
    try:
        resp = await classify.classify_item(ClassifyItemRequest(itemName="手机"), client)
        assert resp.category == "ELECTRONIC"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_sensitive_falls_back_when_disabled(disabled_client: DashScopeClient) -> None:
    try:
        resp = await sensitive.detect_sensitive(
            DetectSensitiveRequest(imageUrl="https://x/id-card.jpg"), disabled_client
        )
        assert resp.is_sensitive is True
        assert resp.sensitive_type == "ID_CARD"
    finally:
        await disabled_client.aclose()


@pytest.mark.asyncio
async def test_match_falls_back_when_disabled(disabled_client: DashScopeClient) -> None:
    try:
        req = CalculateMatchRequest(
            lostItem=MatchItem(name="黑色雨伞", description="蓝色贴纸", location="图书馆"),
            foundItem=MatchItem(name="黑色雨伞", description="蓝色贴纸", location="图书馆"),
        )
        resp = await match.calculate_match(req, disabled_client)
        assert resp.location_score == 100.0
        assert resp.total_score > 0
    finally:
        await disabled_client.aclose()


@pytest.mark.asyncio
async def test_match_falls_back_when_no_text() -> None:
    """With key but empty descriptions, embedding has nothing to compare."""
    client = DashScopeClient(api_key="fake")
    try:
        req = CalculateMatchRequest(
            lostItem=MatchItem(location="图书馆"),
            foundItem=MatchItem(location="图书馆"),
        )
        resp = await match.calculate_match(req, client)
        # baseline path → text_score = 0 because no tokens
        assert resp.text_score == 0.0
        assert resp.location_score == 100.0
    finally:
        await client.aclose()


def test_classify_parses_dashscope_reply() -> None:
    assert classify._parse_category("CERT") == "CERT"
    assert classify._parse_category("电子产品 ELECTRONIC") == "ELECTRONIC"
    assert classify._parse_category("不知道") is None


def test_sensitive_parses_dashscope_reply() -> None:
    assert sensitive._parse_sensitive("ID_CARD") == "ID_CARD"
    assert sensitive._parse_sensitive("NONE") == "NONE"
    assert sensitive._parse_sensitive("奇怪的话") is None
