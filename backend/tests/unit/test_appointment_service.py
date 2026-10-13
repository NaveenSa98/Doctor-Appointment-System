from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import ValidationFailed
from app.services.appointment_service import check_bookable_time

NOW = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)


def test_a_future_time_is_bookable() -> None:
    check_bookable_time(NOW + timedelta(minutes=30), NOW)


@pytest.mark.parametrize("offset", [timedelta(0), timedelta(minutes=-30), timedelta(days=-400)])
def test_now_and_the_past_are_not_bookable(offset: timedelta) -> None:
    with pytest.raises(ValidationFailed) as exc:
        check_bookable_time(NOW + offset, NOW)
    assert exc.value.status_code == 422
    assert exc.value.details == [{"field": "start_time", "message": "must be in the future"}]


def test_two_years_ahead_is_the_limit() -> None:
    check_bookable_time(NOW + timedelta(days=730), NOW)
    with pytest.raises(ValidationFailed) as exc:
        check_bookable_time(NOW + timedelta(days=730, minutes=30), NOW)
    assert exc.value.details is not None
    assert exc.value.details[0]["field"] == "start_time"
