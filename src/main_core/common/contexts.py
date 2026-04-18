"""Runtime context models passed through explicit main-core protocols."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from main_core.common.schemas import (
    FeatureSignalBundle,
    WorldStateSnapshot,
)
from main_core.common.types import CycleId, EntityId


class AlphaAnalysisContext(BaseModel):
    """Frozen L6 runtime context for analyzer protocol calls."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cycle_id: CycleId
    entity_id: EntityId
    feature_bundle: FeatureSignalBundle
    world_state: WorldStateSnapshot
    similar_cases: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_cycle_and_entity_consistency(self) -> AlphaAnalysisContext:
        """Keep L6 analyzer context anchored to one cycle and entity."""

        if self.feature_bundle.cycle_id != self.cycle_id:
            raise ValueError("feature_bundle.cycle_id must match context.cycle_id")
        if self.world_state.cycle_id != self.cycle_id:
            raise ValueError("world_state.cycle_id must match context.cycle_id")
        if self.feature_bundle.entity_id != self.entity_id:
            raise ValueError("feature_bundle.entity_id must match context.entity_id")
        return self


class WorldStateInputs(BaseModel):
    """Frozen L4 runtime inputs for world-state policy evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cycle_id: CycleId
    feature_bundle: FeatureSignalBundle
    macro_context: dict[str, Any] = Field(default_factory=dict)
    graph_impact: dict[str, Any] = Field(default_factory=dict)


class RecommendationConstraintInputs(BaseModel):
    """Frozen L7 runtime inputs for recommendation constraint gates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    world_state: WorldStateSnapshot
    risk_context: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "AlphaAnalysisContext",
    "RecommendationConstraintInputs",
    "WorldStateInputs",
]
