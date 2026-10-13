"""Types shared by several schemas."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, PlainSerializer


def _to_utc_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


# A datetime that is always sent to clients as ISO-8601 UTC with a trailing "Z".
UtcDatetime = Annotated[datetime, PlainSerializer(_to_utc_z, return_type=str, when_used="json")]


class Page[T](BaseModel):
    """One page of a list, with the totals needed for pagination controls."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
