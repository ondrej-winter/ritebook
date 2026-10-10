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
    parser = argparse.ArgumentParser(
        prog="ritebook",
        description="Manage Agent Skills and published skill indexes.",
        epilog="Run 'ritebook <group> <command> --help' for command-specific help.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    commands = parser.add_subparsers(
        dest="command_group",
        required=True,
        metavar="{skills,indexes}",
    )
    _add_commands(commands)
    return parser


def _add_commands(commands: argparse._SubParsersAction) -> None:
    skills = commands.add_parser(
        "skills",
        help="Manage skills and skill workflows.",
        description="Validate, browse, install, synchronize, and contribute skills.",
    )
    skill_commands = skills.add_subparsers(
        dest="skill_command",
        required=True,
        metavar="{lint,list,install,sync,contribute}",
    )
    _add_lint_skills_parser(skill_commands)
    _add_list_skills_parser(skill_commands)
    _add_install_skill_parser(skill_commands)
    _add_install_parser(skill_commands)
    _add_publish_skill_change_parser(skill_commands)

    indexes = commands.add_parser(
        "indexes",
        help="Manage published skill indexes.",
        description="Publish, register, inspect, and refresh skill indexes.",
    )
    index_commands = indexes.add_subparsers(
        dest="index_command",
        required=True,
        metavar="{publish,add,list,update}",
    )
    _add_publish_index_parser(index_commands)
    _add_add_index_parser(index_commands)
    _add_list_indexes_parser(index_commands)
    _add_update_index_parser(index_commands)


def _add_lint_skills_parser(
    commands: argparse._SubParsersAction,
) -> None:
    parser = commands.add_parser(
        "lint",
        help="Validate skill headers.",
        description="Validate every discovered SKILL.md below an explicit root.",
    )
    _set_command_default(parser, LINT_SKILLS_COMMAND)
    parser.add_argument(
        "--root",
        dest="skills_root",
        required=True,
        metavar="PATH",
        help="Explicit root directory to scan for SKILL.md files.",
    )


def _add_publish_index_parser(
    commands: argparse._SubParsersAction,
) -> None:
    parser = commands.add_parser(
        "publish",
        help="Generate a publisher skill index.",
        description=("Validate skills and write ritebook-index.json in the current directory."),
    )
    _set_command_default(parser, PUBLISH_INDEX_COMMAND)
    parser.add_argument(
        "--skills-root",
        required=True,
        metavar="PATH",
        help="Root directory to scan; it must be inside the output directory.",
    )
    parser.add_argument(
        "--name",
        dest="index_name",
        required=True,
        metavar="NAME",
        help="Stable kebab-case name for ritebook-index.json metadata.",
    )


def _add_add_index_parser(
    commands: argparse._SubParsersAction,
) -> None:
    parser = commands.add_parser(
        "add",
        help="Register a Git-backed skill index.",
        description="Register and cache an index from a Git URL or local repository.",
    )
    _set_command_default(parser, ADD_INDEX_COMMAND)
    parser.add_argument(
        "--source",
        required=True,
        metavar="GIT_SOURCE",
        help="Git URL or local Git repository path.",
    )
    parser.add_argument("--alias", metavar="ALIAS", help="Local index namespace.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing alias.",
    )
    parser.add_argument(
        "--registry-path",
        metavar="PATH",
        help="Override the indexes.json registry path.",
    )
    parser.add_argument(
        "--cache-root",
        metavar="PATH",
        help="Override the Ritebook cache root.",
    )


def _add_list_indexes_parser(
    commands: argparse._SubParsersAction,
) -> None:
    parser = commands.add_parser("list", help="List registered skill indexes.")
    _set_command_default(parser, LIST_INDEXES_COMMAND)
    parser.add_argument(
        "--registry-path",
        metavar="PATH",
        help="Override the indexes.json registry path.",
    )


