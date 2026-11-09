# PH-F01 — Исходная интеграционная матрица Project Harness v0.5.0

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Дата фиксации PH-F01:** 2026-10-23  
**Статус:** BASELINE / PRE-REMEDIATION; не является релизной приёмкой.

## Нормативная основа и границы

- `Project_Harness_v0.5.0_Remediation_Plan_RU.md`, раздел PH-F01 и сценарии I-01–I-14 PH-F08.
- `02_Project_Harness_v0.5.0_Implementation_Levels.md` (нормативная спецификация v0.5.0), разделы 8–13, 16–19, 22–23.
- Только fixtures/tests/matrix/test reports. Runtime, schemas, registry, adapter, CLI и API **не изменяются** в PH-F01.
- `GREENFIELD_MVP`, `BROWNFIELD`, `ACCEPTED_PROTOTYPE`, `TARGET_LEVEL_REACHED` материализуются через исходный публичный `prepare/verify/complete/accept-stage/assess-maturity` и тестовые источники. `TARGET_LEVEL_REACHED` получается из *синтетического* формально принятого Brownfield MVP контекста; это тест транзакционных/статусных маршрутов, **не доказательство реальной зрелости MVP**.

## Контрольная матрица нормативных issue IDs

| Issue | Контрольный контракт и существующее покрытие | PH-F01 дополняет | Baseline / следующий этап |
|---|---|---|---|
| B-01 | После `accept-stage` детализируется новая active Stage; `test_implementation_levels.py`, `test_canonical_target.py` | `test_ph_f01_planner_regression`: Prototype→Alpha, API/CLI/status/JIT | **RED**, PH-F03; существующая транзакция фиксирует `PLAN_ACTIVE_STAGE` без planner |
| B-02 | Crash-consistent Stage transaction и recovery; `test_stage_transaction_recovery.py` | Historical evidence/input digests before/after level-up | Existing regression coverage; no semantics changes |
| B-03 | Brownfield freshness и current context binding; `test_assessment_freshness.py` | Separate Brownfield fixture through public assessment | Existing coverage; synthetic evidence distinguished from product proof |
| B-04 | Exact immutable assessment ref; `test_exact_assessment_ref.py` | TARGET_LEVEL_REACHED generated via assessment exact ref | Existing coverage |
| G-01 | Evidence exact ref/kind/digest/final baseline; `test_gate_evidence_contract.py`, `test_stage_gate_preparation_block_recovery.py` | No-op PASS report→four semantically unrelated kinds | **Additional semantic defect RED**, PH-F02; formal G-01 checks insufficient |
| L-01 | Canonical current-cycle target and projections; `test_canonical_target.py` | MVP→RELEASE level-up target, old immutable input unchanged | Existing coverage plus PH-F01 fixture |
| M-01 | Same-level maintenance lifecycle; `test_maintenance_lifecycle.py` | Matrix coverage; no modifications | Existing coverage |
| U-01 | Draft Stage approval; `test_stage_approval_preparation.py` | F02 no-op Gate status and source kind checks | Existing coverage; not a semantic attestator |
| Q-01 | Acceptance preparation Task and JIT; `test_stage_gate_preparation_block_recovery.py` | Real `verify→complete` with zero product changes | Route exists; semantic bug RED, PH-F02 |
| Q-02 | Persisted Gate BLOCKED/recovery; `test_stage_gate_preparation_block_recovery.py` | Matrix only | Existing coverage |
| Q-03 | Strict formal acceptance and level-up approvals; `test_stage_approval_preparation.py` | Real formal acceptance/level-up fixtures | Existing coverage |
| Q-04 | Post-boundary active Stage planning; `test_canonical_target.py` | First READY JIT after Prototype/MVP boundary | **RED**, PH-F03 |

## Исходная PH-F08 end-to-end матрица

`BASELINE` = фактически проверяемый исходный статус/fixture; `RED` = ожидаемое падение PH-F01 regression; `DEFERRED` = сквозная приёмка предназначена для следующего этапа, а не ложный PASS.

