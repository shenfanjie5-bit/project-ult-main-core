"""Override business record schema."""

from __future__ import annotations

from datetime import datetime

from main_core.common.schemas.base import FormalObjectBase
from main_core.common.schemas.recommendation import ActionType
from main_core.common.types import CycleId, EntityId


class OverrideRecord(FormalObjectBase):
    """Human override record for L7 recommendation decisions."""

    cycle_id: CycleId
    entity_id: EntityId
    submitted_by: str
    action_type: ActionType
    rationale: str
    submitted_at: datetime


__all__ = ["OverrideRecord"]
