from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import BizError, ErrorCode
from app.common.utils import format_beijing, mask_phone
from app.core.auth import create_access_token
from app.db.ulid import generate_ulid
from app.user.models import User, UserCertRequest
from app.user.repository import UserCertRequestRepository, UserRepository
from app.user.schemas import (
    CertificationRequest,
    CertificationResponse,
    CurrentUser,
    LoginRequest,
    LoginResponse,
    LoginUserData,
    SmsCodeRequest,
    SmsCodeResponse,
    UpdateProfileRequest,
    UserProfileResponse,
)

DEMO_SMS_CODE = "123456"
_sms_codes: dict[str, tuple[str, datetime, datetime]] = {}


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserRepository(session)
        self._cert_repo = UserCertRequestRepository(session)

    # ---- Auth ----

    async def send_sms_code(self, req: SmsCodeRequest) -> SmsCodeResponse:
        now = datetime.now(UTC)
        existing = _sms_codes.get(req.phone)
        if existing is not None:
            _, _, sent_at = existing
            if now - sent_at < timedelta(seconds=60):
                raise BizError(ErrorCode.DUPLICATE_SUBMIT)

        expires_at = now + timedelta(seconds=300)
        _sms_codes[req.phone] = (DEMO_SMS_CODE, expires_at, now)
        return SmsCodeResponse(sent=True, expires_in=300, debug_code=DEMO_SMS_CODE)

    async def login(self, req: LoginRequest) -> LoginResponse:
        if req.login_type == "PHONE_CODE":
            self._validate_sms_code(req.phone, req.code)
        elif req.password is None:
            raise BizError(ErrorCode.PARAM_ERROR)

        user = await self._repo.get_by_phone(req.phone)
        if user is None:
            if req.login_type != "PHONE_CODE":
                raise BizError(ErrorCode.UNAUTHORIZED)
            user = User(
                id=generate_ulid(),
                phone=req.phone,
                password_hash="",
                nickname=f"用户{req.phone[-4:]}",
                role="USER",
                cert_status="UNVERIFIED",
                credit_score=100,
                status="ACTIVE",
            )
            await self._repo.create(user)
            await self._session.commit()
        else:
            if user.status != "ACTIVE":
                raise BizError(ErrorCode.USER_DISABLED)
            if req.login_type == "PASSWORD" and user.password_hash != req.password:
                raise BizError(ErrorCode.UNAUTHORIZED)

        token = create_access_token({"sub": user.id, "role": user.role, "status": user.status})
        user_data = LoginUserData.model_validate(user)
        return LoginResponse(token=token, user=user_data)

    def _validate_sms_code(self, phone: str, code: str | None) -> None:
        if code is None:
            raise BizError(ErrorCode.SMS_CODE_INVALID)
        now = datetime.now(UTC)
        existing = _sms_codes.get(phone)
        if existing is None:
            raise BizError(ErrorCode.SMS_CODE_INVALID)
        expected, expires_at, _ = existing
        if now > expires_at or code != expected:
            raise BizError(ErrorCode.SMS_CODE_INVALID)

    # ---- Profile ----

    async def get_profile(self, current_user: CurrentUser) -> UserProfileResponse:
        user = await self._repo.get_by_id(current_user.id)
        if user is None:
            raise BizError(ErrorCode.NOT_FOUND)
        resp = UserProfileResponse.model_validate(user)
        resp.phone = mask_phone(user.phone)
        return resp

    async def update_profile(
        self, current_user: CurrentUser, req: UpdateProfileRequest
    ) -> UserProfileResponse:
        user = await self._repo.get_by_id(current_user.id)
        if user is None:
            raise BizError(ErrorCode.NOT_FOUND)
        if req.nickname is not None:
            user.nickname = req.nickname
        if req.avatar_url is not None:
            user.avatar_url = req.avatar_url
        await self._repo.update(user)
        await self._session.commit()
        return await self.get_profile(current_user)

    # ---- Certification ----

    async def submit_certification(
        self, current_user: CurrentUser, req: CertificationRequest
    ) -> CertificationResponse:
        user = await self._repo.get_by_id(current_user.id)
        if user is None:
            raise BizError(ErrorCode.NOT_FOUND)
        if await self._cert_repo.has_pending(current_user.id):
            raise BizError(ErrorCode.CERT_PENDING)

        cert_request = UserCertRequest(
            id=generate_ulid(),
            user_id=current_user.id,
            campus_id=req.campus_id,
            document_image_url=req.document_image_url,
            review_status="PENDING",
        )
        user.campus_id = req.campus_id
        user.real_name = req.real_name
        user.cert_status = "PENDING"

        await self._cert_repo.create(cert_request)
        await self._repo.update(user)
        await self._session.commit()
        return self._to_cert_response(cert_request, user.real_name)

    async def get_certification(self, current_user: CurrentUser) -> CertificationResponse | None:
        user = await self._repo.get_by_id(current_user.id)
        if user is None:
            raise BizError(ErrorCode.NOT_FOUND)
        cert_request = await self._cert_repo.get_latest_by_user(current_user.id)
        if cert_request is None:
            return None
        return self._to_cert_response(cert_request, user.real_name)

    async def cancel_account(self, current_user: CurrentUser) -> dict[str, str]:
        user = await self._repo.get_by_id(current_user.id)
        if user is None:
            raise BizError(ErrorCode.NOT_FOUND)
        user.status = "CANCELLED"
        await self._repo.update(user)
        await self._session.commit()
        return {"id": current_user.id, "status": "CANCELLED"}

    def _to_cert_response(
        self, cert_request: UserCertRequest, real_name: str | None
    ) -> CertificationResponse:
        return CertificationResponse(
            id=cert_request.id,
            campus_id=cert_request.campus_id,
            real_name=real_name,
            document_image_url=cert_request.document_image_url,
            review_status=cert_request.review_status,
            review_comment=cert_request.review_comment,
            reviewed_at=(
                format_beijing(cert_request.reviewed_at)
                if cert_request.reviewed_at is not None
                else None
            ),
            created_at=format_beijing(cert_request.created_at),
        )
