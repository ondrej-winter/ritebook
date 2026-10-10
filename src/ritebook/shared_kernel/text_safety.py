"""Pure validation and escaping for terminal-safe text."""

from __future__ import annotations

C0_CONTROL_MAX = 0x1F
DELETE_CONTROL = 0x7F
C1_CONTROL_MAX = 0x9F
BYTE_MAX = 0xFF
HIGH_SURROGATE_MIN = 0xD800
LOW_SURROGATE_MAX = 0xDFFF
MAX_PORTABLE_DESCRIPTION_LENGTH = 1024


def contains_terminal_control_characters(value: str) -> bool:
    """Return whether text contains C0, DEL, or C1 control characters."""
    return any(_is_terminal_control(character) for character in value)


def require_no_terminal_control_characters(value: str, *, field_name: str) -> None:
    """Raise when text contains a terminal control character."""
    if contains_terminal_control_characters(value):
        msg = f"{field_name} must not contain terminal control characters."
        raise ValueError(msg)


def require_portable_text(value: str, *, field_name: str) -> None:
    """Reject controls and surrogate code points from portable catalog text."""
    if any(_is_non_portable_character(character) for character in value):
        msg = f"{field_name} must contain portable Unicode scalar text."
        raise ValueError(msg)


def contains_unicode_surrogate_code_points(value: str) -> bool:
    """Return whether text contains a Unicode surrogate code point."""
    return any(_is_unicode_surrogate(character) for character in value)


def normalize_portable_description(value: str, *, field_name: str) -> str:
    """Trim and validate one portable schema-v1 skill description."""
    normalized = value.strip()
    if not normalized:
        msg = f"{field_name} must not be blank."
        raise ValueError(msg)
    if len(normalized) > MAX_PORTABLE_DESCRIPTION_LENGTH:
        msg = f"{field_name} must be at most {MAX_PORTABLE_DESCRIPTION_LENGTH} characters."
        raise ValueError(msg)
    require_portable_text(normalized, field_name=field_name)
    return normalized


def escape_terminal_control_characters(value: str) -> str:
    """Render terminal controls as deterministic visible ASCII escapes."""
    return "".join(_escaped_character(character) for character in value)


def _is_terminal_control(character: str) -> bool:
    code_point = ord(character)
    return code_point <= C0_CONTROL_MAX or DELETE_CONTROL <= code_point <= C1_CONTROL_MAX


def _is_non_portable_character(character: str) -> bool:
    return _is_terminal_control(character) or _is_unicode_surrogate(character)


def _is_unicode_surrogate(character: str) -> bool:
    code_point = ord(character)
    return HIGH_SURROGATE_MIN <= code_point <= LOW_SURROGATE_MAX


def _escaped_character(character: str) -> str:
    if not _is_terminal_control(character):
        return character
    named_escape = {
        "\t": r"\t",
        "\n": r"\n",
        "\r": r"\r",
    }.get(character)
    if named_escape is not None:
        return named_escape
    code_point = ord(character)
    if code_point <= BYTE_MAX:
        return rf"\x{code_point:02x}"
    return rf"\u{code_point:04x}"
