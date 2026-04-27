from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile

from app.common.response import success
from app.core.auth import get_current_user
from app.item.deps import get_item_service
from app.item.schemas import (
    ChangeStatusRequest,
    CreateFoundItemRequest,
    CreateLostItemRequest,
    FoundItemQuery,
    LostItemQuery,
)
from app.item.service import ItemService
from app.user.schemas import CurrentUser

router = APIRouter(tags=["items"])


# ---- Lost Items ----


@router.post("/lost-items")
async def create_lost_item(
    req: CreateLostItemRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
) -> dict[str, Any]:
    data = await svc.create_lost_item(req, current_user, background_tasks)
    return success(data=data.model_dump(by_alias=True))


@router.get("/lost-items")
async def list_lost_items(
    page_no: int = Query(default=1, ge=1, alias="pageNo"),
    page_size: int = Query(default=10, ge=1, le=50, alias="pageSize"),
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    location: str | None = Query(default=None),
    sort_by: str = Query(default="CREATED_DESC", alias="sortBy"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
) -> dict[str, Any]:
    query = LostItemQuery(
        pageNo=page_no,
        pageSize=page_size,
        category=category,
        status=status,
        keyword=keyword,
        location=location,
        sortBy=sort_by,
    )
    data = await svc.list_lost_items(query)
    return success(data=data)


@router.get("/lost-items/{item_id}")
async def get_lost_item(
    item_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
) -> dict[str, Any]:
    data = await svc.get_lost_item_detail(item_id, current_user)
    return success(data=data)


@router.patch("/lost-items/{item_id}/status")
async def change_lost_item_status(
    item_id: str,
    req: ChangeStatusRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
) -> dict[str, Any]:
    data = await svc.change_lost_item_status(item_id, req, current_user)
    return success(data=data)


# ---- Found Items ----


@router.post("/found-items")
async def create_found_item(
    req: CreateFoundItemRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
) -> dict[str, Any]:
    data = await svc.create_found_item(req, current_user, background_tasks)
    return success(data=data.model_dump(by_alias=True))


@router.get("/found-items")
async def list_found_items(
    page_no: int = Query(default=1, ge=1, alias="pageNo"),
    page_size: int = Query(default=10, ge=1, le=50, alias="pageSize"),
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    location: str | None = Query(default=None),
    is_sensitive: bool | None = Query(default=None, alias="isSensitive"),
    custody_type: str | None = Query(default=None, alias="custodyType"),
    sort_by: str = Query(default="CREATED_DESC", alias="sortBy"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
) -> dict[str, Any]:
    query = FoundItemQuery(
        pageNo=page_no,
        pageSize=page_size,
        category=category,
        status=status,
        keyword=keyword,
        location=location,
        isSensitive=is_sensitive,
        custodyType=custody_type,
        sortBy=sort_by,
    )
    data = await svc.list_found_items(query)
    return success(data=data)


@router.get("/found-items/{item_id}")
async def get_found_item(
    item_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
) -> dict[str, Any]:
    data = await svc.get_found_item_detail(item_id, current_user)
    return success(data=data)


@router.patch("/found-items/{item_id}/status")
async def change_found_item_status(
    item_id: str,
    req: ChangeStatusRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
) -> dict[str, Any]:
    data = await svc.change_found_item_status(item_id, req, current_user)
    return success(data=data)


# ---- File Upload ----


@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    biz_type: str = Form(..., alias="bizType"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
) -> dict[str, Any]:
    data = await svc.upload_file(file, biz_type, current_user)
    return success(data=data)
