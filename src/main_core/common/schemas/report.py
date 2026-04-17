"""Formal report schema."""

from __future__ import annotations

from typing import Any

from main_core.common.schemas import FormalObjectBase
from main_core.common.types import CycleId


class FormalReport(FormalObjectBase):
    """L8 formal report for human consumption."""

    cycle_id: CycleId
    report_type: str
    recommendation_ref: str
    narrative_sections: dict[str, Any]
    appendix_refs: dict[str, Any]
