# PH-F02 — changed files and scope (2026-10-24)

**Change package:** complete the semantic credibility of Stage Gate evidence, preserving the v0.5.0 contract and the PH-F01 regression boundary. **No PH-F03 active-stage planner** or future-version executors/adapters were implemented.

## Runtime implementation

- `src/project_harness/evidence.py`: kind-specific proof methods and strict exact subject/source/test/operator/external semantic checks; positive proof must have pinned source content and source digest.
- `src/project_harness/stage_gate_lifecycle.py`: no generic PASS verification → unrelated PASS evidence cloning; bounded recovery preserves `BLOCKED` until independently supplied proof exists; deterministic no-repeat blocker/preparation handling.
- `src/project_harness/stages.py`: retain the source-aware candidate filtering and strict Stage approval revalidation delivered with the preceding PH-F02 partial patch.

## Regression and PH-F02 integration tests

- New `tests/gate_proof_fixtures.py` — synthetic **test-only** actual selected test invocations, subject-bound operator-reviewed document sources, reviews and external source fixtures; they do not represent third-party production certification.
- New `tests/run_ph_f02_acceptance.py` — reproducible PH-F02 selection; excludes exactly three known PH-F03 planner RED cases, rejects any other exclusion.
- New `tests/test_ph_f02_semantic_proof_contract.py` — generic/user claim rejection; document sources; selected test/result binding; external source identity; tamper detection.
- Updated `tests/test_implementation_levels.py`, `tests/test_stage_gate_preparation_block_recovery.py`, `tests/test_stage_approval_preparation.py` — compliant positive proof, Gate `BLOCKED → VERIFYING` recovery, unchanged Stage acceptance and Brownfield contract checks.
- Updated `tests/test_engine.py`, `tests/test_contract_hardening.py` — previously incorrect expectation of automatic `VERIFYING` after generic PASS replaced by fail-closed `BLOCKED` and independent proof recovery.
- Kept PH-F01 intentional PH-F03 planner RED tests as-is; PH-F01 Gate-negative checks are now green.

## Packaging / operator instructions

- `README.md`, `CHANGELOG.md`, this changed-files list, `PH_F02_TEST_REPORT.md` and `PH_F02_TEST_LOG.txt`.
- Built distribution source mirror `build/lib/project_harness/*` as applicable; rebuilt `dist/project_harness_engine-0.5.0-py3-none-any.whl` (build-time setuptools metadata is not distributed).
- Synced `docs/Project_Harness_Documentation_v0.5.0/` from the independently validated documentation ZIP; updated both ZIP and SHA-256 manifests.
- Documentation sources: `04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md`, `README.md`, `CHANGELOG.md`; regenerated `Project_Harness_Architecture_v0.5.0_FULL.md`, `FILE_INDEX.md`, `VALIDATION_REPORT.md` and `MANIFEST.sha256`.

**Unchanged boundaries:** immutable accepted reports/Stage historical revisions, exact assessment ref/digest, strict formal approvals, Stage transaction journaling and recovery, Brownfield read-only assessment, same-level maintenance, sequential stages, no PH-F03 planning route, no v0.5.1+ adapters.
