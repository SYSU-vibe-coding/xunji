from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_client import AIClient
from app.db.session import get_session
from app.match.service import MatchService


def get_ai_client(request: Request) -> AIClient | None:
    return getattr(request.app.state, "ai_client", None)


async def get_match_service(
    session: AsyncSession = Depends(get_session),
    ai_client: AIClient | None = Depends(get_ai_client),
) -> MatchService:
    return MatchService(session, ai_client=ai_client)
