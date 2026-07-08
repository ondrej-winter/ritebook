"""Shared pure domain concepts used across Ritebook feature slices."""

from ritebook.shared_kernel.identifiers import (
    KEBAB_CASE_IDENTIFIER_PATTERN,
    is_kebab_case_identifier,
    require_kebab_case_identifier,
)

__all__ = [
    "KEBAB_CASE_IDENTIFIER_PATTERN",
    "is_kebab_case_identifier",
    "require_kebab_case_identifier",
]
