import json
from datetime import timedelta
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.claim.models import ClaimAnswer, ClaimRequest, HandoverRecord
from app.claim.repository import (
    ClaimAnswerRepository,
    ClaimRequestRepository,
    HandoverRecordRepository,
)
from app.claim.schemas import (
    AdminClaimAnswerOutput,
    AdminClaimListItem,
    ClaimAnswerInput,
    ClaimAnswerOutput,
    ClaimAppealRequest,
    ClaimDetailResponse,
    ClaimItemSummary,
    ClaimMyListItem,
    ClaimMyQuery,
    ClaimPartySummary,
    ClaimProofsRequest,
    ClaimReviewRequest,
    ConfirmHandoverRequest,
    CreateClaimRequest,
    CreateClaimResponse,
    CreateHandoverRequest,
    CreateHandoverResponse,
    HandoverOutput,
    parse_datetime,
)
from app.common.errors import BizError, ErrorCode
from app.common.pagination import PaginationParams, paginate
from app.common.utils import format_beijing, now_beijing
from app.core.ai_client import AIClient
from app.credit.service import CreditService
from app.db.ulid import generate_ulid
from app.item.service import ItemService
from app.match.service import MatchService
from app.notification.service import NotificationService
from app.operation_log.service import OperationLogService
from app.user.schemas import CurrentUser
from app.user.service import UserService

REVIEWABLE_STATUSES = {"PENDING", "ANSWER_PASSED", "PROOF_PENDING", "APPEALING"}
VERIFY_FAILURE_REASON = "验证未通过"
VERIFY_FAILURE_COOLDOWN = timedelta(minutes=5)
VERIFY_FAILURE_WINDOW = timedelta(hours=24)
VERIFY_FAILURE_LIMIT = 3


def determine_verify_level(found_category: str, credit_score: int) -> str:
    if found_category == "CERT":
        return "LEVEL_3"
    level = "LEVEL_2" if found_category == "ELECTRONIC" else "LEVEL_1"
    if 30 <= credit_score < 60:
        return "LEVEL_2" if level == "LEVEL_1" else "LEVEL_3"
    return level


