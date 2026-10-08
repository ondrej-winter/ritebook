"""Canonical UTC timestamp parsing and formatting for persisted contracts."""

from __future__ import annotations

import re
from datetime import UTC, datetime

CANONICAL_UTC_TIMESTAMP_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{6})?Z\Z",
)


def format_canonical_utc_timestamp(value: datetime, *, field_name: str) -> str:
    """Format a timezone-aware datetime as canonical schema-v1 UTC text."""
    if value.tzinfo is None or value.utcoffset() is None:
        msg = f"{field_name} must be timezone-aware."
        raise ValueError(msg)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_canonical_utc_timestamp(value: str, *, field_name: str) -> datetime:
    """Parse a real timestamp only when it uses the canonical schema-v1 form."""
    if not CANONICAL_UTC_TIMESTAMP_PATTERN.fullmatch(value):
        raise _timestamp_error(field_name)
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as err:
        raise _timestamp_error(field_name) from err
    if format_canonical_utc_timestamp(parsed, field_name=field_name) != value:
        raise _timestamp_error(field_name)
    return parsed


def _timestamp_error(field_name: str) -> ValueError:
    return ValueError(
        f"{field_name} must be a real canonical UTC timestamp ending in Z.",
    )
