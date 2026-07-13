"""Semantic verification for private claim-question answers."""

from __future__ import annotations

from app.clients.dashscope import DashScopeClient
from app.schemas import AnswerVerifySource, VerifyClaimAnswersRequest, VerifyClaimAnswersResponse

PASS_THRESHOLD = 60.0


async def verify_claim_answers(
    req: VerifyClaimAnswersRequest,
    client: DashScopeClient | None,
) -> VerifyClaimAnswersResponse:
    checks = [
        {
            "question": item.question_text,
            "referenceAnswers": item.reference_answers,
            "userAnswer": item.answer_text,
        }
        for item in req.answers
    ]
    scores = await client.claim_answer_scores(checks) if client is not None else None
    if scores is not None:
        return _response(scores, degraded=False, source="TEXT_MODEL")
    return _response(_keyword_scores(req), degraded=True, source="KEYWORD_RULES")


def _keyword_scores(req: VerifyClaimAnswersRequest) -> list[float]:
    scores: list[float] = []
    for item in req.answers:
        normalized = item.answer_text.casefold()
        hits = sum(reference.casefold() in normalized for reference in item.reference_answers)
        scores.append(round(hits / len(item.reference_answers) * 100.0, 2))
    return scores


def _response(
    scores: list[float], *, degraded: bool, source: AnswerVerifySource
) -> VerifyClaimAnswersResponse:
    average = sum(scores) / len(scores)
    return VerifyClaimAnswersResponse(
        scores=[round(score, 2) for score in scores],
        passed=average >= PASS_THRESHOLD,
        degraded=degraded,
        source=source,
    )
