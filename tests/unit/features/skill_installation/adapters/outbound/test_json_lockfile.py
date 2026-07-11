import json
from pathlib import Path
from typing import Any, cast

from ritebook.features.skill_installation.adapters.outbound.json_lockfile import (
    JsonLockfileAdapter,
)
from ritebook.features.skill_installation.application.dtos import LockfileManifestEntry


def test_json_lockfile_writes_deterministic_schema_sorted_by_index_and_skill(
    tmp_path: Path,
) -> None:
    lockfile_path = tmp_path / "ritebook.lock"
    entries = (
        _entry(requirement="platform-skills/test-driven-development"),
        _entry(requirement="company-agents/security-review"),
        _entry(requirement="platform-skills/code-review"),
    )

    JsonLockfileAdapter().write_lockfile(
        entries,
        str(lockfile_path),
        requirements_file="ritebook.toml",
    )

    data = _read_json(lockfile_path)
    requirements = [entry["requirement"] for entry in data["skills"]]
    assert data["schema_version"] == 1
    assert data["requirements_file"] == "ritebook.toml"
    assert requirements == [
        "company-agents/security-review",
        "platform-skills/code-review",
        "platform-skills/test-driven-development",
    ]
    assert lockfile_path.read_text(encoding="utf-8").endswith("\n")


def test_json_lockfile_preserves_relative_targets_and_optional_target_ref(
    tmp_path: Path,
) -> None:
    lockfile_path = tmp_path / "ritebook.lock"

    JsonLockfileAdapter().write_lockfile(
        (
            _entry(
                requirement="platform-skills/code-review",
                target=".claude/skills/code-review",
                target_ref="claude",
            ),
        ),
        str(lockfile_path),
        requirements_file="config/ritebook.toml",
    )

    data = _read_json(lockfile_path)
    assert data["skills"][0]["target"] == ".claude/skills/code-review"
    assert data["skills"][0]["target_ref"] == "claude"


def test_json_lockfile_omits_optional_fields_when_not_resolved(tmp_path: Path) -> None:
    lockfile_path = tmp_path / "ritebook.lock"

    JsonLockfileAdapter().write_lockfile(
        (
            _entry(
                target_ref=None,
                source_revision=None,
            ),
        ),
        str(lockfile_path),
        requirements_file="ritebook.toml",
    )

    data = _read_json(lockfile_path)
    assert "target_ref" not in data["skills"][0]
    assert "source_revision" not in data["skills"][0]


def test_json_lockfile_full_rewrite_removes_stale_entries(tmp_path: Path) -> None:
    lockfile_path = tmp_path / "ritebook.lock"
    adapter = JsonLockfileAdapter()
    adapter.write_lockfile(
        (
            _entry(requirement="platform-skills/code-review"),
            _entry(requirement="platform-skills/test-driven-development"),
        ),
        str(lockfile_path),
        requirements_file="ritebook.toml",
    )

    adapter.write_lockfile(
        (_entry(requirement="platform-skills/code-review"),),
        str(lockfile_path),
        requirements_file="ritebook.toml",
    )

    data = _read_json(lockfile_path)
    assert [entry["requirement"] for entry in data["skills"]] == [
        "platform-skills/code-review",
    ]


def _entry(
    *,
    requirement: str = "platform-skills/code-review",
    target: str = ".claude/skills/code-review",
    target_ref: str | None = None,
    source_revision: str | None = "abc123",
) -> LockfileManifestEntry:
    index_name, skill_name = requirement.rsplit("/", maxsplit=1)
    return LockfileManifestEntry(
        requirement=requirement,
        index_name=index_name,
        skill_name=skill_name,
        target=target,
        source="git@example.com:company/skills.git",
        source_type="git_url",
        source_revision=source_revision,
        index_schema_version=1,
        skill_path=f"skills/{skill_name}",
        skill_file=f"skills/{skill_name}/SKILL.md",
        target_ref=target_ref,
        locked_at="2026-07-10T21:00:00Z",
    )


def _read_json(path: Path) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))
