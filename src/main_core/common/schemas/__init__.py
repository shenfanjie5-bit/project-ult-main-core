"""Pydantic schemas for main-core formal and runtime objects."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict


class FormalObjectBase(BaseModel):
    """Shared immutable base model for explicit cross-layer contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    def to_json(self) -> str:
        """Serialize the model to a JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, s: str) -> Self:
        """Deserialize a JSON string into the concrete model type."""
        return cls.model_validate_json(s)


from .alpha import (  # noqa: E402
    AlphaResultSnapshot,
    AlphaStatus,
    AnalyzerType,
    single_prompt_result,
)
from .dashboard import DashboardSnapshot  # noqa: E402
from .feature_bundle import FeatureSignalBundle  # noqa: E402
from .override import OverrideRecord  # noqa: E402
from .pool import OfficialAlphaPool  # noqa: E402
from .publish import PublishBundle  # noqa: E402
from .recommendation import ActionType, RecommendationSnapshot  # noqa: E402
from .report import FormalReport  # noqa: E402
from .world_state import WorldStateSnapshot  # noqa: E402

__all__ = [
    "ActionType",
    "AlphaResultSnapshot",
    "AlphaStatus",
    "AnalyzerType",
    "DashboardSnapshot",
    "FeatureSignalBundle",
    "FormalObjectBase",
    "FormalReport",
    "OfficialAlphaPool",
    "OverrideRecord",
    "PublishBundle",
    "RecommendationSnapshot",
    "WorldStateSnapshot",
    "single_prompt_result",
]
