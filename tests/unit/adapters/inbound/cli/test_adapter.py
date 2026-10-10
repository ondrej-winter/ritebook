from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import TextIO

from ritebook import __version__
from ritebook.adapters.inbound.cli import run as run_cli
from ritebook.features.index_registry.application.dtos import (
    AddIndexCommand,
    AddIndexResult,
    CachedSkillSummary,
    ListedIndexSkills,
    ListIndexesCommand,
    ListIndexesResult,
    ListSkillsCommand,
    ListSkillsResult,
    RegisteredIndexSummary,
    UpdateIndexCommand,
    UpdateIndexResult,
)
from ritebook.features.index_registry.application.errors import (
    DuplicateIndexNameError,
    InvalidPublishedIndexError,
    UnknownIndexNameError,
)
from ritebook.features.publisher.application.dtos import (
    PublishIndexCommand,
    PublishIndexResult,
    PublishIndexValidationError,
    SkillPrecheckIssue,
)
from ritebook.features.publisher.application.errors import PublishIndexDiscoveryError
from ritebook.features.skill_contribution.application.dtos import (
    PreparedContribution,
    PublishSkillChangeCommand,
    PublishSkillChangeResult,
    SkillChangeStatus,
)
from ritebook.features.skill_contribution.application.errors import (
    ContributionLockfileEntryNotFoundError,
)
from ritebook.features.skill_installation.application.dtos import (
    InstallationWorkflow,
    InstallFromRequirementsCommand,
    InstallFromRequirementsResult,
    InstallSkillCommand,
    InstallSkillResult,
    OwnedInstallation,
    ReconciliationIssue,
)
from ritebook.features.skill_installation.application.errors import (
    ExistingInstallTargetError,
    InstallationPersistenceError,
    UnknownInstallIndexError,
)
from ritebook.features.skill_linter.application.dtos import (
    LintSkillsCommand,
    LintSkillsResult,
    SkillValidationIssue,
    ValidatedSkill,
)
from ritebook.features.skill_linter.application.errors import LintSkillsDiscoveryError

ARGPARSE_USAGE_ERROR = 2


def run(
    argv: list[str],
    *,
    linter: FakeLinter | FailingLinter,
    publisher: FakePublisher | FailingPublisher,
    stdout: TextIO,
    stderr: TextIO,
    add_index: FakeAddIndex | FailingAddIndex | None = None,
    list_indexes: FakeListIndexes | FailingListIndexes | None = None,
    list_skills: FakeListSkills | FailingListSkills | None = None,
    update_index: FakeUpdateIndex | FailingUpdateIndex | None = None,
    install_skill: FakeInstallSkill | FailingInstallSkill | None = None,
    install_from_requirements: (FakeInstallFromRequirements | FailingInstallFromRequirements | None) = None,
    publish_skill_change: (FakePublishSkillChange | FailingPublishSkillChange | None) = None,
) -> int:
    """Run the CLI test adapter with default consumer command fakes."""
    return run_cli(
        argv,
        linter=linter,
        publisher=publisher,
        add_index=add_index or FakeAddIndex(),
        list_indexes=list_indexes or FakeListIndexes(),
        list_skills=list_skills or FakeListSkills(),
        update_index=update_index or FakeUpdateIndex(),
        install_skill=install_skill or FakeInstallSkill(),
        install_from_requirements=install_from_requirements or FakeInstallFromRequirements(),
        publish_skill_change=publish_skill_change or FakePublishSkillChange(),
        stdout=stdout,
        stderr=stderr,
    )


class FakePublisher:
    """Test double for the publish-index inbound application port."""

    def __init__(self, result: PublishIndexResult | None = None) -> None:
        """Store the result to return and commands received by the CLI."""
        self.result = result or PublishIndexResult(
            discovered_skill_count=2,
            output_path="ritebook-index.json",
        )
        self.commands: list[PublishIndexCommand] = []

    def execute(self, command: PublishIndexCommand) -> PublishIndexResult:
        """Record the command and return the configured result."""
        self.commands.append(command)
        return self.result


def _validated_skill(name: str) -> ValidatedSkill:
    return ValidatedSkill(
        path=name,
        name=name,
        skill_file=f"{name}/SKILL.md",
        description=f"{name} skill.",
    )


class FakeLinter:
    """Test double for the lint-skills inbound application port."""

    def __init__(self, result: LintSkillsResult | None = None) -> None:
        """Store the result to return and commands received by the CLI."""
        self.result = result or LintSkillsResult.create(
            discovered_skill_count=2,
            issues=[],
            validated_skills=[
                _validated_skill("alpha"),
                _validated_skill("zeta"),
            ],
        )
        self.commands: list[LintSkillsCommand] = []

    def execute(self, command: LintSkillsCommand) -> LintSkillsResult:
        """Record the command and return the configured result."""
        self.commands.append(command)
        return self.result


class FakePublishSkillChange:
    """Test double for the publish-skill-change inbound application port."""

    def __init__(self, result: PublishSkillChangeResult | None = None) -> None:
        """Store the result to return and commands received by the CLI."""
        self.result = result or PublishSkillChangeResult(
            skill_reference="platform-skills/code-review",
            status=SkillChangeStatus.NO_CHANGES,
        )
        self.commands: list[PublishSkillChangeCommand] = []

    def execute(self, command: PublishSkillChangeCommand) -> PublishSkillChangeResult:
        """Record the command and return the configured result."""
        self.commands.append(command)
        return self.result


class FakeAddIndex:
    """Test double for the add-index inbound application port."""

    def __init__(self, result: AddIndexResult | None = None) -> None:
        """Store the result to return and commands received by the CLI."""
        self.result = result or AddIndexResult(name="company-skills", skill_count=2)
        self.commands: list[AddIndexCommand] = []

    def execute(self, command: AddIndexCommand) -> AddIndexResult:
        """Record the command and return the configured result."""
        self.commands.append(command)
        return self.result


class FakeUpdateIndex:
    """Test double for the update-index inbound application port."""

    def __init__(self, result: UpdateIndexResult | None = None) -> None:
        """Store the result to return and commands received by the CLI."""
        self.result = result or UpdateIndexResult(name="company-skills", skill_count=3)
        self.commands: list[UpdateIndexCommand] = []

    def execute(self, command: UpdateIndexCommand) -> UpdateIndexResult:
        """Record the command and return the configured result."""
        self.commands.append(command)
        return self.result


