"""Command-line adapter for publisher skill index generation."""

from __future__ import annotations

import argparse
import sys
from contextlib import redirect_stderr
from typing import TYPE_CHECKING, TextIO

from ritebook.features.skill_catalog.adapters.outbound.filesystem import (
    FilesystemSkillDiscoveryError,
)
from ritebook.features.skill_catalog.adapters.outbound.json_index import (
    JsonIndexWriteError,
)
from ritebook.features.skill_catalog.application.dtos import (
    LintSkillsCommand,
    PublishIndexCommand,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ritebook.features.skill_catalog.application.ports import (
        LintSkillsPort,
        PublishIndexPort,
    )

LINT_SKILLS_COMMAND = "lint-skills"
PUBLISH_INDEX_COMMAND = "publish-index"


def run(
    argv: Sequence[str] | None,
    *,
    linter: LintSkillsPort,
    publisher: PublishIndexPort,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the Ritebook CLI with injected application ports."""
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    parser = _build_parser()

    try:
        with redirect_stderr(stderr):
            args = parser.parse_args(argv)
    except SystemExit as err:
        return _exit_code(err)

    if args.command == LINT_SKILLS_COMMAND:
        return _run_lint_skills(
            args,
            linter=linter,
            stdout=stdout,
            stderr=stderr,
        )

    if args.command == PUBLISH_INDEX_COMMAND:
        return _run_publish_index(
            args,
            publisher=publisher,
            stdout=stdout,
            stderr=stderr,
        )

    parser.print_help(file=stderr)
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ritebook")
    subparsers = parser.add_subparsers(dest="command", required=True)

    lint_skills = subparsers.add_parser(
        LINT_SKILLS_COMMAND,
        help="Validate discovered skill headers without writing an index.",
    )
    lint_skills.add_argument(
        "--skills-root",
        required=True,
        help="Explicit root directory to scan for SKILL.md files.",
    )

    publish_index = subparsers.add_parser(
        PUBLISH_INDEX_COMMAND,
        help="Generate a publisher skill index.",
    )
    publish_index.add_argument(
        "--skills-root",
        required=True,
        help="Explicit root directory to scan for SKILL.md files.",
    )
    return parser


def _run_lint_skills(
    args: argparse.Namespace,
    *,
    linter: LintSkillsPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
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


def _run_publish_index(
    args: argparse.Namespace,
    *,
    publisher: PublishIndexPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    command = PublishIndexCommand(
        skills_root=args.skills_root,
    )
    try:
        result = publisher.execute(command)
    except (FilesystemSkillDiscoveryError, JsonIndexWriteError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1

    print(
        "Published skill index with "
        f"{result.discovered_skill_count} skill(s) to {result.output_path}",
        file=stdout,
    )
    return 0


def _exit_code(err: SystemExit) -> int:
    if isinstance(err.code, int):
        return err.code
    return 1
