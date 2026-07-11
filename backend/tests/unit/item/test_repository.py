from datetime import datetime

import pytest
from app.db.ulid import generate_ulid
from app.item.models import FoundItem, LostItem
from app.item.repository import FoundItemRepository, LostItemRepository
from app.item.schemas import FoundItemQuery, LostItemQuery


def test_item_query_rejects_reversed_event_time_range() -> None:
    with pytest.raises(ValueError, match="eventTimeEnd"):
        LostItemQuery(
            eventTimeStart="2026-07-11 12:00:00",
            eventTimeEnd="2026-07-11 11:00:00",
        )
    with pytest.raises(ValueError, match="eventTimeEnd"):
        FoundItemQuery(
            eventTimeStart="2026-07-11 12:00:00",
            eventTimeEnd="2026-07-11 11:00:00",
        )


async def test_lost_repository_filters_by_interval_overlap(session) -> None:
    session.add_all(
        [
            LostItem(
                id=generate_ulid(),
                user_id="owner",
                item_name="overlap",
                category="OTHER",
                lost_time_start=datetime(2026, 7, 11, 10),
                lost_time_end=datetime(2026, 7, 11, 12),
                lost_location="A",
                review_status="APPROVED",
            ),
            LostItem(
                id=generate_ulid(),
                user_id="owner",
                item_name="outside",
                category="OTHER",
                lost_time_start=datetime(2026, 7, 11, 13),
                lost_time_end=datetime(2026, 7, 11, 14),
                lost_location="B",
                review_status="APPROVED",
            ),
        ]
    )
    await session.commit()

    items, total = await LostItemRepository(session).list_with_filter(
        event_time_start=datetime(2026, 7, 11, 11),
        event_time_end=datetime(2026, 7, 11, 12, 30),
    )

    assert total == 1
    assert items[0].item_name == "overlap"


async def test_found_repository_filters_found_time_range(session) -> None:
    session.add_all(
        [
            FoundItem(
                id=generate_ulid(),
                user_id="finder",
                item_name="inside",
                category="OTHER",
                found_time=datetime(2026, 7, 11, 11),
                found_location="A",
                custody_type="SELF",
                contact_preference="IN_APP",
                review_status="APPROVED",
            ),
            FoundItem(
                id=generate_ulid(),
                user_id="finder",
                item_name="outside",
                category="OTHER",
                found_time=datetime(2026, 7, 11, 13),
                found_location="B",
                custody_type="SELF",
                contact_preference="IN_APP",
                review_status="APPROVED",
            ),
        ]
    )
    await session.commit()

    items, total = await FoundItemRepository(session).list_with_filter(
        event_time_start=datetime(2026, 7, 11, 10, 30),
        event_time_end=datetime(2026, 7, 11, 11, 30),
    )

    assert total == 1
    assert items[0].item_name == "inside"
