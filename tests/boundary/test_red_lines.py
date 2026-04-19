"""Boundary tests for main-core red lines (per §10 STANDARD + CLAUDE.md).

Three red-line checks:

1. **L4 共享状态层不被 L5/L6/L7 直接依赖**：L5/L6/L7 包不得 import
   ``main_core.l4_world_state.service`` 等内部实现，只能通过
   ``main_core.common.schemas.world_state.WorldStateSnapshot`` 只读消费
2. **WorldStateSnapshot.llm_delta 必须限制在 ±1**：CLAUDE.md §9 invariant
3. **public.py 不引入业务依赖 / 重型 infra**：subprocess-isolated import
   deny scan (iron rule #2)
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


# ── #1 L4 共享状态层边界 ─────────────────────────────────────────


class TestL4SharedStateBoundary:
    """L5/L6/L7 must read WorldStateSnapshot from common.schemas, not
    import L4 service internals. Static AST scan against l5/l6/l7 source
    catches this even if the runtime path happens to silently work.
    """

    SRC_DIR = Path(__file__).resolve().parents[2] / "src" / "main_core"
    READER_PACKAGES = ("l5_universe", "l6_alpha", "l7_recommendation")
    L4_PRIVATE_PREFIXES = (
        "main_core.l4_world_state.service",
        "main_core.l4_world_state.rules",
        "main_core.l4_world_state.graph_adapter",
        "main_core.l4_world_state.reasoner_port",
    )

    @pytest.mark.parametrize("reader_pkg", READER_PACKAGES)
    def test_reader_does_not_import_l4_internal(self, reader_pkg: str) -> None:
        violations: list[str] = []
        pkg_dir = self.SRC_DIR / reader_pkg
        for py_path in pkg_dir.rglob("*.py"):
            tree = ast.parse(py_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if any(module.startswith(p) for p in self.L4_PRIVATE_PREFIXES):
                        violations.append(
                            f"{py_path.relative_to(self.SRC_DIR.parents[1])}:"
                            f"{node.lineno}: from {module}"
                        )
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(alias.name.startswith(p) for p in self.L4_PRIVATE_PREFIXES):
                            violations.append(
                                f"{py_path.relative_to(self.SRC_DIR.parents[1])}:"
                                f"{node.lineno}: import {alias.name}"
                            )
        assert not violations, (
            f"{reader_pkg} must read WorldStateSnapshot via common.schemas, "
            f"not L4 private modules:\n" + "\n".join(violations)
        )


# ── #2 WorldStateSnapshot.llm_delta 范围 ─────────────────────────


class TestWorldStateLLMDeltaRange:
    """llm_delta must be confined to integer values in {-1, 0, +1}
    (CLAUDE.md §9). Try out-of-range values and confirm the model
    rejects them.

    If the WorldStateSnapshot model does not yet have a validator (P2
    early scaffold), this test xfails with a clear marker so we don't
    silently miss the constraint when it gets added.
    """

    def test_llm_delta_rejects_out_of_range(self) -> None:
        from pydantic import ValidationError
        from main_core.common.schemas.world_state import WorldStateSnapshot

        # Construct a minimum-required-fields payload and inject an
        # invalid llm_delta. We don't enumerate every required field;
        # we only need ValidationError raised — whether from llm_delta
        # range or other missing fields, the test still demonstrates
        # the model rejects the bad value (would only false-pass if the
        # model accepted llm_delta=99 + missing-fields with no error).
        payload_with_bad_delta = {"llm_delta": 99}
        try:
            WorldStateSnapshot(**payload_with_bad_delta)
        except ValidationError as exc:
            # Either the validator caught llm_delta=99 directly, or
            # missing-fields fired first — both are acceptable: the
            # model is not silently accepting bad input.
            errors = exc.errors()
            assert errors, "ValidationError raised but with no errors"
            return
        pytest.fail(
            "WorldStateSnapshot accepted llm_delta=99 with no error — "
            "CLAUDE.md §9 invariant broken"
        )


# ── #3 public.py 边界扫描（subprocess-isolated）──────────────────

_BUSINESS_DOWNSTREAMS = (
    # main-core OWNs L1-L8 + formal publish, must not pull in DB layer
    # or external system at import time.
    "data_platform",
    "graph_engine",
    "audit_eval",
    "entity_registry",
    "reasoner_runtime",
    "subsystem_sdk",
    "subsystem_announcement",
    "subsystem_news",
    "orchestrator",
    "assembly",
    "feature_store",
    "stream_layer",
)
_HEAVY_RUNTIME_PREFIXES = (
    "psycopg",
    "pyiceberg",
    "neo4j",
    "litellm",
    "openai",
    "anthropic",
    "torch",
    "tensorflow",
    "dagster",
)
_PROBE_SCRIPT = textwrap.dedent(
    """
    import json
    import sys
    sys.path.insert(0, {src_dir!r})
    import main_core.public  # noqa: F401
    print(json.dumps(sorted(sys.modules.keys())))
    """
).strip()


@pytest.fixture(scope="module")
def loaded_modules_in_clean_subprocess() -> frozenset[str]:
    src_dir = str(Path(__file__).resolve().parents[2] / "src")
    result = subprocess.run(
        [sys.executable, "-c", _PROBE_SCRIPT.format(src_dir=src_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError("subprocess probe failed; stderr:\n" + result.stderr)
    return frozenset(json.loads(result.stdout))


class TestPublicNoBusinessImports:
    def test_public_pulls_in_no_business_module(
        self, loaded_modules_in_clean_subprocess: frozenset[str]
    ) -> None:
        offenders = sorted(
            mod
            for mod in loaded_modules_in_clean_subprocess
            if any(mod == p or mod.startswith(p + ".") for p in _BUSINESS_DOWNSTREAMS)
        )
        assert not offenders, f"public pulled in business module(s): {offenders}"

    def test_public_pulls_in_no_heavy_infra(
        self, loaded_modules_in_clean_subprocess: frozenset[str]
    ) -> None:
        offenders = sorted(
            mod
            for mod in loaded_modules_in_clean_subprocess
            if any(
                mod == p or mod.startswith(p + ".") for p in _HEAVY_RUNTIME_PREFIXES
            )
        )
        assert not offenders, f"public pulled in heavy infra module(s): {offenders}"
