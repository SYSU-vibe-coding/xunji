import pytest
from app.common.errors import ErrorCode
from app.core.config import settings
from app.user.models import User
from app.user.service import _sms_codes, _sms_sent_at
from httpx import AsyncClient
from sqlalchemy import select


@pytest.fixture(autouse=True)
def _enable_debug_sms(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "SMS_DEBUG_ENABLED", True)
    monkeypatch.setattr(
        settings,
        "SMS_DEMO_PHONES",
        ",".join(f"1380000000{suffix}" for suffix in range(1, 10)),
    )
    _sms_codes.clear()
    _sms_sent_at.clear()
    yield
    _sms_codes.clear()
    _sms_sent_at.clear()


async def _register_and_login(client: AsyncClient, phone: str, password: str = "secret123"):
    code_resp = await client.post(
        "/api/v1/auth/sms-code",
        json={"phone": phone},
    )
    await client.post(
        "/api/v1/auth/register",
        json={
            "phone": phone,
            "code": code_resp.json()["data"]["debugCode"],
            "password": password,
            "nickname": f"用户{phone[-4:]}",
        },
    )
    return await client.post(
        "/api/v1/auth/login",
        json={"loginType": "PASSWORD", "phone": phone, "password": password},
    )


class TestAuthRoutes:
    async def test_sms_without_demo_mode_returns_unavailable(
        self, client: AsyncClient, monkeypatch
    ):
        monkeypatch.setattr(settings, "SMS_DEBUG_ENABLED", False)

        resp = await client.post("/api/v1/auth/sms-code", json={"phone": "13800000008"})

        assert resp.json()["code"] == ErrorCode.SMS_SERVICE_UNAVAILABLE
        assert "13800000008" not in _sms_codes

    async def test_sms_outside_debug_environment_returns_unavailable(
        self, client: AsyncClient, monkeypatch
    ):
        monkeypatch.setattr(settings, "DEBUG", False)

        resp = await client.post("/api/v1/auth/sms-code", json={"phone": "13800000009"})

        assert resp.json()["code"] == ErrorCode.SMS_SERVICE_UNAVAILABLE
        assert "13800000009" not in _sms_codes

    async def test_register_and_password_login(self, client: AsyncClient):
        resp = await _register_and_login(client, "13800000001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert "token" in body["data"]
        assert body["data"]["user"]["role"] == "USER"

    async def test_phone_code_login_requires_existing_user(self, client: AsyncClient):
        code_resp = await client.post(
            "/api/v1/auth/sms-code",
            json={"phone": "13800000002"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "loginType": "PHONE_CODE",
                "phone": "13800000002",
                "code": code_resp.json()["data"]["debugCode"],
            },
        )
        assert resp.json()["code"] == 40002

    async def test_unauthorized_access(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 40002  # UNAUTHORIZED


class TestUserProfileRoutes:
    async def test_get_profile(self, client: AsyncClient):
        login_resp = await _register_and_login(client, "13800000003")
        token = login_resp.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/users/me", headers=headers)
        body = resp.json()
        assert body["code"] == 0
        assert "****" in body["data"]["phone"]

    async def test_update_profile(self, client: AsyncClient):
        login_resp = await _register_and_login(client, "13800000004")
        token = login_resp.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.put(
            "/api/v1/users/me",
            json={"nickname": "TestNick"},
            headers=headers,
        )
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["nickname"] == "TestNick"

    async def test_submit_and_get_certification(self, client: AsyncClient):
        login_resp = await _register_and_login(client, "13800000005")
        token = login_resp.json()["data"]["token"]
        user_id = login_resp.json()["data"]["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}
        document_ref = f"asset://CERT/{user_id}/202607/{'d' * 32}.jpg"

        resp = await client.post(
            "/api/v1/users/me/certification",
            json={
                "campusId": "S20260001",
                "realName": "Test User",
                "documentImageRef": document_ref,
            },
            headers=headers,
        )
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["documentImageRef"] == document_ref
        assert body["data"]["documentImageUrl"].startswith("https://signed.test/")
        assert body["data"]["reviewStatus"] == "PENDING"

        get_resp = await client.get("/api/v1/users/me/certification", headers=headers)
        assert get_resp.json()["data"]["campusId"] == "S20260001"

    async def test_cancelled_user_old_token_rejected(self, client: AsyncClient):
        login_resp = await _register_and_login(client, "13800000006")
        token = login_resp.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        cancel_resp = await client.post("/api/v1/users/me/cancel", headers=headers)
        assert cancel_resp.json()["code"] == 0

        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.json()["code"] == 41005

    async def test_disabled_user_old_token_rejected(self, client: AsyncClient, session):
        login_resp = await _register_and_login(client, "13800000007")
        user_id = login_resp.json()["data"]["user"]["id"]
        token = login_resp.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.status = "DISABLED"
        await session.commit()

        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.json()["code"] == 41005
