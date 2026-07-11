from datetime import UTC, datetime, timedelta

import pytest
from app.common.errors import BizError, ErrorCode
from app.core.config import settings
from app.db.ulid import generate_ulid
from app.item.models import FoundItem, LostItem
from app.job.models import DurableJob
from app.match.models import MatchResult
from app.notification.models import Notification
from app.operation_log.models import OperationLog
from app.user.models import User
from app.user.schemas import (
    CertificationRequest,
    CurrentUser,
    LoginRequest,
    RegisterRequest,
    SmsCodeRequest,
    UpdateProfileRequest,
)
from app.user.service import UserService, _sms_codes, _sms_sent_at
from sqlalchemy import select


@pytest.fixture(autouse=True)
def _enable_debug_sms(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "SMS_DEBUG_ENABLED", True)
    monkeypatch.setattr(
        settings,
        "SMS_DEMO_PHONES",
        ",".join(
            {
                "13900139100",
                "13900139101",
                "13900139102",
                "13900139103",
                "13900139104",
                "13900139105",
                "13900139000",
                "13900139009",
                "13900139001",
                "13900139002",
                "13800001234",
                "13800001235",
                "13800004321",
                "13800004322",
            }
        ),
    )
    _sms_codes.clear()
    _sms_sent_at.clear()
    yield
    _sms_codes.clear()
    _sms_sent_at.clear()


async def _register_user(svc: UserService, phone: str, password: str = "secret123"):
    sms = await svc.send_sms_code(SmsCodeRequest(phone=phone))
    assert sms.debug_code is not None
    return await svc.register(
        RegisterRequest(
            phone=phone,
            code=sms.debug_code,
            password=password,
            nickname=f"用户{phone[-4:]}",
        )
    )


