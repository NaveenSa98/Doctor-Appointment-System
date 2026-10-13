from sqlalchemy import Connection, Engine, text

from tests.db.conftest import run_alembic

EXPECTED_TABLES = {
    "alembic_version",
    "appointments",
    "doctor_hospitals",
    "doctors",
    "hospitals",
    "users",
}


def _tables(connection: Connection) -> set[str]:
    rows = connection.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'"
        )
    )
    return {row[0] for row in rows}


def _enum_types(connection: Connection) -> set[str]:
    rows = connection.execute(
        text(
            "SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace "
            "WHERE n.nspname = current_schema() AND t.typtype = 'e'"
        )
    )
    return {row[0] for row in rows}


def test_upgrade_downgrade_round_trip(fresh_engine: Engine) -> None:
    run_alembic(fresh_engine, "upgrade", "head")
    with fresh_engine.connect() as connection:
        assert _tables(connection) == EXPECTED_TABLES
        assert _enum_types(connection) == {"user_role", "appointment_type", "appointment_status"}

    run_alembic(fresh_engine, "downgrade", "base")
    with fresh_engine.connect() as connection:
        assert _tables(connection) == {"alembic_version"}
        assert _enum_types(connection) == set()

    run_alembic(fresh_engine, "upgrade", "head")
    with fresh_engine.connect() as connection:
        assert _tables(connection) == EXPECTED_TABLES


def test_row_level_security_is_enabled_on_every_table(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT c.relname, c.relrowsecurity FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = current_schema() AND c.relkind = 'r'"
            )
        ).all()
    assert {name for name, _ in rows} == EXPECTED_TABLES
    assert all(enabled for _, enabled in rows)
