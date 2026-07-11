from typing import cast

from sqlalchemy import CursorResult, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.notification.models import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, notification: Notification) -> Notification:
        self._session.add(notification)
        await self._session.flush()
        return notification

    async def create_batch(self, notifications: list[Notification]) -> None:
        if not notifications:
            return
        await self._session.execute(
            insert(Notification),
            [
                {
                    "id": notice.id,
                    "user_id": notice.user_id,
                    "notice_type": notice.notice_type,
                    "title": notice.title,
                    "content": notice.content,
                    "is_read": notice.is_read or 0,
                    "related_type": notice.related_type,
                    "related_id": notice.related_id,
                    "priority": notice.priority,
                }
                for notice in notifications
            ],
        )

    async def get_by_id(self, notification_id: str) -> Notification | None:
        result = await self._session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        *,
        user_id: str,
        is_read: bool | None,
        notice_type: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        count_stmt = (
            select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
        )

        if is_read is not None:
            value = 1 if is_read else 0
            stmt = stmt.where(Notification.is_read == value)
            count_stmt = count_stmt.where(Notification.is_read == value)
        if notice_type:
            stmt = stmt.where(Notification.notice_type == notice_type)
            count_stmt = count_stmt.where(Notification.notice_type == notice_type)

        stmt = stmt.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def count_unread(self, user_id: str) -> tuple[int, dict[str, int]]:
        total_result = await self._session.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == 0,
            )
        )
        total = total_result.scalar() or 0
        by_type_result = await self._session.execute(
            select(Notification.notice_type, func.count())
            .where(Notification.user_id == user_id, Notification.is_read == 0)
            .group_by(Notification.notice_type)
        )
        by_type = {notice_type: count for notice_type, count in by_type_result.all()}
        return total, by_type

    async def mark_read(self, notification: Notification) -> Notification:
        notification.is_read = 1
        await self._session.merge(notification)
        await self._session.flush()
        return notification

    async def mark_all_read(self, user_id: str, notice_type: str | None = None) -> int:
        stmt = update(Notification).where(
            Notification.user_id == user_id, Notification.is_read == 0
        )
        if notice_type:
            stmt = stmt.where(Notification.notice_type == notice_type)
        result = await self._session.execute(stmt.values(is_read=1))
        return cast(CursorResult[object], result).rowcount or 0
