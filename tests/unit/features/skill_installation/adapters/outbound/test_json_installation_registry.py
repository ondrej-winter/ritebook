import json
from pathlib import Path
from typing import Any, cast

import pytest

from ritebook.features.skill_installation.adapters.outbound import (
    json_installation_registry,
)
from ritebook.features.skill_installation.application.dtos import (
    InstallationManifestEntry,
)
from ritebook.features.skill_installation.application.errors import (
    ConflictingRecordedTargetError,
    InstallationPersistenceError,
)


def test_json_installation_registry_writes_deterministic_state_sorted_by_target(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "config" / "ritebook" / "installations.json"
    adapter = json_installation_registry.JsonInstallationRegistryAdapter()

    adapter.write_installation(
        _entry(requirement="platform-skills/test-driven-development", target="z-skill"),
        str(registry_path),
        force=False,
    )
    adapter.write_installation(
        _entry(requirement="platform-skills/code-review", target="a-skill"),
        str(registry_path),
        force=False,
    )

    data = _read_json(registry_path)
    targets = [entry["target"] for entry in data["installations"]]
    assert data["schema_version"] == 1
    assert targets == sorted(targets)
    assert data["installations"][0] == {
        "requirement": "platform-skills/code-review",
        "index_name": "platform-skills",
        "skill_name": "code-review",
        "target": str((Path.cwd() / "a-skill").resolve(strict=False)),
        "source": "git@example.com:company/skills.git",
        "source_type": "git_url",
        "source_revision": "abc123",
        "index_schema_version": 1,
        "skill_path": "skills/code-review",
        "skill_file": "skills/code-review/SKILL.md",
        "installed_at": "2026-07-10T21:00:00Z",
    }
    assert registry_path.read_text(encoding="utf-8").endswith("\n")


def test_json_installation_registry_replaces_same_target_with_force(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "installations.json"
    adapter = json_installation_registry.JsonInstallationRegistryAdapter()
    target = tmp_path / "skills" / "code-review"

    adapter.write_installation(
        _entry(target=str(target), source_revision="old"),
        str(registry_path),
        force=False,
    )
    adapter.write_installation(
        _entry(target=str(target), source_revision="new"),
        str(registry_path),
        force=True,
    )

    data = _read_json(registry_path)
    assert len(data["installations"]) == 1
    assert data["installations"][0]["source_revision"] == "new"


def test_json_installation_registry_refuses_conflicting_recorded_target_without_force(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "installations.json"
    adapter = json_installation_registry.JsonInstallationRegistryAdapter()
    target = tmp_path / "skills" / "shared-target"
    adapter.write_installation(
        _entry(requirement="platform-skills/code-review", target=str(target)),
        str(registry_path),
        force=False,
    )

    with pytest.raises(ConflictingRecordedTargetError, match="use --force"):
        adapter.write_installation(
            _entry(
                requirement="platform-skills/test-driven-development",
                target=str(target),
            ),
            str(registry_path),
            force=False,
        )

    data = _read_json(registry_path)
    assert len(data["installations"]) == 1
    assert data["installations"][0]["requirement"] == "platform-skills/code-review"


def test_json_installation_registry_replaces_conflicting_recorded_target_with_force(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "installations.json"
    adapter = json_installation_registry.JsonInstallationRegistryAdapter()
    target = tmp_path / "skills" / "shared-target"
    adapter.write_installation(
        _entry(requirement="platform-skills/code-review", target=str(target)),
        str(registry_path),
        force=False,
    )

    adapter.write_installation(
        _entry(
            requirement="platform-skills/test-driven-development",
            target=str(target),
        ),
        str(registry_path),
        force=True,
    )

    data = _read_json(registry_path)
    assert len(data["installations"]) == 1
    assert data["installations"][0]["requirement"] == (
        "platform-skills/test-driven-development"
    )


def test_json_installation_registry_omits_unresolved_source_revision(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "installations.json"

    json_installation_registry.JsonInstallationRegistryAdapter().write_installation(
        _entry(source_revision=None),
        str(registry_path),
        force=False,
    )

    data = _read_json(registry_path)
    assert "source_revision" not in data["installations"][0]


def test_json_installation_registry_rejects_malformed_existing_registry(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "installations.json"
    registry_path.write_text("not json", encoding="utf-8")

    with pytest.raises(InstallationPersistenceError, match="cannot be read"):
        json_installation_registry.JsonInstallationRegistryAdapter().write_installation(
            _entry(),
            str(registry_path),
            force=False,
        )


def _entry(
    *,
    requirement: str = "platform-skills/code-review",
    target: str = ".claude/skills/code-review",
    source_revision: str | None = "abc123",
) -> InstallationManifestEntry:
    skill_name = requirement.rsplit("/", maxsplit=1)[1]
    return InstallationManifestEntry(
        requirement=requirement,
        index_name="platform-skills",
        skill_name=skill_name,
        target=target,
        source="git@example.com:company/skills.git",
        source_type="git_url",
        source_revision=source_revision,
        index_schema_version=1,
        skill_path=f"skills/{skill_name}",
        skill_file=f"skills/{skill_name}/SKILL.md",
        installed_at="2026-07-10T21:00:00Z",
    )


def _read_json(path: Path) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))