class ClaimService:
    def __init__(self, session: AsyncSession, *, ai_client: AIClient | None = None) -> None:
        self._session = session
        self._claim_repo = ClaimRequestRepository(session)
        self._answer_repo = ClaimAnswerRepository(session)
        self._handover_repo = HandoverRecordRepository(session)
        self._item_svc = ItemService(session)
        self._user_svc = UserService(session)
        self._match_svc = MatchService(session)
        self._notification_svc = NotificationService(session)
        self._credit_svc = CreditService(session)
        self._log_svc = OperationLogService(session)
        self._ai_client = ai_client

    async def create_claim(
        self, req: CreateClaimRequest, current_user: CurrentUser
    ) -> CreateClaimResponse:
        match = None
        lost_item = None
        if req.match_id:
            match_preview = await self._match_svc.get_by_id(req.match_id)
            if match_preview is None or match_preview.found_item_id != req.found_item_id:
                raise BizError(ErrorCode.MATCH_NOT_FOUND)

        found_preview = await self._item_svc.get_found_item_internal(req.found_item_id)
        claimant_preview = await self._user_svc.get_user_internal(current_user.id)
        if claimant_preview is None or claimant_preview.status != "ACTIVE":
            raise BizError(ErrorCode.UNAUTHORIZED)
        if claimant_preview.credit_score < 30:
            raise BizError(ErrorCode.CREDIT_FROZEN)
        if found_preview.status != "PENDING" or found_preview.review_status != "APPROVED":
            raise BizError(ErrorCode.ITEM_CLOSED)
        if found_preview.user_id == current_user.id:
            raise BizError(ErrorCode.CLAIM_NOT_PARTY, "不可认领自己发布的招领")
        if await self._claim_repo.has_active_claim(req.found_item_id):
            raise BizError(ErrorCode.CLAIM_DUPLICATE)
        await self._enforce_verification_attempt_limit(current_user.id, found_preview.id)
        preview_questions = await self._item_svc.get_verify_questions_internal(req.found_item_id)
        preview_verify_level = determine_verify_level(
            found_preview.category, claimant_preview.credit_score
        )
        scored_answers: list[ClaimAnswer] = []
        answers_passed = True
        verification_source = "NOT_REQUIRED"
        verification_degraded = False
        if preview_verify_level in {"LEVEL_1", "LEVEL_2"}:
            self._validate_answer_set(req.answers, preview_questions)
            if preview_questions:
                (
                    scored_answers,
                    answers_passed,
                    verification_source,
                    verification_degraded,
                ) = await self._score_answers_with_ai(req.answers, preview_questions)
        question_fingerprint = self._question_fingerprint(preview_questions)

        found_item = await self._item_svc.get_found_item_for_update_internal(req.found_item_id)
        if req.match_id:
            match = await self._match_svc.get_by_id_for_update(req.match_id)
            if match is None or match.found_item_id != req.found_item_id:
                raise BizError(ErrorCode.MATCH_NOT_FOUND)
            lost_item = await self._item_svc.get_lost_item_for_update_internal(match.lost_item_id)

        locked_users = {}
        for user_id in sorted({current_user.id, found_item.user_id}):
            locked_users[user_id] = await self._user_svc.get_user_for_update_internal(user_id)
        user = locked_users[current_user.id]
        finder = locked_users[found_item.user_id]
        if user is None or user.status != "ACTIVE":
            raise BizError(ErrorCode.UNAUTHORIZED)
        if user.credit_score < 30:
            raise BizError(ErrorCode.CREDIT_FROZEN)
        if finder is None or finder.status != "ACTIVE":
            raise BizError(ErrorCode.USER_DISABLED, "招领发布者账号当前不可参与认领")
        if found_item.status != "PENDING" or found_item.review_status != "APPROVED":
            raise BizError(ErrorCode.ITEM_CLOSED)
        if found_item.user_id == current_user.id:
            raise BizError(ErrorCode.CLAIM_NOT_PARTY, "不可认领自己发布的招领")
        if await self._claim_repo.has_active_claim(req.found_item_id):
            raise BizError(ErrorCode.CLAIM_DUPLICATE)

        if match is not None:
            assert lost_item is not None
            if (
                lost_item.user_id != current_user.id
                or lost_item.status != "SEARCHING"
                or lost_item.review_status != "APPROVED"
            ):
                raise BizError(ErrorCode.CLAIM_NOT_PARTY)
            if match.match_status not in {"NEW", "READ"}:
                raise BizError(ErrorCode.MATCH_CLAIMED)

        questions = await self._item_svc.get_verify_questions_internal(req.found_item_id)
        verify_level = determine_verify_level(found_item.category, user.credit_score)
        if (
            verify_level != preview_verify_level
            or self._question_fingerprint(questions) != question_fingerprint
        ):
            raise BizError(ErrorCode.CLAIM_INVALID_STATE, "验证问题已更新, 请重新提交")
        await self._item_svc.validate_image_refs_internal(
            req.proof_image_urls,
            uploader_id=current_user.id,
            biz_type="CLAIM_PROOF",
        )
        review_status, answers = self._build_initial_claim_state(
            verify_level=verify_level,
            scored_answers=scored_answers,
            answers_passed=answers_passed,
            questions=questions,
            proof_image_urls=req.proof_image_urls,
        )
        if review_status != "REJECTED":
            reserved = await self._item_svc.transition_found_status_internal(
                req.found_item_id,
                expected_status="PENDING",
                new_status="CLAIMING",
            )
            if not reserved:
                raise BizError(ErrorCode.CLAIM_DUPLICATE)

        claim_id = generate_ulid()
        claim = ClaimRequest(
            id=claim_id,
            match_id=req.match_id,
            found_item_id=req.found_item_id,
            claimant_id=current_user.id,
            verify_level=verify_level,
            review_status=review_status,
            verification_source=verification_source,
            verification_degraded=int(verification_degraded),
            reject_reason=VERIFY_FAILURE_REASON if review_status == "REJECTED" else None,
            claimed_at=now_beijing().replace(tzinfo=None),
        )
        await self._claim_repo.create(claim)
        for answer in answers:
            answer.claim_id = claim_id
        await self._answer_repo.create_batch(answers)
        await self._item_svc.create_claim_proof_images_internal(
            claim_id, req.proof_image_urls, current_user.id
        )
        if match is not None and review_status != "REJECTED":
            await self._match_svc.mark_claimed(match)

        if review_status != "REJECTED":
            await self._notification_svc.create_notice(
                user_id=found_item.user_id,
                notice_type="CLAIM_REQUEST",
                title="收到新的认领申请",
                content=f"{found_item.item_name} 收到新的认领申请",
                related_type="CLAIM",
                related_id=claim_id,
            )
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="CLAIM",
            biz_id=claim_id,
            action="CREATE",
            detail=f"发起认领: {found_item.item_name}",
        )
        await self._session.commit()
        if review_status == "REJECTED":
            raise BizError(
                ErrorCode.CLAIM_ANSWER_MISMATCH,
                "验证未通过, 请稍后重试",
            )
        return CreateClaimResponse(
            id=claim_id, verify_level=verify_level, review_status=review_status
        )

    async def list_my_claims(
        self, current_user: CurrentUser, query: ClaimMyQuery
    ) -> dict[str, Any]:
        statuses = self._parse_status_filter(query.review_status)
        offset = (query.page_no - 1) * query.page_size
        if query.role == "CLAIMANT":
            claims, total = await self._claim_repo.list_by_claimant(
                claimant_id=current_user.id,
                statuses=statuses,
                offset=offset,
                limit=query.page_size,
            )
        else:
            found_ids = await self._item_svc.list_found_item_ids_by_user_internal(current_user.id)
            claims, total = await self._claim_repo.list_by_found_item_ids(
                found_item_ids=found_ids,
                statuses=statuses,
                offset=offset,
                limit=query.page_size,
            )

        items = []
        for claim in claims:
            found_item = await self._item_svc.get_found_item_internal(claim.found_item_id)
            items.append(
                ClaimMyListItem(
                    id=claim.id,
                    found_item_id=claim.found_item_id,
                    item_name=found_item.item_name,
                    verify_level=claim.verify_level,
                    review_status=claim.review_status,
                    updated_at=format_beijing(claim.updated_at),
                ).model_dump(by_alias=True)
            )
        params = PaginationParams(pageNo=query.page_no, pageSize=query.page_size)
        return paginate(items, total, params)

    async def get_claim_detail(
        self, claim_id: str, current_user: CurrentUser
    ) -> ClaimDetailResponse:
        claim = await self._get_claim_or_raise(claim_id)
        found_item = await self._item_svc.get_found_item_internal(claim.found_item_id)
        if not self._is_party_or_admin(claim, found_item.user_id, current_user):
            raise BizError(ErrorCode.CLAIM_NOT_PARTY)
        return await self._to_detail(claim, current_user)

    async def review_claim(
        self, claim_id: str, req: ClaimReviewRequest, current_user: CurrentUser
    ) -> dict[str, str]:
        claim, found_item = await self._lock_claim_and_found(claim_id)
        is_admin = current_user.role == "ADMIN"
        if found_item.user_id != current_user.id and not is_admin:
            raise BizError(ErrorCode.CLAIM_NOT_PARTY)
        if claim.review_status not in REVIEWABLE_STATUSES:
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        if claim.review_status == "APPEALING" and not is_admin:
            raise BizError(ErrorCode.CLAIM_NOT_PARTY)
        if found_item.status != "CLAIMING" or found_item.review_status != "APPROVED":
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        if (
            req.action == "APPROVE"
            and claim.verify_level in {"LEVEL_2", "LEVEL_3"}
            and not await self._item_svc.has_claim_proof_images_internal(claim.id)
        ):
            raise BizError(ErrorCode.CLAIM_PROOF_MISSING)

        old_status = claim.review_status
        if req.action == "APPROVE":
            new_status = "APPROVED"
            reject_reason = None
            action = "REVIEW_APPROVE"
        else:
            new_status = "REJECTED"
            reject_reason = req.comment
            action = "REVIEW_REJECT"

        transitioned = await self._claim_repo.transition_status(
            claim_id=claim.id,
            expected_status=old_status,
            new_status=new_status,
            reject_reason=reject_reason,
        )
        if not transitioned:
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        claim.review_status = new_status
        claim.reject_reason = reject_reason
        if req.action == "REJECT" and not await self._claim_repo.has_active_claim(
            claim.found_item_id, exclude_claim_id=claim.id
        ):
            if found_item.status == "CLAIMING":
                await self._item_svc.transition_found_status_internal(
                    claim.found_item_id,
                    expected_status="CLAIMING",
                    new_status="PENDING",
                )
            if claim.match_id:
                await self._match_svc.release_claimed(claim.match_id)
        await self._notification_svc.create_notice(
            user_id=claim.claimant_id,
            notice_type="CLAIM_REVIEW",
            title="认领审核结果",
            content=(
                f"认领状态变更: {old_status} -> {claim.review_status}. "
                f"审核意见: {req.comment or '无'}"
            ),
            related_type="CLAIM",
            related_id=claim.id,
        )
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="CLAIM",
            biz_id=claim.id,
            action=action,
            detail=json.dumps(
                {
                    "from": old_status,
                    "to": claim.review_status,
                    "comment": req.comment,
                },
                ensure_ascii=False,
            ),
        )
        await self._session.commit()
        return {"id": claim_id, "reviewStatus": claim.review_status}

    async def submit_proofs(
        self, claim_id: str, req: ClaimProofsRequest, current_user: CurrentUser
    ) -> dict[str, str]:
        claim, found_item = await self._lock_claim_and_found(claim_id)
        if claim.claimant_id != current_user.id:
            raise BizError(ErrorCode.CLAIM_NOT_PARTY)
        if claim.review_status not in {"PENDING", "ANSWER_PASSED", "PROOF_PENDING"}:
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        if found_item.status != "CLAIMING" or found_item.review_status != "APPROVED":
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        await self._item_svc.validate_image_refs_internal(
            req.proof_image_urls,
            uploader_id=current_user.id,
            biz_type="CLAIM_PROOF",
        )
        claim.proof_text = req.proof_text
        # Only advance from PROOF_PENDING -> ANSWER_PASSED; for other statuses,
        # proofs are supplementary and don't change the review state.
        if claim.review_status == "PROOF_PENDING":
            claim.review_status = "PENDING" if claim.verify_level == "LEVEL_3" else "ANSWER_PASSED"
        await self._item_svc.create_claim_proof_images_internal(
            claim_id, req.proof_image_urls, current_user.id
        )
        await self._claim_repo.update(claim)
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="CLAIM",
            biz_id=claim_id,
            action="UPDATE_STATUS",
            detail=f"补充凭证: {claim.review_status}",
        )
        await self._session.commit()
        return {"id": claim_id, "reviewStatus": claim.review_status}

    async def appeal_claim(
        self, claim_id: str, req: ClaimAppealRequest, current_user: CurrentUser
    ) -> dict[str, str]:
        claimant = await self._user_svc.get_user_for_update_internal(current_user.id)
        if claimant is None or claimant.status != "ACTIVE":
            raise BizError(ErrorCode.USER_DISABLED)
        claim, found_item = await self._lock_claim_and_found(claim_id)
        finder = await self._user_svc.get_user_for_update_internal(found_item.user_id)
        if finder is None or finder.status != "ACTIVE":
            raise BizError(ErrorCode.USER_DISABLED, "招领发布者账号当前不可参与申诉")
        if claim.claimant_id != current_user.id:
            raise BizError(ErrorCode.CLAIM_NOT_PARTY)
        if claim.review_status != "REJECTED":
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        if claim.appeal_reason:
            raise BizError(ErrorCode.APPEAL_DUPLICATE)
        if (
            found_item.status != "PENDING"
            or found_item.review_status != "APPROVED"
            or await self._claim_repo.has_active_claim(
                claim.found_item_id, exclude_claim_id=claim.id
            )
        ):
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        match = None
        if claim.match_id:
            match = await self._match_svc.get_by_id_for_update(claim.match_id)
            if (
                match is None
                or match.found_item_id != found_item.id
                or match.match_status not in {"NEW", "READ"}
            ):
                raise BizError(ErrorCode.CLAIM_INVALID_STATE)
            lost_item = await self._item_svc.get_lost_item_for_update_internal(match.lost_item_id)
            if (
                lost_item.user_id != claim.claimant_id
                or lost_item.status != "SEARCHING"
                or lost_item.review_status != "APPROVED"
            ):
                raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        if not await self._item_svc.transition_found_status_internal(
            claim.found_item_id,
            expected_status="PENDING",
            new_status="CLAIMING",
        ):
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        claim.appeal_reason = req.reason
        claim.review_status = "APPEALING"
        await self._claim_repo.update(claim)
        if match is not None:
            await self._match_svc.mark_claimed(match)
        after_id = None
        while True:
            admin_ids = await self._user_svc.list_active_user_ids_internal(
                role="ADMIN", after_id=after_id, limit=500
            )
            if not admin_ids:
                break
            await self._notification_svc.create_notices(
                user_ids=admin_ids,
                notice_type="CLAIM_REVIEW",
                title="收到新的认领申诉",
                content=f"认领 {claim.id} 已提交申诉: {req.reason}",
                related_type="CLAIM",
                related_id=claim.id,
                priority="HIGH",
            )
            if len(admin_ids) < 500:
                break
            after_id = admin_ids[-1]
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="CLAIM",
            biz_id=claim_id,
            action="UPDATE_STATUS",
            detail="提交申诉: REJECTED -> APPEALING",
        )
        await self._session.commit()
        return {"id": claim_id, "reviewStatus": "APPEALING"}

    async def list_admin_claims(
        self, *, review_status: str | None, page_no: int, page_size: int
    ) -> dict[str, Any]:
        if review_status is not None:
            self._parse_status_filter(review_status)
        offset = (page_no - 1) * page_size
        claims, total = await self._claim_repo.list_for_admin(
            review_status=review_status, offset=offset, limit=page_size
        )
        items = [
            (await self._to_admin_list_item(claim)).model_dump(by_alias=True) for claim in claims
        ]
        return paginate(items, total, PaginationParams(pageNo=page_no, pageSize=page_size))

    async def get_admin_claim_detail(self, claim_id: str) -> dict[str, Any]:
        claim = await self._get_claim_or_raise(claim_id)
        detail = (
            await self._to_detail(claim, CurrentUser(id="SYSTEM", role="ADMIN", status="ACTIVE"))
        ).model_dump(by_alias=True)
        stored_answers = await self._answer_repo.get_by_claim_id(claim.id)
        detail["answers"] = [
            AdminClaimAnswerOutput(
                question_id=answer.question_id,
                question_text=answer.question_text,
                reference_answers=self._parse_reference_answers(answer.reference_answers),
                answer_text=answer.answer_text,
                match_score=float(answer.match_score),
            ).model_dump(by_alias=True)
            for answer in stored_answers
        ]
        summary = (await self._to_admin_list_item(claim)).model_dump(by_alias=True)
        detail.update(
            claimant=summary["claimant"],
            finder=summary["finder"],
            item=summary["item"],
            verificationSource=summary["verificationSource"],
            verificationDegraded=summary["verificationDegraded"],
        )
        return detail

    async def create_handover(
        self, claim_id: str, req: CreateHandoverRequest, current_user: CurrentUser
    ) -> CreateHandoverResponse:
        claim, found_item = await self._lock_claim_and_found(claim_id)
        if not self._is_party_or_admin(claim, found_item.user_id, current_user):
            raise BizError(ErrorCode.CLAIM_NOT_PARTY)
        existing = await self._handover_repo.get_by_claim_id_for_update(claim_id)
        if existing is not None:
            await self._session.commit()
            return CreateHandoverResponse(handover_id=existing.id)
        if claim.review_status != "APPROVED":
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        if found_item.status != "CLAIMING":
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)

        handover_time = parse_datetime(req.handover_time, "handoverTime")
        if handover_time <= now_beijing().replace(tzinfo=None):
            raise BizError(ErrorCode.PARAM_ERROR, "handoverTime must be greater than now")

        handover = HandoverRecord(
            id=generate_ulid(),
            claim_id=claim_id,
            method=req.method,
            handover_location=req.handover_location,
            handover_time=handover_time,
        )
        try:
            async with self._session.begin_nested():
                await self._handover_repo.create(handover)
        except IntegrityError:
            existing = await self._handover_repo.get_by_claim_id_for_update(claim_id)
            if existing is None:
                raise
            await self._session.commit()
            return CreateHandoverResponse(handover_id=existing.id)
        for user_id in {claim.claimant_id, found_item.user_id}:
            await self._notification_svc.create_notice(
                user_id=user_id,
                notice_type="HANDOVER_REMINDER",
                title="交接安排已创建",
                content=f"交接地点:{req.handover_location}",
                related_type="CLAIM",
                related_id=claim_id,
                priority="HIGH",
            )
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="CLAIM",
            biz_id=claim_id,
            action="CREATE",
            detail="创建交接安排",
        )
        await self._session.commit()
        return CreateHandoverResponse(handover_id=handover.id)

    async def confirm_handover(
        self, claim_id: str, req: ConfirmHandoverRequest, current_user: CurrentUser
    ) -> dict[str, str]:
        claim, found_item = await self._lock_claim_and_found(claim_id)
        handover = await self._handover_repo.get_by_claim_id_for_update(claim_id)
        if handover is None:
            raise BizError(ErrorCode.CLAIM_INVALID_STATE, "交接尚未创建")
        if claim.review_status not in {"APPROVED", "HANDED_OVER"}:
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)

        if req.role == "OWNER":
            if claim.claimant_id != current_user.id:
                raise BizError(ErrorCode.CLAIM_NOT_PARTY)
        else:
            if found_item.user_id != current_user.id:
                raise BizError(ErrorCode.CLAIM_NOT_PARTY)

        if claim.review_status == "HANDED_OVER":
            await self._session.commit()
            return {"id": claim_id, "reviewStatus": "HANDED_OVER"}
        if found_item.status != "CLAIMING" or handover.completed_at is not None:
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        handover = await self._handover_repo.confirm_role(claim_id, req.role)
        if handover is None:
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)

        if (
            handover.owner_confirmed
            and handover.finder_confirmed
            and claim.review_status != "HANDED_OVER"
        ):
            if (
                claim.review_status != "APPROVED"
                or found_item.status != "CLAIMING"
                or found_item.review_status != "APPROVED"
            ):
                raise BizError(ErrorCode.CLAIM_INVALID_STATE)
            match = None
            if claim.match_id:
                match = await self._match_svc.get_by_id_for_update(claim.match_id)
                if (
                    match is None
                    or match.found_item_id != found_item.id
                    or match.match_status != "CLAIMED"
                ):
                    raise BizError(ErrorCode.CLAIM_INVALID_STATE)
                lost_item = await self._item_svc.get_lost_item_for_update_internal(
                    match.lost_item_id
                )
                if (
                    lost_item.user_id != claim.claimant_id
                    or lost_item.status != "SEARCHING"
                    or lost_item.review_status != "APPROVED"
                ):
                    raise BizError(ErrorCode.CLAIM_INVALID_STATE)

            if not await self._item_svc.transition_found_status_internal(
                claim.found_item_id,
                expected_status="CLAIMING",
                new_status="RETURNED",
            ):
                raise BizError(ErrorCode.CLAIM_INVALID_STATE)
            handover.completed_at = now_beijing().replace(tzinfo=None)
            claim.review_status = "HANDED_OVER"
            await self._handover_repo.update(handover)
            await self._claim_repo.update(claim)
            if match is not None:
                await self._item_svc.update_lost_status_internal(match.lost_item_id, "FOUND")

            await self._credit_svc.change_credit(
                user_id=claim.claimant_id,
                delta_score=10,
                reason_code="HANDOVER_SUCCESS",
                reason_text="交接完成",
                biz_type="CLAIM",
                biz_id=claim_id,
                operator_id=current_user.id,
                operator_role=current_user.role,
            )
            await self._credit_svc.change_credit(
                user_id=found_item.user_id,
                delta_score=10,
                reason_code="HANDOVER_SUCCESS",
                reason_text="交接完成",
                biz_type="CLAIM",
                biz_id=claim_id,
                operator_id=current_user.id,
                operator_role=current_user.role,
            )
            for user_id in {claim.claimant_id, found_item.user_id}:
                await self._notification_svc.create_notice(
                    user_id=user_id,
                    notice_type="HANDOVER_REMINDER",
                    title="交接已完成",
                    content="双方已确认交接完成",
                    related_type="CLAIM",
                    related_id=claim_id,
                    priority="HIGH",
                )
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="CLAIM",
            biz_id=claim_id,
            action="HANDOVER_CONFIRM",
            detail=f"交接确认: {req.role}",
        )
        await self._session.commit()
        return {"id": claim_id, "reviewStatus": claim.review_status}

    def _build_initial_claim_state(
        self,
        *,
        verify_level: str,
        scored_answers: list[ClaimAnswer],
        answers_passed: bool,
        questions: list[Any],
        proof_image_urls: list[str],
    ) -> tuple[str, list[ClaimAnswer]]:
        answers = scored_answers
        if verify_level in {"LEVEL_1", "LEVEL_2"} and questions and not answers_passed:
            return "REJECTED", answers
        if verify_level == "LEVEL_1":
            return "ANSWER_PASSED", answers
        if not proof_image_urls:
            return "PROOF_PENDING", answers
        if verify_level == "LEVEL_3":
            return "PENDING", answers
        return "ANSWER_PASSED", answers

    def _validate_answer_set(
        self, claim_answers: list[ClaimAnswerInput], questions: list[Any]
    ) -> None:
        answer_ids = [answer.question_id for answer in claim_answers]
        if len(answer_ids) != len(set(answer_ids)):
            raise BizError(ErrorCode.PARAM_ERROR, "questionId must not be repeated")
        expected_ids = {question.id for question in questions}
        actual_ids = set(answer_ids)
        if actual_ids != expected_ids:
            missing = expected_ids - actual_ids
            unknown = actual_ids - expected_ids
            detail = []
            if missing:
                detail.append(f"missing questionId: {sorted(missing)}")
            if unknown:
                detail.append(f"unknown questionId: {sorted(unknown)}")
            raise BizError(ErrorCode.PARAM_ERROR, "; ".join(detail))

    def _score_answers(
        self, claim_answers: list[ClaimAnswerInput], questions: list[Any]
    ) -> tuple[list[ClaimAnswer], bool]:
        answer_by_question = {answer.question_id: answer.answer_text for answer in claim_answers}
        results: list[ClaimAnswer] = []
        ratios: list[Decimal] = []
        for question in questions:
            answer_text = answer_by_question.get(question.id, "")
            keywords = json.loads(question.answer_keywords)
            normalized_answer = answer_text.lower()
            hits = sum(str(keyword).lower() in normalized_answer for keyword in keywords)
            ratio = Decimal(hits) / Decimal(len(keywords)) if keywords else Decimal("0")
            ratios.append(ratio)
            score = (ratio * Decimal("100")).quantize(Decimal("0.01"))
            results.append(
                ClaimAnswer(
                    id=generate_ulid(),
                    claim_id="",
                    question_id=question.id,
                    question_text=question.question_text,
                    reference_answers=question.answer_keywords,
                    answer_text=answer_text,
                    match_score=score,
                )
            )
        average = sum(ratios, Decimal("0")) / Decimal(len(ratios)) if ratios else Decimal("1")
        return results, average >= Decimal("0.6")

    async def _score_answers_with_ai(
        self, claim_answers: list[ClaimAnswerInput], questions: list[Any]
    ) -> tuple[list[ClaimAnswer], bool, str, bool]:
        if self._ai_client is None:
            answers, passed = self._score_answers(claim_answers, questions)
            return answers, passed, "KEYWORD_RULES", True
        answer_by_question = {answer.question_id: answer.answer_text for answer in claim_answers}
        payload = []
        for question in questions:
            references = json.loads(question.answer_keywords)
            payload.append(
                {
                    "questionText": question.question_text,
                    "referenceAnswers": [str(value) for value in references],
                    "answerText": answer_by_question.get(question.id, ""),
                }
            )
        result = await self._ai_client.verify_claim_answers(payload)
        if result is None:
            logger.warning("[claim-answer] AI unavailable, using keyword rules")
            answers, passed = self._score_answers(claim_answers, questions)
            return answers, passed, "KEYWORD_RULES", True
        answers = [
            ClaimAnswer(
                id=generate_ulid(),
                claim_id="",
                question_id=question.id,
                question_text=question.question_text,
                reference_answers=question.answer_keywords,
                answer_text=answer_by_question.get(question.id, ""),
                match_score=Decimal(str(score)).quantize(Decimal("0.01")),
            )
            for question, score in zip(questions, result["scores"], strict=True)
        ]
        logger.info(
            "[claim-answer] verification source={} degraded={} passed={} questions={}",
            result["source"],
            result["degraded"],
            result["passed"],
            len(questions),
        )
        return (
            answers,
            bool(result["passed"]),
            str(result["source"]),
            bool(result["degraded"]),
        )

    @staticmethod
    def _question_fingerprint(questions: list[Any]) -> tuple[tuple[str, str, str], ...]:
        return tuple(
            (question.id, question.question_text, question.answer_keywords)
            for question in questions
        )

    @staticmethod
    def _parse_reference_answers(raw: str) -> list[str]:
        try:
            values = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(values, list):
            return []
        return [str(value) for value in values]

    async def _enforce_verification_attempt_limit(
        self, claimant_id: str, found_item_id: str
    ) -> None:
        now = now_beijing().replace(tzinfo=None)
        count, latest = await self._claim_repo.verification_failure_stats(
            claimant_id=claimant_id,
            found_item_id=found_item_id,
            since=now - VERIFY_FAILURE_WINDOW,
            failure_reason=VERIFY_FAILURE_REASON,
        )
        if count >= VERIFY_FAILURE_LIMIT or (
            latest is not None and latest > now - VERIFY_FAILURE_COOLDOWN
        ):
            raise BizError(
                ErrorCode.CLAIM_ANSWER_MISMATCH,
                "验证未通过, 请稍后重试",
            )

    async def _get_claim_or_raise(self, claim_id: str) -> ClaimRequest:
        claim = await self._claim_repo.get_by_id(claim_id)
        if claim is None:
            raise BizError(ErrorCode.CLAIM_NOT_FOUND)
        return claim

    async def _get_claim_for_update_or_raise(self, claim_id: str) -> ClaimRequest:
        claim = await self._claim_repo.get_by_id_for_update(claim_id)
        if claim is None:
            raise BizError(ErrorCode.CLAIM_NOT_FOUND)
        return claim

    async def _lock_claim_and_found(self, claim_id: str) -> tuple[ClaimRequest, Any]:
        current = await self._get_claim_or_raise(claim_id)
        found_item = await self._item_svc.get_found_item_for_update_internal(current.found_item_id)
        claim = await self._get_claim_for_update_or_raise(claim_id)
        if claim.found_item_id != found_item.id:
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        return claim, found_item

    def _is_party_or_admin(
        self, claim: ClaimRequest, finder_id: str, current_user: CurrentUser
    ) -> bool:
        return current_user.role == "ADMIN" or current_user.id in {claim.claimant_id, finder_id}

    def _parse_status_filter(self, value: str | None) -> set[str] | None:
        if not value:
            return None
        statuses = {part.strip() for part in value.split(",") if part.strip()}
        invalid = statuses - {
            "PENDING",
            "ANSWER_PASSED",
            "PROOF_PENDING",
            "APPROVED",
            "REJECTED",
            "APPEALING",
            "HANDED_OVER",
            "TERMINATED",
        }
        if invalid:
            raise BizError(ErrorCode.PARAM_ERROR, f"Invalid reviewStatus: {invalid}")
        return statuses

    async def terminate_active_claims(
        self,
        found_item_id: str,
        *,
        operator_id: str,
        operator_role: str,
    ) -> int:
        found_item = await self._item_svc.get_found_item_for_update_internal(found_item_id)
        claims = await self._claim_repo.list_active_for_update(found_item_id)
        for claim in claims:
            claim.review_status = "TERMINATED"
            await self._claim_repo.update(claim)
            if claim.match_id:
                await self._match_svc.expire_match(claim.match_id)
            for user_id in {claim.claimant_id, found_item.user_id}:
                await self._notification_svc.create_notice(
                    user_id=user_id,
                    notice_type="CLAIM_REVIEW",
                    title="认领已终止",
                    content=f"{found_item.item_name} 已关闭, 关联认领终止",
                    related_type="CLAIM",
                    related_id=claim.id,
                )
            await self._log_svc.create_log(
                operator_id=operator_id,
                operator_role=operator_role,
                biz_type="CLAIM",
                biz_id=claim.id,
                action="UPDATE_STATUS",
                detail="招领关闭, 终止活动认领",
            )
        return len(claims)

    async def terminate_claim_for_report(
        self,
        claim_id: str,
        *,
        operator_id: str,
        operator_role: str,
    ) -> int:
        claim, found_item = await self._lock_claim_and_found(claim_id)
        if claim.review_status not in REVIEWABLE_STATUSES | {"APPROVED"}:
            return 0
        old_status = claim.review_status
        transitioned = await self._claim_repo.transition_status(
            claim_id=claim.id,
            expected_status=old_status,
            new_status="TERMINATED",
            reject_reason=claim.reject_reason,
        )
        if not transitioned:
            raise BizError(ErrorCode.REVIEW_STATE_CHANGED)
        claim.review_status = "TERMINATED"
        if claim.match_id:
            await self._match_svc.expire_match(claim.match_id)
        if not await self._claim_repo.has_active_claim(
            claim.found_item_id, exclude_claim_id=claim.id
        ):
            await self._item_svc.transition_found_status_internal(
                claim.found_item_id,
                expected_status="CLAIMING",
                new_status="PENDING",
            )
        for user_id in {claim.claimant_id, found_item.user_id}:
            await self._notification_svc.create_notice(
                user_id=user_id,
                notice_type="CLAIM_REVIEW",
                title="认领已由管理员终止",
                content=f"认领 {claim.id} 因核实举报已终止",
                related_type="CLAIM",
                related_id=claim.id,
                priority="HIGH",
            )
        await self._log_svc.create_log(
            operator_id=operator_id,
            operator_role=operator_role,
            biz_type="CLAIM",
            biz_id=claim.id,
            action="UPDATE_STATUS",
            detail=f"举报联动终止认领: {old_status} -> TERMINATED",
        )
        return 1

    async def get_handover_stats_internal(self) -> dict[str, float | int]:
        handed_over_count = await self._claim_repo.count_by_status("HANDED_OVER")
        completed_times = await self._handover_repo.list_completed_item_times()
        durations = [
            (completed_at - created_at).total_seconds() / 3600
            for created_at, completed_at in completed_times
        ]
        avg_handle_hours = sum(durations) / len(durations) if durations else 0
        return {
            "handedOverCount": handed_over_count,
            "avgHandleHours": round(avg_handle_hours, 2),
        }

    async def _to_detail(
        self, claim: ClaimRequest, current_user: CurrentUser
    ) -> ClaimDetailResponse:
        can_view_score = current_user.role == "ADMIN" or current_user.id != claim.claimant_id
        answers = [
            ClaimAnswerOutput(
                question_id=answer.question_id,
                question_text=answer.question_text,
                answer_text=answer.answer_text,
                match_score=float(answer.match_score) if can_view_score else None,
            )
            for answer in await self._answer_repo.get_by_claim_id(claim.id)
        ]
        handover_orm = await self._handover_repo.get_by_claim_id(claim.id)
        handover = None
        if handover_orm is not None:
            handover = HandoverOutput(
                id=handover_orm.id,
                method=handover_orm.method,
                handover_location=handover_orm.handover_location,
                handover_time=format_beijing(handover_orm.handover_time),
                owner_confirmed=bool(handover_orm.owner_confirmed),
                finder_confirmed=bool(handover_orm.finder_confirmed),
                completed_at=(
                    format_beijing(handover_orm.completed_at)
                    if handover_orm.completed_at is not None
                    else None
                ),
                created_at=format_beijing(handover_orm.created_at),
            )
        return ClaimDetailResponse(
            id=claim.id,
            match_id=claim.match_id,
            found_item_id=claim.found_item_id,
            claimant_id=claim.claimant_id,
            verify_level=claim.verify_level,
            review_status=claim.review_status,
            reject_reason=claim.reject_reason,
            appeal_reason=claim.appeal_reason,
            answers=answers,
            proof_image_urls=await self._item_svc.get_claim_proof_images_internal(claim.id),
            proof_text=claim.proof_text,
            handover=handover,
            claimed_at=format_beijing(claim.claimed_at),
            updated_at=format_beijing(claim.updated_at),
        )

    async def _to_admin_list_item(self, claim: ClaimRequest) -> AdminClaimListItem:
        found_item = await self._item_svc.get_found_item_internal(claim.found_item_id)
        claimant = await self._user_svc.get_user_internal(claim.claimant_id)
        finder = await self._user_svc.get_user_internal(found_item.user_id)
        if claimant is None or finder is None:
            raise BizError(ErrorCode.NOT_FOUND, "认领关联用户不存在")
        return AdminClaimListItem(
            id=claim.id,
            found_item_id=claim.found_item_id,
            verify_level=claim.verify_level,
            review_status=claim.review_status,
            verification_source=claim.verification_source,
            verification_degraded=bool(claim.verification_degraded),
            reject_reason=claim.reject_reason,
            appeal_reason=claim.appeal_reason,
            claimant=ClaimPartySummary(
                id=claimant.id,
                nickname=claimant.nickname,
                phone=claimant.phone,
                status=claimant.status,
            ),
            finder=ClaimPartySummary(
                id=finder.id,
                nickname=finder.nickname,
                phone=finder.phone,
                status=finder.status,
            ),
            item=ClaimItemSummary(
                id=found_item.id,
                item_name=found_item.item_name,
                category=found_item.category,
                description=found_item.description,
                found_time=format_beijing(found_item.found_time),
                found_location=found_item.found_location,
                custody_type=found_item.custody_type,
                contact_preference=found_item.contact_preference,
                status=found_item.status,
                review_status=found_item.review_status,
            ),
            claimed_at=format_beijing(claim.claimed_at),
            updated_at=format_beijing(claim.updated_at),
        )
