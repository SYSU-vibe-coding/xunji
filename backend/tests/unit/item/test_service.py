import pytest
from app.admin.models import Report
from app.claim.models import ClaimRequest
from app.claim.schemas import CreateClaimRequest
from app.claim.service import ClaimService
from app.common.errors import BizError, ErrorCode
from app.db.ulid import generate_ulid
from app.item.schemas import (
    ChangeStatusRequest,
    CreateFoundItemRequest,
    CreateLostItemRequest,
    FoundItemQuery,
    LostItemQuery,
    SubmitReportRequest,
    UpdateFoundItemRequest,
    UpdateLostItemRequest,
    VerifyQuestionInput,
)
from app.item.service import ItemService
from app.match.models import MatchResult
from app.notification.repository import NotificationRepository
from app.user.schemas import CurrentUser
from sqlalchemy import select

MOCK_USER = CurrentUser(id="01TESTUSER000000000000001", role="USER", status="ACTIVE")
OTHER_USER = CurrentUser(id="01OTHERUSER00000000000001", role="USER", status="ACTIVE")
ADMIN_USER = CurrentUser(id="01TESTADMIN00000000000001", role="ADMIN", status="ACTIVE")
LOST_REF_1 = f"asset://LOST/{MOCK_USER.id}/202607/{'1' * 32}.jpg"
LOST_REF_2 = f"asset://LOST/{MOCK_USER.id}/202607/{'2' * 32}.jpg"
FOUND_REF_1 = f"asset://FOUND/{MOCK_USER.id}/202607/{'3' * 32}.jpg"
FOUND_REF_2 = f"asset://FOUND/{MOCK_USER.id}/202607/{'4' * 32}.jpg"


