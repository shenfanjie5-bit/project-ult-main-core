#!/usr/bin/env bash
set -euo pipefail

ruff check .
lint-imports

if command -v pytest >/dev/null 2>&1; then
  pytest tests/test_package_boundaries.py
else
  python3 -m pytest tests/test_package_boundaries.py
fi
