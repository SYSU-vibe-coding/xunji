"""High-priority MATCH_RECOMMEND notification on score ≥ 90 + CERT."""

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from app.db.ulid import generate_ulid
from app.item.models import FoundItem, LostItem
from app.match import service as match_service
from app.notification.repository import NotificationRepository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def patch_session_factory(monkeypatch, session: AsyncSession):
    @asynccontextmanager
    async def factory():
        yield session

    monkeypatch.setattr(match_service, "async_session_factory", factory)
    return session


def _seed_pair(session: AsyncSession, *, category: str) -> tuple[LostItem, FoundItem]:
    lost = LostItem(
        id=generate_ulid(),
        user_id="01TESTUSER000000000000001",
        item_name="校园卡",
        category=category,
        description="蓝色校园卡",
        lost_time_start=datetime(2026, 4, 30, 8, 0, 0),
        lost_time_end=datetime(2026, 4, 30, 12, 0, 0),
        lost_location="图书馆",
        subscribe_match=1,
        status="SEARCHING",
        review_status="APPROVED",
    )
    found = FoundItem(
        id=generate_ulid(),
        user_id="01TESTSTAFF00000000000001",
        item_name="校园卡",
        category=category,
        description="蓝色校园卡",
        found_time=datetime(2026, 4, 30, 9, 0, 0),
        found_location="图书馆",
        is_sensitive=1 if category == "CERT" else 0,
        custody_type="SECURITY",
        contact_preference="IN_APP",
        status="PENDING",
        review_status="APPROVED",
    )
    session.add_all([lost, found])
    return lost, found


async def _read_notices(session: AsyncSession, user_id: str):
    repo = NotificationRepository(session)
    items, total = await repo.list_by_user(
        user_id=user_id, is_read=None, notice_type=None, offset=0, limit=10
    )
    return items, total


async def test_high_priority_notice_on_cert_above_90(
    patch_session_factory, session: AsyncSession
) -> None:
    lost, _ = _seed_pair(session, category="CERT")
    await session.commit()

    fake_client = AsyncMock()
    fake_client.calculate_match.return_value = {
        "imageScore": 90,
        "textScore": 100,
        "locationScore": 100,
        "timeScore": 80,
        "totalScore": 95,
    }

    written = await match_service.trigger_match("LOST", lost.id, ai_client=fake_client)
    assert written == 1

    items, total = await _read_notices(session, lost.user_id)
    assert total == 1
    notice = items[0]
    assert notice.notice_type == "MATCH_RECOMMEND"
    assert notice.priority == "HIGH"
    assert notice.related_type == "MATCH"


async def test_no_high_priority_when_score_just_70(
    patch_session_factory, session: AsyncSession
) -> None:
    lost, _ = _seed_pair(session, category="CERT")
    await session.commit()

    fake_client = AsyncMock()
    fake_client.calculate_match.return_value = {
        "imageScore": 60,
        "textScore": 80,
        "locationScore": 80,
        "timeScore": 60,
        "totalScore": 72,
    }

    written = await match_service.trigger_match("LOST", lost.id, ai_client=fake_client)
    assert written == 1

    _, total = await _read_notices(session, lost.user_id)
    assert total == 0


async def test_no_high_priority_when_category_not_cert(
    patch_session_factory, session: AsyncSession
) -> None:
    lost, _ = _seed_pair(session, category="ELECTRONIC")
    await session.commit()

    fake_client = AsyncMock()
    fake_client.calculate_match.return_value = {
        "imageScore": 95,
        "textScore": 100,
        "locationScore": 100,
        "timeScore": 90,
        "totalScore": 96,
    }

    written = await match_service.trigger_match("LOST", lost.id, ai_client=fake_client)
    assert written == 1

    _, total = await _read_notices(session, lost.user_id)
    assert total == 0
