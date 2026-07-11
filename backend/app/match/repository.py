from decimal import Decimal
from typing import cast

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.item.models import FoundItem, LostItem
from app.match.models import MatchResult
from app.user.models import User


class MatchResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, match_id: str) -> MatchResult | None:
        result = await self._session.execute(select(MatchResult).where(MatchResult.id == match_id))
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, match_id: str) -> MatchResult | None:
        result = await self._session.execute(
            select(MatchResult).where(MatchResult.id == match_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_found_item_id(self, found_item_id: str) -> MatchResult | None:
        stmt = (
            select(MatchResult)
            .where(MatchResult.found_item_id == found_item_id)
            .order_by(MatchResult.total_score.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_pair(self, lost_item_id: str, found_item_id: str) -> MatchResult | None:
        stmt = select(MatchResult).where(
            and_(
                MatchResult.lost_item_id == lost_item_id,
                MatchResult.found_item_id == found_item_id,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_biz(
        self,
        *,
        biz_type: str,
        biz_id: str,
        min_score: Decimal,
        status: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[MatchResult], int]:
        conditions = [
            MatchResult.total_score >= min_score,
        ]
        if biz_type == "LOST":
            conditions.append(MatchResult.lost_item_id == biz_id)
        else:
            conditions.append(MatchResult.found_item_id == biz_id)
        if status is not None:
            conditions.append(MatchResult.match_status == status)

        stmt = (
            select(MatchResult)
            .where(*conditions)
            .order_by(MatchResult.total_score.desc(), MatchResult.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_stmt = select(func.count()).select_from(MatchResult).where(*conditions)

        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_by_user_items(
        self,
        *,
        lost_item_ids: list[str],
        found_item_ids: list[str],
        min_score: Decimal,
        status: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[MatchResult], int]:
        """List matches where the user owns either the lost or found item."""
        conditions = [MatchResult.total_score >= min_score]
        if status is not None:
            conditions.append(MatchResult.match_status == status)

        # Filter: user owns lost OR found item
        id_conditions = []
        if lost_item_ids:
            id_conditions.append(MatchResult.lost_item_id.in_(lost_item_ids))
        if found_item_ids:
            id_conditions.append(MatchResult.found_item_id.in_(found_item_ids))
        if not id_conditions:
            return [], 0
        conditions.append(or_(*id_conditions))

        stmt = (
            select(MatchResult)
            .where(*conditions)
            .order_by(MatchResult.total_score.desc(), MatchResult.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_stmt = select(func.count()).select_from(MatchResult).where(*conditions)

        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_by_user_id(
        self,
        *,
        user_id: str,
        min_score: Decimal,
        status: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[MatchResult], int]:
        conditions = [
            MatchResult.total_score >= min_score,
            or_(LostItem.user_id == user_id, FoundItem.user_id == user_id),
        ]
        if status is not None:
            conditions.append(MatchResult.match_status == status)
        base = (
            select(MatchResult)
            .join(LostItem, LostItem.id == MatchResult.lost_item_id)
            .join(FoundItem, FoundItem.id == MatchResult.found_item_id)
            .where(*conditions)
        )
        stmt = (
            base.order_by(MatchResult.total_score.desc(), MatchResult.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_stmt = (
            select(func.count())
            .select_from(MatchResult)
            .join(LostItem, LostItem.id == MatchResult.lost_item_id)
            .join(FoundItem, FoundItem.id == MatchResult.found_item_id)
            .where(*conditions)
        )
        total_result = await self._session.execute(count_stmt)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total_result.scalar() or 0

    async def expire_by_item(self, biz_type: str, item_id: str) -> int:
        item_column = (
            MatchResult.lost_item_id if biz_type == "LOST" else MatchResult.found_item_id
        )
        result = await self._session.execute(
            update(MatchResult)
            .where(
                item_column == item_id,
                MatchResult.match_status != "EXPIRED",
            )
            .values(match_status="EXPIRED")
        )
        return cast(int, getattr(result, "rowcount", 0))

    async def expire_by_id(self, match_id: str) -> bool:
        result = await self._session.execute(
            update(MatchResult)
            .where(
                MatchResult.id == match_id,
                MatchResult.match_status != "EXPIRED",
            )
            .values(match_status="EXPIRED")
        )
        return cast(int, getattr(result, "rowcount", 0)) == 1

    async def expire_by_pair(self, lost_item_id: str, found_item_id: str) -> bool:
        result = await self._session.execute(
            update(MatchResult)
            .where(
                MatchResult.lost_item_id == lost_item_id,
                MatchResult.found_item_id == found_item_id,
                MatchResult.match_status.in_({"NEW", "READ"}),
            )
            .values(match_status="EXPIRED")
        )
        return cast(int, getattr(result, "rowcount", 0)) == 1

    async def expire_by_items(
        self, *, lost_item_ids: list[str], found_item_ids: list[str]
    ) -> int:
        item_conditions = []
        if lost_item_ids:
            item_conditions.append(MatchResult.lost_item_id.in_(lost_item_ids))
        if found_item_ids:
            item_conditions.append(MatchResult.found_item_id.in_(found_item_ids))
        if not item_conditions:
            return 0
        result = await self._session.execute(
            update(MatchResult)
            .where(or_(*item_conditions), MatchResult.match_status != "EXPIRED")
            .values(match_status="EXPIRED")
        )
        return cast(int, getattr(result, "rowcount", 0))

    async def list_active_lost_owner_ids_for_found_items(
        self, found_item_ids: list[str], *, exclude_user_id: str
    ) -> list[str]:
        if not found_item_ids:
            return []
        result = await self._session.execute(
            select(LostItem.user_id)
            .select_from(MatchResult)
            .join(LostItem, LostItem.id == MatchResult.lost_item_id)
            .join(User, User.id == LostItem.user_id)
            .where(
                MatchResult.found_item_id.in_(found_item_ids),
                MatchResult.match_status != "EXPIRED",
                LostItem.user_id != exclude_user_id,
                User.status == "ACTIVE",
            )
            .distinct()
        )
        return list(result.scalars().all())

    async def mark_read_if_new(self, match_id: str) -> bool:
        result = await self._session.execute(
            update(MatchResult)
            .where(MatchResult.id == match_id, MatchResult.match_status == "NEW")
            .values(match_status="READ")
        )
        return cast(int, getattr(result, "rowcount", 0)) == 1

    async def create(self, match: MatchResult) -> MatchResult:
        self._session.add(match)
        await self._session.flush()
        return match

    async def create_or_get(self, match: MatchResult) -> tuple[MatchResult, bool]:
        try:
            async with self._session.begin_nested():
                await self.create(match)
            return match, True
        except IntegrityError:
            existing = await self.get_by_pair(match.lost_item_id, match.found_item_id)
            if existing is None:
                raise
            return existing, False

    async def update(self, match: MatchResult) -> MatchResult:
        await self._session.merge(match)
        await self._session.flush()
        return match
