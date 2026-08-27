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
    PUBLISH_SKILL_CHANGE_COMMAND,
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
from ritebook.features.skill_contribution.adapters.inbound.cli import (
    run_publish_skill_change,
)
from ritebook.features.skill_installation.adapters.inbound.cli import (
    run_install,
    run_install_skill,
)

if TYPE_CHECKING:
    import argparse
    from collections.abc import Sequence

    from ritebook.features.index_registry.application.ports import (
        AddIndexPort,
        ListIndexesPort,
        ListSkillsPort,
        UpdateIndexPort,
    )
    from ritebook.features.linter.application.ports import LintSkillsPort
    from ritebook.features.publisher.application.ports import PublishIndexPort
    from ritebook.features.skill_contribution.application.ports import (
        PublishSkillChangePort,
    )
    from ritebook.features.skill_installation.application.ports import (
        InstallFromRequirementsPort,
        InstallSkillPort,
    )


def run(  # noqa: PLR0913
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
    publish_skill_change: PublishSkillChangePort | None = None,
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

    target_validation_exit_code = _validate_update_target(
        args,
        parser=parser,
        stderr=stderr,
    )
    if target_validation_exit_code is not None:
        return target_validation_exit_code

    _print_deprecation_warning(args, stderr=stderr)
    return _dispatch(
        args,
        parser=parser,
        linter=linter,
        publisher=publisher,
        add_index=add_index,
        list_indexes=list_indexes,
        list_skills=list_skills,
        update_index=update_index,
        install_skill=install_skill,
        install_from_requirements=install_from_requirements,
        publish_skill_change=publish_skill_change,
        stdout=stdout,
        stderr=stderr,
    )


def _dispatch(  # noqa: C901, PLR0911, PLR0913
    args: argparse.Namespace,
    *,
    parser: argparse.ArgumentParser,
    linter: LintSkillsPort,
    publisher: PublishIndexPort,
    add_index: AddIndexPort,
    list_indexes: ListIndexesPort,
    list_skills: ListSkillsPort,
    update_index: UpdateIndexPort,
    install_skill: InstallSkillPort,
    install_from_requirements: InstallFromRequirementsPort,
    publish_skill_change: PublishSkillChangePort | None,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Dispatch parsed command arguments to their feature-owned CLI handlers."""
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

    if args.command == PUBLISH_SKILL_CHANGE_COMMAND:
        if publish_skill_change is None:
            print(
                "ritebook: error: publish-skill-change is not configured",
                file=stderr,
            )
            return 1
        return run_publish_skill_change(
            args,
            publish_skill_change=publish_skill_change,
            stdout=stdout,
            stderr=stderr,
        )

    parser.print_help(file=stderr)
    return 2


def _deprecation_warning(command: str) -> str:
    replacements = {
        LINT_SKILLS_COMMAND: "skills lint",
        PUBLISH_INDEX_COMMAND: "indexes publish",
        ADD_INDEX_COMMAND: "indexes add",
        LIST_INDEXES_COMMAND: "indexes list",
        LIST_SKILLS_COMMAND: "skills list",
        UPDATE_INDEX_COMMAND: "indexes update",
        INSTALL_SKILL_COMMAND: "skills install",
        INSTALL_COMMAND: "skills sync",
        PUBLISH_SKILL_CHANGE_COMMAND: "skills contribute",
    }
    replacement = replacements[command]
    return f"ritebook: warning: '{command}' is deprecated; use '{replacement}'"


def _print_deprecation_warning(args: argparse.Namespace, *, stderr: TextIO) -> None:
    if args.deprecated_command is not None:
        print(_deprecation_warning(args.deprecated_command), file=stderr)


def _validate_update_target(
    args: object,
    *,
    parser: argparse.ArgumentParser,
    stderr: TextIO,
) -> int | None:
    if not getattr(args, "requires_update_target", False):
        return None
    name = getattr(args, "name", None)
    update_all = getattr(args, "all", False)
    if (name is not None) != update_all:
        return None

    try:
        with redirect_stderr(stderr):
            parser.error("provide exactly one of <local-alias> or --all")
    except SystemExit as err:
        return err.code if isinstance(err.code, int) else 1
