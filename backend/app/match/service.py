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

from app.claim.repository import ClaimRequestRepository
from app.common.errors import BizError, ErrorCode
from app.common.pagination import PaginationParams, paginate
from app.common.utils import format_beijing
from app.core.ai_client import AIClient
from app.core.config import settings
from app.db.session import async_session_factory
from app.db.ulid import generate_ulid
from app.item.service import ItemService
from app.match.models import MatchResult
from app.match.repository import MatchResultRepository
from app.match.schemas import (
    MatchCounterpartSummary,
    MatchDetailResponse,
    MatchListItem,
    MatchListQuery,
    MatchRecalculateRequest,
    MatchRecalculateResponse,
)
from app.match.scoring import rule_based_score
from app.user.repository import UserRepository
from app.user.schemas import CurrentUser
from app.user.service import UserService

# Score thresholds documented in matching-rules.md §3
MATCH_THRESHOLD = 70.0
HIGH_PRIORITY_THRESHOLD = 90.0
# Avoid blasting ai-service when many candidates exist.
MAX_CONCURRENCY = 8


class MatchService:
    def __init__(self, session: AsyncSession, ai_client: AIClient | None = None) -> None:
        self._session = session
        self._repo = MatchResultRepository(session)
        self._item_svc = ItemService(session)
        self._claim_repo = ClaimRequestRepository(session)
        self._user_svc = UserService(session)
        self._ai_client = ai_client

    async def get_by_id(self, match_id: str) -> MatchResult | None:
        return await self._repo.get_by_id(match_id)

    async def get_by_id_for_update(self, match_id: str) -> MatchResult | None:
        return await self._repo.get_by_id_for_update(match_id)

    async def mark_claimed(self, match: MatchResult) -> None:
        match.match_status = "CLAIMED"
        await self._repo.update(match)

    async def release_claimed(self, match_id: str) -> None:
        match = await self._repo.get_by_id_for_update(match_id)
        if match is not None and match.match_status == "CLAIMED":
            match.match_status = "READ"
            await self._repo.update(match)

    async def expire_match(self, match_id: str) -> bool:
        return await self._repo.expire_by_id(match_id)

    async def expire_for_item(self, biz_type: str, item_id: str) -> int:
        return await self._repo.expire_by_item(biz_type, item_id)

    async def list_matches(
        self, query: MatchListQuery, current_user: CurrentUser
    ) -> dict[str, Any]:
        assert query.biz_type is not None and query.biz_id is not None
        await self._ensure_biz_owner(query.biz_type, query.biz_id, current_user)
        params = PaginationParams(pageNo=query.page_no, pageSize=query.page_size)
        matches, total = await self._repo.list_by_biz(
            biz_type=query.biz_type,
            biz_id=query.biz_id,
            min_score=Decimal(str(query.min_score)),
            status=query.status,
            offset=params.offset,
            limit=query.page_size,
        )
        items = [
            (
                await self._to_list_item(
                    match=match,
                    current_user=current_user,
                    source_biz_type=query.biz_type,
                )
            ).model_dump(by_alias=True)
            for match in matches
        ]
        return paginate(items, total, params)

    async def list_my_matches(
        self, query: MatchListQuery, current_user: CurrentUser
    ) -> dict[str, Any]:
        """List all matches across the current user's lost and found items."""
        params = PaginationParams(pageNo=query.page_no, pageSize=query.page_size)
        matches, total = await self._repo.list_by_user_id(
            user_id=current_user.id,
            min_score=Decimal(str(query.min_score)),
            status=query.status,
            offset=params.offset,
            limit=query.page_size,
        )
        items = []
        for match in matches:
            lost_item = await self._item_svc.get_lost_item_internal(match.lost_item_id)
            if lost_item and lost_item.user_id == current_user.id:
                source_biz_type = "LOST"
            else:
                source_biz_type = "FOUND"
            list_item = await self._to_list_item(
                match=match,
                current_user=current_user,
                source_biz_type=source_biz_type,
            )
            items.append(list_item.model_dump(by_alias=True))
        return paginate(items, total, params)

    async def get_match_detail(
        self, match_id: str, current_user: CurrentUser
    ) -> MatchDetailResponse:
        match = await self._get_match_or_raise(match_id)
        lost_item = await self._item_svc.get_lost_item_internal(match.lost_item_id)
        found_item = await self._item_svc.get_found_item_internal(match.found_item_id)
        if current_user.id not in {lost_item.user_id, found_item.user_id}:
            raise BizError(ErrorCode.FORBIDDEN)

        if match.match_status == "NEW" and await self._repo.mark_read_if_new(match.id):
            match.match_status = "READ"

        lost_detail = await self._item_svc.get_lost_item_detail(match.lost_item_id, current_user)
        found_detail = await self._item_svc.get_found_item_detail(match.found_item_id, current_user)
        viewer = await self._user_svc.get_user_internal(current_user.id)
        claim = await self._claim_repo.get_latest_by_match_id(match.id)
        can_claim = (
            viewer is not None
            and viewer.status == "ACTIVE"
            and viewer.credit_score >= 30
            and current_user.id == lost_item.user_id
            and found_item.user_id != current_user.id
            and found_item.status == "PENDING"
            and found_item.review_status == "APPROVED"
            and lost_item.status == "SEARCHING"
            and lost_item.review_status == "APPROVED"
            and match.match_status in {"NEW", "READ"}
            and not await self._claim_repo.has_active_claim(found_item.id)
        )
        list_item = await self._to_list_item(
            match=match,
            current_user=current_user,
            source_biz_type="LOST" if current_user.id == lost_item.user_id else "FOUND",
        )
        detail = MatchDetailResponse(
            **list_item.model_dump(),
            lost_item=lost_detail,
            found_item=found_detail,
            can_claim=can_claim,
            claim_id=claim.id if claim is not None else None,
            claim_status=claim.review_status if claim is not None else None,
        )
        await self._session.commit()
        return detail

    async def recalculate(
        self, req: MatchRecalculateRequest, current_user: CurrentUser
    ) -> MatchRecalculateResponse:
        await self._ensure_biz_owner(req.biz_type, req.biz_id, current_user, allow_admin=True)
        written = await trigger_match(
            req.biz_type,
            req.biz_id,
            ai_client=self._ai_client,
            max_candidates=settings.MATCH_RECALCULATE_MAX_CANDIDATES,
        )
        return MatchRecalculateResponse(matched_count=written)

    async def _get_match_or_raise(self, match_id: str) -> MatchResult:
        match = await self._repo.get_by_id(match_id)
        if match is None:
            raise BizError(ErrorCode.MATCH_NOT_FOUND)
        return match

    async def _ensure_biz_owner(
        self,
        biz_type: str,
        biz_id: str,
        current_user: CurrentUser,
        *,
        allow_admin: bool = False,
    ) -> None:
        if biz_type == "LOST":
            owner_id = (await self._item_svc.get_lost_item_internal(biz_id)).user_id
        else:
            owner_id = (await self._item_svc.get_found_item_internal(biz_id)).user_id
        if owner_id != current_user.id and not (allow_admin and current_user.role == "ADMIN"):
            raise BizError(ErrorCode.FORBIDDEN)

    async def _to_list_item(
        self,
        *,
        match: MatchResult,
        current_user: CurrentUser,
        source_biz_type: str,
    ) -> MatchListItem:
        counterpart = await self._counterpart_summary(match, current_user, source_biz_type)
        return MatchListItem(
            match_id=match.id,
            lost_item_id=match.lost_item_id,
            found_item_id=match.found_item_id,
            image_score=float(match.image_score),
            text_score=float(match.text_score),
            location_score=float(match.location_score),
            time_score=float(match.time_score),
            total_score=float(match.total_score),
            image_available=bool(match.image_available),
            degraded=bool(match.degraded),
            score_source=match.score_source,
            match_status=match.match_status,
            counterpart=counterpart,
            created_at=format_beijing(match.created_at),
        )

    async def _counterpart_summary(
        self, match: MatchResult, current_user: CurrentUser, source_biz_type: str
    ) -> MatchCounterpartSummary:
        if source_biz_type == "LOST":
            detail = await self._item_svc.get_found_item_detail(match.found_item_id, current_user)
            image_urls = detail.get("imageUrls", [])
            return MatchCounterpartSummary(
                id=detail["id"],
                item_name=detail["itemName"],
                category=detail["category"],
                cover_image_url=image_urls[0] if image_urls else None,
                location=detail["foundLocation"],
                time=detail["foundTime"],
            )
        detail = await self._item_svc.get_lost_item_detail(match.lost_item_id, current_user)
        return MatchCounterpartSummary(
            id=detail["id"],
            item_name=detail["itemName"],
            category=detail["category"],
            cover_image_url=detail.get("coverImageUrl"),
            location=detail["lostLocation"],
            time=detail["lostTimeStart"],
        )


