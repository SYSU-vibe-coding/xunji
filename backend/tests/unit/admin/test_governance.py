from datetime import datetime, timedelta

from app.admin.models import Report
from app.claim.models import ClaimRequest
from app.claim.schemas import (
    ClaimAppealRequest,
    ClaimReviewRequest,
    CreateClaimRequest,
)
from app.claim.service import ClaimService
from app.credit.models import CreditLog
from app.db.ulid import generate_ulid
from app.item.models import FoundItem, ItemImage, LostItem, VerifyQuestion
from app.item.schemas import (
    CreateFoundItemRequest,
    CreateLostItemRequest,
    SubmitReportRequest,
)
from app.item.service import ItemService
from app.match.models import MatchResult
from app.notification.models import Notification
from app.notification.repository import NotificationRepository
from app.user.models import User, UserCertRequest
from app.user.schemas import CurrentUser
from fastapi import BackgroundTasks
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

USER = CurrentUser(id="01TESTUSER000000000000001", role="USER", status="ACTIVE")
ADMIN = CurrentUser(id="01TESTADMIN00000000000001", role="ADMIN", status="ACTIVE")
STAFF = CurrentUser(id="01TESTSTAFF00000000000001", role="STAFF", status="ACTIVE")


async def _create_found(
    session: AsyncSession, owner: CurrentUser, name: str = "Governed Item"
) -> str:
    created = await ItemService(session).create_found_item(
        CreateFoundItemRequest(
            itemName=name,
            category="OTHER",
            foundTime="2026-07-10 10:00:00",
            foundLocation="Library",
            custodyType="SELF",
            contactPreference="IN_APP",
        ),
        owner,
        BackgroundTasks(),
    )
    return created.id


async def test_certification_review_is_pending_only_and_keeps_comment(
    client: AsyncClient,
    admin_headers: dict[str, str],
    session: AsyncSession,
):
    cert_id = generate_ulid()
    session.add(
        UserCertRequest(
            id=cert_id,
            user_id=USER.id,
            campus_id="20260001",
            document_image_url="https://example.test/cert.jpg",
            review_status="PENDING",
        )
    )
    await session.commit()

    first = await client.post(
        f"/api/v1/admin/certifications/{cert_id}/review",
        headers=admin_headers,
        json={"action": "APPROVE", "comment": "资料清晰, 认证通过"},
    )
    repeated = await client.post(
        f"/api/v1/admin/certifications/{cert_id}/review",
        headers=admin_headers,
        json={"action": "REJECT", "comment": "不得覆盖既有结果"},
    )

    assert first.json()["code"] == 0
    assert repeated.json()["code"] == 48001
    cert = (
        await session.execute(select(UserCertRequest).where(UserCertRequest.id == cert_id))
    ).scalar_one()
    user = (await session.execute(select(User).where(User.id == USER.id))).scalar_one()
    credit_count = (
        await session.execute(
            select(func.count())
            .select_from(CreditLog)
            .where(CreditLog.biz_id == cert_id, CreditLog.reason_code == "CERT_APPROVED")
        )
    ).scalar_one()
    notices = (
        await session.execute(
            select(Notification).where(
                Notification.user_id == USER.id,
                Notification.related_type == "CERT",
                Notification.related_id == cert_id,
            )
        )
    ).scalars().all()

    assert cert.review_status == "APPROVED"
    assert cert.review_comment == "资料清晰, 认证通过"
    assert user.credit_score == 120
    assert credit_count == 1
    assert any("资料清晰, 认证通过" in (notice.content or "") for notice in notices)


