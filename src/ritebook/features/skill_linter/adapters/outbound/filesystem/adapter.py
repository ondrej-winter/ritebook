"""Filesystem implementation of skill discovery."""

from pathlib import Path

from ritebook.adapters.outbound.filesystem import (
    DiscoveredNamedFile,
    FilesystemSkillDiscoveryError,
    SkillFileReadError,
    discover_named_files,
)
from ritebook.features.skill_linter.adapters.outbound.filesystem.frontmatter import (
    parse_skill_header,
)
from ritebook.features.skill_linter.application.dtos import (
    ParsedSkillHeader,
    SkillHeaderDiscoveryResult,
    SkillValidationIssue,
)
from ritebook.features.skill_linter.application.errors import LintSkillsDiscoveryError
from ritebook.shared_kernel import SKILL_FILE_NAME
from ritebook.shared_kernel.catalog_paths import (
    CatalogPath,
    CatalogPathKind,
    CatalogPathValidationError,
    validate_catalog_path,
    validate_catalog_paths,
)


class FilesystemSkillHeaderDiscovery:
    """Discover and parse skill headers from ``SKILL.md`` files."""

    def discover_headers(self, skills_root: str) -> SkillHeaderDiscoveryResult:
        """Discover non-hidden skill headers below the explicit skills root."""
        issues: list[SkillValidationIssue] = []
        try:
            discovered_files = discover_named_files(
                Path(skills_root),
                file_name=SKILL_FILE_NAME,
            )
        except FilesystemSkillDiscoveryError as err:
            raise LintSkillsDiscoveryError(str(err)) from err

        valid_candidates: list[tuple[DiscoveredNamedFile, CatalogPath]] = []
        for discovered in discovered_files:
            try:
                catalog_path = validate_catalog_path(discovered.relative_dir)
            except CatalogPathValidationError as err:
                issues.append(
                    SkillValidationIssue(
                        skill_file=discovered.relative_file,
                        message=str(err),
                    ),
                )
            else:
                valid_candidates.append((discovered, catalog_path))

        root_paths = {
            catalog_path.value
            for _, catalog_path in valid_candidates
            if catalog_path.kind is CatalogPathKind.ROOT_SKILL
        }
        parse_candidates: list[DiscoveredNamedFile] = []
        for discovered, catalog_path in valid_candidates:
            if catalog_path.collection not in root_paths:
                parse_candidates.append(discovered)
                continue
            try:
                validate_catalog_paths((catalog_path.collection, catalog_path.value))
            except CatalogPathValidationError as err:
                issues.append(
                    SkillValidationIssue(
                        skill_file=discovered.relative_file,
                        message=str(err),
                    ),
                )

        headers, parse_issues = _parse_candidates(parse_candidates)
        issues.extend(parse_issues)

        return SkillHeaderDiscoveryResult.create(
            discovered_skill_count=len(discovered_files),
            headers=headers,
            issues=issues,
        )


def _parse_candidates(
    candidates: list[DiscoveredNamedFile],
) -> tuple[list[ParsedSkillHeader], list[SkillValidationIssue]]:
    headers: list[ParsedSkillHeader] = []
    issues: list[SkillValidationIssue] = []
    for discovered in candidates:
        try:
            parsed = parse_skill_header(
                discovered.path,
                relative_skill_file=discovered.relative_file,
                expected_name=discovered.directory_name,
            )
        except SkillFileReadError:
            issues.append(
                SkillValidationIssue(
                    skill_file=discovered.relative_file,
                    message="skill file must be readable UTF-8 text.",
                ),
            )
            continue
        if isinstance(parsed, SkillValidationIssue):
            issues.append(parsed)
        else:
            headers.append(parsed)
    return headers, issues