class TestUserServiceLogin:
    async def test_sms_code_is_random_and_six_digits(self, session, monkeypatch):
        svc = UserService(session)
        values = iter((7, 42))
        monkeypatch.setattr("app.user.service.secrets.randbelow", lambda _: next(values))
        monkeypatch.setattr(settings, "SMS_CODE_COOLDOWN_SECONDS", 0)

        first = await svc.send_sms_code(SmsCodeRequest(phone="13900139100"))
        second = await svc.send_sms_code(SmsCodeRequest(phone="13900139100"))

        assert first.debug_code == "000007"
        assert second.debug_code == "000042"

    async def test_sms_debug_code_requires_debug_and_explicit_opt_in(self, session, monkeypatch):
        svc = UserService(session)
        monkeypatch.setattr(settings, "SMS_DEBUG_ENABLED", False)
        with pytest.raises(BizError) as disabled:
            await svc.send_sms_code(SmsCodeRequest(phone="13900139101"))
        assert disabled.value.code == ErrorCode.SMS_SERVICE_UNAVAILABLE

        monkeypatch.setattr(settings, "SMS_DEBUG_ENABLED", True)
        monkeypatch.setattr(settings, "DEBUG", False)
        with pytest.raises(BizError) as non_debug:
            await svc.send_sms_code(SmsCodeRequest(phone="13900139101"))
        assert non_debug.value.code == ErrorCode.SMS_SERVICE_UNAVAILABLE
        assert "13900139101" not in _sms_codes

    async def test_non_allowlisted_number_requires_real_sender(self, session, monkeypatch):
        monkeypatch.setattr(settings, "SMS_DEMO_PHONES", "13900139100")
        with pytest.raises(BizError) as exc_info:
            await UserService(session).send_sms_code(SmsCodeRequest(phone="13700000000"))
        assert exc_info.value.code == ErrorCode.SMS_SERVICE_UNAVAILABLE
        assert "13700000000" not in _sms_codes

    async def test_real_sender_sends_before_code_is_stored(self, session, monkeypatch):
        sent: list[tuple[str, str]] = []

        async def sender(phone: str, code: str) -> None:
            sent.append((phone, code))

        monkeypatch.setattr(settings, "DEBUG", False)
        response = await UserService(session, sms_sender=sender).send_sms_code(
            SmsCodeRequest(phone="13700000001")
        )
        assert response.debug_code is None
        assert sent and sent[0][0] == "13700000001"
        assert _sms_codes["13700000001"][0] == sent[0][1]

    async def test_sms_code_send_cooldown(self, session):
        svc = UserService(session)
        phone = "13900139102"
        await svc.send_sms_code(SmsCodeRequest(phone=phone))

        with pytest.raises(BizError) as exc_info:
            await svc.send_sms_code(SmsCodeRequest(phone=phone))

        assert exc_info.value.code == ErrorCode.DUPLICATE_SUBMIT

    async def test_expired_sms_code_is_rejected_and_removed(self, session):
        svc = UserService(session)
        phone = "13900139103"
        sms = await svc.send_sms_code(SmsCodeRequest(phone=phone))
        assert sms.debug_code is not None
        _sms_codes[phone] = (sms.debug_code, datetime.now(UTC) - timedelta(seconds=1))

        with pytest.raises(BizError) as exc_info:
            svc._validate_sms_code(phone, sms.debug_code)

        assert exc_info.value.code == ErrorCode.SMS_CODE_INVALID
        assert phone not in _sms_codes

    async def test_successful_registration_consumes_sms_code(self, session):
        svc = UserService(session)
        phone = "13900139104"
        sms = await svc.send_sms_code(SmsCodeRequest(phone=phone))
        assert sms.debug_code is not None
        await svc.register(
            RegisterRequest(
                phone=phone,
                code=sms.debug_code,
                password="secret123",
                nickname="一次性验证码",
            )
        )

        with pytest.raises(BizError) as cooldown_exc:
            await svc.send_sms_code(SmsCodeRequest(phone=phone))
        assert cooldown_exc.value.code == ErrorCode.DUPLICATE_SUBMIT

        with pytest.raises(BizError) as exc_info:
            await svc.login(LoginRequest(loginType="PHONE_CODE", phone=phone, code=sms.debug_code))

        assert exc_info.value.code == ErrorCode.SMS_CODE_INVALID

    async def test_failed_login_does_not_consume_valid_sms_code(self, session):
        svc = UserService(session)
        phone = "13900139105"
        sms = await svc.send_sms_code(SmsCodeRequest(phone=phone))
        assert sms.debug_code is not None

        with pytest.raises(BizError) as exc_info:
            await svc.login(LoginRequest(loginType="PHONE_CODE", phone=phone, code=sms.debug_code))

        assert exc_info.value.code == ErrorCode.UNAUTHORIZED
        assert phone in _sms_codes

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

    async def test_avatar_requires_owned_asset_ref(self, session):
        svc = UserService(session)
        login_resp = await _register_user(svc, "13800001235")
        current = CurrentUser(id=login_resp.user.id, role="USER", status="ACTIVE")

        with pytest.raises(BizError) as external:
            await svc.update_profile(
                current,
                UpdateProfileRequest(avatarRef="https://example.com/avatar.jpg"),
            )
        assert external.value.code == ErrorCode.PARAM_ERROR

        avatar_ref = f"asset://USER/{current.id}/202607/{'e' * 32}.webp"
        profile = await svc.update_profile(
            current,
            UpdateProfileRequest(avatarRef=avatar_ref),
        )
        assert profile.avatar_ref == avatar_ref
        assert profile.avatar_url is not None
        assert profile.avatar_url.startswith("https://signed.test/")


