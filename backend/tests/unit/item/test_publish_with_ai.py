"""Item publication AI integration without coupling publication success to AI."""

import json
from unittest.mock import AsyncMock

import pytest
from app.item.repository import FoundItemRepository, ItemImageRepository
from app.item.schemas import CreateFoundItemRequest, FoundItemQuery
from app.item.service import ItemService, _classify_and_save, _detect_sensitive_and_save
from app.user.schemas import CurrentUser
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

OWNER = CurrentUser(id="01TESTUSER000000000000001", role="USER", status="ACTIVE")
REF_1 = f"asset://FOUND/{OWNER.id}/202607/{'a' * 32}.jpg"
REF_2 = f"asset://FOUND/{OWNER.id}/202607/{'b' * 32}.jpg"


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
        {
            "isSensitive": False,
            "sensitiveType": None,
            "maskedImageUrl": None,
            "degraded": False,
            "needsReview": False,
        },
        {
            "isSensitive": True,
            "sensitiveType": "ID_CARD",
            "maskedImageUrl": "https://x/2.jpg?masked=1",
            "degraded": False,
            "needsReview": False,
        },
    ]
    svc = ItemService(session, ai_client=fake_ai)

    resp = await svc.create_found_item(
        _req("拾到一沓东西", category="OTHER", urls=[REF_1, REF_2]),
        OWNER,
        BackgroundTasks(),
    )

    assert resp.is_sensitive is True
    found = await FoundItemRepository(session).get_by_id(resp.id)
    assert found is not None
    assert found.is_sensitive == 1
    images = await ItemImageRepository(session).get_by_biz("FOUND", resp.id)
    by_url = {img.image_url: img for img in images}
    assert by_url[REF_1].masked_image_url is None
    assert by_url[REF_2].masked_image_url is None
    # Publication only writes the outbox and returns; the runner performs AI work.
    fake_ai.detect_sensitive.assert_not_awaited()

    await _detect_sensitive_and_save(session, resp.id, fake_ai)

    assert fake_ai.detect_sensitive.await_count == 2
    assert all(
        call.args[0].startswith("http://minio:9000/")
        for call in fake_ai.detect_sensitive.await_args_list
    )


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
        _req("一把伞", category="DAILY_USE", urls=[REF_1]),
        OWNER,
        BackgroundTasks(),
    )
    # Image-bearing FOUND records fail closed before asynchronous review.
    assert resp.is_sensitive is True
    fake_ai.detect_sensitive.assert_not_awaited()
    with pytest.raises(RuntimeError, match="no usable result"):
        await _detect_sensitive_and_save(session, resp.id, fake_ai)
    found = await FoundItemRepository(session).get_by_id(resp.id)
    assert found is not None
    assert found.is_sensitive == 1


@pytest.mark.asyncio
async def test_sensitive_review_releases_only_explicitly_safe_images(
    session: AsyncSession,
) -> None:
    svc = ItemService(session)
    created = await svc.create_found_item(
        _req("普通雨伞", category="DAILY_USE", urls=[REF_1, REF_2]),
        OWNER,
        BackgroundTasks(),
    )
    fake_ai = AsyncMock()
    fake_ai.detect_sensitive.return_value = {
        "isSensitive": False,
        "degraded": False,
        "needsReview": False,
    }

    await _detect_sensitive_and_save(session, created.id, fake_ai)

    found = await FoundItemRepository(session).get_by_id(created.id)
    assert found is not None
    assert found.is_sensitive == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "detection",
    [
        {"isSensitive": False, "degraded": True, "needsReview": False},
        {"isSensitive": False, "degraded": False, "needsReview": True},
    ],
)
async def test_sensitive_review_keeps_degraded_or_review_results_private(
    session: AsyncSession,
    detection: dict[str, bool],
) -> None:
    created = await ItemService(session).create_found_item(
        _req("待复核物品", category="OTHER", urls=[REF_1]),
        OWNER,
        BackgroundTasks(),
    )
    fake_ai = AsyncMock()
    fake_ai.detect_sensitive.return_value = detection

    await _detect_sensitive_and_save(session, created.id, fake_ai)

    found = await FoundItemRepository(session).get_by_id(created.id)
    assert found is not None
    assert found.is_sensitive == 1


@pytest.mark.asyncio
async def test_background_classification_saves_structured_tags_without_overriding_category(
    session: AsyncSession,
) -> None:
    svc = ItemService(session)
    created = await svc.create_found_item(
        _req("一个黑色物品", category="OTHER", urls=[REF_1]),
        OWNER,
        BackgroundTasks(),
    )
    fake_ai = AsyncMock()
    fake_ai.classify_item.return_value = {
        "category": "ELECTRONIC",
        "tags": ["蓝牙耳机", "黑色"],
        "confidence": 91.5,
        "source": "VISION_MODEL",
        "degraded": False,
    }

    await _classify_and_save(session, "FOUND", created.id, fake_ai)

    found = await FoundItemRepository(session).get_by_id(created.id)
    assert found is not None
    assert found.category == "OTHER"
    assert json.loads(found.ai_tags or "{}") == {
        "tags": ["蓝牙耳机", "黑色"],
        "suggestedCategory": "ELECTRONIC",
        "confidence": 91.5,
        "source": "VISION_MODEL",
        "degraded": False,
    }
    assert fake_ai.classify_item.await_args.kwargs["image_urls"][0].startswith(
        "http://minio:9000/"
    )
    search = await svc.list_found_items(FoundItemQuery(keyword="蓝牙耳机"), OWNER)
    assert [item["id"] for item in search["list"]] == [created.id]
