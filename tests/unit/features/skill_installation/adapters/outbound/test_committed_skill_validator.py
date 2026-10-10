from pathlib import Path

import pytest

from ritebook.features.skill_installation.adapters.outbound import (
    LinterCommittedSkillValidatorAdapter,
)
from ritebook.features.skill_installation.application.dtos import ResolvedSkillSource
from ritebook.features.skill_installation.application.errors import (
    CommittedSkillValidationError,
)
from ritebook.features.skill_linter.application.dtos import (
    SkillValidationIssue,
    ValidatedSkillFile,
    ValidateSkillFileCommand,
    ValidateSkillFileResult,
)
from tests.unit.features.skill_installation.application.fakes import installable_skill


class FakeSkillFileValidator:
    def __init__(self, result: ValidateSkillFileResult) -> None:
        self.result = result
        self.commands: list[ValidateSkillFileCommand] = []

    def execute(self, command: ValidateSkillFileCommand) -> ValidateSkillFileResult:
        self.commands.append(command)
        return self.result


def test_committed_skill_validator_maps_validated_snapshot_header(
    tmp_path: Path,
) -> None:
    linter = FakeSkillFileValidator(
        ValidateSkillFileResult(
            validated_skill=ValidatedSkillFile(
                name="code-review",
                description="Helps review code.",
            ),
        ),
    )
    source = resolved_source(tmp_path / "snapshot")
    adapter = LinterCommittedSkillValidatorAdapter(validator=linter)

    result = adapter.validate(
        source,
        installable_skill(
            path="quality/code-review",
            skill_file="quality/code-review/SKILL.md",
            source_root="skills",
        ),
    )

    assert result.name == "code-review"
    assert result.description == "Helps review code."
    assert linter.commands == [
        ValidateSkillFileCommand(
            skill_file=str(tmp_path / "snapshot" / "skills" / "quality" / "code-review" / "SKILL.md"),
            expected_name="code-review",
        ),
    ]


def test_committed_skill_validator_hides_linter_issue_details(tmp_path: Path) -> None:
    linter = FakeSkillFileValidator(
        ValidateSkillFileResult(
            issues=(
                SkillValidationIssue(
                    skill_file="/private/snapshot/skills/code-review/SKILL.md",
                    message="secret source content is invalid",
                ),
            ),
        ),
    )

    with pytest.raises(
        CommittedSkillValidationError,
        match="committed skill header validation failed",
    ) as exc_info:
        LinterCommittedSkillValidatorAdapter(validator=linter).validate(
            resolved_source(tmp_path / "snapshot"),
            installable_skill(),
        )

    assert "secret source content" not in str(exc_info.value)
    assert "/private/snapshot" not in str(exc_info.value)


def resolved_source(repository_path: Path) -> ResolvedSkillSource:
    return ResolvedSkillSource(
        source="git@example.com:company/skills.git",
        source_type="git_url",
        repository_path=str(repository_path),
        source_revision="a" * 40,
        source_branch="refs/heads/main",
        index_digest=f"sha256:{'b' * 64}",
    )
