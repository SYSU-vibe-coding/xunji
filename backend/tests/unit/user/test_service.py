import pytest
from app.common.errors import BizError, ErrorCode
from app.user.schemas import CertificationRequest, CurrentUser, LoginRequest, SmsCodeRequest
from app.user.service import UserService


class TestUserServiceLogin:
    async def test_login_auto_register(self, session):
        svc = UserService(session)
        sms = await svc.send_sms_code(SmsCodeRequest(phone="13900139000"))
        req = LoginRequest(loginType="PHONE_CODE", phone="13900139000", code=sms.debug_code)
        resp = await svc.login(req)
        assert resp.token
        assert resp.user.role == "USER"
        assert resp.user.credit_score == 100

    async def test_login_existing_user(self, session):
        svc = UserService(session)
        sms = await svc.send_sms_code(SmsCodeRequest(phone="13900139001"))
        req = LoginRequest(loginType="PHONE_CODE", phone="13900139001", code=sms.debug_code)
        # First login: auto-register
        resp1 = await svc.login(req)
        # Second login: same user
        resp2 = await svc.login(req)
        assert resp1.user.id == resp2.user.id

    async def test_login_disabled_user(self, session):
        svc = UserService(session)
        sms = await svc.send_sms_code(SmsCodeRequest(phone="13900139002"))
        req = LoginRequest(loginType="PHONE_CODE", phone="13900139002", code=sms.debug_code)
        resp = await svc.login(req)
        # Manually disable
        user = await svc._repo.get_by_id(resp.user.id)
        user.status = "DISABLED"
        await svc._repo.update(user)
        await session.commit()
        # Try login again
        with pytest.raises(BizError) as exc_info:
            await svc.login(req)
        assert exc_info.value.code == ErrorCode.USER_DISABLED


class TestUserServiceProfile:
    async def test_get_profile_masked_phone(self, session):
        svc = UserService(session)
        sms = await svc.send_sms_code(SmsCodeRequest(phone="13800001234"))
        req = LoginRequest(loginType="PHONE_CODE", phone="13800001234", code=sms.debug_code)
        login_resp = await svc.login(req)

        current = CurrentUser(id=login_resp.user.id, role="USER", status="ACTIVE")
        profile = await svc.get_profile(current)
        assert "****" in profile.phone
        assert profile.credit_score == 100


class TestUserServiceCertification:
    async def test_submit_certification(self, session):
        svc = UserService(session)
        sms = await svc.send_sms_code(SmsCodeRequest(phone="13800004321"))
        login_resp = await svc.login(
            LoginRequest(loginType="PHONE_CODE", phone="13800004321", code=sms.debug_code)
        )

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
