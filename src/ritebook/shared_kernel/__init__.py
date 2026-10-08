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
from ritebook.shared_kernel.portable_paths import (
    PortablePathValidationError,
    PortablePathValidationReason,
    validate_portable_relative_posix_path,
)
from ritebook.shared_kernel.schema_v1_catalog import (
    MAX_SCHEMA_V1_SKILL_ENTRIES,
    SchemaV1Catalog,
    SchemaV1CatalogError,
    SchemaV1Skill,
    parse_schema_v1_catalog_bytes,
)
from ritebook.shared_kernel.skill_package import SKILL_FILE_NAME
from ritebook.shared_kernel.strict_json import (
    JsonValue,
    StrictJsonError,
    StrictJsonValidationReason,
    parse_strict_json_bytes,
)
from ritebook.shared_kernel.text_safety import (
    contains_terminal_control_characters,
    contains_unicode_surrogate_code_points,
    escape_terminal_control_characters,
    normalize_portable_description,
    require_no_terminal_control_characters,
    require_portable_text,
)
from ritebook.shared_kernel.timestamps import (
    format_canonical_utc_timestamp,
    parse_canonical_utc_timestamp,
)

__all__ = [
    "GIT_URL_SOURCE_TYPE",
    "INDEX_NAME_PATTERN",
    "KEBAB_CASE_IDENTIFIER_PATTERN",
    "KEBAB_CASE_IDENTIFIER_REGEX",
    "MAX_SCHEMA_V1_SKILL_ENTRIES",
    "SKILL_FILE_NAME",
    "UNSAFE_GIT_SOURCE_MESSAGE",
    "JsonValue",
    "PortablePathValidationError",
    "PortablePathValidationReason",
    "SchemaV1Catalog",
    "SchemaV1CatalogError",
    "SchemaV1Skill",
    "StrictJsonError",
    "StrictJsonValidationReason",
    "contains_terminal_control_characters",
    "contains_unicode_surrogate_code_points",
    "escape_terminal_control_characters",
    "format_canonical_utc_timestamp",
    "is_index_name",
    "is_kebab_case_identifier",
    "normalize_portable_description",
    "parse_canonical_utc_timestamp",
    "parse_schema_v1_catalog_bytes",
    "parse_strict_json_bytes",
    "require_index_name",
    "require_kebab_case_identifier",
    "require_no_terminal_control_characters",
    "require_portable_text",
    "require_safe_persisted_source",
    "safe_source_display",
    "validate_portable_relative_posix_path",
]
