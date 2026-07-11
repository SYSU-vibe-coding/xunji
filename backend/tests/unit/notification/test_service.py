from app.notification.schemas import NotificationQuery
from app.notification.service import NotificationService


async def test_notification_service_list_and_mark_read(session, seeded_users):
    svc = NotificationService(session)
    notice = await svc.create_notice(
        user_id="01TESTUSER000000000000001",
        notice_type="CLAIM_REQUEST",
        title="测试通知",
        content="content",
        related_type="CLAIM",
        related_id="01ARZ3NDEKTSV4RRFFQ69G5FA",
    )
    await session.commit()

    listed = await svc.list_notifications(
        "01TESTUSER000000000000001", NotificationQuery(pageNo=1, pageSize=10)
    )
    assert listed["total"] == 1

    unread = await svc.get_unread_count("01TESTUSER000000000000001")
    assert unread.total == 1
    assert unread.by_type["CLAIM_REQUEST"] == 1

    marked = await svc.mark_read(notice.id, "01TESTUSER000000000000001")
    assert marked == {"id": notice.id, "isRead": True}
    unread = await svc.get_unread_count("01TESTUSER000000000000001")
    assert unread.total == 0

    marked_all = await svc.mark_all_read("01TESTUSER000000000000001", None)
    assert marked_all == {"updated": 0}
