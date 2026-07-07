from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.service import AdminService
from app.db.session import get_session


async def get_admin_service(session: AsyncSession = Depends(get_session)) -> AdminService:
    return AdminService(session)
