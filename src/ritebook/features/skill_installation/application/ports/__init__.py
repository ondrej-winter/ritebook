"""Application ports for skill installation workflows."""

from ritebook.features.skill_installation.application.ports import installation_manifest
from ritebook.features.skill_installation.application.ports.install_skill import (
    InstallSkillPort,
)
from ritebook.features.skill_installation.application.ports.skill_catalog import (
    SkillCatalogPort,
)
from ritebook.features.skill_installation.application.ports.skill_installer import (
    SkillInstallerPort,
)
from ritebook.features.skill_installation.application.ports.skill_source import (
    SkillSourcePort,
)

InstallationManifestPort = installation_manifest.InstallationManifestPort

__all__ = [
    "InstallSkillPort",
    "InstallationManifestPort",
    "SkillCatalogPort",
    "SkillInstallerPort",
    "SkillSourcePort",
]
