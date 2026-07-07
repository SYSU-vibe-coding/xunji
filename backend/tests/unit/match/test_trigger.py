"""trigger_match end-to-end on in-memory DB with mocked AIClient."""

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from app.db.ulid import generate_ulid
from app.item.models import FoundItem, ItemImage, LostItem
from app.match import service as match_service
from app.match.repository import MatchResultRepository
from sqlalchemy.ext.asyncio import AsyncSession


def _make_lost(session: AsyncSession, name: str, location: str) -> LostItem:
    item = LostItem(
        id=generate_ulid(),
        user_id="01TESTUSER000000000000001",
        item_name=name,
        category="DAILY_USE",
        description="蓝色贴纸",
        lost_time_start=datetime(2026, 4, 30, 8, 0, 0),
        lost_time_end=datetime(2026, 4, 30, 12, 0, 0),
        lost_location=location,
        subscribe_match=1,
        status="SEARCHING",
        review_status="APPROVED",
    )
    session.add(item)
    return item


def _make_found(session: AsyncSession, name: str, location: str) -> FoundItem:
    item = FoundItem(
        id=generate_ulid(),
        user_id="01TESTSTAFF00000000000001",
        item_name=name,
        category="DAILY_USE",
        description="蓝色贴纸",
        found_time=datetime(2026, 4, 30, 9, 0, 0),
        found_location=location,
        is_sensitive=0,
        custody_type="SECURITY",
        contact_preference="IN_APP",
        status="PENDING",
        review_status="APPROVED",
    )
    session.add(item)
    return item


def _attach_image(session: AsyncSession, biz_type: str, biz_id: str) -> None:
    session.add(
        ItemImage(
            id=generate_ulid(),
            biz_type=biz_type,
            biz_id=biz_id,
            image_url=f"https://x/{biz_id}.jpg",
            sort_order=0,
        )
    )


@pytest.fixture
def patch_session_factory(monkeypatch, session: AsyncSession):
    """Make trigger_match reuse our in-memory test session."""

    @asynccontextmanager
    async def factory():
        yield session

    monkeypatch.setattr(match_service, "async_session_factory", factory)
    return session


async def test_trigger_match_writes_when_above_threshold(
    patch_session_factory, session: AsyncSession
) -> None:
    lost = _make_lost(session, "黑色雨伞", "图书馆")
    found = _make_found(session, "黑色雨伞", "图书馆")
    _attach_image(session, "LOST", lost.id)
    _attach_image(session, "FOUND", found.id)
    await session.commit()

    fake_client = AsyncMock()
    fake_client.calculate_match.return_value = {
        "imageScore": 80,
        "textScore": 80,
        "locationScore": 100,
        "timeScore": 70,
        "totalScore": 82,
    }

    written = await match_service.trigger_match("LOST", lost.id, ai_client=fake_client)

    assert written == 1
    fake_client.calculate_match.assert_awaited_once()
    repo = MatchResultRepository(session)
    match = await repo.get_by_pair(lost.id, found.id)
    assert match is not None
    assert float(match.total_score) == 82.0
    assert match.match_status == "NEW"


async def test_trigger_match_skips_when_below_threshold(
    patch_session_factory, session: AsyncSession
) -> None:
    lost = _make_lost(session, "黑色雨伞", "图书馆")
    found = _make_found(session, "白色钱包", "操场")
    await session.commit()

    fake_client = AsyncMock()
    fake_client.calculate_match.return_value = {
        "imageScore": 0,
        "textScore": 10,
        "locationScore": 0,
        "timeScore": 30,
        "totalScore": 12,
    }

    written = await match_service.trigger_match("LOST", lost.id, ai_client=fake_client)

    assert written == 0
    repo = MatchResultRepository(session)
    assert await repo.get_by_pair(lost.id, found.id) is None


async def test_trigger_match_falls_back_when_ai_returns_none(
    patch_session_factory, session: AsyncSession
) -> None:
    lost = _make_lost(session, "黑色雨伞", "图书馆")
    found = _make_found(session, "黑色雨伞", "图书馆")
    _attach_image(session, "LOST", lost.id)
    _attach_image(session, "FOUND", found.id)
    await session.commit()

    fake_client = AsyncMock()
    fake_client.calculate_match.return_value = None  # AI failure

    written = await match_service.trigger_match("LOST", lost.id, ai_client=fake_client)

    # Identical name+location+images → rule-based score should clear 70.
    assert written == 1


async def test_trigger_match_unknown_biz_type_is_safe(
    patch_session_factory, session: AsyncSession
) -> None:
    fake_client = AsyncMock()
    written = await match_service.trigger_match("UNKNOWN", generate_ulid(), ai_client=fake_client)
    assert written == 0
    fake_client.calculate_match.assert_not_awaited()
