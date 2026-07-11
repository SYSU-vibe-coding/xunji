from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.ai_client import AIClient
from app.core.config import settings
from app.db.session import async_session_factory
from app.job.models import DurableJob
from app.job.repository import DurableJobRepository
from app.job.service import execute_durable_job


class DurableJobRunner:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
        ai_client_factory: Callable[[], AIClient] = AIClient,
    ) -> None:
        self._session_factory = session_factory
        self._ai_client_factory = ai_client_factory
        self._task: asyncio.Task[None] | None = None
        self._wake = asyncio.Event()

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name="durable-job-runner")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    def wake(self) -> None:
        self._wake.set()

    async def run_once(self) -> bool:
        job = await self._claim_next()
        if job is None:
            return False
        try:
            await self._execute(job)
        except asyncio.CancelledError:
            await self._release(job)
            raise
        except Exception as exc:
            await self._reschedule(job, exc)
        return True

    async def _loop(self) -> None:
        logger.info(
            "[durable-job] runner started poll={}s max_attempts={}",
            settings.DURABLE_JOB_POLL_SECONDS,
            settings.DURABLE_JOB_MAX_ATTEMPTS,
        )
        while True:
            try:
                self._wake.clear()
                if await self.run_once():
                    continue
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(
                        self._wake.wait(), timeout=settings.DURABLE_JOB_POLL_SECONDS
                    )
            except asyncio.CancelledError:
                logger.info("[durable-job] runner stopped")
                raise
            except Exception as exc:  # pragma: no cover - loop-level defense
                logger.exception("[durable-job] polling failed: {}", exc)
                await asyncio.sleep(settings.DURABLE_JOB_POLL_SECONDS)

    async def _claim_next(self) -> DurableJob | None:
        now = _utc_now()
        async with self._session_factory() as session:
            job = await DurableJobRepository(session).claim_next(
                now=now,
                stale_after=timedelta(seconds=settings.DURABLE_JOB_LOCK_TIMEOUT_SECONDS),
            )
            if job is None:
                await session.rollback()
                return None
            await session.commit()
            session.expunge(job)
            logger.info(
                "[durable-job] claimed job_id={} job_type={} request={}/{} version={} attempt={}",
                job.id,
                job.job_type,
                job.biz_type,
                job.biz_id,
                job.biz_version,
                job.attempts,
            )
            return job

    async def _execute(self, claimed: DurableJob) -> None:
        client = self._ai_client_factory()
        try:
            async with self._session_factory() as session:
                job = await DurableJobRepository(session).get_for_update(claimed.id)
                if job is None or job.status != "RUNNING" or job.attempts != claimed.attempts:
                    await session.rollback()
                    return
                await execute_durable_job(session, job, ai_client=client)
                job.status = "COMPLETED"
                job.locked_at = None
                job.last_error = None
                job.updated_at = _utc_now()
                await session.commit()
            logger.info(
                "[durable-job] completed job_id={} job_type={} request={}/{}",
                claimed.id,
                claimed.job_type,
                claimed.biz_type,
                claimed.biz_id,
            )
        finally:
            await client.aclose()

    async def _reschedule(self, claimed: DurableJob, exc: Exception) -> None:
        now = _utc_now()
        async with self._session_factory() as session:
            job = await DurableJobRepository(session).get_for_update(claimed.id)
            if job is None or job.status != "RUNNING" or job.attempts != claimed.attempts:
                await session.rollback()
                return
            job.last_error = str(exc)[:2000]
            job.locked_at = None
            job.updated_at = now
            if job.attempts >= settings.DURABLE_JOB_MAX_ATTEMPTS:
                job.status = "FAILED"
            else:
                delay = settings.DURABLE_JOB_RETRY_BASE_SECONDS * (2 ** (job.attempts - 1))
                job.status = "PENDING"
                job.run_after = now + timedelta(seconds=delay)
            await session.commit()
            logger.warning(
                "[durable-job] failed job_id={} job_type={} request={}/{} "
                "attempt={} status={} error={}",
                job.id,
                job.job_type,
                job.biz_type,
                job.biz_id,
                job.attempts,
                job.status,
                job.last_error,
            )

    async def _release(self, claimed: DurableJob) -> None:
        async with self._session_factory() as session:
            await DurableJobRepository(session).release_running(
                claimed.id, claimed.attempts, now=_utc_now()
            )
            await session.commit()


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


_runner: DurableJobRunner | None = None


def get_durable_job_runner() -> DurableJobRunner:
    global _runner
    if _runner is None:
        _runner = DurableJobRunner()
    return _runner


def nudge_durable_job_runner() -> None:
    """FastAPI BackgroundTasks hint; durability remains in the database."""
    get_durable_job_runner().wake()
