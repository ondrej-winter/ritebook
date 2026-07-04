"""Filesystem skill discovery adapter."""

from ritebook.features.skill_catalog.adapters.outbound.filesystem.adapter import (
    FilesystemSkillDiscovery,
)
from ritebook.features.skill_catalog.adapters.outbound.filesystem.exceptions import (
    FilesystemSkillDiscoveryError,
    SkillFileReadError,
    SkillsRootNotDirectoryError,
    SkillsRootNotFoundError,
)

__all__ = [
    "FilesystemSkillDiscovery",
    "FilesystemSkillDiscoveryError",
    "SkillFileReadError",
    "SkillsRootNotDirectoryError",
    "SkillsRootNotFoundError",
]
