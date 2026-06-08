import io
import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks, UploadFile
from loguru import logger
from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import BizError, ErrorCode
from app.common.pagination import PaginationParams, paginate
from app.common.utils import format_beijing, now_beijing
from app.core.ai_client import AIClient
from app.core.config import settings
from app.db.ulid import generate_ulid
from app.item.models import FoundItem, ItemImage, LostItem, VerifyQuestion
from app.item.repository import (
    FoundItemRepository,
    ItemImageRepository,
    LostItemRepository,
    VerifyQuestionRepository,
)
from app.item.schemas import (
    VALID_BIZ_TYPES,
    ChangeStatusRequest,
    CreateFoundItemRequest,
    CreateFoundItemResponse,
    CreateFoundItemsBatchFailure,
    CreateFoundItemsBatchResponse,
    CreateLostItemRequest,
    CreateLostItemResponse,
    FileUploadResponse,
    FoundItemDetail,
    FoundItemListItem,
    FoundItemQuery,
    LostItemDetail,
    LostItemListItem,
    LostItemQuery,
    UpdateLostItemRequest,
    VerifyQuestionOutput,
)
from app.operation_log.service import OperationLogService
from app.user.schemas import CurrentUser

# Allowed state transitions
LOST_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "SEARCHING": {"FOUND", "CLOSED"},
}
FOUND_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"CLOSED"},
}


