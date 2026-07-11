from __future__ import annotations

import ipaddress
from collections.abc import Collection
from urllib.parse import urlsplit

from app.core.config import settings


def validate_image_url(value: str, allowed_hosts: Collection[str] | None = None) -> str:
    """Validate an externally fetched image URL against the storage allowlist."""
    if len(value) > 2048:
        msg = "image URL is too long"
        raise ValueError(msg)

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        # Accessing port also rejects malformed and out-of-range ports.
        _ = parsed.port
    except ValueError as exc:
        msg = "invalid image URL"
        raise ValueError(msg) from exc

    if parsed.scheme.lower() not in {"http", "https"}:
        msg = "image URL must use http or https"
        raise ValueError(msg)
    if not hostname or parsed.username is not None or parsed.password is not None:
        msg = "image URL must have a host and no user info"
        raise ValueError(msg)

    host = hostname.lower().rstrip(".")
    trusted_private_hosts = settings.trusted_private_image_hosts
    private_host_allowed = host in trusted_private_hosts
    is_private_target = host == "localhost" or host.endswith((".localhost", ".local", ".internal"))

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        # Single-label names also cover common intranet targets and unusual
        # numeric loopback forms such as http://2130706433/.
        if "." not in host:
            is_private_target = True
    else:
        if not address.is_global:
            is_private_target = True

    if private_host_allowed:
        return value
    if is_private_target:
        msg = "private image host is not in AI_TRUSTED_PRIVATE_IMAGE_HOSTS"
        raise ValueError(msg)

    configured_hosts = allowed_hosts if allowed_hosts is not None else settings.allowed_image_hosts
    normalized_hosts = tuple(item.lower().rstrip(".") for item in configured_hosts)
    if not any(_host_matches(host, allowed) for allowed in normalized_hosts):
        msg = "image host is not in AI_ALLOWED_IMAGE_HOSTS"
        raise ValueError(msg)
    return value


def _host_matches(host: str, allowed: str) -> bool:
    if allowed.startswith("*."):
        suffix = allowed[1:]
        return host.endswith(suffix) and host != allowed[2:]
    return host == allowed
