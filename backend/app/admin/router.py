from typing import Any

from fastapi import APIRouter, Depends, Query

from app.admin.deps import get_admin_service
from app.admin.schemas import (
    AnnouncementCreateRequest,
    ReportHandleRequest,
    ReviewRequest,
    UserStatusRequest,
)
from app.admin.service import AdminService
from app.common.response import success
from app.common.validators import validate_ulid
from app.core.auth import require_admin
from app.user.schemas import CurrentUser

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/certifications")
async def list_certifications(
    review_status: str | None = Query(default=None, alias="reviewStatus"),
    page_no: int = Query(default=1, ge=1, alias="pageNo"),
    page_size: int = Query(default=10, ge=1, le=50, alias="pageSize"),
    admin_user: CurrentUser = Depends(require_admin()),
    svc: AdminService = Depends(get_admin_service),
) -> dict[str, Any]:
    data = await svc.list_certifications(review_status, page_no, page_size)
    return success(data=data)


@router.post("/certifications/{cert_id}/review")
async def review_certification(
    cert_id: str,
    req: ReviewRequest,
    admin_user: CurrentUser = Depends(require_admin()),
    svc: AdminService = Depends(get_admin_service),
) -> dict[str, Any]:
    cert_id = validate_ulid(cert_id, "certId")
    data = await svc.review_certification(cert_id, req, admin_user)
    return success(data=data)


@router.get("/items/review")
async def list_items_for_review(
    biz_type: str | None = Query(default=None, alias="bizType"),
    page_no: int = Query(default=1, ge=1, alias="pageNo"),
    page_size: int = Query(default=10, ge=1, le=50, alias="pageSize"),
    admin_user: CurrentUser = Depends(require_admin()),
    svc: AdminService = Depends(get_admin_service),
) -> dict[str, Any]:
    data = await svc.list_items_for_review(biz_type, page_no, page_size)
    return success(data=data)


@router.post("/items/{biz_type}/{item_id}/review")
async def review_item(
    biz_type: str,
    item_id: str,
    req: ReviewRequest,
    admin_user: CurrentUser = Depends(require_admin()),
    svc: AdminService = Depends(get_admin_service),
) -> dict[str, Any]:
    item_id = validate_ulid(item_id, "itemId")
    data = await svc.review_item(biz_type, item_id, req, admin_user)
    return success(data=data)


@router.get("/reports")
async def list_reports(
    handle_status: str | None = Query(default=None, alias="handleStatus"),
    target_type: str | None = Query(default=None, alias="targetType"),
    page_no: int = Query(default=1, ge=1, alias="pageNo"),
    page_size: int = Query(default=10, ge=1, le=50, alias="pageSize"),
    admin_user: CurrentUser = Depends(require_admin()),
    svc: AdminService = Depends(get_admin_service),
) -> dict[str, Any]:
    data = await svc.list_reports(handle_status, target_type, page_no, page_size)
    return success(data=data)


@router.post("/reports/{report_id}/handle")
async def handle_report(
    report_id: str,
    req: ReportHandleRequest,
    admin_user: CurrentUser = Depends(require_admin()),
    svc: AdminService = Depends(get_admin_service),
) -> dict[str, Any]:
    report_id = validate_ulid(report_id, "reportId")
    data = await svc.handle_report(report_id, req, admin_user)
    return success(data=data)


@router.post("/announcements")
async def create_announcement(
    req: AnnouncementCreateRequest,
    admin_user: CurrentUser = Depends(require_admin()),
    svc: AdminService = Depends(get_admin_service),
) -> dict[str, Any]:
    data = await svc.create_announcement(req, admin_user)
    return success(data=data)


@router.get("/dashboard")
async def get_dashboard(
    admin_user: CurrentUser = Depends(require_admin()),
    svc: AdminService = Depends(get_admin_service),
) -> dict[str, Any]:
    data = await svc.get_dashboard()
    return success(data=data)


@router.get("/users")
async def list_users(
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page_no: int = Query(default=1, ge=1, alias="pageNo"),
    page_size: int = Query(default=10, ge=1, le=50, alias="pageSize"),
    admin_user: CurrentUser = Depends(require_admin()),
    svc: AdminService = Depends(get_admin_service),
) -> dict[str, Any]:
    data = await svc.list_users(role, status, keyword, page_no, page_size)
    return success(data=data)


@router.post("/users/{user_id}/status")
async def change_user_status(
    user_id: str,
    req: UserStatusRequest,
    admin_user: CurrentUser = Depends(require_admin()),
    svc: AdminService = Depends(get_admin_service),
) -> dict[str, Any]:
    user_id = validate_ulid(user_id, "userId")
    data = await svc.change_user_status(user_id, req, admin_user)
    return success(data=data)