async def test_content_review_is_pending_only_and_mixed_pagination_is_global(
    client: AsyncClient,
    admin_headers: dict[str, str],
    session: AsyncSession,
):
    base = datetime(2026, 7, 1, 8, 0, 0)
    lost_ids = [generate_ulid(), generate_ulid()]
    found_ids = [generate_ulid(), generate_ulid()]
    exact_user_id = generate_ulid()
    session.add_all(
        [
            User(
                id=exact_user_id,
                phone="13810000999",
                password_hash="",
                nickname="Exact user",
                role="USER",
                cert_status="UNVERIFIED",
                credit_score=100,
                status="ACTIVE",
            ),
            LostItem(
                id=lost_ids[0],
                user_id=USER.id,
                item_name="Lost old",
                category="OTHER",
                lost_time_start=base,
                lost_time_end=base,
                lost_location="A",
                status="SEARCHING",
                review_status="PENDING",
                created_at=base,
            ),
            FoundItem(
                id=found_ids[0],
                user_id=STAFF.id,
                item_name="Found middle old",
                category="OTHER",
                found_time=base,
                found_location="B",
                is_sensitive=0,
                custody_type="SELF",
                contact_preference="IN_APP",
                status="PENDING",
                review_status="APPROVED",
                created_at=base + timedelta(hours=1),
            ),
            LostItem(
                id=lost_ids[1],
                user_id=USER.id,
                item_name="Lost middle new",
                category="OTHER",
                lost_time_start=base,
                lost_time_end=base,
                lost_location="C",
                status="SEARCHING",
                review_status="APPROVED",
                created_at=base + timedelta(hours=2),
            ),
            FoundItem(
                id=found_ids[1],
                user_id=STAFF.id,
                item_name="Found newest",
                category="OTHER",
                found_time=base,
                found_location="D",
                is_sensitive=0,
                custody_type="SELF",
                contact_preference="IN_APP",
                status="PENDING",
                review_status="APPROVED",
                created_at=base + timedelta(hours=3),
            ),
        ]
    )
    await session.commit()

    reviewed = await client.post(
        f"/api/v1/admin/items/LOST/{lost_ids[0]}/review",
        headers=admin_headers,
        json={"action": "APPROVE", "comment": "内容真实"},
    )
    repeated = await client.post(
        f"/api/v1/admin/items/LOST/{lost_ids[0]}/review",
        headers=admin_headers,
        json={"action": "REJECT", "comment": "不得重复审核"},
    )
    page_one = await client.get(
        "/api/v1/admin/items/review?pageNo=1&pageSize=2", headers=admin_headers
    )
    page_two = await client.get(
        "/api/v1/admin/items/review?pageNo=2&pageSize=2", headers=admin_headers
    )
    exact = await client.get(
        f"/api/v1/admin/items/review?targetId={found_ids[0]}", headers=admin_headers
    )
    exact_user = await client.get(
        f"/api/v1/admin/users?userId={exact_user_id}", headers=admin_headers
    )

    assert reviewed.json()["code"] == 0
    assert repeated.json()["code"] == 48001
    reviewed_item = (
        await session.execute(select(LostItem).where(LostItem.id == lost_ids[0]))
    ).scalar_one()
    assert reviewed_item.review_comment == "内容真实"
    assert [item["id"] for item in page_one.json()["data"]["list"]] == [
        found_ids[1],
        lost_ids[1],
    ]
    assert [item["id"] for item in page_two.json()["data"]["list"]] == [
        found_ids[0],
        lost_ids[0],
    ]
    assert exact.json()["data"]["total"] == 1
    assert exact.json()["data"]["list"][0]["id"] == found_ids[0]
    assert exact_user.json()["data"]["total"] == 1
    assert exact_user.json()["data"]["list"][0]["id"] == exact_user_id


