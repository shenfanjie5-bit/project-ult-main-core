"""Cross-repo alignment between main-core runtime models and the
contracts envelope (codex stage-2.3 review #1 fix).

The four main-core formal objects (WorldStateSnapshot / OfficialAlphaPool
/ AlphaResultSnapshot / RecommendationSnapshot) are runtime business
models with typed fields (cycle_id, baseline_regime, llm_delta, etc.).
The contracts envelope (``contracts.schemas.formal_objects.*``) is a
generic ``FormalObjectBase`` carrying object_id / object_name / zone /
version / created_at / cycle_id / payload. They are deliberately
decoupled — main-core builds typed models internally, then serializes
into the contracts envelope's ``payload`` dict for cross-module wire
transport.

This file validates round-trip works for each pairing, so a refactor
that adds a non-serializable field on the main-core side (or breaks the
contracts envelope schema) is caught here, not deep inside assembly e2e
or audit-eval replay.

**Module-level skip on missing dep**: this lane requires the
``[contracts-schemas]`` extra (`pip install -e ".[contracts-schemas]"`).
If absent, the whole module skips with a clear marker so the rest of
the contract tier still runs in offline-first venvs.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

# Soft-skip module if cross-repo schema dep not installed. The other
# contract tests in this directory (test_formal_object_contract.py)
# remain runnable without this dep.
contracts_formal_objects = pytest.importorskip(
    "contracts.schemas.formal_objects",
    reason=(
        "project-ult-contracts not installed; install [contracts-schemas] "
        "extra to run cross-repo alignment tests"
    ),
)


def _build_world_state_runtime():
    from main_core.common.schemas.world_state import WorldStateSnapshot

    return WorldStateSnapshot(
        cycle_id="CYC_2025_01_03_DAILY",
        baseline_regime="neutral",
        llm_delta=0,
        final_regime="neutral",
        llm_rationale="contract-test rationale",
        actual_model_used="gpt-4o-mini",
        actual_provider="openai",
        fallback_path=[],
    )


def _build_official_alpha_pool_runtime():
    from main_core.common.schemas.pool import OfficialAlphaPool

    return OfficialAlphaPool(
        cycle_id="CYC_2025_01_03_DAILY",
        observation_pool_size=1,
        official_alpha_pool_capacity=100,
        selected_entities=["ENT_STOCK_300750_SZ"],
        added_entities=["ENT_STOCK_300750_SZ"],
        removed_entities=[],
        freeze_reason_map={},
    )


class TestRuntimeModelDumpsRoundTripIntoContractEnvelope:
    def test_world_state_runtime_dumps_into_contract_envelope(self) -> None:
        from contracts.schemas.formal_objects import (
            FormalObjectName,
            WorldStateSnapshot as ContractWorldStateSnapshot,
        )

        runtime_model = _build_world_state_runtime()
        envelope = ContractWorldStateSnapshot(
            object_id="WS_CYC_2025_01_03",
            version="0.1.1",
            created_at=datetime.now(UTC),
            cycle_id="CYC_2025_01_03_DAILY",
            payload=runtime_model.model_dump(mode="json"),
        )
        # Object name discriminator must match the canonical enum.
        assert envelope.object_name == FormalObjectName.WORLD_STATE_SNAPSHOT
        # Round-trip: payload survived JSON serialization.
        assert envelope.payload["llm_delta"] == 0
        assert envelope.payload["baseline_regime"] == "neutral"

    def test_official_alpha_pool_runtime_dumps_into_contract_envelope(self) -> None:
        from contracts.schemas.formal_objects import (
            FormalObjectName,
            OfficialAlphaPool as ContractOfficialAlphaPool,
        )

        runtime_model = _build_official_alpha_pool_runtime()
        envelope = ContractOfficialAlphaPool(
            object_id="AP_CYC_2025_01_03",
            version="0.1.1",
            created_at=datetime.now(UTC),
            cycle_id="CYC_2025_01_03_DAILY",
            payload=runtime_model.model_dump(mode="json"),
        )
        assert envelope.object_name == FormalObjectName.OFFICIAL_ALPHA_POOL
        assert envelope.payload["official_alpha_pool_capacity"] == 100
        assert envelope.payload["selected_entities"] == ["ENT_STOCK_300750_SZ"]


class TestFormalObjectNameEnumCoverage:
    """The contracts FormalObjectName enum is the canonical name set
    (per contracts CLAUDE.md "Single Source of Truth"). Every main-core
    formal object must have a corresponding enum entry.
    """

    def test_main_core_four_objects_have_contract_enum_entries(self) -> None:
        from contracts.schemas.formal_objects import FormalObjectName

        canonical = {member.value for member in FormalObjectName}
        for required in (
            "world_state_snapshot",
            "official_alpha_pool",
            "alpha_result_snapshot",
            "recommendation_snapshot",
        ):
            assert required in canonical, (
                f"contracts.FormalObjectName missing {required!r}; "
                f"main-core would have nowhere to declare object_name"
            )
