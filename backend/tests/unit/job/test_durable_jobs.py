from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from app.core.ai_client import AIClient
from app.core.config import settings
from app.db.ulid import generate_ulid
from app.item.models import FoundItem, LostItem
from app.item.schemas import CreateFoundItemRequest, CreateLostItemRequest, UpdateLostItemRequest
from app.item.service import ItemService
from app.job.models import DurableJob
from app.job.runner import DurableJobRunner
from app.job.service import enqueue_item_jobs, execute_durable_job
from app.match.models import MatchResult
from app.notification.models import Notification
from app.user.schemas import CurrentUser
from fastapi import BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TestSessionFactory

OWNER = CurrentUser(id="01TESTUSER000000000000001", role="USER", status="ACTIVE")
OTHER_USER_ID = "01TESTSTAFF00000000000001"
FOUND_REF = f"asset://FOUND/{OWNER.id}/202607/{'d' * 32}.jpg"


def _lost(item_id: str | None = None) -> LostItem:
    return LostItem(
        id=item_id or generate_ulid(),
        user_id=OWNER.id,
        item_name="Black umbrella",
        category="DAILY_USE",
        description="blue sticker",
        lost_time_start=datetime(2026, 7, 11, 8),
        lost_time_end=datetime(2026, 7, 11, 10),
        lost_location="Library",
        subscribe_match=1,
        status="SEARCHING",
        review_status="APPROVED",
    )


def _job(
    *,
    job_type: str,
    biz_type: str,
    biz_id: str,
    version: int = 1,
    status: str = "PENDING",
) -> DurableJob:
    return DurableJob(
        id=generate_ulid(),
        job_type=job_type,
        biz_type=biz_type,
        biz_id=biz_id,
        biz_version=version,
        status=status,
        attempts=0,
        run_after=datetime.now(UTC).replace(tzinfo=None),
    )


def _successful_classification() -> dict[str, Any]:
    return {
        "category": "DAILY_USE",
        "tags": ["umbrella"],
        "confidence": 90,
        "source": "VISION_MODEL",
        "degraded": False,
    }


async def test_enqueue_is_rolled_back_with_business_transaction(session: AsyncSession) -> None:
    lost = _lost()
    session.add(lost)
    await session.flush()
    await enqueue_item_jobs(
        session,
        biz_type="LOST",
        biz_id=lost.id,
        has_images=False,
    )

    await session.rollback()

    assert await session.get(LostItem, lost.id) is None
    count = await session.scalar(select(func.count()).select_from(DurableJob))
    assert count == 0


async def test_item_create_and_update_persist_versioned_jobs(session: AsyncSession) -> None:
    service = ItemService(session)
    created = await service.create_lost_item(
        CreateLostItemRequest(
            itemName="Versioned umbrella",
            category="DAILY_USE",
            lostTimeStart="2026-07-11 08:00:00",
            lostTimeEnd="2026-07-11 10:00:00",
            lostLocation="Library",
        ),
        OWNER,
        BackgroundTasks(),
    )
    await service.update_lost_item(
        created.id,
        UpdateLostItemRequest(
            itemName="Versioned umbrella updated",
            category="DAILY_USE",
            lostTimeStart="2026-07-11 08:00:00",
            lostTimeEnd="2026-07-11 10:00:00",
            lostLocation="Library gate",
        ),
        OWNER,
        BackgroundTasks(),
    )

    jobs = list(
        (
            await session.execute(
                select(DurableJob)
                .where(DurableJob.biz_id == created.id)
                .order_by(DurableJob.biz_version, DurableJob.job_type)
            )
        )
        .scalars()
        .all()
    )
    assert [(job.biz_version, job.job_type) for job in jobs] == [
        (1, "CLASSIFY"),
        (1, "MATCH"),
        (2, "CLASSIFY"),
        (2, "MATCH"),
    ]
    assert {job.status for job in jobs} == {"PENDING"}


async def test_found_with_image_persists_sensitive_job_and_fails_closed(
    session: AsyncSession,
) -> None:
    created = await ItemService(session).create_found_item(
        CreateFoundItemRequest(
            itemName="Image-bearing item",
            category="OTHER",
            foundTime="2026-07-11 09:00:00",
            foundLocation="Library",
            custodyType="SECURITY",
            contactPreference="IN_APP",
            imageUrls=[FOUND_REF],
        ),
        OWNER,
        BackgroundTasks(),
    )

    item = await session.get(FoundItem, created.id)
    jobs = (
        await session.execute(select(DurableJob).where(DurableJob.biz_id == created.id))
    ).scalars()
    assert item is not None
    assert item.is_sensitive == 1
    assert {job.job_type for job in jobs} == {"MATCH", "CLASSIFY", "SENSITIVE"}


