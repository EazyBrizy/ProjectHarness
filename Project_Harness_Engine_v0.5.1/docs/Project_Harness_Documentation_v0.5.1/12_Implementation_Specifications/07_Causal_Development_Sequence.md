# Причинный порядок разработки и readiness

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

«Строго хронологический порядок» в Harness означает не один длинный список, а причинный порядок: никакая задача не становится READY, если необходимый ей функционал, contract, environment или decision ещё не существует.

Правило:

> Consumer task не может начинаться раньше, чем все её обязательные input artifacts произведены, приняты и совместимы.

## 2. Причинная модель

```text
Requirement / Constraint / Decision
→ Contract or Baseline Artifact
→ Producer Implementation
→ Consumer Implementation
→ Integration Verification
→ Release Gate
```

Зависимость должна указывать:

- producer task;
- produced artifact;
- required version/status;
- access mode;
- compatibility rule.

## 3. Типы зависимостей

```text
REQUIRES_ARTIFACT
REQUIRES_DECISION
REQUIRES_ENVIRONMENT
REQUIRES_CAPABILITY
REQUIRES_VERIFICATION
REQUIRES_INTEGRATION
ORDER_ONLY
```

`ORDER_ONLY` допускается редко и требует rationale. Предпочтительна содержательная artifact dependency.

## 4. Readiness Contract

```yaml
task_readiness:
  task_ref: TSK-FE-SEARCH-040@1
  evaluated_at: 2026-08-06T11:00:00Z
  base_revision: sha256:...

  checks:
    task_schema: PASS
    project_gate: PASS
    requirement_state: PASS
    decision_state: PASS
    artifact_dependencies: PASS
    environment_dependencies: PASS
    skill_state: PASS
    scope_conflicts: PASS
    verification_profile: PASS
    documentation_refs: PASS

  missing: []
  stale: []
  conflicts: []
  status: READY
```

Task получает `READY` только при `PASS` всех mandatory checks.

## 5. Алгоритм построения DAG

```text
1. Start from accepted outcomes and requirements.
2. Identify material decisions and baselines.
3. Identify public/internal contracts required by multiple components.
4. Identify bootstrap and environment prerequisites.
5. Define producer tasks for every required artifact.
6. Define consumer and integration tasks.
7. Add verification/release gates.
8. Topologically sort graph.
9. Reject cycles and missing producers.
10. Calculate critical path and safe parallel layers.
```

## 6. Запрет future-only dependencies

Недопустимые конструкции:

- «использовать сервис, который будет добавлен позже»;
- placeholder считается завершённым contract;
- frontend реализуется по непроверенной устной форме API;
- migration test ожидает test database, bootstrap которой отсутствует;
- task ссылается на skill, который ещё только планируется создать;
- verification command требует tool adapter, не включённый в Technology/Capability Baseline.

Planner должен либо:

- добавить producer task раньше;
- изменить текущий scope;
- использовать accepted external artifact;
- остановить route как `BLOCKED` с recovery options.

## 7. Greenfield causal sequence

```text
Mandatory Start Questionnaire
→ Project Definition Gate
→ Requirements + Constraints
→ Architecture + Technology Decision Gate
→ Skill Gap Analysis and Skill Readiness
→ Bootstrap Baseline
→ Contract-first Planning
→ Implementation Layers
→ Integration
→ Release
```

Prompt infrastructure для product tasks готовится только после того, как приняты необходимые baseline decisions. До этого допустимы discovery/decision prompts.

## 8. Brownfield causal sequence

```text
Repository and Documentation Inventory
→ Build/Test/Runtime Reconnaissance
→ Actual Architecture and Contract Extraction
→ Reconciliation of Docs vs Code
→ Brownfield Baseline Gate
→ Continuation / Improvement / Bug-fix Branch Planning
→ Skill/Environment Gaps
→ READY Tasks
```

Нельзя сначала генерировать новые implementation prompts, а затем выяснять структуру существующего проекта.

## 9. Вертикальные срезы

Для реализации самого Harness roadmap строится вокруг раннего walking skeleton:

