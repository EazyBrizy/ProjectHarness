# PH-LW-01 — фактический test report и decision record

**Дата:** 2026-11-01  
**Engine:** 0.5.1 WIP / PH-051-11-derived  
**Companion:** 0.1.0-dev, CONTRACT ONLY / NOT IMPLEMENTED  
**Среда фактического прогона:** Linux-6.18.57-x86_64-with-glibc2.41, Python 3.13.5  
**Native Windows/NTFS/browser/installer:** **NOT RUN**, не эмулированы.  
**Verdict:** PH-LW-01 контрактная часть разработана; exact promised PH-051-12 input **MISSING**, `LOCAL_WEB_MANUAL: NO-GO / NOT IMPLEMENTED`, `AUTOMATIC_EXECUTOR: NO-GO`, полный v0.5.1 NOT RELEASED.

## Preflight — фактическое происхождение

| Input | SHA-256 фактически | CRC | Manifest |
|---|---|---|---|
| Engine PH-051-11 | `44b75136131d917403b99299077e829c025783a6bb94c2b539fbe0b913449dbd` | PASS | 747 exact entries PASS |
| Documentation PH-051-11 | `17ab78d0412c713fabf957bd54e7cc65d0b8dc77d358fe0d7f9f2635bca172fd` | PASS | 132 exact entries PASS |
| Immutable specs ZIP | `56bca615b7da5a0f48d0479c2de24ccd151fcefbf453fdfea89eab0d2675219e` | PASS | 10 exact entries PASS |
| Windows Local Web prompts r2 | `4d85691a5bc89a9ef3a449097898d8b727a041e70c0b13ec9ba45535bcce2829` | PASS | 20 exact entries PASS |

Requested source baseline declared in full PH-LW-01 prompt: Engine `c4bd7bd446f926f32ccfe185fe89ede27207ca6ef0998a35ba3c971293b91174`, Docs `3a5eee4fac314b5ecaec2edb338d64dd26ecddecc3d0e9212fdeff62ca88209a`, and `PH_051_12_TEST_REPORT.md`. **None of those two exact ZIPs nor that report was supplied.** The only actual Engine/Documentation snapshot is PH-051-11 (see preflight). Thus this is *not* an implementation on the specified exact PH-051-12 revision; this remains a provenance blocker for strict PH-LW-01 acceptance. It does not prevent additive contract/fixtures from being delivered for review. Historical PH-051-12 count 346 is NOT a new run result.

Normative `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md` SHA-256 `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e` verified; normative v0.5.0 SHA-256 `ca487d3e978af116418a597b5d05cd890d11e2e93855c9f7a312e21f083dd16f`. Neither document changed.

## Scope и реализованные артефакты

1. 26-command exact control map `resources/local_web/control_map_v1.json`: real CLI parser names, Python modules/public callables, screen/consent/context, read vs mutation, status and test ID. `demo` CLI present but wrapper is private/destructive, UI explicitly DISABLED. `execute-current` explicitly disabled on Windows manual companion, `executor-doctor` only diagnostic.
2. Strict JSON shell schemas: `gpt_exchange_reply_v1.schema.json` draft-only and `operation_receipt_v1.schema.json` local receipt; core Project Input/Stage/Gate schemas unchanged. UI import MUST additionally verify exact context and core schema/approvals, not assume that JSON envelope validation itself authorizes mutation.
3. Pinned dependency names + published SHA256 wheel hashes (including PyYAML) in `local_web/requirements-web-win_amd64-cp314.lock` and inventory; Python 3.14.10 x64 / Flask 3.1.3 / Waitress 3.0.2 / PyInstaller 6.22.3 / Inno Setup 6.7.4 `PrivilegesRequired=lowest` selected. No offline wheelhouse/frozen bundle/installer created; pin compatibility on actual Windows: NOT RUN.
4. Seven docs in `13_Local_Web_Manual_Companion`, README link, accepted-scope threat/budget/GT draft/invalidation/operation journal/Windows CI plan; original engine runtime logic untouched.
5. Fixture source MD, Unicode nested MD ZIP, no-document strict draft, Brownfield repository, untrusted GPT response, stage/maintenance recipe and **opt-in** synthetic CLI generator. Generated project attempt reached timeout in this environment; no success claim. Its opt-in denial and non-overwrite safeguards both returned the expected exit 2 (`PH_LW_01_ADVANCED_FIXTURE_NEGATIVE_NO_OPTIN.log`, `PH_LW_01_ADVANCED_FIXTURE_NEGATIVE_NO_OVERWRITE.log`).
6. Windows-only `local_web/ci_ph_lw_01_windows.ps1` checks actual Windows 11 x64/NTFS, source imports, doctor, full regression and docs validation; not executed on Linux.
7. Engine wheel rebuilt with packaged `resources/local_web/*.json`; console package remains without mandatory Flask/Waitress imports. Historical reports, normative specs and existing accepted records not overwritten.