async def test_content_review_detail_contains_signed_media_publisher_and_questions(
    client: AsyncClient,
    admin_headers: dict[str, str],
    session: AsyncSession,
):
    found_id = generate_ulid()
    image_ref = f"asset://FOUND/{STAFF.id}/202607/{'a' * 32}.jpg"
    session.add(
        FoundItem(
            id=found_id,
            user_id=STAFF.id,
            item_name="待审核校园卡",
            category="CERT",
            description="卡面有蓝色校徽, 背面有贴纸",
            found_time=datetime(2026, 7, 10, 12, 30, 0),
            found_location="一食堂东门",
            is_sensitive=1,
            custody_type="SECURITY",
            contact_preference="IN_APP",
            status="PENDING",
            review_status="PENDING",
            review_comment="等待人工核验",
        )
    )
    session.add(
        ItemImage(
            id=generate_ulid(),
            biz_type="FOUND",
            biz_id=found_id,
            image_url=image_ref,
            sort_order=0,
        )
    )
    session.add(
        VerifyQuestion(
            id=generate_ulid(),
            found_item_id=found_id,
            question_text="卡片背面的贴纸图案是什么?",
            answer_keywords='["星星"]',
        )
    )
    await session.commit()

    response = await client.get(
        f"/api/v1/admin/items/FOUND/{found_id}", headers=admin_headers
    )
    detail = response.json()["data"]

    assert response.json()["code"] == 0
    assert detail["description"] == "卡面有蓝色校徽, 背面有贴纸"
    assert detail["foundTime"] == "2026-07-10 12:30:00"
    assert detail["publisher"]["id"] == STAFF.id
    assert detail["reviewStatus"] == "PENDING"
    assert detail["reviewComment"] == "等待人工核验"
    assert detail["imageUrls"][0].startswith("https://signed.test/")
    assert detail["verifyQuestions"][0]["questionText"] == "卡片背面的贴纸图案是什么?"
    assert "answerKeywords" not in detail["verifyQuestions"][0]


async def test_valid_found_report_forces_penalty_takedown_termination_and_notices(
    client: AsyncClient,
    admin_headers: dict[str, str],
    session: AsyncSession,
):
    found_id = await _create_found(session, USER)
    claim = await ClaimService(session).create_claim(
        CreateClaimRequest(foundItemId=found_id), STAFF
    )
    report = await ItemService(session).submit_report(
        SubmitReportRequest(
            targetType="FOUND_ITEM",
            targetId=found_id,
            reason="FAKE",
            description="虚假发布",
        ),
        ADMIN,
    )

    wrong_rule = await client.post(
        f"/api/v1/admin/reports/{report.id}/handle",
        headers=admin_headers,
        json={
            "action": "VALID",
            "result": "核实为虚假发布",
            "creditDelta": -30,
            "reasonCode": "FRAUD_CLAIM_CONFIRMED",
        },
    )
    handled = await client.post(
        f"/api/v1/admin/reports/{report.id}/handle",
        headers=admin_headers,
        json={"action": "VALID", "result": "核实为虚假发布"},
    )
    repeated = await client.post(
        f"/api/v1/admin/reports/{report.id}/handle",
        headers=admin_headers,
        json={"action": "VALID", "result": "重复处理"},
    )

    assert wrong_rule.json()["code"] == 40001
    assert handled.json()["code"] == 0
    assert repeated.json()["code"] == 48001
    found = (
        await session.execute(select(FoundItem).where(FoundItem.id == found_id))
    ).scalar_one()
    stored_claim = (
        await session.execute(select(ClaimRequest).where(ClaimRequest.id == claim.id))
    ).scalar_one()
    owner = (await session.execute(select(User).where(User.id == USER.id))).scalar_one()
    credit = (
        await session.execute(
            select(CreditLog).where(
                CreditLog.user_id == USER.id,
                CreditLog.biz_id == report.id,
            )
        )
    ).scalar_one()
    assert found.status == "CLOSED"
    assert found.review_status == "REJECTED"
    assert stored_claim.review_status == "TERMINATED"
    assert owner.credit_score == 80
    assert credit.delta_score == -20
    assert credit.reason_code == "FAKE_PUBLISH_CONFIRMED"
    for user_id in (ADMIN.id, USER.id):
        notice = (
            await session.execute(
                select(Notification).where(
                    Notification.user_id == user_id,
                    Notification.related_type == "REPORT",
                    Notification.related_id == report.id,
                    Notification.title == "举报处理结果",
                )
            )
        ).scalar_one_or_none()
        assert notice is not None


