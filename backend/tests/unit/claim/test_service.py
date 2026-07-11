from datetime import timedelta
from types import SimpleNamespace

import pytest
from app.claim.models import ClaimRequest
from app.claim.schemas import (
    ClaimAnswerInput,
    ClaimAppealRequest,
    ClaimReviewRequest,
    ConfirmHandoverRequest,
    CreateClaimRequest,
    CreateHandoverRequest,
)
from app.claim.service import ClaimService, determine_verify_level
from app.common.errors import BizError, ErrorCode
from app.db.ulid import generate_ulid
from app.item.schemas import CreateFoundItemRequest, CreateLostItemRequest, VerifyQuestionInput
from app.item.service import ItemService
from app.match.models import MatchResult
from app.user.schemas import CurrentUser
from app.user.service import UserService
from fastapi import BackgroundTasks
from sqlalchemy import select

CLAIMANT = CurrentUser(id="01TESTUSER000000000000001", role="USER", status="ACTIVE")
FINDER = CurrentUser(id="01TESTSTAFF00000000000001", role="STAFF", status="ACTIVE")
ADMIN = CurrentUser(id="01TESTADMIN00000000000001", role="ADMIN", status="ACTIVE")


@pytest.mark.parametrize(
    ("category", "credit", "expected"),
    [
        ("CERT", 100, "LEVEL_3"),
        ("CERT", 40, "LEVEL_3"),
        ("ELECTRONIC", 100, "LEVEL_2"),
        ("ELECTRONIC", 40, "LEVEL_3"),
        ("OTHER", 100, "LEVEL_1"),
        ("OTHER", 30, "LEVEL_2"),
        ("OTHER", 59, "LEVEL_2"),
        ("OTHER", 60, "LEVEL_1"),
    ],
)
def test_determine_verify_level_is_pure_rule(category: str, credit: int, expected: str) -> None:
    assert determine_verify_level(category, credit) == expected


def test_question_scoring_averages_per_question_keyword_ratios() -> None:
    service = object.__new__(ClaimService)
    questions = [
        SimpleNamespace(
            id="q1", question_text="first", answer_keywords='["red", "round", "metal"]'
        ),
        SimpleNamespace(id="q2", question_text="second", answer_keywords='["engraved", "name"]'),
    ]
    answers = [
        ClaimAnswerInput(questionId="q1", answerText="red round"),
        ClaimAnswerInput(questionId="q2", answerText="engraved"),
    ]

    scored, passed = service._score_answers(answers, questions)

    assert [float(answer.match_score) for answer in scored] == [66.67, 50.0]
    assert passed is False


def test_question_scoring_can_pass_by_average_not_every_question() -> None:
    service = object.__new__(ClaimService)
    questions = [
        SimpleNamespace(id="q1", question_text="one", answer_keywords='["red"]'),
        SimpleNamespace(id="q2", question_text="two", answer_keywords='["round"]'),
        SimpleNamespace(id="q3", question_text="three", answer_keywords='["metal"]'),
    ]
    answers = [
        ClaimAnswerInput(questionId="q1", answerText="red"),
        ClaimAnswerInput(questionId="q2", answerText="round"),
        ClaimAnswerInput(questionId="q3", answerText="unknown"),
    ]

    _, passed = service._score_answers(answers, questions)

    assert passed is True


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
    duplicate_handover = await claim_svc.create_handover(
        claim.id,
        CreateHandoverRequest(
            method="MEETUP",
            handoverLocation="不同地点也应返回既有安排",
            handoverTime="2099-01-02 10:00:00",
        ),
        FINDER,
    )
    assert duplicate_handover.handover_id == handover.handover_id

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

    repeated = await claim_svc.confirm_handover(
        claim.id, ConfirmHandoverRequest(role="FINDER"), FINDER
    )
    assert repeated["reviewStatus"] == "HANDED_OVER"
    claimant = await UserService(session).get_user_internal(CLAIMANT.id)
    finder = await UserService(session).get_user_internal(FINDER.id)
    assert claimant is not None and claimant.credit_score == 110
    assert finder is not None and finder.credit_score == 110


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


