"""Filesystem implementation of publisher skill discovery."""

from collections.abc import Mapping
from pathlib import Path

from ritebook.adapters.outbound.filesystem import (
    DiscoveredNamedFile,
    FilesystemSkillDiscoveryError,
    FrontmatterParseError,
    discover_named_files,
    parse_yaml_frontmatter,
)
from ritebook.features.publisher.application.errors import PublishIndexDiscoveryError
from ritebook.features.publisher.domain import SkillEntry
from ritebook.shared_kernel import SKILL_FILE_NAME
from ritebook.shared_kernel.catalog_paths import (
    CatalogPathValidationError,
    validate_catalog_paths,
)


class FilesystemSkillDiscovery:
    """Discover skill entries from directories containing ``SKILL.md`` files."""

    def discover_skills(self, skills_root: str) -> tuple[SkillEntry, ...]:
        """Discover non-hidden skill directories below the explicit skills root."""
        try:
            discovered_files = discover_named_files(
                Path(skills_root),
                file_name=SKILL_FILE_NAME,
            )
            validate_catalog_paths(
                discovered.relative_dir for discovered in discovered_files
            )
            entries = [_skill_entry(discovered) for discovered in discovered_files]
        except FilesystemSkillDiscoveryError as err:
            raise PublishIndexDiscoveryError(str(err)) from err
        except CatalogPathValidationError as err:
            raise PublishIndexDiscoveryError(str(err)) from err

        return tuple(sorted(entries, key=lambda entry: entry.path))


def _skill_entry(discovered: DiscoveredNamedFile) -> SkillEntry:
    skill_dir = discovered.path.parent
    return SkillEntry(
        name=skill_dir.name,
        path=discovered.relative_dir,
        skill_file=discovered.relative_file,
        description=_extract_header_text(discovered.path, field_name="description"),
    )


def _extract_header_text(skill_file: Path, *, field_name: str) -> str:
    frontmatter = parse_yaml_frontmatter(skill_file)
    if isinstance(frontmatter, FrontmatterParseError):
        msg = f"Unable to read required {field_name} from {skill_file}."
        raise PublishIndexDiscoveryError(msg)
    if not isinstance(frontmatter, Mapping):
        msg = f"Unable to read required {field_name} from {skill_file}."
        raise PublishIndexDiscoveryError(msg)

    value = frontmatter.get(field_name)
    if not isinstance(value, str):
        msg = f"Unable to read required {field_name} from {skill_file}."
        raise PublishIndexDiscoveryError(msg)

    text = value.strip()
    if text:
        return text
    msg = f"Unable to read required {field_name} from {skill_file}."
    raise PublishIndexDiscoveryError(msg)
