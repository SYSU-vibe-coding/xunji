import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import Report
from app.claim.repository import ClaimRequestRepository
from app.common.errors import BizError, ErrorCode
from app.common.pagination import PaginationParams, paginate
from app.common.utils import format_beijing, now_beijing
from app.core.ai_client import AIClient
from app.core.config import settings
from app.core.object_storage import MAX_UPLOAD_BYTES, ObjectStorage, get_object_storage
from app.db.ulid import generate_ulid
from app.item.models import FoundItem, ItemImage, LostItem, VerifyQuestion
from app.item.repository import (
    AdminItemRepository,
    FoundItemRepository,
    ItemImageRepository,
    ItemReportRepository,
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
    SubmitReportRequest,
    SubmitReportResponse,
    UpdateFoundItemRequest,
    UpdateLostItemRequest,
    VerifyQuestionOutput,
)
from app.job.runner import nudge_durable_job_runner
from app.job.service import enqueue_item_jobs, enqueue_jobs
from app.operation_log.service import OperationLogService
from app.user.repository import UserRepository
from app.user.schemas import CurrentUser

# Allowed state transitions
LOST_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "SEARCHING": {"FOUND", "CLOSED"},
}
FOUND_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"CLOSED"},
    "CLAIMING": {"CLOSED"},
}


