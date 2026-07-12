"""Publisher command handlers for the Ritebook CLI adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

from ritebook.features.publisher.application.dtos import (
    PublishIndexCommand,
    PublishIndexValidationError,
)
from ritebook.features.publisher.application.errors import PublisherError

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
    command = PublishIndexCommand(
        index_name=args.index_name,
        skills_root=args.skills_root,
    )
    try:
        result = publisher.execute(command)
    except PublishIndexValidationError as err:
        for issue in err.issues:
            print(issue.format(), file=stderr)
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
