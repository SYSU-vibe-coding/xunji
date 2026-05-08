from sqlalchemy.ext.asyncio import AsyncSession

from app.db.ulid import generate_ulid
from app.operation_log.models import OperationLog
from app.operation_log.repository import OperationLogRepository


class OperationLogService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OperationLogRepository(session)

    async def create_log(
        self,
        *,
        operator_id: str,
        operator_role: str,
        biz_type: str,
        biz_id: str,
        action: str,
        detail: str | None = None,
    ) -> None:
        log = OperationLog(
            id=generate_ulid(),
            operator_id=operator_id,
            operator_role=operator_role,
            biz_type=biz_type,
            biz_id=biz_id,
            action=action,
            detail=detail,
        )
        await self._repo.create(log)