# ---------------------------------------------------------------------------
# Standalone entrypoint used by synchronous manual recalculation.
# ---------------------------------------------------------------------------


async def trigger_match(
    biz_type: str,
    item_id: str,
    *,
    ai_client: AIClient | None = None,
    max_candidates: int | None = None,
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
            count = await run_match_in_session(
                session,
                biz_type,
                item_id,
                client,
                max_candidates=max_candidates,
            )
            await session.commit()
        return count
    finally:
        if owns_client:
            await client.aclose()


async def run_match_in_session(
    session: AsyncSession,
    biz_type: str,
    item_id: str,
    client: AIClient,
    *,
    max_candidates: int | None = None,
) -> int:
    item_svc = ItemService(session)
    repo = MatchResultRepository(session)

    pairs: list[tuple[str, str, dict[str, Any] | None, dict[str, Any] | None]] = []

    if biz_type == "LOST":
        source = await item_svc.get_lost_match_payload_internal(item_id)
        if source is None:
            logger.warning(f"[match] lost item {item_id} not found, skip")
            return 0
        lost_source_item = await item_svc.get_lost_item_internal(item_id)
        for found_cand in await item_svc.list_active_found_items_internal():
            if found_cand.user_id == lost_source_item.user_id:
                continue
            cand_payload = await item_svc.get_found_match_payload_internal(found_cand.id)
            pairs.append((item_id, found_cand.id, source, cand_payload))
    elif biz_type == "FOUND":
        source = await item_svc.get_found_match_payload_internal(item_id)
        if source is None:
            logger.warning(f"[match] found item {item_id} not found, skip")
            return 0
        found_source_item = await item_svc.get_found_item_internal(item_id)
        for lost_cand in await item_svc.list_active_lost_items_internal():
            if lost_cand.user_id == found_source_item.user_id:
                continue
            cand_payload = await item_svc.get_lost_match_payload_internal(lost_cand.id)
            pairs.append((lost_cand.id, item_id, cand_payload, source))
    else:
        logger.warning(f"[match] unknown biz_type {biz_type}, skip")
        return 0

    if not pairs:
        return 0
    if max_candidates is not None:
        pairs = pairs[:max_candidates]

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
    new_matches: list[tuple[str, str, str, float]] = []
    for entry in results:
        if entry is None:
            continue
        lost_id, found_id, scores = entry
        total = float(scores.get("totalScore", 0))
        match, should_notify = await _persist_scored_match(
            session,
            item_svc,
            repo,
            lost_id,
            found_id,
            scores,
        )
        if match is None:
            continue
        written += 1
        if should_notify:
            new_matches.append((match.id, lost_id, found_id, total))

    if new_matches:
        await _push_match_notices(session, item_svc, new_matches)

    return written


async def _persist_scored_match(
    session: AsyncSession,
    item_svc: ItemService,
    repo: MatchResultRepository,
    lost_id: str,
    found_id: str,
    scores: dict[str, Any],
) -> tuple[MatchResult | None, bool]:
    """Re-lock and validate a scored pair before changing its active match."""
    lost_item = await item_svc.get_lost_item_for_update_internal(lost_id)
    found_item = await item_svc.get_found_item_for_update_internal(found_id)
    user_repo = UserRepository(session)
    lost_owner = await user_repo.get_by_id(lost_item.user_id)
    found_owner = await user_repo.get_by_id(found_item.user_id)
    existing = await repo.get_by_pair(lost_id, found_id)
    # Scoring may finish after a user has claimed this pair. Only the claim
    # state machine may release or expire a CLAIMED match.
    if existing is not None and existing.match_status == "CLAIMED":
        return None, False
    valid_pair = (
        lost_item.status == "SEARCHING"
        and lost_item.review_status == "APPROVED"
        and found_item.status == "PENDING"
        and found_item.review_status == "APPROVED"
        and lost_item.user_id != found_item.user_id
        and lost_owner is not None
        and lost_owner.status == "ACTIVE"
        and found_owner is not None
        and found_owner.status == "ACTIVE"
    )
    if not valid_pair or float(scores.get("totalScore", 0)) < MATCH_THRESHOLD:
        await repo.expire_by_pair(lost_id, found_id)
        return None, False
    return await _upsert_match(repo, lost_id, found_id, scores)


async def _push_match_notices(
    session: AsyncSession,
    item_svc: ItemService,
    pairs: list[tuple[str, str, str, float]],
) -> None:
    """Notify subscribed lost-item owners for every newly active match."""
    from app.notification.service import NotificationService

    notify_svc = NotificationService(session)
    for match_id, lost_id, found_id, total in pairs:
        try:
            found_item = await item_svc.get_found_item_internal(found_id)
            lost_item = await item_svc.get_lost_item_internal(lost_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"[match] notice lookup failed: {exc}")
            continue
        if not lost_item.subscribe_match:
            continue
        priority = (
            "HIGH"
            if total >= HIGH_PRIORITY_THRESHOLD and found_item.category == "CERT"
            else "NORMAL"
        )
        await notify_svc.create_notice(
            user_id=lost_item.user_id,
            notice_type="MATCH_RECOMMEND",
            title=f"发现疑似匹配物品 (评分 {total:.0f})",
            content=f"您的失物「{lost_item.item_name}」可能与招领「{found_item.item_name}」匹配",
            related_type="MATCH",
            related_id=match_id,
            priority=priority,
        )


async def _upsert_match(
    repo: MatchResultRepository,
    lost_id: str,
    found_id: str,
    scores: dict[str, Any],
) -> tuple[MatchResult, bool]:
    existing = await repo.get_by_pair(lost_id, found_id)
    if existing is None:
        match = MatchResult(
            id=generate_ulid(),
            lost_item_id=lost_id,
            found_item_id=found_id,
            image_score=Decimal(
                str(scores.get("imageScore", 0) if scores.get("imageAvailable") is True else 0)
            ),
            text_score=Decimal(str(scores.get("textScore", 0))),
            location_score=Decimal(str(scores.get("locationScore", 0))),
            time_score=Decimal(str(scores.get("timeScore", 0))),
            total_score=Decimal(str(scores.get("totalScore", 0))),
            image_available=1 if scores.get("imageAvailable") is True else 0,
            degraded=0 if scores.get("degraded") is False else 1,
            score_source=str(scores.get("scoreSource", "RULE_BASED")),
            match_status="NEW",
        )
        return await repo.create_or_get(match)
    should_notify = existing.match_status == "EXPIRED"
    existing.image_score = Decimal(
        str(scores.get("imageScore", 0) if scores.get("imageAvailable") is True else 0)
    )
    existing.text_score = Decimal(str(scores.get("textScore", 0)))
    existing.location_score = Decimal(str(scores.get("locationScore", 0)))
    existing.time_score = Decimal(str(scores.get("timeScore", 0)))
    existing.total_score = Decimal(str(scores.get("totalScore", 0)))
    existing.image_available = 1 if scores.get("imageAvailable") is True else 0
    existing.degraded = 0 if scores.get("degraded") is False else 1
    existing.score_source = str(scores.get("scoreSource", "RULE_BASED"))
    if should_notify:
        existing.match_status = "NEW"
    await repo.update(existing)
    return existing, should_notify
