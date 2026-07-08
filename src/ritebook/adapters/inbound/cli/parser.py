"""Argument parser construction for the Ritebook CLI adapter."""

from __future__ import annotations

import argparse

LINT_SKILLS_COMMAND = "lint-skills"
PUBLISH_INDEX_COMMAND = "publish-index"
ADD_INDEX_COMMAND = "add-index"
UPDATE_INDEX_COMMAND = "update-index"


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

    update_index = subparsers.add_parser(
        UPDATE_INDEX_COMMAND,
        help="Refresh a registered skill index.",
    )
    update_index.add_argument("--name", required=True, help="Effective index name.")
    update_index.add_argument("--registry-path", help="Path to indexes.json registry.")
    update_index.add_argument(
        "--cache-root",
        help="Root directory for Ritebook cache files.",
    )
    return parser