async def test_create_claim_requires_complete_unique_question_answers(session, seeded_users):
    item_svc = ItemService(session)
    found = await item_svc.create_found_item(
        CreateFoundItemRequest(
            itemName="Question Item",
            category="OTHER",
            foundTime="2026-05-01 10:00:00",
            foundLocation="Gate",
            custodyType="SELF",
            contactPreference="IN_APP",
            verifyQuestions=[VerifyQuestionInput(questionText="Feature?", answerKeywords=["blue"])],
        ),
        FINDER,
        BackgroundTasks(),
    )
    question = (await item_svc.get_verify_questions_internal(found.id))[0]
    svc = ClaimService(session)

    with pytest.raises(BizError) as missing:
        await svc.create_claim(CreateClaimRequest(foundItemId=found.id, answers=[]), CLAIMANT)
    assert missing.value.code == ErrorCode.PARAM_ERROR

    with pytest.raises(BizError) as repeated:
        await svc.create_claim(
            CreateClaimRequest(
                foundItemId=found.id,
                answers=[
                    ClaimAnswerInput(questionId=question.id, answerText="blue"),
                    ClaimAnswerInput(questionId=question.id, answerText="blue"),
                ],
            ),
            CLAIMANT,
        )
    assert repeated.value.code == ErrorCode.PARAM_ERROR

    with pytest.raises(BizError) as unknown:
        await svc.create_claim(
            CreateClaimRequest(
                foundItemId=found.id,
                answers=[ClaimAnswerInput(questionId=generate_ulid(), answerText="blue")],
            ),
            CLAIMANT,
        )
    assert unknown.value.code == ErrorCode.PARAM_ERROR
    assert (await item_svc.get_found_item_internal(found.id)).status == "PENDING"


async def test_match_claim_requires_lost_item_ownership(session, seeded_users):
    item_svc = ItemService(session)
    lost = await item_svc.create_lost_item(
        CreateLostItemRequest(
            itemName="Admin Wallet",
            category="DAILY_USE",
            lostTimeStart="2026-05-01 08:00:00",
            lostTimeEnd="2026-05-01 09:00:00",
            lostLocation="Library",
        ),
        ADMIN,
        BackgroundTasks(),
    )
    found = await item_svc.create_found_item(
        CreateFoundItemRequest(
            itemName="Admin Wallet",
            category="DAILY_USE",
            foundTime="2026-05-01 10:00:00",
            foundLocation="Library",
            custodyType="SELF",
            contactPreference="IN_APP",
        ),
        FINDER,
        BackgroundTasks(),
    )
    match = MatchResult(
        id=generate_ulid(),
        lost_item_id=lost.id,
        found_item_id=found.id,
        match_status="NEW",
    )
    session.add(match)
    await session.commit()

    with pytest.raises(BizError) as exc_info:
        await ClaimService(session).create_claim(
            CreateClaimRequest(foundItemId=found.id, matchId=match.id), CLAIMANT
        )
    assert exc_info.value.code == ErrorCode.CLAIM_NOT_PARTY


