from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.notification.service import NotificationService


async def get_notification_service(
    session: AsyncSession = Depends(get_session),
) -> NotificationService:
    return NotificationService(session)
