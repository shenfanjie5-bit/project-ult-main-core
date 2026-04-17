"""Shared Pydantic base class for main-core schema objects."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict


class FormalObjectBase(BaseModel):
    """Frozen schema base for formal and runtime contract objects."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    def to_json(self) -> str:
        """Serialize the object using Pydantic's JSON representation."""

        return self.model_dump_json()

    @classmethod
    def from_json(cls, payload: str) -> Self:
        """Deserialize an object from Pydantic JSON."""

        return cls.model_validate_json(payload)


__all__ = ["FormalObjectBase"]
