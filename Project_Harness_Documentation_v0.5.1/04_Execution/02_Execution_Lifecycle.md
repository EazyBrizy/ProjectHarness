# Execution lifecycle задачи

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Preconditions

Before side effects:

```text
Task READY/CLAIMED
required artifacts current
material decisions resolved
active primary skill
Prompt/Context/Compatibility resolved
capability grants issued
worktree/environment leases acquired
verification and rollback defined
```

## 2. Run preparation

```text
Create Run Plan
→ JIT compile Prompt Bundle
→ materialize Context Packet
→ verify repository/environment revisions
→ create Run(attempt_no)
→ dispatch through Agent Adapter
```

## 3. Bounded execution

Tool Adapter checks every action against capability, scope, data policy, timeout, idempotency and current lease. Actual writes are recorded and compared with Task Contract.

## 4. Stop conditions

Material ambiguity, missing artifact, hard constraint conflict, scope expansion, unexpected public-contract change, unsafe side effect, denied capability or stale base stops affected task before further writes and returns structured blocker/question.

Non-material reversible detail follows project ambiguity mode.

## 5. Verification

Task uses Verification Profile rather than universal «always run every test» rule. Typical code task runs targeted and nearest regression checks; documentation/config tasks use links/schema/dry-run. Full release suite runs at integration/release gates or high-risk policy.

## 6. Completion

Task becomes `DONE` only when:

- expected result produced;
- REQUIRED_NOW checks pass;
- new regressions absent or resolved;
- actual diff within scope;
- documentation impact resolved;
- evidence and Task Report persisted;
- state transition successful.

Agent self-report alone is insufficient.

## 7. Result and next route

Kernel aggregates Task/Work Package status, renders Result Envelope and selects deterministic next route. Codex may return a hint but cannot choose it.

## 8. Failure/retry

Retry requires retryable error, safe/compensated side effects, current revisions and idempotency strategy. New Run and bundle are created where needed.

Details: specifications 02, 10, 11 and 15 in `12_Implementation_Specifications`.

## 8. v0.4.1 protected phase boundaries

Reservation завершается trusted phase boundary только после записи всех Kernel-owned Run artifacts. Snapshot охватывает product files, весь `.harness/**` control plane и generated root views. Перед verification commands и перед completion движок проверяет changed, deleted, unexpected и unsafe protected paths.

Agent может записать только exact regular UTF-8 JSON result текущего Run по выданному пути. Symlink, hardlink, другой result filename, нестабильный inode/digest или post-verify product change блокируют Run. После safety violation in-place resume запрещён; требуется восстановление из доверенного handoff либо новый Run route.

## 11. v0.5.0 same-level maintenance route

Governed maintenance executes through the same Task runtime without becoming a Stage transition:

```text
strict approved maintenance plan
→ start-maintenance
→ immutable Decision + WP/Tasks/DAG/VFP/CTX/PPL
→ exactly one first JIT Run reservation
→ next → verify → complete
→ [next maintenance Task | immutable completion report]
→ restore previous route
```

The executable fence is the accepted stage, not a future canonical active stage:

```text
execution_stage = highest_accepted_level
maintenance_route = MAINTAIN_CURRENT_STAGE
accepted_maturity_change = FORBIDDEN
```

Normal final completion sets the maintenance WP to `COMPLETED`; it does not invoke Stage Gate readiness, `accept-stage`, or `level-up`. A formal pre-product-change cancel may set open Task/WP revisions to `CANCELLED` and preserve a reserved/blocked Run as immutable history. A completed product-changing Task, an observed completed product diff, or an uncommitted product drift from the trusted Run snapshot makes silent cancel invalid; Project Harness never invents an automatic rollback.

Start, cancel and final completion use the crash-recovery transaction service for canonical route state. Replaying the same approved plan/Decision is idempotent and cannot create duplicate WP/Tasks/Runs or a second first bundle.

## 12. v0.5.0 Stage Gate boundary

Runtime выдаёт и компилирует только Task с `implementation_stage == active_stage`. Intentional future-stage-only implementation классифицируется `STAGE_SCOPE_VIOLATION`.

После последней ordinary mandatory Task runtime не переходит безусловно к manual review. Он вычисляет canonical final product-tree baseline и exact missing Gate evidence items. Если gaps существуют, одной Stage transaction создаются idempotent `STAGE_ACCEPTANCE_PREPARATION` WP/atomic Task, Context/Prompt/Verification Plans, DAG, current-task/index/state projections и ровно один первый JIT bundle. Task проходит обычные `next → verify → complete` semantics; после PASS kernel материализует **только** доказательства, для которых действительно есть конкретный compatible subject/source/method/coverage и exact final-baseline binding. Общий PASS report не подменяет архитектурный документ, permitted use, external source либо другую семантику. Если после Task mandatory gaps сохраняются, Gate остаётся незакрытым/`BLOCKED` с recovery; невозможность доказать item не порождает бесконечные новые Tasks. Лишь при полном compatible evidence coverage Gate становится `VERIFYING`.

`accept-stage` требует formal approval. Malformed/stale/wrong-ref record отклоняется до mutation. Structurally valid review с mandatory `UNKNOWN/PARTIAL/FAIL` атомарно создаёт BLOCKED Plan/Gate revisions, distinct `STAGE_GATE_BLOCKER` и route `RESOLVE_STAGE_GATE`, без Acceptance Report. `resume-stage-gate` revalidates baseline/evidence и создаёт новые ACTIVE/VERIFYING revisions. Closed approval атомарно записывает Acceptance Report, Stage State revision и nearest-next-stage activation; при target acceptance status равен `TARGET_LEVEL_REACHED`.

## PH-051-11 WIP — current operator continuation (addendum)

Текущий `PROJECT_INPUT@4` всегда требует explicit `execution`. Default `MANUAL_HANDOFF` сохраняет `next → external Codex → verify [--allow-command-execution при разрешении оператора] → complete --result <exact-path>`. В PH-051-09 добавлены публичные `executor-doctor` и `execute-current`; только уже корректно подписанный `LOCAL_AUTOMATIC` и успешные реальные Podman isolation probes допускают `RUNNING → independent SANDBOXED verification → validated atomic apply → COMPLETED` или ожидание `complete`. Generic agent exit=0/`COMPLETED` не заменяет верификацию или Gate proof. Stage Gate/level-up по-прежнему отдельно формально принимаются. Manual project `execute-current` → `BLOCKED / EXECUTOR_UNAVAILABLE` без автоматического переключения. Неисправный sandbox → `BLOCKED`, новый Run только после governed resume. `prepare` для нового `LOCAL_AUTOMATIC` пока возвращает `AUTOMATIC_EXECUTOR_NOT_IMPLEMENTED`: это известный pre-existing blocker, а не разрешение редактировать lock. См. [операторский runbook](../05_Updates/14_Operator_Runbook_v0.5.1_WIP.md).