async def test_claim_report_forces_fraud_penalty_and_invalid_report_does_not_penalize(
    client: AsyncClient,
    admin_headers: dict[str, str],
    session: AsyncSession,
):
    found_id = await _create_found(session, USER, "Claim report target")
    claim = await ClaimService(session).create_claim(
        CreateClaimRequest(foundItemId=found_id), STAFF
    )
    claim_report = await ItemService(session).submit_report(
        SubmitReportRequest(
            targetType="CLAIM_REQUEST",
            targetId=claim.id,
            reason="FRAUD",
        ),
        ADMIN,
    )
    handled = await client.post(
        f"/api/v1/admin/reports/{claim_report.id}/handle",
        headers=admin_headers,
        json={"action": "VALID", "result": "认领材料造假"},
    )

    lost = await ItemService(session).create_lost_item(
        CreateLostItemRequest(
            itemName="Valid lost item",
            category="OTHER",
            lostTimeStart="2026-07-10 08:00:00",
            lostTimeEnd="2026-07-10 09:00:00",
            lostLocation="Gate",
        ),
        USER,
        BackgroundTasks(),
    )
    invalid_report = await ItemService(session).submit_report(
        SubmitReportRequest(targetType="LOST_ITEM", targetId=lost.id, reason="MISTAKE"),
        ADMIN,
    )
    rejected = await client.post(
        f"/api/v1/admin/reports/{invalid_report.id}/handle",
        headers=admin_headers,
        json={"action": "INVALID", "result": "举报不成立"},
    )

    staff = (await session.execute(select(User).where(User.id == STAFF.id))).scalar_one()
    owner = (await session.execute(select(User).where(User.id == USER.id))).scalar_one()
    stored_claim = (
        await session.execute(select(ClaimRequest).where(ClaimRequest.id == claim.id))
    ).scalar_one()
    stored_lost = (
        await session.execute(select(LostItem).where(LostItem.id == lost.id))
    ).scalar_one()
    fraud_credit = (
        await session.execute(
            select(CreditLog).where(CreditLog.biz_id == claim_report.id)
        )
    ).scalar_one()

    assert handled.json()["code"] == 0
    assert rejected.json()["code"] == 0
    assert stored_claim.review_status == "TERMINATED"
    assert staff.credit_score == 70
    assert fraud_credit.delta_score == -30
    assert fraud_credit.reason_code == "FRAUD_CLAIM_CONFIRMED"
    assert stored_lost.status == "SEARCHING"
    assert owner.credit_score == 100


async def test_valid_lost_report_terminates_match_backed_claim(
    client: AsyncClient,
    admin_headers: dict[str, str],
    session: AsyncSession,
):
    item_svc = ItemService(session)
    lost = await item_svc.create_lost_item(
        CreateLostItemRequest(
            itemName="Fake matched item",
            category="OTHER",
            lostTimeStart="2026-07-10 08:00:00",
            lostTimeEnd="2026-07-10 09:00:00",
            lostLocation="Gate",
        ),
        USER,
        BackgroundTasks(),
    )
    found_id = await _create_found(session, STAFF, "Fake matched item")
    match = MatchResult(
        id=generate_ulid(),
        lost_item_id=lost.id,
        found_item_id=found_id,
        match_status="NEW",
    )
    session.add(match)
    await session.commit()
    claim = await ClaimService(session).create_claim(
        CreateClaimRequest(foundItemId=found_id, matchId=match.id), USER
    )
    report = await item_svc.submit_report(
        SubmitReportRequest(targetType="LOST_ITEM", targetId=lost.id, reason="FAKE"),
        ADMIN,
    )

    response = await client.post(
        f"/api/v1/admin/reports/{report.id}/handle",
        headers=admin_headers,
        json={"action": "VALID", "result": "虚假寻物信息"},
    )

    stored_lost = (
        await session.execute(select(LostItem).where(LostItem.id == lost.id))
    ).scalar_one()
    stored_found = (
        await session.execute(select(FoundItem).where(FoundItem.id == found_id))
    ).scalar_one()
    stored_claim = (
        await session.execute(select(ClaimRequest).where(ClaimRequest.id == claim.id))
    ).scalar_one()
    assert response.json()["code"] == 0
    assert stored_lost.status == "CLOSED"
    assert stored_lost.review_status == "REJECTED"
    assert stored_found.status == "PENDING"
    assert stored_claim.review_status == "TERMINATED"
    assert match.match_status == "EXPIRED"


