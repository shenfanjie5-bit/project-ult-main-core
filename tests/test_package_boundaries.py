"""Static package boundary checks for the main-core package skeleton."""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXIT_SUCCESS = 0

LAYER_PACKAGES = (
    "l1_l2_basis",
    "l3_features",
    "l4_world_state",
    "l5_universe",
    "l6_alpha",
    "l7_recommendation",
    "l8_publish",
)


def _format_process_output(result: subprocess.CompletedProcess[str]) -> str:
    return f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def _run_lint_imports(cwd: Path) -> subprocess.CompletedProcess[str]:
    lint_imports = shutil.which("lint-imports")
    if lint_imports is None:
        pytest.skip("import-linter CLI is not installed; run `pip install -e .[dev]`")

    env = os.environ.copy()
    package_root = cwd / "src" if (cwd / "src").exists() else cwd
    python_path = [str(package_root)]
    if existing_python_path := env.get("PYTHONPATH"):
        python_path.append(existing_python_path)
    env["PYTHONPATH"] = os.pathsep.join(python_path)

    return subprocess.run(
        [lint_imports, "--config", ".importlinter"],
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_all_layers_importable() -> None:
    for package in LAYER_PACKAGES:
        importlib.import_module(f"main_core.{package}")


def test_importlinter_contracts_pass() -> None:
    result = _run_lint_imports(PROJECT_ROOT)

    assert result.returncode == EXIT_SUCCESS, _format_process_output(result)


def test_forbidden_contract_triggers_on_synthetic_violation(tmp_path: Path) -> None:
    synthetic_root = tmp_path / "main_core"
    synthetic_root.mkdir()
    (synthetic_root / "__init__.py").write_text('"""Synthetic main-core package."""\n')

    for package in LAYER_PACKAGES:
        package_dir = synthetic_root / package
        package_dir.mkdir()
        package_body = '"""Synthetic layer package."""\n'
        if package == "l3_features":
            package_body += "from main_core.l6_alpha import *\n"
        (package_dir / "__init__.py").write_text(package_body)

    shutil.copyfile(PROJECT_ROOT / ".importlinter", tmp_path / ".importlinter")

    result = _run_lint_imports(tmp_path)

    assert result.returncode != EXIT_SUCCESS, _format_process_output(result)