class ItemService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        ai_client: AIClient | None = None,
        storage: ObjectStorage | None = None,
    ) -> None:
        self._session = session
        self._lost_repo = LostItemRepository(session)
        self._found_repo = FoundItemRepository(session)
        self._image_repo = ItemImageRepository(session)
        self._question_repo = VerifyQuestionRepository(session)
        self._report_repo = ItemReportRepository(session)
        self._admin_item_repo = AdminItemRepository(session)
        self._claim_repo = ClaimRequestRepository(session)
        self._user_repo = UserRepository(session)
        self._log_svc = OperationLogService(session)
        self._ai_client = ai_client
        self._storage = storage or get_object_storage()

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
        await self._storage.validate_owned_assets(
            req.image_urls, user_id=current_user.id, biz_type="LOST"
        )

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
        await enqueue_item_jobs(
            self._session,
            biz_type="LOST",
            biz_id=item_id,
            has_images=bool(req.image_urls),
        )
        await self._session.commit()
        background_tasks.add_task(nudge_durable_job_runner)

        return CreateLostItemResponse(id=item_id, status="SEARCHING")

    async def list_lost_items(
        self, query: LostItemQuery, current_user: CurrentUser | None = None
    ) -> dict[str, Any]:
        offset = (query.page_no - 1) * query.page_size
        # 不显式查 status 时, 默认隐藏已找回 / 已关闭
        exclude = None if (query.status or query.include_closed) else ["FOUND", "CLOSED"]
        items, total = await self._lost_repo.list_with_filter(
            category=query.category,
            status=query.status,
            keyword=query.keyword,
            location=query.location,
            event_time_start=self._parse_query_time(query.event_time_start),
            event_time_end=self._parse_query_time(query.event_time_end),
            viewer_user_id=current_user.id if current_user is not None else None,
            include_all_reviews=current_user is not None and current_user.role == "ADMIN",
            sort_by=query.sort_by,
            offset=offset,
            limit=query.page_size,
            exclude_statuses=exclude,
        )

        result_list = []
        for item in items:
            images = await self._image_repo.get_by_biz("LOST", item.id)
            can_view_sensitive = current_user is not None and (
                item.user_id == current_user.id or current_user.role == "ADMIN"
            )
            cover = None
            if images and (item.category != "CERT" or can_view_sensitive):
                cover = await self._storage.sign_reference(
                    images[0].image_url, sensitive=item.category == "CERT"
                )
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
                    review_comment=item.review_comment,
                    cover_image_url=cover,
                    created_at=format_beijing(item.created_at),
                ).model_dump(by_alias=True)
            )

        params = PaginationParams(pageNo=query.page_no, pageSize=query.page_size)
        return paginate(result_list, total, params)

    async def list_my_lost_items(
        self, query: LostItemQuery, current_user: CurrentUser
    ) -> dict[str, Any]:
        offset = (query.page_no - 1) * query.page_size
        items, total = await self._lost_repo.list_with_filter(
            category=query.category,
            status=query.status,
            keyword=query.keyword,
            location=query.location,
            event_time_start=self._parse_query_time(query.event_time_start),
            event_time_end=self._parse_query_time(query.event_time_end),
            user_id=current_user.id,
            include_all_reviews=True,
            sort_by=query.sort_by,
            offset=offset,
            limit=query.page_size,
        )

        result_list = []
        for item in items:
            images = await self._image_repo.get_by_biz("LOST", item.id)
            cover = (
                await self._storage.sign_reference(
                    images[0].image_url, sensitive=item.category == "CERT"
                )
                if images
                else None
            )
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
                    review_comment=item.review_comment,
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

        can_manage = item.user_id == current_user.id or current_user.role == "ADMIN"
        if item.review_status != "APPROVED" and not can_manage:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)

        images = await self._image_repo.get_by_biz("LOST", item_id)
        stored_refs = [img.image_url for img in images]
        is_sensitive = item.category == "CERT"
        image_urls = (
            await self._storage.sign_references(stored_refs, sensitive=is_sensitive)
            if not is_sensitive or can_manage
            else []
        )
        image_refs = [
            asset_ref
            for stored_ref in stored_refs
            if (
                asset_ref := self._storage.editable_asset_ref(
                    stored_ref, user_id=item.user_id, biz_type="LOST"
                )
            )
            is not None
        ]
        cover = image_urls[0] if image_urls else None

        match_count = None
        if item.user_id == current_user.id:
            match_count = await self._lost_repo.count_matches(item_id)

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
            review_comment=item.review_comment,
            cover_image_url=cover,
            image_urls=image_urls,
            image_refs=image_refs if item.user_id == current_user.id else None,
            match_count=match_count,
            created_at=format_beijing(item.created_at),
            updated_at=format_beijing(item.updated_at),
        )
        return detail.model_dump(by_alias=True)

    async def update_lost_item(
        self,
        item_id: str,
        req: UpdateLostItemRequest,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, str]:
        item = await self._lost_repo.get_by_id_for_update(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)
        if item.user_id != current_user.id:
            raise BizError(ErrorCode.NOT_PUBLISHER)
        if item.status == "FOUND":
            raise BizError(ErrorCode.INVALID_STATE)
        await self._ensure_lost_has_no_active_claim(item_id)

        if len(req.image_urls) > 5:
            raise BizError(ErrorCode.IMAGE_EXCEED)
        await self._storage.validate_owned_assets(
            req.image_urls, user_id=current_user.id, biz_type="LOST"
        )

        item.item_name = req.item_name
        item.category = req.category
        item.description = req.description
        item.lost_time_start = datetime.strptime(req.lost_time_start, "%Y-%m-%d %H:%M:%S")
        item.lost_time_end = datetime.strptime(req.lost_time_end, "%Y-%m-%d %H:%M:%S")
        item.lost_location = req.lost_location
        item.subscribe_match = 1 if req.subscribe_match else 0
        item.ai_tags = None
        if item.status == "CLOSED":
            item.status = "SEARCHING"
        item.review_status = "PENDING"
        item.review_comment = None

        await self._expire_matches_internal("LOST", item_id)
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
        await enqueue_item_jobs(
            self._session,
            biz_type="LOST",
            biz_id=item_id,
            has_images=bool(req.image_urls),
        )
        await self._session.commit()
        if background_tasks is not None:
            background_tasks.add_task(nudge_durable_job_runner)
        return {"id": item_id, "status": item.status, "reviewStatus": item.review_status}

    async def delete_lost_item(self, item_id: str, current_user: CurrentUser) -> dict[str, str]:
        item = await self._lost_repo.get_by_id_for_update(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)
        if item.user_id != current_user.id:
            raise BizError(ErrorCode.NOT_PUBLISHER)
        if item.status == "FOUND":
            raise BizError(ErrorCode.INVALID_STATE)
        await self._ensure_lost_has_no_active_claim(item_id)

        await self._expire_matches_internal("LOST", item_id)
        item.status = "CLOSED"
        await self._lost_repo.update(item)
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="LOST",
            biz_id=item_id,
            action="UPDATE_STATUS",
            detail=f"逻辑删除失物: {item.item_name} -> CLOSED",
        )
        await self._session.commit()
        return {"id": item_id, "status": "CLOSED"}

    async def change_lost_item_status(
        self, item_id: str, req: ChangeStatusRequest, current_user: CurrentUser
    ) -> dict[str, str]:
        item = await self._lost_repo.get_by_id_for_update(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)
        is_owner = item.user_id == current_user.id
        is_admin = current_user.role == "ADMIN"
        if not is_owner and not is_admin:
            raise BizError(ErrorCode.NOT_PUBLISHER)
        await self._ensure_lost_has_no_active_claim(item_id)

        allowed = LOST_STATUS_TRANSITIONS.get(item.status, set())
        if req.status not in allowed:
            raise BizError(ErrorCode.INVALID_STATE)

        old_status = item.status
        item.status = req.status

        await self._expire_matches_internal("LOST", item_id)
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
        await self._storage.validate_owned_assets(
            req.image_urls, user_id=current_user.id, biz_type="FOUND"
        )

        item_id = generate_ulid()
        # Image-bearing records stay private until asynchronous detection proves
        # every image safe. CERT records are always sensitive.
        is_sensitive = 1 if req.category == "CERT" or req.image_urls else 0

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
        await enqueue_item_jobs(
            self._session,
            biz_type="FOUND",
            biz_id=item_id,
            has_images=bool(req.image_urls),
        )
        await self._session.commit()
        background_tasks.add_task(nudge_durable_job_runner)

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

    async def list_found_items(
        self, query: FoundItemQuery, current_user: CurrentUser | None = None
    ) -> dict[str, Any]:
        offset = (query.page_no - 1) * query.page_size
        # 不显式查 status 时, 默认隐藏已归还 / 已关闭
        exclude = None if (query.status or query.include_closed) else ["RETURNED", "CLOSED"]
        items, total = await self._found_repo.list_with_filter(
            category=query.category,
            status=query.status,
            keyword=query.keyword,
            location=query.location,
            event_time_start=self._parse_query_time(query.event_time_start),
            event_time_end=self._parse_query_time(query.event_time_end),
            viewer_user_id=current_user.id if current_user is not None else None,
            include_all_reviews=current_user is not None and current_user.role == "ADMIN",
            is_sensitive=query.is_sensitive,
            custody_type=query.custody_type,
            sort_by=query.sort_by,
            offset=offset,
            limit=query.page_size,
            exclude_statuses=exclude,
        )

        result_list = []
        for item in items:
            images = await self._image_repo.get_by_biz("FOUND", item.id)
            cover = None
            can_view_original = current_user is not None and (
                item.user_id == current_user.id or current_user.role == "ADMIN"
            )
            if images and (not item.is_sensitive or can_view_original):
                cover = await self._storage.sign_reference(
                    images[0].image_url, sensitive=bool(item.is_sensitive)
                )

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
                    review_comment=item.review_comment,
                    cover_image_url=cover,
                    created_at=format_beijing(item.created_at),
                ).model_dump(by_alias=True)
            )

        params = PaginationParams(pageNo=query.page_no, pageSize=query.page_size)
        return paginate(result_list, total, params)

    async def list_my_found_items(
        self, query: FoundItemQuery, current_user: CurrentUser
    ) -> dict[str, Any]:
        offset = (query.page_no - 1) * query.page_size
        items, total = await self._found_repo.list_with_filter(
            category=query.category,
            status=query.status,
            keyword=query.keyword,
            location=query.location,
            event_time_start=self._parse_query_time(query.event_time_start),
            event_time_end=self._parse_query_time(query.event_time_end),
            user_id=current_user.id,
            include_all_reviews=True,
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
                cover = await self._storage.sign_reference(
                    images[0].image_url, sensitive=bool(item.is_sensitive)
                )

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
                    review_comment=item.review_comment,
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

        can_manage = item.user_id == current_user.id or current_user.role == "ADMIN"
        if item.review_status != "APPROVED" and not can_manage:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)

        images = await self._image_repo.get_by_biz("FOUND", item_id)

        can_view_original = can_manage
        stored_refs = [img.image_url for img in images]
        image_refs = [
            asset_ref
            for stored_ref in stored_refs
            if (
                asset_ref := self._storage.editable_asset_ref(
                    stored_ref, user_id=item.user_id, biz_type="FOUND"
                )
            )
            is not None
        ]
        image_urls = (
            await self._storage.sign_references(
                stored_refs,
                sensitive=bool(item.is_sensitive),
            )
            if not item.is_sensitive or can_view_original
            else []
        )

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
            review_comment=item.review_comment,
            image_urls=image_urls,
            image_refs=image_refs if item.user_id == current_user.id else None,
            verify_questions=verify_questions,
            has_active_claim=await self._claim_repo.has_active_claim(item_id),
            created_at=format_beijing(item.created_at),
            updated_at=format_beijing(item.updated_at),
        )
        return detail.model_dump(by_alias=True)

    async def update_found_item(
        self,
        item_id: str,
        req: UpdateFoundItemRequest,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, str]:
        item = await self._found_repo.get_by_id_for_update(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)
        if item.user_id != current_user.id:
            raise BizError(ErrorCode.NOT_PUBLISHER)
        if item.status in {"CLAIMING", "RETURNED"}:
            raise BizError(ErrorCode.INVALID_STATE)

        if len(req.image_urls) > 5:
            raise BizError(ErrorCode.IMAGE_EXCEED)
        await self._storage.validate_owned_assets(
            req.image_urls, user_id=current_user.id, biz_type="FOUND"
        )

        is_sensitive = 1 if req.category == "CERT" or req.image_urls else 0

        item.item_name = req.item_name
        item.category = req.category
        item.description = req.description
        item.found_time = datetime.strptime(req.found_time, "%Y-%m-%d %H:%M:%S")
        item.found_location = req.found_location
        item.is_sensitive = is_sensitive
        item.custody_type = req.custody_type
        item.contact_preference = req.contact_preference
        item.ai_tags = None
        if item.status == "CLOSED":
            item.status = "PENDING"
        item.review_status = "PENDING"
        item.review_comment = None

        await self._expire_matches_internal("FOUND", item_id)
        await self._found_repo.update(item)
        await self._image_repo.delete_by_biz("FOUND", item_id)
        if req.image_urls:
            images = [
                ItemImage(
                    id=generate_ulid(),
                    biz_type="FOUND",
                    biz_id=item_id,
                    image_url=url,
                    sort_order=idx,
                )
                for idx, url in enumerate(req.image_urls)
            ]
            await self._image_repo.create_batch(images)

        if req.verify_questions is not None:
            await self._question_repo.delete_by_found_item(item_id)
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
            action="UPDATE",
            detail=f"淇敼鎷涢: {req.item_name}",
        )
        await enqueue_item_jobs(
            self._session,
            biz_type="FOUND",
            biz_id=item_id,
            has_images=bool(req.image_urls),
        )
        await self._session.commit()
        if background_tasks is not None:
            background_tasks.add_task(nudge_durable_job_runner)
        return {"id": item_id, "status": item.status, "reviewStatus": item.review_status}

    async def change_found_item_status(
        self, item_id: str, req: ChangeStatusRequest, current_user: CurrentUser
    ) -> dict[str, str]:
        item = await self._found_repo.get_by_id_for_update(item_id)
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
        if req.status == "CLOSED":
            from app.claim.service import ClaimService

            await ClaimService(self._session).terminate_active_claims(
                item_id,
                operator_id=current_user.id,
                operator_role=current_user.role,
            )
            await self._expire_matches_internal("FOUND", item_id)
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

    async def get_found_item_for_update_internal(self, item_id: str) -> FoundItem:
        item = await self._found_repo.get_by_id_for_update(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)
        return item

    async def get_lost_item_internal(self, item_id: str) -> LostItem:
        item = await self._lost_repo.get_by_id(item_id)
        if item is None:
            raise BizError(ErrorCode.ITEM_NOT_FOUND)
        return item

    async def get_lost_item_for_update_internal(self, item_id: str) -> LostItem:
        item = await self._lost_repo.get_by_id_for_update(item_id)
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

    async def transition_found_status_internal(
        self, item_id: str, *, expected_status: str, new_status: str
    ) -> bool:
        return await self._found_repo.transition_status(
            item_id,
            expected_status=expected_status,
            new_status=new_status,
        )

    async def update_lost_status_internal(self, item_id: str, status: str) -> None:
        item = await self.get_lost_item_internal(item_id)
        item.status = status
        await self._lost_repo.update(item)

    async def create_claim_proof_images_internal(
        self, claim_id: str, image_urls: list[str], uploader_id: str
    ) -> None:
        if not image_urls:
            return
        await self._storage.validate_owned_assets(
            image_urls, user_id=uploader_id, biz_type="CLAIM_PROOF"
        )
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

    async def validate_image_refs_internal(
        self, image_refs: list[str], *, uploader_id: str, biz_type: str
    ) -> None:
        await self._storage.validate_owned_assets(
            image_refs, user_id=uploader_id, biz_type=biz_type
        )

    async def get_claim_proof_images_internal(self, claim_id: str) -> list[str]:
        images = await self._image_repo.get_by_biz("CLAIM_PROOF", claim_id)
        return await self._storage.sign_references(
            [img.image_url for img in images], sensitive=True
        )

    async def has_claim_proof_images_internal(self, claim_id: str) -> bool:
        return bool(await self._image_repo.get_by_biz("CLAIM_PROOF", claim_id))

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
        publisher = await self._user_repo.get_by_id(item.user_id) if item is not None else None
        if (
            item is None
            or item.status != "SEARCHING"
            or item.review_status != "APPROVED"
            or publisher is None
            or publisher.status != "ACTIVE"
        ):
            return None
        images = await self._image_repo.get_by_biz("LOST", item_id)
        return {
            "name": item.item_name,
            "description": item.description,
            "location": item.lost_location,
            "time": item.lost_time_start.isoformat() if item.lost_time_start else None,
            "timeEnd": item.lost_time_end.isoformat() if item.lost_time_end else None,
            "imageUrls": await self._storage.sign_references_for_ai(
                [image.image_url for image in images]
            ),
        }

    async def get_found_match_payload_internal(self, item_id: str) -> dict[str, Any] | None:
        item = await self._found_repo.get_by_id(item_id)
        publisher = await self._user_repo.get_by_id(item.user_id) if item is not None else None
        if (
            item is None
            or item.status != "PENDING"
            or item.review_status != "APPROVED"
            or publisher is None
            or publisher.status != "ACTIVE"
        ):
            return None
        images = await self._image_repo.get_by_biz("FOUND", item_id)
        return {
            "name": item.item_name,
            "description": item.description,
            "location": item.found_location,
            "time": item.found_time.isoformat() if item.found_time else None,
            "imageUrls": await self._storage.sign_references_for_ai(
                [image.image_url for image in images]
            ),
        }

    async def _expire_matches_internal(self, biz_type: str, item_id: str) -> int:
        from app.match.service import MatchService

        return await MatchService(self._session).expire_for_item(biz_type, item_id)

    async def list_admin_items_internal(
        self,
        biz_type: str | None,
        offset: int,
        limit: int,
        target_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        rows, total = await self._admin_item_repo.list_mixed(
            biz_type=biz_type,
            target_id=target_id,
            offset=offset,
            limit=limit,
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            item_id = str(row["id"])
            row_biz_type = str(row["biz_type"])
            created_at = row["created_at"]
            if not isinstance(created_at, datetime):
                raise BizError(ErrorCode.INTERNAL_ERROR, "invalid item creation time")
            report_counts = await self._report_repo.count_by_targets(
                f"{row_biz_type}_ITEM", [item_id]
            )
            result.append(
                {
                    "id": item_id,
                    "bizType": row_biz_type,
                    "itemName": row["item_name"],
                    "category": row["category"],
                    "location": row["location"],
                    "status": row["status"],
                    "reviewStatus": row["review_status"],
                    "reviewComment": row["review_comment"],
                    "isSensitive": bool(row["is_sensitive"]),
                    "userId": row["user_id"],
                    "reportCount": report_counts.get(item_id, 0),
                    "createdAt": format_beijing(created_at),
                }
            )
        return result, total

    async def submit_report(
        self, req: SubmitReportRequest, current_user: CurrentUser
    ) -> SubmitReportResponse:
        target_user_id = None
        if req.target_type == "LOST_ITEM":
            lost_target = await self._lost_repo.get_by_id(req.target_id)
            if lost_target is not None:
                target_user_id = lost_target.user_id
        elif req.target_type == "FOUND_ITEM":
            found_target = await self._found_repo.get_by_id(req.target_id)
            if found_target is not None:
                target_user_id = found_target.user_id
        elif req.target_type == "CLAIM_REQUEST":
            claim_target = await self._claim_repo.get_by_id(req.target_id)
            if claim_target is not None:
                target_user_id = claim_target.claimant_id
        if target_user_id is None:
            raise BizError(ErrorCode.REPORT_TARGET_NOT_FOUND)

        exists = await self._report_repo.exists_by_reporter_and_target(
            reporter_id=current_user.id,
            target_type=req.target_type,
            target_id=req.target_id,
        )
        if exists:
            raise BizError(ErrorCode.REPORT_DUPLICATE)

        report = Report(
            id=generate_ulid(),
            reporter_id=current_user.id,
            reported_user_id=target_user_id,
            target_type=req.target_type,
            target_id=req.target_id,
            reason=req.reason,
            description=req.description,
            handle_status="PENDING",
        )
        try:
            async with self._session.begin_nested():
                await self._report_repo.create(report)
        except IntegrityError as exc:
            raise BizError(ErrorCode.REPORT_DUPLICATE) from exc
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="REPORT",
            biz_id=report.id,
            action="CREATE",
            detail=f"提交举报: {req.target_type}/{req.target_id}",
        )
        await self._session.commit()
        return SubmitReportResponse(id=report.id, handle_status=report.handle_status)

    async def review_item_internal(
        self,
        biz_type: str,
        item_id: str,
        action: str,
        comment: str | None,
        *,
        operator_id: str,
        operator_role: str,
    ) -> dict[str, str]:
        normalized = biz_type.upper()
        if normalized == "LOST":
            lost_item = await self.get_lost_item_for_update_internal(item_id)
            if lost_item.review_status != "PENDING":
                raise BizError(ErrorCode.REVIEW_STATE_CHANGED)
            review_status = "APPROVED" if action == "APPROVE" else "REJECTED"
            transitioned = await self._lost_repo.transition_review(
                item_id,
                review_status=review_status,
                review_comment=comment,
                close_item=action == "REJECT",
            )
            if not transitioned:
                raise BizError(ErrorCode.REVIEW_STATE_CHANGED)
            lost_item.review_status = review_status
            lost_item.review_comment = comment
            if action == "REJECT":
                lost_item.status = "CLOSED"
                await self._expire_matches_internal("LOST", item_id)
            else:
                await enqueue_jobs(
                    self._session,
                    biz_type="LOST",
                    biz_id=item_id,
                    job_types=["MATCH"],
                )
            return {
                "id": lost_item.id,
                "userId": lost_item.user_id,
                "status": lost_item.status,
                "reviewStatus": lost_item.review_status,
                "bizType": "LOST",
            }
        if normalized == "FOUND":
            found_item = await self.get_found_item_for_update_internal(item_id)
            if found_item.review_status != "PENDING":
                raise BizError(ErrorCode.REVIEW_STATE_CHANGED)
            review_status = "APPROVED" if action == "APPROVE" else "REJECTED"
            if action == "REJECT":
                from app.claim.service import ClaimService

                await ClaimService(self._session).terminate_active_claims(
                    item_id,
                    operator_id=operator_id,
                    operator_role=operator_role,
                )
                await self._expire_matches_internal("FOUND", item_id)
            transitioned = await self._found_repo.transition_review(
                item_id,
                review_status=review_status,
                review_comment=comment,
                close_item=action == "REJECT",
            )
            if not transitioned:
                raise BizError(ErrorCode.REVIEW_STATE_CHANGED)
            found_item.review_status = review_status
            found_item.review_comment = comment
            if action == "REJECT":
                found_item.status = "CLOSED"
            else:
                await enqueue_jobs(
                    self._session,
                    biz_type="FOUND",
                    biz_id=item_id,
                    job_types=["MATCH"],
                )
            return {
                "id": found_item.id,
                "userId": found_item.user_id,
                "status": found_item.status,
                "reviewStatus": found_item.review_status,
                "bizType": "FOUND",
            }
        raise BizError(ErrorCode.PARAM_ERROR, "bizType must be LOST or FOUND")

    async def get_report_target_user_for_update(
        self, target_type: str, target_id: str
    ) -> str:
        if target_type == "LOST_ITEM":
            lost_target = await self._lost_repo.get_by_id(target_id)
            if lost_target is not None:
                return lost_target.user_id
        elif target_type == "FOUND_ITEM":
            found_target = await self._found_repo.get_by_id(target_id)
            if found_target is not None:
                return found_target.user_id
        elif target_type == "CLAIM_REQUEST":
            claim_target = await self._claim_repo.get_by_id(target_id)
            if claim_target is not None:
                return claim_target.claimant_id
        raise BizError(ErrorCode.REPORT_TARGET_NOT_FOUND)

    async def take_down_report_target(
        self,
        target_type: str,
        target_id: str,
        *,
        operator_id: str,
        operator_role: str,
    ) -> int:
        from app.claim.service import ClaimService

        claim_svc = ClaimService(self._session)
        if target_type == "LOST_ITEM":
            lost_item = await self._lost_repo.get_by_id_for_update(target_id)
            if lost_item is None:
                raise BizError(ErrorCode.REPORT_TARGET_NOT_FOUND)
            claim_ids = await self._claim_repo.list_active_ids_by_lost_item(target_id)
            terminated = 0
            for claim_id in claim_ids:
                terminated += await claim_svc.terminate_claim_for_report(
                    claim_id, operator_id=operator_id, operator_role=operator_role
                )
            lost_item.status = "CLOSED"
            lost_item.review_status = "REJECTED"
            await self._expire_matches_internal("LOST", target_id)
            await self._lost_repo.update(lost_item)
            return terminated
        if target_type == "FOUND_ITEM":
            found_item = await self._found_repo.get_by_id_for_update(target_id)
            if found_item is None:
                raise BizError(ErrorCode.REPORT_TARGET_NOT_FOUND)
            terminated = await claim_svc.terminate_active_claims(
                target_id, operator_id=operator_id, operator_role=operator_role
            )
            found_item.status = "CLOSED"
            found_item.review_status = "REJECTED"
            await self._expire_matches_internal("FOUND", target_id)
            await self._found_repo.update(found_item)
            return terminated
        if target_type == "CLAIM_REQUEST":
            return await claim_svc.terminate_claim_for_report(
                target_id, operator_id=operator_id, operator_role=operator_role
            )
        raise BizError(ErrorCode.PARAM_ERROR, "unsupported report targetType")

    async def _ensure_lost_has_no_active_claim(self, item_id: str) -> None:
        if await self._claim_repo.has_active_by_lost_item(item_id):
            raise BizError(
                ErrorCode.INVALID_STATE,
                "失物存在进行中的关联认领, 不可编辑、关闭、标记找回或删除",
            )

    @staticmethod
    def _parse_query_time(value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

    # ---------- File Upload ----------

    async def upload_file(
        self, file: UploadFile, biz_type: str, current_user: CurrentUser
    ) -> dict[str, Any]:
        allowed_biz_types = VALID_BIZ_TYPES | {"USER"}
        if biz_type not in allowed_biz_types:
            raise BizError(
                ErrorCode.PARAM_ERROR,
                f"bizType must be one of {sorted(allowed_biz_types)}",
            )

        contents = await file.read(MAX_UPLOAD_BYTES + 1)
        now = now_beijing()
        stored = await self._storage.upload_image(
            contents, biz_type=biz_type, user_id=current_user.id
        )

        resp = FileUploadResponse(
            asset_ref=stored.asset_ref,
            preview_url=stored.preview_url,
            content_type=stored.content_type,
            size=stored.size,
            uploaded_at=format_beijing(now),
        )
        return resp.model_dump(by_alias=True)


async def _classify_and_save(
    session: AsyncSession,
    biz_type: str,
    item_id: str,
    client: AIClient,
) -> None:
    svc = ItemService(session, ai_client=client)
    item: LostItem | FoundItem | None
    if biz_type == "LOST":
        item = await svc._lost_repo.get_by_id(item_id)
    else:
        item = await svc._found_repo.get_by_id(item_id)
    if item is None:
        return
    images = await svc._image_repo.get_by_biz(biz_type, item_id)
    image_urls = await svc._storage.sign_references_for_ai(
        [image.image_url for image in images]
    )
    result = await client.classify_item(
        image_urls=image_urls,
        item_name=item.item_name,
        description=item.description,
    )
    if result is None:
        raise RuntimeError("AI classification returned no usable result")
    tags = [tag.strip()[:20] for tag in result["tags"] if tag.strip()][:5]
    payload = {
        "tags": tags,
        "suggestedCategory": result["category"],
        "confidence": round(float(result["confidence"]), 2),
        "source": result["source"],
        "degraded": result["degraded"],
    }
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    while len(serialized) > 255 and tags:
        tags.pop()
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    item.ai_tags = serialized
    if isinstance(item, LostItem):
        await svc._lost_repo.update(item)
    else:
        await svc._found_repo.update(item)


async def _detect_sensitive_and_save(
    session: AsyncSession,
    item_id: str,
    client: AIClient,
) -> None:
    """Release a FOUND item's images only after every image is explicitly safe."""
    svc = ItemService(session)
    item = await svc._found_repo.get_by_id_for_update(item_id)
    if item is None:
        return
    if item.category == "CERT":
        item.is_sensitive = 1
        await svc._found_repo.update(item)
        return

    images = await svc._image_repo.get_by_biz("FOUND", item_id)
    if not images:
        item.is_sensitive = 0
        await svc._found_repo.update(item)
        return

    semaphore = asyncio.Semaphore(max(1, settings.SENSITIVE_JOB_MAX_CONCURRENCY))

    async def detect(asset_ref: str) -> dict[str, Any]:
        controlled_url = await svc._storage.sign_reference_for_ai(asset_ref)
        if controlled_url is None:
            raise RuntimeError("could not create a controlled AI image URL")
        async with semaphore:
            result = await client.detect_sensitive(controlled_url)
        if result is None:
            raise RuntimeError("AI sensitive detection returned no usable result")
        return result

    detections = await asyncio.gather(*(detect(image.image_url) for image in images))
    explicitly_safe = all(
        detection.get("isSensitive") is False
        and detection.get("needsReview") is False
        and detection.get("degraded") is False
        for detection in detections
    )
    item.is_sensitive = 0 if explicitly_safe else 1
    await svc._found_repo.update(item)
