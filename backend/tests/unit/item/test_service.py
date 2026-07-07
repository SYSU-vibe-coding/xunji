import pytest
from app.admin.models import Report
from app.claim.models import ClaimRequest
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
    VerifyQuestionInput,
)
from app.item.service import ItemService
from app.match.models import MatchResult
from app.user.schemas import CurrentUser
from sqlalchemy import select

MOCK_USER = CurrentUser(id="01TESTUSER000000000000001", role="USER", status="ACTIVE")
OTHER_USER = CurrentUser(id="01OTHERUSER00000000000001", role="USER", status="ACTIVE")
ADMIN_USER = CurrentUser(id="01TESTADMIN00000000000001", role="ADMIN", status="ACTIVE")


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
            imageUrls=["https://example.com/1.jpg", "https://example.com/2.jpg"],
        )
        resp = await svc.create_lost_item(req, MOCK_USER, bg)
        assert resp.status == "SEARCHING"

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
                imageUrls=["https://example.com/old.jpg"],
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
                imageUrls=["https://example.com/new.jpg"],
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
        assert detail["imageUrls"] == ["https://example.com/new.jpg"]
        assert [q["questionText"] for q in detail["verifyQuestions"]] == ["New question?"]

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
            imageUrls=["https://example.com/raw.jpg"],
        )
        created = await svc.create_found_item(req, MOCK_USER, bg)

        listed = await svc.list_found_items(
            FoundItemQuery(pageNo=1, pageSize=10, category="CERT", status="PENDING")
        )
        assert listed["list"][0]["coverImageUrl"] is None

        detail = await svc.get_found_item_detail(created.id, MOCK_USER)
        assert "https://example.com/raw.jpg" not in detail["imageUrls"]

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