def _add_list_skills_parser(
    commands: argparse._SubParsersAction,
) -> None:
    parser = commands.add_parser(
        "list",
        help="List skills from cached indexes.",
        description="Browse skills from locally cached registered indexes.",
    )
    _set_command_default(parser, LIST_SKILLS_COMMAND)
    parser.add_argument(
        "--index",
        dest="index_name",
        metavar="ALIAS",
        help="Limit results to one local index alias.",
    )
    parser.add_argument(
        "--registry-path",
        metavar="PATH",
        help="Override the indexes.json registry path.",
    )
    parser.add_argument(
        "--show-description",
        action="store_true",
        help="Append cached skill descriptions to the output.",
    )


def _add_update_index_parser(
    commands: argparse._SubParsersAction,
) -> None:
    parser = commands.add_parser(
        "update",
        help="Refresh registered skill indexes.",
        description="Refresh one registered index or all registered indexes.",
    )
    _set_command_default(parser, UPDATE_INDEX_COMMAND)
    parser.set_defaults(requires_update_target=True)
    parser.add_argument("name", nargs="?", metavar="ALIAS", help="Local index alias.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Refresh all registered indexes.",
    )
    parser.add_argument(
        "--registry-path",
        metavar="PATH",
        help="Override the indexes.json registry path.",
    )
    parser.add_argument(
        "--cache-root",
        metavar="PATH",
        help="Override the Ritebook cache root.",
    )


def _add_install_skill_parser(
    commands: argparse._SubParsersAction,
) -> None:
    parser = commands.add_parser(
        "install",
        help="Install one cached skill.",
        description=("Install one exact skill reference into an explicit target directory."),
    )
    _set_command_default(parser, INSTALL_SKILL_COMMAND)
    parser.add_argument(
        "skill_reference",
        metavar="SKILL",
        help="Fully qualified <local-alias>/<skill-path> reference.",
    )
    parser.add_argument(
        "--target",
        required=True,
        metavar="PATH",
        help="Target skill directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an unchanged Ritebook-owned target.",
    )
    parser.add_argument(
        "--registry-path",
        metavar="PATH",
        help="Override the indexes.json registry path.",
    )
    parser.add_argument(
        "--installation-registry-path",
        metavar="PATH",
        help="Override the generated installations.json state path.",
    )


def _add_install_parser(
    commands: argparse._SubParsersAction,
) -> None:
    parser = commands.add_parser(
        "sync",
        help="Reconcile skills declared in ritebook.toml.",
        description=("Exactly reconcile skills declared in a Ritebook requirements file."),
    )
    _set_command_default(parser, INSTALL_COMMAND)
    parser.add_argument(
        "--file",
        default="ritebook.toml",
        dest="requirements_file",
        metavar="PATH",
        help="Requirements file to read (default: ritebook.toml).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rematerialize unchanged Ritebook-owned desired targets.",
    )
    parser.add_argument(
        "--registry-path",
        metavar="PATH",
        help="Override the indexes.json registry path.",
    )
    parser.add_argument(
        "--lockfile",
        metavar="PATH",
        help="Override the generated ritebook.lock path.",
    )


def _add_publish_skill_change_parser(
    commands: argparse._SubParsersAction,
) -> None:
    parser = commands.add_parser(
        "contribute",
        help="Prepare one installed skill change for review.",
        description="Prepare a reviewable branch and commit for one installed skill.",
    )
    _set_command_default(parser, PUBLISH_SKILL_CHANGE_COMMAND)
    parser.add_argument(
        "skill_reference",
        metavar="SKILL",
        help="Fully qualified <local-alias>/<skill-path> reference.",
    )
    parser.add_argument(
        "--lockfile",
        metavar="PATH",
        help="Override the ritebook.lock path.",
    )
    parser.add_argument(
        "--contribution-root",
        metavar="PATH",
        help="Override the root for isolated contribution checkouts.",
    )


def _set_command_default(
    parser: argparse.ArgumentParser,
    command: str,
) -> None:
    parser.set_defaults(command=command)
