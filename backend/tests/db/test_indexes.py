from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

EXPECTED_INDEXES = {
    "uq_appointments_doctor_slot",
    "ix_appointments_start_time",
    "ix_appointments_doctor_start",
    "ix_appointments_status_start",
    "ix_appointments_hospital_start",
    "ix_appointments_patient_name_trgm",
    "ix_doctor_hospitals_hospital",
    "uq_hospitals_name_lower",
    "uq_users_email_lower",
}


def test_expected_indexes_exist(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        rows = connection.execute(
            text("SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()")
        )
        names = {row[0] for row in rows}
    assert names >= EXPECTED_INDEXES


def test_double_booking_index_ignores_cancelled_and_deleted_rows(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        definition = connection.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname = current_schema() AND indexname = 'uq_appointments_doctor_slot'"
            )
        ).scalar_one()
    assert "UNIQUE" in definition
    assert "cancelled" in definition
    assert "deleted_at IS NULL" in definition


def test_name_search_uses_the_trigram_index(db_session: Session) -> None:
    db_session.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(
        row[0]
        for row in db_session.execute(
            text("EXPLAIN SELECT id FROM appointments WHERE patient_name ILIKE '%ann%'")
        )
    )
    assert "ix_appointments_patient_name_trgm" in plan
