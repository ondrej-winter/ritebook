"""Strict JSON grammar validation for untrusted catalog bytes."""

from __future__ import annotations

import json
from enum import StrEnum
from typing import cast

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]

UTF8_BYTE_ORDER_MARK = b"\xef\xbb\xbf"
MAX_STRICT_JSON_INPUT_BYTES = 16 * 1024 * 1024
MAX_STRICT_JSON_NESTING_DEPTH = 32


class StrictJsonValidationReason(StrEnum):
    """Stable reasons for strict JSON rejection."""

    EMPTY_INPUT = "empty-input"
    INPUT_TOO_LARGE = "input-too-large"
    BYTE_ORDER_MARK = "byte-order-mark"
    INVALID_UTF8 = "invalid-utf8"
    NESTING_TOO_DEEP = "nesting-too-deep"
    INVALID_JSON = "invalid-json"
    NON_STANDARD_CONSTANT = "non-standard-constant"
    DUPLICATE_MEMBER = "duplicate-member"


class StrictJsonError(ValueError):
    """Report a strict JSON grammar failure without exposing source content."""

    def __init__(self, *, reason: StrictJsonValidationReason) -> None:
        """Initialize a failure with a stable machine-readable reason."""
        self.reason = reason
        super().__init__(_error_message(reason))


class _NonStandardConstantError(ValueError):
    """Internal signal raised by the standard-library JSON decoder."""


class _DuplicateMemberError(ValueError):
    """Internal signal raised by the standard-library JSON decoder."""


def parse_strict_json_bytes(content: bytes) -> JsonValue:
    """Decode JSON bytes after strict grammar and resource preflight."""
    if not content:
        raise StrictJsonError(reason=StrictJsonValidationReason.EMPTY_INPUT)
    if len(content) > MAX_STRICT_JSON_INPUT_BYTES:
        raise StrictJsonError(reason=StrictJsonValidationReason.INPUT_TOO_LARGE)
    if content.startswith(UTF8_BYTE_ORDER_MARK):
        raise StrictJsonError(reason=StrictJsonValidationReason.BYTE_ORDER_MARK)
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as err:
        raise StrictJsonError(
            reason=StrictJsonValidationReason.INVALID_UTF8,
        ) from err
    _require_bounded_nesting(text)
    try:
        value: object = json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_members,
            parse_constant=_reject_non_standard_constant,
        )
    except _NonStandardConstantError as err:
        raise StrictJsonError(
            reason=StrictJsonValidationReason.NON_STANDARD_CONSTANT,
        ) from err
    except _DuplicateMemberError as err:
        raise StrictJsonError(
            reason=StrictJsonValidationReason.DUPLICATE_MEMBER,
        ) from err
    except json.JSONDecodeError as err:
        raise StrictJsonError(reason=StrictJsonValidationReason.INVALID_JSON) from err
    return cast("JsonValue", value)


def _reject_non_standard_constant(_value: str) -> JsonValue:
    raise _NonStandardConstantError


def _object_without_duplicate_members(
    pairs: list[tuple[str, JsonValue]],
) -> dict[str, JsonValue]:
    value: dict[str, JsonValue] = {}
    for name, member in pairs:
        if name in value:
            raise _DuplicateMemberError
        value[name] = member
    return value


def _require_bounded_nesting(text: str) -> None:
    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_STRICT_JSON_NESTING_DEPTH:
                raise StrictJsonError(
                    reason=StrictJsonValidationReason.NESTING_TOO_DEEP,
                )
        elif character in "]}":
            depth -= 1


def _error_message(reason: StrictJsonValidationReason) -> str:
    return {
        StrictJsonValidationReason.EMPTY_INPUT: "JSON input must not be empty.",
        StrictJsonValidationReason.INPUT_TOO_LARGE: (
            "JSON input exceeds the 16 MiB size limit."
        ),
        StrictJsonValidationReason.BYTE_ORDER_MARK: (
            "JSON input must not start with a UTF-8 byte-order mark."
        ),
        StrictJsonValidationReason.INVALID_UTF8: "JSON input must be valid UTF-8.",
        StrictJsonValidationReason.NESTING_TOO_DEEP: (
            "JSON input exceeds the maximum nesting depth of 32."
        ),
        StrictJsonValidationReason.INVALID_JSON: "JSON input is malformed.",
        StrictJsonValidationReason.NON_STANDARD_CONSTANT: (
            "JSON input must not contain non-standard numeric constants."
        ),
        StrictJsonValidationReason.DUPLICATE_MEMBER: (
            "JSON objects must not contain duplicate member names."
        ),
    }[reason]
