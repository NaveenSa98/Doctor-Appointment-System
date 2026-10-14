"""Weekly session rules, without a database."""

import uuid
from datetime import UTC, date, datetime, time

from app.services.schedule import SessionRule, generate_slots, overlaps, slot_allowed, to_clinic

HOSPITAL = uuid.uuid4()
OTHER_HOSPITAL = uuid.uuid4()
SRI_LANKA = 330  # UTC+05:30, no daylight saving
MONDAY = date(2030, 1, 14)


def utc(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2030, 1, day, hour, minute, tzinfo=UTC)


def monday_morning(**overrides: object) -> SessionRule:
    values: dict[str, object] = {
        "hospital_id": HOSPITAL,
        "weekday": 0,
        "start": time(9, 0),
        "end": time(11, 0),
    }
    values.update(overrides)
    return SessionRule(**values)  # type: ignore[arg-type]


def test_slots_are_every_half_hour_in_clinic_time_returned_as_utc() -> None:
    slots = generate_slots([monday_morning()], HOSPITAL, utc(13, 0), utc(16, 0), SRI_LANKA)
    # 09:00, 09:30, 10:00, 10:30 at UTC+05:30
    assert slots == [utc(14, 3, 30), utc(14, 4, 0), utc(14, 4, 30), utc(14, 5, 0)]


def test_the_window_is_inclusive_at_the_start_and_exclusive_at_the_end() -> None:
    rule = [monday_morning()]
    assert generate_slots(rule, HOSPITAL, utc(14, 4, 0), utc(14, 5, 0), SRI_LANKA) == [
        utc(14, 4, 0),
        utc(14, 4, 30),
    ]


def test_other_hospitals_and_other_weekdays_have_no_slots() -> None:
    rule = [monday_morning()]
    assert generate_slots(rule, OTHER_HOSPITAL, utc(13, 0), utc(16, 0), SRI_LANKA) == []
    assert generate_slots([monday_morning(weekday=1)], HOSPITAL, utc(14, 0), utc(15, 0), 0) == []


def test_skipped_days_have_no_slots() -> None:
    rule = [monday_morning(skipped=frozenset({MONDAY}))]
    assert generate_slots(rule, HOSPITAL, utc(13, 0), utc(16, 0), SRI_LANKA) == []
    next_monday = generate_slots(rule, HOSPITAL, utc(20, 0), utc(23, 0), SRI_LANKA)
    assert len(next_monday) == 4  # only the skipped Monday is affected


def test_the_clinic_day_decides_the_weekday_not_the_utc_day() -> None:
    # Monday 01:00 at UTC+05:30 is still Sunday 19:30 in UTC.
    rule = [monday_morning(start=time(1, 0), end=time(2, 0))]
    slots = generate_slots(rule, HOSPITAL, utc(13, 0), utc(15, 0), SRI_LANKA)
    assert slots == [utc(13, 19, 30), utc(13, 20, 0)]


def test_slot_allowed_covers_the_last_slot_but_not_the_end_time() -> None:
    rules = [monday_morning()]
    assert slot_allowed(rules, HOSPITAL, utc(14, 5, 0), SRI_LANKA)  # 10:30 local, last slot
    assert not slot_allowed(rules, HOSPITAL, utc(14, 5, 30), SRI_LANKA)  # 11:00 local, the end
    assert not slot_allowed(rules, HOSPITAL, utc(14, 3, 0), SRI_LANKA)  # 08:30 local
    assert not slot_allowed(rules, OTHER_HOSPITAL, utc(14, 4, 0), SRI_LANKA)


def test_slot_allowed_respects_skipped_days() -> None:
    rules = [monday_morning(skipped=frozenset({MONDAY}))]
    assert not slot_allowed(rules, HOSPITAL, utc(14, 4, 0), SRI_LANKA)


def test_to_clinic_applies_the_fixed_offset() -> None:
    local = to_clinic(utc(14, 3, 30), SRI_LANKA)
    assert (local.hour, local.minute, local.weekday()) == (9, 0, 0)


def test_overlaps_treats_touching_ranges_as_separate() -> None:
    assert overlaps(time(9), time(12), time(11), time(13))
    assert overlaps(time(9), time(12), time(10), time(11))
    assert not overlaps(time(9), time(12), time(12), time(14))
    assert not overlaps(time(9), time(12), time(7), time(9))
