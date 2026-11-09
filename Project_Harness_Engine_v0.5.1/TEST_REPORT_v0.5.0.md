# Отчёт тестирования Project Harness Engine v0.5.0

**Версия:** 0.5.0
**Release date:** 2026-08-18
**Validation run:** 2026-08-20
**Python:** 3.13.5 в release environment; package metadata требует Python 3.11+
**Результат M-01 на 2026-08-20:** PASS (исторический). **PH-F01 на 2026-10-23:** ожидаемые RED; см. `PH_F01_TEST_REPORT.md`.

## 1. Проверенный release boundary

Выполнено только исправление **M-01: governed same-level maintenance lifecycle** поверх актуального v0.5.0 после Gate preparation/recovery:

- публичные CLI/API operations `start-maintenance` и `cancel-maintenance`;
- strict exact-bound maintenance plan и cancel approval;
- исполнимый accepted-stage WP/Task/DAG/VFP/CTX/PPL/JIT route через существующие `next → verify → complete`;
- отдельная maintenance completion/cancellation history и восстановление предыдущего valid route;
- open-maintenance interlock для `level-up`;
- idempotent replay и fail-closed cancellation без invented rollback.

Версия остаётся `0.5.0`. Не добавлялись project-evolution Change Packs, Git/repository operations, deployment, executor adapter, distributed transaction framework или future-stage implementation.

## 2. Публичный и strict input contract

Добавлены операции:

```bash
project-harness start-maintenance --project <root> --plan <record>
project-harness cancel-maintenance --project <root> --approval <record>
```

```python
from project_harness import start_maintenance, cancel_maintenance
```

Input валидируется до mutation двумя отдельными Draft 2020-12 JSON Schemas:

- `SCHEMA-MAINTENANCE-PLAN@1`;
- `SCHEMA-MAINTENANCE-CANCEL-APPROVAL@1`.

На всех нормативных object levels действует `additionalProperties: false`. Plan exact-bound к current `highest_accepted_level`, current target, last Stage Acceptance ref, accepted scope, formal `DEC-*`/`ACT-*` approval, objective/rationale, atomic Tasks, verification, rollback и cancel constraints. Каждый executable Task обязан иметь exact accepted `implementation_stage` и `future_stage_work: FORBIDDEN`.

Cancel approval exact-bound к current plan/WP revision, accepted level, target и last acceptance; разрешён только mode `PRE_PRODUCT_CHANGE_ONLY` и требует отдельную Decision kind `CANCEL_MAINTENANCE`.

## 3. Governed start lifecycle

`start-maintenance` разрешён только при существующем accepted level и отсутствии competing active Run, stage-planning application, Gate transition или другого open maintenance route. Requested implementation stage обязан точно совпадать с `highest_accepted_level`; next/future-stage work отвергается.

Успешный start создаёт:

- immutable `MAINTAIN_CURRENT_STAGE` Decision;
- revisioned maintenance Plan и Work Package;
- atomic Tasks и DAG;
- Verification Profiles, Context Plans и Prompt Plans;
- maintenance index/current state, Task/index/NEXT updates;
- ровно один deterministic first JIT bundle/Run reservation.

Canonical route artifacts записываются crash-consistent Stage transaction service. Первая Run reservation выполняется deterministic/idempotent шагом той же публичной operation: успешный вызов возвращает route с одним first JIT, а exact replay не создаёт второй WP, Task, Run или bundle.

Maintenance binding сохраняется в WP, Tasks, Capability Grant, Context/Prompt/Run Plan, Compiled Prompt Bundle, JIT bundle, trusted snapshot, verification result, Run Report и Task Report:

```text
implementation_stage: <highest_accepted_level>
maintenance_route: MAINTAIN_CURRENT_STAGE
maintenance_plan_ref: <exact RQP-...@revision>
```

Ordinary Stage artifacts не получают пустые maintenance fields.

## 4. Runtime completion routing

Tasks выполняются существующим lifecycle:

