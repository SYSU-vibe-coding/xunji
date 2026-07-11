from datetime import UTC, datetime

from app.common.utils import format_beijing


def test_format_beijing_treats_naive_datetime_as_beijing_wall_time() -> None:
    assert format_beijing(datetime(2026, 7, 10, 12, 30)) == "2026-07-10 12:30:00"


def test_format_beijing_converts_aware_datetime() -> None:
    assert format_beijing(datetime(2026, 7, 10, 4, 30, tzinfo=UTC)) == "2026-07-10 12:30:00"
