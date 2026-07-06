"""Command handlers for the Ritebook CLI adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

from ritebook.adapters.outbound.filesystem import (
    FilesystemSkillDiscoveryError,
)
from ritebook.features.linter.application.dtos import LintSkillsCommand
from ritebook.features.publisher.adapters.outbound.json_index import (
    JsonIndexWriteError,
)
from ritebook.features.publisher.application.dtos import (
    PublishIndexCommand,
    PublishIndexValidationError,
)

if TYPE_CHECKING:
    import argparse

    from ritebook.features.linter.application.ports import LintSkillsPort
    from ritebook.features.publisher.application.ports import PublishIndexPort


def run_lint_skills(
    args: argparse.Namespace,
    *,
    linter: LintSkillsPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Run the lint-skills command against the injected application port."""
    command = LintSkillsCommand(
        skills_root=args.skills_root,
    )
    try:
        result = linter.execute(command)
    except (FilesystemSkillDiscoveryError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1

    if not result.succeeded:
        for issue in result.issues:
            print(issue.format(), file=stderr)
        return 1

    print(
        f"Validated {result.validated_skill_count} skill(s)",
        file=stdout,
    )
    return 0


def run_publish_index(
    args: argparse.Namespace,
    *,
    publisher: PublishIndexPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Run the publish-index command against the injected application port."""
    command = PublishIndexCommand(
        skills_root=args.skills_root,
    )
    try:
        result = publisher.execute(command)
    except PublishIndexValidationError as err:
        for issue in err.issues:
            print(issue.format(), file=stderr)
        return 1
    except (FilesystemSkillDiscoveryError, JsonIndexWriteError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1

    print(
        "Published skill index with "
        f"{result.discovered_skill_count} skill(s) to {result.output_path}",
        file=stdout,
    )
    return 0