async def test_runner_retries_then_marks_failed(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lost = _lost()
    job = _job(job_type="CLASSIFY", biz_type="LOST", biz_id=lost.id)
    session.add_all([lost, job])
    await session.commit()
    client = AsyncMock(spec=AIClient)
    client.classify_item.return_value = None
    monkeypatch.setattr(settings, "DURABLE_JOB_RETRY_BASE_SECONDS", 0.0)
    monkeypatch.setattr(settings, "DURABLE_JOB_MAX_ATTEMPTS", 2)
    runner = DurableJobRunner(
        session_factory=TestSessionFactory,
        ai_client_factory=lambda: cast(AIClient, client),
    )

    assert await runner.run_once() is True
    await session.refresh(job)
    assert job.status == "PENDING"
    assert job.attempts == 1
    assert job.last_error is not None

    assert await runner.run_once() is True
    await session.refresh(job)
    assert job.status == "FAILED"
    assert job.attempts == 2


async def test_new_runner_recovers_stale_running_job(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lost = _lost()
    job = _job(
        job_type="CLASSIFY",
        biz_type="LOST",
        biz_id=lost.id,
        status="RUNNING",
    )
    job.attempts = 1
    job.locked_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=10)
    session.add_all([lost, job])
    await session.commit()
    client = AsyncMock(spec=AIClient)
    client.classify_item.return_value = _successful_classification()
    monkeypatch.setattr(settings, "DURABLE_JOB_LOCK_TIMEOUT_SECONDS", 1)
    restarted_runner = DurableJobRunner(
        session_factory=TestSessionFactory,
        ai_client_factory=lambda: cast(AIClient, client),
    )

    assert await restarted_runner.run_once() is True

    await session.refresh(job)
    await session.refresh(lost)
    assert job.status == "COMPLETED"
    assert job.attempts == 2
    assert lost.ai_tags is not None


async def test_old_version_skips_and_new_version_can_execute(session: AsyncSession) -> None:
    lost = _lost()
    old_job = _job(job_type="CLASSIFY", biz_type="LOST", biz_id=lost.id, version=1)
    new_job = _job(job_type="CLASSIFY", biz_type="LOST", biz_id=lost.id, version=2)
    session.add_all([lost, old_job, new_job])
    await session.commit()
    client = AsyncMock(spec=AIClient)
    client.classify_item.return_value = _successful_classification()
    typed_client = cast(AIClient, client)

    await execute_durable_job(session, old_job, ai_client=typed_client)
    client.classify_item.assert_not_awaited()
    await execute_durable_job(session, new_job, ai_client=typed_client)

    client.classify_item.assert_awaited_once()
    assert lost.ai_tags is not None


async def test_duplicate_match_execution_does_not_duplicate_match_or_notice(
    session: AsyncSession,
    seeded_users: None,
) -> None:
    lost = _lost()
    found = FoundItem(
        id=generate_ulid(),
        user_id=OTHER_USER_ID,
        item_name="Black umbrella",
        category="DAILY_USE",
        description="blue sticker",
        found_time=datetime(2026, 7, 11, 9),
        found_location="Library",
        is_sensitive=0,
        custody_type="SECURITY",
        contact_preference="IN_APP",
        status="PENDING",
        review_status="APPROVED",
    )
    job = _job(job_type="MATCH", biz_type="LOST", biz_id=lost.id, status="RUNNING")
    session.add_all([lost, found, job])
    await session.commit()
    client = AsyncMock(spec=AIClient)
    client.calculate_match.return_value = {
        "imageScore": 0,
        "textScore": 90,
        "locationScore": 100,
        "timeScore": 90,
        "totalScore": 92,
        "imageAvailable": False,
        "degraded": False,
        "scoreSource": "TEXT_MODEL_RULES",
    }

    typed_client = cast(AIClient, client)
    await execute_durable_job(session, job, ai_client=typed_client)
    await session.commit()
    await execute_durable_job(session, job, ai_client=typed_client)
    await session.commit()

    match_count = await session.scalar(select(func.count()).select_from(MatchResult))
    notice_count = await session.scalar(select(func.count()).select_from(Notification))
    assert match_count == 1
    assert notice_count == 1
