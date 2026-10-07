import pytest

from ritebook.features.skill_installation.application.dtos import (
    InstallSkillCommand,
    SkillReference,
)


def test_skill_reference_parses_index_and_skill_names() -> None:
    reference = SkillReference.parse("platform-skills/code-review")

    assert reference.index_name == "platform-skills"
    assert reference.skill_path == "code-review"
    assert reference.skill_name == "code-review"
    assert reference.requirement == "platform-skills/code-review"


def test_skill_reference_parses_nested_skill_paths() -> None:
    reference = SkillReference.parse("platform-skills/browser/runtime-verification")

    assert reference.index_name == "platform-skills"
    assert reference.skill_path == "browser/runtime-verification"
    assert reference.skill_name == "runtime-verification"
    assert reference.requirement == "platform-skills/browser/runtime-verification"


@pytest.mark.parametrize(
    "skill_reference",
    [
        "platform-skills/CodeReview",
        "platform-skills/quality_tools/code-review",
        "platform-skills/quality/python/code-review",
    ],
)
def test_skill_reference_rejects_invalid_catalog_selectors(
    skill_reference: str,
) -> None:
    with pytest.raises(ValueError, match="Catalog path"):
        SkillReference.parse(skill_reference)


def test_skill_reference_rejects_invalid_index_names() -> None:
    with pytest.raises(ValueError, match="Local alias"):
        SkillReference.parse("InvalidIndex/code-review")


@pytest.mark.parametrize(
    "skill_reference",
    [
        "platform-skills//code-review",
        "platform-skills/code-review/",
        "platform-skills/../code-review",
        "platform-skills/browser/../code-review",
        "platform-skills/browser\\code-review",
    ],
)
def test_skill_reference_rejects_unsafe_skill_paths(skill_reference: str) -> None:
    with pytest.raises(ValueError, match="Catalog path"):
        SkillReference.parse(skill_reference)


def test_install_skill_command_requires_qualified_reference() -> None:
    with pytest.raises(ValueError, match="fully qualified"):
        InstallSkillCommand(skill_reference="code-review", target=".claude/skills")


def test_install_skill_command_requires_explicit_target() -> None:
    with pytest.raises(ValueError, match="Target must not be empty"):
        InstallSkillCommand(skill_reference="platform-skills/code-review", target="")
