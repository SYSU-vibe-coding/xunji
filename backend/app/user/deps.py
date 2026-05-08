from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.user.service import UserService


async def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(session)
