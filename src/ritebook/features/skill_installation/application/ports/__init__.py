"""Application ports for skill installation workflows."""

from ritebook.features.skill_installation.application.ports import (
    install_from_requirements,
    installation_manifest,
)
from ritebook.features.skill_installation.application.ports.install_skill import (
    InstallSkillPort,
)
from ritebook.features.skill_installation.application.ports.requirements_reader import (
    RequirementsReaderPort,
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

InstallFromRequirementsPort = install_from_requirements.InstallFromRequirementsPort
InstallationManifestPort = installation_manifest.InstallationManifestPort

__all__ = [
    "InstallFromRequirementsPort",
    "InstallSkillPort",
    "InstallationManifestPort",
    "RequirementsReaderPort",
    "SkillCatalogPort",
    "SkillInstallerPort",
    "SkillSourcePort",
]
