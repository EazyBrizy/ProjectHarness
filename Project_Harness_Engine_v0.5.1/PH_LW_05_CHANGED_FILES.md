# PH-LW-05 — changed-file scope (сравнение с PH-LW-04 ZIP)

**Дата:** 2026-11-04, **версия:** 0.5.1 WIP. Изменения ограничены importer/refresh service/public intake helper/Local Web HTTP and UI, тестами, документацией и package synchronization. Старые accepted reports и нормативные спецификации не правились.

## Modified files

- `CHANGELOG.md`
- `MANIFEST.sha256`
- `MANUAL_INSTALL.md`
- `README.md`
- `build/lib/project_harness/intake.py`
- `build/lib/project_harness/local_web_http.py`
- `build/lib/project_harness/local_web_service.py`
- `build/lib/project_harness/resources/local_web/assets/app.css`
- `build/lib/project_harness/resources/local_web/assets/app.js`
- `build/lib/project_harness/resources/local_web/assets/index.html`
- `dist/project_harness_engine-0.5.1-py3-none-any.whl`
- `docs/Project_Harness_Documentation_v0.5.1/FILE_INDEX.md`
- `docs/Project_Harness_Documentation_v0.5.1/MANIFEST.sha256`
- `docs/Project_Harness_Documentation_v0.5.1/Project_Harness_Architecture_v0.5.0_FULL.md`
- `docs/Project_Harness_Documentation_v0.5.1/README.md`
- `src/project_harness/intake.py`
- `src/project_harness/local_web_http.py`
- `src/project_harness/local_web_service.py`
- `src/project_harness/resources/local_web/assets/app.css`
- `src/project_harness/resources/local_web/assets/app.js`
- `src/project_harness/resources/local_web/assets/index.html`
- `src/project_harness_engine.egg-info/PKG-INFO`
- `src/project_harness_engine.egg-info/SOURCES.txt`

## Added files

