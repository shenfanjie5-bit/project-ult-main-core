# main-core

Implementation is present for the L1-L8 business chain, formal object schemas,
public assembly entrypoints, and tests.

Source of truth:

- `docs/main-core.project-doc.md`
- `docs/PROGRESS.md`

Current workspace state:

- `src/main_core/` contains implementation packages for:
  - `l1_l2_basis`
  - `l3_features`
  - `l4_world_state`
  - `l5_universe`
  - `l6_alpha`
  - `l7_recommendation`
  - `l8_publish`
  - shared `common` schemas, protocols, contexts, errors, and types
- `src/main_core/public.py` exposes assembly-compatible public entrypoints:
  `health_probe`, `smoke_hook`, `init_hook`, `version_declaration`, and `cli`.
- The MVP20 fixed decision pool has landed in `main_core.l5_universe.mvp20`;
  selection is constrained to exactly 20 manifest targets and ignores
  related-entity context for eligibility.
- Tests cover schemas, package boundaries, L1-L8 behavior, public entrypoints,
  smoke checks, contract alignment, integration paths, and regression fixtures.

What is not claimed here:

- Production rollout is not declared complete by this repository.
- Downstream orchestration, including pin/path updates in orchestrator-owned
  repositories, remains a follow-up outside `main-core`.

Execution rule:

1. read the project doc and `docs/PROGRESS.md` first
2. keep work inside this module unless the issue explicitly targets shared
   contracts
3. do not treat documentation freshness as proof of production rollout

Useful local checks:

```bash
PYTHONPATH=src python3 -m pytest -q tests/l5_universe/test_mvp20.py \
  tests/unit/test_public_entrypoints.py \
  tests/smoke/test_public_smoke.py
```

Boundary checks:

- After installing development dependencies, run `bash scripts/check_boundaries.sh`
  to execute Ruff, import-linter, and the package boundary tests.
