"""CLI command handler exports grouped by feature family."""

from ritebook.adapters.inbound.cli.commands.index_registry import (
    run_add_index,
    run_list_indexes,
    run_list_skills,
    run_update_index,
)
from ritebook.adapters.inbound.cli.commands.installation import (
    run_install,
    run_install_skill,
)
from ritebook.adapters.inbound.cli.commands.linter import run_lint_skills
from ritebook.adapters.inbound.cli.commands.publisher import run_publish_index

__all__ = [
    "run_add_index",
    "run_install",
    "run_install_skill",
    "run_lint_skills",
    "run_list_indexes",
    "run_list_skills",
    "run_publish_index",
    "run_update_index",
]
