"""Application use case for validating one explicit skill file."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ritebook.features.skill_linter.application.dtos import (
    SkillValidationIssue,
    ValidatedSkillFile,
    ValidateSkillFileCommand,
    ValidateSkillFileResult,
)
from ritebook.features.skill_linter.application.ports import ValidateSkillFilePort

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ritebook.features.skill_linter.application.ports import SkillHeaderReaderPort
    from ritebook.features.skill_linter.application.use_cases import (
        ValidateSkillHeaders,
    )


class ValidateSkillFile(ValidateSkillFilePort):
    """Parse and validate one explicit ``SKILL.md`` file."""

    def __init__(
        self,
        *,
        header_reader: SkillHeaderReaderPort,
        header_validator: ValidateSkillHeaders,
    ) -> None:
        """Initialize the use case with parsing and pure validation dependencies."""
        self._header_reader = header_reader
        self._header_validator = header_validator

    def execute(self, command: ValidateSkillFileCommand) -> ValidateSkillFileResult:
        """Return normalized portable header values or deterministic issues."""
        parsed = self._header_reader.read_header(
            command.skill_file,
            command.expected_name,
        )
        if isinstance(parsed, SkillValidationIssue):
            return ValidateSkillFileResult(issues=(parsed,))

        report = self._header_validator.execute((parsed,))
        if report.issues:
            return ValidateSkillFileResult(issues=report.issues)

        frontmatter = cast("Mapping[object, object]", parsed.frontmatter)
        return ValidateSkillFileResult(
            validated_skill=ValidatedSkillFile(
                name=cast("str", frontmatter["name"]),
                description=cast("str", frontmatter["description"]).strip(),
            ),
        )
