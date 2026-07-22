"""Index registry command handlers for the Ritebook CLI adapter."""

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
from ritebook.shared_kernel import (
    escape_terminal_control_characters,
    safe_source_display,
)

if TYPE_CHECKING:
    import argparse

    from ritebook.features.index_registry.application.ports import (
        AddIndexPort,
        ListIndexesPort,
        ListSkillsPort,
        UpdateIndexPort,
    )


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
        alias=args.alias,
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
        display_source = escape_terminal_control_characters(
            safe_source_display(index.source, index.source_type),
        )
        print(
            f"{index.name}\t{index.skill_count} skill(s)\t"
            f"{index.source_type}\t{index.updated_at}\t{display_source}",
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
        label = skill.path
        if show_description:
            description = escape_terminal_control_characters(skill.description)
            label = f"{label} — {description}"
        lines.append(f"{prefix}{skill_connector} {label}")
    return lines
