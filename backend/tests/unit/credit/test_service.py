from app.credit.schemas import CreditLogQuery
from app.credit.service import CreditService
from app.user.service import UserService


async def test_change_credit_is_idempotent_and_creates_log(session, seeded_users):
    svc = CreditService(session)
    changed = await svc.change_credit(
        user_id="01TESTUSER000000000000001",
        delta_score=10,
        reason_code="HANDOVER_SUCCESS",
        reason_text="交接完成",
        biz_type="CLAIM",
        biz_id="01ARZ3NDEKTSV4RRFFQ69G5FA",
        operator_id="01TESTADMIN00000000000001",
        operator_role="ADMIN",
    )
    repeated = await svc.change_credit(
        user_id="01TESTUSER000000000000001",
        delta_score=10,
        reason_code="HANDOVER_SUCCESS",
        reason_text="交接完成",
        biz_type="CLAIM",
        biz_id="01ARZ3NDEKTSV4RRFFQ69G5FA",
        operator_id="01TESTADMIN00000000000001",
        operator_role="ADMIN",
    )
    await session.commit()

    user = await UserService(session).get_user_internal("01TESTUSER000000000000001")
    logs = await svc.list_user_logs(
        "01TESTUSER000000000000001", CreditLogQuery(pageNo=1, pageSize=10)
    )
    assert changed is True
    assert repeated is False
    assert user is not None
    assert user.credit_score == 110
    assert logs["total"] == 1
