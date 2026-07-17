"""Command-line adapter for Ritebook application use cases."""

from __future__ import annotations

import sys
from contextlib import redirect_stderr, redirect_stdout
from typing import TYPE_CHECKING, TextIO

from ritebook.adapters.inbound.cli.parser import (
    ADD_INDEX_COMMAND,
    INSTALL_COMMAND,
    INSTALL_SKILL_COMMAND,
    LINT_SKILLS_COMMAND,
    LIST_INDEXES_COMMAND,
    LIST_SKILLS_COMMAND,
    PUBLISH_INDEX_COMMAND,
    UPDATE_INDEX_COMMAND,
    build_parser,
)
from ritebook.features.index_registry.adapters.inbound.cli import (
    run_add_index,
    run_list_indexes,
    run_list_skills,
    run_update_index,
)
from ritebook.features.linter.adapters.inbound.cli import run_lint_skills
from ritebook.features.publisher.adapters.inbound.cli import run_publish_index
from ritebook.features.skill_installation.adapters.inbound.cli import (
    run_install,
    run_install_skill,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ritebook.features.index_registry.application.ports import (
        AddIndexPort,
        ListIndexesPort,
        ListSkillsPort,
        UpdateIndexPort,
    )
    from ritebook.features.linter.application.ports import LintSkillsPort
    from ritebook.features.publisher.application.ports import PublishIndexPort
    from ritebook.features.skill_installation.application.ports import (
        InstallFromRequirementsPort,
        InstallSkillPort,
    )


def run(  # noqa: PLR0911, PLR0913
    argv: Sequence[str] | None,
    *,
    linter: LintSkillsPort,
    publisher: PublishIndexPort,
    add_index: AddIndexPort,
    list_indexes: ListIndexesPort,
    list_skills: ListSkillsPort,
    update_index: UpdateIndexPort,
    install_skill: InstallSkillPort,
    install_from_requirements: InstallFromRequirementsPort,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the Ritebook CLI with injected application ports."""
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    parser = build_parser()

    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
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

    if args.command == ADD_INDEX_COMMAND:
        return run_add_index(
            args,
            add_index=add_index,
            stdout=stdout,
            stderr=stderr,
        )

    if args.command == LIST_INDEXES_COMMAND:
        return run_list_indexes(
            args,
            list_indexes=list_indexes,
            stdout=stdout,
            stderr=stderr,
        )

    if args.command == LIST_SKILLS_COMMAND:
        return run_list_skills(
            args,
            list_skills=list_skills,
            stdout=stdout,
            stderr=stderr,
        )

    if args.command == UPDATE_INDEX_COMMAND:
        return run_update_index(
            args,
            update_index=update_index,
            stdout=stdout,
            stderr=stderr,
        )

    if args.command == INSTALL_SKILL_COMMAND:
        return run_install_skill(
            args,
            install_skill=install_skill,
            stdout=stdout,
            stderr=stderr,
        )

    if args.command == INSTALL_COMMAND:
        return run_install(
            args,
            install_from_requirements=install_from_requirements,
            stdout=stdout,
            stderr=stderr,
        )

    parser.print_help(file=stderr)
    return 2
