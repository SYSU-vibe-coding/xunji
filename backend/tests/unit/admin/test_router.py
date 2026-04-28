from httpx import AsyncClient


async def test_admin_requires_admin_role(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.get("/api/v1/admin/dashboard", headers=auth_headers)
    assert resp.json()["code"] == 48002


async def test_admin_dashboard(client: AsyncClient, admin_headers: dict[str, str]):
    resp = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    assert "totalUsers" in body["data"]
