"""DTOs for skill header validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParsedSkillHeader:
    """Parsed header data for one discovered skill file.

    The outbound adapter owns Markdown/YAML parsing and supplies plain parsed
    data. ``expected_name`` is the directory-derived skill name that the header
    ``name`` field must match.
    """

    skill_file: str
    expected_name: str
    frontmatter: object

    def __post_init__(self) -> None:
        """Validate parsed header input shape after initialization."""
        _require_non_empty_text(self.skill_file, field_name="skill file")
        _require_non_empty_text(self.expected_name, field_name="expected skill name")


@dataclass(frozen=True, order=True)
class SkillValidationIssue:
    """A path-scoped validation issue for a discovered skill file."""

    skill_file: str
    message: str

    def __post_init__(self) -> None:
        """Validate issue shape after initialization."""
        _require_non_empty_text(self.skill_file, field_name="skill file")
        _require_non_empty_text(self.message, field_name="validation message")

    def format(self) -> str:
        """Render the deterministic CLI/reporting representation."""
        return f"{self.skill_file}: {self.message}"


@dataclass(frozen=True)
class SkillValidationReport:
    """Deterministic result of validating discovered skill headers."""

    validated_skill_count: int
    issues: tuple[SkillValidationIssue, ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls,
        *,
        validated_skill_count: int,
        issues: list[SkillValidationIssue] | tuple[SkillValidationIssue, ...],
    ) -> SkillValidationReport:
        """Create a report with deterministically ordered issues."""
        return cls(
            validated_skill_count=validated_skill_count,
            issues=tuple(sorted(issues)),
        )

    @property
    def succeeded(self) -> bool:
        """Return whether all discovered skill headers passed validation."""
        return not self.issues

    def __post_init__(self) -> None:
        """Validate report shape and normalize issue ordering."""
        if self.validated_skill_count < 0:
            msg = "Validated skill count must not be negative."
            raise ValueError(msg)
        object.__setattr__(self, "issues", tuple(sorted(self.issues)))


FrontmatterMapping = Mapping[str, object]


def _require_non_empty_text(value: str, *, field_name: str) -> None:
    if not value:
        msg = f"Skill validation {field_name} must not be empty."
        raise ValueError(msg)
