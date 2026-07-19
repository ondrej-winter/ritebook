import json
from pathlib import Path

import pytest

from ritebook.features.skill_contribution.adapters.outbound.json_lockfile import (
    JsonContributionLockfileReader,
)
from ritebook.features.skill_contribution.application.dtos import (
    ContributionSkillReference,
)
from ritebook.features.skill_contribution.application.errors import (
    AmbiguousContributionSkillReferenceError,
    ContributionLockfileEntryNotFoundError,
    ContributionLockfileReadError,
)


def test_json_lockfile_reader_resolves_exact_requirement(tmp_path: Path) -> None:
    lockfile_path = write_lockfile(tmp_path, skills=[lockfile_entry()])

    result = JsonContributionLockfileReader().resolve_entry(
        ContributionSkillReference.parse("platform-skills/code-review"),
        str(lockfile_path),
    )

    assert result.requirement == "platform-skills/code-review"
    assert result.source_revision == "abc123"
    assert result.target == ".agents/skills/code-review"


def test_json_lockfile_reader_defaults_to_repo_lockfile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_lockfile(tmp_path, skills=[lockfile_entry()])
    monkeypatch.chdir(tmp_path)

    result = JsonContributionLockfileReader().resolve_entry(
        ContributionSkillReference.parse("platform-skills/code-review"),
        None,
    )

    assert result.skill_name == "code-review"


def test_json_lockfile_reader_resolves_exact_skill_path(tmp_path: Path) -> None:
    lockfile_path = write_lockfile(
        tmp_path,
        skills=[
            lockfile_entry(requirement="platform-skills/code-review"),
            lockfile_entry(
                requirement="platform-skills/software-development/code-review",
                skill_path="software-development/code-review",
            ),
        ],
    )

    result = JsonContributionLockfileReader().resolve_entry(
        ContributionSkillReference.parse(
            "platform-skills/software-development/code-review",
        ),
        str(lockfile_path),
    )

    assert result.skill_path == "software-development/code-review"


def test_json_lockfile_reader_resolves_unique_flat_skill_name(tmp_path: Path) -> None:
    lockfile_path = write_lockfile(
        tmp_path,
        skills=[
            lockfile_entry(
                requirement="platform-skills/security-review",
                skill_name="security-review",
                skill_path="security-review",
                skill_file="security-review/SKILL.md",
            ),
            lockfile_entry(
                requirement="platform-skills/software-development/code-review",
                skill_path="software-development/code-review",
            ),
        ],
    )

    result = JsonContributionLockfileReader().resolve_entry(
        ContributionSkillReference.parse("platform-skills/code-review"),
        str(lockfile_path),
    )

    assert result.skill_path == "software-development/code-review"


def test_json_lockfile_reader_filters_by_index_name(tmp_path: Path) -> None:
    lockfile_path = write_lockfile(
        tmp_path,
        skills=[
            lockfile_entry(
                requirement="other-skills/code-review",
                index_name="other-skills",
            ),
        ],
    )

    with pytest.raises(ContributionLockfileEntryNotFoundError, match="no lockfile"):
        JsonContributionLockfileReader().resolve_entry(
            ContributionSkillReference.parse("platform-skills/code-review"),
            str(lockfile_path),
        )


def test_json_lockfile_reader_does_not_expand_path_prefixes(tmp_path: Path) -> None:
    lockfile_path = write_lockfile(
        tmp_path,
        skills=[
            lockfile_entry(
                requirement="platform-skills/software-development/code-review",
                skill_path="software-development/code-review",
            ),
        ],
    )

    with pytest.raises(ContributionLockfileEntryNotFoundError, match="no lockfile"):
        JsonContributionLockfileReader().resolve_entry(
            ContributionSkillReference.parse("platform-skills/software-development"),
            str(lockfile_path),
        )


def test_json_lockfile_reader_rejects_ambiguous_flat_skill_name(
    tmp_path: Path,
) -> None:
    lockfile_path = write_lockfile(
        tmp_path,
        skills=[
            lockfile_entry(
                requirement="platform-skills/software-development/code-review",
                skill_path="software-development/code-review",
            ),
            lockfile_entry(
                requirement="platform-skills/review/code-review",
                skill_path="review/code-review",
            ),
        ],
    )

    with pytest.raises(AmbiguousContributionSkillReferenceError, match="ambiguous"):
        JsonContributionLockfileReader().resolve_entry(
            ContributionSkillReference.parse("platform-skills/code-review"),
            str(lockfile_path),
        )


def test_json_lockfile_reader_rejects_missing_lockfile(tmp_path: Path) -> None:
    with pytest.raises(ContributionLockfileReadError, match="cannot be read"):
        JsonContributionLockfileReader().resolve_entry(
            ContributionSkillReference.parse("platform-skills/code-review"),
            str(tmp_path / "missing.lock"),
        )


