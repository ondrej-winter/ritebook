"""Bridge committed installation snapshots to the single-file linter API."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ritebook.features.skill_installation.application.dtos import (
    CommittedSkillHeader,
)
from ritebook.features.skill_installation.application.errors import (
    CommittedSkillValidationError,
)
from ritebook.features.skill_linter.application.dtos import ValidateSkillFileCommand
from ritebook.features.skill_linter.application.errors import LinterError
from ritebook.shared_kernel import validate_portable_relative_posix_path

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        InstallableSkill,
        ResolvedSkillSource,
    )
    from ritebook.features.skill_linter.application.ports import ValidateSkillFilePort


class LinterCommittedSkillValidatorAdapter:
    """Validate selected committed headers through the linter application API."""

    def __init__(self, *, validator: ValidateSkillFilePort) -> None:
        """Initialize the adapter with the published single-file linter boundary."""
        self._validator = validator

    def validate(
        self,
        source: ResolvedSkillSource,
        skill: InstallableSkill,
    ) -> CommittedSkillHeader:
        """Validate one exact committed ``SKILL.md`` and map its normalized values."""
        try:
            source_root = validate_portable_relative_posix_path(
                skill.source_root,
                field_name="skill source root",
                allow_current_directory=True,
            )
            skill_file = validate_portable_relative_posix_path(
                skill.skill_file,
                field_name="skill file",
            )
        except ValueError as err:
            raise _validation_error() from err

        try:
            result = self._validator.execute(
                ValidateSkillFileCommand(
                    skill_file=str(
                        Path(source.repository_path).joinpath(
                            *source_root.parts,
                            *skill_file.parts,
                        ),
                    ),
                    expected_name=skill.name,
                ),
            )
        except LinterError as err:
            raise _validation_error() from err
        if not result.succeeded or result.validated_skill is None:
            raise _validation_error()
        return CommittedSkillHeader(
            name=result.validated_skill.name,
            description=result.validated_skill.description,
        )


def _validation_error() -> CommittedSkillValidationError:
    return CommittedSkillValidationError("committed skill header validation failed")
