from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.utils import now_beijing
from app.item.models import FoundItem, ItemImage, LostItem, VerifyQuestion


class LostItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, item: LostItem) -> LostItem:
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_by_id(self, item_id: str) -> LostItem | None:
        result = await self._session.execute(select(LostItem).where(LostItem.id == item_id))
        return result.scalar_one_or_none()

    async def list_with_filter(
        self,
        *,
        category: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
        location: str | None = None,
        sort_by: str = "CREATED_DESC",
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[list[LostItem], int]:
        stmt = select(LostItem)
        count_stmt = select(func.count()).select_from(LostItem)

        if category:
            stmt = stmt.where(LostItem.category == category)
            count_stmt = count_stmt.where(LostItem.category == category)
        if status:
            stmt = stmt.where(LostItem.status == status)
            count_stmt = count_stmt.where(LostItem.status == status)
        if keyword:
            pattern = f"%{keyword}%"
            cond = or_(LostItem.item_name.like(pattern), LostItem.description.like(pattern))
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if location:
            stmt = stmt.where(LostItem.lost_location.like(f"%{location}%"))
            count_stmt = count_stmt.where(LostItem.lost_location.like(f"%{location}%"))

        if sort_by == "CREATED_ASC":
            stmt = stmt.order_by(LostItem.created_at.asc())
        else:
            stmt = stmt.order_by(LostItem.created_at.desc())

        stmt = stmt.offset(offset).limit(limit)

        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def update(self, item: LostItem) -> LostItem:
        await self._session.merge(item)
        await self._session.flush()
        return item

    async def check_duplicate(
        self, user_id: str, item_name: str, lost_time_start: str, lost_location: str
    ) -> bool:
        """Check if a duplicate lost item was published within last 1 minute."""
        one_min_ago = now_beijing() - timedelta(minutes=1)
        stmt = (
            select(func.count())
            .select_from(LostItem)
            .where(
                LostItem.user_id == user_id,
                LostItem.item_name == item_name,
                LostItem.lost_location == lost_location,
                LostItem.created_at >= one_min_ago,
            )
        )
        result = await self._session.execute(stmt)
        count = result.scalar() or 0
        return count > 0


class FoundItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, item: FoundItem) -> FoundItem:
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_by_id(self, item_id: str) -> FoundItem | None:
        result = await self._session.execute(select(FoundItem).where(FoundItem.id == item_id))
        return result.scalar_one_or_none()

    async def list_with_filter(
        self,
        *,
        category: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
        location: str | None = None,
        is_sensitive: bool | None = None,
        custody_type: str | None = None,
        sort_by: str = "CREATED_DESC",
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[list[FoundItem], int]:
        stmt = select(FoundItem)
        count_stmt = select(func.count()).select_from(FoundItem)

        if category:
            stmt = stmt.where(FoundItem.category == category)
            count_stmt = count_stmt.where(FoundItem.category == category)
        if status:
            stmt = stmt.where(FoundItem.status == status)
            count_stmt = count_stmt.where(FoundItem.status == status)
        if keyword:
            pattern = f"%{keyword}%"
            cond = or_(FoundItem.item_name.like(pattern), FoundItem.description.like(pattern))
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if location:
            stmt = stmt.where(FoundItem.found_location.like(f"%{location}%"))
            count_stmt = count_stmt.where(FoundItem.found_location.like(f"%{location}%"))
        if is_sensitive is not None:
            val = 1 if is_sensitive else 0
            stmt = stmt.where(FoundItem.is_sensitive == val)
            count_stmt = count_stmt.where(FoundItem.is_sensitive == val)
        if custody_type:
            stmt = stmt.where(FoundItem.custody_type == custody_type)
            count_stmt = count_stmt.where(FoundItem.custody_type == custody_type)

        if sort_by == "CREATED_ASC":
            stmt = stmt.order_by(FoundItem.created_at.asc())
        else:
            stmt = stmt.order_by(FoundItem.created_at.desc())

        stmt = stmt.offset(offset).limit(limit)

        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def update(self, item: FoundItem) -> FoundItem:
        await self._session.merge(item)
        await self._session.flush()
        return item

    async def list_ids_by_user(self, user_id: str) -> list[str]:
        result = await self._session.execute(
            select(FoundItem.id).where(FoundItem.user_id == user_id)
        )
        return list(result.scalars().all())

    async def check_duplicate(
        self, user_id: str, item_name: str, found_time: str, found_location: str
    ) -> bool:
        one_min_ago = now_beijing() - timedelta(minutes=1)
        stmt = (
            select(func.count())
            .select_from(FoundItem)
            .where(
                FoundItem.user_id == user_id,
                FoundItem.item_name == item_name,
                FoundItem.found_location == found_location,
                FoundItem.created_at >= one_min_ago,
            )
        )
        result = await self._session.execute(stmt)
        count = result.scalar() or 0
        return count > 0


class ItemImageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_batch(self, images: list[ItemImage]) -> None:
        self._session.add_all(images)
        await self._session.flush()

    async def get_by_biz(self, biz_type: str, biz_id: str) -> list[ItemImage]:
        stmt = (
            select(ItemImage)
            .where(ItemImage.biz_type == biz_type, ItemImage.biz_id == biz_id)
            .order_by(ItemImage.sort_order)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class VerifyQuestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_batch(self, questions: list[VerifyQuestion]) -> None:
        self._session.add_all(questions)
        await self._session.flush()

    async def get_by_found_item(self, found_item_id: str) -> list[VerifyQuestion]:
        stmt = select(VerifyQuestion).where(VerifyQuestion.found_item_id == found_item_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
