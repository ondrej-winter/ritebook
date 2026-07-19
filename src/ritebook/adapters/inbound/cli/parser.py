"""Argument parser construction for the Ritebook CLI adapter."""

from __future__ import annotations

import argparse

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
    publish_index.add_argument(
        "--index-name",
        required=True,
        help="Stable kebab-case name to publish in ritebook-index.json metadata.",
    )

    add_index = subparsers.add_parser(
        ADD_INDEX_COMMAND,
        help="Register a Git-backed skill index.",
    )
    add_index.add_argument("--source", required=True, help="Git URL or local Git repo.")
    add_index.add_argument("--name", help="Local effective index name override.")
    add_index.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing index with the same effective name.",
    )
    add_index.add_argument("--registry-path", help="Path to indexes.json registry.")
    add_index.add_argument(
        "--cache-root",
        help="Root directory for Ritebook cache files.",
    )

    list_indexes = subparsers.add_parser(
        LIST_INDEXES_COMMAND,
        help="List registered skill indexes.",
    )
    list_indexes.add_argument("--registry-path", help="Path to indexes.json registry.")

    list_skills = subparsers.add_parser(
        LIST_SKILLS_COMMAND,
        help="List skills from registered cached indexes.",
    )
    list_skills.add_argument("--index-name", help="Effective index name to list.")
    list_skills.add_argument("--registry-path", help="Path to indexes.json registry.")
    list_skills.add_argument(
        "--show-description",
        action="store_true",
        help="Show skill descriptions when cached index metadata includes them.",
    )

    update_index = subparsers.add_parser(
        UPDATE_INDEX_COMMAND,
        help="Refresh a registered skill index.",
    )
    update_target = update_index.add_mutually_exclusive_group(required=True)
    update_target.add_argument("--name", help="Effective index name.")
    update_target.add_argument(
        "--all",
        action="store_true",
        help="Refresh all registered indexes and continue after per-index failures.",
    )
    update_index.add_argument("--registry-path", help="Path to indexes.json registry.")
    update_index.add_argument(
        "--cache-root",
        help="Root directory for Ritebook cache files.",
    )

    install_skill = subparsers.add_parser(
        INSTALL_SKILL_COMMAND,
        help="Install one cached skill into an explicit target path.",
    )
    install_skill.add_argument(
        "skill_reference",
        help="Fully qualified skill reference as <index-name>/<skill-name>.",
    )
    install_skill.add_argument(
        "--target",
        required=True,
        help="Explicit target path where the skill directory will be installed.",
    )
    install_skill.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing target path and recorded installation entry.",
    )
    install_skill.add_argument("--registry-path", help="Path to indexes.json registry.")
    install_skill.add_argument(
        "--installation-registry-path",
        help="Path to generated direct-install installations.json state.",
    )

    install = subparsers.add_parser(
        INSTALL_COMMAND,
        help="Install skills declared in a ritebook.toml requirements file.",
    )
    install.add_argument(
        "--file",
        default="ritebook.toml",
        dest="requirements_file",
        help="Path to the requirements TOML file. Defaults to ritebook.toml.",
    )
    install.add_argument(
        "--force",
        action="store_true",
        help="Replace existing target paths during requirements installation.",
    )
    install.add_argument("--registry-path", help="Path to indexes.json registry.")
    install.add_argument(
        "--lockfile",
        help="Path to generated ritebook.lock state.",
    )

    publish_skill_change = subparsers.add_parser(
        PUBLISH_SKILL_CHANGE_COMMAND,
        help="Prepare one installed skill change for upstream review.",
    )
    publish_skill_change.add_argument(
        "skill_reference",
        help="Fully qualified skill reference as <index-name>/<skill-path-or-name>.",
    )
    publish_skill_change.add_argument(
        "--lockfile",
        help="Path to ritebook.lock. Defaults to ritebook.lock.",
    )
    publish_skill_change.add_argument(
        "--contribution-root",
        help="Root for Ritebook-owned isolated contribution checkouts.",
    )
    return parser
