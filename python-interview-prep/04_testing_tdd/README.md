# 04 — TDD, Unit & Integration Testing

Needs `pytest` (`pip install -r ../requirements.txt`). Run with `pytest` from this folder, or
`pytest 04_testing_tdd` from the project root.

## Crib sheet

- **Red-Green-Refactor**: write a failing test first, write the minimum code to pass it, then
  refactor without breaking tests. Forces clear API design and prevents over-engineering.
- **Fixtures** (`@pytest.fixture`) build the object-under-test with its dependencies mocked —
  keeps each test focused on one behavior instead of re-wiring setup every time.
- **`unittest.mock.MagicMock`** stands in for a collaborator (a repo, a payment client) so the
  test exercises only the logic in the class under test, not its dependencies.
- **`pytest.raises`** asserts an exception type (and optionally a message pattern via `match=`).
- **`pytest.mark.parametrize`** runs the same test body against a table of inputs/outputs — far
  less duplication than copy-pasting near-identical test functions.
- **Unit vs integration**: unit tests mock dependencies and test business logic in isolation;
  integration tests exercise real boundaries (an HTTP client hitting a real router, a real DB via
  testcontainers). Both matter; unit tests should dominate by count.
- **Coverage** is a floor, not a target — `pytest --cov=src --cov-fail-under=80` catches
  regressions, but 100% coverage doesn't mean bug-free; it means every line executed once.

## Files

| File | Topic |
|---|---|
| `src/order_service.py` | the class under test — validates items, calls a payment client, saves via a repo |
| `tests/test_order_service.py` | fixtures, mocking, `pytest.raises`, `parametrize` |
| `conftest.py` | shared fixtures available to every test file in this folder |

## Try it

```bash
cd 04_testing_tdd
pytest -v                      # run everything, verbose
pytest -v -k "empty"           # run only tests whose name matches "empty"
pytest --cov=src --cov-report=term-missing   # needs pytest-cov: pip install pytest-cov
```

## Exercise

Add a `discount_code` parameter to `OrderService.place_order`. Write the failing test **first**
(assert a 10% discount is applied when `discount_code="SAVE10"`), watch it fail, then implement
just enough in `src/order_service.py` to make it pass. That's the whole TDD loop in one exercise.
