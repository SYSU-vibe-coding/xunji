from datetime import datetime, timedelta, timezone

BEIJING_TZ = timezone(timedelta(hours=8))


def now_beijing() -> datetime:
    """Return current time in Beijing timezone."""
    return datetime.now(BEIJING_TZ)


def format_beijing(dt: datetime) -> str:
    """Format datetime to yyyy-MM-dd HH:mm:ss in Beijing time."""
    # MySQL fields in this project store Beijing wall time without tzinfo.
    # Treating a naive value as the host timezone makes CI (UTC) differ from
    # local deployments (Asia/Shanghai).
    bj = dt.replace(tzinfo=BEIJING_TZ) if dt.tzinfo is None else dt.astimezone(BEIJING_TZ)
    return bj.strftime("%Y-%m-%d %H:%M:%S")


def mask_phone(phone: str) -> str:
    """Mask middle 4 digits of phone: 138****1234."""
    if len(phone) >= 7:
        return phone[:3] + "****" + phone[7:]
    return phone