def test_json_lockfile_reader_rejects_invalid_json(tmp_path: Path) -> None:
    lockfile_path = tmp_path / "ritebook.lock"
    lockfile_path.write_text("not-json", encoding="utf-8")

    with pytest.raises(ContributionLockfileReadError, match="not valid JSON"):
        JsonContributionLockfileReader().resolve_entry(
            ContributionSkillReference.parse("platform-skills/code-review"),
            str(lockfile_path),
        )


def test_json_lockfile_reader_rejects_non_object_payload(tmp_path: Path) -> None:
    lockfile_path = tmp_path / "ritebook.lock"
    lockfile_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ContributionLockfileReadError, match="JSON object"):
        JsonContributionLockfileReader().resolve_entry(
            ContributionSkillReference.parse("platform-skills/code-review"),
            str(lockfile_path),
        )


def test_json_lockfile_reader_rejects_unsupported_schema(tmp_path: Path) -> None:
    lockfile_path = write_lockfile(tmp_path, overrides={"schema_version": 2})

    with pytest.raises(
        ContributionLockfileReadError,
        match="unsupported lockfile schema_version: 2",
    ):
        JsonContributionLockfileReader().resolve_entry(
            ContributionSkillReference.parse("platform-skills/code-review"),
            str(lockfile_path),
        )


def test_json_lockfile_reader_rejects_missing_skills_array(tmp_path: Path) -> None:
    lockfile_path = write_lockfile(tmp_path, overrides={"skills": None})

    with pytest.raises(ContributionLockfileReadError, match="skills array"):
        JsonContributionLockfileReader().resolve_entry(
            ContributionSkillReference.parse("platform-skills/code-review"),
            str(lockfile_path),
        )


def test_json_lockfile_reader_rejects_non_object_skill_entries(tmp_path: Path) -> None:
    lockfile_path = write_lockfile(tmp_path, skills=["code-review"])

    with pytest.raises(ContributionLockfileReadError, match="JSON objects"):
        JsonContributionLockfileReader().resolve_entry(
            ContributionSkillReference.parse("platform-skills/code-review"),
            str(lockfile_path),
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "requirement",
        "index_name",
        "skill_name",
        "target",
        "source",
        "source_type",
        "source_revision",
        "skill_path",
        "skill_file",
    ],
)
def test_json_lockfile_reader_rejects_missing_required_string_fields(
    tmp_path: Path,
    field_name: str,
) -> None:
    entry = lockfile_entry()
    del entry[field_name]
    lockfile_path = write_lockfile(tmp_path, skills=[entry])

    with pytest.raises(ContributionLockfileReadError, match=field_name):
        JsonContributionLockfileReader().resolve_entry(
            ContributionSkillReference.parse("platform-skills/code-review"),
            str(lockfile_path),
        )


def test_json_lockfile_reader_rejects_missing_index_schema_version(
    tmp_path: Path,
) -> None:
    entry = lockfile_entry()
    del entry["index_schema_version"]
    lockfile_path = write_lockfile(tmp_path, skills=[entry])

    with pytest.raises(ContributionLockfileReadError, match="index_schema_version"):
        JsonContributionLockfileReader().resolve_entry(
            ContributionSkillReference.parse("platform-skills/code-review"),
            str(lockfile_path),
        )


def test_json_lockfile_reader_rejects_malformed_entry_fields(tmp_path: Path) -> None:
    lockfile_path = write_lockfile(
        tmp_path,
        skills=[lockfile_entry(skill_path="../code-review")],
    )

    with pytest.raises(ContributionLockfileReadError, match="safe relative POSIX path"):
        JsonContributionLockfileReader().resolve_entry(
            ContributionSkillReference.parse("platform-skills/code-review"),
            str(lockfile_path),
        )


def write_lockfile(
    tmp_path: Path,
    *,
    skills: list[object] | None = None,
    overrides: dict[str, object] | None = None,
) -> Path:
    payload: dict[str, object] = {
        "schema_version": 1,
        "requirements_file": "ritebook.toml",
        "skills": skills if skills is not None else [lockfile_entry()],
    }
    if overrides is not None:
        payload.update(overrides)
    lockfile_path = tmp_path / "ritebook.lock"
    lockfile_path.write_text(json.dumps(payload), encoding="utf-8")
    return lockfile_path


def lockfile_entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "requirement": "platform-skills/code-review",
        "index_name": "platform-skills",
        "skill_name": "code-review",
        "target": ".agents/skills/code-review",
        "source": "git@example.com:example/skills.git",
        "source_type": "git_url",
        "source_revision": "abc123",
        "index_schema_version": 1,
        "skill_path": "code-review",
        "skill_file": "code-review/SKILL.md",
        "locked_at": "2026-07-19T17:00:00Z",
    }
    entry.update(overrides)
    return entry
