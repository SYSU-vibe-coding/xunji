from datetime import datetime, timedelta

from sqlalchemy import func, literal, or_, select, union_all, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import Report
from app.common.utils import now_beijing
from app.item.models import FoundItem, ItemImage, LostItem, VerifyQuestion
from app.match.models import MatchResult
from app.user.models import User


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

    async def get_by_id_for_update(self, item_id: str) -> LostItem | None:
        result = await self._session.execute(
            select(LostItem)
            .where(LostItem.id == item_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def list_active_by_user_for_update(self, user_id: str) -> list[LostItem]:
        result = await self._session.execute(
            select(LostItem)
            .where(LostItem.user_id == user_id, LostItem.status == "SEARCHING")
            .order_by(LostItem.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return list(result.scalars().all())

    async def list_ids_by_user(self, user_id: str) -> list[str]:
        result = await self._session.execute(
            select(LostItem.id).where(LostItem.user_id == user_id).order_by(LostItem.id)
        )
        return list(result.scalars().all())

    async def list_with_filter(
        self,
        *,
        category: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
        location: str | None = None,
        event_time_start: datetime | None = None,
        event_time_end: datetime | None = None,
        user_id: str | None = None,
        viewer_user_id: str | None = None,
        include_all_reviews: bool = False,
        sort_by: str = "CREATED_DESC",
        offset: int = 0,
        limit: int = 10,
        exclude_statuses: list[str] | None = None,
    ) -> tuple[list[LostItem], int]:
        stmt = select(LostItem)
        count_stmt = select(func.count()).select_from(LostItem)

        if category:
            stmt = stmt.where(LostItem.category == category)
            count_stmt = count_stmt.where(LostItem.category == category)
        if status:
            stmt = stmt.where(LostItem.status == status)
            count_stmt = count_stmt.where(LostItem.status == status)
        elif exclude_statuses:
            stmt = stmt.where(LostItem.status.notin_(exclude_statuses))
            count_stmt = count_stmt.where(LostItem.status.notin_(exclude_statuses))
        if keyword:
            pattern = f"%{keyword}%"
            cond = or_(
                LostItem.item_name.like(pattern),
                LostItem.description.like(pattern),
                LostItem.ai_tags.like(pattern),
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if location:
            stmt = stmt.where(LostItem.lost_location.like(f"%{location}%"))
            count_stmt = count_stmt.where(LostItem.lost_location.like(f"%{location}%"))
        if event_time_start is not None:
            stmt = stmt.where(LostItem.lost_time_end >= event_time_start)
            count_stmt = count_stmt.where(LostItem.lost_time_end >= event_time_start)
        if event_time_end is not None:
            stmt = stmt.where(LostItem.lost_time_start <= event_time_end)
            count_stmt = count_stmt.where(LostItem.lost_time_start <= event_time_end)
        if user_id:
            stmt = stmt.where(LostItem.user_id == user_id)
            count_stmt = count_stmt.where(LostItem.user_id == user_id)
        if not include_all_reviews:
            review_visible = LostItem.review_status == "APPROVED"
            if viewer_user_id is not None:
                review_visible = or_(review_visible, LostItem.user_id == viewer_user_id)
            stmt = stmt.where(review_visible)
            count_stmt = count_stmt.where(review_visible)

        if sort_by == "EVENT_ASC":
            stmt = stmt.order_by(LostItem.lost_time_start.asc(), LostItem.id.asc())
        elif sort_by == "EVENT_DESC":
            stmt = stmt.order_by(LostItem.lost_time_start.desc(), LostItem.id.desc())
        elif sort_by == "CREATED_ASC":
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

    async def transition_review(
        self,
        item_id: str,
        *,
        review_status: str,
        review_comment: str | None,
        close_item: bool,
    ) -> bool:
        values: dict[str, object] = {
            "review_status": review_status,
            "review_comment": review_comment,
            "updated_at": func.now(),
        }
        if close_item:
            values["status"] = "CLOSED"
        result = await self._session.execute(
            update(LostItem)
            .where(LostItem.id == item_id, LostItem.review_status == "PENDING")
            .values(**values)
        )
        return bool(getattr(result, "rowcount", 0))

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

    async def list_active(self, *, exclude_id: str | None = None) -> list[LostItem]:
        """All lost items still being searched (status=SEARCHING)."""
        stmt = (
            select(LostItem)
            .join(User, User.id == LostItem.user_id)
            .where(
                LostItem.status == "SEARCHING",
                LostItem.review_status == "APPROVED",
                User.status == "ACTIVE",
            )
        )
        if exclude_id is not None:
            stmt = stmt.where(LostItem.id != exclude_id)
        stmt = stmt.order_by(LostItem.lost_time_start.desc(), LostItem.id.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_matches(self, item_id: str) -> int:
        stmt = (
            select(func.count()).select_from(MatchResult).where(MatchResult.lost_item_id == item_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0


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

    async def get_by_id_for_update(self, item_id: str) -> FoundItem | None:
        result = await self._session.execute(
            select(FoundItem)
            .where(FoundItem.id == item_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def list_active_by_user_for_update(self, user_id: str) -> list[FoundItem]:
        result = await self._session.execute(
            select(FoundItem)
            .where(FoundItem.user_id == user_id, FoundItem.status == "PENDING")
            .order_by(FoundItem.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return list(result.scalars().all())

    async def list_with_filter(
        self,
        *,
        category: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
        location: str | None = None,
        event_time_start: datetime | None = None,
        event_time_end: datetime | None = None,
        user_id: str | None = None,
        viewer_user_id: str | None = None,
        include_all_reviews: bool = False,
        is_sensitive: bool | None = None,
        custody_type: str | None = None,
        sort_by: str = "CREATED_DESC",
        offset: int = 0,
        limit: int = 10,
        exclude_statuses: list[str] | None = None,
    ) -> tuple[list[FoundItem], int]:
        stmt = select(FoundItem)
        count_stmt = select(func.count()).select_from(FoundItem)

        if category:
            stmt = stmt.where(FoundItem.category == category)
            count_stmt = count_stmt.where(FoundItem.category == category)
        if status:
            stmt = stmt.where(FoundItem.status == status)
            count_stmt = count_stmt.where(FoundItem.status == status)
        elif exclude_statuses:
            stmt = stmt.where(FoundItem.status.notin_(exclude_statuses))
            count_stmt = count_stmt.where(FoundItem.status.notin_(exclude_statuses))
        if keyword:
            pattern = f"%{keyword}%"
            cond = or_(
                FoundItem.item_name.like(pattern),
                FoundItem.description.like(pattern),
                FoundItem.ai_tags.like(pattern),
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if location:
            stmt = stmt.where(FoundItem.found_location.like(f"%{location}%"))
            count_stmt = count_stmt.where(FoundItem.found_location.like(f"%{location}%"))
        if event_time_start is not None:
            stmt = stmt.where(FoundItem.found_time >= event_time_start)
            count_stmt = count_stmt.where(FoundItem.found_time >= event_time_start)
        if event_time_end is not None:
            stmt = stmt.where(FoundItem.found_time <= event_time_end)
            count_stmt = count_stmt.where(FoundItem.found_time <= event_time_end)
        if user_id:
            stmt = stmt.where(FoundItem.user_id == user_id)
            count_stmt = count_stmt.where(FoundItem.user_id == user_id)
        if not include_all_reviews:
            review_visible = FoundItem.review_status == "APPROVED"
            if viewer_user_id is not None:
                review_visible = or_(review_visible, FoundItem.user_id == viewer_user_id)
            stmt = stmt.where(review_visible)
            count_stmt = count_stmt.where(review_visible)
        if is_sensitive is not None:
            val = 1 if is_sensitive else 0
            stmt = stmt.where(FoundItem.is_sensitive == val)
            count_stmt = count_stmt.where(FoundItem.is_sensitive == val)
        if custody_type:
            stmt = stmt.where(FoundItem.custody_type == custody_type)
            count_stmt = count_stmt.where(FoundItem.custody_type == custody_type)

        if sort_by == "EVENT_ASC":
            stmt = stmt.order_by(FoundItem.found_time.asc(), FoundItem.id.asc())
        elif sort_by == "EVENT_DESC":
            stmt = stmt.order_by(FoundItem.found_time.desc(), FoundItem.id.desc())
        elif sort_by == "CREATED_ASC":
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

    async def transition_review(
        self,
        item_id: str,
        *,
        review_status: str,
        review_comment: str | None,
        close_item: bool,
    ) -> bool:
        values: dict[str, object] = {
            "review_status": review_status,
            "review_comment": review_comment,
            "updated_at": func.now(),
        }
        if close_item:
            values["status"] = "CLOSED"
        result = await self._session.execute(
            update(FoundItem)
            .where(FoundItem.id == item_id, FoundItem.review_status == "PENDING")
            .values(**values)
        )
        return bool(getattr(result, "rowcount", 0))

    async def transition_status(
        self, item_id: str, *, expected_status: str, new_status: str
    ) -> bool:
        result = await self._session.execute(
            update(FoundItem)
            .where(FoundItem.id == item_id, FoundItem.status == expected_status)
            .values(status=new_status)
        )
        return bool(getattr(result, "rowcount", 0))

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

    async def list_active(self, *, exclude_id: str | None = None) -> list[FoundItem]:
        """All found items still pending claim (status=PENDING)."""
        stmt = (
            select(FoundItem)
            .join(User, User.id == FoundItem.user_id)
            .where(
                FoundItem.status == "PENDING",
                FoundItem.review_status == "APPROVED",
                User.status == "ACTIVE",
            )
        )
        if exclude_id is not None:
            stmt = stmt.where(FoundItem.id != exclude_id)
        stmt = stmt.order_by(FoundItem.found_time.desc(), FoundItem.id.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


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

    async def delete_by_biz(self, biz_type: str, biz_id: str) -> None:
        images = await self.get_by_biz(biz_type, biz_id)
        for image in images:
            await self._session.delete(image)
        await self._session.flush()


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

    async def delete_by_found_item(self, found_item_id: str) -> None:
        questions = await self.get_by_found_item(found_item_id)
        for question in questions:
            await self._session.delete(question)
        await self._session.flush()


class ItemReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, report: Report) -> Report:
        self._session.add(report)
        await self._session.flush()
        return report

    async def exists_by_reporter_and_target(
        self, *, reporter_id: str, target_type: str, target_id: str
    ) -> bool:
        stmt = select(Report.id).where(
            Report.reporter_id == reporter_id,
            Report.target_type == target_type,
            Report.target_id == target_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count_by_targets(self, target_type: str, target_ids: list[str]) -> dict[str, int]:
        if not target_ids:
            return {}
        stmt = (
            select(Report.target_id, func.count())
            .where(Report.target_type == target_type, Report.target_id.in_(target_ids))
            .group_by(Report.target_id)
        )
        result = await self._session.execute(stmt)
        return {target_id: count for target_id, count in result.all()}


class AdminItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_mixed(
        self,
        *,
        biz_type: str | None,
        target_id: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, object]], int]:
        selects = []
        if biz_type in {None, "LOST"}:
            selects.append(
                select(
                    LostItem.id.label("id"),
                    literal("LOST").label("biz_type"),
                    LostItem.item_name.label("item_name"),
                    LostItem.category.label("category"),
                    LostItem.lost_location.label("location"),
                    LostItem.status.label("status"),
                    LostItem.review_status.label("review_status"),
                    LostItem.review_comment.label("review_comment"),
                    literal(0).label("is_sensitive"),
                    LostItem.user_id.label("user_id"),
                    LostItem.created_at.label("created_at"),
                )
            )
        if biz_type in {None, "FOUND"}:
            selects.append(
                select(
                    FoundItem.id.label("id"),
                    literal("FOUND").label("biz_type"),
                    FoundItem.item_name.label("item_name"),
                    FoundItem.category.label("category"),
                    FoundItem.found_location.label("location"),
                    FoundItem.status.label("status"),
                    FoundItem.review_status.label("review_status"),
                    FoundItem.review_comment.label("review_comment"),
                    FoundItem.is_sensitive.label("is_sensitive"),
                    FoundItem.user_id.label("user_id"),
                    FoundItem.created_at.label("created_at"),
                )
            )
        if not selects:
            return [], 0

        combined = union_all(*selects).subquery()
        base = select(combined)
        count_stmt = select(func.count()).select_from(combined)
        if target_id is not None:
            base = base.where(combined.c.id == target_id)
            count_stmt = count_stmt.where(combined.c.id == target_id)
        stmt = (
            base.order_by(combined.c.created_at.desc(), combined.c.id.desc())
            .offset(offset)
            .limit(limit)
        )
        total = (await self._session.execute(count_stmt)).scalar() or 0
        rows = (await self._session.execute(stmt)).mappings().all()
        return [dict(row) for row in rows], total
