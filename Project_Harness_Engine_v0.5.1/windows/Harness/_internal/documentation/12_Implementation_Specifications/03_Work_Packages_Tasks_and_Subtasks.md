# Work Packages, задачи и подзадачи

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Большой пользовательский запрос должен превращаться не в один перегруженный prompt и не в десятки бессвязных prompts, а в понятный `Work Package` с минимальным набором atomic tasks.

Целевая иерархия:

```text
Request
→ Work Package
  → Atomic Task
  → Atomic Task
  → Integration Task
→ Runs
```

`Work Package` группирует пользовательский outcome. Он не исполняется агентом. Исполняются только atomic tasks.

## 2. Основные сущности

### 2.1. Work Package

Содержит:

- исходный пользовательский outcome;
- scope и границы;
- список mandatory и optional tasks;
- dependency graph;
- aggregation rule;
- overall acceptance;
- progress и next route.

### 2.2. Atomic Task

Atomic task имеет:

- один основной проверяемый результат;
- ограниченный write scope;
- известные входные артефакты;
- одну primary skill route;
- пропорциональный verification profile;
- понятный rollback;
- следующий кандидат, но не сам выбирает его.

### 2.3. Task Group

`Task Group` — необязательное представление для UI или больших work packages. Он не является отдельной исполняемой сущностью и не добавляет обязательный prompt.

## 3. Work Package Contract

```yaml
work_package:
  id: WP-AUTH-001
  revision: 1
  request_refs: [RQ-20260806-0002]
  project_ref: project-example

  title: "Добавить вход пользователя"
  objective: "Пользователь может безопасно войти по email и паролю"
  outcome_refs: [OUT-AUTH-001]
  requirement_refs: [REQ-AUTH-001, REQ-AUTH-002]
  constraint_refs: [CST-SEC-001]
  architecture_refs: [ADR-AUTH-003]
  documentation_refs: [DOC-REQ-AUTH@2]

  scope:
    in: [api/auth, ui/login, tests/auth, docs/auth]
    out: [billing, admin]

  tasks:
    mandatory:
      - TSK-CNT-AUTH-010
      - TSK-BE-AUTH-020
      - TSK-FE-AUTH-030
      - TSK-INT-AUTH-040
    optional: []

  dependency_graph_ref: DAG-WP-AUTH-001@1
  aggregation:
    completion_rule: ALL_MANDATORY_PASS
    result_mode: SINGLE_USER_OUTCOME

  acceptance_criteria:
    - id: AC-WP-AUTH-001
      statement: "Успешный вход создаёт валидную сессию"
      verification_task_ref: TSK-INT-AUTH-040

  status: READY
  progress:
    completed: 0
    total_mandatory: 4
  next_task_ref: TSK-CNT-AUTH-010
```

## 4. Расширенный Task Contract

```yaml
task:
  id: TSK-BE-AUTH-020
  revision: 1
  work_package_ref: WP-AUTH-001
  implementation_stage: PROTOTYPE
  parent_task_ref: null
  child_task_refs: []

  title: "Реализовать backend обработчик входа"
  type: IMPLEMENT
  track: BACKEND
  priority: HIGH

  purpose: "Обеспечить серверную часть принятого auth contract"
  expected_result: "Endpoint /login соответствует CNT-AUTH@1"

  requirement_refs: [REQ-AUTH-001]
  constraint_refs: [CST-SEC-001]
  architecture_refs: [ADR-AUTH-003]
  documentation:
    source_refs:
      - entity_ref: DOC-API-AUTH
        document: docs/api/auth.md
        section_id: login
        revision: 2
    impact: UPDATE_EXISTING
    required_updates:
      - document: docs/api/auth.md
        section_id: login
        reason: "Изменяется реализация login endpoint"

  depends_on_tasks: [TSK-CNT-AUTH-010]
  requires_artifacts:
    - ref: CNT-AUTH@1
      producer_task_ref: TSK-CNT-AUTH-010
      required_status: ACCEPTED
      access: READ

  produces_artifacts:
    - ref: IMPL-BE-AUTH@1
      type: CODE
    - ref: EVD-BE-AUTH@1
      type: EVIDENCE

  scope:
    read: [contracts/auth/**, src/shared/**]
    write: [src/auth/**, tests/auth/backend/**]
    forbidden: [ui/**, migrations/**]

  route:
    primary_skill_ref: SKL-IMPLEMENT-SERVICE@2
    supporting_skill_refs: [SKL-SECURITY-REVIEW@1]
    required_capabilities: [FILESYSTEM_READ, FILESYSTEM_WRITE, COMMAND_EXECUTE]

  prompt_spec_ref: PSP-IMPLEMENT@1
  context_policy_ref: CTP-TASK-STANDARD@1
  verification_profile_ref: VFP-CODE-TARGETED@1

  acceptance_criteria:
    - ref: AC-AUTH-BE-001

  rollback:
    strategy: REVERT_WORKTREE

  status: PLANNED
```

