from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import Announcement
from app.admin.repository import AnnouncementRepository, ReportRepository
from app.admin.schemas import (
    AnnouncementCreateRequest,
    ReportHandleRequest,
    ReviewRequest,
    UserStatusRequest,
)
from app.common.errors import BizError, ErrorCode
from app.common.pagination import PaginationParams, paginate
from app.common.utils import format_beijing
from app.credit.service import CreditService
from app.db.ulid import generate_ulid
from app.item.service import ItemService
from app.notification.service import NotificationService
from app.operation_log.service import OperationLogService
from app.user.schemas import CurrentUser
from app.user.service import UserService


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._report_repo = ReportRepository(session)
        self._announcement_repo = AnnouncementRepository(session)
        self._user_svc = UserService(session)
        self._item_svc = ItemService(session)
        self._credit_svc = CreditService(session)
        self._notification_svc = NotificationService(session)
        self._log_svc = OperationLogService(session)

    async def list_certifications(
        self, review_status: str | None, page_no: int, page_size: int
    ) -> dict[str, Any]:
        offset = (page_no - 1) * page_size
        certs, total = await self._user_svc.list_certifications_internal(
            review_status, offset, page_size
        )
        items = []
        for cert in certs:
            user = await self._user_svc.get_user_internal(cert.user_id)
            items.append(
                {
                    "id": cert.id,
                    "userId": cert.user_id,
                    "nickname": user.nickname if user else "",
                    "campusId": cert.campus_id,
                    "realName": user.real_name if user else None,
                    "documentImageUrl": cert.document_image_url,
                    "reviewStatus": cert.review_status,
                    "createdAt": format_beijing(cert.created_at),
                }
            )
        return paginate(items, total, PaginationParams(pageNo=page_no, pageSize=page_size))

    async def review_certification(
        self, cert_id: str, req: ReviewRequest, admin_user: CurrentUser
    ) -> dict[str, str]:
        cert, user = await self._user_svc.review_certification_internal(
            cert_id, req.action, req.comment, admin_user.id
        )
        if req.action == "APPROVE":
            await self._credit_svc.change_credit(
                user_id=user.id,
                delta_score=20,
                reason_code="CERT_APPROVED",
                reason_text="实名认证通过",
                biz_type="CERT",
                biz_id=cert.id,
                operator_id=admin_user.id,
                operator_role=admin_user.role,
            )
        await self._notification_svc.create_notice(
            user_id=user.id,
            notice_type="SYSTEM_ANNOUNCEMENT",
            title="实名认证审核结果",
            content=f"认证审核结果:{cert.review_status}",
            related_type="CERT",
            related_id=cert.id,
        )
        await self._log_svc.create_log(
            operator_id=admin_user.id,
            operator_role=admin_user.role,
            biz_type="CERT",
            biz_id=cert.id,
            action="CERT_APPROVE" if req.action == "APPROVE" else "CERT_REJECT",
            detail=f"认证审核: {cert.review_status}",
        )
        await self._session.commit()
        return {"id": cert.id, "reviewStatus": cert.review_status}

    async def list_items_for_review(
        self, biz_type: str | None, page_no: int, page_size: int
    ) -> dict[str, Any]:
        offset = (page_no - 1) * page_size
        items, total = await self._item_svc.list_admin_items_internal(biz_type, offset, page_size)
        return paginate(items, total, PaginationParams(pageNo=page_no, pageSize=page_size))

    async def review_item(
        self, biz_type: str, item_id: str, req: ReviewRequest, admin_user: CurrentUser
    ) -> dict[str, str]:
        result = await self._item_svc.review_item_internal(biz_type, item_id, req.action)
        await self._notification_svc.create_notice(
            user_id=result["userId"],
            notice_type="SYSTEM_ANNOUNCEMENT",
            title="物品审核结果",
            content=f"物品审核结果:{req.action}",
            related_type=result["bizType"],
            related_id=item_id,
        )
        await self._log_svc.create_log(
            operator_id=admin_user.id,
            operator_role=admin_user.role,
            biz_type=result["bizType"],
            biz_id=item_id,
            action="REVIEW_APPROVE" if req.action == "APPROVE" else "REVIEW_REJECT",
            detail=f"物品审核: {req.action}",
        )
        await self._session.commit()
        return {"id": item_id, "status": result["status"]}

    async def list_reports(
        self,
        handle_status: str | None,
        target_type: str | None,
        page_no: int,
        page_size: int,
    ) -> dict[str, Any]:
        offset = (page_no - 1) * page_size
        reports, total = await self._report_repo.list_with_filter(
            handle_status=handle_status,
            target_type=target_type,
            offset=offset,
            limit=page_size,
        )
        items = [
            {
                "id": report.id,
                "reporterId": report.reporter_id,
                "reportedUserId": report.reported_user_id,
                "targetType": report.target_type,
                "targetId": report.target_id,
                "reason": report.reason,
                "description": report.description,
                "handleStatus": report.handle_status,
                "createdAt": format_beijing(report.created_at),
            }
            for report in reports
        ]
        return paginate(items, total, PaginationParams(pageNo=page_no, pageSize=page_size))

    async def handle_report(
        self, report_id: str, req: ReportHandleRequest, admin_user: CurrentUser
    ) -> dict[str, str]:
        report = await self._report_repo.get_by_id(report_id)
        if report is None:
            raise BizError(ErrorCode.REPORT_TARGET_NOT_FOUND)
        report.handle_status = "CLOSED" if req.action == "VALID" else "REJECTED"
        report.handle_result = req.result
        report.handler_id = admin_user.id
        await self._report_repo.update(report)
        if (
            req.action == "VALID"
            and report.reported_user_id
            and req.credit_delta
            and req.reason_code
        ):
            await self._credit_svc.change_credit(
                user_id=report.reported_user_id,
                delta_score=req.credit_delta,
                reason_code=req.reason_code,
                reason_text=req.result,
                biz_type="REPORT",
                biz_id=report.id,
                operator_id=admin_user.id,
                operator_role=admin_user.role,
            )
        await self._notification_svc.create_notice(
            user_id=report.reporter_id,
            notice_type="SYSTEM_ANNOUNCEMENT",
            title="举报处理结果",
            content=f"举报处理结果:{report.handle_status}",
            related_type="REPORT",
            related_id=report.id,
        )
        await self._log_svc.create_log(
            operator_id=admin_user.id,
            operator_role=admin_user.role,
            biz_type="REPORT",
            biz_id=report.id,
            action="REPORT_HANDLE",
            detail=f"举报处理: {report.handle_status}",
        )
        await self._session.commit()
        return {"id": report.id, "handleStatus": report.handle_status}

    async def create_announcement(
        self, req: AnnouncementCreateRequest, admin_user: CurrentUser
    ) -> dict[str, str]:
        now = datetime.now(UTC).replace(tzinfo=None)
        announcement = Announcement(
            id=generate_ulid(),
            title=req.title,
            content=req.content,
            status="PUBLISHED" if req.publish_now else "DRAFT",
            published_by=admin_user.id if req.publish_now else None,
            published_at=now if req.publish_now else None,
        )
        await self._announcement_repo.create(announcement)
        await self._log_svc.create_log(
            operator_id=admin_user.id,
            operator_role=admin_user.role,
            biz_type="ANNOUNCEMENT",
            biz_id=announcement.id,
            action="CREATE",
            detail=f"创建公告: {req.title}",
        )
        await self._session.commit()
        return {"id": announcement.id, "status": announcement.status}

    async def get_dashboard(self) -> dict[str, Any]:
        _, total_users = await self._user_svc.list_users_internal(
            role=None, status=None, keyword=None, offset=0, limit=1
        )
        _, total_lost = await self._item_svc.list_admin_items_internal("LOST", 0, 1)
        _, total_found = await self._item_svc.list_admin_items_internal("FOUND", 0, 1)
        _, pending_reports = await self._report_repo.list_with_filter(
            handle_status="PENDING", target_type=None, offset=0, limit=1
        )
        _, pending_certs = await self._user_svc.list_certifications_internal("PENDING", 0, 1)
        return {
            "totalUsers": total_users,
            "totalLost": total_lost,
            "totalFound": total_found,
            "handedOverCount": 0,
            "recoveryRate": 0,
            "avgHandleHours": 0,
            "pendingCertifications": pending_certs,
            "pendingReports": pending_reports,
        }

    async def list_users(
        self,
        role: str | None,
        status: str | None,
        keyword: str | None,
        page_no: int,
        page_size: int,
    ) -> dict[str, Any]:
        offset = (page_no - 1) * page_size
        users, total = await self._user_svc.list_users_internal(
            role=role, status=status, keyword=keyword, offset=offset, limit=page_size
        )
        items = [
            {
                "id": user.id,
                "phone": user.phone,
                "nickname": user.nickname,
                "role": user.role,
                "certStatus": user.cert_status,
                "creditScore": user.credit_score,
                "status": user.status,
                "createdAt": format_beijing(user.created_at),
            }
            for user in users
        ]
        return paginate(items, total, PaginationParams(pageNo=page_no, pageSize=page_size))

    async def change_user_status(
        self, user_id: str, req: UserStatusRequest, admin_user: CurrentUser
    ) -> dict[str, str]:
        user = await self._user_svc.change_user_status_internal(user_id, req.status)
        await self._notification_svc.create_notice(
            user_id=user.id,
            notice_type="SYSTEM_ANNOUNCEMENT",
            title="账号状态变更",
            content=f"账号状态已变更为 {user.status}",
            related_type="USER",
            related_id=user.id,
        )
        await self._log_svc.create_log(
            operator_id=admin_user.id,
            operator_role=admin_user.role,
            biz_type="USER",
            biz_id=user.id,
            action="UPDATE_STATUS",
            detail=f"管理员修改用户状态: {user.status}",
        )
        await self._session.commit()
        return {"id": user.id, "status": user.status}
