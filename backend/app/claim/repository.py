from datetime import datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.claim.models import ClaimAnswer, ClaimRequest, HandoverRecord
from app.item.models import FoundItem

ACTIVE_CLAIM_STATUSES = {
    "PENDING",
    "ANSWER_PASSED",
    "PROOF_PENDING",
    "APPROVED",
    "APPEALING",
}


class ClaimRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, claim: ClaimRequest) -> ClaimRequest:
        self._session.add(claim)
        await self._session.flush()
        return claim

    async def get_by_id(self, claim_id: str) -> ClaimRequest | None:
        result = await self._session.execute(
            select(ClaimRequest).where(ClaimRequest.id == claim_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, claim_id: str) -> ClaimRequest | None:
        result = await self._session.execute(
            select(ClaimRequest).where(ClaimRequest.id == claim_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_latest_by_match_id(self, match_id: str) -> ClaimRequest | None:
        result = await self._session.execute(
            select(ClaimRequest)
            .where(ClaimRequest.match_id == match_id)
            .order_by(ClaimRequest.updated_at.desc(), ClaimRequest.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def has_active_claim(
        self, found_item_id: str, *, exclude_claim_id: str | None = None
    ) -> bool:
        stmt = select(ClaimRequest).where(
            ClaimRequest.found_item_id == found_item_id,
            ClaimRequest.review_status.in_(ACTIVE_CLAIM_STATUSES),
        )
        if exclude_claim_id is not None:
            stmt = stmt.where(ClaimRequest.id != exclude_claim_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_active_for_update(self, found_item_id: str) -> list[ClaimRequest]:
        result = await self._session.execute(
            select(ClaimRequest)
            .where(
                ClaimRequest.found_item_id == found_item_id,
                ClaimRequest.review_status.in_(ACTIVE_CLAIM_STATUSES),
            )
            .with_for_update()
        )
        return list(result.scalars().all())

    async def list_active_ids_by_lost_item(self, lost_item_id: str) -> list[str]:
        from app.match.models import MatchResult

        result = await self._session.execute(
            select(ClaimRequest.id)
            .join(MatchResult, MatchResult.id == ClaimRequest.match_id)
            .where(
                MatchResult.lost_item_id == lost_item_id,
                ClaimRequest.review_status.in_(ACTIVE_CLAIM_STATUSES),
            )
            .order_by(ClaimRequest.id)
        )
        return list(result.scalars().all())

    async def has_active_by_lost_item(self, lost_item_id: str) -> bool:
        from app.match.models import MatchResult

        result = await self._session.execute(
            select(ClaimRequest.id)
            .join(MatchResult, MatchResult.id == ClaimRequest.match_id)
            .where(
                MatchResult.lost_item_id == lost_item_id,
                ClaimRequest.review_status.in_(ACTIVE_CLAIM_STATUSES),
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def has_active_for_user(self, user_id: str) -> bool:
        result = await self._session.execute(
            select(ClaimRequest.id)
            .join(FoundItem, FoundItem.id == ClaimRequest.found_item_id)
            .where(
                or_(ClaimRequest.claimant_id == user_id, FoundItem.user_id == user_id),
                ClaimRequest.review_status.in_(ACTIVE_CLAIM_STATUSES),
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def verification_failure_stats(
        self, *, claimant_id: str, found_item_id: str, since: datetime, failure_reason: str
    ) -> tuple[int, datetime | None]:
        result = await self._session.execute(
            select(func.count(), func.max(ClaimRequest.claimed_at)).where(
                ClaimRequest.claimant_id == claimant_id,
                ClaimRequest.found_item_id == found_item_id,
                ClaimRequest.review_status == "REJECTED",
                ClaimRequest.reject_reason == failure_reason,
                ClaimRequest.claimed_at >= since,
            )
        )
        count, latest = result.one()
        return int(count or 0), latest

    async def list_for_admin(
        self, *, review_status: str | None, offset: int, limit: int
    ) -> tuple[list[ClaimRequest], int]:
        stmt = select(ClaimRequest)
        count_stmt = select(func.count()).select_from(ClaimRequest)
        if review_status is not None:
            stmt = stmt.where(ClaimRequest.review_status == review_status)
            count_stmt = count_stmt.where(ClaimRequest.review_status == review_status)
        stmt = (
            stmt.order_by(ClaimRequest.updated_at.desc(), ClaimRequest.id.desc())
            .offset(offset)
            .limit(limit)
        )
        total_result = await self._session.execute(count_stmt)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total_result.scalar() or 0

    async def list_by_claimant(
        self,
        *,
        claimant_id: str,
        statuses: set[str] | None,
        offset: int,
        limit: int,
    ) -> tuple[list[ClaimRequest], int]:
        stmt = select(ClaimRequest).where(ClaimRequest.claimant_id == claimant_id)
        count_stmt = (
            select(func.count())
            .select_from(ClaimRequest)
            .where(ClaimRequest.claimant_id == claimant_id)
        )
        if statuses:
            stmt = stmt.where(ClaimRequest.review_status.in_(statuses))
            count_stmt = count_stmt.where(ClaimRequest.review_status.in_(statuses))
        stmt = stmt.order_by(ClaimRequest.updated_at.desc()).offset(offset).limit(limit)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_by_found_item_ids(
        self,
        *,
        found_item_ids: list[str],
        statuses: set[str] | None,
        offset: int,
        limit: int,
    ) -> tuple[list[ClaimRequest], int]:
        if not found_item_ids:
            return [], 0
        stmt = select(ClaimRequest).where(ClaimRequest.found_item_id.in_(found_item_ids))
        count_stmt = (
            select(func.count())
            .select_from(ClaimRequest)
            .where(ClaimRequest.found_item_id.in_(found_item_ids))
        )
        if statuses:
            stmt = stmt.where(ClaimRequest.review_status.in_(statuses))
            count_stmt = count_stmt.where(ClaimRequest.review_status.in_(statuses))
        stmt = stmt.order_by(ClaimRequest.updated_at.desc()).offset(offset).limit(limit)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def update(self, claim: ClaimRequest) -> ClaimRequest:
        await self._session.merge(claim)
        await self._session.flush()
        return claim

    async def transition_status(
        self,
        *,
        claim_id: str,
        expected_status: str,
        new_status: str,
        reject_reason: str | None,
    ) -> bool:
        result = await self._session.execute(
            update(ClaimRequest)
            .where(
                ClaimRequest.id == claim_id,
                ClaimRequest.review_status == expected_status,
            )
            .values(
                review_status=new_status,
                reject_reason=reject_reason,
                updated_at=func.now(),
            )
        )
        return bool(getattr(result, "rowcount", 0))

    async def count_by_status(self, status: str) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(ClaimRequest)
            .where(ClaimRequest.review_status == status)
        )
        return result.scalar() or 0


class ClaimAnswerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_batch(self, answers: list[ClaimAnswer]) -> None:
        if not answers:
            return
        self._session.add_all(answers)
        await self._session.flush()

    async def get_by_claim_id(self, claim_id: str) -> list[ClaimAnswer]:
        result = await self._session.execute(
            select(ClaimAnswer).where(ClaimAnswer.claim_id == claim_id)
        )
        return list(result.scalars().all())


class HandoverRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, handover: HandoverRecord) -> HandoverRecord:
        self._session.add(handover)
        await self._session.flush()
        return handover

    async def get_by_claim_id(self, claim_id: str) -> HandoverRecord | None:
        result = await self._session.execute(
            select(HandoverRecord).where(HandoverRecord.claim_id == claim_id)
        )
        return result.scalar_one_or_none()

    async def get_by_claim_id_for_update(self, claim_id: str) -> HandoverRecord | None:
        result = await self._session.execute(
            select(HandoverRecord).where(HandoverRecord.claim_id == claim_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def update(self, handover: HandoverRecord) -> HandoverRecord:
        await self._session.merge(handover)
        await self._session.flush()
        return handover

    async def confirm_role(self, claim_id: str, role: str) -> HandoverRecord | None:
        values = {"owner_confirmed": 1} if role == "OWNER" else {"finder_confirmed": 1}
        await self._session.execute(
            update(HandoverRecord).where(HandoverRecord.claim_id == claim_id).values(**values)
        )
        result = await self._session.execute(
            select(HandoverRecord)
            .where(HandoverRecord.claim_id == claim_id)
            .execution_options(populate_existing=True)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_completed_item_times(self) -> list[tuple[datetime, datetime]]:
        result = await self._session.execute(
            select(FoundItem.created_at, HandoverRecord.completed_at)
            .select_from(HandoverRecord)
            .join(ClaimRequest, ClaimRequest.id == HandoverRecord.claim_id)
            .join(FoundItem, FoundItem.id == ClaimRequest.found_item_id)
            .where(HandoverRecord.completed_at.is_not(None))
        )
        return [
            (created_at, completed_at)
            for created_at, completed_at in result.all()
            if completed_at is not None
        ]
