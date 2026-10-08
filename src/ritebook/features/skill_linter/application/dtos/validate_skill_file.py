"""DTOs for validating one explicit skill file."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ritebook.features.skill_linter.application.dtos.skill_validation import (
        SkillValidationIssue,
    )


@dataclass(frozen=True)
class ValidateSkillFileCommand:
    """Command for validating one explicit ``SKILL.md`` file."""

    skill_file: str
    expected_name: str

    def __post_init__(self) -> None:
        """Validate command shape after initialization."""
        _require_non_empty(self.skill_file, field_name="Skill file")
        _require_non_empty(self.expected_name, field_name="Expected skill name")


@dataclass(frozen=True)
class ValidatedSkillFile:
    """Normalized portable header values from one valid skill file."""

    name: str
    description: str

    def __post_init__(self) -> None:
        """Validate normalized result shape after initialization."""
        _require_non_empty(self.name, field_name="Validated skill name")
        _require_non_empty(
            self.description,
            field_name="Validated skill description",
        )


@dataclass(frozen=True)
class ValidateSkillFileResult:
    """Result returned after validating one explicit skill file."""

    validated_skill: ValidatedSkillFile | None = None
    issues: tuple[SkillValidationIssue, ...] = field(default_factory=tuple)

    @property
    def succeeded(self) -> bool:
        """Return whether the file produced a validated header value."""
        return not self.issues

    def __post_init__(self) -> None:
        """Validate result coherence and deterministic issue ordering."""
        if (self.validated_skill is None) == (not self.issues):
            msg = "Skill-file validation must return either a value or issues."
            raise ValueError(msg)
        object.__setattr__(self, "issues", tuple(sorted(self.issues)))


def _require_non_empty(value: str, *, field_name: str) -> None:
    if not value:
        msg = f"{field_name} must not be empty."
        raise ValueError(msg)
