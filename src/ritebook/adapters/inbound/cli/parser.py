"""Argument parser construction for the Ritebook CLI adapter."""

from __future__ import annotations

import argparse

from ritebook import __version__

LINT_SKILLS_COMMAND = "lint-skills"
PUBLISH_INDEX_COMMAND = "publish-index"
ADD_INDEX_COMMAND = "add-index"
LIST_INDEXES_COMMAND = "list-indexes"
LIST_SKILLS_COMMAND = "list-skills"
UPDATE_INDEX_COMMAND = "update-index"
INSTALL_SKILL_COMMAND = "install-skill"
INSTALL_COMMAND = "install"
PUBLISH_SKILL_CHANGE_COMMAND = "publish-skill-change"


def build_parser() -> argparse.ArgumentParser:
    """Build the Ritebook command-line argument parser."""
    parser = argparse.ArgumentParser(prog="ritebook")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    _add_canonical_commands(commands)
    _add_legacy_commands(commands)
    return parser


def _add_canonical_commands(commands: argparse._SubParsersAction) -> None:
    skills = commands.add_parser("skills", help="Manage skills and skill workflows.")
    skill_commands = skills.add_subparsers(dest="skill_command", required=True)
    _add_lint_skills_parser(skill_commands, name="lint", canonical=True)
    _add_list_skills_parser(skill_commands, name="list", canonical=True)
    _add_install_skill_parser(skill_commands, name="install", canonical=True)
    _add_install_parser(skill_commands, name="sync", canonical=True)
    _add_publish_skill_change_parser(skill_commands, name="contribute", canonical=True)

    indexes = commands.add_parser("indexes", help="Manage published skill indexes.")
    index_commands = indexes.add_subparsers(dest="index_command", required=True)
    _add_publish_index_parser(index_commands, name="publish", canonical=True)
    _add_add_index_parser(index_commands, name="add", canonical=True)
    _add_list_indexes_parser(index_commands, name="list", canonical=True)
    _add_update_index_parser(index_commands, name="update", canonical=True)


def _add_legacy_commands(commands: argparse._SubParsersAction) -> None:
    _add_lint_skills_parser(commands, name=LINT_SKILLS_COMMAND, canonical=False)
    _add_publish_index_parser(commands, name=PUBLISH_INDEX_COMMAND, canonical=False)
    _add_add_index_parser(commands, name=ADD_INDEX_COMMAND, canonical=False)
    _add_list_indexes_parser(commands, name=LIST_INDEXES_COMMAND, canonical=False)
    _add_list_skills_parser(commands, name=LIST_SKILLS_COMMAND, canonical=False)
    _add_update_index_parser(commands, name=UPDATE_INDEX_COMMAND, canonical=False)
    _add_install_skill_parser(commands, name=INSTALL_SKILL_COMMAND, canonical=False)
    _add_install_parser(commands, name=INSTALL_COMMAND, canonical=False)
    _add_publish_skill_change_parser(
        commands,
        name=PUBLISH_SKILL_CHANGE_COMMAND,
        canonical=False,
    )


def _add_lint_skills_parser(
    commands: argparse._SubParsersAction,
    *,
    name: str,
    canonical: bool,
) -> None:
    parser = commands.add_parser(name, help="Validate skill headers.")
    _set_command_defaults(parser, LINT_SKILLS_COMMAND, canonical=canonical)
    option_names = ("--root", "--skills-root") if canonical else ("--skills-root",)
    parser.add_argument(
        *option_names,
        dest="skills_root",
        required=True,
        help="Explicit root directory to scan for SKILL.md files.",
    )


def _add_publish_index_parser(
    commands: argparse._SubParsersAction,
    *,
    name: str,
    canonical: bool,
) -> None:
    parser = commands.add_parser(name, help="Generate a publisher skill index.")
    _set_command_defaults(parser, PUBLISH_INDEX_COMMAND, canonical=canonical)
    parser.add_argument(
        "--skills-root",
        required=True,
        help="Root directory to scan; it must be inside the output directory.",
    )
    option_names = ("--name", "--index-name") if canonical else ("--index-name",)
    parser.add_argument(
        *option_names,
        dest="index_name",
        required=True,
        help="Stable kebab-case name for ritebook-index.json metadata.",
    )


