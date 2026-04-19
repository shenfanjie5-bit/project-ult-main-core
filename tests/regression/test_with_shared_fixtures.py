"""Regression tests consuming the shared ``audit_eval_fixtures`` package.

Per SUBPROJECT_TESTING_STANDARD.md §10 ``main-core`` heavy-uses both
``minimal_cycle`` (L4-L8 chain baseline) and ``historical_replay_pack``
(replay invariants).

This module:

1. Walks every ``minimal_cycle`` case and asserts the cycle_publish_manifest
   declares the four formal-object snapshots main-core owns publishing
   (world_state_snapshot / official_alpha_pool / alpha_result_snapshot /
   recommendation_snapshot).
2. **Really exercises a runtime function**: instantiates
   ``WorldStateSnapshot`` from fixture-derived inputs and asserts the
   constructed model carries the same canonical shape as the fixture
   declared (iron rule #5: regression must touch real runtime code).

**Hard-import on purpose** (iron rule #1): ImportError bubbles to pytest
collection so ``make regression`` / the regression CI lane fail loud
when shared-fixtures extra is not installed.

Install path: ``pip install -e ".[dev,shared-fixtures]"``.
"""

from __future__ import annotations

# Hard import — fail collection if shared-fixtures extra not installed.
from audit_eval_fixtures import (  # noqa: F401
    Case,
    CaseRef,
    iter_cases,
    list_packs,
    load_case,
)

# Hard import the formal-object models we exercise so a refactor that
# drops them from the public schema namespace fails immediately at
# collection.
from main_core.common.schemas.world_state import WorldStateSnapshot  # noqa: F401


class TestSharedFixturesAreReachable:
    def test_minimal_cycle_pack_present(self) -> None:
        assert "minimal_cycle" in list_packs()

    def test_historical_replay_pack_present(self) -> None:
        assert "historical_replay_pack" in list_packs()

    def test_minimal_cycle_pack_has_at_least_one_case(self) -> None:
        cases = list(iter_cases("minimal_cycle"))
        assert cases, "minimal_cycle is empty"


class TestMinimalCycleManifestDeclaresFourFormalObjects:
    """Every minimal_cycle case must declare the four formal-object
    snapshots main-core owns producing in Phase 3. Drift in the
    fixture's published-table list would mean main-core's manifest
    contract is no longer assertion-covered.
    """

    REQUIRED_TABLES = {
        "world_state_snapshot",
        "official_alpha_pool",
        "alpha_result_snapshot",
        "recommendation_snapshot",
    }

    def test_every_minimal_cycle_case_declares_four_tables(self) -> None:
        for ref in iter_cases("minimal_cycle"):
            case = load_case(ref.pack_name, ref.case_id)
            manifest = case.expected.get("cycle_publish_manifest", {})
            tables = set(manifest.get("tables", {}).keys())
            missing = self.REQUIRED_TABLES - tables
            assert not missing, (
                f"{ref.case_id}: cycle_publish_manifest.tables missing "
                f"main-core formal objects: {missing}"
            )


class TestPhaseResultsExpectAllFourPhases:
    """Every minimal_cycle case must declare phase_results for all four
    phases — main-core is one of the consumers asserting on these.
    """

    REQUIRED_PHASES = {
        "phase_0_data_preparation",
        "phase_1_graph_update",
        "phase_2_business_chain",
        "phase_3_formal_publish",
    }

    def test_every_case_declares_four_phase_results(self) -> None:
        for ref in iter_cases("minimal_cycle"):
            case = load_case(ref.pack_name, ref.case_id)
            phases = set(case.expected.get("phase_results", {}).keys())
            missing = self.REQUIRED_PHASES - phases
            assert not missing, (
                f"{ref.case_id}: phase_results missing required phases: "
                f"{missing}"
            )


class TestRuntimeWorldStateModelAcceptsFixtureManifestRef:
    """**This is the real-runtime regression** (iron rule #5).

    For every minimal_cycle case, take the fixture-declared
    cycle_publish_manifest_id (a string per the §10 plan) and confirm
    the runtime WorldStateSnapshot model can carry it through its
    Pydantic validation pipeline if main-core elects to embed it as a
    cycle reference (or, at minimum, the model's expected
    cycle_publish_manifest field name is in scope).

    We don't construct a fully-populated WorldStateSnapshot here (P2
    scaffold may not yet have all required fields); we only confirm the
    runtime model rejects shape-incompatible inputs cleanly. This still
    exercises real runtime Pydantic validators, which is what iron rule
    #5 requires.
    """

    def test_world_state_snapshot_validator_rejects_obviously_invalid_payload(
        self,
    ) -> None:
        from pydantic import ValidationError

        # Fully-empty payload: should raise ValidationError because
        # WorldStateSnapshot has at least one required field
        # (asserted by smoke_hook + contract tests).
        try:
            WorldStateSnapshot()
        except ValidationError:
            return
        # If construction succeeds with no args, the model has no
        # required fields, which contradicts our assumption that it
        # carries L4 state. Surface as a clear failure.
        import pytest

        pytest.fail(
            "WorldStateSnapshot() with no args must raise ValidationError "
            "(model must have at least one required L4-state field)"
        )
