from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.claim.service import ClaimService
from app.core.ai_client import AIClient
from app.db.session import get_session


async def get_claim_service(
    request: Request, session: AsyncSession = Depends(get_session)
) -> ClaimService:
    ai_client: AIClient | None = getattr(request.app.state, "ai_client", None)
    return ClaimService(session, ai_client=ai_client)