| ID | Каноническое название |
|---|---|
| `WP-HARNESS-000` | Core registries, schemas and storage |
| `WP-HARNESS-005` | Single Entry, Request and Result contracts |
| `WP-HARNESS-010` | First end-to-end walking skeleton |
| `WP-HARNESS-020` | Questionnaire and Project Definition |
| `WP-HARNESS-030` | Brownfield inventory and reconciliation |
| `WP-HARNESS-040` | Requirements, ADR, architecture and Technology Baseline |
| `WP-HARNESS-050` | Skill Registry, bootstrap and verification baselines |
| `WP-HARNESS-060` | Work Packages, artifact DAG and safe parallelism |
| `WP-HARNESS-070` | JIT Prompt/Context compiler |
| `WP-HARNESS-080` | Codex Adapter, governed runtime and traces |
| `WP-HARNESS-090` | Verification, documentation and integration |
| `WP-HARNESS-100` | Blockers, resume and Change Packs |
| `WP-HARNESS-110` | Git/publication, security and evaluation suites |
| `WP-HARNESS-120` | Pilots and release |

Названия, dependencies, outputs и acceptance criteria нормативно задаются только в [`../09_Delivery/02_Implementation_Roadmap.md`](../09_Delivery/02_Implementation_Roadmap.md). Эта таблица является проверяемым индексом и не определяет отдельную последовательность. `HNS-REQ-*` используется только для документационных требований.

Каждый этап расширяет уже работающую end-to-end цепочку. Интеграция не откладывается до последнего этапа.

## 10. Deterministic next task

Из множества READY tasks kernel выбирает recommended next task по порядку:

1. explicit user selection;
2. unblock critical path;
3. reduce material uncertainty/risk;
4. satisfy earliest integration dependency;
5. higher product priority;
6. smaller reversible step;
7. stable lexical task ID.

Planner может предложить safe parallel batch. Пользовательский Result Envelope показывает recommended next step и доступные альтернативы.

## 11. Изменение DAG во время разработки

Новый факт, bug или change request может изменить граф. Harness обязан:

1. создать Change Pack или issue-derived Work Package;
2. выполнить impact analysis;
3. пометить affected tasks `STALE`;
4. сохранить completed history;
5. добавить/изменить dependencies;
6. повторно проверить topological order;
7. пересчитать next route.

Завершённые tasks не переписываются; при необходимости создаются corrective tasks.

## 12. Integration tasks

Integration task обязательна, когда:

- несколько independent tasks реализуют один user outcome;
- backend и frontend должны быть проверены вместе;
- contract consumers/producers требуют compatibility check;
- изменения затрагивают несколько repositories;
- migration + application rollout имеют порядок;
- shared environment должен быть подтверждён.

Integration task не должна повторять unit work. Она проверяет границы и общий acceptance.

## 13. Пример

```text
TSK-CNT-010  Принять API contract                 DONE
TSK-DB-020   Добавить индекс                      READY
TSK-BE-030   Реализовать endpoint                 READY
TSK-FE-040   Реализовать UI по CNT@1              READY
TSK-INT-050  Сквозной сценарий                    WAITING (020,030,040)
TSK-REL-060  Release checks                       WAITING (050)
```

Здесь 020, 030 и 040 находятся в одном causal layer и могут выполняться параллельно при отсутствии write conflicts.

## 14. Проверки planner

```text
DAG_ACYCLIC
ALL_REQUIRED_ARTIFACTS_HAVE_PRODUCER
PRODUCER_PRECEDES_CONSUMER
REQUIRED_REVISION_EXISTS
NO_PLACEHOLDER_AS_ACCEPTED_ARTIFACT
ALL_READY_TASKS_HAVE_ACTIVE_SKILLS
ALL_READY_TASKS_HAVE_VERIFICATION_PROFILE
INTEGRATION_COVERS_CROSS_TRACK_OUTCOME
```

## 15. Критерии приёмки

1. Task не становится READY при отсутствующем producer artifact.
2. Planner обнаруживает циклы и future-only dependencies.
3. Greenfield и brownfield имеют явные baseline gates до implementation.
4. Deterministic next task воспроизводим.
5. Safe parallelism разрешён внутри causal layer.
6. Integration tasks закрывают cross-track acceptance.
7. Roadmap Harness содержит ранний working vertical slice.
8. Change Pack корректно инвалидирует и перестраивает affected graph.
