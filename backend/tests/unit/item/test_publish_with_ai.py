"""create_found_item should consult AIClient.detect_sensitive on each image."""

from unittest.mock import AsyncMock

import pytest
from app.item.repository import FoundItemRepository, ItemImageRepository
from app.item.schemas import CreateFoundItemRequest
from app.item.service import ItemService
from app.user.schemas import CurrentUser
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

OWNER = CurrentUser(id="01TESTUSER000000000000001", role="USER", status="ACTIVE")


def _req(name: str, *, category: str, urls: list[str]) -> CreateFoundItemRequest:
    return CreateFoundItemRequest(
        itemName=name,
        category=category,
        foundTime="2026-04-30 09:00:00",
        foundLocation="图书馆",
        custodyType="SECURITY",
        contactPreference="IN_APP",
        imageUrls=urls,
    )


@pytest.mark.asyncio
async def test_create_found_item_marks_sensitive_when_ai_detects(
    session: AsyncSession,
) -> None:
    fake_ai = AsyncMock()
    # First image is a non-sensitive cover; second is a real ID card.
    fake_ai.detect_sensitive.side_effect = [
        {"isSensitive": False, "sensitiveType": None, "maskedImageUrl": None},
        {
            "isSensitive": True,
            "sensitiveType": "ID_CARD",
            "maskedImageUrl": "https://x/2.jpg?masked=1",
        },
    ]
    svc = ItemService(session, ai_client=fake_ai)

    resp = await svc.create_found_item(
        _req("拾到一沓东西", category="OTHER", urls=["https://x/1.jpg", "https://x/2.jpg"]),
        OWNER,
        BackgroundTasks(),
    )

    assert resp.is_sensitive is True
    found = await FoundItemRepository(session).get_by_id(resp.id)
    assert found is not None
    assert found.is_sensitive == 1
    images = await ItemImageRepository(session).get_by_biz("FOUND", resp.id)
    by_url = {img.image_url: img for img in images}
    assert by_url["https://x/1.jpg"].masked_image_url is None
    assert by_url["https://x/2.jpg"].masked_image_url == "https://x/2.jpg?masked=1"
    assert fake_ai.detect_sensitive.await_count == 2


@pytest.mark.asyncio
async def test_create_found_item_keeps_baseline_when_no_ai(
    session: AsyncSession,
) -> None:
    """Without AIClient injected, sensitivity falls back to category-based default."""
    svc = ItemService(session, ai_client=None)
    resp = await svc.create_found_item(
        _req("一卡通", category="CERT", urls=[]),
        OWNER,
        BackgroundTasks(),
    )
    assert resp.is_sensitive is True  # CERT default
    found = await FoundItemRepository(session).get_by_id(resp.id)
    assert found is not None
    assert found.is_sensitive == 1


@pytest.mark.asyncio
async def test_create_found_item_ai_failure_does_not_break(
    session: AsyncSession,
) -> None:
    fake_ai = AsyncMock()
    fake_ai.detect_sensitive.return_value = None  # AI returned nothing
    svc = ItemService(session, ai_client=fake_ai)

    resp = await svc.create_found_item(
        _req("一把伞", category="DAILY_USE", urls=["https://x/1.jpg"]),
        OWNER,
        BackgroundTasks(),
    )
    # Falls back to default (DAILY_USE → not sensitive)
    assert resp.is_sensitive is False
