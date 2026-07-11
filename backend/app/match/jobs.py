"""Admin-controllable match job runner.

A single ``MatchJobRunner`` instance is attached to the FastAPI app via
lifespan. It runs an asyncio loop that periodically scores all live
``SEARCHING`` lost items against all live ``PENDING`` found items. The
interval is configurable via env (``MATCH_AUTO_INTERVAL_MINUTES``) and can
be tuned at runtime through ``set_interval``. An admin can also trigger a
one-off full run via ``trigger_now``.

Status (``get_status``) is safe to read concurrently from request handlers
- all mutable fields are guarded by an asyncio.Lock and reads snapshot the
values.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timedelta
from typing import Any

from loguru import logger

from app.common.utils import now_beijing
from app.core.ai_client import AIClient
from app.core.config import settings
from app.db.session import async_session_factory
from app.db.ulid import generate_ulid
from app.item.service import ItemService
from app.match.repository import MatchResultRepository
from app.match.scoring import rule_based_score
from app.match.service import _persist_scored_match, _push_match_notices


class MatchJobRunner:
    """Background match scheduler with progress reporting."""

    def __init__(self) -> None:
        self._interval_minutes: int = settings.MATCH_AUTO_INTERVAL_MINUTES
        self._max_concurrency: int = settings.MATCH_JOB_MAX_CONCURRENCY
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        # Keep references to fire-and-forget run tasks so the GC doesn't
        # cancel them mid-flight. Cleared in _run_job's finally block.
        self._run_tasks: set[asyncio.Task[None]] = set()

        # Status snapshot, updated under _lock.
        self._status: str = "idle"  # idle | running | stopping
        self._total_pairs: int = 0
        self._processed_pairs: int = 0
        self._written_matches: int = 0
        self._last_run_started_at: datetime | None = None
        self._last_run_finished_at: datetime | None = None
        self._last_run_written: int = 0
        self._last_error: str | None = None
        self._current_job_id: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._loop(), name="match-job-runner")

    async def stop(self) -> None:
        async with self._lock:
            self._status = "stopping"
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task
            self._task = None
        async with self._lock:
            self._status = "idle"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def set_interval(self, minutes: int) -> None:
        """Update the auto-trigger interval. 0 disables the auto loop."""
        if minutes < 0:
            raise ValueError("interval minutes must be >= 0")
        async with self._lock:
            self._interval_minutes = minutes
        logger.info(f"[match-job] interval updated to {minutes} minutes")

    async def trigger_now(self) -> str:
        """Kick off a full match run immediately. Returns the job id.

        If a run is already in progress, returns the existing job id
        instead of starting a duplicate.
        """
        async with self._lock:
            if self._status == "running":
                return self._current_job_id or ""
            job_id = generate_ulid()
            self._current_job_id = job_id
            self._status = "running"
            self._total_pairs = 0
            self._processed_pairs = 0
            self._written_matches = 0
            self._last_error = None
        task = asyncio.create_task(self._run_job(job_id), name=f"match-job-{job_id}")
        self._run_tasks.add(task)
        task.add_done_callback(self._run_tasks.discard)
        return job_id

    async def get_status(self) -> dict[str, Any]:
        async with self._lock:
            interval = self._interval_minutes
            status = self._status
            total = self._total_pairs
            processed = self._processed_pairs
            written = self._written_matches
            last_started = self._last_run_started_at
            last_finished = self._last_run_finished_at
            last_written = self._last_run_written
            last_error = self._last_error
            job_id = self._current_job_id

        next_run: datetime | None = None
        if interval > 0 and status != "running" and last_finished is not None:
            next_run = last_finished + timedelta(minutes=interval)

        return {
            "status": status,
            "intervalMinutes": interval,
            "currentJobId": job_id if status == "running" else None,
            "totalPairs": total,
            "processedPairs": processed,
            "writtenMatches": written,
            "lastRunStartedAt": _format_dt(last_started),
            "lastRunFinishedAt": _format_dt(last_finished),
            "lastRunWrittenMatches": last_written,
            "lastError": last_error,
            "nextRunAt": _format_dt(next_run),
        }

    # ------------------------------------------------------------------
    # Internal loop / job execution
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        logger.info(f"[match-job] loop started, interval={self._interval_minutes}m")
        while True:
            try:
                interval = await self._current_interval()
                if interval > 0:
                    await self._run_job(job_id="auto")
                    # Re-read interval in case it changed during the run.
                    interval = await self._current_interval()
                    await asyncio.sleep(interval * 60)
                else:
                    # Auto disabled. Sleep a bit and re-check so admins can
                    # re-enable at runtime without restarting the process.
                    await asyncio.sleep(30)
            except asyncio.CancelledError:
                logger.info("[match-job] loop cancelled")
                raise
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("[match-job] loop error: {}", exc)
                await asyncio.sleep(60)

    async def _current_interval(self) -> int:
        async with self._lock:
            return self._interval_minutes

    async def _run_job(self, job_id: str) -> None:
        logger.info(f"[match-job] run started job_id={job_id}")
        async with self._lock:
            self._last_run_started_at = now_beijing()
            self._status = "running"
            self._current_job_id = job_id
            self._total_pairs = 0
            self._processed_pairs = 0
            self._written_matches = 0
            self._last_error = None

        try:
            written = await self._score_all_pairs()
            await self._write_run_log(job_id, written, error=None)
            async with self._lock:
                self._last_run_finished_at = now_beijing()
                self._last_run_written = written
                if self._status != "stopping":
                    self._status = "idle"
                self._current_job_id = None
            logger.info(f"[match-job] run finished job_id={job_id} written={written}")
        except asyncio.CancelledError:
            async with self._lock:
                self._last_run_finished_at = now_beijing()
                if self._status != "stopping":
                    self._status = "idle"
                self._current_job_id = None
            raise
        except Exception as exc:
            logger.exception("[match-job] run failed: {}", exc)
            await self._write_run_log(job_id, written=0, error=str(exc))
            async with self._lock:
                self._last_error = str(exc)
                self._last_run_finished_at = now_beijing()
                if self._status != "stopping":
                    self._status = "idle"
                self._current_job_id = None

    async def _write_run_log(self, job_id: str, written: int, error: str | None) -> None:
        """Persist a system operation log for each match run.

        Uses its own session so it works even if the scoring session was
        rolled back. Operator is recorded as SYSTEM/ADMIN since the job is
        triggered by an admin (manual) or the scheduler (auto).
        """
        from app.operation_log.service import OperationLogService

        if error:
            detail = f"匹配任务失败: {error[:200]}"
        else:
            detail = f"匹配任务完成, 写入 {written} 条匹配记录 (job={job_id[:8]})"
        try:
            async with async_session_factory() as session:
                log_svc = OperationLogService(session)
                await log_svc.create_log(
                    operator_id="SYSTEM",
                    operator_role="ADMIN",
                    biz_type="MATCH",
                    biz_id=job_id,
                    action="RUN",
                    detail=detail,
                )
                await session.commit()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"[match-job] failed to write run log: {exc}")

    async def _score_all_pairs(self) -> int:
        """Score every active lost against every active found, upsert matches."""
        async with async_session_factory() as session:
            item_svc = ItemService(session)
            repo = MatchResultRepository(session)

            losts = await item_svc.list_active_lost_items_internal()
            founds = await item_svc.list_active_found_items_internal()

            # Materialize payloads up-front so the scoring loop is cheap.
            lost_payloads: dict[str, dict[str, Any] | None] = {}
            for lost in losts:
                lost_payloads[lost.id] = await item_svc.get_lost_match_payload_internal(lost.id)
            found_payloads: dict[str, dict[str, Any] | None] = {}
            for found in founds:
                found_payloads[found.id] = await item_svc.get_found_match_payload_internal(found.id)

            pairs: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []
            for lost in losts:
                lp = lost_payloads.get(lost.id)
                if lp is None:
                    continue
                for found in founds:
                    if found.user_id == lost.user_id:
                        continue
                    fp = found_payloads.get(found.id)
                    if fp is None:
                        continue
                    pairs.append((lost.id, found.id, lp, fp))

            async with self._lock:
                self._total_pairs = len(pairs)

            if not pairs:
                await session.commit()
                return 0

            semaphore = asyncio.Semaphore(self._max_concurrency)
            ai_client = AIClient()
            written = 0
            new_matches: list[tuple[str, str, str, float]] = []
            try:
                # Process in batches so progress updates are visible.
                batch_size = max(1, self._max_concurrency)
                for start in range(0, len(pairs), batch_size):
                    batch = pairs[start : start + batch_size]

                    async def score_one(
                        pair: tuple[str, str, dict[str, Any], dict[str, Any]],
                    ) -> tuple[str, str, dict[str, Any]] | None:
                        lost_id, found_id, lp, fp = pair
                        async with semaphore:
                            scores = await ai_client.calculate_match(lost=lp, found=fp)
                        if scores is None:
                            scores = rule_based_score(lp, fp)
                        return lost_id, found_id, scores

                    results = await asyncio.gather(
                        *(score_one(p) for p in batch),
                        return_exceptions=True,
                    )

                    for entry in results:
                        if isinstance(entry, BaseException):
                            logger.warning(f"[match-job] pair scoring failed: {entry}")
                            continue
                        if entry is None:
                            continue
                        lost_id, found_id, scores = entry
                        total = float(scores.get("totalScore", 0))
                        match_obj, should_notify = await _persist_scored_match(
                            session,
                            item_svc,
                            repo,
                            lost_id,
                            found_id,
                            scores,
                        )
                        if match_obj is None:
                            continue
                        written += 1
                        if should_notify:
                            new_matches.append((match_obj.id, lost_id, found_id, total))

                    # Push notifications for newly created matches.
                    if new_matches:
                        await _push_match_notices(session, item_svc, new_matches)
                        new_matches.clear()
                    await session.commit()

                    async with self._lock:
                        self._processed_pairs = min(start + len(batch), len(pairs))
                        self._written_matches = written
            finally:
                await ai_client.aclose()

            async with self._lock:
                self._processed_pairs = len(pairs)
                self._written_matches = written
            return written


def _format_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# Module-level singleton, attached to the FastAPI app in main.lifespan.
_runner: MatchJobRunner | None = None


def get_runner() -> MatchJobRunner:
    global _runner
    if _runner is None:
        _runner = MatchJobRunner()
    return _runner
