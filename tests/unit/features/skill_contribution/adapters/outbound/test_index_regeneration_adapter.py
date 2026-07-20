import json
from pathlib import Path

import pytest

from ritebook.features.publisher.application.dtos import (
    PublishIndexCommand,
    PublishIndexResult,
    PublishIndexValidationError,
    SkillPrecheckIssue,
)
from ritebook.features.publisher.application.errors import PublishIndexWriteError
from ritebook.features.skill_contribution.adapters.outbound.index_regeneration import (
    PublisherIndexRegeneratorAdapter,
)
from ritebook.features.skill_contribution.application.dtos import (
    ContributionLockfileEntry,
    ContributionWorkspace,
)
from ritebook.features.skill_contribution.application.errors import (
    ContributionIndexRegenerationError,
    SkillContributionValidationError,
)


class FakePublisher:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.failure = failure
        self.commands: list[PublishIndexCommand] = []
        self.working_directories: list[Path] = []

    def execute(self, command: PublishIndexCommand) -> PublishIndexResult:
        self.commands.append(command)
        self.working_directories.append(Path.cwd())
        if self.failure is not None:
            raise self.failure
        return PublishIndexResult(
            discovered_skill_count=1,
            output_path="ritebook-index.json",
        )


def test_index_regeneration_adapter_preserves_published_skills_root(
    tmp_path: Path,
) -> None:
    publisher = FakePublisher()
    adapter = PublisherIndexRegeneratorAdapter(publisher=publisher)
    workspace = contribution_workspace(tmp_path)
    checkout = Path(workspace.checkout_path)
    original_directory = Path.cwd()

    adapter.regenerate_index(contribution_entry(), workspace)

    assert publisher.commands == [
        PublishIndexCommand(
            index_name="platform-skills",
            skills_root="skills",
        ),
    ]
    assert publisher.working_directories == [checkout]
    assert Path.cwd() == original_directory


def test_index_regeneration_adapter_converts_validation_failure_without_details(
    tmp_path: Path,
) -> None:
    publisher = FakePublisher(
        failure=PublishIndexValidationError(
            [
                SkillPrecheckIssue(
                    skill_file="skills/code-review/SKILL.md",
                    message="secret skill content is invalid",
                ),
            ],
        ),
    )

    with pytest.raises(
        SkillContributionValidationError,
        match=(
            "skill validation failed during index regeneration; "
            "contribution commit was not created"
        ),
    ) as exc_info:
        PublisherIndexRegeneratorAdapter(publisher=publisher).regenerate_index(
            contribution_entry(),
            contribution_workspace(tmp_path),
        )

    assert "secret skill content" not in str(exc_info.value)
    assert "SKILL.md" not in str(exc_info.value)


def test_index_regeneration_adapter_converts_publisher_failure_without_details(
    tmp_path: Path,
) -> None:
    publisher = FakePublisher(
        failure=PublishIndexWriteError("private index output details"),
    )

    with pytest.raises(
        ContributionIndexRegenerationError,
        match=(
            "index regeneration could not be completed; "
            "contribution commit was not created"
        ),
    ) as exc_info:
        PublisherIndexRegeneratorAdapter(publisher=publisher).regenerate_index(
            contribution_entry(),
            contribution_workspace(tmp_path),
        )

    assert "private index output details" not in str(exc_info.value)


def contribution_entry() -> ContributionLockfileEntry:
    return ContributionLockfileEntry(
        requirement="platform-skills/code-review",
        index_name="platform-skills",
        skill_name="code-review",
        target=".agents/skills/code-review",
        source="git@example.com:example/skills.git",
        source_type="git_url",
        source_revision="abc123",
        skill_path="skills/code-review",
        skill_file="skills/code-review/SKILL.md",
        index_schema_version=1,
    )


def contribution_workspace(tmp_path: Path) -> ContributionWorkspace:
    checkout = tmp_path / "contributions" / "platform-skills-code-review"
    checkout.mkdir(parents=True)
    (checkout / "ritebook-index.json").write_text(
        json.dumps({"skills_root": "skills"}),
        encoding="utf-8",
    )
    return ContributionWorkspace(
        checkout_path=str(checkout),
        source_skill_path="skills/code-review",
        current_base_revision="def456",
        locked_revision="abc123",
        has_usable_origin=True,
    )
