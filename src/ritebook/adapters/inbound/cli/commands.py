"""Command handlers for the Ritebook CLI adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

from ritebook.features.index_registry.application.dtos import (
    AddIndexCommand,
    ListedIndexSkills,
    ListIndexesCommand,
    ListSkillsCommand,
    ListSkillsResult,
    UpdateIndexCommand,
)
from ritebook.features.index_registry.application.errors import IndexRegistryError
from ritebook.features.linter.application.dtos import LintSkillsCommand
from ritebook.features.linter.application.errors import LinterError
from ritebook.features.publisher.application.dtos import (
    PublishIndexCommand,
    PublishIndexValidationError,
)
from ritebook.features.publisher.application.errors import (
    PublisherError,
)
from ritebook.features.skill_installation.application.dtos import (
    InstallFromRequirementsCommand,
    InstallSkillCommand,
)
from ritebook.features.skill_installation.application.errors import (
    SkillInstallationError,
)

if TYPE_CHECKING:
    import argparse

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
    except (LinterError, ValueError) as err:
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
    except (PublisherError, ValueError) as err:
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
        all=args.all,
        registry_path=args.registry_path,
        cache_root=args.cache_root,
    )
    try:
        result = update_index.execute(command)
    except (IndexRegistryError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1
    if result.name is not None:
        print(
            f"Updated index {result.name} with {result.skill_count} skill(s)",
            file=stdout,
        )
        return 0
    print(
        "Updated "
        f"{len(result.updated_indexes)} index(es) with "
        f"{result.skill_count} total skill(s)",
        file=stdout,
    )
    if not result.failed_indexes:
        return 0
    print(
        "Failed to update "
        f"{len(result.failed_indexes)} index(es): "
        f"{', '.join(result.failed_indexes)}",
        file=stderr,
    )
    return 1


def run_list_indexes(
    args: argparse.Namespace,
    *,
    list_indexes: ListIndexesPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Run list-indexes against the injected application port."""
    command = ListIndexesCommand(registry_path=args.registry_path)
    try:
        result = list_indexes.execute(command)
    except (IndexRegistryError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1
    if not result.indexes:
        print("No indexes registered", file=stdout)
        return 0
    for index in result.indexes:
        print(
            f"{index.name}\t{index.skill_count} skill(s)\t"
            f"{index.source_type}\t{index.updated_at}\t{index.source}",
            file=stdout,
        )
    return 0


def run_list_skills(
    args: argparse.Namespace,
    *,
    list_skills: ListSkillsPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Run list-skills against the injected application port."""
    command = ListSkillsCommand(
        index_name=args.index_name,
        registry_path=args.registry_path,
        show_description=args.show_description,
    )
    try:
        result = list_skills.execute(command)
    except (IndexRegistryError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1
    if _total_skill_count(result) == 0:
        print("No skills found", file=stdout)
        return 0
    print(
        _render_skill_tree(result, show_description=command.show_description),
        file=stdout,
    )
    return 0


def run_install_skill(
    args: argparse.Namespace,
    *,
    install_skill: InstallSkillPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Run install-skill against the injected application port."""
    command = InstallSkillCommand(
        skill_reference=args.skill_reference,
        target=args.target,
        force=args.force,
        registry_path=args.registry_path,
        installation_registry_path=args.installation_registry_path,
    )
    try:
        result = install_skill.execute(command)
    except (SkillInstallationError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1
    print(f"Installed {result.requirement} to {result.target}", file=stdout)
    return 0


def run_install(
    args: argparse.Namespace,
    *,
    install_from_requirements: InstallFromRequirementsPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Run install against the injected requirements-install application port."""
    command = InstallFromRequirementsCommand(
        requirements_file=args.requirements_file,
        force=args.force,
        registry_path=args.registry_path,
        lockfile_path=args.lockfile,
    )
    try:
        result = install_from_requirements.execute(command)
    except (SkillInstallationError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1
    print(
        f"Installed {result.installed_count} skill(s) from {result.requirements_file}",
        file=stdout,
    )
    return 0


def _total_skill_count(result: ListSkillsResult) -> int:
    return sum(len(index.skills) for index in result.indexes)


def _render_skill_tree(result: ListSkillsResult, *, show_description: bool) -> str:
    lines = ["Indexes"]
    for index_position, index in enumerate(result.indexes):
        is_last_index = index_position == len(result.indexes) - 1
        index_connector = "└──" if is_last_index else "├──"
        lines.append(f"{index_connector} {index.index_name}")
        lines.extend(
            _render_skill_lines(
                index,
                is_last_index=is_last_index,
                show_description=show_description,
            ),
        )
    return "\n".join(lines)


def _render_skill_lines(
    index: ListedIndexSkills,
    *,
    is_last_index: bool,
    show_description: bool,
) -> list[str]:
    prefix = "    " if is_last_index else "│   "
    lines: list[str] = []
    for skill_position, skill in enumerate(index.skills):
        skill_connector = "└──" if skill_position == len(index.skills) - 1 else "├──"
        label = skill.name
        if show_description and skill.description is not None:
            label = f"{label} — {skill.description}"
        lines.append(f"{prefix}{skill_connector} {label}")
    return lines
