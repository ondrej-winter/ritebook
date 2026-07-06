"""DTOs for the lint-skills use case."""

from dataclasses import dataclass, field

from ritebook.features.linter.application.dtos.skill_validation import (
    SkillValidationIssue,
)


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

    validated_skill_count: int
    issues: tuple[SkillValidationIssue, ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls,
        *,
        validated_skill_count: int,
        issues: list[SkillValidationIssue] | tuple[SkillValidationIssue, ...],
    ) -> "LintSkillsResult":
        """Create a lint result with deterministic issue ordering."""
        return cls(
            validated_skill_count=validated_skill_count,
            issues=tuple(sorted(issues)),
        )

    @property
    def succeeded(self) -> bool:
        """Return whether every discovered skill header is valid."""
        return not self.issues

    def __post_init__(self) -> None:
        """Validate result shape after dataclass initialization."""
        if self.validated_skill_count < 0:
            msg = "Validated skill count must not be negative."
            raise ValueError(msg)
        object.__setattr__(self, "issues", tuple(sorted(self.issues)))
