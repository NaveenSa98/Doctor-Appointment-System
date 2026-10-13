"""Throwaway test schema on the shared Supabase database, with a safety guard.

Tests run on the same database as the real data, so every connection is pinned to a
``test_<random>`` schema and verified before use. Nothing here ever touches ``public``.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Protocol

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.pool import NullPool

TEST_SCHEMA_PREFIX = "test_"


class UnsafeSchemaError(RuntimeError):
    """Raised when a connection is not pinned to a throwaway test schema."""


class _Scalar(Protocol):
    def scalar_one(self) -> Any: ...


class _Connection(Protocol):
    def execute(self, statement: Any) -> _Scalar: ...


def assert_test_schema(connection: _Connection) -> str:
    """Return the active schema, or raise if it is not a throwaway test schema."""
    schema = str(connection.execute(text("SELECT current_schema()")).scalar_one())
    if not schema.startswith(TEST_SCHEMA_PREFIX):
        raise UnsafeSchemaError(f"Refusing to run: active schema is {schema!r}, not a test schema")
    return schema


def _pin_search_path(schema: str) -> Any:
    def on_connect(dbapi_connection: Any, _record: Any) -> None:
        previous = dbapi_connection.autocommit
        dbapi_connection.autocommit = True
        try:
            with dbapi_connection.cursor() as cursor:
                cursor.execute(f'SET search_path TO "{schema}"')
                cursor.execute("SELECT current_schema()")
                active = cursor.fetchone()[0]
        finally:
            dbapi_connection.autocommit = previous
        if active != schema or not active.startswith(TEST_SCHEMA_PREFIX):
            raise UnsafeSchemaError(f"Connection is not pinned to {schema!r} (got {active!r})")

    return on_connect


@contextmanager
def temp_schema_engine(url: str) -> Iterator[Engine]:
    """Create a unique test schema, yield an engine pinned to it, and drop it afterwards."""
    schema = f"{TEST_SCHEMA_PREFIX}{uuid.uuid4().hex[:12]}"
    admin = create_engine(url, poolclass=NullPool)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, pool_size=2, max_overflow=1, pool_pre_ping=True)
    # insert=True so the search_path is set before SQLAlchemy initialises the dialect.
    event.listen(engine, "connect", _pin_search_path(schema), insert=True)
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin.dispose()
