from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.credit.models import CreditLog


class CreditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, log: CreditLog) -> CreditLog:
        self._session.add(log)
        await self._session.flush()
        return log

    async def exists_by_biz(
        self,
        *,
        user_id: str,
        biz_type: str,
        biz_id: str,
        reason_code: str,
    ) -> bool:
        stmt = select(CreditLog).where(
            CreditLog.user_id == user_id,
            CreditLog.biz_type == biz_type,
            CreditLog.biz_id == biz_id,
            CreditLog.reason_code == reason_code,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_by_user(
        self,
        *,
        user_id: str,
        reason_code: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[CreditLog], int]:
        stmt = select(CreditLog).where(CreditLog.user_id == user_id)
        count_stmt = select(func.count()).select_from(CreditLog).where(CreditLog.user_id == user_id)
        if reason_code:
            stmt = stmt.where(CreditLog.reason_code == reason_code)
            count_stmt = count_stmt.where(CreditLog.reason_code == reason_code)
        stmt = stmt.order_by(CreditLog.created_at.desc()).offset(offset).limit(limit)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total
