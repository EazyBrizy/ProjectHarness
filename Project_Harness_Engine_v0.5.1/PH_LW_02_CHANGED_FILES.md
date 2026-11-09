# PH-LW-02 — exact changes relative to input PH-LW-01

**Дата:** 2026-11-01  
**Version:** 0.5.1 WIP / WINDOWS_NOT_TESTED  
**Engine input:** `bf2c01ef638e2ad3f41145288d44ba3deede73e9a4271211e2530402f2bee124`  
**Docs input:** `fc58170c80d6b64d6ecbaa5a443faa7aea3646a804ca409c1e2ba7cce47ff3da`  

Изменены только manual/preparation import/path/Stage transaction boundaries, tests, docs, distributable mirrors, reports and checksum metadata. Нормативные спецификации, accept/history и текущие registries не менялись.

## Engine: added=96, modified=28, removed=0, unchanged=802

### Added
- `PH_LW_02_CHANGED_FILES.md`
- `PH_LW_02_LOGS/DOCTOR_SOURCE.log`
- `PH_LW_02_LOGS/DOCTOR_SOURCE_FINAL.log`
- `PH_LW_02_LOGS/DOCUMENTATION_VALIDATION.json`
- `PH_LW_02_LOGS/DOCUMENTATION_VALIDATION.log`
- `PH_LW_02_LOGS/DOCUMENTATION_ZIP_VALIDATION.json`
- `PH_LW_02_LOGS/DOCUMENTATION_ZIP_VALIDATION.log`
- `PH_LW_02_LOGS/FULL_REGRESSION_FINAL.exit`
- `PH_LW_02_LOGS/FULL_REGRESSION_FINAL.log`
- `PH_LW_02_LOGS/FULL_REGRESSION_MATRIX.exit`
- `PH_LW_02_LOGS/FULL_REGRESSION_MATRIX.log`
- `PH_LW_02_LOGS/REGRESSION_MATRIX.json`
- `PH_LW_02_LOGS/REGRESSION_MATRIX_INITIAL.json`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_assessment_freshness.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_canonical_target.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_contract_hardening.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_engine.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_exact_assessment_ref.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_gate_evidence_contract.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_implementation_levels.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_maintenance_lifecycle.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_051_01_contract_baseline.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_051_02_executor_protocol.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_051_03_rootless_podman.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_051_04_disposable_roots.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_051_05_codex_adapter.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_051_06_result_channel.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_051_07_sandbox_verification.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_051_08_atomic_apply.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_051_09_automatic_runtime.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_051_10_migration_recovery.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_051_11_operator_docs.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_f01_gate_semantics_regression.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_f01_planner_regression.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_f02_semantic_proof_contract.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_f03_active_stage_planning.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_f04_runtime_reachability.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_f05_intake_acceptance.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_f06_maturity_lifecycle.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_f08_release_acceptance.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_lw_01_contract.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_ph_lw_02_windows_core.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_stage_approval_preparation.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_stage_gate_preparation_block_recovery.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES/tests_test_stage_transaction_recovery.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_assessment_freshness.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_canonical_target.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_contract_hardening.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_engine.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_exact_assessment_ref.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_gate_evidence_contract.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_implementation_levels.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_maintenance_lifecycle.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_051_01_contract_baseline.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_051_02_executor_protocol.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_051_03_rootless_podman.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_051_04_disposable_roots.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_051_05_codex_adapter.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_051_06_result_channel.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_051_07_sandbox_verification.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_051_08_atomic_apply.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_051_09_automatic_runtime.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_051_10_migration_recovery.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_051_11_operator_docs.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_f01_gate_semantics_regression.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_f01_planner_regression.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_f02_semantic_proof_contract.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_f03_active_stage_planning.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_f04_runtime_reachability.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_f05_intake_acceptance.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_f06_maturity_lifecycle.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_f08_release_acceptance.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_lw_01_contract.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_ph_lw_02_windows_core.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_stage_approval_preparation.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_stage_gate_preparation_block_recovery.log`
- `PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL/tests_test_stage_transaction_recovery.log`
- `PH_LW_02_LOGS/RERUN_EXEC_MODE_FAILURES/RERUN.exit`
- `PH_LW_02_LOGS/RERUN_EXEC_MODE_FAILURES/RERUN.log`
- `PH_LW_02_LOGS/RERUN_EXEC_MODE_FAILURES/rerun.py`
- `PH_LW_02_LOGS/RERUN_EXEC_MODE_FAILURES/tests_test_ph_f01_planner_regression.log`
- `PH_LW_02_LOGS/RERUN_EXEC_MODE_FAILURES/tests_test_ph_f03_active_stage_planning.log`
- `PH_LW_02_LOGS/RERUN_EXEC_MODE_FAILURES/tests_test_ph_f04_runtime_reachability.log`
- `PH_LW_02_LOGS/TARGETED_WINDOWS_CORE_LINUX.log`
- `PH_LW_02_LOGS/WHEEL_BUILD.log`
- `PH_LW_02_LOGS/WHEEL_CLI.log`
- `PH_LW_02_LOGS/WHEEL_INSTALL.log`
- `PH_LW_02_LOGS/run_regression_matrix.py`
- `PH_LW_02_LOGS/run_regression_matrix_final.py`
- `PH_LW_02_PRESERVED_INVARIANTS.md`
- `PH_LW_02_TEST_REPORT.md`
- `build/lib/project_harness/platform_fs.py`
- `docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/07_PH_LW_02_Native_Windows_Manual_Core.md`
- `local_web/ci_ph_lw_02_windows.ps1`
- `src/project_harness/platform_fs.py`
- `tests/test_ph_lw_02_windows_core.py`

### Modified
- `MANIFEST.sha256`
- `MANUAL_INSTALL.md`
- `README.md`
- `build/lib/project_harness/apply.py`
- `build/lib/project_harness/archive.py`
- `build/lib/project_harness/compiler.py`
- `build/lib/project_harness/intake.py`
- `build/lib/project_harness/runtime.py`
- `build/lib/project_harness/safety.py`
- `build/lib/project_harness/stage_transactions.py`
- `build/lib/project_harness/util.py`
- `build/lib/project_harness/validation.py`
- `dist/project_harness_engine-0.5.1-py3-none-any.whl`
- `docs/Project_Harness_Documentation_v0.5.1/FILE_INDEX.md`
- `docs/Project_Harness_Documentation_v0.5.1/MANIFEST.sha256`
- `docs/Project_Harness_Documentation_v0.5.1/Project_Harness_Architecture_v0.5.0_FULL.md`
- `docs/Project_Harness_Documentation_v0.5.1/README.md`
- `src/project_harness/apply.py`
- `src/project_harness/archive.py`
- `src/project_harness/compiler.py`
- `src/project_harness/intake.py`
- `src/project_harness/runtime.py`
- `src/project_harness/safety.py`
- `src/project_harness/stage_transactions.py`
- `src/project_harness/util.py`
- `src/project_harness/validation.py`
- `src/project_harness_engine.egg-info/PKG-INFO`
- `src/project_harness_engine.egg-info/SOURCES.txt`

### Removed
None.

## Standalone Documentation

New technical runbook `13_Local_Web_Manual_Companion/07_PH_LW_02_Native_Windows_Manual_Core.md`; `README.md`, `FILE_INDEX.md`, generated FULL aggregate, checksum manifest updated; technical content and generated files mirror embedded Documentation bytes.

## Historical preservation

All PH-051 / PH-F / PH-LW-01 reports and unchanged historical files retain their original input ZIP hashes. The only initial failed regression results are retained verbatim under PH_LW_02_LOGS/REGRESSION_MODULES_INITIAL, with corrected final rerun in PH_LW_02_LOGS/REGRESSION_MODULES.
