"""Pure validation and display rules for persisted Git source locators."""

from __future__ import annotations

from urllib.parse import SplitResult, urlsplit, urlunsplit

GIT_URL_SOURCE_TYPE = "git_url"
UNSAFE_GIT_SOURCE_MESSAGE = (
    "Git URL must not include credentials; use SSH configuration or a credential helper"
)


def require_safe_persisted_source(source: str, source_type: str) -> None:
    """Reject secret-bearing source forms before persistence or use."""
    if source_type != GIT_URL_SOURCE_TYPE or "://" not in source:
        return
    parsed = urlsplit(source)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(UNSAFE_GIT_SOURCE_MESSAGE)


def safe_source_display(source: str, source_type: str) -> str:
    """Return a credential-free source identifier for terminal output."""
    if source_type != GIT_URL_SOURCE_TYPE or "://" not in source:
        return source
    parsed = urlsplit(source)
    if parsed.username is None and parsed.password is None:
        return source
    hostname = parsed.hostname or "redacted-source"
    if parsed.port is not None:
        hostname = f"{hostname}:{parsed.port}"
    return urlunsplit(
        SplitResult(
            parsed.scheme,
            hostname,
            parsed.path,
            parsed.query,
            parsed.fragment,
        ),
    )
