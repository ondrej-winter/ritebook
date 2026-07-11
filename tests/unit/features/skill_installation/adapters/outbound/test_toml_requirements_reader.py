from pathlib import Path

import pytest

from ritebook.features.skill_installation.adapters.outbound.toml_requirements import (
    TomlRequirementsReader,
)
from ritebook.features.skill_installation.application.errors import (
    RequirementsReadError,
)


def test_toml_requirements_reader_reads_targets_and_skill_entries(
    tmp_path: Path,
) -> None:
    requirements_file = write_requirements(
        tmp_path,
        """
        [targets]
        claude = ".claude/skills"
        shared = "../shared-agent-skills"

        [[skills]]
        name = "platform-skills/code-review"
        target = "claude"

        [[skills]]
        name = "company-skills/security-review"
        target = "shared"
        """,
    )

    result = TomlRequirementsReader().read_requirements(str(requirements_file))

    assert result.targets == {
        "claude": ".claude/skills",
        "shared": "../shared-agent-skills",
    }
    assert [skill.name for skill in result.skills] == [
        "platform-skills/code-review",
        "company-skills/security-review",
    ]
    assert result.skills[0].target == "claude"
    assert result.skills[0].target_path is None


def test_toml_requirements_reader_supports_target_paths_without_targets(
    tmp_path: Path,
) -> None:
    requirements_file = write_requirements(
        tmp_path,
        """
        [[skills]]
        name = "platform-skills/code-review"
        target_path = ".claude/skills/code-review"
        """,
    )

    result = TomlRequirementsReader().read_requirements(str(requirements_file))

    assert result.targets == {}
    assert result.skills[0].target is None
    assert result.skills[0].target_path == ".claude/skills/code-review"


def test_toml_requirements_reader_rejects_missing_file(tmp_path: Path) -> None:
    requirements_file = tmp_path / "missing.toml"

    with pytest.raises(RequirementsReadError, match="does not exist"):
        TomlRequirementsReader().read_requirements(str(requirements_file))


def test_toml_requirements_reader_rejects_invalid_toml(tmp_path: Path) -> None:
    requirements_file = write_requirements(tmp_path, "[[skills]")

    with pytest.raises(RequirementsReadError, match="invalid TOML"):
        TomlRequirementsReader().read_requirements(str(requirements_file))


def test_toml_requirements_reader_rejects_unknown_root_fields(
    tmp_path: Path,
) -> None:
    requirements_file = write_requirements(
        tmp_path,
        """
        version = 1

        [[skills]]
        name = "platform-skills/code-review"
        target_path = ".claude/skills/code-review"
        """,
    )

    with pytest.raises(RequirementsReadError, match=r"unknown field.*version"):
        TomlRequirementsReader().read_requirements(str(requirements_file))


@pytest.mark.parametrize(
    "targets_toml",
    [
        'targets = "claude"',
        '[targets]\nclaude = ""',
        "[targets]\n'bad nickname' = \".claude/skills\"",
        "[targets]\nclaude = 42",
    ],
)
def test_toml_requirements_reader_rejects_malformed_targets(
    tmp_path: Path,
    targets_toml: str,
) -> None:
    requirements_file = write_requirements(
        tmp_path,
        f"""
        {targets_toml}

        [[skills]]
        name = "platform-skills/code-review"
        target_path = ".claude/skills/code-review"
        """,
    )

    with pytest.raises(RequirementsReadError):
        TomlRequirementsReader().read_requirements(str(requirements_file))


def test_toml_requirements_reader_rejects_missing_skills_array(
    tmp_path: Path,
) -> None:
    requirements_file = write_requirements(
        tmp_path,
        """
        [targets]
        claude = ".claude/skills"
        """,
    )

    with pytest.raises(RequirementsReadError, match=r"\[\[skills\]\]"):
        TomlRequirementsReader().read_requirements(str(requirements_file))


def test_toml_requirements_reader_rejects_unknown_skill_fields(
    tmp_path: Path,
) -> None:
    requirements_file = write_requirements(
        tmp_path,
        """
        [[skills]]
        name = "platform-skills/code-review"
        target_path = ".claude/skills/code-review"
        extra = true
        """,
    )

    with pytest.raises(RequirementsReadError, match=r"unknown field.*extra"):
        TomlRequirementsReader().read_requirements(str(requirements_file))


@pytest.mark.parametrize(
    "skill_toml",
    [
        'target_path = ".claude/skills/code-review"',
        'name = "code-review"\ntarget_path = ".claude/skills/code-review"',
        'name = 42\ntarget_path = ".claude/skills/code-review"',
        'name = "platform-skills/code-review"',
        (
            'name = "platform-skills/code-review"\n'
            'target = "claude"\n'
            'target_path = ".claude/skills/code-review"'
        ),
        'name = "platform-skills/code-review"\ntarget_path = ""',
    ],
)
def test_toml_requirements_reader_rejects_malformed_skill_entries(
    tmp_path: Path,
    skill_toml: str,
) -> None:
    requirements_file = write_requirements(
        tmp_path,
        f"""
        [[skills]]
        {skill_toml}
        """,
    )

    with pytest.raises(RequirementsReadError):
        TomlRequirementsReader().read_requirements(str(requirements_file))


def test_toml_requirements_reader_rejects_unknown_target_nickname(
    tmp_path: Path,
) -> None:
    requirements_file = write_requirements(
        tmp_path,
        """
        [targets]
        claude = ".claude/skills"

        [[skills]]
        name = "platform-skills/code-review"
        target = "missing"
        """,
    )

    with pytest.raises(RequirementsReadError, match="target nickname missing"):
        TomlRequirementsReader().read_requirements(str(requirements_file))


def write_requirements(tmp_path: Path, content: str) -> Path:
    requirements_file = tmp_path / "ritebook.toml"
    requirements_file.write_text(content, encoding="utf-8")
    return requirements_file
