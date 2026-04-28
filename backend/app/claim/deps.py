from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.claim.service import ClaimService
from app.db.session import get_session


async def get_claim_service(session: AsyncSession = Depends(get_session)) -> ClaimService:
    return ClaimService(session)
