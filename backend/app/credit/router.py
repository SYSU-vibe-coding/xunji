from typing import Any

from fastapi import APIRouter, Depends, Query

from app.common.response import success
from app.core.auth import get_current_user
from app.credit.deps import get_credit_service
from app.credit.schemas import CreditLogQuery
from app.credit.service import CreditService
from app.user.schemas import CurrentUser

router = APIRouter(tags=["credit"])


@router.get("/users/me/credits")
async def list_my_credit_logs(
    page_no: int = Query(default=1, ge=1, alias="pageNo"),
    page_size: int = Query(default=10, ge=1, le=50, alias="pageSize"),
    reason_code: str | None = Query(default=None, alias="reasonCode"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: CreditService = Depends(get_credit_service),
) -> dict[str, Any]:
    query = CreditLogQuery(pageNo=page_no, pageSize=page_size, reasonCode=reason_code)
    data = await svc.list_user_logs(current_user.id, query)
    return success(data=data)
