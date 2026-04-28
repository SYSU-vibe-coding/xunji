from app.user.models import User
from httpx import AsyncClient
from sqlalchemy import select


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
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/users/me/certification",
            json={
                "campusId": "S20260001",
                "realName": "Test User",
                "documentImageUrl": "https://example.com/cert.jpg",
            },
            headers=headers,
        )
        body = resp.json()
        assert body["code"] == 0
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