```text
start-maintenance
→ next
→ submit result
→ verify
→ complete
→ next maintenance Task (если есть)
→ final maintenance closure
```

После последней mandatory maintenance Task runtime:

- переводит Work Package в revisioned `COMPLETED`;
- создаёт immutable `MAINTENANCE_COMPLETION` report с Decision, Task Report, Run и evidence refs;
- очищает maintenance current state;
- восстанавливает captured previous project status/NEXT route;
- не вызывает Stage Gate readiness или `accept-stage`;
- не меняет target или accepted maturity.

## 5. Cancel semantics

Pre-execution cancellation требует strict formal Decision. При отсутствии completed/observed product change transaction создаёт terminal Task/WP revisions, immutable cancellation report, сохраняет зарезервированный Run как immutable `CANCELLED` history и восстанавливает previous valid route.

Cancellation fail-closed отвергается, когда обнаружено хотя бы одно из следующего:

- completed product-changing maintenance Task;
- submitted Agent Result с product-changing execution;
- observed Task Report changes;
- active или blocked/inactive Run product drift относительно immutable trusted snapshot.

History не переписывается. Автоматический rollback/compensation не синтезируется: после product change требуется normal completion либо уже существующий отдельно governed compensation route.

## 6. Maturity, history, level-up и idempotency invariants

Подтверждено, что maintenance не меняет:

- `.harness/stages/STAGE_STATE.yaml`, включая `highest_accepted_level` и current target;
- immutable Stage Acceptance Reports;
- accepted Stage Plan/Gate revisions;
- pre-existing completed Runs.

`level-up` блокируется только пока maintenance WP имеет open status. После `COMPLETED` или valid pre-execution `CANCELLED` progression снова разрешён. Historical maintenance revisions сохраняются.

Exact replay same plan/Decision возвращает existing route и не создаёт duplicate artifacts. Conflicting reuse того же plan identity, wrong level/target/acceptance binding и future-stage scope отклоняются до mutation.

## 7. Полная regression/conformance/fault-injection matrix

Release launcher `python tests/run_tests.py` завершён без ошибок:

| Модуль | Результат | Tests |
|---|---:|---:|
| `test_assessment_freshness` | PASS | 10/10 |
| `test_canonical_target` | PASS | 5/5 |
| `test_contract_hardening` | PASS | 31/31 |
| `test_engine` | PASS | 14/14 |
| `test_exact_assessment_ref` | PASS | 5/5 |
| `test_gate_evidence_contract` | PASS | 10/10 |
| `test_implementation_levels` | PASS | 8/8 |
| `test_maintenance_lifecycle` | PASS | 7/7 |
| `test_stage_approval_preparation` | PASS | 7/7 |
| `test_stage_gate_preparation_block_recovery` | PASS | 5/5 |
| `test_stage_transaction_recovery` | PASS | 15/15 |
| **Итого** | **PASS** | **117/117** |

Execution time: **231.390 s**. Сохранены все 15 crash-consistency/fault-injection regressions Stage transaction protocol.

## 8. Focused M-01 coverage

Focused command завершён: **15 tests + 4 subtests PASS** за **62.42 s**.

Обязательные сценарии:

1. start создаёт Decision/WP/Tasks/DAG/VFP/CTX/PPL и ровно один first JIT;
2. exact replay идемпотентен;
3. `next → verify → complete` закрывает maintenance и сохраняет target/accepted level;
4. open maintenance блокирует level-up, completion разрешает его;
5. valid pre-execution cancel восстанавливает previous route;
6. cancel после completed product-changing Task отклоняется без history rewrite;
7. wrong accepted level, stale target/acceptance, future-stage scope и conflicting duplicate отклоняются;
8. Stage Acceptance Reports и pre-existing completed Runs остаются byte/digest identical;
9. CLI exposes both public commands.

## 9. Full CLI smoke lifecycle

На двух fresh generated Project Instances выполнены complete и cancel routes.

### Normal completion

