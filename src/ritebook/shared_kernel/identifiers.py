"""Identifier validation shared by feature slices."""

from __future__ import annotations

import re

KEBAB_CASE_IDENTIFIER_REGEX = r"(?=.{1,64}$)[a-z0-9]+(?:-[a-z0-9]+)*"
INDEX_NAME_SEGMENT_REGEX = r"(?=.{1,64}(?:/|$))[a-z0-9]+(?:-[a-z0-9]+)*"
KEBAB_CASE_IDENTIFIER_PATTERN = re.compile(
    rf"^{KEBAB_CASE_IDENTIFIER_REGEX}$",
)
INDEX_NAME_PATTERN = re.compile(
    rf"^(?=.{{1,129}}$){INDEX_NAME_SEGMENT_REGEX}"
    rf"(?:/{INDEX_NAME_SEGMENT_REGEX})?$",
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


def is_index_name(value: str) -> bool:
    """Return whether a value is a valid Ritebook index name."""
    return bool(INDEX_NAME_PATTERN.fullmatch(value))


def require_index_name(value: str, *, field_name: str) -> None:
    """Raise when a value is not a valid Ritebook index name."""
    if is_index_name(value):
        return
    msg = (
        f"{field_name} must be one or two slash-separated lowercase ASCII "
        "kebab-case segments, such as 'company-skills' or "
        "'owner/repository-name'. Each segment must be 1-64 lowercase ASCII "
        "letters, digits, or hyphens; segments must not start or end with a "
        "hyphen or contain consecutive hyphens."
    )
    raise ValueError(msg)
