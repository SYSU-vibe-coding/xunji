"""Match service.

The cheap CRUD methods stay here, but the meat of this module is
``trigger_match``: a fan-out that scores one freshly-created lost/found
item against all live counterparts. Scoring delegates to ai-service when
reachable, and falls back to ``app.match.scoring`` (rule-based) on any
failure — see ``docs/architecture/matching-rules.md §2`` for the formula.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_client import AIClient
from app.db.session import async_session_factory
from app.db.ulid import generate_ulid
from app.item.service import ItemService
from app.match.models import MatchResult
from app.match.repository import MatchResultRepository
from app.match.scoring import rule_based_score

# Score thresholds documented in matching-rules.md §3
MATCH_THRESHOLD = 70.0
HIGH_PRIORITY_THRESHOLD = 90.0
# Avoid blasting ai-service when many candidates exist.
MAX_CONCURRENCY = 8


class MatchService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = MatchResultRepository(session)

    async def get_by_id(self, match_id: str) -> MatchResult | None:
        return await self._repo.get_by_id(match_id)

    async def mark_claimed(self, match: MatchResult) -> None:
        match.match_status = "CLAIMED"
        await self._repo.update(match)


# ---------------------------------------------------------------------------
# Background entrypoint (called from item.service via FastAPI BackgroundTasks)
# ---------------------------------------------------------------------------


async def trigger_match(
    biz_type: str,
    item_id: str,
    *,
    ai_client: AIClient | None = None,
) -> int:
    """Score a freshly-created item against all live counterparts.

    Returns the number of ``match_results`` rows actually inserted/updated
    (≥ MATCH_THRESHOLD). Always uses its own DB session so it can outlive
    the originating HTTP request.
    """
    logger.info(f"[match] trigger_match biz_type={biz_type} item_id={item_id}")

    owns_client = ai_client is None
    client = ai_client or AIClient()
    try:
        async with async_session_factory() as session:
            count = await _run(session, biz_type, item_id, client)
        return count
    finally:
        if owns_client:
            await client.aclose()


async def _run(
    session: AsyncSession,
    biz_type: str,
    item_id: str,
    client: AIClient,
) -> int:
    item_svc = ItemService(session)
    repo = MatchResultRepository(session)

    pairs: list[tuple[str, str, dict[str, Any] | None, dict[str, Any] | None]] = []

    if biz_type == "LOST":
        source = await item_svc.get_lost_match_payload_internal(item_id)
        if source is None:
            logger.warning(f"[match] lost item {item_id} not found, skip")
            return 0
        for found_cand in await item_svc.list_active_found_items_internal():
            cand_payload = await item_svc.get_found_match_payload_internal(found_cand.id)
            pairs.append((item_id, found_cand.id, source, cand_payload))
    elif biz_type == "FOUND":
        source = await item_svc.get_found_match_payload_internal(item_id)
        if source is None:
            logger.warning(f"[match] found item {item_id} not found, skip")
            return 0
        for lost_cand in await item_svc.list_active_lost_items_internal():
            cand_payload = await item_svc.get_lost_match_payload_internal(lost_cand.id)
            pairs.append((lost_cand.id, item_id, cand_payload, source))
    else:
        logger.warning(f"[match] unknown biz_type {biz_type}, skip")
        return 0

    if not pairs:
        return 0

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def score_one(
        pair: tuple[str, str, dict[str, Any] | None, dict[str, Any] | None],
    ) -> tuple[str, str, dict[str, Any]] | None:
        lost_id, found_id, lost_payload, found_payload = pair
        if lost_payload is None or found_payload is None:
            return None
        async with semaphore:
            scores = await client.calculate_match(lost=lost_payload, found=found_payload)
        if scores is None:
            scores = rule_based_score(lost_payload, found_payload)
        return lost_id, found_id, scores

    results = await asyncio.gather(*(score_one(p) for p in pairs))

    written = 0
    high_priority_pairs: list[tuple[str, str, float]] = []
    for entry in results:
        if entry is None:
            continue
        lost_id, found_id, scores = entry
        total = float(scores.get("totalScore", 0))
        if total < MATCH_THRESHOLD:
            continue
        match = await _upsert_match(repo, lost_id, found_id, scores)
        written += 1
        if total >= HIGH_PRIORITY_THRESHOLD:
            high_priority_pairs.append((match.id, found_id, total))

    if written:
        await session.commit()

    # High-priority notifications run *after* match commit. They depend on
    # external lookups (item owner, category) which we keep behind ItemService
    # to respect the cross-module rules.
    if high_priority_pairs:
        await _push_high_priority_notices(session, item_svc, high_priority_pairs)

    return written


async def _push_high_priority_notices(
    session: AsyncSession,
    item_svc: ItemService,
    pairs: list[tuple[str, str, float]],
) -> None:
    """For matches ≥90 on CERT items, notify the lost-item owner with HIGH priority.

    See matching-rules.md §3. We import NotificationService lazily to avoid
    circular imports (notification module is unrelated at module-load time).
    """
    from app.notification.service import NotificationService

    notify_svc = NotificationService(session)
    pushed = 0
    for match_id, found_id, total in pairs:
        try:
            found_item = await item_svc.get_found_item_internal(found_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"[match] high-priority lookup failed: {exc}")
            continue
        if found_item.category != "CERT":
            continue
        match = await MatchResultRepository(session).get_by_id(match_id)
        if match is None:
            continue
        try:
            lost_item = await item_svc.get_lost_item_internal(match.lost_item_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"[match] high-priority lost lookup failed: {exc}")
            continue
        await notify_svc.create_notice(
            user_id=lost_item.user_id,
            notice_type="MATCH_RECOMMEND",
            title=f"高匹配度提示 (评分 {total:.0f})",
            content=f"系统发现一条高度匹配的招领: {found_item.item_name}",
            related_type="MATCH",
            related_id=match_id,
            priority="HIGH",
        )
        pushed += 1
    if pushed:
        await session.commit()


async def _upsert_match(
    repo: MatchResultRepository,
    lost_id: str,
    found_id: str,
    scores: dict[str, Any],
) -> MatchResult:
    existing = await repo.get_by_pair(lost_id, found_id)
    if existing is None:
        match = MatchResult(
            id=generate_ulid(),
            lost_item_id=lost_id,
            found_item_id=found_id,
            image_score=Decimal(str(scores.get("imageScore", 0))),
            text_score=Decimal(str(scores.get("textScore", 0))),
            location_score=Decimal(str(scores.get("locationScore", 0))),
            time_score=Decimal(str(scores.get("timeScore", 0))),
            total_score=Decimal(str(scores.get("totalScore", 0))),
            match_status="NEW",
        )
        await repo.create(match)
        return match
    existing.image_score = Decimal(str(scores.get("imageScore", 0)))
    existing.text_score = Decimal(str(scores.get("textScore", 0)))
    existing.location_score = Decimal(str(scores.get("locationScore", 0)))
    existing.time_score = Decimal(str(scores.get("timeScore", 0)))
    existing.total_score = Decimal(str(scores.get("totalScore", 0)))
    await repo.update(existing)
    return existing