| ID | Сценарий | PH-F01 fixture / первичная проверка | Контрольное состояние |
|---|---|---|---|
| I-01 | Greenfield intake→prepare | `GREENFIELD_MVP`, `test_ph_f01_planner_regression.py` + existing intake tests | BASELINE: handoff compiled; полный опрос PH-F05 |
| I-02 | Greenfield MVP, четыре стадии | `ACCEPTED_PROTOTYPE` после Prototype; next Alpha | RED далее Alpha/Beta/MVP; PH-F03, PH-F06 |
| I-03 | Prototype accepted→Alpha first JIT | `ACCEPTED_PROTOTYPE`; CLI `stage-status`, `next`, proposed governed planner | RED PH-F03 |
| I-04 | Accepted MVP→RELEASE first JIT | `TARGET_LEVEL_REACHED`; formal CLI `level-up`, proposed governed planner | RED PH-F03 |
| I-05 | No-op PASS should not fabricate Gate evidence | `GREENFIELD_MVP`; ordinary Tasks then no-change PASS preparation | RED PH-F02 (four kinds) |
| I-06 | Valid subject-specific proofs→formal Gate acceptance | Existing `test_gate_evidence_contract.py` covers formal refs | DEFERRED subject semantic proof to PH-F02 |
| I-07 | Structurally valid UNKNOWN/FAIL→BLOCKED/recover | Existing `test_stage_gate_preparation_block_recovery.py` | BASELINE existing regression |
| I-08 | Stale/wrong-kind/tamper/dangling evidence | Existing `test_gate_evidence_contract.py` | BASELINE formal contract only |
| I-09 | Brownfield assessment/approval | `BROWNFIELD` and `TARGET_LEVEL_REACHED` synthetic governance fixture | BASELINE current status; real independent maturity PH-F06 |
| I-10 | Maintenance complete→level-up | Existing `test_maintenance_lifecycle.py` | BASELINE existing regression; e2e PH-F06 |
| I-11 | Crash during stage transitions | Existing `test_stage_transaction_recovery.py` | BASELINE existing regression; planning crash PH-F03/PH-F04 |
| I-12 | Retry/stale/duplicate approvals | Existing transaction/maintenance/recovery tests | BASELINE existing regression; planner replay PH-F03/PH-F04 |
| I-13 | Migration v0.4.1→restart | Existing `test_contract_hardening.py` | DEFERRED full migration E2E to PH-F08 |
| I-14 | Fresh installation / wheel / doctor / both validators | Existing engine `doctor`; documentation validator; existing wheel | DEFERRED final clean-install packaging to PH-F08 |

## PH-F01 test selectors

```bash
  # Existing suite (before adding PH-F01 tests):
python tests/run_tests.py

  # New PH-F01 fixtures and intentional RED regressions:
PYTHONPATH=src:. python -m unittest -v \
  tests.test_ph_f01_planner_regression \
  tests.test_ph_f01_gate_semantics_regression
```

`test_01...` tests are expected GREEN and fix the starting state. `test_ph_f02...` must be RED until PH-F02; `test_ph_f03...` must be RED until PH-F03. Do not apply `unittest.expectedFailure` or quietly skip them: subsequent remediation must flip them to actual PASS. The draft→review conversion in the `plan-active-stage` regression is deliberately subject to the exact public reviewed-record schema to be defined by PH-F03; no automatic decision may be assumed.

## Отложенные вопросы / известные ограничения

1. Baseline validation returns `PASS` for boundary `PLAN_ACTIVE_STAGE` even when `stage_status.next_operator_route.command` is null: PH-F04, **не исправлять здесь**.
2. A general PASS verification report is formally well-formed but not semantic evidence of architecture, limitations, permitted use, or externally supplied constraints: PH-F02, **не исправлять здесь**.
3. The current public CLI lacks a next active-stage planner: PH-F03, **не исправлять здесь**.
4. Synthetic `SATISFIED_BY_BASELINE` evidence in the governance-only fixture is not production-acceptance evidence and must not be reused outside tests.
