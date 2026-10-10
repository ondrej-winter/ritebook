import pytest

from ritebook.shared_kernel.strict_json import (
    MAX_STRICT_JSON_INPUT_BYTES,
    MAX_STRICT_JSON_NESTING_DEPTH,
    StrictJsonError,
    StrictJsonValidationReason,
    parse_strict_json_bytes,
)


def test_parse_strict_json_bytes_returns_nested_json_value() -> None:
    assert parse_strict_json_bytes(b'{"index":{"name":"skills"},"skills":[]}') == {
        "index": {"name": "skills"},
        "skills": [],
    }


def test_parse_strict_json_bytes_accepts_exact_input_size_limit() -> None:
    content = b" " * (MAX_STRICT_JSON_INPUT_BYTES - len(b"null")) + b"null"

    assert parse_strict_json_bytes(content) is None


def test_parse_strict_json_bytes_rejects_input_above_size_limit() -> None:
    content = b" " * (MAX_STRICT_JSON_INPUT_BYTES + 1)

    with pytest.raises(StrictJsonError) as exc_info:
        parse_strict_json_bytes(content)

    assert exc_info.value.reason is StrictJsonValidationReason.INPUT_TOO_LARGE


def test_parse_strict_json_bytes_accepts_exact_nesting_depth_limit() -> None:
    content = b"[" * MAX_STRICT_JSON_NESTING_DEPTH + b"null" + b"]" * MAX_STRICT_JSON_NESTING_DEPTH

    parse_strict_json_bytes(content)


def test_parse_strict_json_bytes_rejects_nesting_above_depth_limit() -> None:
    content = b"[" * (MAX_STRICT_JSON_NESTING_DEPTH + 1) + b"null" + b"]" * (MAX_STRICT_JSON_NESTING_DEPTH + 1)

    with pytest.raises(StrictJsonError) as exc_info:
        parse_strict_json_bytes(content)

    assert exc_info.value.reason is StrictJsonValidationReason.NESTING_TOO_DEEP


def test_parse_strict_json_bytes_ignores_brackets_inside_strings_for_depth() -> None:
    assert parse_strict_json_bytes(b'{"value":"[[[[{{{{"}') == {
        "value": "[[[[{{{{",
    }


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (b"", StrictJsonValidationReason.EMPTY_INPUT),
        (b"\xef\xbb\xbf{}", StrictJsonValidationReason.BYTE_ORDER_MARK),
        (b'"\xff"', StrictJsonValidationReason.INVALID_UTF8),
        (b"{", StrictJsonValidationReason.INVALID_JSON),
        (b'{"value":NaN}', StrictJsonValidationReason.NON_STANDARD_CONSTANT),
        (b'{"value":Infinity}', StrictJsonValidationReason.NON_STANDARD_CONSTANT),
        (b'{"value":-Infinity}', StrictJsonValidationReason.NON_STANDARD_CONSTANT),
        (
            b'{"name":"first","name":"second"}',
            StrictJsonValidationReason.DUPLICATE_MEMBER,
        ),
        (
            b'{"outer":{"name":"first","name":"second"}}',
            StrictJsonValidationReason.DUPLICATE_MEMBER,
        ),
    ],
)
def test_parse_strict_json_bytes_rejects_non_strict_input(
    content: bytes,
    reason: StrictJsonValidationReason,
) -> None:
    with pytest.raises(StrictJsonError) as exc_info:
        parse_strict_json_bytes(content)

    assert exc_info.value.reason is reason
