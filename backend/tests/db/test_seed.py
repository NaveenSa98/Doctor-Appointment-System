from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Appointment, Doctor, Hospital, User
from scripts.seed import seed


def _counts(session: Session) -> tuple[int, int, int, int]:
    return (
        session.scalar(select(func.count()).select_from(Hospital)) or 0,
        session.scalar(select(func.count()).select_from(Doctor)) or 0,
        session.scalar(select(func.count()).select_from(User)) or 0,
        session.scalar(select(func.count()).select_from(Appointment)) or 0,
    )


def test_seed_is_idempotent(db_session: Session) -> None:
    seed(db_session)
    first = _counts(db_session)
    assert first == (4, 6, 7, 60)

    seed(db_session)
    assert _counts(db_session) == first


def test_some_doctors_visit_several_hospitals(db_session: Session) -> None:
    seed(db_session)
    doctors = db_session.scalars(select(Doctor)).all()
    assert any(len(doctor.hospitals) > 1 for doctor in doctors)
