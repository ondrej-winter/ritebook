from __future__ import annotations

from io import StringIO
from typing import TextIO

from ritebook.adapters.inbound.cli import run as run_cli
from ritebook.adapters.outbound.filesystem import (
    SkillsRootNotFoundError,
)
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
    UnknownIndexNameError,
)
from ritebook.features.linter.application.dtos import (
    LintSkillsCommand,
    LintSkillsResult,
    SkillValidationIssue,
)
from ritebook.features.publisher.application.dtos import (
    PublishIndexCommand,
    PublishIndexResult,
    PublishIndexValidationError,
    SkillPrecheckIssue,
)

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


class FakeLinter:
    """Test double for the lint-skills inbound application port."""

    def __init__(self, result: LintSkillsResult | None = None) -> None:
        """Store the result to return and commands received by the CLI."""
        self.result = result or LintSkillsResult(validated_skill_count=2)
        self.commands: list[LintSkillsCommand] = []

    def execute(self, command: LintSkillsCommand) -> LintSkillsResult:
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


def test_publish_index_maps_arguments_to_application_command() -> None:
    publisher = FakePublisher(
        PublishIndexResult(discovered_skill_count=3, output_path="ritebook-index.json"),
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        [
            "publish-index",
            "--skills-root",
            "skills",
            "--index-name",
            "company-skills",
        ],
        linter=FakeLinter(),
        publisher=publisher,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert publisher.commands == [
        PublishIndexCommand(index_name="company-skills", skills_root="skills"),
    ]
    assert stdout.getvalue() == (
        "Published skill index with 3 skill(s) to ritebook-index.json\n"
    )
    assert stderr.getvalue() == ""


def test_publish_index_uses_canonical_output_path() -> None:
    publisher = FakePublisher()

    exit_code = run(
        ["publish-index", "--skills-root", ".", "--index-name", "company-skills"],
        linter=FakeLinter(),
        publisher=publisher,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert publisher.commands == [
        PublishIndexCommand(index_name="company-skills", skills_root="."),
    ]


def test_publish_index_rejects_output_argument_with_argparse_error() -> None:
    stderr = StringIO()

    exit_code = run(
        [
            "publish-index",
            "--skills-root",
            "skills",
            "--index-name",
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


def test_publish_index_requires_skills_root_with_argparse_error() -> None:
    stderr = StringIO()

    exit_code = run(
        ["publish-index"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == ARGPARSE_USAGE_ERROR
    assert "usage: ritebook publish-index" in stderr.getvalue()
    assert "--skills-root" in stderr.getvalue()
    assert "--index-name" in stderr.getvalue()


def test_publish_index_requires_index_name_with_argparse_error() -> None:
    stderr = StringIO()

    exit_code = run(
        ["publish-index", "--skills-root", "skills"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == ARGPARSE_USAGE_ERROR
    assert "usage: ritebook publish-index" in stderr.getvalue()
    assert "--index-name" in stderr.getvalue()


def test_publish_index_translates_invalid_root_errors() -> None:
    stderr = StringIO()

    exit_code = run(
        [
            "publish-index",
            "--skills-root",
            "missing",
            "--index-name",
            "company-skills",
        ],
        linter=FakeLinter(),
        publisher=FailingPublisher(SkillsRootNotFoundError("Skills root missing")),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == "ritebook: error: Skills root missing\n"


def test_publish_index_prints_validation_issues_to_stderr() -> None:
    stderr = StringIO()

    exit_code = run(
        [
            "publish-index",
            "--skills-root",
            "skills",
            "--index-name",
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
            "add-index",
            "--source",
            "git@example.com:company/skills.git",
            "--name",
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
            name="platform-skills",
            force=True,
            registry_path="/tmp/indexes.json",
            cache_root="/tmp/cache",
        ),
    ]
    assert stdout.getvalue() == "Added index platform-skills with 12 skill(s)\n"
    assert stderr.getvalue() == ""


def test_add_index_translates_duplicate_name_errors() -> None:
    stderr = StringIO()

    exit_code = run(
        ["add-index", "--source", "repo"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        add_index=FailingAddIndex(DuplicateIndexNameError("company-skills")),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == (
        "ritebook: error: index company-skills already exists; "
        "use --force to replace it\n"
    )


def test_update_index_maps_arguments_to_application_command() -> None:
    update_index = FakeUpdateIndex(
        UpdateIndexResult(name="platform-skills", skill_count=14),
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        [
            "update-index",
            "--name",
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
            "update-index",
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
        ["update-index"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == ARGPARSE_USAGE_ERROR
    assert "one of the arguments --name --all is required" in stderr.getvalue()


def test_list_indexes_maps_arguments_to_application_command() -> None:
    list_indexes = FakeListIndexes()
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        ["list-indexes", "--registry-path", "/tmp/indexes.json"],
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
        "company-skills\t2 skill(s)\tgit_url\t2026-07-08T18:00:00Z\t"
        "git@example.com:company/skills.git\n"
    )
    assert stderr.getvalue() == ""


def test_list_indexes_prints_empty_registry_message() -> None:
    stdout = StringIO()

    exit_code = run(
        ["list-indexes"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_indexes=FakeListIndexes(ListIndexesResult(indexes=())),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert stdout.getvalue() == "No indexes registered\n"


def test_list_skills_maps_arguments_to_application_command() -> None:
    list_skills = FakeListSkills()
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        [
            "list-skills",
            "--index-name",
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
        ),
    ]
    assert stdout.getvalue() == "Indexes\n└── company-skills\n    └── skill-a\n"
    assert stderr.getvalue() == ""


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
                    ),
                    CachedSkillSummary(
                        name="skill-b",
                        path="skill-b",
                        skill_file="skill-b/SKILL.md",
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
                        title="Query Helper",
                    ),
                ),
            ),
        ),
    )

    exit_code = run(
        ["list-skills"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_skills=FakeListSkills(result),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert stdout.getvalue() == (
        "Indexes\n"
        "├── platform-skills\n"
        "│   ├── skill-a\n"
        "│   └── skill-b\n"
        "└── data-skills\n"
        "    └── query-helper\n"
    )


def test_list_skills_prints_empty_result_message() -> None:
    stdout = StringIO()

    exit_code = run(
        ["list-skills"],
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
        ["list-skills", "--index-name", "platform-skills"],
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
        ["list-skills", "--index-name", "missing-skills"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        list_skills=FailingListSkills(UnknownIndexNameError("missing-skills")),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == (
        "ritebook: error: index missing-skills is not registered\n"
    )


def test_lint_skills_maps_arguments_to_application_command() -> None:
    linter = FakeLinter(LintSkillsResult(validated_skill_count=3))
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run(
        ["lint-skills", "--skills-root", "skills"],
        linter=linter,
        publisher=FakePublisher(),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert linter.commands == [LintSkillsCommand(skills_root="skills")]
    assert stdout.getvalue() == "Validated 3 skill(s)\n"
    assert stderr.getvalue() == ""


def test_lint_skills_requires_skills_root_with_argparse_error() -> None:
    stderr = StringIO()

    exit_code = run(
        ["lint-skills"],
        linter=FakeLinter(),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == ARGPARSE_USAGE_ERROR
    assert "usage: ritebook lint-skills" in stderr.getvalue()
    assert "the following arguments are required: --skills-root" in stderr.getvalue()


def test_lint_skills_prints_validation_issues_to_stderr() -> None:
    stderr = StringIO()

    exit_code = run(
        ["lint-skills", "--skills-root", "skills"],
        linter=FakeLinter(
            LintSkillsResult.create(
                validated_skill_count=1,
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


def test_lint_skills_translates_invalid_root_errors() -> None:
    stderr = StringIO()

    exit_code = run(
        ["lint-skills", "--skills-root", "missing"],
        linter=FailingLinter(SkillsRootNotFoundError("Skills root missing")),
        publisher=FakePublisher(),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == "ritebook: error: Skills root missing\n"
