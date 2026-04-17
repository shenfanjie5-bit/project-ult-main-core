"""P2 recommendation constraint stubs for L7."""

from __future__ import annotations

from main_core.common.contexts import RecommendationConstraintInputs
from main_core.common.protocols import RecommendationConstraintProviderBase
from main_core.common.schemas import RecommendationSnapshot


class NullConstraintProviderStub(RecommendationConstraintProviderBase):
    """P2 placeholder, wired in milestone-2."""

    def gate(
        self,
        inputs: RecommendationConstraintInputs,
        candidate: RecommendationSnapshot,
    ) -> RecommendationSnapshot:
        """Return the candidate unchanged until real regime/risk gates land."""

        return candidate


__all__ = ["NullConstraintProviderStub"]
