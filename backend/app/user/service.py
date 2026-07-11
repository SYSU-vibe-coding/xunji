import secrets
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.claim.repository import ClaimRequestRepository
from app.common.errors import BizError, ErrorCode
from app.common.utils import format_beijing, mask_phone
from app.core.auth import create_access_token
from app.core.config import settings
from app.core.object_storage import ObjectStorage, get_object_storage
from app.core.security import hash_password, verify_password
from app.db.ulid import generate_ulid
from app.item.repository import FoundItemRepository, LostItemRepository
from app.job.repository import DurableJobRepository
from app.match.repository import MatchResultRepository
from app.notification.service import NotificationService
from app.operation_log.service import OperationLogService
from app.user.models import User, UserCertRequest
from app.user.repository import UserCertRequestRepository, UserRepository
from app.user.schemas import (
    CertificationRequest,
    CertificationResponse,
    CurrentUser,
    LoginRequest,
    LoginResponse,
    LoginUserData,
    RegisterRequest,
    SmsCodeRequest,
    SmsCodeResponse,
    UpdateProfileRequest,
    UserProfileResponse,
)

_sms_codes: dict[str, tuple[str, datetime]] = {}
_sms_sent_at: dict[str, datetime] = {}
SmsSender = Callable[[str, str], Awaitable[None]]


