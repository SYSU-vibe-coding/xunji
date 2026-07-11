from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import PaginationParams, paginate
from app.common.utils import format_beijing
from app.credit.models import CreditLog
from app.credit.repository import CreditLogRepository
from app.credit.schemas import CreditLogItem, CreditLogQuery, credit_delta_for_reason
from app.db.ulid import generate_ulid
from app.notification.service import NotificationService
from app.operation_log.service import OperationLogService
from app.user.service import UserService


class CreditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CreditLogRepository(session)
        self._user_svc = UserService(session)
        self._notification_svc = NotificationService(session)
        self._log_svc = OperationLogService(session)

    async def change_credit(
        self,
        *,
        user_id: str,
        delta_score: int,
        reason_code: str,
        reason_text: str | None,
        biz_type: str,
        biz_id: str,
        operator_id: str,
        operator_role: str,
    ) -> bool:
        """Apply one credit event without committing the caller's transaction."""
        expected_delta = credit_delta_for_reason(reason_code)
        if expected_delta is None:
            msg = f"Unsupported credit reason: {reason_code}"
            raise ValueError(msg)
        if type(delta_score) is not int or delta_score != expected_delta:
            msg = f"delta_score must be {expected_delta} for reason_code {reason_code}"
            raise ValueError(msg)

        exists = await self._repo.exists_by_biz(
            user_id=user_id,
            biz_type=biz_type,
            biz_id=biz_id,
            reason_code=reason_code,
        )
        if exists:
            return False

        try:
            async with self._session.begin_nested():
                new_score, actual_delta = await self._user_svc.update_credit_score_internal(
                    user_id, delta_score
                )
                log = CreditLog(
                    id=generate_ulid(),
                    user_id=user_id,
                    delta_score=actual_delta,
                    reason_code=reason_code,
                    reason_text=reason_text,
                    biz_type=biz_type,
                    biz_id=biz_id,
                )
                await self._repo.create(log)
                delta_text = f"{actual_delta:+d}" if actual_delta != 0 else "0 (已达积分边界)"
                await self._notification_svc.create_notice(
                    user_id=user_id,
                    notice_type="CREDIT_CHANGED",
                    title="信誉积分变动",
                    content=f"{reason_text or reason_code}: {delta_text},当前积分 {new_score}",
                    related_type=biz_type,
                    related_id=biz_id,
                )
                await self._log_svc.create_log(
                    operator_id=operator_id,
                    operator_role=operator_role,
                    biz_type=biz_type,
                    biz_id=biz_id,
                    action="CREDIT_CHANGE",
                    detail=f"{user_id} {reason_code} {delta_text} -> {new_score}",
                )
        except IntegrityError:
            exists = await self._repo.exists_by_biz(
                user_id=user_id,
                biz_type=biz_type,
                biz_id=biz_id,
                reason_code=reason_code,
                for_update=True,
            )
            if not exists:
                raise
            return False
        return True

    async def list_user_logs(self, user_id: str, query: CreditLogQuery) -> dict[str, Any]:
        offset = (query.page_no - 1) * query.page_size
        logs, total = await self._repo.list_by_user(
            user_id=user_id,
            reason_code=query.reason_code,
            offset=offset,
            limit=query.page_size,
        )
        result = [self._to_item(log).model_dump(by_alias=True) for log in logs]
        params = PaginationParams(pageNo=query.page_no, pageSize=query.page_size)
        return paginate(result, total, params)

    def _to_item(self, log: CreditLog) -> CreditLogItem:
        return CreditLogItem(
            id=log.id,
            user_id=log.user_id,
            delta_score=log.delta_score,
            reason_code=log.reason_code,
            reason_text=log.reason_text,
            biz_type=log.biz_type,
            biz_id=log.biz_id,
            created_at=format_beijing(log.created_at),
        )
