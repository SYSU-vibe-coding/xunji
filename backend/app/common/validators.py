import re

from app.common.errors import BizError, ErrorCode

_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def validate_ulid(value: str, field_name: str = "id") -> str:
    if not _ULID_RE.fullmatch(value):
        raise BizError(ErrorCode.PARAM_ERROR, f"{field_name} must be a valid ULID")
    return value
