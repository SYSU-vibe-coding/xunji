import pytest
from app.schemas import (
    CalculateMatchResponse,
    ClassifyItemRequest,
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
            imageAvailable=False,
            degraded=True,
            scoreSource="RULE_BASED",
        )


@pytest.mark.parametrize("confidence", [-1, 101])
def test_classify_response_rejects_out_of_range_confidence(confidence: float) -> None:
    with pytest.raises(ValidationError):
        ClassifyItemResponse(
            category="OTHER",
            tags=[],
            confidence=confidence,
            degraded=True,
            source="KEYWORD_RULES",
        )


def test_classify_response_rejects_unknown_category() -> None:
    with pytest.raises(ValidationError):
        ClassifyItemResponse(
            category="UNKNOWN",
            tags=[],
            confidence=50,
            degraded=True,
            source="KEYWORD_RULES",
        )


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
        imageAvailable=False,
        degraded=True,
        scoreSource="RULE_BASED",
    )
    assert resp.model_dump(by_alias=True)["totalScore"] == 61.8


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/image.jpg",
        "http://localhost/image.jpg",
        "http://127.0.0.1/image.jpg",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1/image.jpg",
        "http://[::1]/image.jpg",
        "https://untrusted.example/image.jpg",
    ],
)
def test_image_urls_reject_unsafe_or_unlisted_hosts(url: str) -> None:
    with pytest.raises(ValidationError):
        ClassifyItemRequest(imageUrls=[url])


def test_image_urls_accept_exact_and_wildcard_allowlist_hosts() -> None:
    exact = ClassifyItemRequest(imageUrls=["https://example.com/image.jpg"])
    wildcard = ClassifyItemRequest(
        imageUrls=["https://campus.objects.example.edu/image.jpg"]
    )
    assert exact.image_urls == ["https://example.com/image.jpg"]
    assert wildcard.image_urls == ["https://campus.objects.example.edu/image.jpg"]


def test_private_image_host_requires_exact_dedicated_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "AI_TRUSTED_PRIVATE_IMAGE_HOSTS", "minio")
    req = ClassifyItemRequest(imageUrls=["http://minio:9000/xunji/image.jpg"])
    assert req.image_urls == ["http://minio:9000/xunji/image.jpg"]
    with pytest.raises(ValidationError):
        ClassifyItemRequest(imageUrls=["http://mysql:3306/private"])
