"""Domain model for discovered skill catalogs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, ClassVar, Self

from ritebook.shared_kernel import (
    require_index_name,
    require_kebab_case_identifier,
    require_no_terminal_control_characters,
)

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
        _require_skill_file_inside_path(skill_file=self.skill_file, path=self.path)
        require_kebab_case_identifier(self.name, field_name="Skill entry name")
        if not self.description:
            msg = "Skill entry description must not be empty."
            raise ValueError(msg)
        require_no_terminal_control_characters(
            self.description,
            field_name="Skill entry description",
        )


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
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            msg = "Catalog generation timestamp must be timezone-aware."
            raise ValueError(msg)
        require_index_name(self.index_name, field_name="Published index name")
        _require_relative_posix_path(self.skills_root, field_name="skills_root")
        object.__setattr__(
            self,
            "skills",
            tuple(sorted(self.skills, key=lambda skill: skill.path)),
        )


def _require_relative_posix_path(value: str, *, field_name: str) -> None:
    if not value:
        msg = f"{field_name} must not be empty."
        raise ValueError(msg)
    path = PurePosixPath(value)
    if path.is_absolute() or "\\" in value or ".." in path.parts:
        msg = f"{field_name} must be a safe relative POSIX path."
        raise ValueError(msg)
    require_no_terminal_control_characters(value, field_name=field_name)


def _require_skill_file_inside_path(*, skill_file: str, path: str) -> None:
    try:
        PurePosixPath(skill_file).relative_to(PurePosixPath(path))
    except ValueError as err:
        msg = "Skill entry skill_file must be inside path."
        raise ValueError(msg) from err
