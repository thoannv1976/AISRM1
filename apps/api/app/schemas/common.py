"""Shared schema bases."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IdMixin(ORMBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MessageOut(BaseModel):
    message: str
    ok: bool = True
