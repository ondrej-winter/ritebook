"""Identifier validation shared by feature slices."""

from __future__ import annotations

import re

KEBAB_CASE_IDENTIFIER_PATTERN = re.compile(
    r"^(?=.{1,64}$)[a-z0-9]+(?:-[a-z0-9]+)*$",
)


def is_kebab_case_identifier(value: str) -> bool:
    """Return whether a value is a canonical Ritebook kebab-case identifier."""
    return bool(KEBAB_CASE_IDENTIFIER_PATTERN.fullmatch(value))


def require_kebab_case_identifier(value: str, *, field_name: str) -> None:
    """Raise when a value is not a canonical Ritebook kebab-case identifier."""
    if is_kebab_case_identifier(value):
        return
    msg = (
        f"{field_name} must be 1-64 lowercase ASCII letters, digits, or hyphens; "
        "it must not start or end with a hyphen or contain consecutive hyphens."
    )
    raise ValueError(msg)
