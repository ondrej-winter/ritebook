"""Shared pure domain concepts used across Ritebook feature slices."""

from ritebook.shared_kernel.identifiers import (
    INDEX_NAME_PATTERN,
    KEBAB_CASE_IDENTIFIER_PATTERN,
    KEBAB_CASE_IDENTIFIER_REGEX,
    is_index_name,
    is_kebab_case_identifier,
    require_index_name,
    require_kebab_case_identifier,
)

__all__ = [
    "INDEX_NAME_PATTERN",
    "KEBAB_CASE_IDENTIFIER_PATTERN",
    "KEBAB_CASE_IDENTIFIER_REGEX",
    "is_index_name",
    "is_kebab_case_identifier",
    "require_index_name",
    "require_kebab_case_identifier",
]
