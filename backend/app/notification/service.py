from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import BizError, ErrorCode
from app.common.pagination import PaginationParams, paginate
from app.common.utils import format_beijing
from app.db.ulid import generate_ulid
from app.notification.models import Notification
from app.notification.repository import NotificationRepository
from app.notification.schemas import NotificationListItem, NotificationQuery, UnreadCountResponse


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = NotificationRepository(session)

    async def create_notice(
        self,
        *,
        user_id: str,
        notice_type: str,
        title: str,
        content: str | None = None,
        related_type: str | None = None,
        related_id: str | None = None,
        priority: str = "NORMAL",
    ) -> Notification:
        notification = Notification(
            id=generate_ulid(),
            user_id=user_id,
            notice_type=notice_type,
            title=title,
            content=content,
            related_type=related_type,
            related_id=related_id,
            priority=priority,
        )
        return await self._repo.create(notification)

    async def list_notifications(self, user_id: str, query: NotificationQuery) -> dict[str, Any]:
        offset = (query.page_no - 1) * query.page_size
        items, total = await self._repo.list_by_user(
            user_id=user_id,
            is_read=query.is_read,
            notice_type=query.notice_type,
            offset=offset,
            limit=query.page_size,
        )
        result = [self._to_list_item(item).model_dump(by_alias=True) for item in items]
        params = PaginationParams(pageNo=query.page_no, pageSize=query.page_size)
        return paginate(result, total, params)

    async def get_unread_count(self, user_id: str) -> UnreadCountResponse:
        total, by_type = await self._repo.count_unread(user_id)
        return UnreadCountResponse(total=total, by_type=by_type)

    async def mark_read(self, notification_id: str, user_id: str) -> dict[str, str]:
        notification = await self._repo.get_by_id(notification_id)
        if notification is None:
            raise BizError(ErrorCode.NOTIFICATION_NOT_FOUND)
        if notification.user_id != user_id:
            raise BizError(ErrorCode.FORBIDDEN)
        await self._repo.mark_read(notification)
        await self._session.commit()
        return {"id": notification_id, "status": "READ"}

    async def mark_all_read(self, user_id: str, notice_type: str | None) -> dict[str, int]:
        count = await self._repo.mark_all_read(user_id, notice_type)
        await self._session.commit()
        return {"updatedCount": count}

    def _to_list_item(self, notification: Notification) -> NotificationListItem:
        return NotificationListItem(
            id=notification.id,
            notice_type=notification.notice_type,
            title=notification.title,
            content=notification.content,
            is_read=bool(notification.is_read),
            related_type=notification.related_type,
            related_id=notification.related_id,
            priority=notification.priority,
            created_at=format_beijing(notification.created_at),
        )
