from __future__ import annotations

from io import StringIO

from ritebook.features.skill_catalog.adapters.inbound.cli import run
from ritebook.features.skill_catalog.adapters.outbound.filesystem import (
    SkillsRootNotFoundError,
)
from ritebook.features.skill_catalog.application.dtos import (
    LintSkillsCommand,
    LintSkillsResult,
    PublishIndexCommand,
    PublishIndexResult,
    SkillValidationIssue,
)

ARGPARSE_USAGE_ERROR = 2


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
        ],
        linter=FakeLinter(),
        publisher=publisher,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert publisher.commands == [
        PublishIndexCommand(skills_root="skills"),
    ]
    assert stdout.getvalue() == (
        "Published skill index with 3 skill(s) to ritebook-index.json\n"
    )
    assert stderr.getvalue() == ""


def test_publish_index_uses_canonical_output_path() -> None:
    publisher = FakePublisher()

    exit_code = run(
        ["publish-index", "--skills-root", "."],
        linter=FakeLinter(),
        publisher=publisher,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert exit_code == 0
    assert publisher.commands == [
        PublishIndexCommand(skills_root="."),
    ]


def test_publish_index_rejects_output_argument_with_argparse_error() -> None:
    stderr = StringIO()

    exit_code = run(
        [
            "publish-index",
            "--skills-root",
            "skills",
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
    assert "the following arguments are required: --skills-root" in stderr.getvalue()


def test_publish_index_translates_invalid_root_errors() -> None:
    stderr = StringIO()

    exit_code = run(
        ["publish-index", "--skills-root", "missing"],
        linter=FakeLinter(),
        publisher=FailingPublisher(SkillsRootNotFoundError("Skills root missing")),
        stdout=StringIO(),
        stderr=stderr,
    )

    assert exit_code == 1
    assert stderr.getvalue() == "ritebook: error: Skills root missing\n"


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
