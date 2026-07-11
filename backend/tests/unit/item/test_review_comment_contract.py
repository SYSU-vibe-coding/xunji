from datetime import datetime

from app.db.ulid import generate_ulid
from app.item.models import FoundItem, LostItem
from app.item.schemas import FoundItemQuery, LostItemQuery
from app.item.service import ItemService
from app.user.schemas import CurrentUser


async def test_review_comment_is_returned_by_all_item_read_contracts(session) -> None:
    owner = CurrentUser(id="review-owner", role="USER", status="ACTIVE")
    viewer = CurrentUser(id="review-viewer", role="USER", status="ACTIVE")
    lost = LostItem(
        id=generate_ulid(),
        user_id=owner.id,
        item_name="Reviewed lost",
        category="OTHER",
        lost_time_start=datetime(2026, 7, 11, 8),
        lost_time_end=datetime(2026, 7, 11, 9),
        lost_location="Library",
        status="SEARCHING",
        review_status="APPROVED",
        review_comment="失物审核意见",
    )
    found = FoundItem(
        id=generate_ulid(),
        user_id=owner.id,
        item_name="Reviewed found",
        category="OTHER",
        found_time=datetime(2026, 7, 11, 10),
        found_location="Library",
        is_sensitive=0,
        custody_type="SELF",
        contact_preference="IN_APP",
        status="PENDING",
        review_status="APPROVED",
        review_comment="招领审核意见",
    )
    session.add_all([lost, found])
    await session.commit()
    service = ItemService(session)

    lost_list = await service.list_lost_items(LostItemQuery(), viewer)
    found_list = await service.list_found_items(FoundItemQuery(), viewer)
    lost_detail = await service.get_lost_item_detail(lost.id, viewer)
    found_detail = await service.get_found_item_detail(found.id, viewer)

    assert lost_list["list"][0]["reviewComment"] == "失物审核意见"
    assert found_list["list"][0]["reviewComment"] == "招领审核意见"
    assert lost_detail["reviewComment"] == "失物审核意见"
    assert found_detail["reviewComment"] == "招领审核意见"