- `PH_LW_05_LOGS/PH_LW_05_DOC_AFTER_AGGREGATES.json`
- `PH_LW_05_LOGS/PH_LW_05_DOC_AFTER_AGGREGATES.log`
- `PH_LW_05_LOGS/PH_LW_05_DOC_AGGREGATE_BUILD.json`
- `PH_LW_05_LOGS/PH_LW_05_DOC_AGGREGATE_BUILD.log`
- `PH_LW_05_LOGS/PH_LW_05_DOC_ARCHIVE_BUILD.log`
- `PH_LW_05_LOGS/PH_LW_05_DOC_SOURCE_FINAL.json`
- `PH_LW_05_LOGS/PH_LW_05_DOC_SOURCE_FINAL.log`
- `PH_LW_05_LOGS/PH_LW_05_DOC_SOURCE_VALIDATION.json`
- `PH_LW_05_LOGS/PH_LW_05_DOC_SOURCE_VALIDATION.log`
- `PH_LW_05_LOGS/PH_LW_05_DOC_ZIP_VALIDATION.json`
- `PH_LW_05_LOGS/PH_LW_05_DOC_ZIP_VALIDATION.log`
- `PH_LW_05_LOGS/PH_LW_05_HTTP_DEPENDENCY_RESULT.log`
- `PH_LW_05_LOGS/PH_LW_05_PREVIOUS_PLUS_TARGETED.log`
- `PH_LW_05_LOGS/PH_LW_05_RECHECK_PROGRESS.log`
- `PH_LW_05_LOGS/PH_LW_05_REGRESSION_PROGRESS.log`
- `PH_LW_05_LOGS/PH_LW_05_SOURCE_DOCTOR.log`
- `PH_LW_05_LOGS/PH_LW_05_SOURCE_DOCTOR_FINAL.log`
- `PH_LW_05_LOGS/PH_LW_05_STATIC_CHECKS.log`
- `PH_LW_05_LOGS/PH_LW_05_TARGETED_AFTER_COLLISION.log`
- `PH_LW_05_LOGS/PH_LW_05_TARGETED_AFTER_SAFETY.log`
- `PH_LW_05_LOGS/PH_LW_05_TARGETED_FINAL.log`
- `PH_LW_05_LOGS/PH_LW_05_TARGETED_INITIAL.log`
- `PH_LW_05_LOGS/PH_LW_05_UI_MISSING_DEP_FAILCLOSED.log`
- `PH_LW_05_LOGS/PH_LW_05_WHEEL_BUILD.log`
- `PH_LW_05_LOGS/PH_LW_05_WHEEL_INSTALL.log`
- `PH_LW_05_LOGS/PH_LW_05_WHEEL_MODULES.log`
- `PH_LW_05_LOGS/PH_LW_05_WHEEL_SMOKE.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/FINAL_MATRIX.json`
- `PH_LW_05_LOGS/REGRESSION_MODULES/MATRIX.json`
- `PH_LW_05_LOGS/REGRESSION_MODULES/RECHECK_MATRIX.json`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_assessment_freshness.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_canonical_target.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_contract_hardening.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_engine.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_exact_assessment_ref.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_gate_evidence_contract.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_gate_evidence_contract_RECHECK.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_implementation_levels.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_maintenance_lifecycle.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_051_01_contract_baseline.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_051_02_executor_protocol.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_051_03_rootless_podman.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_051_04_disposable_roots.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_051_05_codex_adapter.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_051_06_result_channel.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_051_07_sandbox_verification.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_051_08_atomic_apply.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_051_09_automatic_runtime.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_051_10_migration_recovery.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_051_11_operator_docs.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_f01_gate_semantics_regression.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_f01_planner_regression.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_f01_planner_regression_RECHECK.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_f02_semantic_proof_contract.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_f03_active_stage_planning.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_f03_active_stage_planning_RECHECK.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_f04_runtime_reachability.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_f04_runtime_reachability_RECHECK.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_f05_intake_acceptance.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_f06_maturity_lifecycle.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_f06_maturity_lifecycle_RECHECK.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_f08_release_acceptance.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_lw_01_contract.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_lw_02_windows_core.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_lw_03_service.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_lw_04_http.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_lw_05_http.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_ph_lw_05_import.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_stage_approval_preparation.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_stage_gate_preparation_block_recovery.log`
- `PH_LW_05_LOGS/REGRESSION_MODULES/test_stage_transaction_recovery.log`
- `PH_LW_05_PRESERVED_INVARIANTS.md`
- `PH_LW_05_TEST_REPORT.md`
- `build/lib/project_harness/local_web_imports.py`
- `build/lib/project_harness/local_web_source_refresh.py`
- `build/lib/project_harness/local_web_sources_service.py`
- `docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/10_PH_LW_05_Document_Import_and_Source_Revisions.md`
- `local_web/ci_ph_lw_05_windows.ps1`
- `src/project_harness/local_web_imports.py`
- `src/project_harness/local_web_source_refresh.py`
- `src/project_harness/local_web_sources_service.py`
- `tests/test_ph_lw_05_http.py`
- `tests/test_ph_lw_05_import.py`

## Deleted files

Нет.

## Auxiliary generated files

`PH_LW_05_CHANGED_FILES.md` (этот файл), `PH_LW_05_TEST_REPORT.md`, `PH_LW_05_PRESERVED_INVARIANTS.md`, `PH_LW_05_LOGS/*`, regenerated Engine `MANIFEST.sha256`, refreshed `dist/*.whl` and `build/lib` mirror. `PH_LW_05_LOGS/REGRESSION_MODULES/FINAL_MATRIX.json` — финальная матрица с указанием каждого реально запущенного модуля и пропусков.

**Documentation ZIP:** `README.md`, новый `13_Local_Web_Manual_Companion/10_PH_LW_05_Document_Import_and_Source_Revisions.md`, свежие `FILE_INDEX.md` и `Project_Harness_Architecture_v0.5.0_FULL.md`, `MANIFEST.sha256`. Эти файлы зеркалированы в Engine `docs/`. Нет изменений нормативных 24/03 спецификаций.
