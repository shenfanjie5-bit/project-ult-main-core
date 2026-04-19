PYTHON ?= python3
PYTHONPATH ?= src
export PYTHONPATH

.PHONY: install install-shared test test-fast smoke regression lint typecheck ci

# Pure-pip dev install — offline-first per SUBPROJECT_TESTING_STANDARD.md §2.2.
install:
	$(PYTHON) -m pip install -e ".[dev]"

# install-shared adds the shared-fixtures git extra needed by tests/regression.
install-shared:
	$(PYTHON) -m pip install -e ".[dev,shared-fixtures]"

# Full suite — legacy tests/{l1_l2_basis,l3_features,...} + new canonical
# tier dirs (tests/{unit,contract,boundary,smoke,regression}).
test:
	$(PYTHON) -m pytest

# Fast lane for PR CI and local pre-commit. unit + boundary only.
test-fast:
	$(PYTHON) -m pytest tests/unit tests/boundary -q

# Minimal smoke — exercises public entrypoints. Infra-free.
smoke:
	$(PYTHON) -m pytest tests/smoke -q

# Regression tier — explicit entry. Hard-fails when audit_eval_fixtures
# is not installed (no silent skip per iron rule #1).
regression:
	$(PYTHON) -m pytest tests/regression -q

lint:
	$(PYTHON) -m ruff check . || true

typecheck:
	$(PYTHON) -m mypy src tests || true

ci: test