async def test_reject_releases_found_and_match_and_detail_hides_score(session, seeded_users):
    item_svc = ItemService(session)
    lost = await item_svc.create_lost_item(
        CreateLostItemRequest(
            itemName="Blue Bottle",
            category="DAILY_USE",
            lostTimeStart="2026-05-02 08:00:00",
            lostTimeEnd="2026-05-02 09:00:00",
            lostLocation="Library",
        ),
        CLAIMANT,
        BackgroundTasks(),
    )
    found = await item_svc.create_found_item(
        CreateFoundItemRequest(
            itemName="Blue Bottle",
            category="DAILY_USE",
            foundTime="2026-05-02 10:00:00",
            foundLocation="Library",
            custodyType="SELF",
            contactPreference="IN_APP",
            verifyQuestions=[VerifyQuestionInput(questionText="Color?", answerKeywords=["blue"])],
        ),
        FINDER,
        BackgroundTasks(),
    )
    match = MatchResult(
        id=generate_ulid(),
        lost_item_id=lost.id,
        found_item_id=found.id,
        match_status="READ",
    )
    session.add(match)
    await session.commit()
    question = (await item_svc.get_verify_questions_internal(found.id))[0]
    svc = ClaimService(session)
    claim = await svc.create_claim(
        CreateClaimRequest(
            foundItemId=found.id,
            matchId=match.id,
            answers=[ClaimAnswerInput(questionId=question.id, answerText="blue")],
        ),
        CLAIMANT,
    )

    claimant_detail = await svc.get_claim_detail(claim.id, CLAIMANT)
    finder_detail = await svc.get_claim_detail(claim.id, FINDER)
    assert claimant_detail.answers[0].match_score is None
    assert finder_detail.answers[0].match_score == 100

    await svc.review_claim(
        claim.id, ClaimReviewRequest(action="REJECT", comment="需要更多凭证"), FINDER
    )
    assert (await item_svc.get_found_item_internal(found.id)).status == "PENDING"
    assert match.match_status == "READ"

    await svc.appeal_claim(claim.id, ClaimAppealRequest(reason="可现场核对"), CLAIMANT)
    detail = await svc.get_claim_detail(claim.id, ADMIN)
    assert detail.appeal_reason == "可现场核对"
    with pytest.raises(BizError) as owner_review:
        await svc.review_claim(claim.id, ClaimReviewRequest(action="APPROVE"), FINDER)
    assert owner_review.value.code == ErrorCode.CLAIM_NOT_PARTY


async def test_cert_claim_uses_strict_manual_path(session, seeded_users):
    item_svc = ItemService(session)
    found = await item_svc.create_found_item(
        CreateFoundItemRequest(
            itemName="Campus Card",
            category="CERT",
            foundTime="2026-05-03 10:00:00",
            foundLocation="Office",
            custodyType="OFFICE",
            contactPreference="IN_APP",
        ),
        FINDER,
        BackgroundTasks(),
    )

    claim = await ClaimService(session).create_claim(
        CreateClaimRequest(foundItemId=found.id), CLAIMANT
    )

    assert claim.verify_level == "LEVEL_3"
    assert claim.review_status == "PROOF_PENDING"


async def test_level_two_requires_proof_before_approval(session, seeded_users):
    item_svc = ItemService(session)
    found = await item_svc.create_found_item(
        CreateFoundItemRequest(
            itemName="Laptop",
            category="ELECTRONIC",
            foundTime="2026-05-04 10:00:00",
            foundLocation="Office",
            custodyType="OFFICE",
            contactPreference="IN_APP",
        ),
        FINDER,
        BackgroundTasks(),
    )
    svc = ClaimService(session)

    claim = await svc.create_claim(CreateClaimRequest(foundItemId=found.id), CLAIMANT)

    assert claim.verify_level == "LEVEL_2"
    assert claim.review_status == "PROOF_PENDING"
    with pytest.raises(BizError) as exc_info:
        await svc.review_claim(claim.id, ClaimReviewRequest(action="APPROVE"), FINDER)
    assert exc_info.value.code == ErrorCode.CLAIM_PROOF_MISSING


async def test_level_three_with_proof_still_requires_manual_review(session, seeded_users):
    item_svc = ItemService(session)
    found = await item_svc.create_found_item(
        CreateFoundItemRequest(
            itemName="Campus Card",
            category="CERT",
            foundTime="2026-05-05 10:00:00",
            foundLocation="Office",
            custodyType="OFFICE",
            contactPreference="IN_APP",
        ),
        FINDER,
        BackgroundTasks(),
    )
    proof_ref = f"asset://CLAIM_PROOF/{CLAIMANT.id}/202607/{'a' * 32}.jpg"

    claim = await ClaimService(session).create_claim(
        CreateClaimRequest(foundItemId=found.id, proofImageUrls=[proof_ref]), CLAIMANT
    )

    assert claim.verify_level == "LEVEL_3"
    assert claim.review_status == "PENDING"


