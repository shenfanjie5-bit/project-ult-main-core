"""Formal official alpha pool schema."""

from __future__ import annotations

from pydantic import field_validator, model_validator

from main_core.common.schemas import FormalObjectBase
from main_core.common.types import CycleId, EntityId


class OfficialAlphaPool(FormalObjectBase):
    """L5 formal core pool and cycle-level change record."""

    cycle_id: CycleId
    observation_pool_size: int
    official_alpha_pool_capacity: int = 100
    selected_entities: list[EntityId]
    added_entities: list[EntityId]
    removed_entities: list[EntityId]
    freeze_reason_map: dict[EntityId, str]

    @field_validator("official_alpha_pool_capacity")
    @classmethod
    def validate_positive_capacity(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("official_alpha_pool_capacity must be > 0")
        return value

    @model_validator(mode="after")
    def validate_selected_entity_capacity(self) -> OfficialAlphaPool:
        if len(self.selected_entities) > self.official_alpha_pool_capacity:
            raise ValueError(
                "selected_entities length must be <= official_alpha_pool_capacity"
            )
        return self
