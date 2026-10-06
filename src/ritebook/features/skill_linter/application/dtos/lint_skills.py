"""DTOs for the lint-skills use case."""

from dataclasses import dataclass, field

from ritebook.features.skill_linter.application.dtos.skill_validation import (
    SkillValidationIssue,
)


@dataclass(frozen=True, order=True)
class ValidatedSkill:
    """Immutable snapshot of one successfully validated skill."""

    path: str
    name: str
    skill_file: str
    description: str

    def __post_init__(self) -> None:
        """Validate snapshot shape after dataclass initialization."""
        _require_non_empty_text(self.path, field_name="path")
        _require_non_empty_text(self.name, field_name="name")
        _require_non_empty_text(self.skill_file, field_name="skill file")
        _require_non_empty_text(self.description, field_name="description")


@dataclass(frozen=True)
class LintSkillsCommand:
    """Command for validating discovered skill headers."""

    skills_root: str

    def __post_init__(self) -> None:
        """Validate command shape after dataclass initialization."""
        if not self.skills_root:
            msg = "Lint skills root must not be empty."
            raise ValueError(msg)


@dataclass(frozen=True)
class LintSkillsResult:
    """Result returned after validating discovered skill headers."""

    discovered_skill_count: int
    issues: tuple[SkillValidationIssue, ...] = field(default_factory=tuple)
    validated_skills: tuple[ValidatedSkill, ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls,
        *,
        discovered_skill_count: int,
        issues: list[SkillValidationIssue] | tuple[SkillValidationIssue, ...],
        validated_skills: list[ValidatedSkill] | tuple[ValidatedSkill, ...] = (),
    ) -> "LintSkillsResult":
        """Create a lint result with deterministic collection ordering."""
        return cls(
            discovered_skill_count=discovered_skill_count,
            issues=tuple(sorted(issues)),
            validated_skills=tuple(sorted(validated_skills)),
        )

    @property
    def succeeded(self) -> bool:
        """Return whether every discovered skill header is valid."""
        return not self.issues

    def __post_init__(self) -> None:
        """Validate result shape and normalize deterministic ordering."""
        if self.discovered_skill_count < 0:
            msg = "Discovered skill count must not be negative."
            raise ValueError(msg)
        if self.issues and self.validated_skills:
            msg = "Failed lint results must not expose validated skill snapshots."
            raise ValueError(msg)
        if not self.issues and self.discovered_skill_count != len(
            self.validated_skills
        ):
            msg = "Successful lint result count must match validated skills."
            raise ValueError(msg)
        object.__setattr__(self, "issues", tuple(sorted(self.issues)))
        object.__setattr__(
            self,
            "validated_skills",
            tuple(sorted(self.validated_skills)),
        )


def _require_non_empty_text(value: str, *, field_name: str) -> None:
    if not value:
        msg = f"Validated skill {field_name} must not be empty."
        raise ValueError(msg)
