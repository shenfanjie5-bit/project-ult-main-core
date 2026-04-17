"""Formal dashboard snapshot schema."""

from __future__ import annotations

from typing import Any

from main_core.common.schemas import FormalObjectBase
from main_core.common.types import CycleId


class DashboardSnapshot(FormalObjectBase):
    """L8 formal dashboard-facing snapshot."""

    cycle_id: CycleId
    world_state_ref: str
    pool_ref: str
    recommendation_ref: str
    summary_cards: dict[str, Any]
