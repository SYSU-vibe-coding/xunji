from sqlalchemy import and_, select
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

    async def get_by_pair(
        self, lost_item_id: str, found_item_id: str
    ) -> MatchResult | None:
        stmt = select(MatchResult).where(
            and_(
                MatchResult.lost_item_id == lost_item_id,
                MatchResult.found_item_id == found_item_id,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, match: MatchResult) -> MatchResult:
        self._session.add(match)
        await self._session.flush()
        return match

    async def update(self, match: MatchResult) -> MatchResult:
        await self._session.merge(match)
        await self._session.flush()
        return match
