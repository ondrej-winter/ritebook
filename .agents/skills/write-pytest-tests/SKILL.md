---
name: write-pytest-tests
description: Write or refactor Python tests when pytest-native style, focused scenarios, and deterministic setup are needed.
metadata:
  version: "1.0.0"
---

# Write Pytest Tests

Use this skill when the user asks to add, update, or refactor Python tests and
the target style is pytest-native rather than `unittest`-style.

## Prerequisites

- The behavior under test is clear enough to describe in a test name.
- The project uses `pytest` as its primary test framework.
- You know the narrowest boundary that should be tested.

## Steps

### 1. Choose the smallest useful test scope

- Prefer fast, isolated unit tests by default.
- Use integration tests only for explicit boundaries that touch real I/O.
- Keep each test deterministic and able to run in any order.
- Test one behavior per test.

### 2. Name the behavior clearly

Use scenario-based names that describe the expected outcome.

```python
def test_applies_discount_for_vip_customer():
    ...
```

Prefer names tied to behavior over names tied to helpers, internal methods, or
implementation details.

### 3. Structure tests with Arrange / Act / Assert

```python
def test_applies_discount_for_vip_customer():
    # Arrange
    customer = Customer(is_vip=True)
    order = Order(total=100)

    # Act
    result = calculate_discount(customer, order)

    # Assert
    assert result == 10
```

- Use plain `assert`.
- Keep setup minimal and intention-revealing.
- If a test needs loops, branching, or complex helper logic, simplify it or
  replace repetition with parametrization.

### 4. Use pytest-native tools for common patterns

#### Exceptions

```python
import pytest


def test_raises_for_negative_quantity():
    # Arrange
    quantity = -1

    # Act / Assert
    with pytest.raises(ValueError, match="quantity must be non-negative"):
        create_order(quantity)
```

#### Parametrized scenario matrices

```python
import pytest


@pytest.mark.parametrize(
    ("age", "allowed"),
    [
        (17, False),
        (18, True),
        (19, True),
    ],
)
def test_allows_access_from_minimum_age(age, allowed):
    # Arrange
    policy = AccessPolicy(min_age=18)

    # Act
    result = policy.is_allowed(age)

    # Assert
    assert result is allowed
```

Use `@pytest.mark.parametrize` when several scenarios share the same behavior
and differ only by input and expectation.

#### Small fixtures

```python
import pytest


@pytest.fixture
def vip_customer():
    return Customer(is_vip=True)


def test_applies_discount_for_vip_customer(vip_customer):
    # Arrange
    order = Order(total=100)

    # Act
    result = calculate_discount(vip_customer, order)

    # Assert
    assert result == 10
```

Use fixtures when they remove duplication and keep the scenario clear. Avoid
fixtures that create large implicit worlds.

#### Factories and builders

```python
import pytest


@pytest.fixture
def order_factory():
    def _make_order(total=100, is_vip=False):
        return Order(total=total, customer=Customer(is_vip=is_vip))

    return _make_order


def test_applies_discount_for_vip_customer(order_factory):
    # Arrange
    order = order_factory(total=100, is_vip=True)

    # Act
    result = calculate_discount(order.customer, order)

    # Assert
    assert result == 10
```

Prefer a factory or builder when setup varies by scenario and those variations
should stay visible in the test.

#### Patching with `monkeypatch`

```python
def test_reads_value_from_environment(monkeypatch):
    # Arrange
    monkeypatch.setenv("APP_MODE", "test")

    # Act
    result = get_app_mode()

    # Assert
    assert result == "test"
```

Use `monkeypatch` for environment and dependency patching. If the project
allows pytest plugins, `pytest-mock`'s `mocker` can be used, but it is optional
rather than core `pytest`.

### 5. Assert observable outcomes

- Prefer assertions on returned values, raised exceptions, persisted state in a
  fake, emitted events, or externally visible side effects.
- Avoid asserting on private helpers or deep implementation details.
- Use interaction-based assertions only when verifying a real boundary or
  contract is clearer than asserting on fake state.

### 6. Mock only true boundaries

- Mock or fake gateways, repositories, publishers, clocks, environment access,
  or similar boundaries when isolation is required.
- Prefer small hand-written fakes or stubs over broad `MagicMock` chains.
- Do not mock domain entities or value objects.

### 7. Cover edge cases without making tests heavy

- Cover the happy path plus failure, boundary, and invalid-input cases that
  matter.
- Add regression tests for bugs before or alongside the fix.
- Keep tests readable and direct; do not duplicate production logic inside
  assertions or helpers.

### 8. Avoid pytest anti-patterns

Do not introduce new:

- `unittest.TestCase` subclasses
- `setUp` / `tearDown`
- `self.assertEqual` or other `unittest` assertion methods
- logic-heavy tests with branches or calculations that obscure intent
- order-dependent tests
- tests that rely on live services, ambient environment, wall-clock time, or
  shared developer state

### 9. Run the affected tests

Use the `run-python-tests` skill to run focused tests during development and
the full test suite before handoff.
