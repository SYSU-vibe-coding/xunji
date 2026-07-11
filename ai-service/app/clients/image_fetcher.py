from __future__ import annotations

import asyncio
import base64
import ipaddress
import socket
import warnings
from collections.abc import Awaitable, Callable, Collection
from io import BytesIO
from urllib.parse import urljoin, urlsplit

import httpx
from PIL import Image

from app.core.config import settings
from app.core.url_security import validate_image_url

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_REDIRECTS = 3
DOWNLOAD_TIMEOUT_SECONDS = 5.0

_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_FORMAT_MIME_TYPES = {
    "GIF": "image/gif",
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
_CONTENT_TYPE_ALIASES = {"image/jpg": "image/jpeg"}

ImageHostResolver = Callable[[str, int], Awaitable[Collection[str]]]


class ImageDownloadError(Exception):
    """An image could not be fetched or safely decoded."""


class ImageFetcher:
    """Download allowlisted images without exposing their URLs to model providers."""

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        resolver: ImageHostResolver | None = None,
    ) -> None:
        self._resolver = resolver or _resolve_host
        self._client = httpx.AsyncClient(
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
            headers={"Accept": ", ".join(sorted(_FORMAT_MIME_TYPES.values()))},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def fetch_data_uri(self, image_url: str) -> str:
        try:
            async with asyncio.timeout(DOWNLOAD_TIMEOUT_SECONDS):
                content, content_type = await self._download(image_url)
                return _decode_data_uri(content, content_type)
        except ImageDownloadError:
            raise
        except (TimeoutError, httpx.HTTPError, OSError, ValueError) as exc:
            raise ImageDownloadError("image download failed") from exc

    async def _download(self, image_url: str) -> tuple[bytes, str]:
        current_url = image_url
        for redirect_count in range(MAX_REDIRECTS + 1):
            await self._validate_target(current_url)
            async with self._client.stream("GET", current_url) as response:
                if response.status_code in _REDIRECT_STATUSES:
                    location = response.headers.get("location")
                    if not location or redirect_count == MAX_REDIRECTS:
                        raise ImageDownloadError("invalid or excessive image redirect")
                    current_url = urljoin(str(response.url), location)
                    continue

                response.raise_for_status()
                content_type = _validated_content_type(response)
                content_length = response.headers.get("content-length")
                if content_length is not None:
                    try:
                        declared_size = int(content_length)
                    except ValueError as exc:
                        raise ImageDownloadError("invalid image content length") from exc
                    if declared_size < 0 or declared_size > MAX_IMAGE_BYTES:
                        raise ImageDownloadError("image exceeds maximum size")

                chunks: list[bytes] = []
                downloaded = 0
                async for chunk in response.aiter_bytes():
                    downloaded += len(chunk)
                    if downloaded > MAX_IMAGE_BYTES:
                        raise ImageDownloadError("image exceeds maximum size")
                    chunks.append(chunk)
                return b"".join(chunks), content_type

        raise ImageDownloadError("image redirect limit exceeded")

    async def _validate_target(self, image_url: str) -> None:
        try:
            validate_image_url(image_url)
        except ValueError as exc:
            raise ImageDownloadError("image URL is not allowed") from exc

        parsed = urlsplit(image_url)
        host = parsed.hostname
        if host is None:
            raise ImageDownloadError("image URL has no host")
        host = host.lower().rstrip(".")

        # Exact trusted names are the only targets allowed to resolve privately.
        if host in settings.trusted_private_image_hosts:
            return

        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        try:
            addresses = await self._resolver(host, port)
        except OSError as exc:
            raise ImageDownloadError("image host resolution failed") from exc
        if not addresses:
            raise ImageDownloadError("image host did not resolve")

        try:
            resolved = [ipaddress.ip_address(address.split("%", 1)[0]) for address in addresses]
        except ValueError as exc:
            raise ImageDownloadError("image host resolved to an invalid address") from exc
        if any(not address.is_global for address in resolved):
            raise ImageDownloadError("untrusted image host resolved to a private address")


async def _resolve_host(host: str, port: int) -> tuple[str, ...]:
    loop = asyncio.get_running_loop()
    results = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return tuple(dict.fromkeys(result[4][0] for result in results))


def _validated_content_type(response: httpx.Response) -> str:
    content_type: str = response.headers.get("content-type", "").partition(";")[0].strip().lower()
    content_type = _CONTENT_TYPE_ALIASES.get(content_type, content_type)
    if content_type not in _FORMAT_MIME_TYPES.values():
        raise ImageDownloadError("response is not a supported image content type")
    return content_type


def _decode_data_uri(content: bytes, declared_content_type: str) -> str:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                image_format = image.format
                width, height = image.size
                if width * height > MAX_IMAGE_PIXELS:
                    raise ImageDownloadError("decoded image is too large")
                image.load()
    except ImageDownloadError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, OSError) as exc:
        raise ImageDownloadError("response body is not a valid image") from exc

    actual_content_type = _FORMAT_MIME_TYPES.get(image_format or "")
    if actual_content_type is None or actual_content_type != declared_content_type:
        raise ImageDownloadError("image content type does not match decoded format")
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{actual_content_type};base64,{encoded}"
