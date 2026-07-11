"""trigger_match end-to-end on in-memory DB with mocked AIClient."""

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from app.db.ulid import generate_ulid
from app.item.models import FoundItem, ItemImage, LostItem
from app.item.service import ItemService
from app.match import jobs as match_jobs
from app.match import service as match_service
from app.match.repository import MatchResultRepository
from app.notification.models import Notification
from app.user.models import User
from sqlalchemy import func, select
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
def patch_session_factory(monkeypatch, session: AsyncSession, seeded_users: None):
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
        "imageAvailable": False,
        "degraded": True,
        "scoreSource": "TEXT_MODEL_RULES",
    }

    written = await match_service.trigger_match("LOST", lost.id, ai_client=fake_client)

    assert written == 1
    fake_client.calculate_match.assert_awaited_once()
    repo = MatchResultRepository(session)
    match = await repo.get_by_pair(lost.id, found.id)
    assert match is not None
    assert float(match.total_score) == 82.0
    assert float(match.image_score) == 0.0
    assert match.image_available == 0
    assert match.degraded == 1
    assert match.score_source == "TEXT_MODEL_RULES"
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
    match = await MatchResultRepository(session).get_by_pair(lost.id, found.id)
    assert match is not None
    assert match.image_score == 0
    assert match.score_source == "RULE_BASED"


async def test_trigger_match_unknown_biz_type_is_safe(
    patch_session_factory, session: AsyncSession
) -> None:
    fake_client = AsyncMock()
    written = await match_service.trigger_match("UNKNOWN", generate_ulid(), ai_client=fake_client)
    assert written == 0
    fake_client.calculate_match.assert_not_awaited()


async def test_recalculation_below_threshold_expires_existing_match(
    patch_session_factory, session: AsyncSession
) -> None:
    lost = _make_lost(session, "Black Wallet", "Library")
    found = _make_found(session, "Black Wallet", "Library")
    await session.commit()
    fake_client = AsyncMock()
    fake_client.calculate_match.side_effect = [
        {
            "imageScore": 80,
            "textScore": 80,
            "locationScore": 80,
            "timeScore": 80,
            "totalScore": 80,
        },
        {
            "imageScore": 10,
            "textScore": 10,
            "locationScore": 10,
            "timeScore": 10,
            "totalScore": 10,
        },
    ]

    assert await match_service.trigger_match("LOST", lost.id, ai_client=fake_client) == 1
    assert await match_service.trigger_match("LOST", lost.id, ai_client=fake_client) == 0

    match = await MatchResultRepository(session).get_by_pair(lost.id, found.id)
    assert match is not None
    assert match.match_status == "EXPIRED"


async def test_trigger_match_excludes_same_user_and_unapproved_candidates(
    patch_session_factory, session: AsyncSession
) -> None:
    lost = _make_lost(session, "Black Wallet", "Library")
    same_user_found = _make_found(session, "Black Wallet", "Library")
    same_user_found.user_id = lost.user_id
    unapproved_found = _make_found(session, "Black Wallet", "Library")
    unapproved_found.review_status = "PENDING"
    await session.commit()
    fake_client = AsyncMock()
    fake_client.calculate_match.return_value = {
        "imageScore": 100,
        "textScore": 100,
        "locationScore": 100,
        "timeScore": 100,
        "totalScore": 100,
    }

    written = await match_service.trigger_match("LOST", lost.id, ai_client=fake_client)

    assert written == 0
    fake_client.calculate_match.assert_not_awaited()


