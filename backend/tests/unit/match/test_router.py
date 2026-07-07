from datetime import datetime
from decimal import Decimal
from typing import Any

from app.db.ulid import generate_ulid
from app.item.models import FoundItem, ItemImage, LostItem
from app.match.models import MatchResult
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def _lost_item(session: AsyncSession, *, user_id: str, name: str = "Black Wallet") -> LostItem:
    now = datetime(2026, 4, 30, 9, 0, 0)
    item = LostItem(
        id=generate_ulid(),
        user_id=user_id,
        item_name=name,
        category="DAILY_USE",
        description="wallet with card",
        lost_time_start=now,
        lost_time_end=datetime(2026, 4, 30, 11, 0, 0),
        lost_location="Library",
        subscribe_match=1,
        status="SEARCHING",
        review_status="APPROVED",
        created_at=now,
        updated_at=now,
    )
    session.add(item)
    return item


def _found_item(
    session: AsyncSession,
    *,
    user_id: str,
    name: str = "Black Wallet",
    status: str = "PENDING",
) -> FoundItem:
    now = datetime(2026, 4, 30, 10, 0, 0)
    item = FoundItem(
        id=generate_ulid(),
        user_id=user_id,
        item_name=name,
        category="DAILY_USE",
        description="wallet with card",
        found_time=now,
        found_location="Library front desk",
        is_sensitive=0,
        custody_type="SECURITY",
        contact_preference="IN_APP",
        status=status,
        review_status="APPROVED",
        created_at=now,
        updated_at=now,
    )
    session.add(item)
    return item


def _match(
    session: AsyncSession,
    *,
    lost_id: str,
    found_id: str,
    total_score: str = "88.50",
    status: str = "NEW",
) -> MatchResult:
    match = MatchResult(
        id=generate_ulid(),
        lost_item_id=lost_id,
        found_item_id=found_id,
        image_score=Decimal("80.00"),
        text_score=Decimal("90.00"),
        location_score=Decimal("95.00"),
        time_score=Decimal("75.00"),
        total_score=Decimal(total_score),
        match_status=status,
        created_at=datetime(2026, 4, 30, 12, 0, 0),
    )
    session.add(match)
    return match


def _image(session: AsyncSession, *, biz_type: str, biz_id: str, url: str) -> None:
    session.add(
        ItemImage(
            id=generate_ulid(),
            biz_type=biz_type,
            biz_id=biz_id,
            image_url=url,
            sort_order=0,
            created_at=datetime(2026, 4, 30, 12, 0, 0),
        )
    )


async def _seed_owned_match(session: AsyncSession) -> tuple[LostItem, FoundItem, MatchResult]:
    lost = _lost_item(session, user_id="01TESTUSER000000000000001")
    found = _found_item(session, user_id="01TESTSTAFF00000000000001")
    match = _match(session, lost_id=lost.id, found_id=found.id)
    _image(session, biz_type="FOUND", biz_id=found.id, url="https://cdn/found.jpg")
    _image(session, biz_type="LOST", biz_id=lost.id, url="https://cdn/lost.jpg")
    await session.commit()
    return lost, found, match


async def test_list_matches_filters_and_uses_camel_case(
    client: AsyncClient,
    session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    lost, found, match = await _seed_owned_match(session)
    low_found = _found_item(session, user_id="01TESTSTAFF00000000000001", name="Blue Bottle")
    _match(
        session,
        lost_id=lost.id,
        found_id=low_found.id,
        total_score="62.00",
        status="READ",
    )
    await session.commit()

    resp = await client.get(
        "/api/v1/matches",
        params={
            "bizType": "lost",
            "bizId": lost.id,
            "minScore": 70,
            "status": "NEW",
            "pageNo": 1,
            "pageSize": 10,
        },
        headers=auth_headers,
    )

    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    item = body["data"]["list"][0]
    assert item["matchId"] == match.id
    assert item["lostItemId"] == lost.id
    assert item["foundItemId"] == found.id
    assert item["matchStatus"] == "NEW"
    assert item["totalScore"] == 88.5
    assert item["counterpart"]["id"] == found.id
    assert item["counterpart"]["itemName"] == "Black Wallet"
    assert item["counterpart"]["category"] == "DAILY_USE"
    assert item["counterpart"]["coverImageUrl"] == "https://cdn/found.jpg"
    assert item["counterpart"]["location"] == "Library front desk"
    assert "time" in item["counterpart"]


async def test_get_match_detail_returns_parties_and_can_claim(
    client: AsyncClient,
    session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    lost, found, match = await _seed_owned_match(session)

    resp = await client.get(f"/api/v1/matches/{match.id}", headers=auth_headers)

    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["matchId"] == match.id
    assert data["lostItem"]["id"] == lost.id
    assert data["foundItem"]["id"] == found.id
    assert data["canClaim"] is True


async def test_recalculate_invokes_trigger_match(
    client: AsyncClient,
    session: AsyncSession,
    auth_headers: dict[str, str],
    monkeypatch: Any,
) -> None:
    lost = _lost_item(session, user_id="01TESTUSER000000000000001")
    await session.commit()
    calls: list[tuple[str, str]] = []

    async def fake_trigger_match(biz_type: str, item_id: str, **_: Any) -> int:
        calls.append((biz_type, item_id))
        return 3

    monkeypatch.setattr("app.match.service.trigger_match", fake_trigger_match)

    resp = await client.post(
        "/api/v1/matches/recalculate",
        json={"bizType": "LOST", "bizId": lost.id},
        headers=auth_headers,
    )

    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["estimatedCount"] == 3
    assert body["data"]["status"] == "COMPLETED"
    assert len(body["data"]["taskId"]) == 26
    assert calls == [("LOST", lost.id)]


async def test_matches_require_auth(client: AsyncClient, session: AsyncSession) -> None:
    lost, _, _ = await _seed_owned_match(session)

    resp = await client.get(
        "/api/v1/matches",
        params={"bizType": "LOST", "bizId": lost.id},
    )

    assert resp.json()["code"] == 40002


async def test_get_match_not_found(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.get(
        "/api/v1/matches/01ARZ3NDEKTSV4RRFFQ69G5FAV",
        headers=auth_headers,
    )

    assert resp.json()["code"] == 43001


async def test_non_party_cannot_access_detail(
    client: AsyncClient,
    session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    lost = _lost_item(session, user_id="01TESTSTAFF00000000000001")
    found = _found_item(session, user_id="01TESTADMIN00000000000001")
    match = _match(session, lost_id=lost.id, found_id=found.id)
    await session.commit()

    resp = await client.get(f"/api/v1/matches/{match.id}", headers=auth_headers)

    assert resp.json()["code"] == 40003


async def test_invalid_biz_id_returns_param_error(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.get(
        "/api/v1/matches",
        params={"bizType": "LOST", "bizId": "not-a-ulid"},
        headers=auth_headers,
    )

    assert resp.json()["code"] == 40001
