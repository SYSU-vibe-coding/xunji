import pytest
from app.core.config import settings
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def _enable_debug_sms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "SMS_DEBUG_ENABLED", True)
    monkeypatch.setattr(
        settings,
        "SMS_DEMO_PHONES",
        ",".join(f"139000000{suffix:02d}" for suffix in range(10, 24)),
    )


async def _login_and_get_headers(client: AsyncClient, phone: str) -> dict[str, str]:
    """Helper: register, login, and return auth headers."""
    code_resp = await client.post(
        "/api/v1/auth/sms-code",
        json={"phone": phone},
    )
    await client.post(
        "/api/v1/auth/register",
        json={
            "phone": phone,
            "code": code_resp.json()["data"]["debugCode"],
            "password": "secret123",
            "nickname": f"用户{phone[-4:]}",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "loginType": "PASSWORD",
            "phone": phone,
            "password": "secret123",
        },
    )
    token = resp.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


class TestLostItemRoutes:
    async def test_create_lost_item(self, client: AsyncClient):
        headers = await _login_and_get_headers(client, "13900000010")
        resp = await client.post(
            "/api/v1/lost-items",
            json={
                "itemName": "Laptop",
                "category": "ELECTRONIC",
                "lostTimeStart": "2026-04-20 10:00:00",
                "lostTimeEnd": "2026-04-20 12:00:00",
                "lostLocation": "Library",
            },
            headers=headers,
        )
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["status"] == "SEARCHING"

    async def test_list_lost_items(self, client: AsyncClient):
        headers = await _login_and_get_headers(client, "13900000011")
        resp = await client.get("/api/v1/lost-items", headers=headers)
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["total"] >= 0

    async def test_get_lost_item_not_found(self, client: AsyncClient):
        headers = await _login_and_get_headers(client, "13900000012")
        resp = await client.get("/api/v1/lost-items/01ARZ3NDEKTSV4RRFFQ69G5FAV", headers=headers)
        body = resp.json()
        assert body["code"] == 42001


class TestFoundItemRoutes:
    async def test_batch_create_found_items_requires_staff(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        staff_headers: dict[str, str],
    ):
        payload = {
            "items": [
                {
                    "itemName": "Batch Umbrella",
                    "category": "DAILY_USE",
                    "foundTime": "2026-04-20 14:00:00",
                    "foundLocation": "Gate",
                    "custodyType": "SELF",
                    "contactPreference": "IN_APP",
                }
            ]
        }

        forbidden = await client.post(
            "/api/v1/found-items/batch", json=payload, headers=auth_headers
        )
        assert forbidden.json()["code"] == 40003

        ok = await client.post("/api/v1/found-items/batch", json=payload, headers=staff_headers)
        body = ok.json()
        assert body["code"] == 0
        assert len(body["data"]["successIds"]) == 1
        assert body["data"]["failures"] == []

    async def test_invalid_item_ulid(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.get("/api/v1/found-items/not-a-ulid", headers=auth_headers)
        assert resp.json()["code"] == 40001

    async def test_create_found_item(self, client: AsyncClient):
        headers = await _login_and_get_headers(client, "13900000020")
        resp = await client.post(
            "/api/v1/found-items",
            json={
                "itemName": "Campus Card",
                "category": "CERT",
                "foundTime": "2026-04-20 14:00:00",
                "foundLocation": "Gate",
                "custodyType": "SELF",
                "contactPreference": "IN_APP",
            },
            headers=headers,
        )
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["status"] == "PENDING"
        assert body["data"]["isSensitive"] is True

    async def test_change_status_unauthorized(self, client: AsyncClient):
        headers_a = await _login_and_get_headers(client, "13900000021")
        create_resp = await client.post(
            "/api/v1/found-items",
            json={
                "itemName": "Pen",
                "category": "DAILY_USE",
                "foundTime": "2026-04-21 10:00:00",
                "foundLocation": "Classroom",
                "custodyType": "SELF",
                "contactPreference": "IN_APP",
            },
            headers=headers_a,
        )
        item_id = create_resp.json()["data"]["id"]

        headers_b = await _login_and_get_headers(client, "13900000022")
        resp = await client.patch(
            f"/api/v1/found-items/{item_id}/status",
            json={"status": "CLOSED"},
            headers=headers_b,
        )
        body = resp.json()
        assert body["code"] == 42004  # NOT_PUBLISHER
