from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.job.models import DurableJob


class DurableJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def next_biz_version(self, biz_type: str, biz_id: str) -> int:
        result = await self._session.execute(
            select(func.max(DurableJob.biz_version)).where(
                DurableJob.biz_type == biz_type,
                DurableJob.biz_id == biz_id,
            )
        )
        current = result.scalar_one_or_none()
        return (current or 0) + 1

    async def create_batch(self, jobs: list[DurableJob]) -> None:
        self._session.add_all(jobs)
        await self._session.flush()

    async def claim_next(
        self,
        *,
        now: datetime,
        stale_after: timedelta,
    ) -> DurableJob | None:
        stale_before = now - stale_after
        result = await self._session.execute(
            select(DurableJob)
            .where(
                or_(
                    (
                        (DurableJob.status == "PENDING")
                        & (DurableJob.run_after <= now)
                    ),
                    (
                        (DurableJob.status == "RUNNING")
                        & (DurableJob.locked_at <= stale_before)
                    ),
                )
            )
            .order_by(DurableJob.run_after.asc(), DurableJob.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return None
        job.status = "RUNNING"
        job.attempts += 1
        job.locked_at = now
        job.updated_at = now
        await self._session.flush()
        return job

    async def get_for_update(self, job_id: str) -> DurableJob | None:
        result = await self._session.execute(
            select(DurableJob).where(DurableJob.id == job_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def has_newer_biz_version(self, job: DurableJob) -> bool:
        result = await self._session.execute(
            select(DurableJob.id)
            .where(
                DurableJob.job_type == job.job_type,
                DurableJob.biz_type == job.biz_type,
                DurableJob.biz_id == job.biz_id,
                DurableJob.biz_version > job.biz_version,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def release_running(self, job_id: str, attempts: int, *, now: datetime) -> None:
        await self._session.execute(
            update(DurableJob)
            .where(
                DurableJob.id == job_id,
                DurableJob.status == "RUNNING",
                DurableJob.attempts == attempts,
            )
            .values(status="PENDING", run_after=now, locked_at=None, updated_at=now)
        )

    async def cancel_pending_for_items(
        self, *, lost_item_ids: list[str], found_item_ids: list[str], now: datetime
    ) -> int:
        item_conditions = []
        if lost_item_ids:
            item_conditions.append(
                and_(DurableJob.biz_type == "LOST", DurableJob.biz_id.in_(lost_item_ids))
            )
        if found_item_ids:
            item_conditions.append(
                and_(DurableJob.biz_type == "FOUND", DurableJob.biz_id.in_(found_item_ids))
            )
        if not item_conditions:
            return 0
        result = await self._session.execute(
            update(DurableJob)
            .where(DurableJob.status == "PENDING", or_(*item_conditions))
            .values(
                status="FAILED",
                locked_at=None,
                last_error="cancelled: publisher account cancelled",
                updated_at=now,
            )
        )
        return int(getattr(result, "rowcount", 0))
