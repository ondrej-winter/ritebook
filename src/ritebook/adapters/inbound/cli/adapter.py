"""Command-line adapter for publisher skill index generation."""

from __future__ import annotations

import sys
from contextlib import redirect_stderr
from typing import TYPE_CHECKING, TextIO

from ritebook.adapters.inbound.cli.commands import run_lint_skills, run_publish_index
from ritebook.adapters.inbound.cli.parser import (
    LINT_SKILLS_COMMAND,
    PUBLISH_INDEX_COMMAND,
    build_parser,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ritebook.features.linter.application.ports import LintSkillsPort
    from ritebook.features.publisher.application.ports import PublishIndexPort


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
    parser = build_parser()

    try:
        with redirect_stderr(stderr):
            args = parser.parse_args(argv)
    except SystemExit as err:
        return err.code if isinstance(err.code, int) else 1

    if args.command == LINT_SKILLS_COMMAND:
        return run_lint_skills(
            args,
            linter=linter,
            stdout=stdout,
            stderr=stderr,
        )

    if args.command == PUBLISH_INDEX_COMMAND:
        return run_publish_index(
            args,
            publisher=publisher,
            stdout=stdout,
            stderr=stderr,
        )

    parser.print_help(file=stderr)
    return 2
