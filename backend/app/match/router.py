from typing import Any

from fastapi import APIRouter, Depends, Query

from app.common.response import success
from app.common.validators import validate_ulid
from app.core.auth import get_current_user
from app.match.deps import get_match_service
from app.match.schemas import MatchListQuery, MatchRecalculateRequest
from app.match.service import MatchService
from app.user.schemas import CurrentUser

router = APIRouter(tags=["matches"])


@router.get("/matches")
async def list_matches(
    biz_type: str | None = Query(default=None, alias="bizType"),
    biz_id: str | None = Query(default=None, alias="bizId"),
    page_no: int = Query(default=1, ge=1, alias="pageNo"),
    page_size: int = Query(default=20, ge=1, le=50, alias="pageSize"),
    min_score: float = Query(default=70, ge=0, le=100, alias="minScore"),
    status: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    svc: MatchService = Depends(get_match_service),
) -> dict[str, Any]:
    query = MatchListQuery(
        bizType=biz_type,
        bizId=biz_id,
        pageNo=page_no,
        pageSize=page_size,
        minScore=min_score,
        status=status,
    )
    if query.biz_type is not None and query.biz_id is not None:
        query.biz_id = validate_ulid(query.biz_id, "bizId")
        data = await svc.list_matches(query, current_user)
    else:
        data = await svc.list_my_matches(query, current_user)
    return success(data=data)


@router.post("/matches/recalculate")
async def recalculate_matches(
    req: MatchRecalculateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: MatchService = Depends(get_match_service),
) -> dict[str, Any]:
    req.biz_id = validate_ulid(req.biz_id, "bizId")
    data = await svc.recalculate(req, current_user)
    return success(data=data.model_dump(by_alias=True))


@router.get("/matches/{match_id}")
async def get_match(
    match_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    svc: MatchService = Depends(get_match_service),
) -> dict[str, Any]:
    match_id = validate_ulid(match_id, "matchId")
    data = await svc.get_match_detail(match_id, current_user)
    return success(data=data.model_dump(by_alias=True))