async def test_appeal_queue_detail_and_admin_notice(
    client: AsyncClient,
    admin_headers: dict[str, str],
    session: AsyncSession,
):
    found_id = await _create_found(session, STAFF, "Appealed claim")
    svc = ClaimService(session)
    claim = await svc.create_claim(CreateClaimRequest(foundItemId=found_id), USER)
    await svc.review_claim(
        claim.id,
        ClaimReviewRequest(action="REJECT", comment="原凭证不足"),
        STAFF,
    )
    await svc.appeal_claim(
        claim.id,
        ClaimAppealRequest(reason="可补充现场核验材料"),
        USER,
    )

    queue = await client.get("/api/v1/admin/claims", headers=admin_headers)
    detail = await client.get(f"/api/v1/admin/claims/{claim.id}", headers=admin_headers)
    approved = await client.post(
        f"/api/v1/claims/{claim.id}/review",
        headers=admin_headers,
        json={"action": "APPROVE", "comment": "申诉材料核验通过"},
    )
    stale_reject = await client.post(
        f"/api/v1/claims/{claim.id}/review",
        headers=admin_headers,
        json={"action": "REJECT", "comment": "并发页面的过期操作"},
    )
    refreshed_queue = await client.get("/api/v1/admin/claims", headers=admin_headers)
    admin_notices, total = await NotificationRepository(session).list_by_user(
        user_id=ADMIN.id,
        is_read=None,
        notice_type="CLAIM_REVIEW",
        offset=0,
        limit=10,
    )

    assert queue.json()["code"] == 0
    assert queue.json()["data"]["total"] == 1
    queued = queue.json()["data"]["list"][0]
    assert queued["reviewStatus"] == "APPEALING"
    assert queued["appealReason"] == "可补充现场核验材料"
    assert queued["rejectReason"] == "原凭证不足"
    assert queued["claimant"]["id"] == USER.id
    assert queued["finder"]["id"] == STAFF.id
    assert detail.json()["data"]["item"]["id"] == found_id
    assert approved.json()["data"]["reviewStatus"] == "APPROVED"
    assert stale_reject.json()["code"] == 44003
    assert refreshed_queue.json()["data"]["total"] == 0
    assert total == 1
    assert admin_notices[0].related_id == claim.id


async def test_announcement_lifecycle_visibility_and_idempotent_notification_deep_link(
    client: AsyncClient,
    admin_headers: dict[str, str],
    session: AsyncSession,
):
    draft = await client.post(
        "/api/v1/admin/announcements",
        headers=admin_headers,
        json={"title": "内部草稿", "content": "尚未发布", "publishNow": False},
    )
    draft_id = draft.json()["data"]["id"]

    hidden_draft = await client.get(f"/api/v1/announcements/{draft_id}")
    admin_drafts = await client.get(
        "/api/v1/admin/announcements?status=DRAFT", headers=admin_headers
    )
    first_publish = await client.post(
        f"/api/v1/admin/announcements/{draft_id}/publish", headers=admin_headers
    )
    repeated_publish = await client.post(
        f"/api/v1/admin/announcements/{draft_id}/publish", headers=admin_headers
    )
    listed = await client.get("/api/v1/announcements")
    visible = await client.get(f"/api/v1/announcements/{draft_id}")
    notice_count = (
        await session.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.notice_type == "SYSTEM_ANNOUNCEMENT",
                Notification.related_type == "ANNOUNCEMENT",
                Notification.related_id == draft_id,
            )
        )
    ).scalar_one()
    session.expire_all()
    notice = (
        await session.execute(
            select(Notification).where(
                Notification.user_id == USER.id,
                Notification.related_type == "ANNOUNCEMENT",
                Notification.related_id == draft_id,
            )
        )
    ).scalar_one()
    offline = await client.post(
        f"/api/v1/admin/announcements/{draft_id}/offline", headers=admin_headers
    )
    repeated_offline = await client.post(
        f"/api/v1/admin/announcements/{draft_id}/offline", headers=admin_headers
    )
    hidden_offline = await client.get(f"/api/v1/announcements/{draft_id}")
    empty_public_list = await client.get("/api/v1/announcements")

    assert hidden_draft.json()["code"] == 40004
    assert admin_drafts.json()["data"]["total"] == 1
    assert admin_drafts.json()["data"]["list"][0]["content"] == "尚未发布"
    assert first_publish.json()["data"]["status"] == "PUBLISHED"
    assert repeated_publish.json()["data"]["status"] == "PUBLISHED"
    assert listed.json()["data"]["total"] == 1
    assert listed.json()["data"]["list"][0]["id"] == draft_id
    assert visible.json()["data"]["content"] == "尚未发布"
    assert notice_count == 3
    assert notice.notice_type == "SYSTEM_ANNOUNCEMENT"
    assert notice.related_id == draft_id
    assert offline.json()["data"]["status"] == "OFFLINE"
    assert repeated_offline.json()["data"]["status"] == "OFFLINE"
    assert hidden_offline.json()["code"] == 40004
    assert empty_public_list.json()["data"]["total"] == 0


