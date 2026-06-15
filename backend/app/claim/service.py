import json
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.claim.models import ClaimAnswer, ClaimRequest, HandoverRecord
from app.claim.repository import (
    ClaimAnswerRepository,
    ClaimRequestRepository,
    HandoverRecordRepository,
)
from app.claim.schemas import (
    ClaimAnswerInput,
    ClaimAnswerOutput,
    ClaimAppealRequest,
    ClaimDetailResponse,
    ClaimMyListItem,
    ClaimMyQuery,
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
from app.credit.service import CreditService
from app.db.ulid import generate_ulid
from app.item.service import ItemService
from app.match.service import MatchService
from app.notification.service import NotificationService
from app.operation_log.service import OperationLogService
from app.user.schemas import CurrentUser
from app.user.service import UserService

REVIEWABLE_STATUSES = {"PENDING", "ANSWER_PASSED", "PROOF_PENDING", "APPEALING"}


class ClaimService:
    def __init__(self, session: AsyncSession) -> None:
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

    async def create_claim(
        self, req: CreateClaimRequest, current_user: CurrentUser
    ) -> CreateClaimResponse:
        user = await self._user_svc.get_user_internal(current_user.id)
        if user is None:
            raise BizError(ErrorCode.UNAUTHORIZED)
        if user.credit_score < 30:
            raise BizError(ErrorCode.CREDIT_FROZEN)

        found_item = await self._item_svc.get_found_item_internal(req.found_item_id)
        if found_item.status not in {"PENDING", "CLAIMING"}:
            raise BizError(ErrorCode.ITEM_CLOSED)
        if found_item.user_id == current_user.id:
            raise BizError(ErrorCode.CLAIM_NOT_PARTY, "不可认领自己发布的招领")
        if await self._claim_repo.has_active_claim(req.found_item_id):
            raise BizError(ErrorCode.CLAIM_DUPLICATE)

        if req.match_id:
            match = await self._match_svc.get_by_id(req.match_id)
            if match is None or match.found_item_id != req.found_item_id:
                raise BizError(ErrorCode.MATCH_NOT_FOUND)

        questions = await self._item_svc.get_verify_questions_internal(req.found_item_id)
        verify_level, review_status, answers = self._build_initial_claim_state(
            claim_answers=req.answers,
            questions=questions,
            proof_image_urls=req.proof_image_urls,
            found_category=found_item.category,
            user_cert_status=user.cert_status,
        )

        claim_id = generate_ulid()
        claim = ClaimRequest(
            id=claim_id,
            match_id=req.match_id,
            found_item_id=req.found_item_id,
            claimant_id=current_user.id,
            verify_level=verify_level,
            review_status=review_status,
        )
        await self._claim_repo.create(claim)
        for answer in answers:
            answer.claim_id = claim_id
        await self._answer_repo.create_batch(answers)
        await self._item_svc.create_claim_proof_images_internal(claim_id, req.proof_image_urls)
        if review_status != "REJECTED":
            await self._item_svc.update_found_status_internal(req.found_item_id, "CLAIMING")
        if req.match_id:
            match = await self._match_svc.get_by_id(req.match_id)
            if match is not None:
                await self._match_svc.mark_claimed(match)

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
        return await self._to_detail(claim)

    async def review_claim(
        self, claim_id: str, req: ClaimReviewRequest, current_user: CurrentUser
    ) -> dict[str, str]:
        claim = await self._get_claim_or_raise(claim_id)
        found_item = await self._item_svc.get_found_item_internal(claim.found_item_id)
        is_admin = current_user.role == "ADMIN"
        if found_item.user_id != current_user.id and not is_admin:
            raise BizError(ErrorCode.CLAIM_NOT_PARTY)
        if claim.review_status not in REVIEWABLE_STATUSES:
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        if claim.review_status == "APPEALING" and not is_admin:
            raise BizError(ErrorCode.CLAIM_NOT_PARTY)

        old_status = claim.review_status
        if req.action == "APPROVE":
            claim.review_status = "APPROVED"
            claim.reject_reason = None
            action = "REVIEW_APPROVE"
        else:
            claim.review_status = "REJECTED"
            claim.reject_reason = req.comment
            action = "REVIEW_REJECT"

        await self._claim_repo.update(claim)
        await self._notification_svc.create_notice(
            user_id=claim.claimant_id,
            notice_type="CLAIM_REVIEW",
            title="认领审核结果",
            content=f"认领状态变更: {old_status} -> {claim.review_status}",
            related_type="CLAIM",
            related_id=claim.id,
        )
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="CLAIM",
            biz_id=claim.id,
            action=action,
            detail=f"认领审核: {old_status} -> {claim.review_status}",
        )
        await self._session.commit()
        return {"id": claim_id, "reviewStatus": claim.review_status}

    async def submit_proofs(
        self, claim_id: str, req: ClaimProofsRequest, current_user: CurrentUser
    ) -> dict[str, str]:
        claim = await self._get_claim_or_raise(claim_id)
        if claim.claimant_id != current_user.id:
            raise BizError(ErrorCode.CLAIM_NOT_PARTY)
        if claim.review_status != "PROOF_PENDING":
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        claim.proof_text = req.proof_text
        claim.review_status = "ANSWER_PASSED"
        await self._item_svc.create_claim_proof_images_internal(claim_id, req.proof_image_urls)
        await self._claim_repo.update(claim)
        await self._log_svc.create_log(
            operator_id=current_user.id,
            operator_role=current_user.role,
            biz_type="CLAIM",
            biz_id=claim_id,
            action="UPDATE_STATUS",
            detail="补充凭证: PROOF_PENDING -> ANSWER_PASSED",
        )
        await self._session.commit()
        return {"id": claim_id, "reviewStatus": "ANSWER_PASSED"}

    async def appeal_claim(
        self, claim_id: str, req: ClaimAppealRequest, current_user: CurrentUser
    ) -> dict[str, str]:
        claim = await self._get_claim_or_raise(claim_id)
        if claim.claimant_id != current_user.id:
            raise BizError(ErrorCode.CLAIM_NOT_PARTY)
        if claim.review_status != "REJECTED":
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        if claim.appeal_reason:
            raise BizError(ErrorCode.APPEAL_DUPLICATE)
        claim.appeal_reason = req.reason
        claim.review_status = "APPEALING"
        await self._claim_repo.update(claim)
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

    async def create_handover(
        self, claim_id: str, req: CreateHandoverRequest, current_user: CurrentUser
    ) -> CreateHandoverResponse:
        claim = await self._get_claim_or_raise(claim_id)
        found_item = await self._item_svc.get_found_item_internal(claim.found_item_id)
        if not self._is_party_or_admin(claim, found_item.user_id, current_user):
            raise BizError(ErrorCode.CLAIM_NOT_PARTY)
        if claim.review_status != "APPROVED":
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)
        if await self._handover_repo.get_by_claim_id(claim_id) is not None:
            raise BizError(ErrorCode.DUPLICATE_SUBMIT)

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
        await self._handover_repo.create(handover)
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
        # Keep this path aligned with the rest of the service: let SQLAlchemy
        # autobegin the transaction and commit once at the end. Calling
        # session.begin() here can fail after get_current_user has already
        # issued a SELECT on the same session.
        claim = await self._get_claim_or_raise(claim_id)
        handover = await self._handover_repo.get_by_claim_id(claim_id)
        if handover is None:
            raise BizError(ErrorCode.CLAIM_INVALID_STATE, "交接尚未创建")
        found_item = await self._item_svc.get_found_item_internal(claim.found_item_id)
        if claim.review_status not in {"APPROVED", "HANDED_OVER"}:
            raise BizError(ErrorCode.CLAIM_INVALID_STATE)

        if req.role == "OWNER":
            if claim.claimant_id != current_user.id:
                raise BizError(ErrorCode.CLAIM_NOT_PARTY)
            handover.owner_confirmed = 1
        else:
            if found_item.user_id != current_user.id:
                raise BizError(ErrorCode.CLAIM_NOT_PARTY)
            handover.finder_confirmed = 1
        await self._handover_repo.update(handover)

        if (
            handover.owner_confirmed
            and handover.finder_confirmed
            and claim.review_status != "HANDED_OVER"
        ):
            handover.completed_at = now_beijing().replace(tzinfo=None)
            claim.review_status = "HANDED_OVER"
            await self._handover_repo.update(handover)
            await self._claim_repo.update(claim)
            await self._item_svc.update_found_status_internal(claim.found_item_id, "RETURNED")
            if claim.match_id:
                match = await self._match_svc.get_by_id(claim.match_id)
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
        claim_answers: list[ClaimAnswerInput],
        questions: list[Any],
        proof_image_urls: list[str],
        found_category: str,
        user_cert_status: str,
    ) -> tuple[str, str, list[ClaimAnswer]]:
        if found_category == "CERT" and user_cert_status == "APPROVED":
            return "FAST_TRACK", "APPROVED", []
        if questions:
            answers, passed = self._score_answers(claim_answers, questions)
            return "LEVEL_1", "ANSWER_PASSED" if passed else "REJECTED", answers
        if proof_image_urls:
            return "LEVEL_2", "ANSWER_PASSED", []
        return "LEVEL_2", "PROOF_PENDING", []

    def _score_answers(
        self, claim_answers: list[ClaimAnswerInput], questions: list[Any]
    ) -> tuple[list[ClaimAnswer], bool]:
        answer_by_question = {answer.question_id: answer.answer_text for answer in claim_answers}
        results: list[ClaimAnswer] = []
        passed = True
        for question in questions:
            answer_text = answer_by_question.get(question.id, "")
            keywords = json.loads(question.answer_keywords)
            normalized_answer = answer_text.lower()
            hit = any(str(keyword).lower() in normalized_answer for keyword in keywords)
            score = Decimal("100.00") if hit else Decimal("0.00")
            if not hit:
                passed = False
            results.append(
                ClaimAnswer(
                    id=generate_ulid(),
                    claim_id="",
                    question_id=question.id,
                    question_text=question.question_text,
                    answer_text=answer_text,
                    match_score=score,
                )
            )
        return results, passed

    async def _get_claim_or_raise(self, claim_id: str) -> ClaimRequest:
        claim = await self._claim_repo.get_by_id(claim_id)
        if claim is None:
            raise BizError(ErrorCode.CLAIM_NOT_FOUND)
        return claim

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
        }
        if invalid:
            raise BizError(ErrorCode.PARAM_ERROR, f"Invalid reviewStatus: {invalid}")
        return statuses

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

    async def _to_detail(self, claim: ClaimRequest) -> ClaimDetailResponse:
        answers = [
            ClaimAnswerOutput(
                question_id=answer.question_id,
                question_text=answer.question_text,
                answer_text=answer.answer_text,
                match_score=float(answer.match_score),
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
            answers=answers,
            proof_image_urls=await self._item_svc.get_claim_proof_images_internal(claim.id),
            proof_text=claim.proof_text,
            handover=handover,
            claimed_at=format_beijing(claim.claimed_at),
            updated_at=format_beijing(claim.updated_at),
        )
