"""Filesystem skill discovery adapter."""

from ritebook.features.skill_catalog.adapters.outbound.filesystem.adapter import (
    FilesystemSkillDiscovery,
    FilesystemSkillHeaderDiscovery,
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
    "FilesystemSkillHeaderDiscovery",
    "SkillFileReadError",
    "SkillsRootNotDirectoryError",
    "SkillsRootNotFoundError",
]
