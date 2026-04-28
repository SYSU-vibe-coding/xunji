from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.credit.service import CreditService
from app.db.session import get_session


async def get_credit_service(session: AsyncSession = Depends(get_session)) -> CreditService:
    return CreditService(session)
