"""JSON lockfile adapter exports."""

from ritebook.features.skill_installation.adapters.outbound.json_lockfile import adapter

JsonLockfileAdapter = adapter.JsonLockfileAdapter

__all__ = ["JsonLockfileAdapter"]
