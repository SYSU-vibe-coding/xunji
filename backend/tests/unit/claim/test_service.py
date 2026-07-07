from app.claim.schemas import (
    ClaimAnswerInput,
    ClaimReviewRequest,
    ConfirmHandoverRequest,
    CreateClaimRequest,
    CreateHandoverRequest,
)
from app.claim.service import ClaimService
from app.db.ulid import generate_ulid
from app.item.schemas import CreateFoundItemRequest, CreateLostItemRequest, VerifyQuestionInput
from app.item.service import ItemService
from app.match.models import MatchResult
from app.user.schemas import CurrentUser
from app.user.service import UserService
from fastapi import BackgroundTasks

CLAIMANT = CurrentUser(id="01TESTUSER000000000000001", role="USER", status="ACTIVE")
FINDER = CurrentUser(id="01TESTSTAFF00000000000001", role="STAFF", status="ACTIVE")


async def test_claim_handover_flow_updates_credit_and_status(session, seeded_users):
    item_svc = ItemService(session)
    found = await item_svc.create_found_item(
        CreateFoundItemRequest(
            itemName="蓝色水杯",
            category="DAILY_USE",
            foundTime="2026-04-23 10:00:00",
            foundLocation="图书馆",
            custodyType="SELF",
            contactPreference="IN_APP",
            verifyQuestions=[
                VerifyQuestionInput(questionText="水杯颜色?", answerKeywords=["蓝色", "蓝"])
            ],
        ),
        FINDER,
        BackgroundTasks(),
    )
    questions = await item_svc.get_verify_questions_internal(found.id)

    claim_svc = ClaimService(session)
    claim = await claim_svc.create_claim(
        CreateClaimRequest(
            foundItemId=found.id,
            answers=[ClaimAnswerInput(questionId=questions[0].id, answerText="蓝色")],
        ),
        CLAIMANT,
    )
    assert claim.review_status == "ANSWER_PASSED"

    reviewed = await claim_svc.review_claim(claim.id, ClaimReviewRequest(action="APPROVE"), FINDER)
    assert reviewed["reviewStatus"] == "APPROVED"

    handover = await claim_svc.create_handover(
        claim.id,
        CreateHandoverRequest(
            method="MEETUP",
            handoverLocation="图书馆门口",
            handoverTime="2099-01-01 10:00:00",
        ),
        CLAIMANT,
    )
    assert handover.handover_id

    first = await claim_svc.confirm_handover(
        claim.id, ConfirmHandoverRequest(role="OWNER"), CLAIMANT
    )
    assert first["reviewStatus"] == "APPROVED"
    second = await claim_svc.confirm_handover(
        claim.id, ConfirmHandoverRequest(role="FINDER"), FINDER
    )
    assert second["reviewStatus"] == "HANDED_OVER"

    claimant = await UserService(session).get_user_internal(CLAIMANT.id)
    finder = await UserService(session).get_user_internal(FINDER.id)
    found_item = await item_svc.get_found_item_internal(found.id)
    assert claimant is not None and claimant.credit_score == 110
    assert finder is not None and finder.credit_score == 110
    assert found_item.status == "RETURNED"


async def test_match_backed_handover_marks_lost_item_found(session, seeded_users):
    item_svc = ItemService(session)
    lost = await item_svc.create_lost_item(
        CreateLostItemRequest(
            itemName="Black Wallet",
            category="DAILY_USE",
            lostTimeStart="2026-04-23 08:00:00",
            lostTimeEnd="2026-04-23 09:00:00",
            lostLocation="Library",
        ),
        CLAIMANT,
        BackgroundTasks(),
    )
    found = await item_svc.create_found_item(
        CreateFoundItemRequest(
            itemName="Black Wallet",
            category="DAILY_USE",
            foundTime="2026-04-23 10:00:00",
            foundLocation="Library",
            custodyType="SELF",
            contactPreference="IN_APP",
            verifyQuestions=[VerifyQuestionInput(questionText="Color?", answerKeywords=["black"])],
        ),
        FINDER,
        BackgroundTasks(),
    )
    match_id = generate_ulid()
    session.add(
        MatchResult(
            id=match_id,
            lost_item_id=lost.id,
            found_item_id=found.id,
            match_status="NEW",
        )
    )
    await session.commit()

    questions = await item_svc.get_verify_questions_internal(found.id)
    claim_svc = ClaimService(session)
    claim = await claim_svc.create_claim(
        CreateClaimRequest(
            matchId=match_id,
            foundItemId=found.id,
            answers=[ClaimAnswerInput(questionId=questions[0].id, answerText="black")],
        ),
        CLAIMANT,
    )
    await claim_svc.review_claim(claim.id, ClaimReviewRequest(action="APPROVE"), FINDER)
    await claim_svc.create_handover(
        claim.id,
        CreateHandoverRequest(
            method="MEETUP",
            handoverLocation="Library gate",
            handoverTime="2099-01-01 10:00:00",
        ),
        CLAIMANT,
    )

    await claim_svc.confirm_handover(claim.id, ConfirmHandoverRequest(role="OWNER"), CLAIMANT)
    await claim_svc.confirm_handover(claim.id, ConfirmHandoverRequest(role="FINDER"), FINDER)

    found_item = await item_svc.get_found_item_internal(found.id)
    lost_item = await item_svc.get_lost_item_internal(lost.id)
    assert found_item.status == "RETURNED"
    assert lost_item.status == "FOUND"
