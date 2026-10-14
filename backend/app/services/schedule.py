"""Pure scheduling rules: which start times a doctor's weekly sessions allow.

No database here. Sessions are wall-clock times at the clinic, a fixed offset from UTC;
every datetime that comes in or goes out is timezone-aware UTC.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta, timezone

SLOT_LENGTH = timedelta(minutes=30)


@dataclass(frozen=True)
class SessionRule:
    """One weekly session as plain data (Monday is weekday 0)."""

    hospital_id: uuid.UUID
    weekday: int
    start: time
    end: time
    skipped: frozenset[date] = field(default_factory=frozenset)


def clinic_tz(offset_minutes: int) -> timezone:
    """The clinic's fixed-offset timezone."""
    return timezone(timedelta(minutes=offset_minutes))


def to_clinic(moment: datetime, offset_minutes: int) -> datetime:
    """A UTC instant as clinic wall-clock time."""
    return moment.astimezone(clinic_tz(offset_minutes))


def covers(rule: SessionRule, hospital_id: uuid.UUID, local: datetime) -> bool:
    """True if the session runs at this hospital, on this local day, and `local` is a slot start."""
    return (
        rule.hospital_id == hospital_id
        and rule.weekday == local.weekday()
        and local.date() not in rule.skipped
        and rule.start <= local.time().replace(tzinfo=None) < rule.end
    )


def slot_allowed(
    rules: Iterable[SessionRule], hospital_id: uuid.UUID, start: datetime, offset_minutes: int
) -> bool:
    """True if some session covers this start time at this hospital."""
    local = to_clinic(start, offset_minutes)
    return any(covers(rule, hospital_id, local) for rule in rules)


def generate_slots(
    rules: Iterable[SessionRule],
    hospital_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
    offset_minutes: int,
) -> list[datetime]:
    """Every bookable start (UTC, ascending) in [date_from, date_to) at one hospital."""
    tz = clinic_tz(offset_minutes)
    first = date_from.astimezone(tz).date()
    last = date_to.astimezone(tz).date()
    slots: set[datetime] = set()
    for rule in rules:
        if rule.hospital_id != hospital_id:
            continue
        for offset in range((last - first).days + 1):
            day = first + timedelta(days=offset)
            if day.weekday() != rule.weekday or day in rule.skipped:
                continue
            cursor = datetime.combine(day, rule.start, tzinfo=tz)
            stop = datetime.combine(day, rule.end, tzinfo=tz)
            while cursor < stop:
                moment = cursor.astimezone(UTC)
                if date_from <= moment < date_to:
                    slots.add(moment)
                cursor += SLOT_LENGTH
    return sorted(slots)


def overlaps(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    """True if two same-day time ranges share any time."""
    return a_start < b_end and b_start < a_end
