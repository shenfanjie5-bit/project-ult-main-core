"""Runtime publish bundle schema."""

from __future__ import annotations

from typing import Any

from main_core.common.schemas import FormalObjectBase
from main_core.common.types import CycleId


class PublishBundle(FormalObjectBase):
    """Phase 3 runtime bundle of formal object payloads and manifest data."""

    cycle_id: CycleId
    formal_objects: dict[str, Any]
    manifest_candidate: dict[str, Any]
    audit_payload: dict[str, Any]
    retrospective_seed: dict[str, Any]
