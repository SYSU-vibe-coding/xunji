from unittest.mock import AsyncMock

import pytest
from app.credit.models import CreditLog
from app.credit.schemas import CreditLogQuery
from app.credit.service import CreditService
from app.notification.models import Notification
from app.operation_log.models import OperationLog
from app.user.service import UserService
from sqlalchemy import func, select

USER_ID = "01TESTUSER000000000000001"
ADMIN_ID = "01TESTADMIN00000000000001"


async def _change_credit(
    svc: CreditService,
    *,
    delta_score: int = 10,
    reason_code: str = "HANDOVER_SUCCESS",
    reason_text: str | None = "交接完成",
    biz_id: str = "01ARZ3NDEKTSV4RRFFQ69G5FA",
) -> bool:
    return await svc.change_credit(
        user_id=USER_ID,
        delta_score=delta_score,
        reason_code=reason_code,
        reason_text=reason_text,
        biz_type="CLAIM",
        biz_id=biz_id,
        operator_id=ADMIN_ID,
        operator_role="ADMIN",
    )


async def test_change_credit_is_idempotent_and_creates_log(session, seeded_users):
    svc = CreditService(session)
    changed = await _change_credit(svc)
    repeated = await _change_credit(svc)

    assert session.in_transaction()
    await session.commit()

    user = await UserService(session).get_user_internal(USER_ID)
    logs = await svc.list_user_logs(
        USER_ID, CreditLogQuery(pageNo=1, pageSize=10)
    )
    assert changed is True
    assert repeated is False
    assert user is not None
    assert user.credit_score == 110
    assert logs["total"] == 1


async def test_change_credit_does_not_commit(session, seeded_users, monkeypatch):
    commit = AsyncMock()
    monkeypatch.setattr(session, "commit", commit)

    changed = await _change_credit(CreditService(session))

    assert changed is True
    commit.assert_not_awaited()


async def test_change_credit_records_clipped_actual_delta_at_upper_bound(session, seeded_users):
    user = await UserService(session).get_user_internal(USER_ID)
    assert user is not None
    user.credit_score = 995
    await session.flush()

    changed = await _change_credit(CreditService(session))

    log = (
        await session.execute(select(CreditLog).where(CreditLog.user_id == USER_ID))
    ).scalar_one()
    notice = (
        await session.execute(
            select(Notification).where(Notification.notice_type == "CREDIT_CHANGED")
        )
    ).scalar_one()
    operation = (
        await session.execute(
            select(OperationLog).where(OperationLog.action == "CREDIT_CHANGE")
        )
    ).scalar_one()
    assert changed is True
    assert user.credit_score == 999
    assert log.delta_score == 4
    assert notice.content == "交接完成: +4,当前积分 999"
    assert operation.detail == f"{USER_ID} HANDOVER_SUCCESS +4 -> 999"


async def test_change_credit_records_zero_when_lower_bound_clips_all_delta(session, seeded_users):
    user = await UserService(session).get_user_internal(USER_ID)
    assert user is not None
    user.credit_score = 0
    await session.flush()

    changed = await _change_credit(
        CreditService(session),
        delta_score=-20,
        reason_code="FAKE_PUBLISH_CONFIRMED",
        reason_text="虚假发布核实",
    )

    log = (
        await session.execute(select(CreditLog).where(CreditLog.user_id == USER_ID))
    ).scalar_one()
    notice = (
        await session.execute(
            select(Notification).where(Notification.notice_type == "CREDIT_CHANGED")
        )
    ).scalar_one()
    operation = (
        await session.execute(
            select(OperationLog).where(OperationLog.action == "CREDIT_CHANGE")
        )
    ).scalar_one()
    assert changed is True
    assert user.credit_score == 0
    assert log.delta_score == 0
    assert notice.content == "虚假发布核实: 0 (已达积分边界),当前积分 0"
    assert operation.detail == f"{USER_ID} FAKE_PUBLISH_CONFIRMED 0 (已达积分边界) -> 0"


async def test_unique_conflict_rolls_back_only_credit_savepoint(
    session, seeded_users, monkeypatch
):
    user = await UserService(session).get_user_internal(USER_ID)
    assert user is not None
    user.credit_score = 110
    session.add(
        CreditLog(
            id="01EXISTINGCREDITLOG0000001",
            user_id=USER_ID,
            delta_score=10,
            reason_code="HANDOVER_SUCCESS",
            reason_text="并发请求已完成",
            biz_type="CLAIM",
            biz_id="01ARZ3NDEKTSV4RRFFQ69G5FA",
        )
    )
    await session.commit()

    user.nickname = "外层事务变更"
    svc = CreditService(session)
    original_exists = svc._repo.exists_by_biz

    async def simulate_stale_precheck(
        *,
        user_id: str,
        biz_type: str,
        biz_id: str,
        reason_code: str,
        for_update: bool = False,
    ) -> bool:
        if not for_update:
            return False
        return await original_exists(
            user_id=user_id,
            biz_type=biz_type,
            biz_id=biz_id,
            reason_code=reason_code,
            for_update=True,
        )

    monkeypatch.setattr(svc._repo, "exists_by_biz", simulate_stale_precheck)

    changed = await _change_credit(svc)
    await session.commit()

    refreshed_user = await UserService(session).get_user_internal(USER_ID)
    log_count = await session.scalar(
        select(func.count()).select_from(CreditLog).where(CreditLog.user_id == USER_ID)
    )
    notice_count = await session.scalar(select(func.count()).select_from(Notification))
    operation_count = await session.scalar(select(func.count()).select_from(OperationLog))
    assert changed is False
    assert refreshed_user is not None
    assert refreshed_user.credit_score == 110
    assert refreshed_user.nickname == "外层事务变更"
    assert log_count == 1
    assert notice_count == 0
    assert operation_count == 0


@pytest.mark.parametrize(
    ("delta_score", "reason_code"),
    [
        (0, "HANDOVER_SUCCESS"),
        (-10, "HANDOVER_SUCCESS"),
        (10.0, "HANDOVER_SUCCESS"),
        (10, "UNKNOWN_REASON"),
    ],
)
async def test_change_credit_validates_delta_and_reason(
    session, seeded_users, delta_score, reason_code
):
    with pytest.raises(ValueError):
        await _change_credit(
            CreditService(session),
            delta_score=delta_score,
            reason_code=reason_code,
        )
