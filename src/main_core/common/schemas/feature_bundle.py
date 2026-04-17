"""Runtime feature and signal bundle schema."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from pydantic import field_validator

from main_core.common.schemas import FormalObjectBase
from main_core.common.types import CycleId, EntityId


class FeatureSignalBundle(FormalObjectBase):
    """L3 runtime bundle shared with downstream layers during one cycle."""

    cycle_id: CycleId
    entity_id: EntityId
    feature_values: dict[str, float]
    signal_values: dict[str, Any]
    graph_features: dict[str, Any]
    feature_weight_multiplier: dict[str, float]
    generated_at: datetime

    @field_validator("feature_weight_multiplier")
    @classmethod
    def validate_positive_multipliers(cls, value: dict[str, float]) -> dict[str, float]:
        for feature_name, multiplier in value.items():
            if not math.isfinite(multiplier) or multiplier <= 0:
                raise ValueError(
                    f"feature_weight_multiplier[{feature_name!r}] must be finite and > 0"
                )
        return value
