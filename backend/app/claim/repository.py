from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.claim.models import ClaimAnswer, ClaimRequest, HandoverRecord
from app.item.models import FoundItem

ACTIVE_CLAIM_STATUSES = {"PENDING", "ANSWER_PASSED", "PROOF_PENDING", "APPROVED", "APPEALING"}


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

    async def has_active_claim(self, found_item_id: str) -> bool:
        stmt = select(ClaimRequest).where(
            ClaimRequest.found_item_id == found_item_id,
            ClaimRequest.review_status.in_(ACTIVE_CLAIM_STATUSES),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

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

    async def update(self, handover: HandoverRecord) -> HandoverRecord:
        await self._session.merge(handover)
        await self._session.flush()
        return handover

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
