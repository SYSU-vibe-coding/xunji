from sqlalchemy import func, select
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


class AnnouncementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, announcement: Announcement) -> Announcement:
        self._session.add(announcement)
        await self._session.flush()
        return announcement
