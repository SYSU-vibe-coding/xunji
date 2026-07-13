"""DashScope client unit tests using httpx.MockTransport (no real network)."""

import base64
import json

import httpx
import pytest
from app.clients.dashscope import DashScopeClient
from app.clients.image_fetcher import MAX_IMAGE_BYTES
from app.core.config import settings
from app.schemas import CalculateMatchRequest, MatchItem
from app.services import match

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


async def _public_resolver(_host: str, _port: int) -> tuple[str, ...]:
    return ("8.8.8.8",)


def _image_response(content: bytes = PNG_BYTES) -> httpx.Response:
    return httpx.Response(200, content=content, headers={"Content-Type": "image/png"})


def _embedding_response(vectors: list[list[float]]) -> httpx.Response:
    body = {
        "output": {
            "embeddings": [{"text_index": idx, "embedding": vec} for idx, vec in enumerate(vectors)]
        },
        "usage": {"total_tokens": 1},
    }
    return httpx.Response(200, content=json.dumps(body))


def _vl_response(text: str) -> httpx.Response:
    body = {
        "output": {"choices": [{"message": {"role": "assistant", "content": [{"text": text}]}}]}
    }
    return httpx.Response(200, content=json.dumps(body))


@pytest.mark.asyncio
async def test_disabled_when_no_api_key() -> None:
    client = DashScopeClient(api_key="")
    try:
        assert client.enabled is False
        assert await client.text_embedding(["hi"]) is None
        assert await client.vl_understand("http://x", "p") is None
    finally:
        await client.aclose()


def test_default_timeout_stays_within_backend_ai_budget() -> None:
    # Backend AI_SERVICE_TIMEOUT default is 15s; ai-service must stay under it.
    assert settings.DASHSCOPE_TIMEOUT <= 15.0


