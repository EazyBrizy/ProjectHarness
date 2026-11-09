# PH-051-09 — Scoped changed files (v0.5.1 WIP)

**Источник:** Engine+Docs PH-051-08; **область:** `runtime.py`, `cli.py`, `validation.py`, API exports, `stages.py` continuation/status, targeted tests, docs и mirrors/packaging.

## Production source changes

- `src/project_harness/runtime.py` — project-scoped doctor/execute lifecycle, signed Run boundaries, verification and policy-gated completion; no host agent invocation.
- `src/project_harness/cli.py` — documented public `executor-doctor`/`execute-current`, flags and exit codes.
- `src/project_harness/stages.py` — automatic status/next continuation for exactly active READY Run.
- `src/project_harness/validation.py` — actual runtime verification envelope and exact Apply Evidence schema/binding; direct integration regression fix.
- `src/project_harness/__init__.py` — exports `executor_doctor`, `execute_current`.
- Corresponding `build/lib/project_harness/{runtime,cli,stages,validation,__init__}.py` mirrors synchronized (not a different implementation).

## Targeted tests

- NEW `tests/test_ph_051_09_automatic_runtime.py` — 15 public/API/negative simulated-transport tests.
- Existing `tests/test_ph_051_01_contract_baseline.py`, `tests/test_ph_051_02_executor_protocol.py`, `tests/test_ph_051_03_rootless_podman.py`, `tests/test_ph_051_05_codex_adapter.py`, `tests/test_ph_051_08_atomic_apply.py`: only update obsolete assertions that public automatic routes must be absent. No other behavior/scopes changed.

## Deliverable synchronizations

- Engine `README.md`, `CHANGELOG.md`, `dist/project_harness_engine-0.5.1-py3-none-any.whl`, `MANIFEST.sha256` and this phase reports/logs; executable bit of `bin/project-harness` preserved as in input ZIP.
- Documentation `05_Updates/12_Governed_Automatic_Run_and_Public_CLI_v0.5.1_WIP.md` (new), `CHANGELOG.md`, generated `FILE_INDEX.md`, generated `Project_Harness_Architecture_v0.5.0_FULL.md`, `MANIFEST.sha256`, embedded byte-for-byte copy in `docs/Project_Harness_Documentation_v0.5.1/`.
- All preceding PH-051-01..08 artifacts, historical test reports, embedded registry mirrors and normative specification are unchanged. No schema or registry new revision added.
