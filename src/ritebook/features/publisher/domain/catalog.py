"""Domain model for discovered skill catalogs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, ClassVar, Self

from ritebook.shared_kernel import (
    MAX_SCHEMA_V1_SKILL_ENTRIES,
    format_canonical_utc_timestamp,
    normalize_portable_description,
    require_index_name,
    require_kebab_case_identifier,
    validate_portable_relative_posix_path,
)
from ritebook.shared_kernel.catalog_paths import validate_catalog_paths

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True, order=True)
class SkillEntry:
    """A discovered skill package entry.

    Paths are POSIX-style strings relative to the explicit skills root. Adapters
    are responsible for filesystem traversal and path normalization before
    constructing entries.
    """

    path: str
    name: str
    skill_file: str
    description: str

    def __post_init__(self) -> None:
        """Validate entry invariants after dataclass initialization."""
        _require_relative_posix_path(self.path, field_name="path")
        _require_relative_posix_path(self.skill_file, field_name="skill_file")
        require_kebab_case_identifier(self.name, field_name="Skill entry name")
        if self.name != PurePosixPath(self.path).name:
            msg = "Skill entry name must match the final path segment."
            raise ValueError(msg)
        _require_canonical_skill_file(skill_file=self.skill_file, path=self.path)
        if not self.description:
            msg = "Skill entry description must not be empty."
            raise ValueError(msg)
        normalized_description = normalize_portable_description(
            self.description,
            field_name="Skill entry description",
        )
        if normalized_description != self.description:
            msg = "Skill entry description must be normalized without edge whitespace."
            raise ValueError(msg)


@dataclass(frozen=True)
class SkillCatalog:
    """A deterministic catalog of discovered skills."""

    SCHEMA_VERSION: ClassVar[int] = 1

    index_name: str
    generated_at: datetime
    skills_root: str
    skills: tuple[SkillEntry, ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls,
        *,
        index_name: str,
        generated_at: datetime,
        skills_root: str,
        skills: list[SkillEntry] | tuple[SkillEntry, ...],
    ) -> Self:
        """Create a catalog with deterministically sorted skill entries."""
        return cls(
            index_name=index_name,
            generated_at=generated_at,
            skills_root=skills_root,
            skills=tuple(sorted(skills, key=lambda skill: skill.path)),
        )

    @property
    def schema_version(self) -> int:
        """Return the publisher index schema version."""
        return self.SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate catalog invariants after dataclass initialization."""
        format_canonical_utc_timestamp(
            self.generated_at,
            field_name="Catalog generation timestamp",
        )
        require_index_name(self.index_name, field_name="Published index name")
        _require_relative_posix_path(
            self.skills_root,
            field_name="skills_root",
            allow_current_directory=True,
        )
        if len(self.skills) > MAX_SCHEMA_V1_SKILL_ENTRIES:
            msg = "Schema-v1 catalogs must contain at most 10,000 skill entries."
            raise ValueError(msg)
        object.__setattr__(
            self,
            "skills",
            tuple(sorted(self.skills, key=lambda skill: skill.path)),
        )
        validate_catalog_paths(skill.path for skill in self.skills)


def _require_relative_posix_path(
    value: str,
    *,
    field_name: str,
    allow_current_directory: bool = False,
) -> None:
    try:
        validate_portable_relative_posix_path(
            value,
            field_name=field_name,
            allow_current_directory=allow_current_directory,
        )
    except ValueError as err:
        msg = f"{field_name} must be a safe relative POSIX path."
        raise ValueError(msg) from err


def _require_canonical_skill_file(*, skill_file: str, path: str) -> None:
    if skill_file != f"{path}/SKILL.md":
        msg = "Skill entry skill_file must be exactly path/SKILL.md."
        raise ValueError(msg)