## 5. Когда задача считается слишком большой

Задача должна быть разделена, если выполняется хотя бы одно условие:

- имеет более одного независимого пользовательского результата;
- требует разных primary skills;
- меняет несколько independently deployable компонентов;
- содержит material decision и реализацию этого решения одновременно;
- требует разных permission scopes;
- имеет несвязанные acceptance criteria;
- не может быть проверена одним verification profile;
- превышает configured change-size threshold;
- включает contract design, producer implementation и consumer integration без явных промежуточных artifacts;
- её безопасный rollback требует отката независимых частей.

## 6. Когда не нужно дробить задачу

Не следует создавать отдельную task для каждого файла, функции или команды. Сохранять одну task допустимо, если:

- изменения служат одному результату;
- имеют один bounded scope;
- проверяются одним набором checks;
- выполняются одной skill route;
- не создают независимого integration gate;
- промежуточное состояние не имеет самостоятельной ценности.

Цель — минимальное достаточное число tasks, а не максимальная детализация.

## 7. Алгоритм декомпозиции

```text
1. Extract the user-visible outcome.
2. Resolve requirements, constraints and accepted architecture.
3. Identify required output artifacts.
4. For every output artifact, identify producers and consumers.
5. Split material decisions from implementation.
6. Split incompatible write scopes, skills or permission sets.
7. Add integration task only where cross-component acceptance is needed.
8. Merge trivial adjacent units that share outcome, route and verification.
9. Validate DAG and artifact availability.
10. Produce Work Package Draft and decomposition rationale.
```

Inference worker может предложить decomposition, но kernel обязан проверять atomicity, cycles, missing producers и scope conflicts.

## 8. Parent/child semantics

По умолчанию иерархия реализуется через Work Package. `parent_task_ref` применяется только при runtime split уже существующей task:

```text
TSK-ORIGINAL status → SPLIT
TSK-CHILD-A and TSK-CHILD-B created
original acceptance → aggregation rule over children
original task is never executed again
```

История исходной task сохраняется. Нельзя тихо заменить её двумя tasks без event и source map.

## 9. Artifact-first dependencies

Task dependency должна объяснять не только «ждать задачу X», но и какой артефакт нужен.

```yaml
requires_artifacts:
  - ref: CNT-SEARCH@2
    producer_task_ref: TSK-CNT-SEARCH-010
    required_status: ACCEPTED
```

Kernel проверяет:

- producer существует;
- producer расположен раньше consumer;
- artifact version удовлетворяет requirement;
- artifact не stale;
- access mode согласован с parallel policy;
- placeholder не считается готовым artifact.

## 10. Lifecycle

Work Package:

```text
DRAFT → PLANNED → READY → IN_PROGRESS → COMPLETED
                         ↘ PARTIAL
                         ↘ BLOCKED
DRAFT/PLANNED/READY/IN_PROGRESS → CANCELLED | SUPERSEDED
```

Task:

```text
DRAFT → PLANNED → READY → CLAIMED → RUNNING → VERIFYING → DONE
                           ↘ BLOCKED
                           ↘ FAILED_RECOVERABLE
                           ↘ SPLIT
Any non-terminal → CANCELLED | STALE | SUPERSEDED
```

`DONE` требует mandatory verification and documentation impact resolution.

## 11. Aggregation и следующий шаг

Deterministic next task выбирается kernel по:

1. dependency readiness;
2. artifact availability;
3. priority;
4. risk reduction;
5. critical path;
6. stable tie-breaker by task ID.

Agent не выбирает следующую задачу самостоятельно. Он может вернуть candidates, но Result Envelope использует решение planner/kernel.

## 12. Пример декомпозиции большой задачи

Пользователь:

> Добавь поиск в backend и frontend, миграцию индекса, тесты и документацию.

Work Package:

```text
TSK-CNT-SEARCH-010    определить/подтвердить search contract
TSK-DB-SEARCH-020     добавить индекс и migration verification
TSK-BE-SEARCH-030     реализовать backend по contract
TSK-FE-SEARCH-040     реализовать frontend по contract
TSK-INT-SEARCH-050    интеграционные acceptance checks и docs reconciliation
```

После `TSK-CNT-SEARCH-010` database, backend и frontend могут быть READY в зависимости от read/write sets. Это пять задач, а не десятки prompts по числу файлов.

## 13. Критерии приёмки

1. Большой request создаёт один Work Package и минимальный набор atomic tasks.
2. Каждая task имеет один expected result, primary skill и verification profile.
3. Все required artifacts имеют producer или являются accepted external inputs.
4. DAG не содержит циклов и future-only dependencies.
5. Runtime split сохраняет lineage и не теряет acceptance criteria.
6. Work Package status агрегируется детерминированно.
7. Agent получает только одну task или утверждённый safe parallel batch.
8. UI может показать пользователю цель, прогресс, блокировку и следующий шаг без чтения prompt bundles.
