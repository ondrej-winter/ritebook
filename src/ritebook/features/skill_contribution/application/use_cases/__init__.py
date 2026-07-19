"""Application use cases for skill contribution workflows."""

from ritebook.features.skill_contribution.application.use_cases import (
    publish_skill_change,
)

PublishSkillChange = publish_skill_change.PublishSkillChange
PublishSkillChangeDependencies = publish_skill_change.PublishSkillChangeDependencies

__all__ = ["PublishSkillChange", "PublishSkillChangeDependencies"]