class ItemService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        ai_client: AIClient | None = None,
    ) -> None:
        self._session = session
        self._lost_repo = LostItemRepository(session)
        self._found_repo = FoundItemRepository(session)
        self._image_repo = ItemImageRepository(session)
        self._question_repo = VerifyQuestionRepository(session)
        self._log_svc = OperationLogService(session)
        self._ai_client = ai_client

    # ---------- Lost Items ----------

    async def create_lost_item(
        self,
        req: CreateLostItemRequest,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
    ) -> CreateLostItemResponse:
        dup = await self._lost_repo.check_duplicate(
            current_user.id, req.item_name, req.lost_time_start, req.lost_location
        )
        if dup:
            raise BizError(ErrorCode.DUPLICATE_SUBMIT)

        if len(req.image_urls) > 5:
            raise BizError(ErrorCode.IMAGE_EXCEED)

        item_id = generate_ulid()
        lost_item = LostItem(
            id=item_id,
            user_id=current_user.id,
            item_name=req.item_name,
            category=req.category,
            description=req.description,
            lost_time_start=datetime.strptime(req.lost_time_start, "%Y-%m-%d %H:%M:%S"),
            lost_time_end=datetime.strptime(req.lost_time_end, "%Y-%m-%d %H:%M:%S"),
            lost_location=req.lost_location,
            subscribe_match=1 if req.subscribe_match else 0,
            status="SEARCHING",
            review_status="APPROVED",
        )

        await self._lost_repo.create(lost_item)

        if req.image_urls:
            images = [
                ItemImage(
                    id=generate_ulid(),
                    biz_type="LOST",
                    biz_id=item_id,
                    image_url=url,
                    sort_order=idx,
                )
                for idx, url in enumerate(req.image_urls)
            ]
            await self._image_repo.create_batch(images)

        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="LOST",
            biz_id=item_id,
            action="CREATE",
            detail=f"发布失物: {req.item_name}",
        )
        await self._session.commit()

        background_tasks.add_task(_trigger_match_for_lost, item_id)
        return CreateLostItemResponse(id=item_id, status="SEARCHING")

    async def list_lost_items(self, query: LostItemQuery) -> dict[str, Any]:
        offset = (query.page_no - 1) * query.page_size
        items, total = await self._lost_repo.list_with_filter(
            category=query.category,
            status=query.status,
            keyword=query.keyword,
            location=query.location,
            sort_by=query.sort_by,
            offset=offset,
            limit=query.page_size,
        )

        result_list = []
        for item in items:
            images = await self._image_repo.get_by_biz("LOST", item.id)
            cover = images[0].image_url if images else None
            result_list.append(
                LostItemListItem(
                    id=item.id,
                    user_id=item.user_id,
                    item_name=item.item_name,
                    category=item.category,
                    description=item.description,
                    lost_time_start=format_beijing(item.lost_time_start),
                    lost_time_end=format_beijing(item.lost_time_end),
                    lost_location=item.lost_location,
                    status=item.status,
                    review_status=item.review_status,
                    cover_image_url=cover,
                    created_at=format_beijing(item.created_at),
                ).model_dump(by_alias=True)
            )

        params = PaginationParams(pageNo=query.page_no, pageSize=query.page_size)
        return paginate(result_list, total, params)

    async def get_lost_item_detail(self, item_id: str, current_user: CurrentUser) -> dict[str, Any]:
        item = await self._lost_repo.get_by_id(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)

        images = await self._image_repo.get_by_biz("LOST", item_id)
        image_urls = [img.image_url for img in images]
        cover = image_urls[0] if image_urls else None

        match_count = None
        if item.user_id == current_user.id:
            match_count = 0  # Stub

        detail = LostItemDetail(
            id=item.id,
            user_id=item.user_id,
            item_name=item.item_name,
            category=item.category,
            description=item.description,
            lost_time_start=format_beijing(item.lost_time_start),
            lost_time_end=format_beijing(item.lost_time_end),
            lost_location=item.lost_location,
            subscribe_match=bool(item.subscribe_match),
            status=item.status,
            review_status=item.review_status,
            cover_image_url=cover,
            image_urls=image_urls,
            match_count=match_count,
            created_at=format_beijing(item.created_at),
            updated_at=format_beijing(item.updated_at),
        )
        return detail.model_dump(by_alias=True)

    async def update_lost_item(
        self, item_id: str, req: UpdateLostItemRequest, current_user: CurrentUser
    ) -> dict[str, str]:
        item = await self._lost_repo.get_by_id(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)
        if item.user_id != current_user.id:
            raise BizError(ErrorCode.NOT_PUBLISHER)
        if item.status == "FOUND":
            raise BizError(ErrorCode.INVALID_STATE)

        if len(req.image_urls) > 5:
            raise BizError(ErrorCode.IMAGE_EXCEED)

        item.item_name = req.item_name
        item.category = req.category
        item.description = req.description
        item.lost_time_start = datetime.strptime(req.lost_time_start, "%Y-%m-%d %H:%M:%S")
        item.lost_time_end = datetime.strptime(req.lost_time_end, "%Y-%m-%d %H:%M:%S")
        item.lost_location = req.lost_location
        item.subscribe_match = 1 if req.subscribe_match else 0
        if item.status == "CLOSED":
            item.status = "SEARCHING"
        item.review_status = "PENDING"

        await self._lost_repo.update(item)
        await self._image_repo.delete_by_biz("LOST", item_id)
        if req.image_urls:
            images = [
                ItemImage(
                    id=generate_ulid(),
                    biz_type="LOST",
                    biz_id=item_id,
                    image_url=url,
                    sort_order=idx,
                )
                for idx, url in enumerate(req.image_urls)
            ]
            await self._image_repo.create_batch(images)

        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="LOST",
            biz_id=item_id,
            action="UPDATE",
            detail=f"修改失物: {req.item_name}",
        )
        await self._session.commit()
        return {"id": item_id, "status": item.status, "reviewStatus": item.review_status}

    async def delete_lost_item(self, item_id: str, current_user: CurrentUser) -> dict[str, str]:
        item = await self._lost_repo.get_by_id(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)
        if item.user_id != current_user.id:
            raise BizError(ErrorCode.NOT_PUBLISHER)
        if item.status == "FOUND":
            raise BizError(ErrorCode.INVALID_STATE)

        await self._image_repo.delete_by_biz("LOST", item_id)
        await self._lost_repo.delete(item)
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="LOST",
            biz_id=item_id,
            action="DELETE",
            detail=f"删除失物: {item.item_name}",
        )
        await self._session.commit()
        return {"id": item_id, "status": "DELETED"}

    async def change_lost_item_status(
        self, item_id: str, req: ChangeStatusRequest, current_user: CurrentUser
    ) -> dict[str, str]:
        item = await self._lost_repo.get_by_id(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)
        if item.user_id != current_user.id:
            raise BizError(ErrorCode.NOT_PUBLISHER)

        allowed = LOST_STATUS_TRANSITIONS.get(item.status, set())
        if req.status not in allowed:
            raise BizError(ErrorCode.INVALID_STATE)

        old_status = item.status
        item.status = req.status

        await self._lost_repo.update(item)
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="LOST",
            biz_id=item_id,
            action="UPDATE_STATUS",
            detail=f"状态变更: {old_status} -> {req.status}",
        )
        await self._session.commit()

        return {"id": item_id, "status": req.status}

    # ---------- Found Items ----------

    async def create_found_item(
        self,
        req: CreateFoundItemRequest,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
    ) -> CreateFoundItemResponse:
        dup = await self._found_repo.check_duplicate(
            current_user.id, req.item_name, req.found_time, req.found_location
        )
        if dup:
            raise BizError(ErrorCode.DUPLICATE_SUBMIT)

        if len(req.image_urls) > 5:
            raise BizError(ErrorCode.IMAGE_EXCEED)

        item_id = generate_ulid()
        # Default sensitivity by category. ai-service may upgrade individual
        # images and we OR-combine the results below.
        is_sensitive = 1 if req.category == "CERT" else 0
        masked_per_image: dict[str, str] = {}
        if self._ai_client is not None and req.image_urls:
            for url in req.image_urls:
                detection = await self._ai_client.detect_sensitive(url)
                if detection and detection.get("isSensitive"):
                    is_sensitive = 1
                    masked = detection.get("maskedImageUrl")
                    if masked:
                        masked_per_image[url] = masked

        found_item = FoundItem(
            id=item_id,
            user_id=current_user.id,
            item_name=req.item_name,
            category=req.category,
            description=req.description,
            found_time=datetime.strptime(req.found_time, "%Y-%m-%d %H:%M:%S"),
            found_location=req.found_location,
            is_sensitive=is_sensitive,
            custody_type=req.custody_type,
            contact_preference=req.contact_preference,
            status="PENDING",
            review_status="APPROVED",
        )

        await self._found_repo.create(found_item)

        if req.image_urls:
            images = [
                ItemImage(
                    id=generate_ulid(),
                    biz_type="FOUND",
                    biz_id=item_id,
                    image_url=url,
                    masked_image_url=masked_per_image.get(url),
                    sort_order=idx,
                )
                for idx, url in enumerate(req.image_urls)
            ]
            await self._image_repo.create_batch(images)

        if req.verify_questions:
            questions = [
                VerifyQuestion(
                    id=generate_ulid(),
                    found_item_id=item_id,
                    question_text=q.question_text,
                    answer_keywords=json.dumps(q.answer_keywords, ensure_ascii=False),
                )
                for q in req.verify_questions
            ]
            await self._question_repo.create_batch(questions)

        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="FOUND",
            biz_id=item_id,
            action="CREATE",
            detail=f"发布招领: {req.item_name}",
        )
        await self._session.commit()

        background_tasks.add_task(_trigger_match_for_found, item_id)
        return CreateFoundItemResponse(
            id=item_id, status="PENDING", is_sensitive=bool(is_sensitive)
        )

    async def create_found_items_batch(
        self,
        items: list[CreateFoundItemRequest],
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
    ) -> CreateFoundItemsBatchResponse:
        success_ids: list[str] = []
        failures: list[CreateFoundItemsBatchFailure] = []
        seen_keys: set[tuple[str, str, str]] = set()

        for idx, req in enumerate(items):
            duplicate_key = (req.item_name, req.found_time, req.found_location)
            if duplicate_key in seen_keys:
                failures.append(CreateFoundItemsBatchFailure(index=idx, error="重复提交"))
                continue

            try:
                resp = await self.create_found_item(req, current_user, background_tasks)
                success_ids.append(resp.id)
                seen_keys.add(duplicate_key)
            except BizError as exc:
                await self._session.rollback()
                failures.append(CreateFoundItemsBatchFailure(index=idx, error=exc.message))
            except Exception:
                await self._session.rollback()
                failures.append(CreateFoundItemsBatchFailure(index=idx, error="服务内部错误"))

        return CreateFoundItemsBatchResponse(success_ids=success_ids, failures=failures)

    async def list_found_items(self, query: FoundItemQuery) -> dict[str, Any]:
        offset = (query.page_no - 1) * query.page_size
        items, total = await self._found_repo.list_with_filter(
            category=query.category,
            status=query.status,
            keyword=query.keyword,
            location=query.location,
            is_sensitive=query.is_sensitive,
            custody_type=query.custody_type,
            sort_by=query.sort_by,
            offset=offset,
            limit=query.page_size,
        )

        result_list = []
        for item in items:
            images = await self._image_repo.get_by_biz("FOUND", item.id)
            cover = None
            if images:
                cover = images[0].masked_image_url if item.is_sensitive else images[0].image_url

            result_list.append(
                FoundItemListItem(
                    id=item.id,
                    user_id=item.user_id,
                    item_name=item.item_name,
                    category=item.category,
                    description=item.description,
                    found_time=format_beijing(item.found_time),
                    found_location=item.found_location,
                    is_sensitive=bool(item.is_sensitive),
                    custody_type=item.custody_type,
                    contact_preference=item.contact_preference,
                    status=item.status,
                    review_status=item.review_status,
                    cover_image_url=cover,
                    created_at=format_beijing(item.created_at),
                ).model_dump(by_alias=True)
            )

        params = PaginationParams(pageNo=query.page_no, pageSize=query.page_size)
        return paginate(result_list, total, params)

    async def get_found_item_detail(
        self, item_id: str, current_user: CurrentUser
    ) -> dict[str, Any]:
        item = await self._found_repo.get_by_id(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)

        images = await self._image_repo.get_by_biz("FOUND", item_id)

        image_urls: list[str] = []
        for img in images:
            if item.is_sensitive:
                image_urls.append(img.masked_image_url or "")
            else:
                image_urls.append(img.image_url)

        questions_orm = await self._question_repo.get_by_found_item(item_id)
        verify_questions = [
            VerifyQuestionOutput(id=q.id, question_text=q.question_text).model_dump(by_alias=True)
            for q in questions_orm
        ]

        detail = FoundItemDetail(
            id=item.id,
            user_id=item.user_id,
            item_name=item.item_name,
            category=item.category,
            description=item.description,
            found_time=format_beijing(item.found_time),
            found_location=item.found_location,
            is_sensitive=bool(item.is_sensitive),
            custody_type=item.custody_type,
            contact_preference=item.contact_preference,
            status=item.status,
            review_status=item.review_status,
            image_urls=image_urls,
            verify_questions=verify_questions,
            has_active_claim=False,  # Stub
            created_at=format_beijing(item.created_at),
            updated_at=format_beijing(item.updated_at),
        )
        return detail.model_dump(by_alias=True)

    async def change_found_item_status(
        self, item_id: str, req: ChangeStatusRequest, current_user: CurrentUser
    ) -> dict[str, str]:
        item = await self._found_repo.get_by_id(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)

        is_owner = item.user_id == current_user.id
        is_admin = current_user.role == "ADMIN"
        if not is_owner and not is_admin:
            raise BizError(ErrorCode.NOT_PUBLISHER)

        allowed = FOUND_STATUS_TRANSITIONS.get(item.status, set())
        if req.status not in allowed:
            raise BizError(ErrorCode.INVALID_STATE)

        old_status = item.status
        item.status = req.status

        await self._found_repo.update(item)
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="FOUND",
            biz_id=item_id,
            action="UPDATE_STATUS",
            detail=f"状态变更: {old_status} -> {req.status}",
        )
        await self._session.commit()

        return {"id": item_id, "status": req.status}

    # ---------- Internal helpers for Backend B ----------

    async def get_found_item_internal(self, item_id: str) -> FoundItem:
        item = await self._found_repo.get_by_id(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)
        return item

    async def get_lost_item_internal(self, item_id: str) -> LostItem:
        item = await self._lost_repo.get_by_id(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)
        return item

    async def get_verify_questions_internal(self, found_item_id: str) -> list[VerifyQuestion]:
        return await self._question_repo.get_by_found_item(found_item_id)

    async def list_found_item_ids_by_user_internal(self, user_id: str) -> list[str]:
        return await self._found_repo.list_ids_by_user(user_id)

    async def update_found_status_internal(self, item_id: str, status: str) -> None:
        item = await self.get_found_item_internal(item_id)
        item.status = status
        await self._found_repo.update(item)

    async def update_lost_status_internal(self, item_id: str, status: str) -> None:
        item = await self.get_lost_item_internal(item_id)
        item.status = status
        await self._lost_repo.update(item)

    async def create_claim_proof_images_internal(
        self, claim_id: str, image_urls: list[str]
    ) -> None:
        if not image_urls:
            return
        images = [
            ItemImage(
                id=generate_ulid(),
                biz_type="CLAIM_PROOF",
                biz_id=claim_id,
                image_url=url,
                sort_order=idx,
            )
            for idx, url in enumerate(image_urls)
        ]
        await self._image_repo.create_batch(images)

    async def get_claim_proof_images_internal(self, claim_id: str) -> list[str]:
        images = await self._image_repo.get_by_biz("CLAIM_PROOF", claim_id)
        return [img.image_url for img in images]

    # --- Match-related internal helpers ---

    async def list_active_lost_items_internal(
        self, *, exclude_id: str | None = None
    ) -> list[LostItem]:
        return await self._lost_repo.list_active(exclude_id=exclude_id)

    async def list_active_found_items_internal(
        self, *, exclude_id: str | None = None
    ) -> list[FoundItem]:
        return await self._found_repo.list_active(exclude_id=exclude_id)

    async def get_lost_match_payload_internal(self, item_id: str) -> dict[str, Any] | None:
        item = await self._lost_repo.get_by_id(item_id)
        if item is None:
            return None
        images = await self._image_repo.get_by_biz("LOST", item_id)
        return {
            "name": item.item_name,
            "description": item.description,
            "location": item.lost_location,
            "time": item.lost_time_start.isoformat() if item.lost_time_start else None,
            "imageUrls": [img.image_url for img in images],
        }

    async def get_found_match_payload_internal(self, item_id: str) -> dict[str, Any] | None:
        item = await self._found_repo.get_by_id(item_id)
        if item is None:
            return None
        images = await self._image_repo.get_by_biz("FOUND", item_id)
        return {
            "name": item.item_name,
            "description": item.description,
            "location": item.found_location,
            "time": item.found_time.isoformat() if item.found_time else None,
            "imageUrls": [img.image_url for img in images],
        }

    async def list_admin_items_internal(
        self, biz_type: str | None, offset: int, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        result: list[dict[str, Any]] = []
        total = 0
        if biz_type in {None, "LOST"}:
            lost_items, lost_total = await self._lost_repo.list_with_filter(
                offset=offset, limit=limit
            )
            total += lost_total
            result.extend(
                {
                    "id": item.id,
                    "bizType": "LOST",
                    "itemName": item.item_name,
                    "category": item.category,
                    "location": item.lost_location,
                    "status": item.status,
                    "reviewStatus": item.review_status,
                    "isSensitive": False,
                    "userId": item.user_id,
                    "reportCount": 0,
                    "createdAt": format_beijing(item.created_at),
                }
                for item in lost_items
            )
        if biz_type in {None, "FOUND"}:
            found_items, found_total = await self._found_repo.list_with_filter(
                offset=offset, limit=limit
            )
            total += found_total
            result.extend(
                {
                    "id": item.id,
                    "bizType": "FOUND",
                    "itemName": item.item_name,
                    "category": item.category,
                    "location": item.found_location,
                    "status": item.status,
                    "reviewStatus": item.review_status,
                    "isSensitive": bool(item.is_sensitive),
                    "userId": item.user_id,
                    "reportCount": 0,
                    "createdAt": format_beijing(item.created_at),
                }
                for item in found_items
            )
        return result[:limit], total

    async def review_item_internal(
        self, biz_type: str, item_id: str, action: str
    ) -> dict[str, str]:
        normalized = biz_type.upper()
        if normalized == "LOST":
            lost_item = await self.get_lost_item_internal(item_id)
            lost_item.review_status = "APPROVED" if action == "APPROVE" else "REJECTED"
            if action == "REJECT":
                lost_item.status = "CLOSED"
            await self._lost_repo.update(lost_item)
            return {
                "id": lost_item.id,
                "userId": lost_item.user_id,
                "status": lost_item.status,
                "reviewStatus": lost_item.review_status,
                "bizType": "LOST",
            }
        if normalized == "FOUND":
            found_item = await self.get_found_item_internal(item_id)
            found_item.review_status = "APPROVED" if action == "APPROVE" else "REJECTED"
            if action == "REJECT":
                found_item.status = "CLOSED"
            await self._found_repo.update(found_item)
            return {
                "id": found_item.id,
                "userId": found_item.user_id,
                "status": found_item.status,
                "reviewStatus": found_item.review_status,
                "bizType": "FOUND",
            }
        raise BizError(ErrorCode.PARAM_ERROR, "bizType must be LOST or FOUND")

    # ---------- File Upload ----------

    async def upload_file(
        self, file: UploadFile, biz_type: str, current_user: CurrentUser
    ) -> dict[str, Any]:
        if biz_type not in VALID_BIZ_TYPES:
            raise BizError(ErrorCode.PARAM_ERROR, f"bizType must be one of {VALID_BIZ_TYPES}")

        if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise BizError(ErrorCode.PARAM_ERROR, "仅支持 JPEG/PNG/WebP 格式")

        contents = await file.read()
        size = len(contents)
        if size > 10 * 1024 * 1024:
            raise BizError(ErrorCode.UPLOAD_FAILED, "文件大小不能超过 10MB")

        ext = (file.filename or "").rsplit(".", 1)[-1] if file.filename else "jpg"
        now = now_beijing()
        object_key = f"{biz_type}/{now.strftime('%Y%m')}/{uuid.uuid4().hex}.{ext}"

        try:
            client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )

            if not client.bucket_exists(settings.MINIO_BUCKET):
                client.make_bucket(settings.MINIO_BUCKET)

            # Ensure bucket is publicly readable so that the stored URL stays
            # valid without per-request signing. Idempotent.
            try:
                policy = json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"AWS": ["*"]},
                                "Action": ["s3:GetObject"],
                                "Resource": [f"arn:aws:s3:::{settings.MINIO_BUCKET}/*"],
                            }
                        ],
                    }
                )
                client.set_bucket_policy(settings.MINIO_BUCKET, policy)
            except Exception:  # noqa: BLE001 - non-fatal, just log
                logger.warning("Failed to set public-read policy on bucket {}", settings.MINIO_BUCKET)

            client.put_object(
                settings.MINIO_BUCKET,
                object_key,
                io.BytesIO(contents),
                length=size,
                content_type=file.content_type or "application/octet-stream",
            )

            url = f"{settings.minio_public_base_url}/{settings.MINIO_BUCKET}/{object_key}"
        except BizError:
            raise
        except Exception as exc:
            raise BizError(ErrorCode.STORAGE_ERROR) from exc

        resp = FileUploadResponse(
            url=url,
            content_type=file.content_type or "application/octet-stream",
            size=size,
            uploaded_at=format_beijing(now),
        )
        return resp.model_dump(by_alias=True)


# ---- Background task stubs ----


async def _trigger_match_for_lost(item_id: str) -> None:
    from app.match.service import trigger_match

    await trigger_match(biz_type="LOST", item_id=item_id)


async def _trigger_match_for_found(item_id: str) -> None:
    from app.match.service import trigger_match

    await trigger_match(biz_type="FOUND", item_id=item_id)
