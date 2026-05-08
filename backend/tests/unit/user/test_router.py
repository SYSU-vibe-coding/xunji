from httpx import AsyncClient


class TestAuthRoutes:
    async def test_sms_code_and_login_auto_register(self, client: AsyncClient):
        code_resp = await client.post(
            "/api/v1/auth/sms-code",
            json={"phone": "13800000001"},
        )
        code = code_resp.json()["data"]["debugCode"]

        resp = await client.post(
            "/api/v1/auth/login",
            json={"loginType": "PHONE_CODE", "phone": "13800000001", "code": code},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert "token" in body["data"]
        assert body["data"]["user"]["role"] == "USER"

    async def test_unauthorized_access(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 40002  # UNAUTHORIZED


class TestUserProfileRoutes:
    async def test_get_profile(self, client: AsyncClient):
        code_resp = await client.post(
            "/api/v1/auth/sms-code",
            json={"phone": "13800000003"},
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "loginType": "PHONE_CODE",
                "phone": "13800000003",
                "code": code_resp.json()["data"]["debugCode"],
            },
        )
        token = login_resp.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/users/me", headers=headers)
        body = resp.json()
        assert body["code"] == 0
        assert "****" in body["data"]["phone"]

    async def test_update_profile(self, client: AsyncClient):
        code_resp = await client.post(
            "/api/v1/auth/sms-code",
            json={"phone": "13800000004"},
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "loginType": "PHONE_CODE",
                "phone": "13800000004",
                "code": code_resp.json()["data"]["debugCode"],
            },
        )
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
        code_resp = await client.post(
            "/api/v1/auth/sms-code",
            json={"phone": "13800000005"},
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "loginType": "PHONE_CODE",
                "phone": "13800000005",
                "code": code_resp.json()["data"]["debugCode"],
            },
        )
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