def _add_add_index_parser(
    commands: argparse._SubParsersAction,
    *,
    name: str,
    canonical: bool,
) -> None:
    parser = commands.add_parser(name, help="Register a Git-backed skill index.")
    _set_command_defaults(parser, ADD_INDEX_COMMAND, canonical=canonical)
    parser.add_argument("--source", required=True, help="Git URL or local Git repo.")
    parser.add_argument("--alias", help="Local index namespace.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing alias.",
    )
    parser.add_argument("--registry-path", help="Path to indexes.json registry.")
    parser.add_argument("--cache-root", help="Root directory for Ritebook cache files.")


def _add_list_indexes_parser(
    commands: argparse._SubParsersAction,
    *,
    name: str,
    canonical: bool,
) -> None:
    parser = commands.add_parser(name, help="List registered skill indexes.")
    _set_command_defaults(parser, LIST_INDEXES_COMMAND, canonical=canonical)
    parser.add_argument("--registry-path", help="Path to indexes.json registry.")


def _add_list_skills_parser(
    commands: argparse._SubParsersAction,
    *,
    name: str,
    canonical: bool,
) -> None:
    parser = commands.add_parser(name, help="List skills from cached indexes.")
    _set_command_defaults(parser, LIST_SKILLS_COMMAND, canonical=canonical)
    option_names = ("--index", "--index-name") if canonical else ("--index-name",)
    parser.add_argument(*option_names, dest="index_name")
    parser.add_argument("--registry-path", help="Path to indexes.json registry.")
    parser.add_argument("--show-description", action="store_true")


def _add_update_index_parser(
    commands: argparse._SubParsersAction,
    *,
    name: str,
    canonical: bool,
) -> None:
    parser = commands.add_parser(name, help="Refresh registered skill indexes.")
    _set_command_defaults(parser, UPDATE_INDEX_COMMAND, canonical=canonical)
    if canonical:
        parser.set_defaults(requires_update_target=True)
        parser.add_argument("name", nargs="?", help="Local index alias.")
        parser.add_argument("--name", help=argparse.SUPPRESS)
        parser.add_argument(
            "--all",
            action="store_true",
            help="Refresh all registered indexes.",
        )
    else:
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--name", help="Local index alias.")
        target.add_argument(
            "--all",
            action="store_true",
            help="Refresh all registered indexes.",
        )
    parser.add_argument("--registry-path", help="Path to indexes.json registry.")
    parser.add_argument("--cache-root", help="Root directory for Ritebook cache files.")


def _add_install_skill_parser(
    commands: argparse._SubParsersAction,
    *,
    name: str,
    canonical: bool,
) -> None:
    parser = commands.add_parser(name, help="Install one cached skill.")
    _set_command_defaults(parser, INSTALL_SKILL_COMMAND, canonical=canonical)
    parser.add_argument("skill_reference", help="Fully qualified skill reference.")
    parser.add_argument("--target", required=True, help="Target skill directory.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing target.",
    )
    parser.add_argument("--registry-path", help="Path to indexes.json registry.")
    parser.add_argument(
        "--installation-registry-path",
        help="Path to installations.json state.",
    )


def _add_install_parser(
    commands: argparse._SubParsersAction,
    *,
    name: str,
    canonical: bool,
) -> None:
    parser = commands.add_parser(name, help="Install skills declared in ritebook.toml.")
    _set_command_defaults(parser, INSTALL_COMMAND, canonical=canonical)
    parser.add_argument("--file", default="ritebook.toml", dest="requirements_file")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing targets.",
    )
    parser.add_argument("--registry-path", help="Path to indexes.json registry.")
    parser.add_argument("--lockfile", help="Path to generated ritebook.lock state.")


def _add_publish_skill_change_parser(
    commands: argparse._SubParsersAction,
    *,
    name: str,
    canonical: bool,
) -> None:
    parser = commands.add_parser(
        name,
        help="Prepare one installed skill change for review.",
    )
    _set_command_defaults(parser, PUBLISH_SKILL_CHANGE_COMMAND, canonical=canonical)
    parser.add_argument("skill_reference", help="Fully qualified skill reference.")
    parser.add_argument("--lockfile", help="Path to ritebook.lock.")
    parser.add_argument("--contribution-root", help="Root for contribution checkouts.")


def _set_command_defaults(
    parser: argparse.ArgumentParser,
    command: str,
    *,
    canonical: bool,
) -> None:
    parser.set_defaults(
        command=command,
        deprecated_command=None if canonical else command,
    )
