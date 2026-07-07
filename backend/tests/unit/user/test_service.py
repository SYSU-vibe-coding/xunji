import pytest
from app.common.errors import BizError, ErrorCode
from app.operation_log.models import OperationLog
from app.user.schemas import (
    CertificationRequest,
    CurrentUser,
    LoginRequest,
    RegisterRequest,
    SmsCodeRequest,
)
from app.user.service import UserService
from sqlalchemy import select


async def _register_user(svc: UserService, phone: str, password: str = "secret123"):
    sms = await svc.send_sms_code(SmsCodeRequest(phone=phone))
    return await svc.register(
        RegisterRequest(
            phone=phone,
            code=sms.debug_code,
            password=password,
            nickname=f"用户{phone[-4:]}",
        )
    )


class TestUserServiceLogin:
    async def test_register_and_password_login(self, session):
        svc = UserService(session)
        await _register_user(svc, "13900139000")
        req = LoginRequest(loginType="PASSWORD", phone="13900139000", password="secret123")
        resp = await svc.login(req)
        assert resp.token
        assert resp.user.role == "USER"
        assert resp.user.credit_score == 100

    async def test_phone_code_login_requires_existing_user(self, session):
        svc = UserService(session)
        sms = await svc.send_sms_code(SmsCodeRequest(phone="13900139009"))
        req = LoginRequest(loginType="PHONE_CODE", phone="13900139009", code=sms.debug_code)
        with pytest.raises(BizError) as exc_info:
            await svc.login(req)
        assert exc_info.value.code == ErrorCode.UNAUTHORIZED

    async def test_login_existing_user(self, session):
        svc = UserService(session)
        await _register_user(svc, "13900139001")
        req = LoginRequest(loginType="PASSWORD", phone="13900139001", password="secret123")
        resp1 = await svc.login(req)
        resp2 = await svc.login(req)
        assert resp1.user.id == resp2.user.id

    async def test_login_disabled_user(self, session):
        svc = UserService(session)
        resp = await _register_user(svc, "13900139002")
        user = await svc._repo.get_by_id(resp.user.id)
        user.status = "DISABLED"
        await svc._repo.update(user)
        await session.commit()
        req = LoginRequest(loginType="PASSWORD", phone="13900139002", password="secret123")
        with pytest.raises(BizError) as exc_info:
            await svc.login(req)
        assert exc_info.value.code == ErrorCode.USER_DISABLED


class TestUserServiceProfile:
    async def test_get_profile_masked_phone(self, session):
        svc = UserService(session)
        login_resp = await _register_user(svc, "13800001234")

        current = CurrentUser(id=login_resp.user.id, role="USER", status="ACTIVE")
        profile = await svc.get_profile(current)
        assert "****" in profile.phone
        assert profile.credit_score == 100


class TestUserServiceCertification:
    async def test_submit_certification(self, session):
        svc = UserService(session)
        login_resp = await _register_user(svc, "13800004321")

        current = CurrentUser(id=login_resp.user.id, role="USER", status="ACTIVE")
        cert = await svc.submit_certification(
            current,
            CertificationRequest(
                campusId="S20260002",
                realName="Test User",
                documentImageUrl="https://example.com/cert.jpg",
            ),
        )
        assert cert.review_status == "PENDING"

        result = await session.execute(
            select(OperationLog).where(
                OperationLog.biz_type == "CERT",
                OperationLog.biz_id == cert.id,
                OperationLog.action == "CREATE",
            )
        )
        assert result.scalar_one_or_none() is not None

    async def test_cancel_account_writes_operation_log(self, session):
        svc = UserService(session)
        login_resp = await _register_user(svc, "13800004322")

        current = CurrentUser(id=login_resp.user.id, role="USER", status="ACTIVE")
        resp = await svc.cancel_account(current)
        assert resp["status"] == "CANCELLED"

        result = await session.execute(
            select(OperationLog).where(
                OperationLog.biz_type == "USER",
                OperationLog.biz_id == login_resp.user.id,
                OperationLog.action == "UPDATE_STATUS",
            )
        )
        assert result.scalar_one_or_none() is not None
