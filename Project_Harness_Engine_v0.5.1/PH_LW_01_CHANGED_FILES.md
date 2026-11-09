# PH-LW-01 — changed files / exact input diff

**Дата:** 2026-11-01  
**Версия:** 0.5.1 WIP, additive PH-LW-01  
**Scope:** companion docs, schemas/resources, fixtures, CI, wheel/package metadata; production runtime unchanged.

## Engine: added=81, modified=10, removed=0, unchanged=738

### ADDED
- `PH_LW_01_CHANGED_FILES.md`
- `PH_LW_01_LOGS/BASELINE_PH05111_TESTS.exit`
- `PH_LW_01_LOGS/BASELINE_PH05111_TESTS.log`
- `PH_LW_01_LOGS/PH_LW_01_ADVANCED_FIXTURE_GENERATION.log`
- `PH_LW_01_LOGS/PH_LW_01_ADVANCED_FIXTURE_NEGATIVE_NO_OPTIN.log`
- `PH_LW_01_LOGS/PH_LW_01_ADVANCED_FIXTURE_NEGATIVE_NO_OVERWRITE.log`
- `PH_LW_01_LOGS/PH_LW_01_DOC_FINAL_VALIDATOR.json`
- `PH_LW_01_LOGS/PH_LW_01_DOC_FINAL_VALIDATOR.log`
- `PH_LW_01_LOGS/PH_LW_01_ENGINE_DOCTOR_PRELIM.log`
- `PH_LW_01_LOGS/PH_LW_01_FINAL_FULL_REGRESSION.exit`
- `PH_LW_01_LOGS/PH_LW_01_FINAL_FULL_REGRESSION.log`
- `PH_LW_01_LOGS/PH_LW_01_SHARDED_FINAL_RUNNER.exit`
- `PH_LW_01_LOGS/PH_LW_01_SHARDED_FINAL_RUNNER.log`
- `PH_LW_01_LOGS/PH_LW_01_TARGETED_CONTRACT.exit`
- `PH_LW_01_LOGS/PH_LW_01_TARGETED_CONTRACT.log`
- `PH_LW_01_LOGS/PH_LW_01_WHEEL_BUILD.log`
- `PH_LW_01_LOGS/PH_LW_01_WHEEL_INSTALL_SMOKE.log`
- `PH_LW_01_LOGS/PREFLIGHT_ARCHIVE_INTEGRITY.json`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_assessment_freshness.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_canonical_target.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_contract_hardening.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_engine.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_exact_assessment_ref.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_gate_evidence_contract.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_implementation_levels.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_maintenance_lifecycle.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_051_01_contract_baseline.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_051_02_executor_protocol.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_051_03_rootless_podman.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_051_04_disposable_roots.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_051_05_codex_adapter.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_051_06_result_channel.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_051_07_sandbox_verification.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_051_08_atomic_apply.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_051_09_automatic_runtime.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_051_10_migration_recovery.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_051_11_operator_docs.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_f01_gate_semantics_regression.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_f01_planner_regression.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_f02_semantic_proof_contract.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_f03_active_stage_planning.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_f04_runtime_reachability.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_f05_intake_acceptance.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_f06_maturity_lifecycle.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_f08_release_acceptance.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_ph_lw_01_contract.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_stage_approval_preparation.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_stage_gate_preparation_block_recovery.log`
- `PH_LW_01_LOGS/SHARDED_FINAL/tests_test_stage_transaction_recovery.log`
- `PH_LW_01_LOGS/SHARDED_FINAL_MATRIX.json`
- `PH_LW_01_PRESERVED_INVARIANTS.md`
- `PH_LW_01_TEST_REPORT.md`
- `build/lib/project_harness/resources/local_web/control_map_v1.json`
- `build/lib/project_harness/resources/local_web/gpt_exchange_reply_v1.schema.json`
- `build/lib/project_harness/resources/local_web/metadata_v1.json`
- `build/lib/project_harness/resources/local_web/operation_receipt_v1.schema.json`
- `docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/00_Entry_And_Base.md`
- `docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/01_Architecture_Runtime_Installation.md`
- `docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/02_Control_Map_26_Commands.md`
- `docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/03_Draft_Approvals_Journal.md`
- `docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/04_Threat_Model_And_Consent.md`
- `docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/05_Acceptance_CI_Baseline.md`
- `docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/06_Golden_Fixtures.md`
- `local_web/ci_ph_lw_01_windows.ps1`
- `local_web/fixtures/advanced_state_recipe.json`
- `local_web/fixtures/brownfield_existing_repository/README.md`
- `local_web/fixtures/brownfield_existing_repository/app.py`
- `local_web/fixtures/brownfield_existing_repository/tests/test_app.py`
- `local_web/fixtures/generate_advanced_state.py`
- `local_web/fixtures/gpt_reply_draft_only_positive.json`
- `local_web/fixtures/gpt_reply_untrusted_reject.json`
- `local_web/fixtures/greenfield_nested_md.zip`
- `local_web/fixtures/greenfield_single_md/IDEA.md`
- `local_web/fixtures/no_doc_unapproved_project_input_v4.json`
- `local_web/requirements-web-win_amd64-cp314.lock`
- `local_web/wheel_inventory_v1.json`
- `src/project_harness/resources/local_web/control_map_v1.json`
- `src/project_harness/resources/local_web/gpt_exchange_reply_v1.schema.json`
- `src/project_harness/resources/local_web/metadata_v1.json`
- `src/project_harness/resources/local_web/operation_receipt_v1.schema.json`
- `tests/test_ph_lw_01_contract.py`

### MODIFIED
- `MANIFEST.sha256`
- `README.md`
- `dist/project_harness_engine-0.5.1-py3-none-any.whl`
- `docs/Project_Harness_Documentation_v0.5.1/FILE_INDEX.md`
- `docs/Project_Harness_Documentation_v0.5.1/MANIFEST.sha256`
- `docs/Project_Harness_Documentation_v0.5.1/Project_Harness_Architecture_v0.5.0_FULL.md`
- `docs/Project_Harness_Documentation_v0.5.1/README.md`
- `pyproject.toml`
- `src/project_harness_engine.egg-info/PKG-INFO`
- `src/project_harness_engine.egg-info/SOURCES.txt`

### REMOVED
- (none)

## Documentation: added=7, modified=4, removed=0, unchanged=129

### ADDED
- `13_Local_Web_Manual_Companion/00_Entry_And_Base.md`
- `13_Local_Web_Manual_Companion/01_Architecture_Runtime_Installation.md`
- `13_Local_Web_Manual_Companion/02_Control_Map_26_Commands.md`
- `13_Local_Web_Manual_Companion/03_Draft_Approvals_Journal.md`
- `13_Local_Web_Manual_Companion/04_Threat_Model_And_Consent.md`
- `13_Local_Web_Manual_Companion/05_Acceptance_CI_Baseline.md`
- `13_Local_Web_Manual_Companion/06_Golden_Fixtures.md`

### MODIFIED
- `FILE_INDEX.md`
- `MANIFEST.sha256`
- `Project_Harness_Architecture_v0.5.0_FULL.md`
- `README.md`

### REMOVED
- (none)

## Границы

Служебные файлы текущей поставки `PH_LW_01_TEST_REPORT.md`, `PH_LW_01_CHANGED_FILES.md`, `PH_LW_01_PRESERVED_INVARIANTS.md`, `PH_LW_01_LOGS/` и соответствующий rebuilt root manifest добавляются при финальной сборке; их имена обязательны и не являются изменениями core semantics.
Запрещённых production source edits не обнаружено. История `PH_051_*` и нормативные исходники оставлены неизменными.
