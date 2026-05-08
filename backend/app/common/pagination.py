import math
from typing import Any

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Query params for paginated endpoints."""

    pageNo: int = Field(default=1, ge=1, description="Page number starting from 1")
    pageSize: int = Field(default=10, ge=1, le=50, description="Items per page, max 50")

    @property
    def offset(self) -> int:
        return (self.pageNo - 1) * self.pageSize


class PaginatedData(BaseModel):
    """Paginated response body inside `data`."""

    list: list[Any]
    pageNo: int
    pageSize: int
    total: int
    totalPages: int


def paginate(items: list[Any], total: int, params: PaginationParams) -> dict[str, Any]:
    """Build the pagination data dict."""
    total_pages = math.ceil(total / params.pageSize) if params.pageSize > 0 else 0
    return {
        "list": items,
        "pageNo": params.pageNo,
        "pageSize": params.pageSize,
        "total": total,
        "totalPages": total_pages,
    }
