from typing import Any

from fastapi import APIRouter, Depends

from app.common.response import success
from app.core.auth import get_current_user
from app.user.deps import get_user_service
from app.user.schemas import (
    CertificationRequest,
    CurrentUser,
    LoginRequest,
    RegisterRequest,
    SmsCodeRequest,
    UpdateProfileRequest,
)
from app.user.service import UserService

router = APIRouter(tags=["auth", "user"])


# ---- Auth (public) ----


@router.post("/auth/sms-code")
async def send_sms_code(
    req: SmsCodeRequest,
    svc: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    data = await svc.send_sms_code(req)
    return success(data=data.model_dump(by_alias=True, exclude_none=True))


@router.post("/auth/login")
async def login(
    req: LoginRequest,
    svc: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    data = await svc.login(req)
    return success(data=data.model_dump(by_alias=True))


@router.post("/auth/register")
async def register(
    req: RegisterRequest,
    svc: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    data = await svc.register(req)
    return success(data=data.model_dump(by_alias=True))


# ---- User profile (authenticated) ----


@router.get("/users/me")
async def get_my_profile(
    current_user: CurrentUser = Depends(get_current_user),
    svc: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    data = await svc.get_profile(current_user)
    return success(data=data.model_dump(by_alias=True))


@router.put("/users/me")
async def update_my_profile(
    req: UpdateProfileRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    data = await svc.update_profile(current_user, req)
    return success(data=data.model_dump(by_alias=True))


@router.post("/users/me/certification")
async def submit_my_certification(
    req: CertificationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    data = await svc.submit_certification(current_user, req)
    return success(data=data.model_dump(by_alias=True))


@router.get("/users/me/certification")
async def get_my_certification(
    current_user: CurrentUser = Depends(get_current_user),
    svc: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    data = await svc.get_certification(current_user)
    return success(data=data.model_dump(by_alias=True) if data is not None else None)


@router.post("/users/me/cancel")
async def cancel_my_account(
    current_user: CurrentUser = Depends(get_current_user),
    svc: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    data = await svc.cancel_account(current_user)
    return success(data=data)
