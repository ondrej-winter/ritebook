"""Lint command handlers for the Ritebook CLI adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

from ritebook.features.linter.application.dtos import LintSkillsCommand
from ritebook.features.linter.application.errors import LinterError

if TYPE_CHECKING:
    import argparse

    from ritebook.features.linter.application.ports import LintSkillsPort


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
    except (LinterError, ValueError) as err:
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