@pytest.mark.asyncio
async def test_text_embedding_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/text-embedding")
        return _embedding_response([[0.1, 0.2], [0.3, 0.4]])

    client = DashScopeClient(api_key="fake", transport=httpx.MockTransport(handler))
    try:
        vecs = await client.text_embedding(["a", "b"])
        assert vecs == [[0.1, 0.2], [0.3, 0.4]]
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_text_embedding_5xx_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content="boom")

    client = DashScopeClient(api_key="fake", transport=httpx.MockTransport(handler))
    try:
        assert await client.text_embedding(["x"]) is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_text_embedding_count_mismatch_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _embedding_response([[0.1]])  # only 1 vector for 2 inputs

    client = DashScopeClient(api_key="fake", transport=httpx.MockTransport(handler))
    try:
        assert await client.text_embedding(["a", "b"]) is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_claim_answer_embeddings_allow_paraphrase_and_cap_contradiction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "LLM_MODEL", "")
    monkeypatch.setattr(settings, "TEXT_EMBEDDING_MODEL", "test-embedding")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/embeddings"
        body = {
            "data": [
                {"index": 0, "embedding": [1.0, 0.0]},
                {"index": 1, "embedding": [0.95, 0.05]},
                {"index": 2, "embedding": [1.0, 0.0]},
                {"index": 3, "embedding": [1.0, 0.0]},
            ]
        }
        return httpx.Response(200, content=json.dumps(body))

    client = DashScopeClient(
        api_key="fake",
        base_url="https://example.com/v1",
        transport=httpx.MockTransport(handler),
    )
    checks = [
        {
            "question": "伞柄上有什么特征",
            "referenceAnswers": ["蓝色星星贴纸"],
            "userAnswer": "把手贴着一颗蓝色五角星",
        },
        {
            "question": "伞柄上有什么特征",
            "referenceAnswers": ["蓝色星星贴纸"],
            "userAnswer": "没有任何贴纸",
        },
    ]
    try:
        scores = await client.claim_answer_scores(checks)
        assert scores is not None
        assert scores[0] > 90
        assert scores[1] == 20
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_vl_understand_success() -> None:
    def provider_handler(request: httpx.Request) -> httpx.Response:
        return _vl_response("CERT")

    client = DashScopeClient(
        api_key="fake",
        transport=httpx.MockTransport(provider_handler),
        image_transport=httpx.MockTransport(lambda _request: _image_response()),
        image_resolver=_public_resolver,
    )
    try:
        reply = await client.vl_understand("https://example.com/img", "classify please")
        assert reply == "CERT"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_vl_understand_string_content() -> None:
    def provider_handler(request: httpx.Request) -> httpx.Response:
        body = {"output": {"choices": [{"message": {"content": "ELECTRONIC"}}]}}
        return httpx.Response(200, content=json.dumps(body))

    client = DashScopeClient(
        api_key="fake",
        transport=httpx.MockTransport(provider_handler),
        image_transport=httpx.MockTransport(lambda _request: _image_response()),
        image_resolver=_public_resolver,
    )
    try:
        assert await client.vl_understand("https://example.com/img", "?") == "ELECTRONIC"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_vl_understand_timeout_returns_none() -> None:
    def provider_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("simulated", request=request)

    client = DashScopeClient(
        api_key="fake",
        transport=httpx.MockTransport(provider_handler),
        image_transport=httpx.MockTransport(lambda _request: _image_response()),
        image_resolver=_public_resolver,
    )
    try:
        assert await client.vl_understand("https://example.com/img", "?") is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_vl_rejects_untrusted_url_before_provider_call() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return _vl_response("CERT")

    client = DashScopeClient(api_key="fake", transport=httpx.MockTransport(handler))
    try:
        assert await client.vl_understand("http://127.0.0.1/private", "?") is None
        assert called is False
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_private_image_is_downloaded_and_provider_receives_data_uri(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AI_TRUSTED_PRIVATE_IMAGE_HOSTS", "minio")
    private_url = "http://minio:9000/xunji/photo.png?X-Amz-Signature=secret"

    def image_handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == private_url
        assert "authorization" not in request.headers
        return _image_response()

    def provider_handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        image_source = payload["input"]["messages"][0]["content"][0]["image"]
        assert image_source.startswith("data:image/png;base64,")
        assert "minio" not in request.content.decode()
        assert "X-Amz-Signature" not in request.content.decode()
        return _vl_response("CERT")

    client = DashScopeClient(
        api_key="fake",
        transport=httpx.MockTransport(provider_handler),
        image_transport=httpx.MockTransport(image_handler),
    )
    try:
        assert await client.vl_understand(private_url, "classify") == "CERT"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_vl_rejects_image_over_ten_megabytes_before_provider_call() -> None:
    provider_called = False

    def image_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "Content-Type": "image/png",
                "Content-Length": str(MAX_IMAGE_BYTES + 1),
            },
        )

    def provider_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal provider_called
        provider_called = True
        return _vl_response("CERT")

    client = DashScopeClient(
        api_key="fake",
        transport=httpx.MockTransport(provider_handler),
        image_transport=httpx.MockTransport(image_handler),
        image_resolver=_public_resolver,
    )
    try:
        assert await client.vl_understand("https://example.com/large.png", "?") is None
        assert provider_called is False
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_vl_revalidates_redirect_and_rejects_private_ssrf() -> None:
    fetched_urls: list[str] = []
    provider_called = False

    def image_handler(request: httpx.Request) -> httpx.Response:
        fetched_urls.append(str(request.url))
        return httpx.Response(302, headers={"Location": "http://169.254.169.254/latest"})

    def provider_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal provider_called
        provider_called = True
        return _vl_response("CERT")

    client = DashScopeClient(
        api_key="fake",
        transport=httpx.MockTransport(provider_handler),
        image_transport=httpx.MockTransport(image_handler),
        image_resolver=_public_resolver,
    )
    try:
        assert await client.vl_understand("https://example.com/image.png", "?") is None
        assert fetched_urls == ["https://example.com/image.png"]
        assert provider_called is False
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_match_llm_prompt_contains_only_name_and_description(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "LLM_MODEL", "text-model")
    captured_payloads: list[dict[str, object]] = []

    def provider_handler(request: httpx.Request) -> httpx.Response:
        captured_payloads.append(json.loads(request.content))
        return httpx.Response(200, content=json.dumps({"output": {"text": "82"}}))

    client = DashScopeClient(api_key="fake", transport=httpx.MockTransport(provider_handler))
    req = CalculateMatchRequest(
        lostItem=MatchItem(
            name="lost-name-marker",
            description="lost-description-marker",
            location="lost-location-marker",
            time="2026-07-11T09:31:27+00:00",
        ),
        foundItem=MatchItem(
            name="found-name-marker",
            description="found-description-marker",
            location="found-location-marker",
            time="2026-07-11T10:42:38+00:00",
        ),
    )
    try:
        response = await match.calculate_match(req, client)
    finally:
        await client.aclose()

    prompt_payload = json.dumps(captured_payloads, ensure_ascii=False)
    assert response.text_score == 82.0
    assert "lost-name-marker lost-description-marker" in prompt_payload
    assert "found-name-marker found-description-marker" in prompt_payload
    assert "lost-location-marker" not in prompt_payload
    assert "found-location-marker" not in prompt_payload
    assert "09:31:27" not in prompt_payload
    assert "10:42:38" not in prompt_payload
