"""Portable relative POSIX path validation shared by catalog boundaries."""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath

from ritebook.shared_kernel.text_safety import require_portable_text

WINDOWS_FORBIDDEN_CHARACTERS = frozenset('<>:"\\|?*')
WINDOWS_RESERVED_NAMES = frozenset(
    {
        "aux",
        "con",
        "nul",
        "prn",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
    },
)


class PortablePathValidationReason(StrEnum):
    """Stable reasons for rejecting a portable relative POSIX path."""

    MALFORMED_PATH = "malformed-path"
    INVALID_SEGMENT = "invalid-segment"


class PortablePathValidationError(ValueError):
    """Report a portable relative POSIX path validation failure."""

    def __init__(
        self,
        *,
        field_name: str,
        reason: PortablePathValidationReason,
    ) -> None:
        """Initialize a failure without exposing untrusted path contents."""
        self.field_name = field_name
        self.reason = reason
        detail = {
            PortablePathValidationReason.MALFORMED_PATH: ("must be a literal relative POSIX path"),
            PortablePathValidationReason.INVALID_SEGMENT: ("contains a non-portable path segment"),
        }[reason]
        super().__init__(f"{field_name} {detail}.")


def validate_portable_relative_posix_path(
    value: str,
    *,
    field_name: str,
    allow_current_directory: bool = False,
) -> PurePosixPath:
    """Validate a normalized portable relative POSIX path literal."""
    if value == "." and allow_current_directory:
        return PurePosixPath(value)
    if _is_malformed_literal(value):
        raise PortablePathValidationError(
            field_name=field_name,
            reason=PortablePathValidationReason.MALFORMED_PATH,
        )

    path = PurePosixPath(value)
    for segment in value.split("/"):
        if not _is_portable_segment(segment):
            raise PortablePathValidationError(
                field_name=field_name,
                reason=PortablePathValidationReason.INVALID_SEGMENT,
            )
    return path


def _is_malformed_literal(value: str) -> bool:
    return (
        not value
        or value.startswith("/")
        or value.endswith("/")
        or "//" in value
        or "\\" in value
        or any(segment in {".", ".."} for segment in value.split("/"))
    )


def _is_portable_segment(segment: str) -> bool:
    try:
        require_portable_text(segment, field_name="Path segment")
    except ValueError:
        return False
    if segment.endswith((".", " ")):
        return False
    if any(character in WINDOWS_FORBIDDEN_CHARACTERS for character in segment):
        return False
    base_name = segment.split(".", maxsplit=1)[0].casefold()
    return base_name not in WINDOWS_RESERVED_NAMES
