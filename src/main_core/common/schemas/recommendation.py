"""L7 formal recommendation schema."""

from __future__ import annotations

from typing import Any, Literal

from main_core.common.schemas.base import FormalObjectBase
from main_core.common.types import CycleId, EntityId

ActionType = Literal["buy", "hold", "reduce", "inconclusive"]
TriggerSource = Literal["system", "human_decision"]


class RecommendationSnapshot(FormalObjectBase):
    """Formal L7 recommendation snapshot described in §9.3."""

    cycle_id: CycleId
    entity_id: EntityId
    action_type: ActionType
    rating: str | None
    confidence: float | None
    triggered_by: TriggerSource
    override_applied: bool
    constraints_applied: dict[str, Any]


__all__ = ["ActionType", "RecommendationSnapshot", "TriggerSource"]
