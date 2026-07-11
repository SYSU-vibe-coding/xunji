from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from app.common.errors import BizError, ErrorCode
from app.core import bootstrap
from app.core.config import Settings, settings
from app.core.security import hash_password, verify_password
from app.db.ulid import generate_ulid
from app.user.models import User, UserCertRequest
from app.user.repository import UserRepository
from app.user.service import UserService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _use_test_session(monkeypatch, session: AsyncSession) -> None:
    @asynccontextmanager
    async def session_factory() -> AsyncIterator[AsyncSession]:
        yield session

    monkeypatch.setattr(bootstrap, "async_session_factory", session_factory)


def _user(*, phone: str, nickname: str, role: str = "USER") -> User:
    return User(
        id=generate_ulid(),
        phone=phone,
        password_hash=hash_password("existing-password"),
        nickname=nickname,
        role=role,
        cert_status="UNVERIFIED",
        credit_score=88,
        status="DISABLED",
    )


class TestPasswordSecurity:
    def test_password_hash_round_trip(self):
        stored_hash = hash_password("secret123")
        assert verify_password("secret123", stored_hash)
        assert not verify_password("wrong-password", stored_hash)

    def test_plaintext_password_is_never_accepted(self):
        assert not verify_password("secret123", "secret123")
        assert not verify_password("", "")


class TestSmsConfiguration:
    def test_sms_debug_is_disabled_by_default(self):
        assert Settings.model_fields["SMS_DEBUG_ENABLED"].default is False

    def test_sms_demo_allowlist_is_empty_by_default(self):
        assert Settings.model_fields["SMS_DEMO_PHONES"].default == ""


class TestRuntimeSecurity:
    def test_insecure_defaults_are_rejected_outside_debug(self):
        configured = Settings(_env_file=None, DEBUG=False)
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY, ADMIN_PASSWORD"):
            configured.validate_startup_security()

    def test_explicit_local_debug_allows_defaults_but_never_cors_wildcard(self):
        Settings(_env_file=None, DEBUG=True).validate_startup_security()
        configured = Settings(
            _env_file=None,
            DEBUG=True,
            CORS_ALLOWED_ORIGINS="*",
        )
        with pytest.raises(RuntimeError, match="explicit origin allowlist"):
            configured.validate_startup_security()

    def test_bootstrap_admin_is_disabled_by_default(self):
        assert Settings.model_fields["BOOTSTRAP_ADMIN_ENABLED"].default is False


class TestAdminBootstrap:
    async def test_disabled_bootstrap_creates_nothing(self, session: AsyncSession, monkeypatch):
        monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_ENABLED", False)
        monkeypatch.setattr(settings, "ADMIN_PHONE", "19900000100")
        _use_test_session(monkeypatch, session)

        await bootstrap.ensure_default_admin()

        result = await session.execute(select(User).where(User.phone == "19900000100"))
        assert result.scalar_one_or_none() is None

    async def test_creates_admin_without_promoting_same_nickname(
        self, session: AsyncSession, monkeypatch
    ):
        monkeypatch.setattr(settings, "ADMIN_ACCOUNT", "admin-alias")
        monkeypatch.setattr(settings, "ADMIN_PHONE", "19900000101")
        monkeypatch.setattr(settings, "ADMIN_PASSWORD", "bootstrap-password")
        monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_ENABLED", True)
        _use_test_session(monkeypatch, session)
        ordinary_user = _user(phone="13900000101", nickname="admin-alias")
        original_hash = ordinary_user.password_hash
        session.add(ordinary_user)
        await session.commit()

        await bootstrap.ensure_default_admin()

        result = await session.execute(select(User).where(User.phone == "19900000101"))
        admin = result.scalar_one()
        assert admin.role == "ADMIN"
        assert verify_password("bootstrap-password", admin.password_hash)
        assert ordinary_user.role == "USER"
        assert ordinary_user.status == "DISABLED"
        assert ordinary_user.password_hash == original_hash

    async def test_existing_admin_is_never_modified(self, session: AsyncSession, monkeypatch):
        monkeypatch.setattr(settings, "ADMIN_ACCOUNT", "configured-alias")
        monkeypatch.setattr(settings, "ADMIN_PHONE", "19900000102")
        monkeypatch.setattr(settings, "ADMIN_PASSWORD", "new-password")
        monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_ENABLED", True)
        _use_test_session(monkeypatch, session)
        admin = _user(phone="19900000102", nickname="custom-name", role="ADMIN")
        original_hash = admin.password_hash
        session.add(admin)
        await session.commit()

        await bootstrap.ensure_default_admin()

        assert admin.nickname == "custom-name"
        assert admin.password_hash == original_hash
        assert admin.role == "ADMIN"
        assert admin.cert_status == "UNVERIFIED"
        assert admin.credit_score == 88
        assert admin.status == "DISABLED"

    async def test_configured_phone_conflict_is_rejected(self, session: AsyncSession, monkeypatch):
        monkeypatch.setattr(settings, "ADMIN_PHONE", "19900000103")
        monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_ENABLED", True)
        _use_test_session(monkeypatch, session)
        ordinary_user = _user(phone="19900000103", nickname="ordinary-user")
        original_hash = ordinary_user.password_hash
        session.add(ordinary_user)
        await session.commit()

        with pytest.raises(RuntimeError, match="non-admin"):
            await bootstrap.ensure_default_admin()

        assert ordinary_user.role == "USER"
        assert ordinary_user.status == "DISABLED"
        assert ordinary_user.password_hash == original_hash


class TestAdminAccountLookup:
    async def test_account_alias_only_resolves_configured_admin_phone(
        self, session: AsyncSession, monkeypatch
    ):
        monkeypatch.setattr(settings, "ADMIN_ACCOUNT", "admin-alias")
        monkeypatch.setattr(settings, "ADMIN_PHONE", "19900000104")
        nickname_collision = _user(phone="13900000104", nickname="admin-alias")
        session.add(nickname_collision)
        await session.commit()
        repo = UserRepository(session)

        assert await repo.get_by_account("admin-alias") is None
        assert await repo.get_by_account("ordinary-user") is None

        admin = _user(phone="19900000104", nickname="renamed-admin", role="ADMIN")
        session.add(admin)
        await session.commit()

        assert await repo.get_by_account("admin-alias") is admin


async def test_stale_certification_cannot_overwrite_latest_request(
    session: AsyncSession,
) -> None:
    user = _user(phone="13900000105", nickname="cert-user")
    user.cert_status = "PENDING"
    older = UserCertRequest(
        id="01CERTREQUEST00000000000001",
        user_id=user.id,
        campus_id="20260001",
        document_image_url="asset://CERT/user/old.jpg",
        review_status="PENDING",
    )
    latest = UserCertRequest(
        id="01CERTREQUEST00000000000002",
        user_id=user.id,
        campus_id="20260002",
        document_image_url="asset://CERT/user/new.jpg",
        review_status="PENDING",
    )
    session.add_all([user, older, latest])
    await session.commit()

    with pytest.raises(BizError) as exc_info:
        await UserService(session).review_certification_internal(
            older.id, "APPROVE", None, "01TESTADMIN00000000000001"
        )

    assert exc_info.value.code == ErrorCode.REVIEW_STATE_CHANGED
    assert user.cert_status == "PENDING"
    assert older.review_status == "PENDING"
