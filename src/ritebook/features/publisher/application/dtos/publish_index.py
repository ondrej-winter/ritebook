"""DTOs for the publish-index use case."""

from dataclasses import dataclass, field

from ritebook.shared_kernel import require_kebab_case_identifier

CANONICAL_INDEX_FILENAME = "ritebook-index.json"


@dataclass(frozen=True)
class PublishIndexCommand:
    """Command for generating a publisher skill index."""

    index_name: str
    skills_root: str

    def __post_init__(self) -> None:
        """Validate command shape after dataclass initialization."""
        require_kebab_case_identifier(self.index_name, field_name="Publish index name")
        if not self.skills_root:
            msg = "Publish index skills root must not be empty."
            raise ValueError(msg)


@dataclass(frozen=True)
class PublishIndexResult:
    """Result returned after writing a publisher skill index."""

    discovered_skill_count: int
    output_path: str

    def __post_init__(self) -> None:
        """Validate result shape after dataclass initialization."""
        if self.discovered_skill_count < 0:
            msg = "Discovered skill count must not be negative."
            raise ValueError(msg)
        if not self.output_path:
            msg = "Publish index output path must not be empty."
            raise ValueError(msg)


@dataclass(frozen=True, order=True)
class SkillPrecheckIssue:
    """A path-scoped issue that prevents publisher index generation."""

    skill_file: str
    message: str

    def __post_init__(self) -> None:
        """Validate issue shape after initialization."""
        _require_non_empty_text(self.skill_file, field_name="skill file")
        _require_non_empty_text(self.message, field_name="precheck message")

    def format(self) -> str:
        """Render the deterministic CLI/reporting representation."""
        return f"{self.skill_file}: {self.message}"


@dataclass(frozen=True)
class SkillPrecheckResult:
    """Result returned by publisher prechecks before index generation."""

    checked_skill_count: int
    issues: tuple[SkillPrecheckIssue, ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls,
        *,
        checked_skill_count: int,
        issues: list[SkillPrecheckIssue] | tuple[SkillPrecheckIssue, ...],
    ) -> "SkillPrecheckResult":
        """Create a precheck result with deterministic issue ordering."""
        return cls(
            checked_skill_count=checked_skill_count,
            issues=tuple(sorted(issues)),
        )

    @property
    def succeeded(self) -> bool:
        """Return whether the publisher prechecks passed."""
        return not self.issues

    def __post_init__(self) -> None:
        """Validate result shape after dataclass initialization."""
        if self.checked_skill_count < 0:
            msg = "Checked skill count must not be negative."
            raise ValueError(msg)
        object.__setattr__(self, "issues", tuple(sorted(self.issues)))


class PublishIndexValidationError(ValueError):
    """Raised when skill validation prevents index publication."""

    def __init__(
        self,
        issues: list[SkillPrecheckIssue] | tuple[SkillPrecheckIssue, ...],
    ) -> None:
        """Store deterministic validation issues for adapter rendering."""
        if not issues:
            msg = "Publish index validation error requires at least one issue."
            raise ValueError(msg)
        self.issues = tuple(sorted(issues))
        super().__init__("Skill validation failed.")


def _require_non_empty_text(value: str, *, field_name: str) -> None:
    if not value:
        msg = f"Publisher precheck {field_name} must not be empty."
        raise ValueError(msg)
