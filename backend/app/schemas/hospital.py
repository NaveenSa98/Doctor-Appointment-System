"""Hospital response shape."""

import uuid

from pydantic import BaseModel, ConfigDict


class HospitalOut(BaseModel):
    """A hospital in lists and inside other responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
