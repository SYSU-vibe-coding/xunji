import pytest
from app.schemas import (
    CalculateMatchResponse,
    ClassifyItemResponse,
    DetectSensitiveResponse,
)
from pydantic import ValidationError


@pytest.mark.parametrize("score", [-0.01, 100.01])
def test_match_response_rejects_out_of_range_scores(score: float) -> None:
    with pytest.raises(ValidationError):
        CalculateMatchResponse(
            imageScore=score,
            textScore=50,
            locationScore=50,
            timeScore=50,
            totalScore=50,
        )


@pytest.mark.parametrize("confidence", [-1, 101])
def test_classify_response_rejects_out_of_range_confidence(confidence: float) -> None:
    with pytest.raises(ValidationError):
        ClassifyItemResponse(category="OTHER", tags=[], confidence=confidence)


def test_classify_response_rejects_unknown_category() -> None:
    with pytest.raises(ValidationError):
        ClassifyItemResponse(category="UNKNOWN", tags=[], confidence=50)


def test_sensitive_response_rejects_unknown_sensitive_type() -> None:
    with pytest.raises(ValidationError):
        DetectSensitiveResponse(isSensitive=True, sensitiveType="PASSWORD")


def test_response_accepts_contract_values() -> None:
    resp = CalculateMatchResponse(
        imageScore=30,
        textScore=100,
        locationScore=0,
        timeScore=98,
        totalScore=61.8,
    )
    assert resp.model_dump(by_alias=True)["totalScore"] == 61.8
