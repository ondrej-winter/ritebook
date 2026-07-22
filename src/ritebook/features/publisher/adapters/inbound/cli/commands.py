"""Publisher command handlers for the Ritebook CLI adapter."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from ritebook.features.publisher.application.dtos import (
    PublishIndexCommand,
    PublishIndexValidationError,
)
from ritebook.features.publisher.application.errors import PublisherError
from ritebook.shared_kernel import escape_terminal_control_characters

if TYPE_CHECKING:
    import argparse

    from ritebook.features.publisher.application.ports import PublishIndexPort


def run_publish_index(
    args: argparse.Namespace,
    *,
    publisher: PublishIndexPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Run the publish-index command against the injected application port."""
    try:
        command = _publish_command(args)
        result = publisher.execute(command)
    except PublishIndexValidationError as err:
        for issue in err.issues:
            print(escape_terminal_control_characters(issue.format()), file=stderr)
        return 1
    except (PublisherError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1

    print(
        "Published skill index with "
        f"{result.discovered_skill_count} skill(s) to {result.output_path}",
        file=stdout,
    )
    return 0


def _publish_command(args: argparse.Namespace) -> PublishIndexCommand:
    output_root = Path.cwd().resolve()
    skills_root = Path(args.skills_root).resolve()
    try:
        published_root = skills_root.relative_to(output_root)
    except ValueError as err:
        msg = "Skills root must be inside the index output directory."
        raise ValueError(msg) from err
    return PublishIndexCommand(
        index_name=args.index_name,
        skills_root=str(skills_root),
        published_skills_root=published_root.as_posix(),
    )
