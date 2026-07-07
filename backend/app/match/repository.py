from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.match.models import MatchResult


class MatchResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, match_id: str) -> MatchResult | None:
        result = await self._session.execute(select(MatchResult).where(MatchResult.id == match_id))
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
        from sqlalchemy import or_

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

    async def create(self, match: MatchResult) -> MatchResult:
        self._session.add(match)
        await self._session.flush()
        return match

    async def update(self, match: MatchResult) -> MatchResult:
        await self._session.merge(match)
        await self._session.flush()
        return match
