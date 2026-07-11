"""TOML requirements reader adapter exports."""

from ritebook.features.skill_installation.adapters.outbound.toml_requirements import (
    reader,
)

TomlRequirementsReader = reader.TomlRequirementsReader

__all__ = ["TomlRequirementsReader"]