class TestUserServiceCertification:
    async def test_submit_certification(self, session):
        svc = UserService(session)
        login_resp = await _register_user(svc, "13800004321")

        current = CurrentUser(id=login_resp.user.id, role="USER", status="ACTIVE")
        document_ref = f"asset://CERT/{current.id}/202607/{'c' * 32}.jpg"
        cert = await svc.submit_certification(
            current,
            CertificationRequest(
                campusId="S20260002",
                realName="Test User",
                documentImageRef=document_ref,
            ),
        )
        assert cert.review_status == "PENDING"
        assert cert.document_image_ref == document_ref
        assert cert.document_image_url.startswith("https://signed.test/")

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

    async def test_cancel_account_closes_items_matches_and_pending_jobs(self, session):
        svc = UserService(session)
        login_resp = await _register_user(svc, "13800004322")
        current = CurrentUser(id=login_resp.user.id, role="USER", status="ACTIVE")
        other_user = User(
            id=generate_ulid(),
            phone="13800004323",
            password_hash="",
            nickname="other",
            role="USER",
            cert_status="UNVERIFIED",
            credit_score=100,
            status="ACTIVE",
        )
        owned_lost = LostItem(
            id=generate_ulid(),
            user_id=current.id,
            item_name="Owned lost",
            category="OTHER",
            lost_time_start=datetime(2026, 7, 11, 8),
            lost_time_end=datetime(2026, 7, 11, 9),
            lost_location="A",
            status="SEARCHING",
            review_status="APPROVED",
        )
        other_lost = LostItem(
            id=generate_ulid(),
            user_id=other_user.id,
            item_name="Other lost",
            category="OTHER",
            lost_time_start=datetime(2026, 7, 11, 8),
            lost_time_end=datetime(2026, 7, 11, 9),
            lost_location="A",
            status="SEARCHING",
            review_status="APPROVED",
        )
        owned_found = FoundItem(
            id=generate_ulid(),
            user_id=current.id,
            item_name="Owned found",
            category="OTHER",
            found_time=datetime(2026, 7, 11, 10),
            found_location="A",
            is_sensitive=0,
            custody_type="SELF",
            contact_preference="IN_APP",
            status="PENDING",
            review_status="APPROVED",
        )
        other_found = FoundItem(
            id=generate_ulid(),
            user_id=other_user.id,
            item_name="Other found",
            category="OTHER",
            found_time=datetime(2026, 7, 11, 10),
            found_location="A",
            is_sensitive=0,
            custody_type="SELF",
            contact_preference="IN_APP",
            status="PENDING",
            review_status="APPROVED",
        )
        matches = [
            MatchResult(
                id=generate_ulid(),
                lost_item_id=owned_lost.id,
                found_item_id=other_found.id,
                match_status="NEW",
            ),
            MatchResult(
                id=generate_ulid(),
                lost_item_id=other_lost.id,
                found_item_id=owned_found.id,
                match_status="READ",
            ),
        ]
        jobs = [
            DurableJob(
                id=generate_ulid(),
                job_type="MATCH",
                biz_type="LOST",
                biz_id=owned_lost.id,
                biz_version=1,
                status="PENDING",
                attempts=0,
                run_after=datetime.now(UTC).replace(tzinfo=None),
            ),
            DurableJob(
                id=generate_ulid(),
                job_type="MATCH",
                biz_type="FOUND",
                biz_id=owned_found.id,
                biz_version=1,
                status="PENDING",
                attempts=0,
                run_after=datetime.now(UTC).replace(tzinfo=None),
            ),
        ]
        session.add_all(
            [other_user, owned_lost, other_lost, owned_found, other_found, *matches, *jobs]
        )
        await session.commit()

        response = await svc.cancel_account(current)

        assert response["status"] == "CANCELLED"
        assert owned_lost.status == "CLOSED"
        assert owned_found.status == "CLOSED"
        for match in matches:
            await session.refresh(match)
            assert match.match_status == "EXPIRED"
        for job in jobs:
            await session.refresh(job)
            assert job.status == "FAILED"
            assert job.last_error == "cancelled: publisher account cancelled"
        notices = list(
            (
                await session.execute(
                    select(Notification).where(Notification.user_id == other_user.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(notices) == 1
        assert notices[0].notice_type == "MATCH_RECOMMEND"
        log = (
            await session.execute(
                select(OperationLog).where(
                    OperationLog.biz_type == "USER",
                    OperationLog.biz_id == current.id,
                )
            )
        ).scalar_one()
        assert "关闭失物 1 条、招领 1 条" in (log.detail or "")