class FakeListIndexes:
    """Test double for the list-indexes inbound application port."""

    def __init__(self, result: ListIndexesResult | None = None) -> None:
        """Store the result to return and commands received by the CLI."""
        self.result = result or ListIndexesResult(
            indexes=(
                RegisteredIndexSummary(
                    name="company-skills",
                    published_name="company-skills",
                    source_type="git_url",
                    source="git@example.com:company/skills.git",
                    skill_count=2,
                    updated_at="2026-07-08T18:00:00Z",
                ),
            ),
        )
        self.commands: list[ListIndexesCommand] = []

    def execute(self, command: ListIndexesCommand) -> ListIndexesResult:
        """Record the command and return the configured result."""
        self.commands.append(command)
        return self.result


class FakeListSkills:
    """Test double for the list-skills inbound application port."""

    def __init__(self, result: ListSkillsResult | None = None) -> None:
        """Store the result to return and commands received by the CLI."""
        self.result = result or ListSkillsResult(
            indexes=(
                ListedIndexSkills(
                    index_name="company-skills",
                    skills=(
                        CachedSkillSummary(
                            name="skill-a",
                            path="skill-a",
                            skill_file="skill-a/SKILL.md",
                            description="Helps with skill A workflows.",
                        ),
                    ),
                ),
            ),
        )
        self.commands: list[ListSkillsCommand] = []

    def execute(self, command: ListSkillsCommand) -> ListSkillsResult:
        """Record the command and return the configured result."""
        self.commands.append(command)
        return self.result


class FakeInstallSkill:
    """Test double for the install-skill inbound application port."""

    def __init__(self, result: InstallSkillResult | None = None) -> None:
        """Store the result to return and commands received by the CLI."""
        self.result = result or InstallSkillResult(
            requirement="platform-skills/code-review",
            target=".claude/skills/code-review",
            ownership_entry=_owned_installation(),
        )
        self.commands: list[InstallSkillCommand] = []

    def execute(self, command: InstallSkillCommand) -> InstallSkillResult:
        """Record the command and return the configured result."""
        self.commands.append(command)
        return self.result


class FakeInstallFromRequirements:
    """Test double for the install inbound application port."""

    def __init__(self, result: InstallFromRequirementsResult | None = None) -> None:
        """Store the result to return and commands received by the CLI."""
        self.result = result or InstallFromRequirementsResult(
            requirements_file="ritebook.toml",
            installed_count=3,
            updated_count=1,
            unchanged_count=2,
            pruned_count=1,
            ownership_entries=(),
            issues=(),
        )
        self.commands: list[InstallFromRequirementsCommand] = []

    def execute(
        self,
        command: InstallFromRequirementsCommand,
    ) -> InstallFromRequirementsResult:
        """Record the command and return the configured result."""
        self.commands.append(command)
        return self.result


def _owned_installation() -> OwnedInstallation:
    target = ".claude/skills/code-review"
    return OwnedInstallation(
        workflow=InstallationWorkflow.DIRECT,
        requirement="platform-skills/code-review",
        index_name="platform-skills",
        skill_name="code-review",
        target=target,
        target_id=f"sha256:{'1' * 64}",
        canonical_target=str((Path.cwd() / target).resolve(strict=False)),
        source="git@example.com:company/skills.git",
        source_type="git_url",
        source_revision="a" * 40,
        source_branch="refs/heads/main",
        index_digest=f"sha256:{'b' * 64}",
        index_schema_version=1,
        skill_path="skills/code-review",
        skill_file="skills/code-review/SKILL.md",
        installed_tree_digest=f"sha256:{'c' * 64}",
    )


class FailingPublisher:
    """Test double that raises a configured runtime error."""

    def __init__(self, error: Exception) -> None:
        """Store the error raised when the CLI invokes the port."""
        self.error = error

    def execute(self, _command: PublishIndexCommand) -> PublishIndexResult:
        """Raise the configured error for runtime error handling tests."""
        raise self.error


class FailingLinter:
    """Test double that raises a configured lint runtime error."""

    def __init__(self, error: Exception) -> None:
        """Store the error raised when the CLI invokes the port."""
        self.error = error

    def execute(self, _command: LintSkillsCommand) -> LintSkillsResult:
        """Raise the configured error for runtime error handling tests."""
        raise self.error


class FailingAddIndex:
    """Test double that raises a configured add-index runtime error."""

    def __init__(self, error: Exception) -> None:
        """Store the error raised when the CLI invokes the port."""
        self.error = error

    def execute(self, _command: AddIndexCommand) -> AddIndexResult:
        """Raise the configured error for runtime error handling tests."""
        raise self.error


class FailingUpdateIndex:
    """Test double that raises a configured update-index runtime error."""

    def __init__(self, error: Exception) -> None:
        """Store the error raised when the CLI invokes the port."""
        self.error = error

    def execute(self, _command: UpdateIndexCommand) -> UpdateIndexResult:
        """Raise the configured error for runtime error handling tests."""
        raise self.error


class FailingListIndexes:
    """Test double that raises a configured list-indexes runtime error."""

    def __init__(self, error: Exception) -> None:
        """Store the error raised when the CLI invokes the port."""
        self.error = error

    def execute(self, _command: ListIndexesCommand) -> ListIndexesResult:
        """Raise the configured error for runtime error handling tests."""
        raise self.error


class FailingListSkills:
    """Test double that raises a configured list-skills runtime error."""

    def __init__(self, error: Exception) -> None:
        """Store the error raised when the CLI invokes the port."""
        self.error = error

    def execute(self, _command: ListSkillsCommand) -> ListSkillsResult:
        """Raise the configured error for runtime error handling tests."""
        raise self.error


class FailingInstallSkill:
    """Test double that raises a configured install-skill runtime error."""

    def __init__(self, error: Exception) -> None:
        """Store the error raised when the CLI invokes the port."""
        self.error = error

    def execute(self, _command: InstallSkillCommand) -> InstallSkillResult:
        """Raise the configured error for runtime error handling tests."""
        raise self.error


