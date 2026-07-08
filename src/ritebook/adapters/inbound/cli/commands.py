"""Command handlers for the Ritebook CLI adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

from ritebook.adapters.outbound.filesystem import (
    FilesystemSkillDiscoveryError,
)
from ritebook.features.index_registry.application.dtos import (
    AddIndexCommand,
    UpdateIndexCommand,
)
from ritebook.features.index_registry.application.errors import IndexRegistryError
from ritebook.features.linter.application.dtos import LintSkillsCommand
from ritebook.features.publisher.adapters.outbound.json_index import (
    JsonIndexWriteError,
)
from ritebook.features.publisher.application.dtos import (
    PublishIndexCommand,
    PublishIndexValidationError,
)

if TYPE_CHECKING:
    import argparse

    from ritebook.features.index_registry.application.ports import (
        AddIndexPort,
        UpdateIndexPort,
    )
    from ritebook.features.linter.application.ports import LintSkillsPort
    from ritebook.features.publisher.application.ports import PublishIndexPort


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
    except (FilesystemSkillDiscoveryError, ValueError) as err:
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
    except (FilesystemSkillDiscoveryError, JsonIndexWriteError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1

    print(
        "Published skill index with "
        f"{result.discovered_skill_count} skill(s) to {result.output_path}",
        file=stdout,
    )
    return 0


def run_add_index(
    args: argparse.Namespace,
    *,
    add_index: AddIndexPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Run add-index against the injected application port."""
    command = AddIndexCommand(
        source=args.source,
        name=args.name,
        force=args.force,
        registry_path=args.registry_path,
        cache_root=args.cache_root,
    )
    try:
        result = add_index.execute(command)
    except (IndexRegistryError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1
    print(f"Added index {result.name} with {result.skill_count} skill(s)", file=stdout)
    return 0


def run_update_index(
    args: argparse.Namespace,
    *,
    update_index: UpdateIndexPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Run update-index against the injected application port."""
    command = UpdateIndexCommand(
        name=args.name,
        registry_path=args.registry_path,
        cache_root=args.cache_root,
    )
    try:
        result = update_index.execute(command)
    except (IndexRegistryError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1
    print(
        f"Updated index {result.name} with {result.skill_count} skill(s)",
        file=stdout,
    )
    return 0
