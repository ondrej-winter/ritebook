"""Schema-v1 catalog-relative skill path policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ritebook.shared_kernel.identifiers import is_kebab_case_identifier

if TYPE_CHECKING:
    from collections.abc import Iterable

MAX_CATALOG_PATH_SEGMENTS = 2


class CatalogPathKind(StrEnum):
    """Supported schema-v1 catalog path classifications."""

    ROOT_SKILL = "root-skill"
    COLLECTION_CHILD = "collection-child"


class CatalogPathValidationReason(StrEnum):
    """Stable reasons for schema-v1 catalog path rejection."""

    MALFORMED_PATH = "malformed-path"
    INVALID_DEPTH = "invalid-depth"
    INVALID_SEGMENT = "invalid-segment"
    DUPLICATE_PATH = "duplicate-path"
    MIXED_NODE = "mixed-node"


class CatalogPathValidationError(ValueError):
    """Report a technology-neutral schema-v1 catalog path failure."""

    def __init__(
        self,
        *,
        reason: CatalogPathValidationReason,
        path: str,
        related_path: str | None = None,
    ) -> None:
        """Initialize a failure with a stable reason and offending paths."""
        self.reason = reason
        self.path = path
        self.related_path = related_path
        super().__init__(_error_message(reason, path, related_path))


@dataclass(frozen=True)
class CatalogPath:
    """A validated schema-v1 catalog-relative skill path."""

    value: str
    kind: CatalogPathKind
    collection: str | None
    skill_name: str


def validate_catalog_path(value: str) -> CatalogPath:
    """Validate and classify one literal schema-v1 catalog path."""
    if _is_malformed_literal(value):
        raise CatalogPathValidationError(
            reason=CatalogPathValidationReason.MALFORMED_PATH,
            path=value,
        )

    parts = PurePosixPath(value).parts
    if len(parts) > MAX_CATALOG_PATH_SEGMENTS:
        raise CatalogPathValidationError(
            reason=CatalogPathValidationReason.INVALID_DEPTH,
            path=value,
        )
    if any(not is_kebab_case_identifier(part) for part in parts):
        raise CatalogPathValidationError(
            reason=CatalogPathValidationReason.INVALID_SEGMENT,
            path=value,
        )
    if len(parts) == 1:
        return CatalogPath(
            value=value,
            kind=CatalogPathKind.ROOT_SKILL,
            collection=None,
            skill_name=parts[0],
        )
    return CatalogPath(
        value=value,
        kind=CatalogPathKind.COLLECTION_CHILD,
        collection=parts[0],
        skill_name=parts[1],
    )


def validate_catalog_paths(values: Iterable[str]) -> tuple[CatalogPath, ...]:
    """Validate a complete schema-v1 catalog path set."""
    catalog_paths = tuple(validate_catalog_path(value) for value in values)
    paths_by_value: dict[str, CatalogPath] = {}
    for catalog_path in catalog_paths:
        if catalog_path.value in paths_by_value:
            raise CatalogPathValidationError(
                reason=CatalogPathValidationReason.DUPLICATE_PATH,
                path=catalog_path.value,
            )
        paths_by_value[catalog_path.value] = catalog_path

    root_paths = {
        path.value for path in catalog_paths if path.kind is CatalogPathKind.ROOT_SKILL
    }
    for child_path in sorted(
        (
            path
            for path in catalog_paths
            if path.kind is CatalogPathKind.COLLECTION_CHILD
        ),
        key=lambda path: path.value,
    ):
        if child_path.collection in root_paths:
            raise CatalogPathValidationError(
                reason=CatalogPathValidationReason.MIXED_NODE,
                path=child_path.collection,
                related_path=child_path.value,
            )

    return catalog_paths


def _is_malformed_literal(value: str) -> bool:
    return (
        not value
        or value.startswith("/")
        or value.endswith("/")
        or "//" in value
        or "\\" in value
        or any(part in {".", ".."} for part in value.split("/"))
    )


def _error_message(
    reason: CatalogPathValidationReason,
    path: str,
    related_path: str | None,
) -> str:
    if reason is CatalogPathValidationReason.MALFORMED_PATH:
        return f"Catalog path is not a literal relative POSIX path: {path!r}."
    if reason is CatalogPathValidationReason.INVALID_DEPTH:
        return f"Catalog path must contain one or two segments: {path!r}."
    if reason is CatalogPathValidationReason.INVALID_SEGMENT:
        return f"Catalog path contains a non-canonical identifier segment: {path!r}."
    if reason is CatalogPathValidationReason.DUPLICATE_PATH:
        return f"Catalog contains duplicate skill path: {path!r}."
    return (
        f"Catalog node cannot be both a root skill and a collection: {path!r} "
        f"conflicts with {related_path!r}."
    )
