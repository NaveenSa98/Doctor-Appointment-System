from typing import Any

import pytest

from tests.db.schema import UnsafeSchemaError, assert_test_schema


class _FakeConnection:
    def __init__(self, schema: str) -> None:
        self._schema = schema

    def execute(self, _statement: Any) -> "_FakeConnection":
        return self

    def scalar_one(self) -> str:
        return self._schema


def test_guard_accepts_a_test_schema() -> None:
    assert assert_test_schema(_FakeConnection("test_abc123")) == "test_abc123"


@pytest.mark.parametrize("schema", ["public", "extensions", "auth", "Test_abc", "mytest_x"])
def test_guard_refuses_any_other_schema(schema: str) -> None:
    with pytest.raises(UnsafeSchemaError):
        assert_test_schema(_FakeConnection(schema))
