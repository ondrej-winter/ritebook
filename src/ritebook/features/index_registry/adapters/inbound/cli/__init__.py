"""CLI command handlers for the index registry feature."""

from ritebook.features.index_registry.adapters.inbound.cli.commands import (
    run_add_index,
    run_list_indexes,
    run_list_skills,
    run_update_index,
)

__all__ = [
    "run_add_index",
    "run_list_indexes",
    "run_list_skills",
    "run_update_index",
]
