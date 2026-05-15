from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.match.models import MatchResult
from app.match.repository import MatchResultRepository


class MatchService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = MatchResultRepository(session)

    async def get_by_id(self, match_id: str) -> MatchResult | None:
        return await self._repo.get_by_id(match_id)

    async def mark_claimed(self, match: MatchResult) -> None:
        match.match_status = "CLAIMED"
        await self._repo.update(match)


async def trigger_match(biz_type: str, item_id: str) -> None:
    """
    Stub for match triggering. Will be implemented in the AI/match integration phase.

    See docs/architecture/matching-rules.md for scoring weights and thresholds.
    """
    logger.info(f"[match-stub] trigger_match called: biz_type={biz_type}, item_id={item_id}")