async def test_announcement_can_publish_during_creation(
    client: AsyncClient,
    admin_headers: dict[str, str],
    session: AsyncSession,
):
    response = await client.post(
        "/api/v1/admin/announcements",
        headers=admin_headers,
        json={"title": "即时公告", "content": "即时通知内容", "publishNow": True},
    )
    announcement_id = response.json()["data"]["id"]
    public_detail = await client.get(f"/api/v1/announcements/{announcement_id}")
    notice_count = (
        await session.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.related_type == "ANNOUNCEMENT",
                Notification.related_id == announcement_id,
            )
        )
    ).scalar_one()

    assert response.json()["data"]["status"] == "PUBLISHED"
    assert public_detail.json()["data"]["content"] == "即时通知内容"
    assert notice_count == 3


async def test_cancelled_is_terminal_and_active_claim_blocks_cancel_and_disable(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_headers: dict[str, str],
    session: AsyncSession,
):
    found_id = await _create_found(session, STAFF, "Account state claim")
    await ClaimService(session).create_claim(CreateClaimRequest(foundItemId=found_id), USER)
    governed_user_id = generate_ulid()
    session.add(
        User(
            id=governed_user_id,
            phone="13810000888",
            password_hash="",
            nickname="Governed user",
            role="USER",
            cert_status="UNVERIFIED",
            credit_score=100,
            status="ACTIVE",
        )
    )
    await session.commit()
    governed_user = CurrentUser(id=governed_user_id, role="USER", status="ACTIVE")
    second_found_id = await _create_found(session, STAFF, "Admin disable claim")
    await ClaimService(session).create_claim(
        CreateClaimRequest(foundItemId=second_found_id), governed_user
    )

    cancelled_with_claim = await client.post(
        "/api/v1/users/me/cancel", headers=auth_headers
    )
    disabled_with_claim = await client.post(
        f"/api/v1/admin/users/{governed_user_id}/status",
        headers=admin_headers,
        json={"status": "DISABLED", "reason": "治理检查"},
    )

    assert cancelled_with_claim.json()["code"] == 40005
    assert disabled_with_claim.json()["code"] == 40005

    user = (
        await session.execute(select(User).where(User.id == governed_user_id))
    ).scalar_one()
    user.status = "CANCELLED"
    await session.commit()
    reactivated = await client.post(
        f"/api/v1/admin/users/{governed_user_id}/status",
        headers=admin_headers,
        json={"status": "ACTIVE"},
    )
    assert reactivated.json()["code"] == 40005


async def test_report_with_missing_exact_target_is_rejected(
    client: AsyncClient,
    admin_headers: dict[str, str],
    session: AsyncSession,
):
    report_id = generate_ulid()
    session.add(
        Report(
            id=report_id,
            reporter_id=ADMIN.id,
            reported_user_id=USER.id,
            target_type="FOUND_ITEM",
            target_id=generate_ulid(),
            reason="STALE",
            handle_status="PENDING",
        )
    )
    await session.commit()

    response = await client.post(
        f"/api/v1/admin/reports/{report_id}/handle",
        headers=admin_headers,
        json={"action": "INVALID", "result": "目标已不存在"},
    )
    assert response.json()["code"] == 47001
