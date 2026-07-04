"""Domain model for discovered skill catalogs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Self

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
    title: str | None = None

    def __post_init__(self) -> None:
        """Validate entry invariants after dataclass initialization."""
        _require_relative_posix_path(self.path, field_name="path")
        _require_relative_posix_path(self.skill_file, field_name="skill_file")
        if not self.name:
            msg = "Skill entry name must not be empty."
            raise ValueError(msg)
        if self.title == "":
            msg = "Skill entry title must be omitted instead of empty."
            raise ValueError(msg)


@dataclass(frozen=True)
class SkillCatalog:
    """A deterministic catalog of discovered skills."""

    SCHEMA_VERSION: ClassVar[int] = 1

    generated_at: datetime
    skills_root: str
    skills: tuple[SkillEntry, ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls,
        *,
        generated_at: datetime,
        skills_root: str,
        skills: list[SkillEntry] | tuple[SkillEntry, ...],
    ) -> Self:
        """Create a catalog with deterministically sorted skill entries."""
        return cls(
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
        if not self.skills_root:
            msg = "Catalog skills root must not be empty."
            raise ValueError(msg)
        object.__setattr__(
            self,
            "skills",
            tuple(sorted(self.skills, key=lambda skill: skill.path)),
        )


def _require_relative_posix_path(value: str, *, field_name: str) -> None:
    if not value:
        msg = f"Skill entry {field_name} must not be empty."
        raise ValueError(msg)
    if value.startswith("/"):
        msg = f"Skill entry {field_name} must be relative to the skills root."
        raise ValueError(msg)
    if "\\" in value:
        msg = f"Skill entry {field_name} must use POSIX-style separators."
        raise ValueError(msg)
