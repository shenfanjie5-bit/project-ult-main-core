"""Formal recommendation snapshot schema."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import model_validator

from main_core.common.schemas import FormalObjectBase
from main_core.common.types import CycleId, EntityId

ActionType = Literal["buy", "hold", "reduce", "inconclusive"]


class RecommendationSnapshot(FormalObjectBase):
    """L7 formal recommendation for one entity."""

    cycle_id: CycleId
    entity_id: EntityId
    action_type: ActionType
    rating: str | None
    confidence: float | None
    triggered_by: Literal["system", "human_decision"]
    override_applied: bool
    constraints_applied: dict[str, Any]

    @model_validator(mode="after")
    def validate_inconclusive_confidence(self) -> RecommendationSnapshot:
        if self.action_type == "inconclusive" and self.confidence is not None:
            raise ValueError("inconclusive recommendation must not include confidence")
        return self
