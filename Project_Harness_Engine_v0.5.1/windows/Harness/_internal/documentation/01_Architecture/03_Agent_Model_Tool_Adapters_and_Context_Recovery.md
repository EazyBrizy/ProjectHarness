# Agent, model и tool adapters; восстановление контекста

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Разделение адаптеров

| Adapter | Ответственность |
|---|---|
| Agent Adapter | Render compiled bundle, mediate execution and normalize structured result. |
| Model Profile/Adapter | Declare supported input/output/context/data capabilities. |
| Tool Adapter | Enforce capability, scope, audit, timeout and side-effect semantics. |
| Repository Adapter | Revisions, branches, worktrees, diffs and publication. |
| Source Parser | Extract trusted data candidates from documents/repositories. |

## 2. Codex first

Codex is the first Agent Adapter, not universal kernel logic. It receives one bounded Task Contract and cannot select project scope, ADR, permissions or next task. Full contract: [`../12_Implementation_Specifications/15_Codex_Agent_Adapter.md`](../12_Implementation_Specifications/15_Codex_Agent_Adapter.md).

## 3. Generated guidance

Root `AGENTS.md` is a compact generated recovery view:

- project identity and current baseline refs;
- how to locate state/current assigned task;
- source precedence and critical invariants;
- scope/decision/blocker protocol;
- publication rule;
- links to nested guidance.

It does not contain the full roadmap or mutable current task text.

## 4. Cold start

```text
nearest trusted guidance
→ project lock/config
→ current Project/Brownfield Definition
→ constraints and accepted decisions
→ architecture and Technology Baseline
→ state and active Work Package
→ assigned Task Contract
→ Prompt/Context/Run Plan
→ relevant reports/evidence
→ repository revisions and leases
```

Agent session memory is not canonical.

## 5. Compatibility

Before Run, kernel checks required capabilities, data policy, output schema, context fit, adapter/tool versions, repository/environment state, permissions and current revisions.

```text
COMPATIBLE
COMPATIBLE_WITH_REDUCTION
FALLBACK_REQUIRED
WAITING_DECISION
UNSUPPORTED
```

Reduction cannot remove mandatory source or constraint.

## 6. Adapter invariants

Adapter must:

- accept immutable bundle/grants;
- reject incompatible context or unsupported output contract;
- not mutate canonical state directly;
- return structured result and tool trace;
- enforce redaction and data policy;
- support cancellation boundary;
- prevent unauthorized side effects;
- expose version/provenance;
- avoid provider billing/token accounting fields.

## PH-051-11 WIP — две различные модели исполнения

`MANUAL_HANDOFF` остаётся default: browser GPT только собирает исходные ответы, approvals, canonical `PROJECT_INPUT@4` и handoff; внешний Codex/оператор работает по текущему JIT. `LOCAL_AUTOMATIC` (для ранее точно и легитимно opt-in проекта) — единственный adapter `CODEX_CLI_LOCAL`, один OS backend `ROOTLESS_PODMAN`, независимый verifier, bounded Apply Evidence и governed completion. Agent работает только в disposable product root; canonical repository и `.harness` не являются agent-write mounts. `doctor` distribution не аттестует OS sandbox, `executor-doctor` — только после действительных Podman probes. Отсутствие Podman/незавершённый self-test/отказ egress → BLOCKED и никакого host execution. Непосредственный публичный `prepare` пока отклоняет новый `LOCAL_AUTOMATIC` input; не редактировать принятую control plane вручную как workaround. См. [runbook](../05_Updates/14_Operator_Runbook_v0.5.1_WIP.md), [security matrix](../05_Updates/15_Podman_Security_Validation_v0.5.1_WIP.md).