class FailingInstallFromRequirements:
    """Test double that raises a configured install runtime error."""

    def __init__(self, error: Exception) -> None:
        """Store the error raised when the CLI invokes the port."""
        self.error = error

    def execute(
        self,
        _command: InstallFromRequirementsCommand,
    ) -> InstallFromRequirementsResult:
        """Raise the configured error for runtime error handling tests."""
        raise self.error


class FailingPublishSkillChange:
    """Test double that raises a configured contribution runtime error."""

    def __init__(self, error: Exception) -> None:
        """Store the error raised when the CLI invokes the port."""
        self.error = error

    def execute(
        self,
        _command: PublishSkillChangeCommand,
    ) -> PublishSkillChangeResult:
        """Raise the configured error for runtime error handling tests."""
        raise self.error


def test_publish_skill_change_maps_default_arguments_and_prints_no_op() -> None:
    publish_skill_change = FakePublishSkillChange()
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        ["skills", "contribute", "platform-skills/code-review"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        publish_skill_change=publish_skill_change,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert publish_skill_change.commands == [
        PublishSkillChangeCommand(skill_reference="platform-skills/code-review"),
    ]
    assert stdout.getvalue() == ("No local changes to publish for platform-skills/code-review\n")
    assert stderr.getvalue() == ""


def test_skills_contribute_maps_canonical_arguments_without_warning() -> None:
    publish_skill_change = FakePublishSkillChange()
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        ["skills", "contribute", "platform-skills/code-review"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        publish_skill_change=publish_skill_change,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert publish_skill_change.commands == [
        PublishSkillChangeCommand(skill_reference="platform-skills/code-review"),
    ]
    assert stdout.getvalue() == ("No local changes to publish for platform-skills/code-review\n")
    assert stderr.getvalue() == ""


def test_removed_flat_command_is_rejected() -> None:
    stderr = StringIO()

    exit_code = run_cli(
        ["publish-skill-change", "platform-skills/code-review"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        add_index=FakeAddIndex(),
        list_indexes=FakeListIndexes(),
        list_skills=FakeListSkills(),
        update_index=FakeUpdateIndex(),
        install_skill=FakeInstallSkill(),
        install_from_requirements=FakeInstallFromRequirements(),
        publish_skill_change=FakePublishSkillChange(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == ARGPARSE_USAGE_ERROR
    assert "invalid choice: 'publish-skill-change'" in stderr.getvalue()


def test_publish_skill_change_maps_path_overrides() -> None:
    publish_skill_change = FakePublishSkillChange()

    exit_code = run(
        [
            "skills",
            "contribute",
            "platform-skills/code-review",
            "--lockfile",
            "/tmp/repo/ritebook.lock",
            "--contribution-root",
            "/tmp/ritebook/contributions",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        publish_skill_change=publish_skill_change,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert publish_skill_change.commands == [
        PublishSkillChangeCommand(
            skill_reference="platform-skills/code-review",
            lockfile_path="/tmp/repo/ritebook.lock",
            contribution_root="/tmp/ritebook/contributions",
        ),
    ]


def test_publish_skill_change_prints_prepared_contribution_with_push_step() -> None:
    result = PublishSkillChangeResult(
        skill_reference="platform-skills/code-review",
        status=SkillChangeStatus.CHANGED,
        prepared_contribution=PreparedContribution(
            skill_reference="platform-skills/code-review",
            checkout_path="/tmp/ritebook/contributions/platform-skills-code-review",
            branch_name="ritebook/code-review-20260718201534",
            commit_hash="abc1234",
            push_command="git push origin ritebook/code-review-20260718201534",
        ),
    )
    stdout = StringIO()

    exit_code = run(
        ["skills", "contribute", "platform-skills/code-review"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        publish_skill_change=FakePublishSkillChange(result),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert stdout.getvalue() == (
        "Prepared contribution for platform-skills/code-review\n"
        "Branch: ritebook/code-review-20260718201534\n"
        "Commit: abc1234\n"
        "Checkout: /tmp/ritebook/contributions/platform-skills-code-review\n"
        "Next: cd /tmp/ritebook/contributions/platform-skills-code-review && "
        "git push origin ritebook/code-review-20260718201534\n"
    )


def test_publish_skill_change_prints_manual_guidance_without_origin() -> None:
    result = PublishSkillChangeResult(
        skill_reference="platform-skills/code-review",
        status=SkillChangeStatus.CHANGED,
        prepared_contribution=PreparedContribution(
            skill_reference="platform-skills/code-review",
            checkout_path="/tmp/ritebook/contributions/platform-skills-code-review",
            branch_name="ritebook/code-review-20260718201534",
            commit_hash="abc1234",
        ),
    )
    stdout = StringIO()

    exit_code = run(
        ["skills", "contribute", "platform-skills/code-review"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        publish_skill_change=FakePublishSkillChange(result),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert stdout.getvalue() == (
        "Prepared contribution for platform-skills/code-review\n"
        "Branch: ritebook/code-review-20260718201534\n"
        "Commit: abc1234\n"
        "Checkout: /tmp/ritebook/contributions/platform-skills-code-review\n"
        "Next: inspect the checkout and push or share the branch manually; "
        "no usable origin remote is configured.\n"
    )
    assert "git push origin" not in stdout.getvalue()


def test_publish_skill_change_translates_application_errors() -> None:
    stderr = StringIO()

    exit_code = run(
        ["skills", "contribute", "platform-skills/missing"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        publish_skill_change=FailingPublishSkillChange(
            ContributionLockfileEntryNotFoundError(
                "no lockfile entry found for platform-skills/missing",
            ),
        ),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == ("ritebook: error: no lockfile entry found for platform-skills/missing\n")


def test_install_skill_translates_command_validation_errors() -> None:
    stderr = StringIO()

    exit_code = run(
        ["skills", "install", "malformed", "--target", "target"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == (
        "ritebook: error: Skill reference must be fully qualified as <local-alias>/<skill-path>.\n"
    )


def test_sync_translates_command_validation_errors() -> None:
    stderr = StringIO()

    exit_code = run(
        ["skills", "sync", "--file", ""],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == ("ritebook: error: Requirements file must not be empty.\n")


def test_cli_error_boundaries_escape_controls_without_forging_lines() -> None:
    unsafe_error = ValueError("unsafe\n\x1b[31mforged")
    scenarios = (
        (
            ["indexes", "add", "--source", "git@example.com:company/skills.git"],
            {"add_index": FailingAddIndex(unsafe_error)},
        ),
        (
            ["skills", "install", "platform-skills/code-review", "--target", "target"],
            {"install_skill": FailingInstallSkill(unsafe_error)},
        ),
        (
            ["skills", "contribute", "platform-skills/code-review"],
            {"publish_skill_change": FailingPublishSkillChange(unsafe_error)},
        ),
        (
            ["indexes", "publish", "--skills-root", ".", "--name", "skills"],
            {"publisher": FailingPublisher(unsafe_error)},
        ),
        (
            ["skills", "lint", "--root", "."],
            {"linter": FailingLinter(unsafe_error)},
        ),
    )

    for argv, overrides in scenarios:
        stderr = StringIO()
        dependencies = {
            "linter": FakeLinter(),
            "publisher": FakePublisher(),
            **overrides,
        }

        exit_code = run(
            argv,
            stdout=StringIO(),
            stderr=stderr,
            **dependencies,
        )

        assert exit_code == 1
        assert stderr.getvalue() == r"ritebook: error: unsafe\n\x1b[31mforged" + "\n"
        assert stderr.getvalue().count("\n") == 1
        assert "\x1b" not in stderr.getvalue()


def test_publish_skill_change_requires_skill_reference_with_argparse_error() -> None:
    stderr = StringIO()

    exit_code = run(
        ["skills", "contribute"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == ARGPARSE_USAGE_ERROR
    assert "usage: ritebook skills contribute" in stderr.getvalue()
    assert "the following arguments are required: SKILL" in stderr.getvalue()


def test_publish_index_maps_arguments_to_application_command() -> None:
    publisher = FakePublisher(
        PublishIndexResult(discovered_skill_count=3, output_path="ritebook-index.json"),
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        [
            "indexes",
            "publish",
            "--skills-root",
            "skills",
            "--name",
            "company-skills",
        ],
        linter=FakeLinter(),
        publisher=publisher,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert publisher.commands == [
        PublishIndexCommand(
            index_name="company-skills",
            skills_root=str(Path.cwd() / "skills"),
            published_skills_root="skills",
        ),
    ]
    assert stdout.getvalue() == ("Published skill index with 3 skill(s) to ritebook-index.json\n")
    assert stderr.getvalue() == ""


def test_indexes_publish_maps_canonical_arguments_to_application_command() -> None:
    publisher = FakePublisher(
        PublishIndexResult(discovered_skill_count=3, output_path="ritebook-index.json"),
    )

    exit_code = run(
        ["indexes", "publish", "--skills-root", "skills", "--name", "company-skills"],
        linter=FakeLinter(),
        publisher=publisher,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert publisher.commands == [
        PublishIndexCommand(
            index_name="company-skills",
            skills_root=str(Path.cwd() / "skills"),
            published_skills_root="skills",
        ),
    ]


def test_publish_index_uses_canonical_output_path() -> None:
    publisher = FakePublisher()

    exit_code = run(
        ["indexes", "publish", "--skills-root", ".", "--name", "company-skills"],
        linter=FakeLinter(),
        publisher=publisher,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert publisher.commands == [
        PublishIndexCommand(
            index_name="company-skills",
            skills_root=str(Path.cwd()),
            published_skills_root=".",
        ),
    ]


def test_publish_index_normalizes_absolute_nested_root() -> None:
    publisher = FakePublisher()
    skills_root = Path.cwd() / "nested" / "skills"

    exit_code = run(
        [
            "indexes",
            "publish",
            "--skills-root",
            str(skills_root),
            "--name",
            "company-skills",
        ],
        linter=FakeLinter(),
        publisher=publisher,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert publisher.commands == [
        PublishIndexCommand(
            index_name="company-skills",
            skills_root=str(skills_root),
            published_skills_root="nested/skills",
        ),
    ]


def test_publish_index_rejects_skills_root_outside_output_directory(
    tmp_path: Path,
) -> None:
    publisher = FakePublisher()
    stderr = StringIO()

    exit_code = run(
        [
            "indexes",
            "publish",
            "--skills-root",
            str(tmp_path),
            "--name",
            "company-skills",
        ],
        linter=FakeLinter(),
        publisher=publisher,
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert publisher.commands == []
    assert stderr.getvalue() == ("ritebook: error: Skills root must be inside the index output directory.\n")


def test_publish_index_rejects_output_argument_with_argparse_error() -> None:
    stderr = StringIO()

    exit_code = run(
        [
            "indexes",
            "publish",
            "--skills-root",
            "skills",
            "--name",
            "company-skills",
            "--output",
            "custom-index.json",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == ARGPARSE_USAGE_ERROR
    assert "unrecognized arguments: --output custom-index.json" in stderr.getvalue()


def test_top_level_help_uses_injected_stdout() -> None:
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        ["--help"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert "usage: ritebook" in stdout.getvalue()
    assert "Manage Agent Skills and published skill indexes." in stdout.getvalue()
    assert "skills" in stdout.getvalue()
    assert "indexes" in stdout.getvalue()
    assert "publish-index" not in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_top_level_version_uses_injected_stdout() -> None:
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        ["--version"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert stdout.getvalue() == f"ritebook {__version__}\n"
    assert stderr.getvalue() == ""


def test_subcommand_help_uses_injected_stdout() -> None:
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        ["indexes", "publish", "--help"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert "usage: ritebook indexes publish" in stdout.getvalue()
    assert "--skills-root" in stdout.getvalue()
    assert "--name" in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_command_group_help_describes_available_workflows() -> None:
    stdout = StringIO()

    exit_code = run(
        ["skills", "--help"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert "Validate, browse, install, synchronize, and contribute skills." in (stdout.getvalue())
    assert "{lint,list,install,sync,contribute}" in stdout.getvalue()


def test_removed_canonical_option_aliases_are_rejected() -> None:
    scenarios = (
        ["skills", "lint", "--skills-root", "skills"],
        ["indexes", "publish", "--skills-root", "skills", "--index-name", "name"],
        ["skills", "list", "--index-name", "platform-skills"],
        ["indexes", "update", "--name", "platform-skills"],
    )

    for argv in scenarios:
        stderr = StringIO()

        exit_code = run(
            argv,
            linter=FakeLinter(),
            publisher=FakePublisher(),
            stdout=StringIO(),
            stderr=stderr,
        )

        assert exit_code == ARGPARSE_USAGE_ERROR
        assert "error:" in stderr.getvalue()


def test_publish_index_requires_skills_root_with_argparse_error() -> None:
    stderr = StringIO()

    exit_code = run(
        ["indexes", "publish"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == ARGPARSE_USAGE_ERROR
    assert "usage: ritebook indexes publish" in stderr.getvalue()
    assert "--skills-root" in stderr.getvalue()
    assert "--name" in stderr.getvalue()


def test_publish_index_requires_index_name_with_argparse_error() -> None:
    stderr = StringIO()

    exit_code = run(
        ["indexes", "publish", "--skills-root", "skills"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == ARGPARSE_USAGE_ERROR
    assert "usage: ritebook indexes publish" in stderr.getvalue()
    assert "--name" in stderr.getvalue()


def test_publish_index_translates_invalid_root_errors() -> None:
    stderr = StringIO()

    exit_code = run(
        [
            "indexes",
            "publish",
            "--skills-root",
            "missing",
            "--name",
            "company-skills",
        ],
        linter=FakeLinter(),
        publisher=FailingPublisher(PublishIndexDiscoveryError("Skills root missing")),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == "ritebook: error: Skills root missing\n"


def test_publish_index_prints_validation_issues_to_stderr() -> None:
    stderr = StringIO()

    exit_code = run(
        [
            "indexes",
            "publish",
            "--skills-root",
            "skills",
            "--name",
            "company-skills",
        ],
        linter=FakeLinter(),
        publisher=FailingPublisher(
            PublishIndexValidationError(
                [
                    SkillPrecheckIssue(
                        skill_file="alpha/SKILL.md",
                        message="description is required.",
                    ),
                ],
            ),
        ),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == "alpha/SKILL.md: description is required.\n"


def test_add_index_maps_arguments_to_application_command() -> None:
    add_index = FakeAddIndex(AddIndexResult(name="platform-skills", skill_count=12))
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        [
            "indexes",
            "add",
            "--source",
            "git@example.com:company/skills.git",
            "--alias",
            "platform-skills",
            "--force",
            "--registry-path",
            "/tmp/indexes.json",
            "--cache-root",
            "/tmp/cache",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        add_index=add_index,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert add_index.commands == [
        AddIndexCommand(
            source="git@example.com:company/skills.git",
            alias="platform-skills",
            force=True,
            registry_path="/tmp/indexes.json",
            cache_root="/tmp/cache",
        ),
    ]
    assert stdout.getvalue() == "Added index platform-skills with 12 skill(s)\n"
    assert stderr.getvalue() == ""


def test_indexes_add_maps_canonical_arguments_to_application_command() -> None:
    add_index = FakeAddIndex(
        AddIndexResult(name="platform-skills", skill_count=2),
    )

    exit_code = run(
        [
            "indexes",
            "add",
            "--source",
            "repo",
            "--alias",
            "platform-skills",
            "--force",
            "--registry-path",
            "registry.json",
            "--cache-root",
            "cache",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        add_index=add_index,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert add_index.commands == [
        AddIndexCommand(
            source="repo",
            alias="platform-skills",
            force=True,
            registry_path="registry.json",
            cache_root="cache",
        ),
    ]


def test_add_index_rejects_removed_name_override() -> None:
    stderr = StringIO()

    exit_code = run(
        ["indexes", "add", "--source", "repo", "--name", "platform-skills"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == ARGPARSE_USAGE_ERROR
    assert "unrecognized arguments: --name platform-skills" in stderr.getvalue()


def test_add_index_translates_duplicate_name_errors() -> None:
    stderr = StringIO()

    exit_code = run(
        ["indexes", "add", "--source", "repo"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        add_index=FailingAddIndex(DuplicateIndexNameError("company-skills")),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == (
        "ritebook: error: local alias company-skills already exists; use --force to replace it\n"
    )


def test_update_index_maps_arguments_to_application_command() -> None:
    update_index = FakeUpdateIndex(
        UpdateIndexResult(name="platform-skills", skill_count=14),
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        [
            "indexes",
            "update",
            "platform-skills",
            "--registry-path",
            "/tmp/indexes.json",
            "--cache-root",
            "/tmp/cache",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        update_index=update_index,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert update_index.commands == [
        UpdateIndexCommand(
            name="platform-skills",
            all=False,
            registry_path="/tmp/indexes.json",
            cache_root="/tmp/cache",
        ),
    ]
    assert stdout.getvalue() == "Updated index platform-skills with 14 skill(s)\n"
    assert stderr.getvalue() == ""


def test_indexes_update_maps_canonical_positional_alias_to_application_command() -> None:
    update_index = FakeUpdateIndex(
        UpdateIndexResult(name="platform-skills", skill_count=2),
    )

    exit_code = run(
        [
            "indexes",
            "update",
            "platform-skills",
            "--registry-path",
            "registry.json",
            "--cache-root",
            "cache",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        update_index=update_index,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert update_index.commands == [
        UpdateIndexCommand(
            name="platform-skills",
            registry_path="registry.json",
            cache_root="cache",
        ),
    ]


def test_update_index_all_maps_arguments_to_application_command() -> None:
    update_index = FakeUpdateIndex(
        UpdateIndexResult(
            name=None,
            skill_count=17,
            updated_indexes=("alpha-skills", "gamma-skills"),
            failed_indexes=("beta-skills",),
        ),
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        [
            "indexes",
            "update",
            "--all",
            "--registry-path",
            "/tmp/indexes.json",
            "--cache-root",
            "/tmp/cache",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        update_index=update_index,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 1
    assert update_index.commands == [
        UpdateIndexCommand(
            name=None,
            all=True,
            registry_path="/tmp/indexes.json",
            cache_root="/tmp/cache",
        ),
    ]
    assert stdout.getvalue() == ("Updated 2 index(es) with 17 total skill(s)\n")
    assert stderr.getvalue() == "Failed to update 1 index(es): beta-skills\n"


def test_update_index_requires_name_or_all_with_argparse_error() -> None:
    stderr = StringIO()

    exit_code = run(
        ["indexes", "update"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == ARGPARSE_USAGE_ERROR
    assert "provide exactly one of <local-alias> or --all" in stderr.getvalue()


def test_list_indexes_maps_arguments_to_application_command() -> None:
    list_indexes = FakeListIndexes()
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        ["indexes", "list", "--registry-path", "/tmp/indexes.json"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_indexes=list_indexes,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert list_indexes.commands == [
        ListIndexesCommand(registry_path="/tmp/indexes.json"),
    ]
    assert stdout.getvalue() == (
        "company-skills\t2 skill(s)\tgit_url\t2026-07-08T18:00:00Z\tgit@example.com:company/skills.git\n"
    )
    assert stderr.getvalue() == ""


def test_indexes_list_maps_canonical_arguments_to_application_command() -> None:
    list_indexes = FakeListIndexes()

    exit_code = run(
        ["indexes", "list", "--registry-path", "registry.json"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_indexes=list_indexes,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert list_indexes.commands == [ListIndexesCommand(registry_path="registry.json")]


def test_list_indexes_prints_empty_registry_message() -> None:
    stdout = StringIO()

    exit_code = run(
        ["indexes", "list"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_indexes=FakeListIndexes(ListIndexesResult(indexes=())),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert stdout.getvalue() == "No indexes registered\n"


def test_list_indexes_redacts_url_user_info_defensively() -> None:
    sentinel = "sentinel-secret"
    stdout = StringIO()
    result = ListIndexesResult(
        indexes=(
            RegisteredIndexSummary(
                name="company-skills",
                published_name="company-skills",
                source_type="git_url",
                source=f"https://user:{sentinel}@example.com/company/skills.git",
                skill_count=2,
                updated_at="2026-07-08T18:00:00Z",
            ),
        ),
    )

    exit_code = run(
        ["indexes", "list"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_indexes=FakeListIndexes(result),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert sentinel not in stdout.getvalue()
    assert stdout.getvalue().endswith("https://example.com/company/skills.git\n")


def test_list_indexes_escapes_source_controls_without_forging_lines() -> None:
    stdout = StringIO()
    result = ListIndexesResult(
        indexes=(
            RegisteredIndexSummary(
                name="company-skills",
                published_name="company-skills",
                source_type="local_git_repo",
                source="/repos/company\n\x1b[31mforged",
                skill_count=2,
                updated_at="2026-07-08T18:00:00Z",
            ),
        ),
    )

    exit_code = run(
        ["indexes", "list"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_indexes=FakeListIndexes(result),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert stdout.getvalue().count("\n") == 1
    assert "\x1b" not in stdout.getvalue()
    assert stdout.getvalue().endswith(r"/repos/company\n\x1b[31mforged" + "\n")


def test_list_skills_maps_arguments_to_application_command() -> None:
    list_skills = FakeListSkills()
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        [
            "skills",
            "list",
            "--index",
            "platform-skills",
            "--registry-path",
            "/tmp/indexes.json",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_skills=list_skills,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert list_skills.commands == [
        ListSkillsCommand(
            index_name="platform-skills",
            registry_path="/tmp/indexes.json",
            show_description=False,
        ),
    ]
    assert stdout.getvalue() == "Indexes\n└── company-skills\n    └── skill-a\n"
    assert stderr.getvalue() == ""


def test_skills_list_maps_canonical_arguments_to_application_command() -> None:
    list_skills = FakeListSkills()

    exit_code = run(
        [
            "skills",
            "list",
            "--index",
            "platform-skills",
            "--registry-path",
            "registry.json",
            "--show-description",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_skills=list_skills,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert list_skills.commands == [
        ListSkillsCommand(
            index_name="platform-skills",
            registry_path="registry.json",
            show_description=True,
        ),
    ]


def test_list_skills_prints_deterministic_tree_output() -> None:
    stdout = StringIO()
    result = ListSkillsResult(
        indexes=(
            ListedIndexSkills(
                index_name="platform-skills",
                skills=(
                    CachedSkillSummary(
                        name="skill-a",
                        path="skill-a",
                        skill_file="skill-a/SKILL.md",
                        description="Helps with skill A workflows.",
                    ),
                    CachedSkillSummary(
                        name="skill-b",
                        path="skill-b",
                        skill_file="skill-b/SKILL.md",
                        description="Helps with skill B workflows.",
                    ),
                ),
            ),
            ListedIndexSkills(
                index_name="data-skills",
                skills=(
                    CachedSkillSummary(
                        name="query-helper",
                        path="query-helper",
                        skill_file="query-helper/SKILL.md",
                        description="Helps with query workflows.",
                    ),
                ),
            ),
        ),
    )

    exit_code = run(
        ["skills", "list"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_skills=FakeListSkills(result),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert stdout.getvalue() == (
        "Indexes\n├── platform-skills\n│   ├── skill-a\n│   └── skill-b\n└── data-skills\n    └── query-helper\n"
    )


def test_list_skills_prints_nested_skill_paths() -> None:
    stdout = StringIO()
    result = ListSkillsResult(
        indexes=(
            ListedIndexSkills(
                index_name="platform-skills",
                skills=(
                    CachedSkillSummary(
                        name="runtime-verification",
                        path="browser/runtime-verification",
                        skill_file="browser/runtime-verification/SKILL.md",
                        description="Helps verify browser behavior.",
                    ),
                ),
            ),
        ),
    )

    exit_code = run(
        ["skills", "list"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_skills=FakeListSkills(result),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert stdout.getvalue() == ("Indexes\n└── platform-skills\n    └── browser/runtime-verification\n")


def test_list_skills_maps_show_description_to_application_command() -> None:
    list_skills = FakeListSkills()

    exit_code = run(
        ["skills", "list", "--show-description"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_skills=list_skills,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert list_skills.commands == [ListSkillsCommand(show_description=True)]


def test_list_skills_prints_descriptions_when_requested() -> None:
    stdout = StringIO()
    result = ListSkillsResult(
        indexes=(
            ListedIndexSkills(
                index_name="platform-skills",
                skills=(
                    CachedSkillSummary(
                        name="skill-a",
                        path="skill-a",
                        skill_file="skill-a/SKILL.md",
                        description="Helps with alpha workflows.",
                    ),
                    CachedSkillSummary(
                        name="skill-b",
                        path="skill-b",
                        skill_file="skill-b/SKILL.md",
                        description="Helps with beta workflows.",
                    ),
                ),
            ),
        ),
    )

    exit_code = run(
        ["skills", "list", "--show-description"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_skills=FakeListSkills(result),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert stdout.getvalue() == (
        "Indexes\n"
        "└── platform-skills\n"
        "    ├── skill-a — Helps with alpha workflows.\n"
        "    └── skill-b — Helps with beta workflows.\n"
    )


def test_list_skills_escapes_description_controls_and_preserves_unicode() -> None:
    stdout = StringIO()
    result = ListSkillsResult(
        indexes=(
            ListedIndexSkills(
                index_name="platform-skills",
                skills=(
                    CachedSkillSummary(
                        name="skill-a",
                        path="skill-a",
                        skill_file="skill-a/SKILL.md",
                        description="Příliš žluťoučký kůň\n\x1b[31m検証 🔍.",
                    ),
                ),
            ),
        ),
    )

    exit_code = run(
        ["skills", "list", "--show-description"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_skills=FakeListSkills(result),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert stdout.getvalue().count("\n") == 3
    assert "\x1b" not in stdout.getvalue()
    assert "Příliš žluťoučký kůň" in stdout.getvalue()
    assert r"\n\x1b[31m検証 🔍." in stdout.getvalue()


def test_list_skills_prints_empty_result_message() -> None:
    stdout = StringIO()

    exit_code = run(
        ["skills", "list"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_skills=FakeListSkills(ListSkillsResult(indexes=())),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert stdout.getvalue() == "No skills found\n"


def test_list_skills_prints_empty_selected_index_message() -> None:
    stdout = StringIO()
    result = ListSkillsResult(
        indexes=(ListedIndexSkills(index_name="platform-skills", skills=()),),
    )

    exit_code = run(
        ["skills", "list", "--index", "platform-skills"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_skills=FakeListSkills(result),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert stdout.getvalue() == "No skills found\n"


def test_list_skills_translates_application_errors() -> None:
    stderr = StringIO()

    exit_code = run(
        ["skills", "list", "--index", "missing-skills"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_skills=FailingListSkills(UnknownIndexNameError("missing-skills")),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == ("ritebook: error: local alias missing-skills is not registered\n")


def test_list_skills_reports_invalid_catalog_republish_guidance() -> None:
    stderr = StringIO()
    error = InvalidPublishedIndexError(
        "invalid schema-v1 catalog structure; reorganize skills and republish the index",
    )

    exit_code = run(
        ["skills", "list"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_skills=FailingListSkills(error),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == (
        "ritebook: error: invalid schema-v1 catalog structure; reorganize skills and republish the index\n"
    )


def test_install_skill_maps_arguments_to_application_command() -> None:
    install_skill = FakeInstallSkill()
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        [
            "skills",
            "install",
            "platform-skills/code-review",
            "--target",
            ".claude/skills/code-review",
            "--force",
            "--registry-path",
            "/tmp/indexes.json",
            "--installation-registry-path",
            "/tmp/installations.json",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        install_skill=install_skill,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert install_skill.commands == [
        InstallSkillCommand(
            skill_reference="platform-skills/code-review",
            target=".claude/skills/code-review",
            force=True,
            registry_path="/tmp/indexes.json",
            installation_registry_path="/tmp/installations.json",
        ),
    ]
    assert stdout.getvalue() == ("Installed platform-skills/code-review to .claude/skills/code-review\n")
    assert stderr.getvalue() == ""


def test_skills_install_maps_canonical_arguments_to_application_command() -> None:
    install_skill = FakeInstallSkill()

    exit_code = run(
        [
            "skills",
            "install",
            "platform-skills/code-review",
            "--target",
            ".agents/skills/code-review",
            "--force",
            "--registry-path",
            "registry.json",
            "--installation-registry-path",
            "installations.json",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        install_skill=install_skill,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert install_skill.commands == [
        InstallSkillCommand(
            skill_reference="platform-skills/code-review",
            target=".agents/skills/code-review",
            force=True,
            registry_path="registry.json",
            installation_registry_path="installations.json",
        ),
    ]


def test_install_skill_requires_target_with_argparse_error() -> None:
    stderr = StringIO()

    exit_code = run(
        ["skills", "install", "platform-skills/code-review"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == ARGPARSE_USAGE_ERROR
    assert "usage: ritebook skills install" in stderr.getvalue()
    assert "the following arguments are required: --target" in stderr.getvalue()


def test_install_skill_translates_application_errors() -> None:
    stderr = StringIO()

    exit_code = run(
        [
            "skills",
            "install",
            "platform-skills/code-review",
            "--target",
            ".claude/skills/code-review",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        install_skill=FailingInstallSkill(
            ExistingInstallTargetError(".claude/skills/code-review"),
        ),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == (
        "ritebook: error: target .claude/skills/code-review already exists; use --force to replace it\n"
    )


def test_install_skill_translates_transaction_recovery_failure() -> None:
    stderr = StringIO()

    exit_code = run(
        [
            "skills",
            "install",
            "platform-skills/code-review",
            "--target",
            ".claude/skills/code-review",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        install_skill=FailingInstallSkill(
            InstallationPersistenceError(
                "installation rollback failed; recover using journal /tmp/installation-transaction.json",
            ),
        ),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == (
        "ritebook: error: installation rollback failed; recover using journal /tmp/installation-transaction.json\n"
    )


def test_install_maps_default_arguments_to_application_command() -> None:
    install_from_requirements = FakeInstallFromRequirements()
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        ["skills", "sync"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        install_from_requirements=install_from_requirements,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert install_from_requirements.commands == [
        InstallFromRequirementsCommand(requirements_file="ritebook.toml"),
    ]
    assert stdout.getvalue() == (
        "Reconciled skills from ritebook.toml: installed 3, updated 1, unchanged 2, pruned 1\n"
    )
    assert stderr.getvalue() == ""


def test_skills_sync_maps_canonical_arguments_to_application_command() -> None:
    install_from_requirements = FakeInstallFromRequirements()

    exit_code = run(
        [
            "skills",
            "sync",
            "--file",
            "requirements.toml",
            "--force",
            "--registry-path",
            "registry.json",
            "--lockfile",
            "ritebook.lock",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        install_from_requirements=install_from_requirements,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert install_from_requirements.commands == [
        InstallFromRequirementsCommand(
            requirements_file="requirements.toml",
            force=True,
            registry_path="registry.json",
            lockfile_path="ritebook.lock",
        ),
    ]


def test_install_maps_overrides_to_application_command() -> None:
    install_from_requirements = FakeInstallFromRequirements(
        InstallFromRequirementsResult(
            requirements_file="config/ritebook.toml",
            installed_count=2,
            updated_count=0,
            unchanged_count=1,
            pruned_count=0,
            ownership_entries=(),
            issues=(),
        ),
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        [
            "skills",
            "sync",
            "--file",
            "config/ritebook.toml",
            "--force",
            "--registry-path",
            "/tmp/indexes.json",
            "--lockfile",
            "/tmp/ritebook.lock",
        ],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        install_from_requirements=install_from_requirements,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert install_from_requirements.commands == [
        InstallFromRequirementsCommand(
            requirements_file="config/ritebook.toml",
            force=True,
            registry_path="/tmp/indexes.json",
            lockfile_path="/tmp/ritebook.lock",
        ),
    ]
    assert stdout.getvalue() == (
        "Reconciled skills from config/ritebook.toml: installed 2, updated 0, unchanged 1, pruned 0\n"
    )
    assert stderr.getvalue() == ""


def test_install_reports_partial_reconciliation_and_returns_nonzero() -> None:
    issue = ReconciliationIssue(
        code="local-changes",
        target=".agents/skills/code-review",
        requirement="platform-skills/code-review",
        detail="target has local changes\nand was preserved",
    )
    result = InstallFromRequirementsResult(
        requirements_file="ritebook.toml",
        installed_count=1,
        updated_count=0,
        unchanged_count=2,
        pruned_count=1,
        ownership_entries=(),
        issues=(issue,),
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        ["skills", "sync"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        install_from_requirements=FakeInstallFromRequirements(result),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 1
    assert stdout.getvalue() == (
        "Reconciled skills from ritebook.toml: installed 1, updated 0, unchanged 2, pruned 1\n"
    )
    assert stderr.getvalue() == (
        "ritebook: issue: local-changes: .agents/skills/code-review: "
        r"target has local changes\nand was preserved" + "\n"
    )
    assert stderr.getvalue().count("\n") == 1


def test_install_translates_application_errors() -> None:
    stderr = StringIO()

    exit_code = run(
        ["skills", "sync", "--file", "config/ritebook.toml"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        install_from_requirements=FailingInstallFromRequirements(
            UnknownInstallIndexError("platform-skills"),
        ),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == ("ritebook: error: unknown local alias: platform-skills\n")


def test_install_translates_transaction_recovery_failure() -> None:
    stderr = StringIO()

    exit_code = run(
        ["skills", "sync", "--file", "ritebook.toml"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        install_from_requirements=FailingInstallFromRequirements(
            InstallationPersistenceError(
                "interrupted installation recovery failed; recover using journal .ritebook/transaction.json",
            ),
        ),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == (
        "ritebook: error: interrupted installation recovery failed; recover using journal .ritebook/transaction.json\n"
    )


def test_lint_skills_maps_arguments_to_application_command() -> None:
    linter = FakeLinter(
        LintSkillsResult.create(
            discovered_skill_count=3,
            issues=[],
            validated_skills=[
                _validated_skill("alpha"),
                _validated_skill("beta"),
                _validated_skill("zeta"),
            ],
        ),
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        ["skills", "lint", "--root", "skills"],
        linter=linter,
        publisher=FakePublisher(),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert linter.commands == [LintSkillsCommand(skills_root="skills")]
    assert stdout.getvalue() == "Checked 3 skill(s)\n"
    assert stderr.getvalue() == ""


def test_skills_lint_maps_canonical_arguments_to_application_command() -> None:
    linter = FakeLinter()

    exit_code = run(
        ["skills", "lint", "--root", "skills"],
        linter=linter,
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert linter.commands == [LintSkillsCommand(skills_root="skills")]


def test_lint_skills_requires_skills_root_with_argparse_error() -> None:
    stderr = StringIO()

    exit_code = run(
        ["skills", "lint"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == ARGPARSE_USAGE_ERROR
    assert "usage: ritebook skills lint" in stderr.getvalue()
    assert "the following arguments are required: --root" in stderr.getvalue()


def test_lint_skills_prints_validation_issues_to_stderr() -> None:
    stderr = StringIO()

    exit_code = run(
        ["skills", "lint", "--root", "skills"],
        linter=FakeLinter(
            LintSkillsResult.create(
                discovered_skill_count=1,
                issues=[
                    SkillValidationIssue(
                        skill_file="alpha/SKILL.md",
                        message="description is required.",
                    ),
                ],
            ),
        ),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == "alpha/SKILL.md: description is required.\n"


def test_lint_skills_escapes_controls_in_diagnostics() -> None:
    stderr = StringIO()

    exit_code = run(
        ["skills", "lint", "--root", "skills"],
        linter=FakeLinter(
            LintSkillsResult.create(
                discovered_skill_count=1,
                issues=[
                    SkillValidationIssue(
                        skill_file="alpha\nforged/SKILL.md",
                        message="invalid\x1b[31m description.",
                    ),
                ],
            ),
        ),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue().count("\n") == 1
    assert "\x1b" not in stderr.getvalue()
    assert stderr.getvalue() == (r"alpha\nforged/SKILL.md: invalid\x1b[31m description." + "\n")


def test_lint_skills_translates_invalid_root_errors() -> None:
    stderr = StringIO()

    exit_code = run(
        ["skills", "lint", "--root", "missing"],
        linter=FailingLinter(LintSkillsDiscoveryError("Skills root missing")),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == "ritebook: error: Skills root missing\n"
