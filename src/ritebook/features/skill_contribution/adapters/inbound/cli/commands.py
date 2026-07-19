"""Skill contribution command handler for the Ritebook CLI adapter."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING, TextIO

from ritebook.features.skill_contribution.application.dtos import (
    PublishSkillChangeCommand,
    SkillChangeStatus,
)
from ritebook.features.skill_contribution.application.errors import (
    SkillContributionError,
)

if TYPE_CHECKING:
    import argparse

    from ritebook.features.skill_contribution.application.dtos import (
        PreparedContribution,
    )
    from ritebook.features.skill_contribution.application.ports import (
        PublishSkillChangePort,
    )


def run_publish_skill_change(
    args: argparse.Namespace,
    *,
    publish_skill_change: PublishSkillChangePort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Run publish-skill-change against the injected application port."""
    try:
        command = PublishSkillChangeCommand(
            skill_reference=args.skill_reference,
            lockfile_path=args.lockfile,
            contribution_root=args.contribution_root,
        )
        result = publish_skill_change.execute(command)
    except (SkillContributionError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1

    if result.status is SkillChangeStatus.NO_CHANGES:
        print(
            f"No local changes to publish for {result.skill_reference}",
            file=stdout,
        )
        return 0

    prepared = result.prepared_contribution
    if prepared is None:
        print(
            "ritebook: error: prepared contribution metadata is missing",
            file=stderr,
        )
        return 1
    _print_prepared_contribution(prepared, stdout=stdout)
    return 0


def _print_prepared_contribution(
    prepared: PreparedContribution,
    *,
    stdout: TextIO,
) -> None:
    print(f"Prepared contribution for {prepared.skill_reference}", file=stdout)
    print(f"Branch: {prepared.branch_name}", file=stdout)
    print(f"Commit: {prepared.commit_hash}", file=stdout)
    print(f"Checkout: {prepared.checkout_path}", file=stdout)
    if prepared.push_command is not None:
        checkout_path = shlex.quote(prepared.checkout_path)
        print(f"Next: cd {checkout_path} && {prepared.push_command}", file=stdout)
        return
    print(
        "Next: inspect the checkout and push or share the branch manually; "
        "no usable origin remote is configured.",
        file=stdout,
    )
