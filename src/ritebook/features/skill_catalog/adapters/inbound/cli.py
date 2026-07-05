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
from ritebook.features.skill_catalog.application.dtos import PublishIndexCommand

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ritebook.features.skill_catalog.application.ports import PublishIndexPort

DEFAULT_OUTPUT_PATH = "ritebook-index.json"
PUBLISH_INDEX_COMMAND = "publish-index"


def run(
    argv: Sequence[str] | None,
    *,
    publisher: PublishIndexPort,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the Ritebook CLI with an injected publish-index application port."""
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    parser = _build_parser()

    try:
        with redirect_stderr(stderr):
            args = parser.parse_args(argv)
    except SystemExit as err:
        return _exit_code(err)

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
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output index path. Defaults to {DEFAULT_OUTPUT_PATH}.",
    )
    return parser


def _run_publish_index(
    args: argparse.Namespace,
    *,
    publisher: PublishIndexPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    command = PublishIndexCommand(
        skills_root=args.skills_root,
        output_path=args.output,
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