## Tests — actual results / logs

| Verification | Command/evidence | Result |
|---|---|---|
| Input archive integrity | `PREFLIGHT_ARCHIVE_INTEGRITY.json`, CRC + all source manifest hashes | **PASS**: Engine 747, Docs 132 |
| Targeted contract | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_lw_01_contract` | **PASS**: 9/9, 0 FAIL; `PH_LW_01_TARGETED_CONTRACT.log` |
| Documentation source/standalone ZIP | `python tools/validate_documentation.py <docs-root> --zip <PH_LW_01-docs.zip> --json <report>` | **PASS**: 36/36, 0 errors, 0 warnings, CRC/manifests; `PH_LW_01_DOC_FINAL_VALIDATOR.json` |
| Source doctor | `PYTHONPATH=src:. python project-harness.py doctor` with regenerated manifest | **PASS**, exact resource mirrors; `PH_LW_01_ENGINE_DOCTOR_PRELIM.log` |
| Wheel packaging | `python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist` | **PASS**: packaged four local_web JSON resources; `PH_LW_01_WHEEL_BUILD.log` |
| Installed wheel smoke (Linux) | venv with `--system-site-packages`, `pip install --no-index --no-deps`, resource lookup, `--version`, `doctor` | **PASS**; `PH_LW_01_WHEEL_INSTALL_SMOKE.log`. This does not prove standalone no-PyYAML install or Windows compatibility |
| Existing regression monolithic baseline | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python tests/run_tests.py` | INCOMPLETE_INTERRUPTED_NOT_ACCEPTED: 317 completed tests visible; this is NOT full PASS |
| Full final regression by module | 31 `tests.test_*.py` modules separately via unittest, up to 6 concurrent workers, exact log per module | **PASS**: 351 tests, 2 skipped, 31 modules; exact per-module log + JSON |
| Redundant monolithic final attempt | `python tests/run_tests.py` in staging prior to final docs/fixtures, intentionally interrupted in favour of isolated full matrix | **INCOMPLETE / NOT COUNTED**, `67` partial ok rows, log preserved |
| Synthetic advanced-state generator | `python local_web/fixtures/generate_advanced_state.py --output <new> --test-only-synthetic-approval` | **NOT PASS**: exceeded bounded tool run; partial generated fixture external to ZIP excluded; no fabricated approval claim |
| Windows 11 NTFS import/frozen/wheelhouse | `pwsh ... ci_ph_lw_01_windows.ps1` | **NOT RUN**: Windows 11 test stand absent |
| Real Windows browser / HTTP security / offline installer | LW-E01…LW-E36 E2E | **NOT RUN** (contracts and fixtures only; not Web implementation) |
| Real rootless Podman / governed positive egress | Normative v0.5.1 security gate | **NOT RUN / NO-GO**; no sandbox/egress PASS claimed |

## Core invariants and permitted changes

`PH_LW_01_CHANGED_FILES.md` enumerates exact relative changes; direct diff confirms **zero modifications under `src/project_harness/` outside new `resources/local_web` JSON**, no deleted files. Stage State/accepted input/history/old Runs/targets, strict evidence, no unsandboxed fallback, manual governance unchanged. Only additive docs, metadata/packaging resources, tests and fixtures were added/modified.

Known Windows blockers: `__init__.py → runtime.py → apply.py → fcntl` import, mutation in `check-intake`/`next`, destructive `prepare_handoff(... keep_directory=...)`, private destructive `_demo`. They are scope PH-LW-02/03/08, NOT fixed here.

## Conclusions / next gate

This step supplies reviewable, testable PH-LW-01 design artifacts and two full WIP ZIPs. It does not certify the absent PH-051-12 input snapshot, installed Windows product, browser UX or automatic executor. Native Windows readiness must be tested in later scoped stages, and the requested exact WIP base needs reconciliation before a strict same-lineage GO can be stated.
