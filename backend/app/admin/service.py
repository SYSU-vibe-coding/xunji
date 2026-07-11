import json
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
from app.claim.service import ClaimService
from app.common.errors import BizError, ErrorCode
from app.common.pagination import PaginationParams, paginate
from app.common.utils import format_beijing
from app.core.object_storage import get_object_storage
from app.credit.service import CreditService
from app.db.ulid import generate_ulid
from app.item.service import ItemService
from app.notification.service import NotificationService
from app.operation_log.repository import OperationLogRepository
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
        self._claim_svc = ClaimService(session)
        self._credit_svc = CreditService(session)
        self._notification_svc = NotificationService(session)
        self._log_svc = OperationLogService(session)
        self._log_repo = OperationLogRepository(session)
        self._storage = get_object_storage()

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
                    "documentImageUrl": await self._storage.sign_reference(
                        cert.document_image_url, sensitive=True
                    ),
                    "reviewStatus": cert.review_status,
                    "reviewComment": cert.review_comment,
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
            content=self._review_notice_content(cert.review_status, req.comment),
            related_type="CERT",
            related_id=cert.id,
        )
        await self._log_svc.create_log(
            operator_id=admin_user.id,
            operator_role=admin_user.role,
            biz_type="CERT",
            biz_id=cert.id,
            action="CERT_APPROVE" if req.action == "APPROVE" else "CERT_REJECT",
            detail=json.dumps(
                {"reviewStatus": cert.review_status, "comment": req.comment},
                ensure_ascii=False,
            ),
        )
        await self._session.commit()
        return {"id": cert.id, "reviewStatus": cert.review_status}

    async def list_items_for_review(
        self,
        biz_type: str | None,
        target_id: str | None,
        page_no: int,
        page_size: int,
    ) -> dict[str, Any]:
        offset = (page_no - 1) * page_size
        items, total = await self._item_svc.list_admin_items_internal(
            biz_type, offset, page_size, target_id
        )
        for item in items:
            user = await self._user_svc.get_user_internal(item["userId"])
            item["ownerNickname"] = user.nickname if user else ""
        return paginate(items, total, PaginationParams(pageNo=page_no, pageSize=page_size))

    async def review_item(
        self, biz_type: str, item_id: str, req: ReviewRequest, admin_user: CurrentUser
    ) -> dict[str, str]:
        result = await self._item_svc.review_item_internal(
            biz_type,
            item_id,
            req.action,
            req.comment,
            operator_id=admin_user.id,
            operator_role=admin_user.role,
        )
        await self._notification_svc.create_notice(
            user_id=result["userId"],
            notice_type="SYSTEM_ANNOUNCEMENT",
            title="物品审核结果",
            content=self._review_notice_content(result["reviewStatus"], req.comment),
            related_type=result["bizType"],
            related_id=item_id,
        )
        await self._log_svc.create_log(
            operator_id=admin_user.id,
            operator_role=admin_user.role,
            biz_type=result["bizType"],
            biz_id=item_id,
            action="REVIEW_APPROVE" if req.action == "APPROVE" else "REVIEW_REJECT",
            detail=json.dumps(
                {
                    "action": req.action,
                    "reviewStatus": result["reviewStatus"],
                    "comment": req.comment,
                },
                ensure_ascii=False,
            ),
        )
        await self._session.commit()
        return {"id": item_id, "status": result["status"], "reviewStatus": result["reviewStatus"]}

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
                "handleResult": report.handle_result,
                "handlerId": report.handler_id,
                "createdAt": format_beijing(report.created_at),
            }
            for report in reports
        ]
        return paginate(items, total, PaginationParams(pageNo=page_no, pageSize=page_size))

    async def get_item_review_detail(
        self, biz_type: str, item_id: str, admin_user: CurrentUser
    ) -> dict[str, Any]:
        normalized = biz_type.upper()
        if normalized == "LOST":
            lost_item = await self._item_svc.get_lost_item_internal(item_id)
            detail = await self._item_svc.get_lost_item_detail(item_id, admin_user)
            publisher_id = lost_item.user_id
            review_comment = lost_item.review_comment
        elif normalized == "FOUND":
            found_item = await self._item_svc.get_found_item_internal(item_id)
            detail = await self._item_svc.get_found_item_detail(item_id, admin_user)
            publisher_id = found_item.user_id
            review_comment = found_item.review_comment
        else:
            raise BizError(ErrorCode.PARAM_ERROR, "bizType must be LOST or FOUND")
        publisher = await self._user_svc.get_user_internal(publisher_id)
        if publisher is None:
            raise BizError(ErrorCode.NOT_FOUND, "物品发布者不存在")
        detail.update(
            bizType=normalized,
            reviewComment=review_comment,
            publisher={
                "id": publisher.id,
                "nickname": publisher.nickname,
                "phone": publisher.phone,
                "status": publisher.status,
            },
        )
        return detail

    async def list_claims(
        self, review_status: str | None, page_no: int, page_size: int
    ) -> dict[str, Any]:
        return await self._claim_svc.list_admin_claims(
            review_status=review_status, page_no=page_no, page_size=page_size
        )

    async def get_claim_detail(self, claim_id: str) -> dict[str, Any]:
        return await self._claim_svc.get_admin_claim_detail(claim_id)

    async def handle_report(
        self, report_id: str, req: ReportHandleRequest, admin_user: CurrentUser
    ) -> dict[str, str]:
        report = await self._report_repo.get_by_id_for_update(report_id)
        if report is None:
            raise BizError(ErrorCode.REPORT_TARGET_NOT_FOUND)
        if report.handle_status not in {"PENDING", "PROCESSING"}:
            raise BizError(ErrorCode.REVIEW_STATE_CHANGED)
        reported_user_id = await self._item_svc.get_report_target_user_for_update(
            report.target_type, report.target_id
        )
        penalty = self._report_penalty(report.target_type)
        if req.action == "VALID" and (
            (req.credit_delta is not None and req.credit_delta != penalty[0])
            or (req.reason_code is not None and req.reason_code != penalty[1])
        ):
            raise BizError(ErrorCode.PARAM_ERROR, "举报处罚必须使用目标类型对应的规则")
        new_status = "CLOSED" if req.action == "VALID" else "REJECTED"
        transitioned = await self._report_repo.transition_open(
            report_id=report.id,
            expected_status=report.handle_status,
            handle_status=new_status,
            handle_result=req.result,
            handler_id=admin_user.id,
            reported_user_id=reported_user_id,
        )
        if not transitioned:
            raise BizError(ErrorCode.REVIEW_STATE_CHANGED)
        report.handle_status = new_status
        report.handle_result = req.result
        report.handler_id = admin_user.id
        report.reported_user_id = reported_user_id
        terminated_count = 0
        if req.action == "VALID":
            terminated_count = await self._item_svc.take_down_report_target(
                report.target_type,
                report.target_id,
                operator_id=admin_user.id,
                operator_role=admin_user.role,
            )
            await self._credit_svc.change_credit(
                user_id=reported_user_id,
                delta_score=penalty[0],
                reason_code=penalty[1],
                reason_text=req.result,
                biz_type="REPORT",
                biz_id=report.id,
                operator_id=admin_user.id,
                operator_role=admin_user.role,
            )
        for user_id in {report.reporter_id, reported_user_id}:
            audience = "您提交的举报" if user_id == report.reporter_id else "涉及您的举报"
            await self._notification_svc.create_notice(
                user_id=user_id,
                notice_type="SYSTEM_ANNOUNCEMENT",
                title="举报处理结果",
                content=f"{audience}已处理为 {report.handle_status}: {req.result or '未核实'}",
                related_type="REPORT",
                related_id=report.id,
                priority="HIGH" if req.action == "VALID" else "NORMAL",
            )
        await self._log_svc.create_log(
            operator_id=admin_user.id,
            operator_role=admin_user.role,
            biz_type="REPORT",
            biz_id=report.id,
            action="REPORT_HANDLE",
            detail=json.dumps(
                {
                    "action": req.action,
                    "handleStatus": report.handle_status,
                    "result": req.result,
                    "targetType": report.target_type,
                    "targetId": report.target_id,
                    "reporterId": report.reporter_id,
                    "reportedUserId": reported_user_id,
                    "creditDelta": penalty[0] if req.action == "VALID" else None,
                    "reasonCode": penalty[1] if req.action == "VALID" else None,
                    "terminatedClaims": terminated_count,
                },
                ensure_ascii=False,
            ),
        )
        await self._session.commit()
        return {"id": report.id, "handleStatus": report.handle_status}

    async def create_announcement(
        self, req: AnnouncementCreateRequest, admin_user: CurrentUser
    ) -> dict[str, str]:
        announcement = Announcement(
            id=generate_ulid(),
            title=req.title,
            content=req.content,
            status="DRAFT",
            published_by=None,
            published_at=None,
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
        if req.publish_now:
            await self._publish_announcement(announcement, admin_user)
        await self._session.commit()
        return {"id": announcement.id, "status": announcement.status}

    async def list_announcements(
        self, status: str | None, page_no: int, page_size: int
    ) -> dict[str, Any]:
        if status is not None and status not in {"DRAFT", "PUBLISHED", "OFFLINE"}:
            raise BizError(ErrorCode.PARAM_ERROR, "status must be DRAFT, PUBLISHED or OFFLINE")
        announcements, total = await self._announcement_repo.list_for_admin(
            status=status,
            offset=(page_no - 1) * page_size,
            limit=page_size,
        )
        items = [self._announcement_data(item) for item in announcements]
        return paginate(items, total, PaginationParams(pageNo=page_no, pageSize=page_size))

    async def publish_announcement(
        self, announcement_id: str, admin_user: CurrentUser
    ) -> dict[str, str]:
        announcement = await self._get_announcement_or_raise(announcement_id)
        await self._publish_announcement(announcement, admin_user)
        await self._session.commit()
        return {"id": announcement.id, "status": announcement.status}

    async def offline_announcement(
        self, announcement_id: str, admin_user: CurrentUser
    ) -> dict[str, str]:
        announcement = await self._get_announcement_or_raise(announcement_id)
        if announcement.status == "OFFLINE":
            return {"id": announcement.id, "status": announcement.status}
        if announcement.status != "PUBLISHED":
            raise BizError(ErrorCode.INVALID_STATE, "仅已发布公告可下线")
        transitioned = await self._announcement_repo.transition_status(
            announcement_id=announcement.id,
            expected_status="PUBLISHED",
            new_status="OFFLINE",
        )
        if not transitioned:
            await self._session.refresh(announcement)
            if announcement.status == "OFFLINE":
                return {"id": announcement.id, "status": announcement.status}
            raise BizError(ErrorCode.REVIEW_STATE_CHANGED)
        announcement.status = "OFFLINE"
        await self._log_svc.create_log(
            operator_id=admin_user.id,
            operator_role=admin_user.role,
            biz_type="ANNOUNCEMENT",
            biz_id=announcement.id,
            action="OFFLINE",
            detail=f"下线公告: {announcement.title}",
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
        handover_stats = await self._claim_svc.get_handover_stats_internal()
        total_items = total_lost + total_found
        recovery_rate = (
            round(handover_stats["handedOverCount"] / total_items * 100, 2) if total_items else 0
        )
        return {
            "totalUsers": total_users,
            "totalLost": total_lost,
            "totalFound": total_found,
            "handedOverCount": handover_stats["handedOverCount"],
            "recoveryRate": recovery_rate,
            "avgHandleHours": handover_stats["avgHandleHours"],
            "pendingCertifications": pending_certs,
            "pendingReports": pending_reports,
        }

    async def list_users(
        self,
        role: str | None,
        status: str | None,
        keyword: str | None,
        user_id: str | None,
        page_no: int,
        page_size: int,
    ) -> dict[str, Any]:
        offset = (page_no - 1) * page_size
        users, total = await self._user_svc.list_users_internal(
            role=role,
            status=status,
            keyword=keyword,
            user_id=user_id,
            offset=offset,
            limit=page_size,
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
        user_before = await self._user_svc.get_user_internal(user_id)
        if user_before is None:
            raise BizError(ErrorCode.NOT_FOUND)
        old_status = user_before.status
        user = await self._user_svc.change_user_status_internal(user_id, req.status)
        await self._notification_svc.create_notice(
            user_id=user.id,
            notice_type="SYSTEM_ANNOUNCEMENT",
            title="账号状态变更",
            content=f"账号状态已变更为 {user.status}. 原因: {req.reason or '管理员恢复账号'}",
            related_type="USER",
            related_id=user.id,
        )
        await self._log_svc.create_log(
            operator_id=admin_user.id,
            operator_role=admin_user.role,
            biz_type="USER",
            biz_id=user.id,
            action="UPDATE_STATUS",
            detail=json.dumps(
                {"from": old_status, "to": user.status, "reason": req.reason},
                ensure_ascii=False,
            ),
        )
        await self._session.commit()
        return {"id": user.id, "status": user.status}

    def _review_notice_content(self, status: str, comment: str | None) -> str:
        return f"审核结果: {status}. 审核意见: {comment or '无'}"

    def _report_penalty(self, target_type: str) -> tuple[int, str]:
        if target_type in {"LOST_ITEM", "FOUND_ITEM"}:
            return -20, "FAKE_PUBLISH_CONFIRMED"
        if target_type == "CLAIM_REQUEST":
            return -30, "FRAUD_CLAIM_CONFIRMED"
        raise BizError(ErrorCode.PARAM_ERROR, "该举报目标类型不支持处罚")

    async def _get_announcement_or_raise(self, announcement_id: str) -> Announcement:
        announcement = await self._announcement_repo.get_by_id(announcement_id)
        if announcement is None:
            raise BizError(ErrorCode.NOT_FOUND)
        return announcement

    async def _publish_announcement(
        self, announcement: Announcement, admin_user: CurrentUser
    ) -> None:
        if announcement.status == "PUBLISHED":
            return
        if announcement.status != "DRAFT":
            raise BizError(ErrorCode.INVALID_STATE, "仅草稿公告可发布")
        now = datetime.now(UTC).replace(tzinfo=None)
        transitioned = await self._announcement_repo.transition_status(
            announcement_id=announcement.id,
            expected_status="DRAFT",
            new_status="PUBLISHED",
            published_by=admin_user.id,
            published_at=now,
        )
        if not transitioned:
            await self._session.refresh(announcement)
            if announcement.status == "PUBLISHED":
                return
            raise BizError(ErrorCode.REVIEW_STATE_CHANGED)
        announcement.status = "PUBLISHED"
        announcement.published_by = admin_user.id
        announcement.published_at = now
        after_id = None
        while True:
            user_ids = await self._user_svc.list_active_user_ids_internal(
                after_id=after_id, limit=500
            )
            if not user_ids:
                break
            await self._notification_svc.create_notices(
                user_ids=user_ids,
                notice_type="SYSTEM_ANNOUNCEMENT",
                title=announcement.title,
                content=(announcement.content or "")[:500],
                related_type="ANNOUNCEMENT",
                related_id=announcement.id,
            )
            if len(user_ids) < 500:
                break
            after_id = user_ids[-1]
        await self._log_svc.create_log(
            operator_id=admin_user.id,
            operator_role=admin_user.role,
            biz_type="ANNOUNCEMENT",
            biz_id=announcement.id,
            action="PUBLISH",
            detail=f"发布公告: {announcement.title}",
        )

    def _announcement_data(self, announcement: Announcement) -> dict[str, Any]:
        return {
            "id": announcement.id,
            "title": announcement.title,
            "content": announcement.content or "",
            "status": announcement.status,
            "publishedBy": announcement.published_by,
            "publishedAt": (
                format_beijing(announcement.published_at)
                if announcement.published_at is not None
                else None
            ),
            "createdAt": format_beijing(announcement.created_at),
            "updatedAt": format_beijing(announcement.updated_at),
        }

    async def list_operation_logs(
        self,
        biz_type: str | None,
        action: str | None,
        operator_role: str | None,
        keyword: str | None,
        page_no: int,
        page_size: int,
    ) -> dict[str, Any]:
        offset = (page_no - 1) * page_size
        logs, total = await self._log_repo.list_with_filter(
            biz_type=biz_type,
            action=action,
            operator_role=operator_role,
            keyword=keyword,
            offset=offset,
            limit=page_size,
        )
        items: list[dict[str, Any]] = []
        for log in logs:
            items.append(
                {
                    "id": log.id,
                    "operatorId": log.operator_id,
                    "operatorRole": log.operator_role,
                    "bizType": log.biz_type,
                    "bizId": log.biz_id,
                    "action": log.action,
                    "detail": log.detail,
                    "createdAt": format_beijing(log.created_at),
                }
            )
        params = PaginationParams(pageNo=page_no, pageSize=page_size)
        return paginate(items, total, params)
