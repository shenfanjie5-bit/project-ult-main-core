#!/usr/bin/env bash
set -euo pipefail

ruff check .

if command -v lint-imports >/dev/null 2>&1; then
  lint-imports
else
  echo "lint-imports is not installed; skipping import-linter contracts"
fi

if command -v pytest >/dev/null 2>&1; then
  pytest tests/test_package_boundaries.py
else
  python3 -m pytest tests/test_package_boundaries.py
fi
