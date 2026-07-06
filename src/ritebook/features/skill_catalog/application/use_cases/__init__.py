"""Application use cases for skill catalog generation."""

from ritebook.features.skill_catalog.application.use_cases import validate_skill_headers
from ritebook.features.skill_catalog.application.use_cases.publish_index import (
    PublishIndex,
)

ValidateSkillHeaders = validate_skill_headers.ValidateSkillHeaders

__all__ = ["PublishIndex", "ValidateSkillHeaders"]
