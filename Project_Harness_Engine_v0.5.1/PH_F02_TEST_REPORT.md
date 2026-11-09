# PH-F02 final remediation and acceptance report — 2026-10-24

**Verdict: PH-F02 ACCEPTED for handoff to PH-F03.** This is **not** a claim that all v0.5.0 or its later remediation packages are complete. Only the *semantic credibility of Stage Gate evidence* was repaired and accepted.

## Implemented within PH-F02

1. Removed universal `PASS` verification-report promotion: successful preparation does not create false `ARCHITECTURE_RECORD`, `LIMITATIONS_RECORD`, `PERMITTED_USE_RECORD`, `EXTERNAL_EVIDENCE` (or any other unrelated) positive evidence.
2. Enforced exact subject-level `details.semantic_proof` for positive Gate candidates, with registered kind-compatible methods: `DOCUMENT_REVIEW`, `EXECUTED_TEST`, `OPERATOR_VERIFICATION`, `EXTERNAL_SOURCE`.
3. Required a real existing digest-bound local source artifact for each subject; performed checks, exact baseline, test identifier/result/command for tests; actor/review details for manual verification; issuer/origin and exact source identity for external proof. Generic user declarations, verification reports and unverified sources are not Gate-eligible.
4. A completed preparation run without authentic proof stays persisted `BLOCKED`, with a bounded `RESOLVE_STAGE_GATE`/`resume-stage-gate` continuation. Exact repeated recovery cannot mint duplicate identical preparation Tasks or Gate blockers; product/baseline drift requires new pinned proof.
5. After compatible evidence is actually supplied, `resume-stage-gate` independently rechecks it and enables `VERIFYING` with exact `prepare-stage-approval` candidates. Only a separate formal decision through `accept-stage` accepts the Stage.
6. Preserved strict positive-only, canonical refs, tamper protection, source/baseline freshness, formal `NOT_APPLICABLE`, Stage transaction recovery, accepted history, Brownfield read-only semantics and same-level maintenance.

**Trust boundary:** These rules verify provenance *records*, exact subject alignment, source integrity and recorded check outcomes; they do not cryptographically authenticate an external issuer or prove subjective document content true. A named operator must evaluate semantic sufficiency before formal Stage approval. This is the governed v0.5.0 model, **not** an automatic Codex executor or independent third-party verification service.

## Actual tests executed

| Verification | Actual result |
|---|---|
| Complete PH-F02 applicable Python regression suite, including PH-F01 semantic Gate regressions and previous Brownfield, maintenance, strict approval, Stage crash/recovery and migration tests | **128/128 PASS, 488.259 s** |
| PH-F01 Gate-negative cases (generic PASS, wrong subject kinds) | **3/3 PASS** within suite |
| Dedicated semantic proof contract tests | **5/5 PASS** within suite |
| Real selected-test, document, operator and external proof → Gate recovery → strict acceptance | **PASS** within suite |
| Public `accept-stage` CLI with valid generated formal review and evidence, followed by `validate-project` | **PASS** (`TARGET_LEVEL_REACHED`, `PROTOTYPE` accepted) |
| Independent PH-F01 fixture (Greenfield MVP, Brownfield and target reached) | **PASS** within suite |
| Bundled source `doctor` after release manifest regeneration | **PASS** |
| Fresh installation of rebuilt v0.5.0 wheel and installed `project-harness doctor` | **PASS** |
| Python source and tests `compileall` | **PASS** |
| Documentation validator with final ZIP | **36 checks PASS, 0 errors, 0 warnings**; ZIP CRC + exact archive tree PASS |

**Raw result:** `PH_F02_TEST_LOG.txt` contains the full named-test trace and `Ran 128 tests ... OK`. Tests used the `unittest` discovery suite, excluding only the three exact `test_ph_f03_*` cases; the shipped `tests/run_ph_f02_acceptance.py` reproduces that selection and refuses an unexpected exclusion set. From the extracted engine source root, rerun with:

```bash
python tests/run_ph_f02_acceptance.py --list
python tests/run_ph_f02_acceptance.py
python project-harness.py doctor
python -m compileall -q src/project_harness tests
```

The full `python tests/run_tests.py` still includes exactly **three intentionally RED PH-F03 planner-continuation tests**. One was independently reproduced as an expected `FAIL` because `prepare-active-stage-plan` is not yet a public CLI command. **No PH-F03 route or next-stage planner was implemented in PH-F02.** Excluding these *specific future-scope tests only* is necessary to make the PH-F02 acceptance result meaningful; no PH-F02 or older regression tests were skipped.

## Runtime and invariant scope

- Greenfield: ordinary Tasks/JIT, no-op Gate preparation remains blocked; supplied exact Gate evidence → `resume-stage-gate` → `VERIFYING` → formal Prototype acceptance.
- Brownfield: assessment/digest freshness, strict revision resolution, baseline approvals and immutable records remain accepted/rejected as before; synthetic fixtures do not claim independent MVP product certification.
- Maintenance: repeatable same-level Tasks, cancellation and level-up fencing preserved.
- Stage transactions: controlled interruption, crash recovery, rollback, idempotency and mixed-state detection all PASS.
- Future: PH-F03 public active-stage planner, v0.5.1 execution sandbox and v0.6.x Git/deployment remain excluded from this change.

**Artifacts:** updated engine and documentation ZIPs; synchronized embedded docs, regenerated SHA-256 manifests and rebuilt distributable wheel. `PH_F02_CHANGED_FILES.md` lists the files and strict scope. Separate PH-F08 end-to-end release acceptance still remains to be performed.
