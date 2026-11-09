# PH-F08 — release acceptance matrix (v0.5.0)

**Статус:** RELEASE GATE, результаты с фактического полного прогона 2026-10-25.  
**Основание:** PH-F08 из remediation plan, нормативная спецификация v0.5.0.  
**Доказательство:** `PH_F08_LOGS/full_suite_final.log`, wheel/doctor/docs/ZIP checks в `PH_F08_LOGS/`.

| ID | Сценарий | Результат | Фактический тест / источник |
|---|---|---|---|
| I-01 | Greenfield minimal sources, explicit target decision, 4 approvals, prepare | **PASS** | `test_ph_f08_release_acceptance.PHF08ReleaseAcceptanceTests.test_i01_minimal_greenfield_waiting_decision_to_exact_first_jit` |
| I-02 | Greenfield MVP, Prototype → Alpha → Beta → MVP via execution and Stage acceptance | **PASS** | `test_ph_f06_maturity_lifecycle.PHF06MaturityLifecycleTests.test_01_greenfield_all_four_stages_have_verified_immutable_acceptances` |
| I-03 | Accepted Prototype → reviewed Alpha Stage planning | **PASS** | `test_ph_f08_release_acceptance.PHF08ReleaseAcceptanceTests.test_i03_i12_prototype_alpha_planning_exact_replay_and_stale_rejection` |
| I-04 | Accepted MVP → level-up RELEASE → Stage planning | **PASS** | `test_ph_f06_maturity_lifecycle.PHF06MaturityLifecycleTests.test_02_maintenance_complete_level_up_release_and_idempotent_replay` |
| I-05 | No-change generic PASS Gate preparation | **PASS** | `test_ph_f01_gate_semantics_regression.PHF01GateSemanticsTests.test_ph_f02_noop_pass_keeps_gate_unclosed_without_subject_proofs` |
| I-06 | Subject-specific source proof + exact formal review | **PASS** | `test_stage_gate_preparation_block_recovery.StageGatePreparationBlockRecoveryTests.test_valid_unknown_persists_gate_blocker_then_recovers_to_verifying_and_accepts_target` |
| I-07 | Structurally valid UNKNOWN/FAIL review, Stage Gate BLOCKED, recovery | **PASS** | `test_stage_gate_preparation_block_recovery.StageGatePreparationBlockRecoveryTests.test_valid_unknown_persists_gate_blocker_then_recovers_to_verifying_and_accepts_target` |
| I-08 | Dangling/stale/tampered/wrong-kind or wrong-subject evidence | **PASS** | `test_gate_evidence_contract.GateEvidenceContractTests.test_dangling_evidence_ref_is_rejected` |
| I-09 | Brownfield read-only assessment → separate formal baseline approval | **PASS** | `test_ph_f06_maturity_lifecycle.PHF06BrownfieldTests.test_05_supplied_proofs_survive_assessment_then_sequential_baseline_reports_and_planner` |
| I-10 | Maintenance after acceptance, complete, then level-up | **PASS** | `test_ph_f06_maturity_lifecycle.PHF06MaturityLifecycleTests.test_02_maintenance_complete_level_up_release_and_idempotent_replay` |
| I-11 | Crash interruption in stage planning, acceptance and level-up | **PASS** | `test_ph_f03_active_stage_planning.PHF03ActiveStagePlannerTests.test_transaction_recovery_restores_pre_plan_boundary` |
| I-12 | Repeated commands, duplicate approvals and stale plans | **PASS** | `test_ph_f08_release_acceptance.PHF08ReleaseAcceptanceTests.test_i03_i12_prototype_alpha_planning_exact_replay_and_stale_rejection` |
| I-13 | v0.4.1 migration and restart | **PASS** | `test_ph_f06_maturity_lifecycle.PHF06MigrationTests.test_09_migration_restart_preserves_historical_completed_runs` |
| I-14 | Fresh isolated wheel distribution, doctor, both validators, ZIP manifests | **PASS** | `EXTERNAL:wheel_smoke.json` |

Все перечисленные тесты отмечены `ok` в **одном** полном исходном прогоне. `I-14` дополнительно выполняет независимую установку wheel с отключённым `PYTHONPATH`, `doctor`, оба validators и проверку двух ZIP. В строках таблицы показан первый подтверждающий тест; ниже machine-readable полная матрица в `PH_F08_RELEASE_MATRIX.json`.

Синтетические approvals и operator-supplied proof artifacts существуют **только в тестовых Project Instances**: они моделируют формальный управляемый workflow и не являются автоматическим подтверждением готовности реального продукта. Базовые документы, immutable history и нормативная спецификация не заменены этими fixtures.
