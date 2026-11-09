# Термины и роли

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Основные термины

| Термин | Определение |
|---|---|
| Request | Неизменяемая запись пользовательского ввода, classification, mode and correlation ID. |
| Request Plan | DAG внутренних routes, преобразующий Request в answer, intake, Work Package or maintenance result. |
| Result Envelope | Единый пользовательский результат со status, changes, verification, blockers and next route. |
| Intake Session | Временный контекст опроса и анализа до принятия Project Definition. |
| Project Definition | Принятая модель целей, users, scope, success criteria, assumptions, unknowns and risks. |
| Brownfield Baseline | Принятое фактическое starting state existing project after reconciliation. |
| Technology Baseline | Принятые technologies, versions, compatibility and decision refs. |
| Work Package | Неисполняемая группа atomic tasks, закрывающая один user outcome. |
| Atomic Task | Bounded executable unit с одним expected result. |
| Artifact Dependency | Required input с producer, version/status and access mode. |
| Prompt Module | Reusable canonical Prompt IR fragment. |
| Prompt Spec | Reusable logical template класса tasks. |
| Prompt Plan | Resolved generated plan конкретной READY task. |
| Compiled Prompt Bundle | Immutable payload одного Run. |
| Skill | Versioned repeatable workflow with contracts, capabilities and evaluations. |
| Run Plan | Immutable execution plan before side effects. |
| Run | Одна конкретная attempt выполнения Task; retry создаёт новый Run. |
| Request Trace | Correlated event/spans от input до Result Envelope. |
| Evidence | Проверяемый результат check с provenance and revisions. |
| Change Pack | Quarantined normalized change for exactly one target plane. |
| Project Harness Instance | Project-local control plane in `.harness/`. |

## 2. Эпистемические статусы

```text
UNKNOWN
ASSUMED
PROPOSED
CONFIRMED
CONFLICTING
REJECTED
SUPERSEDED
```

Они не заменяют lifecycle status.

## 3. Роли

| Роль | Ответственность |
|---|---|
| Project Sponsor | Outcome and material scope. |
| Product/Domain Owner | Requirements, users and acceptance. |
| Architecture Approver | Material architecture/technology decisions. |
| Security Approver | Data, trust, dangerous permissions and waivers. |
| Repository Owner | Git/publication policy. |
| Harness Operator | Single-entry interaction, plans and approvals. |
| Agent Executor | Bounded Task execution; Codex is first adapter. |
| Validator | Independent checks and evidence. |
| Harness Maintainer | Project Control or Distribution maintenance. |

Один человек может совмещать роли, но authority фиксируется по scope and decision.

## 4. Нормативные registries

Полные ID/status/profile lifecycles: [`../12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md`](../12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md).
