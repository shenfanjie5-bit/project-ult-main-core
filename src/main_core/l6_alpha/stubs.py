"""P2 analyzer stubs for L6 alpha analysis."""

from __future__ import annotations

from typing import ClassVar

from main_core.common.contexts import AlphaAnalysisContext
from main_core.common.protocols import AnalyzerBase
from main_core.common.schemas import AlphaResultSnapshot
from main_core.common.types import EntityId


class SinglePromptAnalyzerStub(AnalyzerBase):
    """P2 placeholder, wired in milestone-2."""

    analyzer_type: ClassVar[str] = "single_prompt_v1"

    def analyze(
        self,
        entity_id: EntityId,
        context: AlphaAnalysisContext,
    ) -> AlphaResultSnapshot:
        """Reserve the L6 analyzer contract until the real implementation lands."""

        raise NotImplementedError("implemented in #9")


__all__ = ["SinglePromptAnalyzerStub"]