async def test_question_failure_is_generic_persisted_and_cooled_down(session, seeded_users):
    item_svc = ItemService(session)
    found = await item_svc.create_found_item(
        CreateFoundItemRequest(
            itemName="Secret Bottle",
            category="OTHER",
            foundTime="2026-05-06 10:00:00",
            foundLocation="Office",
            custodyType="SELF",
            contactPreference="IN_APP",
            verifyQuestions=[
                VerifyQuestionInput(questionText="Features?", answerKeywords=["red", "round"])
            ],
        ),
        FINDER,
        BackgroundTasks(),
    )
    question = (await item_svc.get_verify_questions_internal(found.id))[0]
    svc = ClaimService(session)
    failed_request = CreateClaimRequest(
        foundItemId=found.id,
        answers=[ClaimAnswerInput(questionId=question.id, answerText="red")],
    )

    with pytest.raises(BizError) as first:
        await svc.create_claim(failed_request, CLAIMANT)
    with pytest.raises(BizError) as cooldown:
        await svc.create_claim(
            CreateClaimRequest(
                foundItemId=found.id,
                answers=[ClaimAnswerInput(questionId=question.id, answerText="red and round")],
            ),
            CLAIMANT,
        )

    assert first.value.code == ErrorCode.CLAIM_ANSWER_MISMATCH
    assert cooldown.value.code == ErrorCode.CLAIM_ANSWER_MISMATCH
    assert first.value.message == cooldown.value.message
    failures = await session.execute(
        select(ClaimRequest).where(
            ClaimRequest.claimant_id == CLAIMANT.id,
            ClaimRequest.found_item_id == found.id,
        )
    )
    stored = failures.scalar_one()
    assert stored.review_status == "REJECTED"
    assert stored.reject_reason == "验证未通过"

    stored.claimed_at -= timedelta(minutes=6)
    await session.commit()
    accepted = await svc.create_claim(
        CreateClaimRequest(
            foundItemId=found.id,
            answers=[ClaimAnswerInput(questionId=question.id, answerText="red and round")],
        ),
        CLAIMANT,
    )
    assert accepted.review_status == "ANSWER_PASSED"


async def test_question_failures_are_limited_to_three_per_day(session, seeded_users):
    item_svc = ItemService(session)
    found = await item_svc.create_found_item(
        CreateFoundItemRequest(
            itemName="Limited Attempts",
            category="OTHER",
            foundTime="2026-05-07 10:00:00",
            foundLocation="Office",
            custodyType="SELF",
            contactPreference="IN_APP",
            verifyQuestions=[VerifyQuestionInput(questionText="Color?", answerKeywords=["blue"])],
        ),
        FINDER,
        BackgroundTasks(),
    )
    question = (await item_svc.get_verify_questions_internal(found.id))[0]
    svc = ClaimService(session)
    request = CreateClaimRequest(
        foundItemId=found.id,
        answers=[ClaimAnswerInput(questionId=question.id, answerText="wrong")],
    )

    for attempt in range(3):
        with pytest.raises(BizError) as failed:
            await svc.create_claim(request, CLAIMANT)
        assert failed.value.code == ErrorCode.CLAIM_ANSWER_MISMATCH
        latest = (
            (
                await session.execute(
                    select(ClaimRequest)
                    .where(
                        ClaimRequest.claimant_id == CLAIMANT.id,
                        ClaimRequest.found_item_id == found.id,
                    )
                    .order_by(ClaimRequest.claimed_at.desc(), ClaimRequest.id.desc())
                )
            )
            .scalars()
            .first()
        )
        assert latest is not None
        latest.claimed_at -= timedelta(minutes=6 * (attempt + 1))
        await session.commit()

    with pytest.raises(BizError) as limited:
        await svc.create_claim(request, CLAIMANT)
    assert limited.value.code == ErrorCode.CLAIM_ANSWER_MISMATCH
    failures = await session.execute(
        select(ClaimRequest).where(
            ClaimRequest.claimant_id == CLAIMANT.id,
            ClaimRequest.found_item_id == found.id,
        )
    )
    assert len(failures.scalars().all()) == 3