class TestLostItemService:
    async def test_create_lost_item(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        bg = BackgroundTasks()
        req = CreateLostItemRequest(
            itemName="MacBook Pro",
            category="ELECTRONIC",
            description="Silver 14-inch",
            lostTimeStart="2026-04-20 10:00:00",
            lostTimeEnd="2026-04-20 12:00:00",
            lostLocation="图书馆3楼",
        )
        resp = await svc.create_lost_item(req, MOCK_USER, bg)
        assert resp.status == "SEARCHING"
        assert len(resp.id) == 26
        assert len(bg.tasks) == 1

    async def test_create_lost_item_with_images(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        bg = BackgroundTasks()
        req = CreateLostItemRequest(
            itemName="iPhone 15",
            category="ELECTRONIC",
            lostTimeStart="2026-04-21 08:00:00",
            lostTimeEnd="2026-04-21 09:00:00",
            lostLocation="食堂",
            imageUrls=[LOST_REF_1, LOST_REF_2],
        )
        resp = await svc.create_lost_item(req, MOCK_USER, bg)
        assert resp.status == "SEARCHING"

    async def test_create_lost_item_rejects_external_image_url(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        req = CreateLostItemRequest(
            itemName="External image",
            category="OTHER",
            lostTimeStart="2026-04-21 08:00:00",
            lostTimeEnd="2026-04-21 09:00:00",
            lostLocation="Gate",
            imageUrls=["https://example.com/image.jpg"],
        )
        with pytest.raises(BizError) as exc_info:
            await svc.create_lost_item(req, MOCK_USER, BackgroundTasks())
        assert exc_info.value.code == ErrorCode.PARAM_ERROR

    async def test_create_lost_item_too_many_images(self):
        with pytest.raises(ValueError, match="最多上传5张图片"):
            CreateLostItemRequest(
                itemName="Test",
                category="OTHER",
                lostTimeStart="2026-04-22 10:00:00",
                lostTimeEnd="2026-04-22 11:00:00",
                lostLocation="操场",
                imageUrls=[f"https://example.com/{i}.jpg" for i in range(6)],
            )

    async def test_change_lost_status_valid(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        bg = BackgroundTasks()
        create_req = CreateLostItemRequest(
            itemName="Wallet",
            category="DAILY_USE",
            lostTimeStart="2026-04-23 10:00:00",
            lostTimeEnd="2026-04-23 11:00:00",
            lostLocation="教学楼",
        )
        created = await svc.create_lost_item(create_req, MOCK_USER, bg)

        change_req = ChangeStatusRequest(status="FOUND")
        result = await svc.change_lost_item_status(created.id, change_req, MOCK_USER)
        assert result["status"] == "FOUND"

    async def test_change_lost_status_invalid_transition(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        bg = BackgroundTasks()
        create_req = CreateLostItemRequest(
            itemName="Keys",
            category="OTHER",
            lostTimeStart="2026-04-24 10:00:00",
            lostTimeEnd="2026-04-24 11:00:00",
            lostLocation="实验室",
        )
        created = await svc.create_lost_item(create_req, MOCK_USER, bg)

        await svc.change_lost_item_status(
            created.id, ChangeStatusRequest(status="FOUND"), MOCK_USER
        )
        with pytest.raises(BizError) as exc_info:
            await svc.change_lost_item_status(
                created.id, ChangeStatusRequest(status="SEARCHING"), MOCK_USER
            )
        assert exc_info.value.code == ErrorCode.INVALID_STATE

    async def test_change_status_not_publisher(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        bg = BackgroundTasks()
        create_req = CreateLostItemRequest(
            itemName="Umbrella",
            category="DAILY_USE",
            lostTimeStart="2026-04-25 10:00:00",
            lostTimeEnd="2026-04-25 11:00:00",
            lostLocation="体育馆",
        )
        created = await svc.create_lost_item(create_req, MOCK_USER, bg)

        other_user = CurrentUser(id="01OTHERUSER00000000000001", role="USER", status="ACTIVE")
        with pytest.raises(BizError) as exc_info:
            await svc.change_lost_item_status(
                created.id, ChangeStatusRequest(status="CLOSED"), other_user
            )
        assert exc_info.value.code == ErrorCode.NOT_PUBLISHER

    async def test_lost_detail_uses_real_match_count_for_publisher(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        bg = BackgroundTasks()
        lost = await svc.create_lost_item(
            CreateLostItemRequest(
                itemName="Camera",
                category="ELECTRONIC",
                lostTimeStart="2026-04-25 10:00:00",
                lostTimeEnd="2026-04-25 11:00:00",
                lostLocation="Library",
            ),
            MOCK_USER,
            bg,
        )
        found = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Camera",
                category="ELECTRONIC",
                foundTime="2026-04-25 12:00:00",
                foundLocation="Library",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            OTHER_USER,
            bg,
        )
        session.add(
            MatchResult(
                id=generate_ulid(),
                lost_item_id=lost.id,
                found_item_id=found.id,
                match_status="NEW",
            )
        )
        await session.commit()

        owner_detail = await svc.get_lost_item_detail(lost.id, MOCK_USER)
        other_detail = await svc.get_lost_item_detail(lost.id, OTHER_USER)

        assert owner_detail["matchCount"] == 1
        assert other_detail["matchCount"] is None

    async def test_list_my_lost_items_only_returns_current_user_items(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        bg = BackgroundTasks()
        mine = await svc.create_lost_item(
            CreateLostItemRequest(
                itemName="My Wallet",
                category="DAILY_USE",
                lostTimeStart="2026-04-26 10:00:00",
                lostTimeEnd="2026-04-26 11:00:00",
                lostLocation="Gate",
            ),
            MOCK_USER,
            bg,
        )
        await svc.create_lost_item(
            CreateLostItemRequest(
                itemName="Other Wallet",
                category="DAILY_USE",
                lostTimeStart="2026-04-26 10:00:00",
                lostTimeEnd="2026-04-26 11:00:00",
                lostLocation="Gate",
            ),
            OTHER_USER,
            bg,
        )
        await svc.change_lost_item_status(mine.id, ChangeStatusRequest(status="CLOSED"), MOCK_USER)

        result = await svc.list_my_lost_items(LostItemQuery(pageNo=1, pageSize=10), MOCK_USER)

        assert result["total"] == 1
        assert result["list"][0]["id"] == mine.id
        assert result["list"][0]["status"] == "CLOSED"

    async def test_lost_items_support_event_time_sorting(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        later = await svc.create_lost_item(
            CreateLostItemRequest(
                itemName="Later Event",
                category="OTHER",
                lostTimeStart="2026-05-02 10:00:00",
                lostTimeEnd="2026-05-02 11:00:00",
                lostLocation="Gate A",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )
        earlier = await svc.create_lost_item(
            CreateLostItemRequest(
                itemName="Earlier Event",
                category="OTHER",
                lostTimeStart="2026-04-01 10:00:00",
                lostTimeEnd="2026-04-01 11:00:00",
                lostLocation="Gate B",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )

        asc = await svc.list_lost_items(LostItemQuery(sortBy="EVENT_ASC"))
        desc = await svc.list_lost_items(LostItemQuery(sortBy="EVENT_DESC"))

        assert [item["id"] for item in asc["list"]] == [earlier.id, later.id]
        assert [item["id"] for item in desc["list"]] == [later.id, earlier.id]

    async def test_admin_can_change_lost_status(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        created = await svc.create_lost_item(
            CreateLostItemRequest(
                itemName="Admin Close",
                category="OTHER",
                lostTimeStart="2026-04-27 10:00:00",
                lostTimeEnd="2026-04-27 11:00:00",
                lostLocation="Office",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )

        result = await svc.change_lost_item_status(
            created.id, ChangeStatusRequest(status="CLOSED"), ADMIN_USER
        )

        assert result["status"] == "CLOSED"

    async def test_admin_lost_list_uses_real_report_count(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        created = await svc.create_lost_item(
            CreateLostItemRequest(
                itemName="Reported Lost",
                category="OTHER",
                lostTimeStart="2026-04-28 10:00:00",
                lostTimeEnd="2026-04-28 11:00:00",
                lostLocation="Office",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )
        await svc.submit_report(
            SubmitReportRequest(
                targetType="LOST_ITEM",
                targetId=created.id,
                reason="SPAM",
                description="bad listing",
            ),
            OTHER_USER,
        )

        items, _ = await svc.list_admin_items_internal("LOST", offset=0, limit=10)
        item = next(i for i in items if i["id"] == created.id)

        assert item["reportCount"] == 1

    async def test_cert_lost_images_are_hidden_from_non_owner(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        created = await svc.create_lost_item(
            CreateLostItemRequest(
                itemName="Student Card",
                category="CERT",
                lostTimeStart="2026-05-01 10:00:00",
                lostTimeEnd="2026-05-01 11:00:00",
                lostLocation="Library",
                imageUrls=[LOST_REF_1],
            ),
            MOCK_USER,
            BackgroundTasks(),
        )

        outsider_list = await svc.list_lost_items(LostItemQuery(), OTHER_USER)
        outsider_detail = await svc.get_lost_item_detail(created.id, OTHER_USER)
        owner_detail = await svc.get_lost_item_detail(created.id, MOCK_USER)
        admin_detail = await svc.get_lost_item_detail(created.id, ADMIN_USER)

        assert outsider_list["list"][0]["coverImageUrl"] is None
        assert outsider_detail["imageUrls"] == []
        assert outsider_detail["coverImageUrl"] is None
        assert owner_detail["imageUrls"][0].startswith("https://signed.test/")
        assert admin_detail["imageUrls"][0].startswith("https://signed.test/")

    async def test_pending_lost_is_visible_only_to_owner_and_admin(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        created = await svc.create_lost_item(
            CreateLostItemRequest(
                itemName="Review Me",
                category="OTHER",
                lostTimeStart="2026-05-02 10:00:00",
                lostTimeEnd="2026-05-02 11:00:00",
                lostLocation="Gate",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )
        await svc.update_lost_item(
            created.id,
            UpdateLostItemRequest(
                itemName="Review Me Updated",
                category="OTHER",
                lostTimeStart="2026-05-02 10:00:00",
                lostTimeEnd="2026-05-02 11:00:00",
                lostLocation="Gate",
            ),
            MOCK_USER,
        )

        outsider = await svc.list_lost_items(LostItemQuery(), OTHER_USER)
        owner = await svc.list_lost_items(LostItemQuery(), MOCK_USER)
        admin = await svc.list_lost_items(LostItemQuery(), ADMIN_USER)

        assert outsider["total"] == 0
        assert owner["total"] == 1
        assert admin["total"] == 1
        with pytest.raises(BizError) as detail_error:
            await svc.get_lost_item_detail(created.id, OTHER_USER)
        assert detail_error.value.code == ErrorCode.ITEM_NOT_FOUND

    async def test_active_match_claim_blocks_all_lost_mutations(self, session, seeded_users):
        from fastapi import BackgroundTasks

        finder = CurrentUser(id="01TESTSTAFF00000000000001", role="STAFF", status="ACTIVE")
        svc = ItemService(session)
        lost = await svc.create_lost_item(
            CreateLostItemRequest(
                itemName="Claimed Lost",
                category="OTHER",
                lostTimeStart="2026-05-03 08:00:00",
                lostTimeEnd="2026-05-03 09:00:00",
                lostLocation="Library",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )
        found = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Claimed Lost",
                category="OTHER",
                foundTime="2026-05-03 10:00:00",
                foundLocation="Library",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            finder,
            BackgroundTasks(),
        )
        match = MatchResult(
            id=generate_ulid(),
            lost_item_id=lost.id,
            found_item_id=found.id,
            match_status="NEW",
        )
        session.add(match)
        await session.commit()
        await ClaimService(session).create_claim(
            CreateClaimRequest(foundItemId=found.id, matchId=match.id), MOCK_USER
        )
        update = UpdateLostItemRequest(
            itemName="Blocked",
            category="OTHER",
            lostTimeStart="2026-05-03 08:00:00",
            lostTimeEnd="2026-05-03 09:00:00",
            lostLocation="Library",
        )

        operations = [
            svc.update_lost_item(lost.id, update, MOCK_USER),
            svc.change_lost_item_status(lost.id, ChangeStatusRequest(status="FOUND"), MOCK_USER),
            svc.change_lost_item_status(lost.id, ChangeStatusRequest(status="CLOSED"), MOCK_USER),
            svc.delete_lost_item(lost.id, MOCK_USER),
        ]
        for operation in operations:
            with pytest.raises(BizError) as exc_info:
                await operation
            assert exc_info.value.code == ErrorCode.INVALID_STATE
            assert "关联认领" in exc_info.value.message

    async def test_delete_lost_item_is_logical_close(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        created = await svc.create_lost_item(
            CreateLostItemRequest(
                itemName="Logical Delete",
                category="OTHER",
                lostTimeStart="2026-05-04 08:00:00",
                lostTimeEnd="2026-05-04 09:00:00",
                lostLocation="Gate",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )

        result = await svc.delete_lost_item(created.id, MOCK_USER)
        stored = await svc.get_lost_item_internal(created.id)

        assert result["status"] == "CLOSED"
        assert stored.status == "CLOSED"


class TestFoundItemService:
    async def test_create_found_item(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        bg = BackgroundTasks()
        req = CreateFoundItemRequest(
            itemName="Student Card",
            category="CERT",
            foundTime="2026-04-20 14:00:00",
            foundLocation="操场旁",
            custodyType="SELF",
            contactPreference="IN_APP",
        )
        resp = await svc.create_found_item(req, MOCK_USER, bg)
        assert resp.status == "PENDING"
        assert resp.is_sensitive is True
        assert len(bg.tasks) == 1

    async def test_create_found_item_with_questions(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        bg = BackgroundTasks()
        req = CreateFoundItemRequest(
            itemName="Water Bottle",
            category="DAILY_USE",
            foundTime="2026-04-21 16:00:00",
            foundLocation="食堂",
            custodyType="SELF",
            contactPreference="PHONE",
            verifyQuestions=[
                VerifyQuestionInput(questionText="什么颜色?", answerKeywords=["蓝色", "蓝"]),
                VerifyQuestionInput(questionText="什么牌子?", answerKeywords=["膳魔师"]),
            ],
        )
        resp = await svc.create_found_item(req, MOCK_USER, bg)
        assert resp.status == "PENDING"
        assert resp.is_sensitive is False

    async def test_change_found_status_closed(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        bg = BackgroundTasks()
        req = CreateFoundItemRequest(
            itemName="Notebook",
            category="BOOK",
            foundTime="2026-04-22 10:00:00",
            foundLocation="自习室",
            custodyType="SELF",
            contactPreference="IN_APP",
        )
        created = await svc.create_found_item(req, MOCK_USER, bg)

        result = await svc.change_found_item_status(
            created.id, ChangeStatusRequest(status="CLOSED"), MOCK_USER
        )
        assert result["status"] == "CLOSED"

    async def test_found_detail_uses_real_active_claim_flag(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        created = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Headphones",
                category="ELECTRONIC",
                foundTime="2026-04-22 10:00:00",
                foundLocation="Library",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )
        session.add(
            ClaimRequest(
                id=generate_ulid(),
                found_item_id=created.id,
                claimant_id=OTHER_USER.id,
                verify_level="BASIC",
                review_status="PENDING",
            )
        )
        await session.commit()

        detail = await svc.get_found_item_detail(created.id, MOCK_USER)

        assert detail["hasActiveClaim"] is True

    async def test_list_my_found_items_only_returns_current_user_items(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        bg = BackgroundTasks()
        mine = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="My Book",
                category="BOOK",
                foundTime="2026-04-23 10:00:00",
                foundLocation="Library",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
            bg,
        )
        await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Other Book",
                category="BOOK",
                foundTime="2026-04-23 11:00:00",
                foundLocation="Library",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            OTHER_USER,
            bg,
        )

        result = await svc.list_my_found_items(FoundItemQuery(pageNo=1, pageSize=10), MOCK_USER)

        assert result["total"] == 1
        assert result["list"][0]["id"] == mine.id

    async def test_found_items_support_event_time_sorting(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        later = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Later Found Event",
                category="OTHER",
                foundTime="2026-05-02 10:00:00",
                foundLocation="Gate A",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )
        earlier = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Earlier Found Event",
                category="OTHER",
                foundTime="2026-04-01 10:00:00",
                foundLocation="Gate B",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )

        asc = await svc.list_found_items(FoundItemQuery(sortBy="EVENT_ASC"), MOCK_USER)
        desc = await svc.list_found_items(FoundItemQuery(sortBy="EVENT_DESC"), MOCK_USER)

        assert [item["id"] for item in asc["list"]] == [earlier.id, later.id]
        assert [item["id"] for item in desc["list"]] == [later.id, earlier.id]

    async def test_found_claiming_can_be_closed_by_publisher(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        created = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Claiming Item",
                category="OTHER",
                foundTime="2026-04-24 10:00:00",
                foundLocation="Gate",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )
        await svc.update_found_status_internal(created.id, "CLAIMING")
        await session.commit()

        result = await svc.change_found_item_status(
            created.id, ChangeStatusRequest(status="CLOSED"), MOCK_USER
        )

        assert result["status"] == "CLOSED"

    async def test_close_found_terminates_claim_expires_match_and_notifies_parties(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        lost = await svc.create_lost_item(
            CreateLostItemRequest(
                itemName="Matched Item",
                category="OTHER",
                lostTimeStart="2026-04-24 08:00:00",
                lostTimeEnd="2026-04-24 09:00:00",
                lostLocation="Gate",
            ),
            OTHER_USER,
            BackgroundTasks(),
        )
        found = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Matched Item",
                category="OTHER",
                foundTime="2026-04-24 10:00:00",
                foundLocation="Gate",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )
        match = MatchResult(
            id=generate_ulid(),
            lost_item_id=lost.id,
            found_item_id=found.id,
            match_status="CLAIMED",
        )
        claim = ClaimRequest(
            id=generate_ulid(),
            match_id=match.id,
            found_item_id=found.id,
            claimant_id=OTHER_USER.id,
            verify_level="LEVEL_2",
            review_status="APPROVED",
        )
        session.add_all([match, claim])
        await svc.update_found_status_internal(found.id, "CLAIMING")
        await session.commit()

        result = await svc.change_found_item_status(
            found.id, ChangeStatusRequest(status="CLOSED"), MOCK_USER
        )

        assert result["status"] == "CLOSED"
        assert claim.review_status == "TERMINATED"
        assert match.match_status == "EXPIRED"
        notice_repo = NotificationRepository(session)
        for user_id in (MOCK_USER.id, OTHER_USER.id):
            notices, total = await notice_repo.list_by_user(
                user_id=user_id,
                is_read=None,
                notice_type="CLAIM_REVIEW",
                offset=0,
                limit=10,
            )
            assert total == 1
            assert notices[0].related_id == claim.id

    async def test_claiming_found_content_cannot_be_modified(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        created = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Locked Item",
                category="OTHER",
                foundTime="2026-04-24 10:00:00",
                foundLocation="Gate",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )
        await svc.update_found_status_internal(created.id, "CLAIMING")
        await session.commit()

        with pytest.raises(BizError) as exc_info:
            await svc.update_found_item(
                created.id,
                UpdateFoundItemRequest(
                    itemName="Changed Item",
                    category="OTHER",
                    foundTime="2026-04-24 11:00:00",
                    foundLocation="Elsewhere",
                    custodyType="SELF",
                    contactPreference="IN_APP",
                ),
                MOCK_USER,
            )
        assert exc_info.value.code == ErrorCode.INVALID_STATE

    async def test_pending_found_is_visible_only_to_owner_and_admin(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        created = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Pending Found",
                category="OTHER",
                foundTime="2026-05-04 10:00:00",
                foundLocation="Gate",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )
        await svc.update_found_item(
            created.id,
            UpdateFoundItemRequest(
                itemName="Pending Found Updated",
                category="OTHER",
                foundTime="2026-05-04 10:00:00",
                foundLocation="Gate",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
        )

        outsider = await svc.list_found_items(FoundItemQuery(), OTHER_USER)
        owner = await svc.list_found_items(FoundItemQuery(), MOCK_USER)
        admin = await svc.list_found_items(FoundItemQuery(), ADMIN_USER)

        assert outsider["total"] == 0
        assert owner["total"] == 1
        assert admin["total"] == 1
        with pytest.raises(BizError) as detail_error:
            await svc.get_found_item_detail(created.id, OTHER_USER)
        assert detail_error.value.code == ErrorCode.ITEM_NOT_FOUND

    async def test_update_found_item_replaces_images_and_questions(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        created = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Old Bottle",
                category="DAILY_USE",
                foundTime="2026-04-25 10:00:00",
                foundLocation="Old Gate",
                custodyType="SELF",
                contactPreference="IN_APP",
                imageUrls=[FOUND_REF_1],
                verifyQuestions=[
                    VerifyQuestionInput(questionText="Old question?", answerKeywords=["old"])
                ],
            ),
            MOCK_USER,
            BackgroundTasks(),
        )
        await svc.change_found_item_status(
            created.id, ChangeStatusRequest(status="CLOSED"), MOCK_USER
        )

        result = await svc.update_found_item(
            created.id,
            UpdateFoundItemRequest(
                itemName="New Bottle",
                category="BOOK",
                description="updated",
                foundTime="2026-04-26 11:00:00",
                foundLocation="New Gate",
                custodyType="OFFICE",
                contactPreference="PHONE",
                imageUrls=[FOUND_REF_2],
                verifyQuestions=[
                    VerifyQuestionInput(questionText="New question?", answerKeywords=["new"])
                ],
            ),
            MOCK_USER,
        )
        detail = await svc.get_found_item_detail(created.id, MOCK_USER)

        assert result == {"id": created.id, "status": "PENDING", "reviewStatus": "PENDING"}
        assert detail["itemName"] == "New Bottle"
        assert detail["category"] == "BOOK"
        assert detail["description"] == "updated"
        assert detail["foundLocation"] == "New Gate"
        assert detail["custodyType"] == "OFFICE"
        assert detail["contactPreference"] == "PHONE"
        assert detail["imageUrls"] == [
            f"https://signed.test/xunji/FOUND/{MOCK_USER.id}/202607/{'4' * 32}.jpg?signature=test"
        ]
        assert detail["imageRefs"] == [FOUND_REF_2]
        assert [q["questionText"] for q in detail["verifyQuestions"]] == ["New question?"]

    async def test_update_found_item_expires_old_match_and_schedules_recalculation(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        lost = await svc.create_lost_item(
            CreateLostItemRequest(
                itemName="Old Name",
                category="OTHER",
                lostTimeStart="2026-04-26 08:00:00",
                lostTimeEnd="2026-04-26 09:00:00",
                lostLocation="Gate",
            ),
            OTHER_USER,
            BackgroundTasks(),
        )
        found = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Old Name",
                category="OTHER",
                foundTime="2026-04-26 10:00:00",
                foundLocation="Gate",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )
        match = MatchResult(
            id=generate_ulid(),
            lost_item_id=lost.id,
            found_item_id=found.id,
            match_status="NEW",
        )
        session.add(match)
        await session.commit()
        tasks = BackgroundTasks()

        await svc.update_found_item(
            found.id,
            UpdateFoundItemRequest(
                itemName="New Name",
                category="OTHER",
                foundTime="2026-04-26 11:00:00",
                foundLocation="Office",
                custodyType="OFFICE",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
            tasks,
        )

        assert match.match_status == "EXPIRED"
        assert len(tasks.tasks) == 1

    async def test_update_found_item_not_publisher(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        created = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Owner Item",
                category="OTHER",
                foundTime="2026-04-27 10:00:00",
                foundLocation="Gate",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )

        with pytest.raises(BizError) as exc_info:
            await svc.update_found_item(
                created.id,
                UpdateFoundItemRequest(
                    itemName="Bad Update",
                    category="OTHER",
                    foundTime="2026-04-27 11:00:00",
                    foundLocation="Gate",
                    custodyType="SELF",
                    contactPreference="IN_APP",
                ),
                OTHER_USER,
            )

        assert exc_info.value.code == ErrorCode.NOT_PUBLISHER

    async def test_submit_report_creates_report_and_prevents_duplicate(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        created = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Reportable Item",
                category="OTHER",
                foundTime="2026-04-25 10:00:00",
                foundLocation="Gate",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )

        resp = await svc.submit_report(
            SubmitReportRequest(
                targetType="FOUND_ITEM",
                targetId=created.id,
                reason="SPAM",
                description="bad listing",
            ),
            OTHER_USER,
        )
        result = await session.execute(select(Report).where(Report.id == resp.id))
        report = result.scalar_one()

        assert resp.handle_status == "PENDING"
        assert report.reported_user_id == MOCK_USER.id

        with pytest.raises(BizError) as exc_info:
            await svc.submit_report(
                SubmitReportRequest(targetType="FOUND_ITEM", targetId=created.id, reason="SPAM"),
                OTHER_USER,
            )
        assert exc_info.value.code == ErrorCode.REPORT_DUPLICATE

    async def test_report_unique_conflict_maps_to_duplicate(self, session, monkeypatch):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        created = await svc.create_found_item(
            CreateFoundItemRequest(
                itemName="Concurrent Report",
                category="OTHER",
                foundTime="2026-04-25 11:00:00",
                foundLocation="Gate",
                custodyType="SELF",
                contactPreference="IN_APP",
            ),
            MOCK_USER,
            BackgroundTasks(),
        )

        async def stale_precheck(**kwargs):
            return False

        monkeypatch.setattr(svc._report_repo, "exists_by_reporter_and_target", stale_precheck)
        request = SubmitReportRequest(targetType="FOUND_ITEM", targetId=created.id, reason="SPAM")
        await svc.submit_report(request, OTHER_USER)

        with pytest.raises(BizError) as exc_info:
            await svc.submit_report(request, OTHER_USER)

        assert exc_info.value.code == ErrorCode.REPORT_DUPLICATE
        reports = await session.execute(
            select(Report).where(
                Report.reporter_id == OTHER_USER.id,
                Report.target_type == "FOUND_ITEM",
                Report.target_id == created.id,
            )
        )
        assert len(reports.scalars().all()) == 1

    async def test_batch_create_found_items_partial_failure(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        bg = BackgroundTasks()
        req = CreateFoundItemRequest(
            itemName="Batch Pen",
            category="DAILY_USE",
            foundTime="2026-04-22 10:00:00",
            foundLocation="自习室",
            custodyType="SELF",
            contactPreference="IN_APP",
        )

        resp = await svc.create_found_items_batch([req, req], MOCK_USER, bg)

        assert len(resp.success_ids) == 1
        assert len(resp.failures) == 1
        assert resp.failures[0].index == 1
        assert resp.failures[0].error

    async def test_sensitive_found_item_list_and_detail_do_not_return_original_image(self, session):
        from fastapi import BackgroundTasks

        svc = ItemService(session)
        bg = BackgroundTasks()
        req = CreateFoundItemRequest(
            itemName="Campus Card",
            category="CERT",
            foundTime="2026-04-23 10:00:00",
            foundLocation="图书馆",
            custodyType="SELF",
            contactPreference="IN_APP",
            imageUrls=[FOUND_REF_1],
        )
        created = await svc.create_found_item(req, MOCK_USER, bg)

        listed = await svc.list_found_items(
            FoundItemQuery(pageNo=1, pageSize=10, category="CERT", status="PENDING")
        )
        assert listed["list"][0]["coverImageUrl"] is None

        outsider_detail = await svc.get_found_item_detail(created.id, OTHER_USER)
        assert outsider_detail["isSensitive"] is True
        assert outsider_detail["imageUrls"] == []
        assert outsider_detail["imageRefs"] is None

        owner_detail = await svc.get_found_item_detail(created.id, MOCK_USER)
        assert owner_detail["imageUrls"][0].startswith("https://signed.test/")
        assert owner_detail["imageRefs"] == [FOUND_REF_1]

        admin_detail = await svc.get_found_item_detail(created.id, ADMIN_USER)
        assert admin_detail["imageUrls"][0].startswith("https://signed.test/")
        assert admin_detail["imageRefs"] is None

    async def test_item_schema_validation(self):
        with pytest.raises(ValueError, match="lostTimeEnd"):
            CreateLostItemRequest(
                itemName="Bad Time",
                category="OTHER",
                lostTimeStart="2026-04-23 11:00:00",
                lostTimeEnd="2026-04-23 10:00:00",
                lostLocation="教学楼",
            )

        with pytest.raises(ValueError, match="answerKeywords"):
            VerifyQuestionInput(questionText="什么特征?", answerKeywords=["x" * 21])

        with pytest.raises(ValueError, match="category"):
            LostItemQuery(category="BAD")
