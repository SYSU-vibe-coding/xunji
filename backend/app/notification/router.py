from typing import Any

from fastapi import APIRouter, Depends, Query

from app.common.response import success
from app.common.validators import validate_ulid
from app.core.auth import get_current_user
from app.notification.deps import get_notification_service
from app.notification.schemas import NotificationQuery, ReadAllRequest
from app.notification.service import NotificationService
from app.user.schemas import CurrentUser

router = APIRouter(tags=["notifications"])


@router.get("/announcements")
async def list_announcements(
    page_no: int = Query(default=1, ge=1, alias="pageNo"),
    page_size: int = Query(default=10, ge=1, le=50, alias="pageSize"),
    svc: NotificationService = Depends(get_notification_service),
) -> dict[str, Any]:
    data = await svc.list_announcements(page_no=page_no, page_size=page_size)
    return success(data=data)


@router.get("/announcements/{announcement_id}")
async def get_announcement(
    announcement_id: str,
    svc: NotificationService = Depends(get_notification_service),
) -> dict[str, Any]:
    announcement_id = validate_ulid(announcement_id, "announcementId")
    data = await svc.get_announcement(announcement_id)
    return success(data=data.model_dump(by_alias=True))


@router.get("/notifications")
async def list_notifications(
    page_no: int = Query(default=1, ge=1, alias="pageNo"),
    page_size: int = Query(default=10, ge=1, le=50, alias="pageSize"),
    is_read: bool | None = Query(default=None, alias="isRead"),
    notice_type: str | None = Query(default=None, alias="noticeType"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: NotificationService = Depends(get_notification_service),
) -> dict[str, Any]:
    query = NotificationQuery(
        pageNo=page_no,
        pageSize=page_size,
        isRead=is_read,
        noticeType=notice_type,
    )
    data = await svc.list_notifications(current_user.id, query)
    return success(data=data)


@router.get("/notifications/unread-count")
async def get_unread_count(
    current_user: CurrentUser = Depends(get_current_user),
    svc: NotificationService = Depends(get_notification_service),
) -> dict[str, Any]:
    data = await svc.get_unread_count(current_user.id)
    return success(data=data.model_dump(by_alias=True))


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    svc: NotificationService = Depends(get_notification_service),
) -> dict[str, Any]:
    notification_id = validate_ulid(notification_id, "notificationId")
    data = await svc.mark_read(notification_id, current_user.id)
    return success(data=data)


@router.post("/notifications/read-all")
async def mark_notifications_read_all(
    req: ReadAllRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: NotificationService = Depends(get_notification_service),
) -> dict[str, Any]:
    data = await svc.mark_all_read(current_user.id, req.notice_type)
    return success(data=data)
