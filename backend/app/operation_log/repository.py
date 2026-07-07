from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.operation_log.models import OperationLog


class OperationLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, log: OperationLog) -> None:
        self._session.add(log)
        await self._session.flush()

    async def list_with_filter(
        self,
        *,
        biz_type: str | None = None,
        action: str | None = None,
        operator_role: str | None = None,
        keyword: str | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[list[OperationLog], int]:
        stmt: Select[tuple[OperationLog]] = select(OperationLog)
        count_stmt = select(func.count(OperationLog.id))

        if biz_type:
            stmt = stmt.where(OperationLog.biz_type == biz_type)
            count_stmt = count_stmt.where(OperationLog.biz_type == biz_type)
        if action:
            stmt = stmt.where(OperationLog.action == action)
            count_stmt = count_stmt.where(OperationLog.action == action)
        if operator_role:
            stmt = stmt.where(OperationLog.operator_role == operator_role)
            count_stmt = count_stmt.where(OperationLog.operator_role == operator_role)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(OperationLog.detail.like(like))
            count_stmt = count_stmt.where(OperationLog.detail.like(like))

        stmt = stmt.order_by(OperationLog.created_at.desc()).offset(offset).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        total = (await self._session.execute(count_stmt)).scalar_one()
        return list(rows), total
