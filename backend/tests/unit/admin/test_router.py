from datetime import datetime, timedelta

from app.claim.models import ClaimRequest, HandoverRecord
from app.db.ulid import generate_ulid
from app.item.models import FoundItem
from app.operation_log.models import OperationLog
from app.user.models import UserCertRequest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def test_admin_requires_admin_role(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.get("/api/v1/admin/dashboard", headers=auth_headers)
    assert resp.json()["code"] == 48002


async def test_admin_dashboard(client: AsyncClient, admin_headers: dict[str, str]):
    resp = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    assert "totalUsers" in body["data"]


async def test_admin_dashboard_uses_real_handover_stats(
    client: AsyncClient, admin_headers: dict[str, str], session: AsyncSession
):
    created_at = datetime(2026, 5, 1, 8, 0, 0)
    completed_at = created_at + timedelta(hours=6)
    session.add(
        FoundItem(
            id="01FOUNDDASHBOARD0000000001",
            user_id="01TESTUSER000000000000001",
            item_name="雨伞",
            category="DAILY_USE",
            description="黑色长柄伞",
            found_time=created_at,
            found_location="图书馆",
            is_sensitive=0,
            custody_type="SELF",
            contact_preference="IN_APP",
            status="RETURNED",
            review_status="APPROVED",
            created_at=created_at,
        )
    )
    session.add(
        ClaimRequest(
            id="01CLAIMDASHBOARD000000001",
            match_id=None,
            found_item_id="01FOUNDDASHBOARD0000000001",
            claimant_id="01TESTSTAFF00000000000001",
            verify_level="LEVEL_1",
            review_status="HANDED_OVER",
            claimed_at=created_at + timedelta(hours=1),
        )
    )
    session.add(
        HandoverRecord(
            id="01HANDOVERDASHBOARD000001",
            claim_id="01CLAIMDASHBOARD000000001",
            method="MEETUP",
            handover_location="图书馆一楼",
            handover_time=created_at + timedelta(hours=5),
            owner_confirmed=1,
            finder_confirmed=1,
            completed_at=completed_at,
            created_at=created_at + timedelta(hours=2),
        )
    )
    await session.commit()

    resp = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["totalFound"] == 1
    assert body["data"]["handedOverCount"] == 1
    assert body["data"]["recoveryRate"] == 100
    assert body["data"]["avgHandleHours"] == 6


async def test_admin_certification_review_writes_operation_log(
    client: AsyncClient, admin_headers: dict[str, str], session: AsyncSession
):
    cert_id = generate_ulid()
    session.add(
        UserCertRequest(
            id=cert_id,
            user_id="01TESTUSER000000000000001",
            campus_id="20260001",
            document_image_url="https://example.test/cert.jpg",
            review_status="PENDING",
        )
    )
    await session.commit()

    resp = await client.post(
        f"/api/v1/admin/certifications/{cert_id}/review",
        headers=admin_headers,
        json={"action": "APPROVE"},
    )
    body = resp.json()

    assert body["code"] == 0
    result = await session.execute(
        select(OperationLog).where(
            OperationLog.biz_type == "CERT",
            OperationLog.biz_id == cert_id,
            OperationLog.action == "CERT_APPROVE",
            OperationLog.operator_id == "01TESTADMIN00000000000001",
        )
    )
    assert result.scalar_one_or_none() is not None
