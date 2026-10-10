from datetime import UTC, datetime, timedelta, timezone

import pytest

from ritebook.shared_kernel.timestamps import (
    format_canonical_utc_timestamp,
    parse_canonical_utc_timestamp,
)


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        (datetime(2026, 7, 4, 18, 49, tzinfo=UTC), "2026-07-04T18:49:00Z"),
        (
            datetime(2026, 7, 4, 20, 49, tzinfo=timezone(timedelta(hours=2))),
            "2026-07-04T18:49:00Z",
        ),
        (
            datetime(2026, 7, 4, 18, 49, 0, 123456, tzinfo=UTC),
            "2026-07-04T18:49:00.123456Z",
        ),
    ],
)
def test_format_canonical_utc_timestamp_emits_schema_v1_form(
    timestamp: datetime,
    expected: str,
) -> None:
    assert format_canonical_utc_timestamp(timestamp, field_name="generated_at") == expected


def test_parse_canonical_utc_timestamp_returns_utc_datetime() -> None:
    assert parse_canonical_utc_timestamp(
        "2026-07-04T18:49:00.123456Z",
        field_name="generated_at",
    ) == datetime(2026, 7, 4, 18, 49, 0, 123456, tzinfo=UTC)


@pytest.mark.parametrize(
    "value",
    [
        "2026-07-04T18:49Z",
        "2026-07-04T18:49:00+00:00",
        "2026-07-04T20:49:00+02:00",
        "2026-07-04t18:49:00Z",
        "2026-07-04T18:49:00.1Z",
        "2026-02-30T18:49:00Z",
        "2026-07-04T18:49:60Z",
    ],
)
def test_parse_canonical_utc_timestamp_rejects_non_canonical_values(value: str) -> None:
    with pytest.raises(ValueError, match="canonical UTC timestamp"):
        parse_canonical_utc_timestamp(value, field_name="generated_at")


def test_format_canonical_utc_timestamp_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        format_canonical_utc_timestamp(
            datetime(2026, 7, 4, 18, 49),
            field_name="generated_at",
        )
