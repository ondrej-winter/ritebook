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
            index_name="company-skills",
            skills_root=str(checkout / "skills"),
            published_skills_root="skills",
        ),
    ]
    assert publisher.working_directories == [checkout]
    assert Path.cwd() == original_directory


def test_index_regeneration_adapter_preserves_publisher_name_not_local_alias(
    tmp_path: Path,
) -> None:
    publisher = FakePublisher()
    workspace = contribution_workspace(tmp_path)

    PublisherIndexRegeneratorAdapter(publisher=publisher).regenerate_index(
        contribution_entry(),
        workspace,
    )

    assert publisher.commands[0].index_name == "company-skills"


def test_index_regeneration_adapter_uses_provenance_root_not_existing_index_root(
    tmp_path: Path,
) -> None:
    publisher = FakePublisher()
    workspace = contribution_workspace(tmp_path, existing_skills_root="other-skills")

    PublisherIndexRegeneratorAdapter(publisher=publisher).regenerate_index(
        contribution_entry(),
        workspace,
    )

    assert publisher.commands[0].published_skills_root == "skills"


def test_index_regeneration_adapter_derives_root_from_nested_selector(
    tmp_path: Path,
) -> None:
    publisher = FakePublisher()

    PublisherIndexRegeneratorAdapter(publisher=publisher).regenerate_index(
        contribution_entry(
            requirement="platform-skills/quality/code-review",
            skill_path="catalog/skills/quality/code-review",
        ),
        contribution_workspace(tmp_path),
    )

    assert publisher.commands == [
        PublishIndexCommand(
            index_name="company-skills",
            skills_root=str(Path(contribution_workspace(tmp_path).checkout_path) / "catalog/skills"),
            published_skills_root="catalog/skills",
        ),
    ]


def test_index_regeneration_adapter_rejects_inconsistent_provenance(
    tmp_path: Path,
) -> None:
    publisher = FakePublisher()

    with pytest.raises(
        ContributionIndexRegenerationError,
        match=("contribution provenance does not identify a catalog root; contribution commit was not created"),
    ):
        PublisherIndexRegeneratorAdapter(publisher=publisher).regenerate_index(
            contribution_entry(skill_path="skills/security-review"),
            contribution_workspace(tmp_path),
        )

    assert publisher.commands == []


def test_index_regeneration_adapter_rejects_missing_existing_index(
    tmp_path: Path,
) -> None:
    publisher = FakePublisher()
    workspace = contribution_workspace(tmp_path)
    (Path(workspace.checkout_path) / "ritebook-index.json").unlink()

    with pytest.raises(
        ContributionIndexRegenerationError,
        match=("existing index metadata could not be read safely; contribution commit was not created"),
    ):
        PublisherIndexRegeneratorAdapter(publisher=publisher).regenerate_index(
            contribution_entry(),
            workspace,
        )

    assert publisher.commands == []


def test_index_regeneration_adapter_rejects_symlinked_existing_index(
    tmp_path: Path,
) -> None:
    publisher = FakePublisher()
    workspace = contribution_workspace(tmp_path)
    checkout = Path(workspace.checkout_path)
    index_path = checkout / "ritebook-index.json"
    external_index = tmp_path / "external-index.json"
    external_content = _index_content()
    external_index.write_bytes(external_content)
    index_path.unlink()
    index_path.symlink_to(external_index)

    with pytest.raises(
        ContributionIndexRegenerationError,
        match=("existing index metadata could not be read safely; contribution commit was not created"),
    ):
        PublisherIndexRegeneratorAdapter(publisher=publisher).regenerate_index(
            contribution_entry(),
            workspace,
        )

    assert publisher.commands == []
    assert external_index.read_bytes() == external_content


def test_index_regeneration_adapter_rejects_non_strict_existing_index(
    tmp_path: Path,
) -> None:
    publisher = FakePublisher()
    workspace = contribution_workspace(tmp_path)
    (Path(workspace.checkout_path) / "ritebook-index.json").write_bytes(
        b'{"schema_version":1,"schema_version":1}',
    )

    with pytest.raises(
        ContributionIndexRegenerationError,
        match=("existing index metadata could not be read safely; contribution commit was not created"),
    ):
        PublisherIndexRegeneratorAdapter(publisher=publisher).regenerate_index(
            contribution_entry(),
            workspace,
        )

    assert publisher.commands == []


def test_index_regeneration_adapter_rejects_symlinked_checkout_ancestor(
    tmp_path: Path,
) -> None:
    publisher = FakePublisher()
    real_root = tmp_path / "real-contributions"
    real_checkout = real_root / "platform-skills-code-review"
    real_checkout.mkdir(parents=True)
    linked_root = tmp_path / "linked-contributions"
    linked_root.symlink_to(real_root, target_is_directory=True)
    workspace = ContributionWorkspace(
        checkout_path=str(linked_root / real_checkout.name),
        source_skill_path="skills/code-review",
        current_base_revision="def456",
        locked_revision="abc123",
        has_usable_origin=True,
    )

    with pytest.raises(
        ContributionIndexRegenerationError,
        match=("contribution checkout could not be used safely; contribution commit was not created"),
    ):
        PublisherIndexRegeneratorAdapter(publisher=publisher).regenerate_index(
            contribution_entry(),
            workspace,
        )

    assert publisher.commands == []


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
        match=("skill validation failed during index regeneration; contribution commit was not created"),
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
        match=("index regeneration could not be completed; contribution commit was not created"),
    ) as exc_info:
        PublisherIndexRegeneratorAdapter(publisher=publisher).regenerate_index(
            contribution_entry(),
            contribution_workspace(tmp_path),
        )

    assert "private index output details" not in str(exc_info.value)


def contribution_entry(
    *,
    requirement: str = "platform-skills/code-review",
    skill_path: str = "skills/code-review",
) -> ContributionLockfileEntry:
    return ContributionLockfileEntry(
        requirement=requirement,
        index_name="platform-skills",
        skill_name="code-review",
        target=".agents/skills/code-review",
        source="git@example.com:example/skills.git",
        source_type="git_url",
        source_revision="a" * 40,
        source_branch="refs/heads/main",
        index_digest=f"sha256:{'b' * 64}",
        skill_path=skill_path,
        skill_file=f"{skill_path}/SKILL.md",
        index_schema_version=1,
        installed_tree_digest=f"sha256:{'c' * 64}",
    )


def contribution_workspace(
    tmp_path: Path,
    *,
    existing_skills_root: str = "skills",
) -> ContributionWorkspace:
    checkout = tmp_path / "contributions" / "platform-skills-code-review"
    checkout.mkdir(parents=True, exist_ok=True)
    (checkout / "ritebook-index.json").write_bytes(
        _index_content(skills_root=existing_skills_root),
    )
    return ContributionWorkspace(
        checkout_path=str(checkout),
        source_skill_path="skills/code-review",
        current_base_revision="def456",
        locked_revision="abc123",
        has_usable_origin=True,
    )


def _index_content(*, skills_root: str = "skills") -> bytes:
    return json.dumps(
        {
            "schema_version": 1,
            "index": {"name": "company-skills"},
            "generated_at": "2026-07-08T18:00:00Z",
            "skills_root": skills_root,
            "skills": [
                {
                    "name": "code-review",
                    "path": "code-review",
                    "skill_file": "code-review/SKILL.md",
                    "description": "Helps review code.",
                },
            ],
        },
    ).encode()
