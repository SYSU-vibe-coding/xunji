from typing import Any

from fastapi import APIRouter, Depends, Query

from app.claim.deps import get_claim_service
from app.claim.schemas import (
    ClaimAppealRequest,
    ClaimMyQuery,
    ClaimProofsRequest,
    ClaimReviewRequest,
    ConfirmHandoverRequest,
    CreateClaimRequest,
    CreateHandoverRequest,
)
from app.claim.service import ClaimService
from app.common.response import success
from app.common.validators import validate_ulid
from app.core.auth import get_current_user
from app.user.schemas import CurrentUser

router = APIRouter(tags=["claims"])


@router.post("/claims")
async def create_claim(
    req: CreateClaimRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ClaimService = Depends(get_claim_service),
) -> dict[str, Any]:
    data = await svc.create_claim(req, current_user)
    return success(data=data.model_dump(by_alias=True))


@router.get("/claims/my")
async def list_my_claims(
    role: str = Query(default="CLAIMANT"),
    review_status: str | None = Query(default=None, alias="reviewStatus"),
    page_no: int = Query(default=1, ge=1, alias="pageNo"),
    page_size: int = Query(default=10, ge=1, le=50, alias="pageSize"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ClaimService = Depends(get_claim_service),
) -> dict[str, Any]:
    query = ClaimMyQuery(
        role=role,
        reviewStatus=review_status,
        pageNo=page_no,
        pageSize=page_size,
    )
    data = await svc.list_my_claims(current_user, query)
    return success(data=data)


@router.get("/claims/{claim_id}")
async def get_claim(
    claim_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ClaimService = Depends(get_claim_service),
) -> dict[str, Any]:
    claim_id = validate_ulid(claim_id, "claimId")
    data = await svc.get_claim_detail(claim_id, current_user)
    return success(data=data.model_dump(by_alias=True))


@router.post("/claims/{claim_id}/review")
async def review_claim(
    claim_id: str,
    req: ClaimReviewRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ClaimService = Depends(get_claim_service),
) -> dict[str, Any]:
    claim_id = validate_ulid(claim_id, "claimId")
    data = await svc.review_claim(claim_id, req, current_user)
    return success(data=data)


@router.post("/claims/{claim_id}/proofs")
async def submit_claim_proofs(
    claim_id: str,
    req: ClaimProofsRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ClaimService = Depends(get_claim_service),
) -> dict[str, Any]:
    claim_id = validate_ulid(claim_id, "claimId")
    data = await svc.submit_proofs(claim_id, req, current_user)
    return success(data=data)


@router.post("/claims/{claim_id}/appeal")
async def appeal_claim(
    claim_id: str,
    req: ClaimAppealRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ClaimService = Depends(get_claim_service),
) -> dict[str, Any]:
    claim_id = validate_ulid(claim_id, "claimId")
    data = await svc.appeal_claim(claim_id, req, current_user)
    return success(data=data)


@router.post("/claims/{claim_id}/handover")
async def create_handover(
    claim_id: str,
    req: CreateHandoverRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ClaimService = Depends(get_claim_service),
) -> dict[str, Any]:
    claim_id = validate_ulid(claim_id, "claimId")
    data = await svc.create_handover(claim_id, req, current_user)
    return success(data=data.model_dump(by_alias=True))


@router.post("/claims/{claim_id}/handover/confirm")
async def confirm_handover(
    claim_id: str,
    req: ConfirmHandoverRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ClaimService = Depends(get_claim_service),
) -> dict[str, Any]:
    claim_id = validate_ulid(claim_id, "claimId")
    data = await svc.confirm_handover(claim_id, req, current_user)
    return success(data=data)
