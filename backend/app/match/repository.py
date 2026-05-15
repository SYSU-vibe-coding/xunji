from sqlalchemy import select
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

    async def update(self, match: MatchResult) -> MatchResult:
        await self._session.merge(match)
        await self._session.flush()
        return match
