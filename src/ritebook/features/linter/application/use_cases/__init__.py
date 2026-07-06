"""Application use cases for skill linting."""

from ritebook.features.linter.application.use_cases import validate_skill_headers
from ritebook.features.linter.application.use_cases.lint_skills import LintSkills

ValidateSkillHeaders = validate_skill_headers.ValidateSkillHeaders

__all__ = ["LintSkills", "ValidateSkillHeaders"]
