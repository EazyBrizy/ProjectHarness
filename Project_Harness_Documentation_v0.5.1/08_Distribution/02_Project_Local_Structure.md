# Project-local structure и Codex handoff

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION BASELINE

## 1. Human-readable root

```text
CODEX_START.md
AGENTS.md
HANDOFF_SUMMARY.md
PROJECT.md
ARCHITECTURE.md
TECHNOLOGY.md
ROADMAP.md
STATUS.md
MANIFEST.sha256
```

`CODEX_START.md` указывает текущую READY Task и точные runtime commands. Human views воспроизводимы из canonical state.

## 2. Control plane

```text
.harness/
├── config/
│   ├── PROJECT.yaml
│   └── PROJECT_LOCK.yaml
├── sessions/
├── requests/
│   ├── REQUESTS/
│   ├── PLANS/
│   ├── RESULTS/
│   └── TRACES/
├── intake/
│   ├── SOURCES/
│   ├── INVENTORIES/
│   ├── QUESTIONNAIRES/
│   ├── QUESTIONS/
│   ├── ANSWERS/
│   └── BROWNFIELD/
├── canonical/
│   ├── DEFINITION/
│   │   └── BROWNFIELD/
│   ├── REQUIREMENTS/
│   ├── CONSTRAINTS/
│   ├── DECISIONS/
│   ├── ARCHITECTURE/
│   ├── TECHNOLOGY/
│   ├── CONTRACTS/
│   └── DOCUMENTATION/
├── work-packages/
│   └── ROUTE_PORTFOLIO/
├── tasks/
├── dags/
├── prompts/
│   ├── PLANS/
│   └── BUNDLES_BY_RUN/
├── context/
│   ├── POLICIES/
│   ├── PLANS/
│   └── PACKETS_BY_RUN/
├── skills/
│   ├── registry.yaml
│   ├── DRAFT/
│   ├── VALIDATING/
│   ├── VALIDATED/
│   ├── REJECTED/
│   ├── ACTIVE/
│   ├── SUSPENDED/
│   ├── DEPRECATED/
│   ├── RETIRED/
│   ├── EVALUATIONS/
│   └── MIGRATIONS/
├── verification/
│   ├── PROFILES/
│   ├── TEST_ENVIRONMENTS/
│   └── BASELINES/
├── runtime/
│   ├── RUN_PLANS/
│   ├── RUNS/
│   ├── AGENT_RESULTS/
│   ├── TOOL_INVOCATIONS/
│   ├── CAPABILITY_GRANTS/
│   ├── LEASES/
│   └── PARALLEL_BATCHES/
├── evidence/
├── reports/
├── blockers/
├── changes/
├── migrations/
├── events/
├── state/
├── generated/
├── incoming/
└── engine/
```

## 3. Storage rules

- provisional intake существует вне project-local tree до handoff;
- `incoming/` immutable/quarantined;
- canonical entities schema-valid и revisioned;
- `Run` является одной immutable attempt;
- bundle/context packet привязан к конкретному Run;
- completed runs, evidence и events append-only;
- `.harness/skills/registry.yaml` является reproducible generated index, не отдельным source of truth;
- lifecycle directories skills соответствуют `registries/statuses.yaml`;
- generated views не редактируются напрямую;
- secrets хранятся как external secret references.

## 4. JIT invariant

На initial handoff существует ровно один compiled bundle — для текущей READY Task. Для будущих tasks существуют contracts/plans, но compiled bundle создаётся только после перехода state.

## 5. Mutable project validation

`validate-handoff` проверяет первоначальный immutable manifest. После разрешённых product changes используется `validate-project`, который проверяет canonical state, task/run relationships, scope/evidence и current route без требования совпадения исходного product digest.

## 6. Minimal mode

MINIMAL может материализовать меньше human views и агрегировать reports, но machine semantics, permissions, scope verification и Evidence сохраняются. Подробности: [`../12_Implementation_Specifications/17_Documentation_Layers_and_Minimal_Mode.md`](../12_Implementation_Specifications/17_Documentation_Layers_and_Minimal_Mode.md).

## 7. Brownfield install

Исходный repository не изменяется во время intake/prepare. Project-local tree создаётся внутри выходного handoff после accepted baseline. Любая последующая restructuring оформляется отдельной Task с declared write scope.

## 8. v0.5.0 Stage control plane

К project-local tree добавляются exact contract paths:

```text
.harness/stages/STAGE_STATE.yaml
.harness/stages/PLANS/
.harness/stages/GATES/
.harness/stages/ACCEPTANCE/
.harness/stages/ASSESSMENTS/
.harness/stages/STATE_HISTORY/
.harness/stages/TRANSACTIONS/
```

Каждая Stage transaction materializes as:

```text
.harness/stages/TRANSACTIONS/<transaction-id>/
├── TRANSACTION.yaml
├── backups/
├── staged/
└── recovery/
```

`TRANSACTION.yaml`, backups и staged candidates создаются до первого canonical replace. Terminal journal остаётся audit/recovery evidence и не удаляется после commit/rollback. Acceptance/assessment records immutable; Stage State versioned with history. Uppercase paths нормативны.

## 9. Mutable project validation and Stage recovery

`validate-project` сначала reconciles pending Stage transactions, затем выполняет обычные canonical/cross-reference checks. Corrupt journal, missing backup, duplicate sequence или mixed canonical write set возвращают validation `FAIL` и блокируют следующую Stage mutation. Initial `validate-handoff` по-прежнему проверяет immutable distribution manifest; post-handoff recovery относится к mutable project validation.

PH‑F04 добавляет отдельную проверку `Persisted runtime continuation and Stage boundary reachability` в `validate-project`. Она проверяет реальность публичного continuation, согласованность Stage State/Plan/Gate, executable-stage fence для current Task/Run, актуальные блокировки и `NEXT_TASK` boundary projection. Legacy pre-migration v0.4.1 остаётся в собственном compatibility contract. Формальные решения и действительные внешние prerequisites не создаются автоматически.
