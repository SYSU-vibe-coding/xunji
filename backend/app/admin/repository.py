from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import Announcement, Report


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, report: Report) -> Report:
        self._session.add(report)
        await self._session.flush()
        return report

    async def get_by_id(self, report_id: str) -> Report | None:
        result = await self._session.execute(select(Report).where(Report.id == report_id))
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, report_id: str) -> Report | None:
        result = await self._session.execute(
            select(Report).where(Report.id == report_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_with_filter(
        self,
        *,
        handle_status: str | None,
        target_type: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Report], int]:
        stmt = select(Report)
        count_stmt = select(func.count()).select_from(Report)
        if handle_status:
            stmt = stmt.where(Report.handle_status == handle_status)
            count_stmt = count_stmt.where(Report.handle_status == handle_status)
        if target_type:
            stmt = stmt.where(Report.target_type == target_type)
            count_stmt = count_stmt.where(Report.target_type == target_type)
        stmt = stmt.order_by(Report.created_at.desc()).offset(offset).limit(limit)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def update(self, report: Report) -> Report:
        await self._session.merge(report)
        await self._session.flush()
        return report

    async def transition_open(
        self,
        *,
        report_id: str,
        expected_status: str,
        handle_status: str,
        handle_result: str | None,
        handler_id: str,
        reported_user_id: str,
    ) -> bool:
        result = await self._session.execute(
            update(Report)
            .where(
                Report.id == report_id,
                Report.handle_status == expected_status,
                Report.handle_status.in_({"PENDING", "PROCESSING"}),
            )
            .values(
                handle_status=handle_status,
                handle_result=handle_result,
                handler_id=handler_id,
                reported_user_id=reported_user_id,
                updated_at=func.now(),
            )
        )
        return bool(getattr(result, "rowcount", 0))


class AnnouncementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, announcement: Announcement) -> Announcement:
        self._session.add(announcement)
        await self._session.flush()
        return announcement

    async def get_by_id(self, announcement_id: str) -> Announcement | None:
        result = await self._session.execute(
            select(Announcement).where(Announcement.id == announcement_id)
        )
        return result.scalar_one_or_none()

    async def list_for_admin(
        self, *, status: str | None, offset: int, limit: int
    ) -> tuple[list[Announcement], int]:
        stmt = select(Announcement)
        count_stmt = select(func.count()).select_from(Announcement)
        if status is not None:
            stmt = stmt.where(Announcement.status == status)
            count_stmt = count_stmt.where(Announcement.status == status)
        stmt = (
            stmt.order_by(Announcement.created_at.desc(), Announcement.id.desc())
            .offset(offset)
            .limit(limit)
        )
        total = (await self._session.execute(count_stmt)).scalar() or 0
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def transition_status(
        self,
        *,
        announcement_id: str,
        expected_status: str,
        new_status: str,
        published_by: str | None = None,
        published_at: datetime | None = None,
    ) -> bool:
        values: dict[str, object | None] = {
            "status": new_status,
            "updated_at": func.now(),
        }
        if new_status == "PUBLISHED":
            values.update(published_by=published_by, published_at=published_at)
        result = await self._session.execute(
            update(Announcement)
            .where(
                Announcement.id == announcement_id,
                Announcement.status == expected_status,
            )
            .values(**values)
        )
        return bool(getattr(result, "rowcount", 0))

    async def list_published(self, *, offset: int, limit: int) -> tuple[list[Announcement], int]:
        condition = Announcement.status == "PUBLISHED"
        stmt = (
            select(Announcement)
            .where(condition)
            .order_by(Announcement.published_at.desc(), Announcement.id.desc())
            .offset(offset)
            .limit(limit)
        )
        count_stmt = select(func.count()).select_from(Announcement).where(condition)
        total = (await self._session.execute(count_stmt)).scalar() or 0
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_published_by_id(self, announcement_id: str) -> Announcement | None:
        result = await self._session.execute(
            select(Announcement).where(
                Announcement.id == announcement_id,
                Announcement.status == "PUBLISHED",
            )
        )
        return result.scalar_one_or_none()
