import pytest
from app.common.errors import BizError, ErrorCode
from app.item.schemas import (
    ChangeStatusRequest,
    CreateFoundItemRequest,
    CreateLostItemRequest,
    FoundItemQuery,
    LostItemQuery,
    VerifyQuestionInput,
)
from app.item.service import ItemService
from app.user.schemas import CurrentUser

MOCK_USER = CurrentUser(id="01TESTUSER000000000000001", role="USER", status="ACTIVE")


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
