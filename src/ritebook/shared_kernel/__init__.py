"""Shared pure domain concepts used across Ritebook feature slices."""

from ritebook.shared_kernel.git_sources import (
    GIT_URL_SOURCE_TYPE,
    UNSAFE_GIT_SOURCE_MESSAGE,
    require_safe_persisted_source,
    safe_source_display,
)
from ritebook.shared_kernel.identifiers import (
    INDEX_NAME_PATTERN,
    KEBAB_CASE_IDENTIFIER_PATTERN,
    KEBAB_CASE_IDENTIFIER_REGEX,
    is_index_name,
    is_kebab_case_identifier,
    require_index_name,
    require_kebab_case_identifier,
)
from ritebook.shared_kernel.skill_package import SKILL_FILE_NAME
from ritebook.shared_kernel.text_safety import (
    contains_terminal_control_characters,
    escape_terminal_control_characters,
    require_no_terminal_control_characters,
)

__all__ = [
    "GIT_URL_SOURCE_TYPE",
    "INDEX_NAME_PATTERN",
    "KEBAB_CASE_IDENTIFIER_PATTERN",
    "KEBAB_CASE_IDENTIFIER_REGEX",
    "SKILL_FILE_NAME",
    "UNSAFE_GIT_SOURCE_MESSAGE",
    "contains_terminal_control_characters",
    "escape_terminal_control_characters",
    "is_index_name",
    "is_kebab_case_identifier",
    "require_index_name",
    "require_kebab_case_identifier",
    "require_no_terminal_control_characters",
    "require_safe_persisted_source",
    "safe_source_display",
]
