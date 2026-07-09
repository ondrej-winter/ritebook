from pathlib import Path

from ritebook.features.index_registry.adapters.outbound.index_cache import (
    FilesystemIndexCache,
)


def test_index_cache_writes_current_index_under_effective_name(tmp_path: Path) -> None:
    cache = FilesystemIndexCache()

    path = cache.write_index(
        name="company-skills",
        content='{"schema_version":1}\n',
        cache_root=str(tmp_path),
    )

    assert path == str(tmp_path / "indexes" / "company-skills" / "ritebook-index.json")
    assert Path(path).read_text(encoding="utf-8") == '{"schema_version":1}\n'


def test_index_cache_flattens_repository_style_name_for_cache_directory(
    tmp_path: Path,
) -> None:
    cache = FilesystemIndexCache()

    path = cache.write_index(
        name="ondrej-winter/ritebook-shelf",
        content='{"schema_version":1}\n',
        cache_root=str(tmp_path),
    )

    assert path == str(
        tmp_path / "indexes" / "ondrej-winter_ritebook-shelf" / "ritebook-index.json",
    )
    assert Path(path).read_text(encoding="utf-8") == '{"schema_version":1}\n'


def test_index_cache_overwrites_existing_content(tmp_path: Path) -> None:
    cache = FilesystemIndexCache()
    cache.write_index(name="company-skills", content="old", cache_root=str(tmp_path))

    path = cache.write_index(
        name="company-skills",
        content="new",
        cache_root=str(tmp_path),
    )

    assert Path(path).read_text(encoding="utf-8") == "new"
