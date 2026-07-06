"""Validate-skill-headers use case package."""

from ritebook.features.linter.application.use_cases.validate_skill_headers import (
    service,
)

ValidateSkillHeaders = service.ValidateSkillHeaders

__all__ = ["ValidateSkillHeaders"]
