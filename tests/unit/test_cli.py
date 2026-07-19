from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING

import ritebook.cli as cli_module
from ritebook.features.skill_contribution.adapters.outbound import (
    contribution_checkout,
)
from ritebook.features.skill_contribution.adapters.outbound.git_workspace import (
    GitSkillChangeDetectorAdapter,
    GitWorkspaceAdapter,
)
from ritebook.features.skill_contribution.adapters.outbound.index_regeneration import (
    PublisherIndexRegeneratorAdapter,
)
from ritebook.features.skill_contribution.adapters.outbound.json_lockfile import (
    JsonContributionLockfileReader,
)
from ritebook.features.skill_contribution.adapters.outbound.skill_directory import (
    FilesystemSkillDirectoryAdapter,
)
from ritebook.features.skill_contribution.adapters.outbound.validation import (
    LinterSkillValidatorAdapter,
)
from ritebook.features.skill_contribution.application.use_cases import (
    PublishSkillChange,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest


def test_main_wires_skill_contribution_with_existing_application_ports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_ports: dict[str, object] = {}

    def capture_run(
        argv: Sequence[str] | None,
        **ports: object,
    ) -> int:
        assert argv == ["publish-skill-change", "company-skills/code-review"]
        captured_ports.update(ports)
        return 17

    monkeypatch.setattr(cli_module, "run", capture_run)

    exit_code = cli_module.main(
        ["publish-skill-change", "company-skills/code-review"],
    )

    assert exit_code == 17
    assert set(captured_ports) == {
        "add_index",
        "install_from_requirements",
        "install_skill",
        "linter",
        "list_indexes",
        "list_skills",
        "publish_skill_change",
        "publisher",
        "update_index",
    }

    contribution = captured_ports["publish_skill_change"]
    assert isinstance(contribution, PublishSkillChange)
    dependencies = contribution._dependencies  # noqa: SLF001
    assert isinstance(dependencies.lockfile, JsonContributionLockfileReader)
    assert isinstance(dependencies.source_workspace, GitWorkspaceAdapter)
    assert isinstance(dependencies.change_detector, GitSkillChangeDetectorAdapter)
    assert isinstance(dependencies.skill_directory, FilesystemSkillDirectoryAdapter)
    assert (
        dependencies.change_detector._local_change_detector  # noqa: SLF001
        is dependencies.skill_directory
    )

    assert isinstance(
        dependencies.checkout,
        contribution_checkout.ContributionCheckoutAdapter,
    )
    assert dependencies.checkout._clock().tzinfo is UTC  # noqa: SLF001

    assert isinstance(dependencies.validator, LinterSkillValidatorAdapter)
    assert dependencies.validator._linter is captured_ports["linter"]  # noqa: SLF001
    assert isinstance(dependencies.index_regenerator, PublisherIndexRegeneratorAdapter)
    assert (
        dependencies.index_regenerator._publisher  # noqa: SLF001
        is captured_ports["publisher"]
    )
