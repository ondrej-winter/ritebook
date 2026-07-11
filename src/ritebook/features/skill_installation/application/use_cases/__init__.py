"""Application use cases for skill installation workflows."""

from ritebook.features.skill_installation.application.use_cases import (
    install_from_requirements,
)
from ritebook.features.skill_installation.application.use_cases.install_skill import (
    InstallSkill,
)

InstallFromRequirements = install_from_requirements.InstallFromRequirements

__all__ = ["InstallFromRequirements", "InstallSkill"]
