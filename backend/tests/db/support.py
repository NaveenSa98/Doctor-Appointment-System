"""Helpers for running Alembic against a throwaway test schema."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import Engine

from alembic import command
from tests.db.schema import assert_test_schema

BACKEND_DIR = Path(__file__).resolve().parents[2]


def run_alembic(engine: Engine, action: str, revision: str) -> None:
    """Run an Alembic command on a connection from the given (schema-pinned) engine."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    with engine.begin() as connection:
        assert_test_schema(connection)
        config.attributes["connection"] = connection
        getattr(command, action)(config, revision)
