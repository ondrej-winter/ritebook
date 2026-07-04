"""DTOs for the publish-index use case."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PublishIndexCommand:
    """Command for generating a publisher skill index."""

    skills_root: str
    output_path: str

    def __post_init__(self) -> None:
        """Validate command shape after dataclass initialization."""
        if not self.skills_root:
            msg = "Publish index skills root must not be empty."
            raise ValueError(msg)
        if not self.output_path:
            msg = "Publish index output path must not be empty."
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