async def test_trigger_match_relocks_lost_then_found_before_write(
    patch_session_factory,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lost = _make_lost(session, "Black Wallet", "Library")
    _make_found(session, "Black Wallet", "Library")
    await session.commit()
    lock_order: list[str] = []
    original_lost_lock = ItemService.get_lost_item_for_update_internal
    original_found_lock = ItemService.get_found_item_for_update_internal

    async def lock_lost(self: ItemService, item_id: str) -> LostItem:
        lock_order.append("LOST")
        return await original_lost_lock(self, item_id)

    async def lock_found(self: ItemService, item_id: str) -> FoundItem:
        lock_order.append("FOUND")
        return await original_found_lock(self, item_id)

    monkeypatch.setattr(ItemService, "get_lost_item_for_update_internal", lock_lost)
    monkeypatch.setattr(ItemService, "get_found_item_for_update_internal", lock_found)
    fake_client = AsyncMock()
    fake_client.calculate_match.return_value = {"totalScore": 90}

    assert await match_service.trigger_match("LOST", lost.id, ai_client=fake_client) == 1
    assert lock_order == ["LOST", "FOUND"]


async def test_close_during_scoring_leaves_no_active_match_or_new_notice(
    patch_session_factory,
    session: AsyncSession,
) -> None:
    lost = _make_lost(session, "Black Wallet", "Library")
    found = _make_found(session, "Black Wallet", "Library")
    await session.commit()
    fake_client = AsyncMock()
    fake_client.calculate_match.return_value = {"totalScore": 90}
    assert await match_service.trigger_match("LOST", lost.id, ai_client=fake_client) == 1

    async def close_found_during_score(**_: object) -> dict[str, float]:
        found.status = "CLOSED"
        await session.flush()
        return {"totalScore": 95}

    fake_client.calculate_match.side_effect = close_found_during_score
    assert await match_service.trigger_match("LOST", lost.id, ai_client=fake_client) == 0

    match = await MatchResultRepository(session).get_by_pair(lost.id, found.id)
    notice_count = await session.scalar(select(func.count()).select_from(Notification))
    assert match is not None
    assert match.match_status == "EXPIRED"
    assert notice_count == 1


async def test_claim_during_scoring_keeps_claimed_match(
    patch_session_factory,
    session: AsyncSession,
) -> None:
    lost = _make_lost(session, "Black Wallet", "Library")
    found = _make_found(session, "Black Wallet", "Library")
    await session.commit()
    fake_client = AsyncMock()
    fake_client.calculate_match.return_value = {"totalScore": 90}
    assert await match_service.trigger_match("LOST", lost.id, ai_client=fake_client) == 1
    match = await MatchResultRepository(session).get_by_pair(lost.id, found.id)
    assert match is not None

    async def claim_during_score(**_: object) -> dict[str, float]:
        found.status = "CLAIMING"
        match.match_status = "CLAIMED"
        await session.flush()
        return {"totalScore": 95}

    fake_client.calculate_match.side_effect = claim_during_score
    assert await match_service.trigger_match("LOST", lost.id, ai_client=fake_client) == 0

    await session.refresh(match)
    assert match.match_status == "CLAIMED"


async def test_full_job_revalidates_pair_after_scoring(
    session: AsyncSession,
    seeded_users: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lost = _make_lost(session, "Black Wallet", "Library")
    found = _make_found(session, "Black Wallet", "Library")
    await session.commit()

    @asynccontextmanager
    async def factory():
        yield session

    async def close_found_during_score(**_: object) -> dict[str, float]:
        found.status = "CLOSED"
        await session.flush()
        return {"totalScore": 95}

    fake_client = AsyncMock()
    fake_client.calculate_match.side_effect = close_found_during_score
    monkeypatch.setattr(match_jobs, "async_session_factory", factory)
    monkeypatch.setattr(match_jobs, "AIClient", lambda: fake_client)

    written = await match_jobs.MatchJobRunner()._score_all_pairs()

    assert written == 0
    assert await MatchResultRepository(session).get_by_pair(lost.id, found.id) is None


async def test_match_candidates_exclude_disabled_publishers(
    patch_session_factory,
    session: AsyncSession,
) -> None:
    lost = _make_lost(session, "Black Wallet", "Library")
    _make_found(session, "Black Wallet", "Library")
    finder = await session.get(User, "01TESTSTAFF00000000000001")
    assert finder is not None
    finder.status = "DISABLED"
    await session.commit()
    fake_client = AsyncMock()
    fake_client.calculate_match.return_value = {"totalScore": 100}

    assert await match_service.trigger_match("LOST", lost.id, ai_client=fake_client) == 0
    fake_client.calculate_match.assert_not_awaited()