class UserService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: ObjectStorage | None = None,
        sms_sender: SmsSender | None = None,
    ) -> None:
        self._session = session
        self._repo = UserRepository(session)
        self._cert_repo = UserCertRequestRepository(session)
        self._claim_repo = ClaimRequestRepository(session)
        self._lost_repo = LostItemRepository(session)
        self._found_repo = FoundItemRepository(session)
        self._match_repo = MatchResultRepository(session)
        self._job_repo = DurableJobRepository(session)
        self._notification_svc = NotificationService(session)
        self._log_svc = OperationLogService(session)
        self._storage = storage or get_object_storage()
        self._sms_sender = sms_sender

    # ---- Auth ----

    async def send_sms_code(self, req: SmsCodeRequest) -> SmsCodeResponse:
        is_demo_phone = (
            settings.DEBUG and settings.SMS_DEBUG_ENABLED and req.phone in settings.sms_demo_phones
        )
        if not is_demo_phone and self._sms_sender is None:
            raise BizError(
                ErrorCode.SMS_SERVICE_UNAVAILABLE,
                "短信服务未配置; 课程演示号码必须显式加入 SMS_DEMO_PHONES 白名单",
            )

        now = datetime.now(UTC)
        sent_at = _sms_sent_at.get(req.phone)
        if sent_at is not None and now - sent_at < timedelta(
            seconds=settings.SMS_CODE_COOLDOWN_SECONDS
        ):
            raise BizError(ErrorCode.DUPLICATE_SUBMIT)

        code = f"{secrets.randbelow(1_000_000):06d}"
        if self._sms_sender is not None and not is_demo_phone:
            try:
                await self._sms_sender(req.phone, code)
            except Exception as exc:
                raise BizError(ErrorCode.SMS_SERVICE_UNAVAILABLE) from exc
        expires_at = now + timedelta(seconds=settings.SMS_CODE_TTL_SECONDS)
        _sms_codes[req.phone] = (code, expires_at)
        _sms_sent_at[req.phone] = now
        return SmsCodeResponse(
            sent=True,
            expires_in=settings.SMS_CODE_TTL_SECONDS,
            debug_code=code if is_demo_phone else None,
        )

    async def login(self, req: LoginRequest) -> LoginResponse:
        if req.login_type == "PHONE_CODE":
            if req.phone is None:
                raise BizError(ErrorCode.PARAM_ERROR)
            self._validate_sms_code(req.phone, req.code)
        elif req.password is None:
            raise BizError(ErrorCode.PARAM_ERROR)

        user = (
            await self._repo.get_by_phone(req.phone)
            if req.phone is not None
            else await self._repo.get_by_account(req.account or "")
        )
        if user is None:
            raise BizError(ErrorCode.UNAUTHORIZED)
        if user.status != "ACTIVE":
            raise BizError(ErrorCode.USER_DISABLED)
        if user.role == "ADMIN" and req.login_type != "PASSWORD":
            raise BizError(ErrorCode.UNAUTHORIZED)
        if req.login_type == "PASSWORD" and not verify_password(
            req.password or "", user.password_hash
        ):
            raise BizError(ErrorCode.UNAUTHORIZED)
        if req.login_type == "PHONE_CODE":
            self._consume_sms_code(req.phone or "", req.code)

        token = create_access_token({"sub": user.id, "role": user.role, "status": user.status})
        user_data = LoginUserData.model_validate(user)
        user_data.avatar_url = await self._storage.sign_reference(user.avatar_url, sensitive=False)
        return LoginResponse(token=token, user=user_data)

    async def register(self, req: RegisterRequest) -> LoginResponse:
        self._validate_sms_code(req.phone, req.code)
        existing = await self._repo.get_by_phone(req.phone)
        if existing is not None:
            raise BizError(ErrorCode.PHONE_REGISTERED)

        user = User(
            id=generate_ulid(),
            phone=req.phone,
            password_hash=hash_password(req.password),
            nickname=req.nickname,
            role="USER",
            cert_status="UNVERIFIED",
            credit_score=100,
            status="ACTIVE",
        )
        await self._repo.create(user)
        await self._session.commit()
        self._consume_sms_code(req.phone, req.code)
        token = create_access_token({"sub": user.id, "role": user.role, "status": user.status})
        return LoginResponse(token=token, user=LoginUserData.model_validate(user))

    def _validate_sms_code(self, phone: str, code: str | None) -> None:
        if code is None:
            raise BizError(ErrorCode.SMS_CODE_INVALID)
        now = datetime.now(UTC)
        existing = _sms_codes.get(phone)
        if existing is None:
            raise BizError(ErrorCode.SMS_CODE_INVALID)
        expected, expires_at = existing
        if now > expires_at:
            _sms_codes.pop(phone, None)
            raise BizError(ErrorCode.SMS_CODE_INVALID)
        if not secrets.compare_digest(code, expected):
            raise BizError(ErrorCode.SMS_CODE_INVALID)

    def _consume_sms_code(self, phone: str, code: str | None) -> None:
        self._validate_sms_code(phone, code)
        _sms_codes.pop(phone, None)

    # ---- Internal helpers ----

    async def get_user_internal(self, user_id: str) -> User | None:
        return await self._repo.get_by_id(user_id)

    async def get_user_for_update_internal(self, user_id: str) -> User | None:
        return await self._repo.get_by_id_for_update(user_id)

    async def update_credit_score_internal(self, user_id: str, delta_score: int) -> tuple[int, int]:
        user = await self._repo.get_by_id_for_update(user_id)
        if user is None:
            raise BizError(ErrorCode.NOT_FOUND)
        old_score = user.credit_score
        user.credit_score = max(0, min(999, old_score + delta_score))
        await self._repo.update(user)
        return user.credit_score, user.credit_score - old_score

    async def list_certifications_internal(
        self, review_status: str | None, offset: int, limit: int
    ) -> tuple[list[UserCertRequest], int]:
        return await self._cert_repo.list_with_filter(
            review_status=review_status, offset=offset, limit=limit
        )

    async def review_certification_internal(
        self, cert_id: str, action: str, comment: str | None, reviewer_id: str
    ) -> tuple[UserCertRequest, User]:
        existing = await self._cert_repo.get_by_id(cert_id)
        if existing is None:
            raise BizError(ErrorCode.NOT_FOUND)
        user = await self._repo.get_by_id_for_update(existing.user_id)
        if user is None:
            raise BizError(ErrorCode.NOT_FOUND)
        cert_request = await self._cert_repo.get_by_id_for_update(cert_id)
        if cert_request is None:
            raise BizError(ErrorCode.NOT_FOUND)
        if cert_request.review_status != "PENDING":
            raise BizError(ErrorCode.REVIEW_STATE_CHANGED)
        latest = await self._cert_repo.get_latest_by_user(user.id)
        if latest is None or latest.id != cert_request.id:
            raise BizError(ErrorCode.REVIEW_STATE_CHANGED)
        review_status = "APPROVED" if action == "APPROVE" else "REJECTED"
        reviewed_at = datetime.now(UTC).replace(tzinfo=None)
        transitioned = await self._cert_repo.transition_pending(
            cert_id=cert_id,
            review_status=review_status,
            review_comment=comment,
            reviewer_id=reviewer_id,
            reviewed_at=reviewed_at,
        )
        if not transitioned:
            raise BizError(ErrorCode.REVIEW_STATE_CHANGED)
        cert_request.review_status = review_status
        cert_request.review_comment = comment
        cert_request.reviewer_id = reviewer_id
        cert_request.reviewed_at = reviewed_at
        user.cert_status = review_status
        await self._repo.update(user)
        return cert_request, user

    async def list_users_internal(
        self,
        *,
        role: str | None,
        status: str | None,
        keyword: str | None,
        offset: int,
        limit: int,
        user_id: str | None = None,
    ) -> tuple[list[User], int]:
        return await self._repo.list_with_filter(
            role=role,
            status=status,
            keyword=keyword,
            offset=offset,
            limit=limit,
            user_id=user_id,
        )

    async def change_user_status_internal(self, user_id: str, status: str) -> User:
        user = await self._repo.get_by_id_for_update(user_id)
        if user is None:
            raise BizError(ErrorCode.NOT_FOUND)
        if (user.status, status) not in {("ACTIVE", "DISABLED"), ("DISABLED", "ACTIVE")}:
            raise BizError(ErrorCode.INVALID_STATE, "账号状态仅允许 ACTIVE 与 DISABLED 互转")
        if status == "DISABLED" and await self._claim_repo.has_active_for_user(user_id):
            raise BizError(ErrorCode.INVALID_STATE, "用户存在进行中的认领或交接, 暂不可禁用")
        user.status = status
        await self._repo.update(user)
        return user

    async def list_active_user_ids_internal(
        self, *, role: str | None = None, after_id: str | None = None, limit: int = 500
    ) -> list[str]:
        return await self._repo.list_active_ids(role=role, after_id=after_id, limit=limit)

    # ---- Profile ----

    async def get_profile(self, current_user: CurrentUser) -> UserProfileResponse:
        user = await self._repo.get_by_id(current_user.id)
        if user is None:
            raise BizError(ErrorCode.NOT_FOUND)
        resp = UserProfileResponse.model_validate(user)
        resp.phone = mask_phone(user.phone)
        resp.avatar_ref = self._storage.editable_asset_ref(
            user.avatar_url, user_id=user.id, biz_type="USER"
        )
        resp.avatar_url = await self._storage.sign_reference(user.avatar_url, sensitive=False)
        return resp

    async def update_profile(
        self, current_user: CurrentUser, req: UpdateProfileRequest
    ) -> UserProfileResponse:
        user = await self._repo.get_by_id(current_user.id)
        if user is None:
            raise BizError(ErrorCode.NOT_FOUND)
        if req.nickname is not None:
            user.nickname = req.nickname
        if req.avatar_ref is not None:
            await self._storage.validate_owned_asset(
                req.avatar_ref, user_id=current_user.id, biz_type="USER"
            )
            user.avatar_url = req.avatar_ref
        await self._repo.update(user)
        await self._session.commit()
        return await self.get_profile(current_user)

    # ---- Certification ----

    async def submit_certification(
        self, current_user: CurrentUser, req: CertificationRequest
    ) -> CertificationResponse:
        user = await self._repo.get_by_id_for_update(current_user.id)
        if user is None:
            raise BizError(ErrorCode.NOT_FOUND)
        if await self._cert_repo.has_pending(current_user.id):
            raise BizError(ErrorCode.CERT_PENDING)
        await self._storage.validate_owned_asset(
            req.document_image_ref, user_id=current_user.id, biz_type="CERT"
        )

        cert_request = UserCertRequest(
            id=generate_ulid(),
            user_id=current_user.id,
            campus_id=req.campus_id,
            document_image_url=req.document_image_ref,
            review_status="PENDING",
        )
        old_status = user.cert_status
        user.campus_id = req.campus_id
        user.real_name = req.real_name
        user.cert_status = "PENDING"

        await self._cert_repo.create(cert_request)
        await self._repo.update(user)
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="CERT",
            biz_id=cert_request.id,
            action="CREATE",
            detail=f"实名认证状态变更: {old_status} -> PENDING",
        )
        await self._session.flush()
        await self._session.refresh(cert_request)
        await self._session.commit()
        return await self._to_cert_response(cert_request, user.real_name)

    async def get_certification(self, current_user: CurrentUser) -> CertificationResponse | None:
        user = await self._repo.get_by_id(current_user.id)
        if user is None:
            raise BizError(ErrorCode.NOT_FOUND)
        cert_request = await self._cert_repo.get_latest_by_user(current_user.id)
        if cert_request is None:
            return None
        return await self._to_cert_response(cert_request, user.real_name)

    async def cancel_account(self, current_user: CurrentUser) -> dict[str, str]:
        user = await self._repo.get_by_id_for_update(current_user.id)
        if user is None:
            raise BizError(ErrorCode.NOT_FOUND)
        if user.status != "ACTIVE":
            raise BizError(ErrorCode.INVALID_STATE, "当前账号状态不可注销")
        if await self._claim_repo.has_active_for_user(user.id):
            raise BizError(ErrorCode.INVALID_STATE, "存在进行中的认领或交接, 请完成后再注销")

        # Match finalization locks lost before found. Keep the same item-table order.
        lost_items = await self._lost_repo.list_active_by_user_for_update(user.id)
        found_items = await self._found_repo.list_active_by_user_for_update(user.id)
        lost_ids = await self._lost_repo.list_ids_by_user(user.id)
        found_ids = await self._found_repo.list_ids_by_user(user.id)
        affected_lost_owners = await self._match_repo.list_active_lost_owner_ids_for_found_items(
            found_ids, exclude_user_id=user.id
        )

        for lost_item in lost_items:
            lost_item.status = "CLOSED"
            await self._lost_repo.update(lost_item)
        for found_item in found_items:
            found_item.status = "CLOSED"
            await self._found_repo.update(found_item)
        expired_matches = await self._match_repo.expire_by_items(
            lost_item_ids=lost_ids,
            found_item_ids=found_ids,
        )
        cancelled_jobs = await self._job_repo.cancel_pending_for_items(
            lost_item_ids=lost_ids,
            found_item_ids=found_ids,
            now=datetime.now(UTC).replace(tzinfo=None),
        )

        old_status = user.status
        user.status = "CANCELLED"
        await self._repo.update(user)
        await self._notification_svc.create_notices(
            user_ids=affected_lost_owners,
            notice_type="MATCH_RECOMMEND",
            title="一条匹配信息已失效",
            content="关联招领已因发布者注销关闭, 请查看其他匹配结果。",
        )
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="USER",
            biz_id=user.id,
            action="UPDATE_STATUS",
            detail=(
                f"用户状态变更: {old_status} -> CANCELLED; "
                f"关闭失物 {len(lost_items)} 条、招领 {len(found_items)} 条, "
                f"失效匹配 {expired_matches} 条、待执行任务 {cancelled_jobs} 条"
            ),
        )
        await self._session.commit()
        return {"id": current_user.id, "status": "CANCELLED"}

    async def _to_cert_response(
        self, cert_request: UserCertRequest, real_name: str | None
    ) -> CertificationResponse:
        document_image_url = await self._storage.sign_reference(
            cert_request.document_image_url, sensitive=True
        )
        document_image_ref = self._storage.editable_asset_ref(
            cert_request.document_image_url,
            user_id=cert_request.user_id,
            biz_type="CERT",
        )
        return CertificationResponse(
            id=cert_request.id,
            campus_id=cert_request.campus_id,
            real_name=real_name,
            document_image_url=document_image_url,
            document_image_ref=document_image_ref,
            review_status=cert_request.review_status,
            review_comment=cert_request.review_comment,
            reviewed_at=(
                format_beijing(cert_request.reviewed_at)
                if cert_request.reviewed_at is not None
                else None
            ),
            created_at=format_beijing(cert_request.created_at),
        )
