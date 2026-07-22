import pytest

from ritebook.shared_kernel.catalog_paths import (
    CatalogPathKind,
    CatalogPathValidationError,
    CatalogPathValidationReason,
    validate_catalog_path,
    validate_catalog_paths,
)


@pytest.mark.parametrize(
    ("value", "kind", "collection", "skill_name"),
    [
        ("code-review", CatalogPathKind.ROOT_SKILL, None, "code-review"),
        (
            "quality/code-review",
            CatalogPathKind.COLLECTION_CHILD,
            "quality",
            "code-review",
        ),
    ],
)
def test_validate_catalog_path_classifies_valid_paths(
    value: str,
    kind: CatalogPathKind,
    collection: str | None,
    skill_name: str,
) -> None:
    catalog_path = validate_catalog_path(value)

    assert catalog_path.value == value
    assert catalog_path.kind is kind
    assert catalog_path.collection == collection
    assert catalog_path.skill_name == skill_name


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/code-review",
        "quality\\code-review",
        ".",
        "..",
        "quality/./code-review",
        "quality/../code-review",
        "quality//code-review",
        "quality/code-review/",
    ],
)
def test_validate_catalog_path_rejects_malformed_literal_paths(value: str) -> None:
    with pytest.raises(CatalogPathValidationError) as exc_info:
        validate_catalog_path(value)

    assert exc_info.value.reason is CatalogPathValidationReason.MALFORMED_PATH
    assert exc_info.value.path == value


def test_validate_catalog_path_rejects_over_deep_paths() -> None:
    with pytest.raises(CatalogPathValidationError) as exc_info:
        validate_catalog_path("quality/python/code-review")

    assert exc_info.value.reason is CatalogPathValidationReason.INVALID_DEPTH
    assert exc_info.value.path == "quality/python/code-review"


@pytest.mark.parametrize(
    "value",
    [
        "CodeReview",
        "quality_tools/code-review",
        "quality/code--review",
        f"quality/{'a' * 65}",
    ],
)
def test_validate_catalog_path_rejects_invalid_segments(value: str) -> None:
    with pytest.raises(CatalogPathValidationError) as exc_info:
        validate_catalog_path(value)

    assert exc_info.value.reason is CatalogPathValidationReason.INVALID_SEGMENT
    assert exc_info.value.path == value


def test_validate_catalog_paths_returns_paths_in_input_order() -> None:
    catalog_paths = validate_catalog_paths(
        ["frontend/code-review", "code-review", "backend/code-review"],
    )

    assert tuple(path.value for path in catalog_paths) == (
        "frontend/code-review",
        "code-review",
        "backend/code-review",
    )


def test_validate_catalog_paths_allows_duplicate_names_at_distinct_paths() -> None:
    catalog_paths = validate_catalog_paths(
        ["backend/code-review", "frontend/code-review"],
    )

    assert [path.skill_name for path in catalog_paths] == ["code-review", "code-review"]


def test_validate_catalog_paths_rejects_duplicate_exact_paths() -> None:
    with pytest.raises(CatalogPathValidationError) as exc_info:
        validate_catalog_paths(["quality/code-review", "quality/code-review"])

    assert exc_info.value.reason is CatalogPathValidationReason.DUPLICATE_PATH
    assert exc_info.value.path == "quality/code-review"


@pytest.mark.parametrize(
    "values",
    [
        ["quality", "quality/code-review"],
        ["quality/code-review", "quality"],
    ],
)
def test_validate_catalog_paths_rejects_mixed_skill_collection_nodes(
    values: list[str],
) -> None:
    with pytest.raises(CatalogPathValidationError) as exc_info:
        validate_catalog_paths(values)

    assert exc_info.value.reason is CatalogPathValidationReason.MIXED_NODE
    assert exc_info.value.path == "quality"
    assert exc_info.value.related_path == "quality/code-review"
