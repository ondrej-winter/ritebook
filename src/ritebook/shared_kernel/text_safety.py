"""Pure validation and escaping for terminal-safe text."""

from __future__ import annotations

C0_CONTROL_MAX = 0x1F
DELETE_CONTROL = 0x7F
C1_CONTROL_MAX = 0x9F
BYTE_MAX = 0xFF


def contains_terminal_control_characters(value: str) -> bool:
    """Return whether text contains C0, DEL, or C1 control characters."""
    return any(_is_terminal_control(character) for character in value)


def require_no_terminal_control_characters(value: str, *, field_name: str) -> None:
    """Raise when text contains a terminal control character."""
    if contains_terminal_control_characters(value):
        msg = f"{field_name} must not contain terminal control characters."
        raise ValueError(msg)


def escape_terminal_control_characters(value: str) -> str:
    """Render terminal controls as deterministic visible ASCII escapes."""
    return "".join(_escaped_character(character) for character in value)


def _is_terminal_control(character: str) -> bool:
    code_point = ord(character)
    return (
        code_point <= C0_CONTROL_MAX or DELETE_CONTROL <= code_point <= C1_CONTROL_MAX
    )


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
