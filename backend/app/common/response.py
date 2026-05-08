import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel


class ResponseSchema(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None
    requestId: str = ""
    timestamp: str = ""


def success(
    data: Any = None, message: str = "success", request_id: str | None = None
) -> dict[str, Any]:
    """Build a success envelope dict."""
    return {
        "code": 0,
        "message": message,
        "data": data,
        "requestId": request_id or uuid.uuid4().hex,
        "timestamp": datetime.now(UTC).astimezone().isoformat(),
    }