```text
start-maintenance
→ initial next idempotent replay
→ Task 1 verify/complete
→ Task 2 verify/complete
→ MAINTENANCE_COMPLETION
→ TARGET_LEVEL_REACHED / TARGET_ALREADY_REACHED
→ validate-project PASS
```

Подтверждено:

- first Run: `RUN-HARNESS-DEMO-TASK-CLI-004-A1`;
- Tasks completed: 2;
- maintenance Runs/JIT bundles: 2/2;
- completion report: `VAL-HARNESS-DEMO-TASK-CLI-MAINT-COMPLETE-24ABCCDD9C@1`;
- accepted level/target: `PROTOTYPE` / `PROTOTYPE`;
- Stage State: byte-identical;
- Acceptance Reports: byte-identical;
- pre-existing completed Runs: byte-identical;
- `validate-project`: PASS.

### Formal pre-execution cancel

```text
start-maintenance
→ cancel-maintenance
→ immutable CANCELLED Run + cancellation report
→ TARGET_LEVEL_REACHED / TARGET_ALREADY_REACHED
→ validate-project PASS
```

Подтверждено:

- cancel Decision: `DEC-HARNESS-DEMO-TASK-CLI-MAINT-CANCEL-SMOKE-AUTH@1`;
- cancellation report: `VAL-HARNESS-DEMO-TASK-CLI-MAINT-CANCEL-6B84E5E495@1`;
- reserved Run `RUN-HARNESS-DEMO-TASK-CLI-004-A1` сохранён со status `CANCELLED`;
- Stage State: byte-identical;
- accepted level/target: `PROTOTYPE` / `PROTOTYPE`;
- `validate-project`: PASS.

Machine-readable smoke evidence: `maintenance_smoke_report.json` в release validation workspace.

## 10. Distribution и documentation integrity

- `python -m compileall -q src tests`: PASS;
- `git diff --check`: PASS;
- root ↔ embedded maintenance schemas: exact byte parity;
- standalone ↔ embedded documentation trees: exact byte parity;
- source-tree `doctor --skip-manifest`: PASS;
- final static distribution manifest + `doctor`: PASS;
- wheel rebuilt: `project_harness_engine-0.5.0-py3-none-any.whl`;
- wheel entries: 60; CRC: PASS;
- wheel contains `project_harness/maintenance.py` and both embedded maintenance schemas;
- wheel SHA-256: `d6b7a58afd0a18ba681571de4a65587abdd476971afe4aa13e525768b3ff95db`;
- wheel metadata version: `0.5.0`;
- documentation validator: PASS, 36 checks, 0 errors, 0 warnings;
- documentation files: 108; Markdown: 98; YAML: 8; examples: 137; local links: 785;
- documentation source tree hash: `sha256:55545e7a39c45c0488ab9d26efa1dcf7aa849413eb604bc36ed3da0afa0a659f`;
- documentation ZIP CRC/exact tree: PASS;
- documentation ZIP SHA-256: `0ae9537d5a78c2cdb250dc73972ab899fc910a8bc7d0f0c4d622fe529b64dfaf`.

Engine ZIP CRC, exact source-tree membership, single top-level directory, path-traversal and symlink checks выполняются как внешний final release check после закрытия static manifest; архив не пытается self-attest собственный hash.

## 11. Scope exclusions и совместимость

- Stage Gate preparation/recovery, strict approvals, exact Gate evidence, Brownfield assessment, canonical target и transaction semantics предыдущих исправлений сохранены;
- maintenance работает только внутри уже accepted product scope;
- future-stage work запрещён;
- не добавлены Change Packs, Git, deployment, repository/executor adapters или автоматический rollback;
- canonical engine, package и schema version остаются `0.5.0` / `6`.

## 12. Итог

M-01 реализован в bounded v0.5.0 scope. Private maintenance stub заменён публичным governed lifecycle с strict exact binding, нормальным Task execution, immutable completion/cancellation history, безопасным level-up interlock и fail-closed cancel semantics. Full regression matrix, focused suite, complete/cancel CLI smoke, doctor, wheel и documentation validation завершились PASS.
