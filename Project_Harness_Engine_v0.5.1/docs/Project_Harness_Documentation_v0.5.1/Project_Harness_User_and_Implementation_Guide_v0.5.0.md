# Project Harness — пользовательское и реализационное руководство v0.5.0

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** GENERATED IMPLEMENTATION GUIDE — редактировать source specifications

Руководство воспроизводимо собрано из 24 нормативных implementation specifications. Source path markers являются частью generation contract.

## Состав

1. `12_Implementation_Specifications/01_Single_Entry_Request_Contract.md`
2. `12_Implementation_Specifications/02_Result_Envelope_and_Statuses.md`
3. `12_Implementation_Specifications/03_Work_Packages_Tasks_and_Subtasks.md`
4. `12_Implementation_Specifications/04_JIT_Prompt_Compilation.md`
5. `12_Implementation_Specifications/05_Documentation_Traceability.md`
6. `12_Implementation_Specifications/06_ADR_and_Decision_Policy.md`
7. `12_Implementation_Specifications/07_Causal_Development_Sequence.md`
8. `12_Implementation_Specifications/08_Safe_Parallel_Execution.md`
9. `12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md`
10. `12_Implementation_Specifications/10_Blockers_Recovery_and_Progression.md`
11. `12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md`
12. `12_Implementation_Specifications/12_Request_Trace_and_Logging.md`
13. `12_Implementation_Specifications/13_Technology_Baseline.md`
14. `12_Implementation_Specifications/14_Skill_Registry_and_Lifecycle.md`
15. `12_Implementation_Specifications/15_Codex_Agent_Adapter.md`
16. `12_Implementation_Specifications/16_Harness_Maintenance_Plane.md`
17. `12_Implementation_Specifications/17_Documentation_Layers_and_Minimal_Mode.md`
18. `12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md`
19. `12_Implementation_Specifications/19_Semantic_Documentation_Validation.md`
20. `12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md`
21. `12_Implementation_Specifications/21_Project_Start_Questionnaire.md`
22. `12_Implementation_Specifications/22_Browser_GPT_Preparation_and_Codex_Handoff.md`
23. `12_Implementation_Specifications/23_Contract_Hardening_v0.4.1.md`
24. `12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md`

---

<!-- SOURCE: 12_Implementation_Specifications/01_Single_Entry_Request_Contract.md -->

## Единая точка входа и Request Contract

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Единая точка входа — единственный обязательный пользовательский интерфейс Project Harness. Пользователь пишет обычным языком. Он не обязан знать команды `init`, `define`, `compile`, `route`, `run`, `resume` или внутренние идентификаторы.

Точка входа должна одинаково корректно обрабатывать:

- обычный вопрос о проекте или Harness;
- начало нового проекта;
- подключение существующего проекта;
- задачу разработки;
- изменение уже принятого scope или архитектуры;
- запрос состояния;
- восстановление заблокированной задачи;
- обслуживание project-local control plane;
- обслуживание самой Harness Distribution.

Единая точка входа является тонким orchestrator. Она не должна содержать всю документацию и не должна выполнять работу Codex самостоятельно.

### 2. Разделение понятий

Маршрутизация строится по трём независимым осям.

#### 2.1. Request Class

`Request Class` описывает пользовательский смысл запроса.

<!-- REGISTRY-ENUM: request_classes -->
```text
QUERY
PROJECT_START
DEVELOPMENT_REQUEST
PROJECT_EVOLUTION
PROJECT_CONTROL_MAINTENANCE
HARNESS_DISTRIBUTION_MAINTENANCE
CONTROL_REQUEST
```
<!-- /REGISTRY-ENUM -->

| Класс | Когда применяется | Создаёт task |
|---|---|---:|
| `QUERY` | Вопрос, объяснение, чтение статуса или документации без side effects. | Нет, если пользователь не просит изменения. |
| `PROJECT_START` | Новый greenfield, brownfield или hybrid project intake. | Сначала создаёт Intake Session; tasks появляются после readiness. |
| `DEVELOPMENT_REQUEST` | Реализация, исправление, тестирование, рефакторинг, документация продукта. | Да. |
| `PROJECT_EVOLUTION` | Изменение принятого scope, requirement, architecture или technology baseline. | Создаёт Change Pack и затем tasks. |
| `PROJECT_CONTROL_MAINTENANCE` | Изменение project-local prompts, routes, skills, policies или adapters. | Да, в изолированном control-plane work package. |
| `HARNESS_DISTRIBUTION_MAINTENANCE` | Изменение universal kernel, schemas, generic modules, profiles и adapters. | Да, только в distribution workspace. |
| `CONTROL_REQUEST` | `status`, `next`, `resume`, `cancel`, `approve`, `reject`, `publish`. | Обычно нет product task; может запустить существующий route. |

#### 2.2. Request Mode

<!-- REGISTRY-ENUM: request_modes -->
```text
READ_ONLY
PLAN
EXECUTE
```
<!-- /REGISTRY-ENUM -->

- `READ_ONLY` запрещает writes и внешние side effects.
- `PLAN` разрешает canonical candidates, Request Plan и Work Package Draft, но не product changes.
- `EXECUTE` разрешает execution только после всех gates и capability checks.

Явное указание пользователя имеет приоритет. При отсутствии явного указания применяется самый безопасный режим, совместимый с запросом.

#### 2.3. Internal Operation

Операция является внутренним шагом маршрута, а не пользовательским intent.

<!-- REGISTRY-ENUM: internal_operations -->
```text
ANSWER
INSPECT_SOURCES
START_INTAKE
ASK_QUESTION_BATCH
RECONCILE_PROJECT
DEFINE_PROJECT
PROPOSE_ARCHITECTURE
BUILD_TECHNOLOGY_BASELINE
PREPARE_SKILLS
BOOTSTRAP_PROJECT
PLAN_WORK
COMPILE_TASK
RUN_TASK
VALIDATE_RESULT
UPDATE_DOCUMENTATION
RESUME_ROUTE
REPORT_STATUS
PUBLISH_CHANGE
APPLY_CHANGE_PACK
```
<!-- /REGISTRY-ENUM -->

Нельзя помещать `COMPILE_TASK`, `VALIDATE_RESULT` или `RESUME_ROUTE` в один enum с `IMPLEMENT` и `FIX`: это разные уровни модели.

### 3. Request Contract

```yaml
request:
  id: RQ-20260806-0001
  schema_version: 1
  project_ref: project-example | null
  session_ref: SES-20260806-0001

  input:
    raw_text: "Добавь поиск по названию и обнови документацию API"
    attachments: []
    source_refs: []
    actor_ref: ACT-USER-001
    received_at: 2026-08-06T09:00:00Z

  classification:
    request_class: DEVELOPMENT_REQUEST
    mode: EXECUTE
    confidence: 0.96
    candidate_classes: []
    material_ambiguity_refs: []
    rationale_summary: "Запрошено изменение продукта и документации"

  scope_hint:
    repository_refs: [REP-APP-001]
    paths: []
    work_package_ref: null
    task_ref: null
    blocker_ref: null

  user_expectation:
    expected_outcome: "Поиск реализован и описан"
    requested_deadline: null
    requested_output_format: RESULT_ENVELOPE

  safety:
    requested_side_effects: [FILESYSTEM_WRITE, COMMAND_EXECUTE]
    prohibited_side_effects: []

  status: CLASSIFIED
  correlation_id: COR-20260806-0001
  idempotency_key: sha256:client-scope-and-normalized-request
```

#### 3.1. Обязательные поля

- `raw_text` сохраняется неизменяемо как исходный source.
- `request_class`, `mode` и `correlation_id` обязательны до построения Request Plan.
- `idempotency_key` обязателен для повторяемых transport calls. Если adapter получает его в header/metadata, он сохраняет то же значение в Request record до planning.
- `project_ref` может отсутствовать только для общего вопроса или до выбора/создания Project Instance.
- Любая классификационная неопределённость фиксируется, а не скрывается.
- Полный chain-of-thought модели не сохраняется. Допускается только краткое проверяемое `rationale_summary`.

### 4. Request lifecycle

```text
RECEIVED
→ CLASSIFYING
→ CLASSIFIED
→ PLANNING
→ PLANNED
→ READY
→ EXECUTING
→ COMPLETED
```

Дополнительные состояния:

```text
WAITING_USER_INPUT
WAITING_APPROVAL
PARTIAL
BLOCKED
FAILED_RECOVERABLE
CANCELLED
SUPERSEDED
```

#### 4.1. Правила переходов

1. `RECEIVED → CLASSIFYING` происходит без side effects.
2. `CLASSIFIED → PLANNING` допускается только после выбора Project Instance или Intake Session.
3. `PLANNED → READY` требует пройденных route gates.
4. `READY → EXECUTING` требует capability grants и current revision check.
5. `WAITING_*` не теряет уже подготовленный plan и имеет `resume_condition`.
6. Любой терминальный статус создаёт Result Envelope.
7. Повторная отправка одного и того же `idempotency_key` не создаёт дубликаты Work Package или side effects.

### 5. Классификация обычного сообщения

#### 5.1. Правило по умолчанию

Сообщение не является задачей разработки только потому, что в нём упомянут код. Создание task допускается, когда запрос содержит ожидаемое изменение или явное планирование изменения.

Примеры:

| Сообщение | Класс | Поведение |
|---|---|---|
| «Почему используется PostgreSQL?» | `QUERY` | Ответить из accepted ADR/Technology Baseline. Task не создавать. |
| «Какая следующая задача?» | `CONTROL_REQUEST` | Вернуть deterministic next route. |
| «Добавь endpoint поиска» | `DEVELOPMENT_REQUEST` | Создать Request Plan и Work Package. |
| «Давай заменим PostgreSQL на SQLite» | `PROJECT_EVOLUTION` | Создать material Change Pack, не менять stack напрямую. |
| «Обнови маршрутизатор Harness для этого проекта» | `PROJECT_CONTROL_MAINTENANCE` | Изолированный control-plane route. |
| «Измени универсальную схему Request» | `HARNESS_DISTRIBUTION_MAINTENANCE` | Distribution maintenance route. |

#### 5.2. Алгоритм классификации

```text
1. Normalize input without changing meaning.
2. Detect explicit control commands and referenced IDs.
3. Detect project selection or need for Intake Session.
4. Generate candidate Request Classes.
5. Apply deterministic rules and project policies.
6. Use inference worker only for semantic ambiguity.
7. Evaluate materiality of remaining ambiguity.
8. If material: ask one bounded clarification batch.
9. Otherwise choose reversible default and record assumption if policy permits.
10. Persist classification event.
```

Классификатор не имеет права запускать tool writes.

### 6. Request Plan Contract

`Request Plan` связывает пользовательский запрос с конкретным набором маршрутов. Он не заменяет Work Package и не является prompt.

```yaml
request_plan:
  id: RQP-20260806-0001
  request_ref: RQ-20260806-0001
  project_ref: project-example
  base_project_revision: sha256:...
  plan_revision: 1

  objective: "Добавить поиск по названию и синхронизировать API-документацию"
  request_class: DEVELOPMENT_REQUEST
  mode: EXECUTE

  routes:
    - id: RTE-001
      sequence: 10
      operation: PLAN_WORK
      output_ref_type: WORK_PACKAGE
      depends_on: []
      gate_refs: [GATE-PROJECT-READY]

    - id: RTE-002
      sequence: 20
      operation: RUN_TASK
      output_ref_type: TASK_REPORT
      depends_on: [RTE-001]
      gate_refs: [GATE-TASK-READY, GATE-CAPABILITY]

    - id: RTE-003
      sequence: 30
      operation: UPDATE_DOCUMENTATION
      output_ref_type: DOCUMENTATION_CHANGE
      depends_on: [RTE-002]
      gate_refs: []

  work_package_refs: []
  decision_refs: []
  assumptions: []
  prohibited_operations: [PUBLISH_CHANGE]

  expected_result:
    public_statuses: [COMPLETED, PARTIAL, BLOCKED, FAILED_RECOVERABLE]
    result_schema_ref: SCHEMA-RESULT-ENVELOPE@1

  next_route_policy: EXACTLY_ONE_RECOMMENDED
  status: PLANNED
  created_at: 2026-08-06T09:00:02Z
```

#### 6.1. Инварианты Request Plan

- Каждая route имеет одну операцию и один проверяемый output type.
- Зависимости routes образуют DAG.
- Side-effect route не может предшествовать планированию и readiness gates.
- `QUERY` обычно содержит одну route `ANSWER`.
- `PROJECT_START` обязательно содержит `START_INTAKE` и `ASK_QUESTION_BATCH`.
- Request Plan не создаёт заранее prompts для всех будущих tasks.
- Смена base project revision делает plan `STALE`, если затронуты его входы.

### 7. Единая точка входа как API

Минимальный logical interface:

```text
handle(input, actor, optional_project_ref, requested_mode)
  → ResultEnvelope
```

Внутренние операции:

```text
create_request()
classify_request()
resolve_project_context()
build_request_plan()
execute_current_route()
render_result_envelope()
```

CLI, web UI, chat UI и API являются adapters этого интерфейса. Команды допускаются как shortcuts, но не являются обязательным UX.

### 8. Ошибки и остановки

| Ситуация | Поведение |
|---|---|
| Не выбран project, но запрос явно относится к одному из нескольких | `WAITING_USER_INPUT`, показать короткий список проектов. |
| Запрос смешивает product change и Harness maintenance | Разделить на два Request Plan либо остановить и предложить выбор порядка. |
| Пользователь просит execute, но project не прошёл readiness | Перевести в intake/planning route, не выполнять write. |
| Запрос требует необратимого side effect | Добавить approval route. |
| Classification confidence низкая, но ambiguity нематериальна | Применить policy default и показать assumption. |
| Classification ambiguity меняет scope/архитектуру | Остановить affected route и задать уточнение. |

### 9. Пользовательское представление

Пользователь видит не внутренний список операций, а:

```text
Распознано: задача разработки
Режим: выполнение
План: 3 атомарные задачи, одна из них готова сейчас
Требуется решение: нет
Текущий шаг: реализация backend-поиска
```

Внутренние IDs показываются компактно и только когда полезны для traceability.

### 10. Критерии приёмки

1. Один natural-language endpoint обрабатывает все Request Classes.
2. Обычный вопрос не создаёт Work Package и Task.
3. Development request создаёт Request, Request Plan и correlation trace.
4. Mixed-plane request не выполняется одной неявной transaction.
5. Side effects не начинаются до режима `EXECUTE`, gates и grants.
6. Любой terminal или waiting state возвращает Result Envelope.
7. Повтор запроса с тем же idempotency key не дублирует изменение.
8. Classification и planning покрыты deterministic и behavioral fixtures.

### 11. Минимальные тестовые сценарии

```text
RQ-QUERY-001        ordinary question → ANSWERED, no task
RQ-START-001        new project → intake session and first question batch
RQ-BROWNFIELD-001   repository supplied → brownfield inspection route
RQ-DEV-001          feature request → work package draft
RQ-EVOLUTION-001    stack change → Change Pack, no direct write
RQ-MIXED-001        product + harness maintenance → split or decision
RQ-RESUME-001       blocker reference → resume route
RQ-IDEMPOTENT-001   duplicate request key → same request/result
```

---

<!-- SOURCE: 12_Implementation_Specifications/02_Result_Envelope_and_Statuses.md -->

## Result Envelope и пользовательские статусы

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Каждый запрос к Harness завершается единым `Result Envelope`. Пользователь не должен угадывать, закончена ли задача, что изменилось, почему произошла остановка и что делать дальше.

Result Envelope используется для:

- обычного ответа;
- завершённой задачи;
- частично выполненного Work Package;
- material question;
- blocker;
- recoverable failure;
- статуса или control request;
- project intake;
- Harness maintenance.

Внутренние Task Report, Run Trace и Evidence остаются подробными инженерными артефактами. Result Envelope является стабильным пользовательским контрактом поверх них.

### 2. Публичные статусы

```text
ANSWERED
COMPLETED
PARTIAL
WAITING_DECISION
BLOCKED
FAILED_RECOVERABLE
NO_ACTION
CANCELLED
```

| Статус | Значение |
|---|---|
| `ANSWERED` | Read-only вопрос получил ответ; изменений нет. |
| `COMPLETED` | Запрошенный текущий scope полностью выполнен и проверен. |
| `PARTIAL` | Безопасная часть выполнена, но весь scope ещё не закрыт. |
| `WAITING_DECISION` | Нужен материальный ответ или approval пользователя. |
| `BLOCKED` | Продолжение текущего route невозможно до выполнения resume condition. |
| `FAILED_RECOVERABLE` | Попытка завершилась ошибкой, но известен безопасный route восстановления. |
| `NO_ACTION` | Запрос корректно обработан, но изменение не требовалось или уже присутствует. |
| `CANCELLED` | Пользователь или policy отменили дальнейшее выполнение. |

Публичный статус `FAILED_FINAL` не используется как тупиковое состояние. Невозможность исходного подхода должна возвращать `BLOCKED`, `FAILED_RECOVERABLE` или `CANCELLED` с альтернативным route.

### 3. Result Envelope Contract

```yaml
result:
  id: RES-20260806-0001
  schema_version: 1
  request_ref: RQ-20260806-0001
  correlation_id: COR-20260806-0001
  project_ref: project-example
  work_package_ref: WP-SEARCH-001
  task_ref: TSK-BE-SEARCH-010
  run_ref: RUN-20260806-0007

  status: COMPLETED
  title: "Поиск по названию реализован"
  summary: "Добавлен backend endpoint, обновлена API-документация и пройдены целевые проверки."

  progress:
    completed_units: 2
    total_units: 2
    percent: 100
    current_unit: null

  changes:
    added:
      - path: src/search/service.ts
        description: "Сервис поиска"
    changed:
      - path: docs/api/search.md
        description: "Контракт endpoint"
    removed: []
    unchanged: []

  verification:
    status: PASS
    checks:
      - name: targeted-tests
        result: PASS
        evidence_ref: EVD-TEST-001
    known_unrelated_failures: []

  documentation:
    status: UPDATED
    updated_refs: [DOC-API-SEARCH@3]
    created_refs: []
    superseded_refs: []
    not_applicable_reason: null

  decisions:
    created_refs: []
    reused_refs: [ADR-API-004]
    assumptions: []

  blockers: []
  recovery_options: []
  warnings: []

  next_step:
    route: RUN_NEXT_READY_TASK
    label: "Перейти к frontend-интеграции"
    task_ref: TSK-FE-SEARCH-020
    requires_user_action: false

  detail_refs:
    task_report_ref: TRP-TSK-BE-SEARCH-010-001
    request_trace_ref: TRT-COR-20260806-0001

  completed_at: 2026-08-06T09:15:00Z
```

### 4. Обязательные блоки по статусам

#### 4.1. `ANSWERED`

Обязательны:

- `summary` с самим ответом;
- `changes` пустой;
- `verification` может иметь `NOT_APPLICABLE`;
- source/document refs, если ответ основан на project state;
- `next_step` только если естественно следует из вопроса.

#### 4.2. `COMPLETED`

Обязательны:

- понятное описание результата;
- `added`, `changed`, `removed`;
- verification status и evidence;
- documentation status;
- точный следующий route либо `NONE`.

#### 4.3. `PARTIAL`

Обязательны:

- что уже завершено;
- что осталось;
- почему весь scope не завершён;
- сохранён ли safe state;
- следующий route;
- tasks, которые можно продолжать независимо.

#### 4.4. `WAITING_DECISION`

Обязательны:

- один material question или компактная согласованная группа;
- объяснение влияния ответа;
- 2–4 понятных варианта;
- рекомендуемый вариант и его последствия;
- возможность ответа «не знаю»;
- exact resume condition.

#### 4.5. `BLOCKED`

Обязательны:

- `stopped_at`;
- причина и evidence;
- затронутый scope;
- безопасно выполненная часть;
- recovery options;
- recommendation;
- independent ready tasks;
- resume condition.

#### 4.6. `FAILED_RECOVERABLE`

Обязательны:

- классифицированная ошибка;
- номер попытки;
- были ли side effects;
- выполнена ли компенсация;
- допустим ли retry;
- альтернативный route, если retry нецелесообразен.

### 5. Mapping внутренних статусов

| Internal state | Public status |
|---|---|
| Request `COMPLETED` + read-only | `ANSWERED` |
| Task `DONE`, verification `PASS` | `COMPLETED` |
| Work Package с частью `DONE`, частью `READY/BLOCKED` | `PARTIAL` |
| Request `WAITING_USER_INPUT` или `WAITING_APPROVAL` | `WAITING_DECISION` |
| Task `BLOCKED_*` | `BLOCKED` |
| Run `FAILED_RETRYABLE` | `FAILED_RECOVERABLE` |
| План не требует изменения | `NO_ACTION` |
| Request/Task `CANCELLED` | `CANCELLED` |

Mapping должен быть детерминированным и находиться в kernel, а не в свободном тексте agent response.

### 6. Правила формулировки

Result renderer обязан отвечать на пять вопросов:

```text
Что произошло?
Что конкретно изменилось?
Как это проверено?
Есть ли препятствия или риски?
Какой следующий шаг?
```

Запрещено:

- возвращать только «готово»;
- скрывать удалённые файлы или изменения публичного контракта;
- смешивать warning и blocker;
- объявлять `COMPLETED`, если обязательная verification не пройдена;
- объявлять `BLOCKED` без recovery option;
- использовать внутренние stack traces как основной пользовательский текст.

### 7. Агрегация Work Package

```text
All mandatory tasks DONE and acceptance PASS → COMPLETED
Some mandatory tasks DONE, remainder READY/BLOCKED → PARTIAL
No task executed, material decision required → WAITING_DECISION
No task executed, technical prerequisite absent → BLOCKED
All requested behavior already exists and verified → NO_ACTION
```

Optional task не препятствует `COMPLETED`, если aggregation rule явно помечает его optional.

### 8. Пример незавершённого результата

```yaml
status: BLOCKED
summary: "Backend-часть подготовлена, но интеграция не может начаться без принятого API-контракта."
progress:
  completed_units: 1
  total_units: 3
changes:
  added:
    - path: src/search/query.ts
verification:
  status: PARTIAL_PASS
documentation:
  status: PENDING
blockers:
  - ref: BLK-API-CONTRACT-001
    reason: "Не определён формат пагинации"
recovery_options:
  - id: OPT-CURSOR
    label: "Cursor pagination"
    consequences: "Стабильно для больших наборов, сложнее клиент"
  - id: OPT-OFFSET
    label: "Offset pagination"
    consequences: "Проще, но менее устойчиво при изменении данных"
recommendation: OPT-CURSOR
next_step:
  route: ANSWER_MATERIAL_QUESTION
  requires_user_action: true
```

### 9. Версионирование и совместимость

- Result Envelope имеет независимый `schema_version`.
- Добавление optional поля является backward-compatible.
- Переименование статуса или изменение его смысла требует migration.
- Agent adapter может возвращать provider-specific payload, но kernel обязан нормализовать его в Result Envelope.
- Renderer для CLI, chat и API не меняет смысл полей.

### 10. Критерии приёмки

1. Каждый route возвращает schema-valid Result Envelope.
2. `COMPLETED` невозможен без удовлетворения mandatory acceptance criteria.
3. `BLOCKED` невозможен без recovery options и resume condition.
4. `WAITING_DECISION` содержит варианты и понятное объяснение.
5. Changes перечисляют добавленное, изменённое и удалённое.
6. Documentation status присутствует даже при `NOT_APPLICABLE`.
7. Work Package aggregation детерминирован и покрыт fixtures.
8. Пользовательский текст остаётся понятным без чтения внутренних reports.

### 14. v0.4.1 lifecycle clarification

Public `Result.status = COMPLETED` не является универсальным internal lifecycle status. Успешные Task и Run обязаны использовать соответственно `DONE` и `SUCCEEDED`; Work Package, Task Report, Agent Task Result и public Result сохраняют `COMPLETED`. Validator применяет status group из `registries/statuses.yaml` по contract type.

---

<!-- SOURCE: 12_Implementation_Specifications/03_Work_Packages_Tasks_and_Subtasks.md -->

## Work Packages, задачи и подзадачи

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

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

### 2. Основные сущности

#### 2.1. Work Package

Содержит:

- исходный пользовательский outcome;
- scope и границы;
- список mandatory и optional tasks;
- dependency graph;
- aggregation rule;
- overall acceptance;
- progress и next route.

#### 2.2. Atomic Task

Atomic task имеет:

- один основной проверяемый результат;
- ограниченный write scope;
- известные входные артефакты;
- одну primary skill route;
- пропорциональный verification profile;
- понятный rollback;
- следующий кандидат, но не сам выбирает его.

#### 2.3. Task Group

`Task Group` — необязательное представление для UI или больших work packages. Он не является отдельной исполняемой сущностью и не добавляет обязательный prompt.

### 3. Work Package Contract

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

### 4. Расширенный Task Contract

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

### 5. Когда задача считается слишком большой

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

### 6. Когда не нужно дробить задачу

Не следует создавать отдельную task для каждого файла, функции или команды. Сохранять одну task допустимо, если:

- изменения служат одному результату;
- имеют один bounded scope;
- проверяются одним набором checks;
- выполняются одной skill route;
- не создают независимого integration gate;
- промежуточное состояние не имеет самостоятельной ценности.

Цель — минимальное достаточное число tasks, а не максимальная детализация.

### 7. Алгоритм декомпозиции

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

### 8. Parent/child semantics

По умолчанию иерархия реализуется через Work Package. `parent_task_ref` применяется только при runtime split уже существующей task:

```text
TSK-ORIGINAL status → SPLIT
TSK-CHILD-A and TSK-CHILD-B created
original acceptance → aggregation rule over children
original task is never executed again
```

История исходной task сохраняется. Нельзя тихо заменить её двумя tasks без event и source map.

### 9. Artifact-first dependencies

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

### 10. Lifecycle

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

### 11. Aggregation и следующий шаг

Deterministic next task выбирается kernel по:

1. dependency readiness;
2. artifact availability;
3. priority;
4. risk reduction;
5. critical path;
6. stable tie-breaker by task ID.

Agent не выбирает следующую задачу самостоятельно. Он может вернуть candidates, но Result Envelope использует решение planner/kernel.

### 12. Пример декомпозиции большой задачи

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

### 13. Критерии приёмки

1. Большой request создаёт один Work Package и минимальный набор atomic tasks.
2. Каждая task имеет один expected result, primary skill и verification profile.
3. Все required artifacts имеют producer или являются accepted external inputs.
4. DAG не содержит циклов и future-only dependencies.
5. Runtime split сохраняет lineage и не теряет acceptance criteria.
6. Work Package status агрегируется детерминированно.
7. Agent получает только одну task или утверждённый safe parallel batch.
8. UI может показать пользователю цель, прогресс, блокировку и следующий шаг без чтения prompt bundles.

---

<!-- SOURCE: 12_Implementation_Specifications/04_JIT_Prompt_Compilation.md -->

## JIT-компиляция task-specific prompts

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Harness не должен хранить огромное количество заранее скомпилированных промтов. Canonical backlog состоит из Work Packages и Task Contracts. Prompt bundle создаётся непосредственно перед исполнением только для READY task или утверждённого safe parallel batch.

Принцип:

```text
Store tasks, policies and reusable prompt modules.
Compile execution prompt just in time.
Retain immutable bundle only for an actual run.
```

### 2. Уровни Prompt IR

```text
Prompt Module
→ Prompt Spec
→ Prompt Plan
→ Compiled Prompt Bundle
→ Adapter-rendered Request
→ Run
```

| Уровень | Назначение | Canonical/Generated |
|---|---|---|
| Prompt Module | Переиспользуемая инструкция или policy fragment. | Canonical. |
| Prompt Spec | Логический шаблон класса задач. | Canonical. |
| Prompt Plan | Разрешённый состав конкретной task. | Generated, reproducible. |
| Compiled Bundle | Точная ordered payload для run. | Generated, immutable for run. |
| Adapter Request | Provider/agent-specific rendering. | Ephemeral или retained in trace. |

### 3. Минимальный набор Prompt Specs

Первый релиз использует ограниченный registry:

```text
PSP-DISCOVER
PSP-DECIDE
PSP-ARCHITECT
PSP-PLAN
PSP-IMPLEMENT
PSP-FIX
PSP-VALIDATE
PSP-DOCUMENT
PSP-UPDATE
PSP-MAINTAIN-HARNESS
```

Новый Prompt Spec создаётся только если существующий класс задач не может выразить иной output contract, permissions model или execution protocol. Для большинства implementation tasks используется один `PSP-IMPLEMENT` с разными Task Contracts и Context Plans.

### 4. Условия компиляции

Компиляция разрешена только когда:

- task status `READY` или `CLAIMED`;
- все required artifacts доступны и имеют принятые revisions;
- Task Contract schema-valid;
- effective constraints вычислены;
- primary skill `ACTIVE` и совместим;
- agent/model/tool compatibility `PASS`;
- context plan может быть materialized без silent truncation;
- required capabilities могут быть выданы;
- task base revision не stale.

Если хотя бы одно условие не выполнено, compiler возвращает structured blocker, а не частичный prompt.

### 5. Prompt Plan Contract

```yaml
prompt_plan:
  id: PPL-TSK-BE-AUTH-020-R1
  schema_version: 1
  task_ref: TSK-BE-AUTH-020@1
  request_ref: RQ-20260806-0002
  work_package_ref: WP-AUTH-001@1

  prompt_spec_ref: PSP-IMPLEMENT@1
  module_refs:
    - PMD-CORE-ROLE@3
    - PMD-TASK-CONTRACT@2
    - PMD-DOCUMENTATION-DUTY@1
    - PMD-BLOCKER-PROTOCOL@2
    - PMD-RESULT-SCHEMA@1

  resolved_inputs:
    task_hash: sha256:...
    constraints_hash: sha256:...
    architecture_hash: sha256:...
    skill_hash: sha256:...
    context_plan_hash: sha256:...
    capability_plan_hash: sha256:...

  instruction_order:
    - GOVERNANCE
    - TASK_PURPOSE
    - INPUT_ARTIFACTS
    - BOUNDED_SCOPE
    - EXECUTION_STEPS
    - VERIFICATION
    - DOCUMENTATION
    - STOP_CONDITIONS
    - OUTPUT_CONTRACT
    - NEXT_ROUTE_HINT

  output_schema_ref: SCHEMA-AGENT-TASK-RESULT@1
  status: RESOLVED
```

### 6. Compiled Prompt Bundle

```yaml
compiled_prompt_bundle:
  id: CPB-RUN-20260806-0007
  prompt_plan_ref: PPL-TSK-BE-AUTH-020-R1
  task_ref: TSK-BE-AUTH-020@1
  run_ref: RUN-20260806-0007
  adapter_profile_ref: ADP-CODEX@1

  messages: []
  tool_schemas: []
  output_schema_ref: SCHEMA-AGENT-TASK-RESULT@1
  context_packet_refs: [CPK-TSK-BE-AUTH-020-R1]
  capability_grant_refs: [CGR-RUN-0007]
  source_map_ref: SMP-CPB-0007

  compilation_hash: sha256:...
  compiled_at: 2026-08-06T09:10:00Z
  status: COMPILED
```

Bundle становится immutable после привязки к run.

### 7. Обязательное содержание task prompt

Codex или другой agent должен видеть:

1. **Что сделать** — один expected result.
2. **Зачем** — связь с Work Package outcome и requirements.
3. **На что опираться** — accepted artifacts и documentation refs.
4. **Что уже существует** — relevant current implementation.
5. **Что разрешено менять** — read/write/forbidden scopes.
6. **Какие skills и capabilities использовать**.
7. **Как проверить** — exact verification profile and commands.
8. **Когда остановиться** — material ambiguity, constraint violation, scope expansion.
9. **Что вернуть** — structured agent result schema.
10. **Что следует дальше** — только hint; окончательный next route выбирает kernel.

Полная документация проекта не вставляется автоматически. Context Plan выбирает только необходимый контекст.

### 8. Lifecycle prompt artifacts

Prompt Module / Prompt Spec:

```text
DRAFT → VALIDATED → ACTIVE → DEPRECATED → RETIRED
```

Prompt Plan:

```text
PLANNED → RESOLVED → STALE | CONSUMED
```

Compiled Bundle:

```text
COMPILED → DISPATCHED → EXECUTED
         ↘ EXPIRED
         ↘ CANCELLED
```

`COMPILED` является статусом bundle, а не Prompt Module или Prompt Spec.

### 9. Invalidation

Prompt Plan или bundle становится `STALE/EXPIRED`, если изменился любой material input:

- Task Contract revision;
- requirement/constraint/ADR revision;
- accepted contract artifact;
- Prompt Spec или Module;
- Skill revision;
- Context Policy/Plan;
- Agent/Model/Tool profile;
- capability grants;
- repository base revision;
- verification profile.

Старый bundle сохраняется в Run Trace, но не может быть повторно dispatch без нового compatibility check.

### 10. Retention policy

Хранятся обязательно:

- active Prompt Modules and Specs;
- Prompt Plan для active/queued run;
- bundle каждого реально выполненного run;
- source map и hashes;
- evaluation evidence.

Не требуется хранить:

- заранее compiled bundles для будущих tasks;
- промежуточные неисполненные renderings;
- полные дубликаты неизменившихся context sources.

### 11. Алгоритм compiler

```text
compile(task_ref, execution_profile):
  task = load_current_task(task_ref)
  assert task.status in {READY, CLAIMED}
  assert_artifacts_ready(task.requires_artifacts)
  effective_constraints = resolve_constraints(task)
  skill = resolve_active_skill(task.route)
  compatibility = resolve_compatibility(task, skill, execution_profile)
  context_plan = build_context_plan(task)
  assert_no_silent_overflow(context_plan)
  capability_plan = resolve_capabilities(task)
  prompt_plan = compose_prompt_plan(...)
  validate_prompt_plan(prompt_plan)
  bundle = render_deterministically(prompt_plan, execution_profile)
  persist_hashes_and_source_map(bundle)
  return bundle
```

Одинаковые canonical inputs и compiler version должны давать одинаковый logical bundle. Provider metadata, timestamps и nonce исключаются из compilation hash.

### 12. Ошибки компиляции

```text
TASK_NOT_READY
MISSING_ARTIFACT
STALE_INPUT
PROMPT_SPEC_INACTIVE
SKILL_NOT_READY
CONSTRAINT_CONFLICT
CONTEXT_OVERFLOW
CAPABILITY_UNAVAILABLE
ADAPTER_INCOMPATIBLE
OUTPUT_SCHEMA_UNSUPPORTED
```

Каждая ошибка преобразуется в Blocker Contract с recovery options.

### 13. Критерии приёмки

1. Неисполненные future tasks не имеют обязательных compiled bundles.
2. READY task компилируется reproducibly из canonical inputs.
3. Любое material изменение инвалидирует plan/bundle.
4. Один base Prompt Spec обслуживает множество tasks без копирования.
5. Bundle содержит task purpose, result, verification, documentation duty и stop protocol.
6. Silent context truncation невозможен.
7. Compiled bundle привязан к одному run и не переписывается.
8. Compiler errors являются structured blockers, а не свободным текстом.

---

<!-- SOURCE: 12_Implementation_Specifications/05_Documentation_Traceability.md -->

## Трассировка задач и изменений к документации

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Каждая задача должна явно знать:

- к какому пользовательскому outcome относится;
- какие requirements, constraints и decisions реализует;
- какие документы и разделы являются её входом;
- какую документацию она обязана изменить;
- почему документация не меняется, если это действительно не требуется.

Документация является частью результата разработки, но не каждая мелкая операция требует нового документа или ADR.

### 2. Двойная ссылка

Каждая значимая ссылка включает:

1. устойчивую canonical entity;
2. человекочитаемое расположение документа.

```yaml
documentation_ref:
  entity_ref: REQ-AUTH-001
  document: docs/requirements/authentication.md
  section_id: auth-login
  heading_hint: "Вход пользователя"
  revision: 4
  content_hash: sha256:...
  relation: SOURCE
```

`heading_hint` предназначен только для отображения. Стабильным идентификатором является `section_id` или explicit anchor.

### 3. Documentation Impact

```text
NONE
UPDATE_EXISTING
CREATE_NEW
SUPERSEDE
GENERATED_ONLY
```

| Значение | Когда использовать |
|---|---|
| `NONE` | Поведение, интерфейсы и принятые решения не изменяются. Требуется rationale. |
| `UPDATE_EXISTING` | Меняется существующее документированное поведение. |
| `CREATE_NEW` | Возникает новый публичный контракт, workflow или material concept. |
| `SUPERSEDE` | Старый документ/раздел становится историческим и заменяется новым. |
| `GENERATED_ONLY` | Изменяется только generated view, исходные canonical entities уже обновлены. |

### 4. Поля Task Contract

```yaml
documentation:
  source_refs:
    - entity_ref: REQ-SEARCH-001
      document: docs/requirements/search.md
      section_id: search-by-name
      revision: 2
      content_hash: sha256:...

  decision_refs:
    - entity_ref: ADR-API-004
      document: docs/architecture/adr/004-search-api.md
      section_id: decision
      revision: 1

  impact: UPDATE_EXISTING
  required_updates:
    - document: docs/api/search.md
      section_id: endpoint-search
      reason: "Добавляется параметр query"
      owner: TSK-BE-SEARCH-030

  generated_views:
    - STATUS.md
    - .harness/generated/requirements-coverage.md

  not_applicable_reason: null
```

### 5. Documentation gate

Task не может перейти в `DONE`, пока не выполнено одно из условий:

- required documentation updates applied and validated;
- documentation impact `NONE` с непустым rationale;
- documentation work вынесена в зависимую task, которая является mandatory частью того же Work Package;
- documentation intentionally deferred через approved decision/waiver.

Нельзя помечать `NONE` автоматически только потому, что agent не изменил Markdown.

### 6. Source precedence

Для реализации используется порядок:

```text
Accepted canonical entity
→ accepted ADR/Decision
→ accepted human-readable document section
→ generated view
→ current implementation evidence
→ untrusted source
```

Если код расходится с accepted requirement, это не означает автоматическое изменение requirement. Brownfield reconciliation определяет, является ли код фактическим baseline или дефектом.

### 7. Update workflow

```text
1. Resolve task documentation source refs.
2. Verify document revision/hash.
3. Detect documentation impact before execution.
4. Add documentation changes to write scope.
5. Execute product change.
6. Update canonical entities first when semantics changed.
7. Update human-readable documents.
8. Regenerate derived views.
9. Validate links, anchors, examples and contract consistency.
10. Record changed/superseded refs in Task Report and Result Envelope.
```

### 8. Stable section identifiers

Рекомендуемый Markdown-формат:

```markdown
<a id="auth-login"></a>
## Вход пользователя
```

или front matter registry:

```yaml
sections:
  auth-login:
    heading: "Вход пользователя"
```

Validation tool должен обнаруживать:

- missing anchor;
- duplicate section ID;
- stale revision/hash;
- ссылка на superseded document;
- required update без task owner;
- changed public interface без documentation impact.

### 9. Документация разных типов задач

| Task type | Ожидаемый documentation impact |
|---|---|
| Новая публичная API-функция | `UPDATE_EXISTING` или `CREATE_NEW` |
| Внутренний refactoring без изменения поведения | Обычно `NONE` с rationale |
| Architecture decision | `CREATE_NEW` ADR и обновление architecture baseline |
| Bug fix, возвращающий documented behavior | Обычно `NONE` или update known-issues/changelog |
| Изменение documented behavior | `UPDATE_EXISTING` + requirement/decision change |
| Directory/bootstrap | `GENERATED_ONLY` или update project layout docs |
| Test-only task | `NONE`, если behavior не меняется |
| Skill/prompt maintenance | Update control-plane documentation and registry |

### 10. Task Report fragment

```yaml
documentation_result:
  status: UPDATED
  source_refs_verified: true
  updated:
    - entity_ref: DOC-API-SEARCH
      previous_revision: 2
      resulting_revision: 3
      path: docs/api/search.md
      sections: [endpoint-search]
  created: []
  superseded: []
  generated_views_refreshed:
    - .harness/generated/requirements-coverage.md
  validation_evidence_refs:
    - EVD-DOC-LINKS-001
    - EVD-DOC-CONTRACT-002
```

### 11. Documentation ownership при параллельной работе

Разделы документации имеют read/write sets, как код и contracts.

```yaml
documentation_access:
  read:
    - docs/api/search.md#endpoint-search
  write:
    - docs/implementation/backend-search.md
```

Две parallel tasks могут читать один раздел. Одновременная запись в один section ID запрещена без explicit merge owner.

### 12. Критерии приёмки

1. Каждая executable task имеет `documentation` block.
2. Source refs включают canonical entity и document section.
3. Public behavior change не может завершиться с impact `NONE`.
4. Documentation gate входит в Task completion.
5. Broken/stale anchors выявляются автоматически.
6. Result Envelope показывает, что обновлено, создано или superseded.
7. Parallel planner учитывает documentation write conflicts.
8. Generated views не становятся canonical source of truth.

---

<!-- SOURCE: 12_Implementation_Specifications/06_ADR_and_Decision_Policy.md -->

## Политика ADR и material decisions

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Harness обязан фиксировать важные инженерные решения, но не должен превращать ADR-каталог в журнал каждой выполненной задачи. Разные типы информации сохраняются в разных артефактах:

| Вопрос | Артефакт |
|---|---|
| Какое долговременное решение принято и почему? | ADR / Decision Record |
| Что требуется сделать? | Work Package / Task Contract |
| Что исполнялось? | Run Trace |
| Что изменено и как проверено? | Task Report / Evidence |
| Как изменилось состояние? | State Event |
| Что выполнять дальше? | DAG / Result Envelope |

### 2. Material decision

Решение является material, если оно способно заметно изменить хотя бы одно из следующего:

- границы системы или компонентов;
- публичный API, event, data или integration contract;
- модель данных и миграционный путь;
- security/trust boundary;
- обработку чувствительных данных;
- deployment topology;
- поддерживаемые платформы;
- ключевой язык, runtime, framework, database или инфраструктурный provider;
- consistency, availability, performance или scalability strategy;
- необратимость, rollback или migration risk;
- universal/project-local routing, prompt, skill или permission semantics;
- обязательный quality gate.

### 3. Когда ADR обязателен

ADR создаётся или обновляется для:

```text
SYSTEM_BOUNDARY
ARCHITECTURE_STYLE
TECHNOLOGY_SELECTION
PUBLIC_CONTRACT
DATA_MODEL
SECURITY_BOUNDARY
DEPLOYMENT_TOPOLOGY
MATERIAL_MIGRATION
CROSS_REPOSITORY_OWNERSHIP
HARNESS_ROUTING_SEMANTICS
HARNESS_PROMPT_OR_SKILL_SEMANTICS
MATERIAL_POLICY_OR_WAIVER
```

Примеры:

- выбор PostgreSQL вместо SQLite;
- переход от monolith к нескольким services;
- принятие cursor pagination как публичного API contract;
- выбор session storage model;
- изменение стратегии multi-tenant isolation;
- изменение правила parallel execution или capability enforcement.

### 4. Когда ADR не нужен

ADR обычно не создаётся для:

- обычной реализации endpoint по принятому contract;
- исправления дефекта без изменения expected behavior;
- локального refactoring;
- переименования символа;
- обновления документации;
- добавления или корректировки теста;
- создания каталога;
- изменения generated view;
- повторного использования уже принятого ADR;
- operational retry или blocker recovery, не меняющего baseline.

Такие действия фиксируются Task Contract, Task Report, Evidence и State Event.

### 5. Decision classification

```text
MATERIAL_ARCHITECTURE
MATERIAL_PRODUCT
MATERIAL_SECURITY
MATERIAL_TECHNOLOGY
MATERIAL_HARNESS
OPERATIONAL_APPROVAL
TASK_LOCAL_CHOICE
ASSUMPTION
```

- Первые пять типов требуют ADR или formal Decision Record.
- `OPERATIONAL_APPROVAL` фиксирует разрешение на конкретный side effect и не становится ADR.
- `TASK_LOCAL_CHOICE` может быть записан в Task Report, если обратим и не влияет на другие tasks.
- `ASSUMPTION` управляется Assumption Contract и review trigger.

### 6. Алгоритм определения необходимости ADR

```text
1. Does the choice alter accepted requirement, constraint or public contract?
2. Does it affect more than one task, component, repository or release?
3. Is the choice expensive or risky to reverse?
4. Does it create a new long-lived dependency or technology?
5. Does it alter security, data, deployment or operational boundaries?
6. Will a future contributor reasonably ask "why was this chosen"?

If any material rule is true → ADR candidate.
Otherwise → task-local record.
```

Inference worker может предложить classification, но Decision Policy evaluator принимает итог по формальным правилам.

### 7. ADR Contract

```yaml
adr:
  id: ADR-AUTH-003
  revision: 1
  title: "Хранение пользовательских сессий"
  decision_type: MATERIAL_ARCHITECTURE
  status: ACCEPTED

  context:
    problem: "Нужно обеспечить отзыв и горизонтальное масштабирование сессий"
    driver_refs: [REQ-AUTH-001, QUA-AVAIL-002]
    constraint_refs: [CST-SEC-001, CST-DATA-003]
    source_refs: [DOC-ARCH-AUTH@2]

  options:
    - id: OPT-JWT
      summary: "Stateless JWT"
      benefits: []
      costs: []
      risks: []
    - id: OPT-REDIS
      summary: "Server-side sessions in Redis"
      benefits: []
      costs: []
      risks: []

  decision:
    selected_option_ref: OPT-REDIS
    statement: "Использовать server-side sessions in Redis"
    rationale: "Требуется централизованный отзыв сессий"

  consequences:
    positive: []
    negative: []
    obligations:
      - "Добавить health and availability checks"
      - "Определить retention policy"

  affected_refs:
    work_packages: [WP-AUTH-001]
    contracts: [CNT-AUTH@1]
    documentation: [DOC-ARCH-AUTH]

  verification:
    acceptance_refs: [AC-ADR-AUTH-001]
    review_triggers:
      - "Рост требований к offline operation"
      - "Удаление Redis из technology baseline"

  supersedes: []
  superseded_by: null
  approved_by: ACT-ARCH-001
  decided_at: 2026-08-06T10:00:00Z
```

### 8. ADR lifecycle

```text
DRAFT → PROPOSED → ACCEPTED
                    ↘ REJECTED
ACCEPTED → SUPERSEDED
ACCEPTED → DEPRECATED
```

- `DRAFT` не может использоваться как обязательный input реализации.
- `PROPOSED` может блокировать dependent task, если решение material.
- `ACCEPTED` фиксирует baseline.
- Изменение принятого решения создаёт новую revision или superseding ADR; история не переписывается.

### 9. Decision Gate

Material decision route обязан показать пользователю:

- контекст и почему решение требуется сейчас;
- 2–4 реалистичных варианта;
- ограничения, выгоды и риски;
- рекомендуемый вариант;
- последствия откладывания;
- какие tasks будут разблокированы;
- возможность предложить свой вариант;
- возможность ответить «не знаю» и принять reversible default, если это разрешено policy.

После выбора Harness:

1. создаёт Decision/ADR;
2. обновляет Architecture/Technology Baseline;
3. выполняет impact analysis;
4. помечает затронутые tasks/prompts stale;
5. перестраивает readiness;
6. возвращает Result Envelope.

### 10. Связь ADR с задачами

Task Contract содержит:

```yaml
architecture_refs:
  - ADR-AUTH-003@1

decision_requirement:
  creates_new_decision: false
  required_decision_refs: [ADR-AUTH-003@1]
```

Если task обнаруживает необходимость нового material decision, она не должна принимать его скрыто. Task останавливается в `WAITING_DECISION`, а отдельный decision route создаёт ADR. После принятия task пересобирается и компилируется заново.

### 11. ADR и bug fixes

Bug fix не требует ADR, когда он возвращает код к уже принятому behavior. ADR или requirement change нужен, если:

- текущее documented behavior признано неверным;
- исправление меняет публичный contract;
- выбран workaround с долгосрочными последствиями;
- bug выявляет новую architecture/security boundary;
- необходима material migration.

### 12. Проверки

Semantic validator проверяет:

- каждая accepted material decision имеет ADR;
- ADR содержит минимум два варианта либо rationale, почему альтернативы отсутствуют;
- task не ссылается на `DRAFT/REJECTED/SUPERSEDED` ADR как на current baseline;
- supersession chain не содержит циклов;
- public contract change имеет decision/requirement update;
- обычные implementation tasks не создают ADR без materiality rationale.

### 13. Критерии приёмки

1. ADR создаётся только для material decisions.
2. Каждая material decision имеет контекст, варианты, rationale и consequences.
3. Task-local choices не загрязняют ADR registry.
4. Изменение accepted ADR запускает impact/replanning.
5. Agent не принимает material decision самостоятельно.
6. Result Envelope показывает созданные и повторно использованные decisions.
7. Semantic tests обнаруживают missing и избыточные ADR patterns.

---

<!-- SOURCE: 12_Implementation_Specifications/07_Causal_Development_Sequence.md -->

## Причинный порядок разработки и readiness

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

«Строго хронологический порядок» в Harness означает не один длинный список, а причинный порядок: никакая задача не становится READY, если необходимый ей функционал, contract, environment или decision ещё не существует.

Правило:

> Consumer task не может начинаться раньше, чем все её обязательные input artifacts произведены, приняты и совместимы.

### 2. Причинная модель

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

### 3. Типы зависимостей

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

### 4. Readiness Contract

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

### 5. Алгоритм построения DAG

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

### 6. Запрет future-only dependencies

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

### 7. Greenfield causal sequence

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

### 8. Brownfield causal sequence

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

### 9. Вертикальные срезы

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

Названия, dependencies, outputs и acceptance criteria нормативно задаются только в [`../09_Delivery/02_Implementation_Roadmap.md`](09_Delivery/02_Implementation_Roadmap.md). Эта таблица является проверяемым индексом и не определяет отдельную последовательность. `HNS-REQ-*` используется только для документационных требований.

Каждый этап расширяет уже работающую end-to-end цепочку. Интеграция не откладывается до последнего этапа.

### 10. Deterministic next task

Из множества READY tasks kernel выбирает recommended next task по порядку:

1. explicit user selection;
2. unblock critical path;
3. reduce material uncertainty/risk;
4. satisfy earliest integration dependency;
5. higher product priority;
6. smaller reversible step;
7. stable lexical task ID.

Planner может предложить safe parallel batch. Пользовательский Result Envelope показывает recommended next step и доступные альтернативы.

### 11. Изменение DAG во время разработки

Новый факт, bug или change request может изменить граф. Harness обязан:

1. создать Change Pack или issue-derived Work Package;
2. выполнить impact analysis;
3. пометить affected tasks `STALE`;
4. сохранить completed history;
5. добавить/изменить dependencies;
6. повторно проверить topological order;
7. пересчитать next route.

Завершённые tasks не переписываются; при необходимости создаются corrective tasks.

### 12. Integration tasks

Integration task обязательна, когда:

- несколько independent tasks реализуют один user outcome;
- backend и frontend должны быть проверены вместе;
- contract consumers/producers требуют compatibility check;
- изменения затрагивают несколько repositories;
- migration + application rollout имеют порядок;
- shared environment должен быть подтверждён.

Integration task не должна повторять unit work. Она проверяет границы и общий acceptance.

### 13. Пример

```text
TSK-CNT-010  Принять API contract                 DONE
TSK-DB-020   Добавить индекс                      READY
TSK-BE-030   Реализовать endpoint                 READY
TSK-FE-040   Реализовать UI по CNT@1              READY
TSK-INT-050  Сквозной сценарий                    WAITING (020,030,040)
TSK-REL-060  Release checks                       WAITING (050)
```

Здесь 020, 030 и 040 находятся в одном causal layer и могут выполняться параллельно при отсутствии write conflicts.

### 14. Проверки planner

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

### 15. Критерии приёмки

1. Task не становится READY при отсутствующем producer artifact.
2. Planner обнаруживает циклы и future-only dependencies.
3. Greenfield и brownfield имеют явные baseline gates до implementation.
4. Deterministic next task воспроизводим.
5. Safe parallelism разрешён внутри causal layer.
6. Integration tasks закрывают cross-track acceptance.
7. Roadmap Harness содержит ранний working vertical slice.
8. Change Pack корректно инвалидирует и перестраивает affected graph.

---

<!-- SOURCE: 12_Implementation_Specifications/08_Safe_Parallel_Execution.md -->

## Безопасное параллельное выполнение задач

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Harness должен разрешать параллельную работу только там, где задачи причинно готовы и не могут повредить результаты друг друга. Типичный пример — backend и frontend после принятия общего API contract.

Параллельность является оптимизацией. Correctness, traceability и интеграция имеют приоритет.

### 2. Read/write model

Каждая task объявляет sets по нескольким ресурсным доменам:

```yaml
access_sets:
  repository_paths:
    read: [contracts/search/**, src/shared/types/**]
    write: [src/backend/search/**]

  contracts:
    read: [CNT-SEARCH@2]
    write: []

  documentation:
    read: [docs/api/search.md#endpoint-search]
    write: [docs/implementation/backend-search.md]

  database:
    read: [schema@12]
    write: []

  environment:
    read: [ENV-TEST-APP]
    write: []

  shared_artifacts:
    read: [LOCK-NPM@4]
    write: []
```

Домены должны поддерживать минимум:

- repository paths;
- public/internal contracts;
- documentation sections;
- database schema and migration head;
- dependency lockfiles;
- generated clients/code;
- shared configuration;
- test environments;
- release manifests;
- external systems.

### 3. Условие безопасной параллельности

Для каждой пары задач A и B должно выполняться:

```text
write(A) ∩ write(B) = ∅
write(A) ∩ read(B)  = ∅
read(A)  ∩ write(B) = ∅
```

Одинаковый read-only artifact разрешён, если обе task закреплены на одной accepted revision.

Дополнительно:

- обе tasks находятся в `READY`;
- нет causal dependency A→B или B→A;
- нет exclusive environment/capability lease conflict;
- integration route определён;
- rollback одной task не отменяет обязательный результат другой;
- shared contract frozen на время batch.

### 4. Parallel Batch Contract

```yaml
parallel_batch:
  id: PBT-SEARCH-001
  work_package_ref: WP-SEARCH-001
  task_refs:
    - TSK-DB-SEARCH-020
    - TSK-BE-SEARCH-030
    - TSK-FE-SEARCH-040

  frozen_inputs:
    - ref: CNT-SEARCH@2
      hash: sha256:...
    - ref: ADR-SEARCH-004@1
      hash: sha256:...

  conflict_analysis_ref: CFA-PBT-SEARCH-001
  lease_refs:
    - LSE-WT-BACKEND-001
    - LSE-WT-FRONTEND-001
    - LSE-DB-SCHEMA-001

  integration_task_ref: TSK-INT-SEARCH-050
  failure_policy: CONTINUE_INDEPENDENT_TASKS
  status: READY
```

### 5. Frozen contract rule

Frontend и backend могут читать один API contract. Они не могут одновременно менять его.

```text
Contract status ACCEPTED
→ revision/hash frozen in batch
→ all consumers compile against that revision
→ proposed change creates new Change Pack
→ affected tasks pause or finish under old revision by explicit policy
```

Contract writer task является отдельной causal prerequisite и не входит в consumer batch.

### 6. Worktrees и ownership

Для Git-backed проектов рекомендуется:

- отдельный worktree/branch на task;
- lease на write paths;
- task-scoped base revision;
- no implicit push;
- merge/integration owner;
- pre-merge conflict and stale checks.

Lease не заменяет declared scope. Даже при технической возможности agent не должен писать вне Task Contract.

### 7. Special shared resources

#### 7.1. Dependency lockfile

Если две tasks могут изменить один lockfile, они конфликтуют. Варианты:

- объединить dependency changes;
- назначить одну dependency task;
- последовательный merge/rebase gate;
- использовать isolated package scopes, если lockfiles действительно независимы.

#### 7.2. Database migrations

Две migration-writing tasks нельзя параллелить на одном migration head без reservation protocol. Допустимы:

- migration sequence lease;
- заранее выделенные non-conflicting namespaces, если framework поддерживает;
- отдельная integration migration task.

#### 7.3. Generated clients

Producer contract может быть frozen, но генерация одного и того же client output directory двумя tasks запрещена. Генерацию следует вынести в одну producer task.

#### 7.4. Test environment

Shared mutable environment требует lease или per-run isolation. Read-only use разрешён при доказанной изоляции test data.

### 8. Failure policy

```text
FAIL_FAST_BATCH
CONTINUE_INDEPENDENT_TASKS
PAUSE_ON_SHARED_INPUT_RISK
```

Default — `CONTINUE_INDEPENDENT_TASKS`, если failure не влияет на frozen inputs и shared environment. При подозрении на contract/environment corruption batch приостанавливается.

### 9. Integration Gate

После завершения parallel tasks integration task выполняет:

- merge/rebase checks;
- contract compatibility;
- cross-component tests;
- database/app ordering;
- documentation reconciliation;
- combined acceptance criteria;
- release readiness impact.

Нельзя объявлять Work Package `COMPLETED` только потому, что все parallel tasks по отдельности зелёные.

### 10. Пример backend/frontend

```text
TSK-CNT-SEARCH-010  принимает CNT-SEARCH@2        DONE

Parallel Batch:
  TSK-DB-SEARCH-020 writes migrations/search/**
  TSK-BE-SEARCH-030 writes backend/search/**
  TSK-FE-SEARCH-040 writes frontend/search/**
  all read CNT-SEARCH@2

TSK-INT-SEARCH-050:
  merge + generated client + e2e + docs
```

Если frontend task хочет изменить contract, она возвращает `WAITING_DECISION` или создаёт change proposal, но не редактирует frozen contract.

### 11. Dynamic conflict detection

До run выполняется static analysis declared sets. Во время run Tool Adapter проверяет actual writes. Если actual write выходит за scope:

```text
stop tool action
→ record SCOPE_VIOLATION
→ mark run FAILED_RECOVERABLE or BLOCKED
→ preserve evidence
→ recompute batch safety
```

Нельзя автоматически расширять write scope по факту попытки.

### 12. Критерии приёмки

1. Две tasks могут читать один frozen contract параллельно.
2. Любое write/read или write/write пересечение блокирует batch.
3. Planner учитывает paths, contracts, docs, DB, lockfiles и environments.
4. Worktrees и leases привязаны к task/run.
5. Actual writes проверяются runtime adapter.
6. Failure одной independent task не обязательно останавливает весь batch.
7. Integration task обязательна для общего user outcome.
8. Parallel batch пересчитывается при staleness или изменении shared input.

---

<!-- SOURCE: 12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md -->

## Политика неоднозначностей, вопросов и предположений

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Harness не должен молча угадывать material требования, но также не должен останавливать разработку из-за каждой мелкой детали. Неоднозначность сначала классифицируется по влиянию, и только затем выбирается действие.

### 2. Materiality levels

```text
MATERIAL
NON_MATERIAL_REVERSIBLE
TRIVIAL
```

#### 2.1. Material ambiguity

Неоднозначность material, если ответ может изменить:

- product scope или user outcome;
- architecture/technology baseline;
- public contract;
- security/privacy/data handling;
- irreversible migration;
- supported platform;
- permissions/side effects;
- acceptance criteria;
- существенный срок, capacity или reliability target;
- ownership между repositories/components.

Affected route обязан остановиться.

#### 2.2. Non-material reversible ambiguity

Примеры:

- локальное имя внутренней функции;
- расположение небольшого private helper в пределах разрешённого scope;
- formatting choice;
- обратимая implementation detail, не влияющая на contract.

В `PRAGMATIC` режиме можно применить default и зафиксировать assumption/task-local choice.

#### 2.3. Trivial ambiguity

Решается существующими style guides, formatter, linter или deterministic policy без отдельной записи.

### 3. Project ambiguity mode

```text
STRICT
PRAGMATIC
```

- `STRICT`: любая неразрешённая non-trivial ambiguity возвращается пользователю.
- `PRAGMATIC`: material ambiguity останавливает; non-material reversible ambiguity разрешается default с прозрачной записью.

Default для нового проекта — `PRAGMATIC`, если пользователь не выбрал strict governance и profile не требует strict mode.

### 4. Question Contract

```yaml
question:
  id: QST-ARCH-001
  intake_or_request_ref: RQ-20260806-0003
  project_ref: project-example

  text: "Должна ли система работать без подключения к интернету?"
  why_asked: "Ответ влияет на storage, sync и authentication architecture"
  materiality: MATERIAL
  affects:
    - ARCHITECTURE_BASELINE
    - TECHNOLOGY_BASELINE
    - REQUIREMENTS

  answer_type: SINGLE_CHOICE
  options:
    - id: ONLINE_ONLY
      label: "Только онлайн"
      explanation: "Проще инфраструктура; без сети функции недоступны"
    - id: LIMITED_OFFLINE
      label: "Часть функций офлайн"
      explanation: "Нужны локальный cache и синхронизация"
    - id: OFFLINE_FIRST
      label: "Полноценная offline-first работа"
      explanation: "Самая сложная модель данных и конфликтов"
    - id: UNKNOWN
      label: "Пока не знаю"
      explanation: "Harness предложит безопасный baseline и review trigger"

  recommendation:
    option_ref: ONLINE_ONLY
    rationale: "В исходной документации нет требования offline"

  blocking_scope:
    work_package_refs: [WP-BOOTSTRAP-001]
    task_refs: []

  response_required: true
  status: OPEN
```

### 5. Требования к формулировке вопроса

Пользователь должен понимать:

- о чём спрашивают;
- зачем это важно;
- как ответ повлияет на проект;
- какие варианты допустимы;
- что выбрать, если он не уверен;
- какой вариант рекомендует Harness и почему.

Запрещены вопросы без контекста вроде «Выберите consistency model» без пояснения понятным языком.

### 6. Question batching

Чтобы не перегружать пользователя:

- задаётся не более 3–5 связанных material вопросов за один batch;
- вопросы сортируются по blocking impact;
- зависимый вопрос не задаётся раньше ответа на родительский;
- ответы из документации не спрашиваются повторно;
- типовые вопросы, не влияющие на ближайший gate, откладываются;
- одна тема не размазывается на множество микровопросов.

### 7. Ответ «не знаю»

`UNKNOWN` является допустимым ответом. Harness обязан предложить:

1. reversible default;
2. последствия default;
3. owner unknown;
4. review trigger или срок пересмотра;
5. какие решения остаются отложенными;
6. может ли разработка продолжаться безопасно.

Пример:

```yaml
assumption:
  id: ASM-SCALE-001
  statement: "Первый релиз рассчитан до 1 000 активных пользователей в сутки"
  epistemic_status: ASSUMED
  owner_ref: ACT-PRODUCT-001
  impact_if_false: MEDIUM
  review_trigger: "Перед production launch или при уточнении capacity"
  reversible: true
```

### 8. Stop protocol

При material ambiguity agent обязан:

```text
1. Stop only the affected operation before unsafe side effects.
2. Preserve completed safe changes and evidence.
3. Record exact ambiguity and affected artifacts.
4. Return structured question/options/recommendation.
5. Mark task/request WAITING_DECISION.
6. Expose independent READY tasks.
7. Resume from stored checkpoint after answer.
```

Нельзя продолжать affected task «наиболее вероятным» способом без policy authorization.

### 9. Non-material defaults

Допустимый default должен быть:

- обратимым;
- локальным;
- соответствующим accepted style/policy;
- не расширяющим scope;
- не ослабляющим security/quality constraints;
- явно отмеченным в Task Report, если он не trivial.

```yaml
local_choice:
  statement: "Private helper размещён рядом с service implementation"
  basis_ref: PLC-CODE-STYLE-001
  reversible: true
```

### 10. Конфликты источников

Если documentation, user answer и current code расходятся:

- конфликт фиксируется как `CONFLICTING`;
- precedence применяется только там, где уже существует accepted policy;
- material semantic conflict требует reconciliation question/decision;
- code не считается автоматически источником истины;
- supplied documentation не считается автоматически current, пока не проверена revision/authority.

### 11. Examples

| Неоднозначность | Класс | Действие |
|---|---|---|
| Сколько пользователей ожидается? | Material для capacity, если влияет на architecture | Спросить или принять bounded assumption. |
| Как назвать private method? | Trivial | Style policy. |
| Offset или cursor pagination? | Material public contract | Decision question. |
| В какой папке разместить внутренний helper? | Non-material reversible | Default в pragmatic mode. |
| Можно ли отправлять данные во внешний model adapter? | Material security/data | Обязательное approval/policy. |

### 12. Критерии приёмки

1. Materiality оценивается до остановки.
2. Material ambiguity никогда не разрешается молча.
3. Non-material reversible choice не создаёт ненужный blocker в pragmatic mode.
4. Вопрос содержит объяснение, варианты, recommendation и `UNKNOWN` path.
5. Batch ограничен и не повторяет уже известные ответы.
6. Остановка затрагивает только зависимый scope.
7. Ответ создаёт event и пересчитывает readiness.
8. Assumptions имеют owner и review trigger.

---

<!-- SOURCE: 12_Implementation_Specifications/10_Blockers_Recovery_and_Progression.md -->

## Blockers, восстановление и гарантированный следующий маршрут

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Harness не гарантирует, что любой исходный подход выполним. Он гарантирует, что пользователь никогда не получает тупиковый статус без объяснения и следующего маршрута.

Инвариант:

> У каждого незавершённого состояния есть хотя бы один безопасный recovery route: исправить prerequisite, изменить подход, изменить scope, отложить, отменить или запросить разрешённое исключение.

### 2. Blocker classes

```text
BLOCKED_USER_DECISION
BLOCKED_APPROVAL
BLOCKED_DEPENDENCY
BLOCKED_ARTIFACT
BLOCKED_CAPABILITY
BLOCKED_ENVIRONMENT
BLOCKED_CONSTRAINT
BLOCKED_CONFLICT
BLOCKED_STALE_STATE
BLOCKED_EXTERNAL_SYSTEM
BLOCKED_SECURITY
```

Run failures классифицируются отдельно:

```text
FAILED_RETRYABLE
FAILED_NON_RETRYABLE_APPROACH
FAILED_COMPENSATION_REQUIRED
FAILED_VALIDATION
```

### 3. Blocker Contract

```yaml
blocker:
  id: BLK-SEARCH-001
  schema_version: 1
  project_ref: project-example
  request_ref: RQ-20260806-0004
  work_package_ref: WP-SEARCH-001
  task_ref: TSK-BE-SEARCH-030@1
  run_ref: RUN-20260806-0010 | null

  class: BLOCKED_ARTIFACT
  status: OPEN
  stopped_at: TASK_READINESS
  reason: "API contract CNT-SEARCH не принят"
  impact: "Backend и frontend implementation не могут компилироваться"

  safe_progress:
    completed_steps: []
    preserved_artifacts: []
    side_effects: NONE
    compensation_status: NOT_REQUIRED

  evidence_refs: [EVD-READINESS-010]
  affected_refs: [TSK-BE-SEARCH-030, TSK-FE-SEARCH-040]
  independent_ready_task_refs: [TSK-DOC-GLOSSARY-005]

  options:
    - id: OPT-DECIDE-CONTRACT
      action: RESOLVE_DECISION
      label: "Принять search contract"
      consequences: "Разблокирует backend и frontend"
      route: RTE-DECIDE-SEARCH-CONTRACT
    - id: OPT-REDUCE-SCOPE
      action: CHANGE_SCOPE
      label: "Оставить только backend prototype"
      consequences: "Не создаёт публичный frontend contract"
      route: RTE-CHANGE-SCOPE
    - id: OPT-DEFER
      action: DEFER_TASK
      label: "Отложить feature"
      consequences: "Work Package останется PARTIAL"
      route: RTE-DEFER-SEARCH

  recommendation:
    option_ref: OPT-DECIDE-CONTRACT
    rationale: "Это минимальный prerequisite исходного outcome"

  resume_condition:
    expression: "CNT-SEARCH.status == ACCEPTED"
    check_operation: EVALUATE_TASK_READINESS

  created_at: 2026-08-06T12:00:00Z
```

### 4. Разрешённые recovery actions

```text
ANSWER_QUESTION
APPROVE_ACTION
PREPARE_ENVIRONMENT
ACQUIRE_CAPABILITY
CREATE_OR_ACCEPT_ARTIFACT
FIX_DEPENDENCY
RETRY_RUN
REPLAN_TASK
SPLIT_TASK
CHANGE_APPROACH
CHANGE_SCOPE
REQUEST_ALLOWED_WAIVER
REPLACE_DEPENDENCY
DEFER_TASK
CANCEL_TASK
SUPERSEDE_REQUIREMENT
ROLLBACK_OR_COMPENSATE
```

`REQUEST_ALLOWED_WAIVER` допустим только если policy разрешает waiver. Hard safety/legal prohibition нельзя обходить ради продолжения.

### 5. Отсутствие «100% blocker»

Даже если исходный запрос невозможен, Harness возвращает варианты:

- реализовать безопасную альтернативу;
- сузить scope;
- заменить технологию;
- подготовить недостающую среду;
- перенести выполнение;
- отменить task с сохранением причины;
- пересмотреть requirement через formal decision.

Это не означает обязательное ослабление hard constraint.

### 6. Scope блокировки

Blocker имеет минимально необходимый scope:

```text
TASK_LOCAL
WORK_PACKAGE_LOCAL
TRACK_LOCAL
PROJECT_WIDE
HARNESS_DISTRIBUTION
```

Project-wide blocker допустим только при нарушении global invariant, повреждении canonical state или отсутствии обязательного Project Definition/Architecture baseline. Обычная blocked task не останавливает независимые READY tasks.

### 7. Safe state and compensation

При runtime failure Harness фиксирует:

- какие writes начались;
- какие завершены;
- транзакционны ли они;
- какой rollback доступен;
- выполнена ли компенсация;
- можно ли безопасно retry.

```yaml
safe_state:
  repository_revision: sha256:...
  uncommitted_changes_ref: ART-WT-SNAPSHOT-001
  external_side_effects: []
  compensation_status: COMPLETE
  retry_safe: true
```

Если полная компенсация невозможна, статус `PARTIALLY_COMPENSATED` должен быть зарегистрирован в едином compensation status registry и отражён в Result Envelope как warning/blocker.

### 8. Retry policy

Retry допустим только если:

- ошибка классифицирована retryable;
- idempotency strategy известна;
- base revisions не изменились;
- capability grants ещё действуют;
- side effects отсутствуют или compensated;
- retry budget policy не превышена;
- повтор имеет отличимый `run_id` и увеличенный `attempt_no`.

Нельзя бесконечно повторять deterministic failure.

### 9. Resume workflow

```text
User/automation satisfies option
→ recovery evidence recorded
→ resume condition evaluated
→ affected task/work package revalidated
→ stale prompt/context discarded
→ new JIT bundle compiled
→ new Run created
→ Result Envelope references original blocker
```

Resume не продолжает старый agent session без проверки current state.

### 10. Независимые задачи

При blocker Harness показывает:

- recommended recovery route;
- независимые READY tasks;
- риск переключения контекста;
- будет ли blocked work package оставаться current.

Автоматическое переключение допустимо только при project policy. Иначе пользователь получает выбор, но blocked state сохраняется.

### 11. User-facing blocked result

```text
Статус: BLOCKED
Остановлено на: проверке готовности backend-задачи
Причина: API-контракт ещё не принят
Уже сделано: изменений кода нет
Рекомендуется: выбрать формат пагинации и принять CNT-SEARCH@2
Другие варианты: уменьшить scope или отложить feature
Можно продолжить независимо: задача обновления glossary
```

### 12. Критерии приёмки

1. Каждый blocker имеет class, evidence, options, recommendation и resume condition.
2. Hard constraint не ослабляется автоматически.
3. Blocker scope минимален и не замораживает независимый проект без причины.
4. Runtime failure сохраняет safe state и compensation status.
5. Retry создаёт новый Run и проходит current revision checks.
6. Resume пересобирает stale prompt/context.
7. Даже невозможный подход имеет alternative/change-scope/cancel route.
8. Result Envelope понятно объясняет причину и варианты устранения.

---

<!-- SOURCE: 12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md -->

## Verification, тестирование и test data policy

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Каждая выполненная задача должна иметь достаточное доказательство результата, но Harness не должен создавать бесполезные тесты ради формального наличия теста. Универсальное правило:

> Каждая task имеет пропорциональный Verification Profile, соответствующий типу изменения и риску.

### 2. Verification Profile

```yaml
verification_profile:
  id: VFP-CODE-TARGETED-001
  revision: 1
  applies_to: [IMPLEMENT, FIX, REFACTOR]
  risk_level: MEDIUM

  required_checks:
    - TARGETED_TESTS
    - NEAREST_REGRESSION
    - STATIC_ANALYSIS
    - SCOPE_DIFF_CHECK
    - DOCUMENTATION_IMPACT_CHECK

  conditional_checks:
    - when: "public_contract_changed"
      add: [CONTRACT_COMPATIBILITY]
    - when: "database_changed"
      add: [MIGRATION_FORWARD, DATA_INTEGRITY, RESTORE_OR_ROLLBACK]

  completion_rule: ALL_REQUIRED_PASS
  known_failure_policy_ref: PLC-KNOWN-FAILURES-001
  evidence_retention: PROJECT_LIFETIME
  status: ACTIVE
```

### 3. Матрица проверок по типу задачи

| Task type | Минимальная проверка |
|---|---|
| `CODE` | Targeted tests, nearest regression, static checks, diff/scope validation. |
| `BUG_FIX` | Reproduction fixture, fix verification, nearest regression. |
| `REFACTOR` | Behavior-preserving tests, static checks, public contract diff. |
| `API_OR_CONTRACT` | Schema validation, compatibility, provider/consumer checks. |
| `DATABASE_MIGRATION` | Forward migration, data integrity, repeatability/idempotency, rollback/restore plan. |
| `UI` | Component/browser/accessibility checks пропорционально риску. |
| `INFRASTRUCTURE` | Syntax/schema, plan/dry-run, policy, rollback. |
| `DOCUMENTATION` | Links, anchors, examples, references, schema consistency. |
| `DIRECTORY_OR_CONFIG` | Structure/schema/dry-run; отдельный unit test обычно не нужен. |
| `ARCHITECTURE_DECISION` | Completeness, alternatives, constraint coverage, approval. |
| `SKILL_OR_PROMPT` | Compiler/routing fixtures, behavioral and negative tests. |
| `SECURITY` | Positive + negative policy checks, boundary tests. |

### 4. Test selection

Harness не запускает полный suite на каждой мелкой task по умолчанию. Набор определяется:

```text
changed paths
+ affected requirements/contracts
+ dependency graph
+ risk level
+ task type
+ project policy
+ release phase
```

Уровни:

```text
TARGETED
NEAREST_REGRESSION
TRACK_INTEGRATION
PROJECT_REGRESSION
RELEASE_SUITE
```

Task completion обычно требует первых двух уровней. Полный project/release suite запускается на integration/release gates или при high-risk change.

### 5. Baseline failures

До выполнения code-changing task Harness по возможности фиксирует baseline:

```yaml
test_baseline:
  id: TSB-20260806-001
  repository_revision: sha256:...
  environment_ref: TEN-APP-TEST@5
  selected_suite: NEAREST_REGRESSION
  passed: 124
  failed:
    - test_ref: TEST-LEGACY-007
      failure_hash: sha256:...
      classification: KNOWN_UNRELATED
  captured_at: 2026-08-06T13:00:00Z
```

После изменения failure классифицируется:

```text
NEW_REGRESSION
EXPECTED_BEHAVIOR_CHANGE
STALE_TEST
KNOWN_UNRELATED
FLAKY_SUSPECTED
ENVIRONMENT_FAILURE
```

Новая регрессия, внесённая текущей task, блокирует completion. Known unrelated failure не приписывается текущей task, но остаётся видимой.

### 6. Политика устаревших тестов

Тест считается stale, если он проверяет behavior, который формально изменён accepted requirement/decision.

Правила:

1. Test update/delete выполняется в той же Work Package или mandatory dependent task.
2. Удаление требует ссылки на superseded requirement/decision или доказательство дублирования.
3. Нельзя удалить тест только ради зелёного результата.
4. Если тест выявляет реальную регрессию, изменение кода не считается завершённым.
5. Если test fixture несовместима с новой valid architecture, она обновляется с documentation/evidence.
6. Release gate не игнорирует known failures без policy/waiver.

```yaml
stale_test_resolution:
  test_ref: TEST-AUTH-OLD-SESSION
  action: UPDATE
  reason: "ADR-AUTH-003 superseded stateless session behavior"
  decision_ref: ADR-AUTH-003@1
  replacement_test_refs: [TEST-AUTH-REDIS-SESSION]
```

### 7. Test Environment Contract

```yaml
test_environment:
  id: TEN-APP-TEST
  revision: 5
  strategy: PREMIGRATED_TEMPLATE
  database_engine_ref: TEC-POSTGRES@16
  migration_set_hash: sha256:...
  fixture_version: 12

  isolation:
    mode: SCHEMA_PER_RUN
    naming_template: "harness_${run_id}"
    cleanup: DROP_SCHEMA_ON_SUCCESS_OR_TTL

  reset_strategy: TRANSACTION_ROLLBACK
  shared_services:
    - ref: SVC-REDIS-TEST
      isolation: NAMESPACE_PER_RUN

  rebuild_when:
    - MIGRATION_SET_CHANGED
    - TEMPLATE_INCOMPATIBLE
    - CORRUPTION_DETECTED

  status: READY
```

### 8. Test database policy

Harness не пересоздаёт всю БД и не прогоняет все миграции на каждую task без необходимости.

Preferred flow:

```text
Maintain pre-migrated template/snapshot keyed by migration_set_hash
→ create isolated clone/schema for run
→ apply only pending migrations when hash changed
→ load versioned minimal fixtures
→ execute targeted tests
→ reset via transaction/clone disposal
```

Варианты isolation по приоритету:

1. database clone per run;
2. schema per run;
3. container/instance per parallel batch;
4. shared persistent test DB with exclusive lease — только если изоляция выше недоступна.

### 9. Миграции

Database-changing task обязана проверить:

- migration ordering;
- forward apply на current baseline;
- повторный запуск или explicit non-idempotency contract;
- data compatibility;
- application compatibility before/after rollout, если требуется;
- rollback либо restore procedure;
- template migration hash update;
- parallel migration-head conflicts.

Нельзя считать «миграция применена локально» достаточным evidence для shared/release gate.

### 10. Documentation and structural tasks

Для задач документации, каталогов и простых config changes не создаются искусственные unit tests. Достаточны:

- schema/format validation;
- link/anchor/reference checks;
- expected path existence;
- dry-run;
- generated-view consistency;
- diff scope check.

Verification Profile должен явно возвращать `NOT_APPLICABLE` для неуместных test categories, а не молча пропускать их.

### 11. Evidence Contract

```yaml
verification_evidence:
  schema_version: 1
  id: EVD-TSK-BE-SEARCH-030-001
  ref: EVD-TSK-BE-SEARCH-030-001
  kind: TEST_REPORT
  status: PASS
  provenance:
    source_type: PROJECT_HARNESS_VALIDATION_REPORT
    source_ref: VAL-RUN-20260806-0011
    producer: PROJECT_HARNESS_RUNTIME
  base_revision: tree:sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  criterion_refs: [PROTOTYPE_CORE_FLOW]
  outcome_refs: []
  profile_control_refs: []
  source_bindings:
    - ref: VAL-RUN-20260806-0011
      path: .harness/reports/VAL-RUN-20260806-0011.yaml
      sha256: sha256:abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
  created_at: 2026-08-18T12:00:00Z
  task_ref: TSK-BE-SEARCH-030@1
  run_ref: RUN-20260806-0011
  report_refs: [VAL-RUN-20260806-0011]
  validator: PROJECT_HARNESS_RUNTIME
  details:
    profile_ref: VFP-CODE-TARGETED-001@1
    environment_revision: TEN-APP-TEST@5
    checks:
      - id: CHK-TARGETED
        command_ref: CMD-NPM-TEST-SEARCH
        result: PASS
        exit_code: 0
        output_digest: sha256:abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
    baseline_comparison:
      new_failures: []
      resolved_failures: []
      unchanged_known_failures: [TEST-LEGACY-007]
```

Новые Gate используют только normalized immutable evidence. Historical record без `schema_version` остаётся readable, но не закрывает mandatory criterion без нового source-bound artifact.

### 12. Flaky tests

Flaky suspected test не отключается автоматически. Harness:

1. сравнивает failure signature с baseline/history;
2. выполняет bounded rerun по policy;
3. классифицирует как suspected flaky;
4. создаёт отдельную corrective task, если подтверждено;
5. не объявляет product task failed, если failure доказан как unrelated и policy разрешает;
6. сохраняет warning для release gate.

### 13. Критерии приёмки

1. Каждая task имеет Verification Profile, но не обязательно unit test.
2. Test selection зависит от impact и риска.
3. Новая регрессия блокирует completion; known unrelated failure не маскируется.
4. Stale test update/delete имеет formal rationale.
5. Test DB использует pre-migrated template и isolation, а не полный rebuild каждый раз.
6. Parallel runs не разделяют mutable test data без lease/isolation.
7. Documentation/config tasks проверяются пропорционально.
8. Evidence воспроизводимо связано с revisions и environment.

---

<!-- SOURCE: 12_Implementation_Specifications/12_Request_Trace_and_Logging.md -->

## Сквозной Request Trace и логирование

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Логирование Harness должно позволять ответить:

- что попросил пользователь;
- как запрос классифицирован;
- какой план и tasks созданы;
- какой prompt/context/capability набор использован;
- какие tools вызваны;
- что изменилось;
- как это проверено;
- почему произошла остановка;
- как продолжить.

Run Trace недостаточен: нужен `Request Trace`, связывающий весь путь от ввода до Result Envelope.

### 2. Correlation model

```yaml
trace_context:
  correlation_id: COR-20260806-0001
  session_id: SES-20260806-0001
  request_id: RQ-20260806-0001
  request_plan_id: RQP-20260806-0001
  work_package_id: WP-SEARCH-001
  task_id: TSK-BE-SEARCH-030
  run_id: RUN-20260806-0011
  tool_invocation_id: TIV-20260806-0042
```

Не все IDs присутствуют на ранних этапах, но `correlation_id` создаётся при приёме input и проходит через все события.

### 3. Request Trace Contract

```yaml
request_trace:
  id: TRT-COR-20260806-0001
  correlation_id: COR-20260806-0001
  project_ref: project-example
  actor_ref: ACT-USER-001
  started_at: 2026-08-06T14:00:00Z

  spans:
    - id: SPN-001
      parent_span_ref: null
      type: REQUEST_RECEIVED
      entity_ref: RQ-20260806-0001
      started_at: ...
      ended_at: ...
      status: OK

    - id: SPN-002
      parent_span_ref: SPN-001
      type: REQUEST_CLASSIFIED
      entity_ref: RQ-20260806-0001
      attributes:
        request_class: DEVELOPMENT_REQUEST
        mode: EXECUTE
      status: OK

    - id: SPN-003
      parent_span_ref: SPN-001
      type: TASK_RUN
      entity_ref: RUN-20260806-0011
      status: OK

  result_ref: RES-20260806-0001
  terminal_status: COMPLETED
  completed_at: 2026-08-06T14:12:00Z
```

### 4. Event types

Минимальный registry:

```text
REQUEST_RECEIVED
REQUEST_CLASSIFIED
REQUEST_PLAN_CREATED
QUESTION_ASKED
ANSWER_RECORDED
DECISION_ACCEPTED
WORK_PACKAGE_CREATED
TASK_CREATED
TASK_READY
TASK_CLAIMED
PROMPT_PLAN_RESOLVED
PROMPT_BUNDLE_COMPILED
RUN_STARTED
TOOL_INVOCATION_STARTED
TOOL_INVOCATION_COMPLETED
ARTIFACT_CHANGED
VERIFICATION_COMPLETED
DOCUMENTATION_UPDATED
BLOCKER_CREATED
RECOVERY_SELECTED
RUN_COMPLETED
TASK_COMPLETED
WORK_PACKAGE_COMPLETED
RESULT_RENDERED
STATE_TRANSITIONED
```

Каждый event имеет schema, actor, timestamp, entity refs, previous/resulting revisions и data classification.

### 5. Логировать обязательно

- request classification и mode;
- material assumptions/questions/decisions;
- plan and DAG changes;
- hashes ключевых canonical inputs;
- selected skill/adapter/profile;
- capability grants and denials;
- exact commands/tool operations в нормализованном виде;
- actual write paths;
- verification outcomes;
- blockers/retries/resume;
- documentation and state updates;
- terminal Result Envelope.

### 6. Не логировать

- секреты, credentials, private keys, access tokens;
- полный sensitive context без необходимости;
- скрытый chain-of-thought модели;
- неограниченные raw dumps;
- содержимое файлов, если достаточно hash/path/diff summary;
- provider billing, monetary cost или token-usage accounting.

Допустимы технические context compatibility metrics, например размер materialized packet, только для предотвращения overflow. Они не образуют cost ledger.

### 7. Data classification и redaction

Каждое поле имеет classification:

```text
PUBLIC
PROJECT_INTERNAL
CONFIDENTIAL
RESTRICTED
SECRET_REFERENCE_ONLY
```

До persist выполняется redaction policy:

- secret value заменяется reference/digest;
- sensitive tool output хранится в защищённом evidence store;
- user-facing trace возвращает только безопасную сводку;
- export требует отдельной capability и policy.

### 8. Append-only semantics

Исторические events, runs и evidence не переписываются. Исправление создаёт новый event:

```text
EVENT_RECORDED
→ CORRECTION_EVENT references original
```

Current state является materialized view поверх append-only event log и canonical snapshots.

### 9. Tool Invocation Contract

```yaml
tool_invocation:
  id: TIV-20260806-0042
  run_ref: RUN-20260806-0011
  task_ref: TSK-BE-SEARCH-030@1
  adapter_ref: TAD-FILESYSTEM@2
  capability_grant_ref: CGR-RUN-0011

  operation: WRITE_FILE
  normalized_target: src/backend/search/service.ts
  input_digest: sha256:...
  output_digest: sha256:...
  actual_write_paths:
    - src/backend/search/service.ts

  started_at: ...
  completed_at: ...
  status: SUCCESS
  error_ref: null
```

### 10. Логирование стадий проекта

Intake, architecture, planning, execution, integration, release и maintenance используют один event envelope. Для non-code stages evidence может быть:

- accepted answer batch;
- schema validation;
- decision approval;
- link/reference validation;
- dry-run output;
- source inventory hash.

«Все этапы покрыты логами» не означает запуск тестов для каждого Markdown-файла; это означает, что переходы и результаты доказуемы.

### 11. Status and recovery queries

Control request `status` читает trace/state и возвращает:

- current project phase;
- active Work Package;
- running/blocked tasks;
- last completed result;
- next recommended route;
- outstanding decisions;
- known failures/risks.

`resume` использует blocker and trace refs, а не свободное угадывание, где остановилась работа.

### 12. Retention

Рекомендуемые классы:

```text
PERMANENT_PROJECT_HISTORY
RELEASE_LIFETIME
ACTIVE_WORK_LIFETIME
EPHEMERAL_DEBUG
```

Canonical decisions, task reports, run summaries, evidence digests и state events сохраняются как project history. Большие raw tool outputs могут иметь TTL при наличии digest и policy.

### 13. Критерии приёмки

1. Один correlation ID связывает Request, Plan, Work Package, Task, Run, Evidence и Result.
2. Все state transitions имеют events.
3. Actual writes логируются и сравниваются со scope.
4. Секреты и hidden reasoning не попадают в trace.
5. History append-only; corrections не переписывают прошлое.
6. Status/resume восстанавливаются из state/trace после cold start.
7. Logging работает для code и non-code stages.
8. Token/cost accounting отсутствует в contracts и reports.

---

<!-- SOURCE: 12_Implementation_Specifications/13_Technology_Baseline.md -->

## Technology Baseline и выбор стека технологий

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Architecture Baseline отвечает на вопрос «как устроена система», а Technology Baseline — «какими конкретными технологиями и версиями она реализуется». Harness не должен скрыто выбирать stack из шаблона или предпочтений модели.

Technology Baseline создаётся после Project Definition и architecture options, но до bootstrap и product implementation.

### 2. Области baseline

```text
LANGUAGES
RUNTIMES
FRAMEWORKS
DATABASES
MESSAGING
STORAGE
INFRASTRUCTURE
BUILD_TOOLS
PACKAGE_MANAGERS
TEST_TOOLS
OBSERVABILITY
SECURITY_TOOLS
DEPLOYMENT_TARGETS
SUPPORTED_PLATFORMS
```

Не все области обязательны для каждого profile; `NOT_APPLICABLE` фиксируется явно.

### 3. Technology Baseline Contract

```yaml
technology_baseline:
  id: TBL-TECH-001
  revision: 1
  project_ref: project-example
  status: ACCEPTED

  drivers:
    requirement_refs: [REQ-001]
    quality_attribute_refs: [QUA-001, QUA-002]
    constraint_refs: [CST-PLATFORM-001]
    architecture_refs: [ADR-ARCH-001]

  selections:
    - area: LANGUAGE
      technology_ref: TEC-TYPESCRIPT
      version_constraint: ">=5.6 <6"
      status: ACCEPTED
      decision_ref: ADR-TECH-001

    - area: RUNTIME
      technology_ref: TEC-NODE
      version_constraint: "22.x"
      status: ACCEPTED
      decision_ref: ADR-TECH-001

    - area: DATABASE
      technology_ref: TEC-POSTGRES
      version_constraint: "16.x"
      status: ACCEPTED
      decision_ref: ADR-DATA-002

  compatibility_matrix_ref: CMP-TECH-001
  lifecycle_risks: []
  license_constraints: []
  team_capability_assumptions: []
  verification_commands: []
  source_refs: []
  accepted_by: DEC-TECH-001
```

### 4. Technology Candidate Contract

```yaml
technology_candidate:
  id: TCN-DB-POSTGRES
  area: DATABASE
  label: "PostgreSQL"
  satisfies_refs: [REQ-DATA-001, QUA-RELIABILITY-001]

  evaluation:
    architecture_fit: HIGH
    operational_fit: MEDIUM
    team_fit: UNKNOWN
    ecosystem_maturity: HIGH
    portability: MEDIUM
    security_fit: HIGH
    migration_complexity: LOW

  constraints:
    violated: []
    assumptions: [ASM-TEAM-SQL-001]

  benefits: []
  tradeoffs: []
  risks: []
  required_skills: [SKL-POSTGRES-MIGRATIONS]
  bootstrap_impact: []
```

### 5. Процедура выбора

```text
1. Read Project Definition, constraints and quality attributes.
2. For brownfield, inventory existing technologies and versions.
3. Determine mandatory technology areas by profile/architecture.
4. Reuse accepted existing technology unless change has justified value.
5. Produce 2–4 realistic candidates for material selections.
6. Evaluate compatibility, lifecycle, operations, security and team impact.
7. Ask only material user questions.
8. Record ADR/Decision.
9. Build compatibility matrix.
10. Derive skill gaps, bootstrap tasks and verification commands.
```

### 6. Критерии оценки

- соответствие requirements and constraints;
- architecture fit;
- поддерживаемые deployment platforms;
- security/data boundaries;
- availability/reliability needs;
- performance/capacity assumptions;
- operational complexity;
- maintainability;
- team knowledge and hiring constraints;
- ecosystem/tooling;
- version compatibility;
- licensing and supply-chain policy;
- migration/rollback complexity;
- offline requirements;
- brownfield compatibility.

Cost/token optimization model providers не входит в Technology Baseline Harness. Бизнес-стоимость инфраструктуры создаваемого проекта может быть обычным project constraint, если пользователь её задал.

### 7. Пользовательские вопросы о stack

Пользователь не обязан знать конкретную технологию. Вопрос формулируется через последствия:

```text
Нужна ли работа без интернета?
Где будет размещаться система?
Есть ли у команды обязательный язык/платформа?
Нужна ли горизонтальная масштабируемость?
Есть ли существующая БД, которую нельзя менять?
```

Если пользователь отвечает «не знаю», Harness предлагает recommended baseline и объясняет, почему он подходит, какие assumptions приняты и когда их пересмотреть.

### 8. Brownfield baseline

Для существующего проекта технологии получают один из статусов:

```text
ACCEPTED_AS_IS
ACCEPTED_WITH_UPGRADE_TASK
LEGACY_TOLERATED
REPLACE_PROPOSED
UNSUPPORTED_BLOCKER
UNKNOWN_VERSION
```

Harness не заменяет framework или database автоматически. Улучшение оформляется отдельной improvement branch/Work Package с impact and migration plan.

### 9. Compatibility Matrix

```yaml
technology_compatibility:
  id: CMP-TECH-001
  combinations:
    - refs: [TEC-NODE@22, TEC-TYPESCRIPT@5.6, TEC-FRAMEWORK-X@4]
      status: VERIFIED
      evidence_refs: [EVD-TECH-COMPAT-001]
  unsupported: []
  unknown: []
```

Unknown material compatibility блокирует bootstrap или получает explicit validation task раньше dependent implementation.

### 10. Изменение baseline

Technology change после bootstrap проходит `PROJECT_EVOLUTION`:

```text
Change request
→ alternatives and ADR
→ impact map
→ migration/rollback plan
→ task and skill invalidation
→ staged implementation
→ compatibility and release gates
```

Нельзя изменить version/technology только редактированием config без canonical decision.

### 11. Связь со skills и prompts

Accepted selections создают требования к:

- project skills;
- tool adapters;
- verification profiles;
- bootstrap templates;
- context sources;
- Codex guidance.

Task не становится READY, если необходимый skill/tool для accepted technology отсутствует.

### 12. Критерии приёмки

1. Stack не выбирается до Project Definition и architecture drivers.
2. Каждая material selection имеет decision reference.
3. Version constraints and compatibility записаны явно.
4. Brownfield technology не заменяется скрыто.
5. Unknown compatibility создаёт prerequisite validation task.
6. Technology Baseline порождает skill gap and bootstrap plan.
7. Изменение baseline выполняется через Change Pack and migration.
8. Пользователь получает понятное объяснение вариантов без требования знать jargon.

---

<!-- SOURCE: 12_Implementation_Specifications/14_Skill_Registry_and_Lifecycle.md -->

## Skill Registry, создание и lifecycle скиллов

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Skills описывают повторяемые способы выполнения классов задач. Harness не должен создавать новый skill для каждой task. Сначала проверяется возможность повторного использования и настройки существующего skill.

Порядок предпочтения:

```text
REUSE
→ CONFIGURE
→ EXTEND
→ CREATE
```

### 2. Уровни skills

```text
UNIVERSAL
PROFILE
PROJECT
TEMPORARY_EXPERIMENTAL
```

| Уровень | Назначение |
|---|---|
| `UNIVERSAL` | Общие repeatable workflows Harness. |
| `PROFILE` | Дополнение для типа проекта, например API service. |
| `PROJECT` | Специфичный повторяемый workflow конкретного проекта. |
| `TEMPORARY_EXPERIMENTAL` | Candidate для проверки; не используется READY tasks без explicit approval. |

Одноразовая работа описывается Task Contract, а не skill.

### 3. Skill Contract

```yaml
skill:
  id: SKL-PROJECT-CSV-IMPORT
  revision: 2
  namespace: project:example
  level: PROJECT
  status: ACTIVE

  name: "CSV import implementation"
  purpose: "Повторяемая реализация и проверка import pipeline"
  applies_to_task_types: [IMPLEMENT, FIX, VALIDATE]
  technology_refs: [TEC-TYPESCRIPT, TEC-POSTGRES]

  input_contract:
    required_refs: [TASK_CONTRACT, CONTEXT_PLAN]
    optional_refs: [MIGRATION_BASELINE]

  output_contract_ref: SCHEMA-AGENT-TASK-RESULT@1
  required_capabilities:
    - FILESYSTEM_READ
    - FILESYSTEM_WRITE
    - COMMAND_EXECUTE

  allowed_scope_patterns: []
  prohibited_operations: [GIT_PUSH, DEPLOY]
  procedure:
    steps: []
    stop_conditions: []
    verification_profile_ref: VFP-CODE-TARGETED-001

  prompt_module_refs: [PMD-SKL-CSV-IMPORT@2]
  adapter_compatibility: [ADP-CODEX@1]
  evaluation_suite_ref: EVS-SKL-CSV-IMPORT@2

  provenance:
    created_from: SKL-PROFILE-DATA-PIPELINE@1
    owner_ref: ACT-MAINTAINER-001
  version_policy: SEMANTIC
```

### 4. Skill lifecycle

```text
DRAFT → VALIDATING → VALIDATED → ACTIVE
          ↘ REJECTED
ACTIVE → DEPRECATED → RETIRED
ACTIVE → SUSPENDED
```

- `DRAFT`/`VALIDATING` не используются production tasks.
- `REJECTED` завершает неуспешную validation revision; повторная попытка создаёт новую revision.
- `VALIDATED` означает пройденные tests, но ещё не выбранный default.
- `ACTIVE` разрешён routing.
- `SUSPENDED` временно запрещён из-за defect/security issue.
- `DEPRECATED` остаётся для старых runs, но новые tasks получают replacement.

### 5. Skill Readiness Gate

```yaml
skill_readiness:
  skill_ref: SKL-PROJECT-CSV-IMPORT@2
  checks:
    schema: PASS
    procedure_completeness: PASS
    capability_minimization: PASS
    output_schema: PASS
    adapter_compatibility: PASS
    behavioral_fixtures: PASS
    negative_fixtures: PASS
    documentation: PASS
    supply_chain: PASS
  status: PASS
```

Task не становится READY, пока primary skill не `ACTIVE` и не совместим с execution profile.

### 6. Skill Gap Analysis

После Architecture and Technology Baseline Harness строит:

```yaml
skill_gap_analysis:
  project_ref: project-example
  required_workflows:
    - workflow: IMPLEMENT_API_ENDPOINT
      result: REUSE
      skill_ref: SKL-UNIVERSAL-IMPLEMENT@3
    - workflow: APPLY_PROJECT_MIGRATION_PATTERN
      result: EXTEND
      base_skill_ref: SKL-PROFILE-DB-MIGRATION@2
    - workflow: GENERATE_VENDOR_SPECIFIC_PACKAGE
      result: CREATE
      rationale: "Повторяемый project-specific packaging protocol"
  one_off_workflows:
    - workflow: INITIAL_DATA_CLEANUP
      result: TASK_ONLY
```

### 7. Создание нового skill

```text
1. Identify repeatable workflow and expected outputs.
2. Verify no active skill can express it through configuration.
3. Select namespace and owner.
4. Define input/output contracts and minimal capabilities.
5. Write bounded procedure and stop conditions.
6. Define evaluation fixtures and negative cases.
7. Validate against at least two representative tasks where possible.
8. Activate through control-plane change.
9. Recompute dependent task readiness.
```

Skill creation itself является отдельной project control task и причинным prerequisite product tasks.

### 8. Routing policy

Каждая task имеет:

```yaml
route:
  primary_skill_ref: SKL-UNIVERSAL-IMPLEMENT@3
  supporting_skill_refs:
    - SKL-PROFILE-SECURITY-REVIEW@1
```

- primary skill ровно один;
- supporting skills добавляются только для отдельной bounded concern;
- generic tool usage не оформляется как skill;
- skill не выбирает следующую task;
- skill не расширяет permissions Task Contract.

### 9. Project-local storage

```text
.harness/
└── skills/
    ├── registry.yaml
    ├── ACTIVE/
    ├── DRAFT/
    ├── EVALUATIONS/
    └── MIGRATIONS/
```

Universal/profile skills referenced by version and digest; project-local archive не обязан копировать их содержимое, если distribution доступна и integrity verified.

### 10. Versioning and invalidation

- breaking input/output/procedure change → major revision;
- backward-compatible addition → minor revision;
- editorial clarification without semantic change → patch.

Изменение active skill:

1. создаёт new revision;
2. запускает evaluation suite;
3. выполняет impact analysis;
4. помечает queued Prompt Plans stale;
5. не изменяет bundle completed runs;
6. переводит dependent tasks на новую revision только по migration policy.

### 11. Skill evaluation

Минимум:

- happy-path fixture;
- material ambiguity stop case;
- scope violation negative case;
- missing capability case;
- malformed output case;
- representative technology/profile case;
- regression fixture for every fixed skill defect.

### 12. Project resolution в Core v0.4.1

Skill не создаётся заново для каждого Project Instance.

Для каждого проекта создаются только:

```text
Skill Gap Analysis
resolved skill references
project configuration
exact versions and digests in PROJECT_LOCK
reproducible .harness/skills/registry.yaml
```

Причинная цепочка:

```text
documentation + repository evidence + questionnaire
→ accepted Project Definition
→ Architecture Baseline
→ Technology Baseline
→ required repeatable workflows
→ Skill Gap Analysis
→ REUSE / CONFIGURE / EXTEND / CREATE / TASK_ONLY
```

Core runtime разрешает `REUSE`, `CONFIGURE` и `TASK_ONLY`. `EXTEND` и `CREATE` требуют hardening evaluation/activation route и не должны подменяться сгенерированным DRAFT skill.

`.harness/skills/registry.yaml` является generated index. Source of truth — exact skill revisions/digests в distribution или project-local lifecycle directories.

Storage должен поддерживать все lifecycle values: `DRAFT`, `VALIDATING`, `VALIDATED`, `REJECTED`, `ACTIVE`, `SUSPENDED`, `DEPRECATED`, `RETIRED`, а также отдельные `EVALUATIONS` и `MIGRATIONS`.

Product Task получает ровно один ACTIVE primary skill. Bootstrap требует завершённый Skill Gap Analysis; он не требует заранее завершить полный authoring lifecycle, если первая Task уже покрывается ACTIVE seed skill.

### 13. Критерии приёмки

1. Skill Registry различает universal/profile/project scopes.
2. Новый skill создаётся только после reuse/configure/extend analysis.
3. Primary skill ровно один на task.
4. `ACTIVE` требует readiness/evaluation PASS.
5. Skill capabilities минимальны и не расширяют Task Contract.
6. Skill update инвалидирует будущие prompt plans, но не history.
7. Project-local structure содержит registry and lifecycle directories.
8. Одноразовая работа остаётся Task Contract, а не skill.

---

<!-- SOURCE: 12_Implementation_Specifications/15_Codex_Agent_Adapter.md -->

## Codex Agent Adapter

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Codex является первым целевым agent executor, но не частью universal kernel. Harness подготавливает task, prompt, context, skills, permissions и verification; Codex выполняет bounded work и возвращает structured result.

Разделение ответственности:

```text
Harness decides what, why, scope, readiness and permissions.
Codex decides how to implement within that bounded contract.
Harness validates, records and selects the next route.
```

### 2. Что Codex получает

Codex Adapter передаёт:

- immutable Task Contract revision;
- Work Package purpose;
- accepted requirement/constraint/ADR/documentation refs;
- exact input artifacts;
- read/write/forbidden scope;
- active skill procedure;
- capability grants;
- verification profile and commands;
- material ambiguity stop protocol;
- structured output schema;
- current repository/worktree revision.

Codex не должен получать весь project archive без Context Plan.

### 3. Что Codex не решает

Codex не имеет права самостоятельно:

- выбирать следующую task;
- менять Project Definition or accepted scope;
- принимать material ADR;
- менять Technology Baseline;
- расширять write scope;
- выдавать себе capabilities;
- выполнять push/deploy/publication без grant;
- ослаблять hard constraint;
- скрывать failed verification;
- объявлять Work Package completed.

При необходимости такого решения Codex возвращает `NEEDS_DECISION` или blocker.

### 4. Adapter Profile

```yaml
agent_adapter_profile:
  id: ADP-CODEX
  revision: 1
  status: ACTIVE

  supported_input:
    prompt_bundle_versions: [1]
    context_packet_versions: [1]
    task_contract_versions: [1]

  supported_output:
    schema_ref: SCHEMA-AGENT-TASK-RESULT@1
    structured_mode: REQUIRED

  capabilities:
    filesystem_read: true
    filesystem_write: true
    command_execute: true
    network: POLICY_GATED
    git_commit: POLICY_GATED
    git_push: false
    deploy: false

  guidance:
    project_file: AGENTS.md
    max_nested_guidance_depth: 4

  stop_signal_mapping: {}
  error_mapping: {}
  compatibility_suite_ref: EVS-ADP-CODEX@1
```

### 5. Adapter execution protocol

```text
1. Verify Task/Prompt/Context/Grant revisions.
2. Create or attach isolated worktree/workspace.
3. Render compiled bundle into Codex-native request.
4. Start Run and emit trace event.
5. Mediate every tool invocation through adapters/grants.
6. Monitor actual writes and stop conditions.
7. Receive structured Agent Task Result.
8. Normalize errors and blocker signals.
9. Run independent Harness verification where required.
10. Persist Run Trace, Evidence and Result Envelope.
```

### 6. Codex Task Result Contract

```yaml
agent_task_result:
  schema_version: 1
  task_ref: TSK-BE-SEARCH-030@1
  run_ref: RUN-20260806-0012

  execution_status: COMPLETED
  summary: "Реализован search service по CNT-SEARCH@2"

  changes:
    added: []
    modified:
      - src/backend/search/service.ts
    removed: []

  commands_executed:
    - command_ref: CMD-TEST-SEARCH
      result: PASS

  verification_claims:
    - criterion_ref: AC-SEARCH-BE-001
      result: PASS
      evidence_hint: "targeted tests"

  documentation_changes:
    - docs/implementation/backend-search.md

  assumptions: []
  questions: []
  blockers: []
  warnings: []

  next_step_hint:
    type: INTEGRATION_READY
```

Claims Codex не являются финальным evidence, пока Harness validator не подтвердит их.

### 7. AGENTS.md

Harness генерирует короткий `AGENTS.md` для cold start:

- project identity and current baseline refs;
- как найти `.harness/` state;
- запрет выбирать tasks вне assigned contract;
- правила scope, decisions, blockers and result schema;
- команды проверки состояния;
- ссылки на более узкие nested guidance.

`AGENTS.md` не копирует всю документацию и не содержит mutable current task. Current task передаётся через bundle/context.

### 8. Tool mediation

Даже если Codex технически умеет вызывать shell или Git, Harness Tool Adapter проверяет:

- capability grant;
- target path/system;
- command policy;
- timeout;
- environment lease;
- actual writes;
- sensitive data egress;
- idempotency and side-effect class.

Direct unmanaged tool access считается unsupported execution mode для governed runs.

### 9. Stop conditions

Codex обязан остановиться и вернуть structured signal при:

```text
MATERIAL_AMBIGUITY
MISSING_REQUIRED_ARTIFACT
SCOPE_EXPANSION_REQUIRED
HARD_CONSTRAINT_CONFLICT
UNEXPECTED_PUBLIC_CONTRACT_CHANGE
UNSAFE_OR_IRREVERSIBLE_SIDE_EFFECT
CAPABILITY_DENIED
BASE_REVISION_CHANGED
VERIFICATION_ENVIRONMENT_BROKEN
```

Небольшая обратимая implementation detail обрабатывается по project ambiguity mode.

### 10. Verification separation

Codex может запускать targeted tests, но Harness:

- independently validates result schema;
- compares actual diff to declared scope;
- checks baseline/new failures;
- verifies documentation impact;
- computes task completion;
- chooses next route.

Для high-risk tasks Validator может быть отдельным run/agent or deterministic toolchain.

### 11. Errors and resume

Provider/agent-specific ошибки нормализуются:

```text
ADAPTER_UNAVAILABLE
SESSION_TERMINATED
MALFORMED_OUTPUT
TOOL_PERMISSION_DENIED
CONTEXT_REJECTED
COMMAND_TIMEOUT
AGENT_SCOPE_VIOLATION
```

Retry создаёт новый Run и новый bundle при изменившихся inputs. Harness не предполагает, что внутренняя память Codex session является canonical state.

### 12. Security and provenance

Adapter trace фиксирует:

- adapter/profile revision;
- rendered bundle digest;
- context packet digests;
- capability grants;
- tool calls;
- actual writes;
- normalized output digest.

Secrets передаются только через reference-based tool mechanism и не включаются в prompt text без explicit policy.

### 13. Browser handoff и local runtime v0.4.1

Browser GPT не является Codex Agent Adapter. Он готовит semantic input и вызывает deterministic `prepare`.

Codex получает self-contained handoff с `CODEX_START.md`, `NEXT_TASK.yaml`, current Prompt Bundle, Context Packet, Verification Profile и embedded runtime.

Normative local loop:

```bash
python .harness/engine/project-harness.py validate-handoff --project .
python .harness/engine/project-harness.py status --project .
python .harness/engine/project-harness.py next --project .
python .harness/engine/project-harness.py verify --project . --allow-command-execution
python .harness/engine/project-harness.py complete --project . --result <agent-result>
```

Codex не выбирает следующую Task, не меняет accepted baselines и не расширяет declared scope. После начала product changes initial manifest больше не отражает mutable tree; применяется `validate-project`.

Core adapter является handoff/protocol adapter и не обещает provider-specific automatic dispatch. Автоматический вызов Codex CLI/API относится к hardening и обязан сохранять те же contracts, observed-diff verification и Run-as-attempt semantics.

Команды запускаются без shell, в проверенном cwd, с timeout и сокращённым environment. Это не OS-level sandbox: network/process isolation и запрет writes вне repository обеспечиваются контейнером, VM или эквивалентным внешним boundary.

### 14. Критерии приёмки

1. Codex получает один bounded Task Contract и понимает purpose/result/verification.
2. Codex не выбирает governance decisions or next task.
3. Tool calls проходят через grants and scope checks.
4. Structured output обязателен и schema-valid.
5. Harness independently подтверждает claims and completion.
6. Material ambiguity вызывает stop signal, а не скрытый выбор.
7. Cold start восстанавливается из canonical state, не из памяти session.
8. Adapter version and provenance присутствуют в Run Trace.

---

<!-- SOURCE: 12_Implementation_Specifications/16_Harness_Maintenance_Plane.md -->

## Изолированный Harness Maintenance Plane

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Пользователь должен иметь возможность одним natural-language запросом изменить маршрутизацию, prompt modules, skills, schemas или другие элементы Harness. Такое изменение не должно смешиваться с текущей feature development и не должно незаметно менять правила уже выполняемой задачи.

### 2. Три плоскости изменений

```text
PRODUCT
PROJECT_CONTROL
HARNESS_DISTRIBUTION
```

| Plane | Что изменяет | Пример |
|---|---|---|
| `PRODUCT` | Код, инфраструктуру, данные, документацию создаваемого проекта. | Добавить endpoint. |
| `PROJECT_CONTROL` | `.harness/` конкретного проекта: local routes, prompts, skills, policies, adapters. | Изменить project-specific skill. |
| `HARNESS_DISTRIBUTION` | Universal kernel, schemas, generic modules, profiles, adapters, migrations. | Добавить новый Request Class. |

Один Change Pack имеет ровно один `target_plane`. Mixed-plane пакет запрещён.

### 3. Maintenance Request

Natural-language запрос:

> Пропатчь маршрутизацию: bug-fix задачи должны сначала проверять наличие reproduction test.

Классифицируется как `PROJECT_CONTROL_MAINTENANCE` или `HARNESS_DISTRIBUTION_MAINTENANCE` в зависимости от scope. Harness показывает выбранный plane до применения.

### 4. Change Pack Contract

```yaml
change_pack:
  id: CHP-20260806-001
  revision: 1
  request_ref: RQ-20260806-0020

  kind: PROJECT_CONTROL_MAINTENANCE
  target_plane: PROJECT_CONTROL
  target_project_ref: project-example
  target_distribution_ref: null
  mixed_plane: FORBIDDEN

  objective: "Добавить reproduction gate для bug-fix routes"
  affected_entities:
    - SKL-PROJECT-BUG-FIX@2
    - PLC-ROUTING-BUG-FIX@1

  normalized_changes: []
  migration_plan_ref: MIG-CHP-001
  impact_analysis_ref: IMP-CHP-001
  evaluation_plan_ref: EVS-CHP-001
  rollback_plan_ref: RBP-CHP-001

  required_capabilities: [PROJECT_CONTROL_WRITE]
  status: PROPOSED
```

### 5. Maintenance lifecycle

```text
RECEIVED
→ QUARANTINED
→ ANALYZED
→ PROPOSED
→ VALIDATED
→ APPROVED
→ APPLIED
→ CANARY
→ ACTIVE
```

Альтернативные lifecycle outcomes:

```text
REJECTED
ROLLED_BACK
FAILED_RECOVERABLE
```

Отдельное поле `compensation_status` может иметь `PARTIALLY_COMPENSATED`; это не lifecycle status Change Pack.

`QUARANTINED` означает, что входящий patch не влияет на active runtime до validation/approval.

Определение `kind` и `target_plane` выполняется при приёме, но не создаёт отдельный lifecycle status `CLASSIFIED`.

### 6. Протокол применения

```text
1. Resolve target plane and scope.
2. Snapshot current control/distribution revision.
3. Parse requested semantic change.
4. Produce normalized Change Pack.
5. Run impact analysis over routes, tasks, skills, prompts, schemas and migrations.
6. Build migration and rollback plans.
7. Apply changes in isolated maintenance workspace.
8. Run structural, behavioral, adversarial and compatibility suites.
9. Ask approval for material semantics.
10. Activate through atomic pointer/version switch where possible.
11. Mark affected future plans/tasks stale.
12. Observe canary and rollback on policy threshold.
```

### 7. Project Control Maintenance

Может изменять только project-local:

- routing policies;
- Prompt Modules/Specs;
- project skills;
- Context Policies;
- verification profiles;
- adapter configuration;
- project schemas/extensions;
- generated guidance templates.

Не может изменять universal semantics или schemas без distribution migration. Не может одновременно менять product code.

### 8. Harness Distribution Maintenance

Может изменять:

- kernel behavior;
- core contracts and registries;
- universal profiles;
- generic prompts and skills;
- adapters;
- migrations;
- semantic validator;
- release packaging.

Требует:

- `HARNESS_DISTRIBUTION_WRITE` capability;
- отдельного repository/worktree;
- version bump;
- migration and compatibility declaration;
- cross-profile regression;
- distribution archive integrity check;
- rollback/reinstall path.

### 9. Влияние на текущую разработку

Active run использует immutable bundle и grants. Maintenance activation:

- не меняет уже завершённый или выполняющийся bundle;
- может запретить дальнейшие tool calls только при emergency security policy;
- помечает queued plans `STALE`;
- пересчитывает READY tasks;
- показывает affected Work Packages;
- не изменяет product files.

При emergency suspension создаётся explicit event и Result Envelope, а не скрытая остановка.

### 10. One-prompt patch UX

Пользователь может сформулировать изменение одним сообщением. Harness обязан сам:

- определить target plane;
- показать scope;
- задать вопрос только при material ambiguity;
- создать Change Pack;
- провести проверки;
- вернуть, что изменено в routes/prompts/skills/schemas;
- перечислить invalidated tasks/plans;
- дать rollback reference.

«Одним промтом» означает один пользовательский request, но не отменяет внутренних этапов validation и approval.

### 11. Evaluation requirements

Для routing/prompt/skill change обязательны:

- structural schema checks;
- positive route fixtures;
- negative/misrouting fixtures;
- material ambiguity fixture;
- scope/permission adversarial fixture;
- representative project profile fixtures;
- old-version compatibility or migration fixture;
- canary outcome comparison.

### 12. Rollback

Rollback восстанавливает previous active revision/pointer. Он не удаляет history:

```yaml
rollback_result:
  change_pack_ref: CHP-20260806-001
  restored_revision: sha256:...
  compensation_status: COMPLETE
  affected_runs: []
  affected_queued_tasks: [TSK-FIX-020]
```

Если migration необратима, Change Pack не может быть approved без explicit restore/forward-fix strategy.

### 13. Критерии приёмки

1. Product, Project Control и Distribution changes не смешиваются.
2. Один пользовательский request создаёт isolated Change Pack.
3. Active runs не переписываются после activation.
4. Future prompt plans/tasks инвалидируются детерминированно.
5. Routing/prompt/skill changes проходят behavioral and negative fixtures.
6. Material semantics требуют approval.
7. Rollback and migration всегда определены.
8. Result Envelope показывает scope, изменения, проверки и affected routes.

---

<!-- SOURCE: 12_Implementation_Specifications/17_Documentation_Layers_and_Minimal_Mode.md -->

## Слои документации и режимы materialization

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Harness использует богатую machine-readable модель, но пользователь и Codex не должны постоянно читать десятки внутренних сущностей. Документация разделяется на понятный human layer и machine/control layer.

### 2. Human-readable layer

Рекомендуемый минимум проекта:

```text
PROJECT.md
ARCHITECTURE.md
TECHNOLOGY.md
ROADMAP.md
STATUS.md
DECISIONS/
TASK_REPORTS/
```

| Документ | Содержание |
|---|---|
| `PROJECT.md` | Цели, пользователи, scope, ограничения, success criteria. |
| `ARCHITECTURE.md` | Компоненты, границы, потоки, contracts и links to ADR. |
| `TECHNOLOGY.md` | Принятый stack, versions, compatibility and rationale. |
| `ROADMAP.md` | Work Packages, causal layers, milestones and current route. |
| `STATUS.md` | Что сделано, что blocked, next step, outstanding decisions. |
| `DECISIONS/` | Material ADR. |
| `TASK_REPORTS/` | Краткие проверяемые результаты выполненных задач. |

Эти документы генерируются или синхронизируются из canonical state, но допускают curated explanatory text с source mapping.

### 3. Machine/control layer

```text
.harness/
├── config/
├── registries/
├── intake/
├── canonical/
├── work-packages/
├── tasks/
├── prompts/
├── context/
├── skills/
├── runs/
├── evidence/
├── blockers/
├── changes/
├── events/
├── state/
└── generated/
```

`.harness/` является control plane. Пользователь обычно взаимодействует через single entry and generated views, а не редактирует state вручную.

### 4. Documentation modes

```text
MINIMAL
STANDARD
MULTI_REPO
REGULATED
```

#### 4.1. MINIMAL

Для небольшого проекта:

- `PROJECT.md` объединяет project definition and basic technology;
- `ARCHITECTURE.md` только при material architecture;
- `ROADMAP.md` и `STATUS.md` обязательны;
- ADR только для material decisions;
- machine contracts сохраняются полностью;
- task reports могут агрегироваться по Work Package.

#### 4.2. STANDARD

Default:

- все базовые human documents;
- отдельные ADR;
- task reports для executable tasks;
- requirements/coverage views;
- full trace/evidence digests.

#### 4.3. MULTI_REPO

Добавляет:

- repository map;
- ownership and cross-repo contracts;
- coordinated change sets;
- integration/release order;
- per-repository status views.

#### 4.4. REGULATED

Добавляет:

- formal approvals;
- stricter retention;
- data classification and audit exports;
- waiver register;
- independent validation and separation of duties;
- controlled document revisions.

Режим влияет на количество materialized views/gates, но не ослабляет semantics Task Contract, constraints, evidence или permissions.

### 5. Source of truth

```text
Canonical machine entity
→ human-readable synchronized document
→ generated summary/status
```

Generated `STATUS.md` или combined guide не становится canonical source. Ручное изменение generated file либо запрещается, либо импортируется как Change Pack candidate.

### 6. Избежание дублирования

Нормативное правило определяется один раз и переиспользуется ссылкой. Например, запрет billing/token accounting хранится в scope/non-goals и schema tests, а не копируется в каждом документе.

Documentation build должен поддерживать:

- transclusion/concatenation для общего руководства;
- source maps;
- link/anchor validation;
- duplicate normative statement warnings;
- version and metadata generation.

### 7. Общая пользовательская документация

Комплект публикует два агрегата:

```text
Project_Harness_User_and_Implementation_Guide_v0.4.1.md
Project_Harness_Architecture_v0.4.1_FULL.md
```

Первый объединяет реализационные спецификации 01–21. Второй объединяет весь комплект. Оба генерируются, а не редактируются независимо.

### 8. Generated project views

После intake Harness создаёт:

```text
PROJECT.md          accepted definition and assumptions
ARCHITECTURE.md     accepted architecture and contracts
TECHNOLOGY.md       accepted stack and compatibility
ROADMAP.md          work packages and DAG layers
STATUS.md           current result, blockers and next route
AGENTS.md           compact executor guidance
```

Каждый generated view содержит:

- generated timestamp;
- source revision/hash;
- «do not edit directly» marker либо import policy;
- source entity refs.

### 9. Пользовательский язык

Human layer обязан:

- объяснять термины при первом использовании;
- показывать последствия вариантов;
- не требовать знания internal enums;
- отделять «принято», «предполагается» и «неизвестно»;
- показывать current status and next step в начале `STATUS.md`;
- не скрывать blockers за техническим stack trace.

### 10. Документирование мелких задач

Мелкая task не обязана создавать новый Markdown-файл. Достаточно:

- Task Report record;
- обновления существующего раздела, если impact есть;
- event/evidence;
- generated status refresh.

Это предотвращает избыточное число документов.

### 11. Build pipeline

```text
Validate canonical schemas
→ resolve registries and references
→ render human views
→ render combined guides
→ validate links/anchors/examples
→ run semantic documentation tests
→ generate FILE_INDEX and checksums
→ package archive
```

### 12. Критерии приёмки

1. Human layer понятен без просмотра `.harness/` internals.
2. Machine layer сохраняет полную traceability.
3. MINIMAL не меняет core semantics.
4. Общие руководства генерируются из отдельных files.
5. Нормативные правила не дублируются бесконтрольно.
6. Generated views имеют source revisions/maps.
7. Мелкие tasks не создают искусственные документы.
8. STATUS всегда содержит текущий результат, blockers and exact next route.

---

<!-- SOURCE: 12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md -->

## Единые registries, lifecycles и нормализация contracts

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Profiles, ID prefixes, statuses, request classes и capability values не должны определяться независимо в разных документах. В реализации они загружаются из versioned machine-readable registries до parsing, planning, compilation и semantic validation.

Canonical files:

```text
registries/id_prefixes.yaml
registries/project_profiles.yaml
registries/statuses.yaml
registries/request_routing.yaml
registries/capabilities.yaml
registries/contracts.yaml
```

### 2. Registry loading contract

```text
Load distribution manifest
→ verify registry hashes/signature
→ validate registry schemas
→ reject duplicate keys/prefixes
→ build immutable runtime registry view
→ load project extension registries
→ verify namespace and compatibility
→ allow document/schema parsing
```

Registry load failure is a startup blocker. Runtime must not silently substitute hard-coded values.

### 3. Project Profile Registry

Baseline v1:

```text
BASE_SOFTWARE
WEB_APPLICATION
API_SERVICE
MOBILE_APPLICATION
DESKTOP_APPLICATION
CLI_TOOL
LIBRARY
DATA_PIPELINE
ML_SYSTEM
INFRASTRUCTURE
EMBEDDED_SYSTEM
AUTOMATION
MULTI_SERVICE_SYSTEM
CUSTOM
```

- `BASE_SOFTWARE` — neutral baseline when no more specific primary profile exists.
- Profiles may compose through registered extensions.
- Overview, questionnaire, profile matrix, MVP and schema enums are generated from the same registry.
- `CUSTOM` requires explicit extension namespace/schema; it is not a free-form escape hatch.

### 4. ID Prefix Registry

| Prefix | Entity | Schema key |
|---|---|---|
| `AC` | Acceptance Criterion | `acceptance_criterion` |
| `ACT` | Actor or role binding | `actor` |
| `ADP` | Executor/agent adapter profile | `adapter_profile` |
| `ADR` | Architecture or material Decision Record | `adr` |
| `ANS` | Questionnaire answer | `answer` |
| `ARB` | Architecture Baseline | `architecture_baseline` |
| `ART` | Generic produced artifact | `artifact` |
| `ASM` | Assumption | `assumption` |
| `BFB` | Brownfield Baseline | `brownfield_baseline` |
| `BFI` | Brownfield Intake | `brownfield_intake` |
| `BLK` | Blocker | `blocker` |
| `BRI` | Brownfield route item | `brownfield_route_item` |
| `BST` | Bootstrap Plan | `bootstrap_plan` |
| `CCS` | Coordinated multi-repository change set | `coordinated_change_set` |
| `CFA` | Conflict analysis | `conflict_analysis` |
| `CGR` | Capability Grant | `capability_grant` |
| `CHK` | Verification or policy check | `check` |
| `CHP` | Change Pack | `change_pack` |
| `CMD` | Command descriptor | `command` |
| `CMP` | Compatibility result or matrix | `compatibility` |
| `CNF` | Source/semantic conflict | `conflict` |
| `CNT` | Canonical product or integration contract | `contract` |
| `COR` | Correlation context | `correlation` |
| `CPB` | Compiled Prompt Bundle | `compiled_prompt_bundle` |
| `CPK` | Context Packet | `context_packet` |
| `CPL` | Commit Plan | `commit_plan` |
| `CST` | Constraint | `constraint` |
| `CTP` | Context Policy | `context_policy` |
| `CTX` | Context Plan | `context_plan` |
| `DAG` | Dependency graph | `dependency_graph` |
| `DEC` | Decision | `decision` |
| `DOC` | Documentation record or stable section | `documentation_record` |
| `ENV` | Logical execution environment resource | `environment_resource` |
| `EVD` | Evidence | `evidence` |
| `EVS` | Evaluation Suite | `evaluation_suite` |
| `EVT` | State or audit Event | `event` |
| `GATE` | Readiness or approval Gate | `gate` |
| `GOL` | Goal | `goal` |
| `HNS` | Documentation-level Harness requirement | `documentation_requirement` |
| `IMP` | Impact Analysis | `impact_analysis` |
| `IMPL` | Implementation artifact | `implementation_artifact` |
| `INV` | Invariant | `invariant` |
| `LOCK` | Shared lock or lockfile resource | `lock_resource` |
| `LSE` | Ownership or environment Lease | `lease` |
| `MIG` | Migration | `migration` |
| `OPT` | Decision, blocker, or recovery Option | `option` |
| `OUT` | Outcome | `outcome` |
| `PBT` | Parallel Batch | `parallel_batch` |
| `PJD` | Project Definition | `project_definition` |
| `PLC` | Policy | `policy` |
| `PMD` | Prompt Module | `prompt_module` |
| `PPL` | Prompt Plan | `prompt_plan` |
| `PRF` | Project Profile | `project_profile` |
| `PSP` | Prompt Spec | `prompt_spec` |
| `QNS` | Questionnaire Session | `questionnaire_session` |
| `QST` | Question | `question` |
| `QUA` | Quality Attribute | `quality_attribute` |
| `RBP` | Rollback or compensation Plan | `rollback_plan` |
| `REG` | Versioned Registry | `registry` |
| `REP` | Repository | `repository` |
| `REQ` | Requirement | `requirement` |
| `RES` | Public Result Envelope | `result_envelope` |
| `RIV` | Repository Inventory | `repository_inventory` |
| `RNP` | Run Plan | `run_plan` |
| `RQ` | Request | `request` |
| `RQP` | Request Plan | `request_plan` |
| `RTE` | Route | `route` |
| `RUN` | Run; one immutable execution attempt | `run` |
| `SCHEMA` | Schema identifier | `schema` |
| `SCP` | Scope definition | `scope` |
| `SEM` | Semantic documentation validation rule | `semantic_rule` |
| `SES` | User or intake Session | `session` |
| `SIV` | Source Inventory | `source_inventory` |
| `SKL` | Skill | `skill` |
| `SMP` | Source Map | `source_map` |
| `SPN` | Trace Span | `trace_span` |
| `SRC` | Source | `source` |
| `SUC` | Success Criterion | `success_criterion` |
| `SVC` | Shared/external service resource | `service_resource` |
| `TAD` | Tool Adapter | `tool_adapter` |
| `TBL` | Technology Baseline | `technology_baseline` |
| `TCN` | Technology Candidate | `technology_candidate` |
| `TEC` | Technology reference | `technology` |
| `TEN` | Test Environment contract | `test_environment` |
| `TEST` | Test Case | `test_case` |
| `TIV` | Tool Invocation | `tool_invocation` |
| `TRP` | Task Report | `task_report` |
| `TRT` | Request Trace | `request_trace` |
| `TSB` | Test Baseline | `test_baseline` |
| `TSK` | Atomic Task | `task` |
| `UNK` | Unknown | `unknown` |
| `VAL` | Validation run/report | `validation` |
| `VFP` | Verification Profile | `verification_profile` |
| `WP` | Work Package | `work_package` |
| `WVR` | Waiver | `waiver` |

`SHA-256` and enum names such as `SIDE-EFFECT` are not entity IDs and are excluded by the ID parser. Prefix cannot have two meanings. Project extensions use a registered namespace and collision check.

### 5. Normalized context and Git prefixes

Чтобы исключить collision:

```text
CTP = Context Policy
CTX = Context Plan
CPK = Context Packet
CPL = Commit Plan
```

Capability Grant uses `CGR`; Lease uses `LSE`; Project Definition uses `PJD`; Evidence uses `EVD`; State Event uses `EVT`.

### 6. Run и Attempt

Отдельная canonical entity `Attempt` отсутствует. Каждый `Run` — одна immutable execution attempt:

```yaml
run:
  id: RUN-20260806-0012
  task_ref: TSK-BE-SEARCH-030@1
  attempt_no: 2
  previous_run_ref: RUN-20260806-0011
  status: PLANNED
```

```text
Task → Run #1 → Run #2
```

Tool Invocations принадлежат Run. Retry всегда создаёт новый Run; существующий Run не изменяется в новую попытку.

### 7. Run Plan Contract

```yaml
run_plan:
  id: RNP-RUN-20260806-0012
  revision: 1
  task_ref: TSK-BE-SEARCH-030@1
  request_ref: RQ-20260806-0004
  work_package_ref: WP-SEARCH-001@1

  base_revisions:
    project: sha256:...
    repository: sha256:...
    task: sha256:...

  prompt_bundle_ref: CPB-RUN-20260806-0012
  context_packet_refs: [CPK-TSK-BE-SEARCH-030-R2]
  adapter_ref: ADP-CODEX@1
  capability_grant_refs: [CGR-RUN-0012]
  lease_refs: [LSE-WT-0012]
  verification_profile_ref: VFP-CODE-TARGETED-001@1
  side_effect_class: REVERSIBLE
  idempotency_key: sha256:...
  status: READY
```

Run Plan имеет собственный schema/storage path и создаётся после readiness, compatibility and permission checks.

### 8. Lifecycle Status Registry

Normative values находятся в `registries/statuses.yaml`. Основные группы:

Ниже приведена generated matrix полного registry; ручное изменение этой таблицы без изменения YAML запрещено.

<!-- REGISTRY-MATRIX: statuses -->
| Status group | Допустимые значения |
|---|---|
| `public_result` | `ANSWERED`, `COMPLETED`, `PARTIAL`, `WAITING_DECISION`, `BLOCKED`, `FAILED_RECOVERABLE`, `NO_ACTION`, `CANCELLED` |
| `request` | `RECEIVED`, `CLASSIFYING`, `CLASSIFIED`, `PLANNING`, `PLANNED`, `READY`, `EXECUTING`, `WAITING_USER_INPUT`, `WAITING_APPROVAL`, `PARTIAL`, `BLOCKED`, `FAILED_RECOVERABLE`, `COMPLETED`, `CANCELLED`, `SUPERSEDED` |
| `questionnaire_session` | `CREATED`, `SOURCE_PENDING`, `ANALYZING_SOURCES`, `QUESTIONING`, `DRAFT_READY`, `WAITING_CONFIRMATION`, `ACCEPTED`, `CANCELLED`, `SUPERSEDED` |
| `session` | `CREATED`, `ACTIVE`, `WAITING_INPUT`, `WAITING_DECISION`, `READY`, `COMPLETED`, `BLOCKED`, `CANCELLED`, `SUPERSEDED` |
| `project_definition` | `DRAFT`, `PROPOSED`, `WAITING_DECISION`, `ACCEPTED`, `STALE`, `SUPERSEDED` |
| `architecture_baseline` | `DRAFT`, `PROPOSED`, `ACCEPTED`, `ACTIVE`, `STALE`, `SUPERSEDED` |
| `work_package` | `DRAFT`, `PLANNED`, `READY`, `IN_PROGRESS`, `PARTIAL`, `BLOCKED`, `COMPLETED`, `CANCELLED`, `SUPERSEDED` |
| `task` | `DRAFT`, `PLANNED`, `READY`, `CLAIMED`, `RUNNING`, `VERIFYING`, `DONE`, `BLOCKED`, `FAILED_RECOVERABLE`, `SPLIT`, `STALE`, `CANCELLED`, `SUPERSEDED` |
| `run_plan` | `DRAFT`, `READY`, `STALE`, `CANCELLED` |
| `run` | `PLANNED`, `READY`, `RUNNING`, `VERIFYING`, `SUCCEEDED`, `FAILED_RETRYABLE`, `FAILED_NON_RETRYABLE`, `BLOCKED`, `CANCELLED`, `TIMED_OUT` |
| `prompt_module` | `DRAFT`, `VALIDATED`, `ACTIVE`, `DEPRECATED`, `RETIRED` |
| `prompt_spec` | `DRAFT`, `VALIDATED`, `ACTIVE`, `DEPRECATED`, `RETIRED` |
| `prompt_plan` | `PLANNED`, `RESOLVED`, `CONSUMED`, `STALE`, `CANCELLED` |
| `compiled_prompt_bundle` | `COMPILED`, `DISPATCHED`, `EXECUTED`, `EXPIRED`, `CANCELLED` |
| `context_plan` | `DRAFT`, `READY`, `CONSUMED`, `STALE`, `CANCELLED` |
| `context_packet` | `GENERATED`, `BOUND`, `CONSUMED`, `STALE`, `EXPIRED` |
| `skill` | `DRAFT`, `VALIDATING`, `VALIDATED`, `REJECTED`, `ACTIVE`, `SUSPENDED`, `DEPRECATED`, `RETIRED` |
| `technology_baseline` | `DRAFT`, `PROPOSED`, `ACCEPTED`, `ACTIVE`, `STALE`, `SUPERSEDED` |
| `lease` | `REQUESTED`, `ACTIVE`, `RELEASED`, `EXPIRED`, `REVOKED` |
| `verification` | `NOT_RUN`, `RUNNING`, `PASS`, `FAIL`, `BLOCKED`, `NOT_APPLICABLE` |
| `change_pack` | `RECEIVED`, `QUARANTINED`, `ANALYZED`, `PROPOSED`, `VALIDATED`, `APPROVED`, `APPLIED`, `CANARY`, `ACTIVE`, `REJECTED`, `ROLLED_BACK`, `FAILED_RECOVERABLE` |
| `compensation` | `NOT_REQUIRED`, `PENDING`, `COMPLETE`, `PARTIALLY_COMPENSATED`, `FAILED` |
| `blocker` | `OPEN`, `MITIGATING`, `RESOLVED`, `SUPERSEDED` |
| `request_plan` | `DRAFT`, `PLANNED`, `READY`, `EXECUTING`, `PARTIAL`, `BLOCKED`, `COMPLETED`, `STALE`, `CANCELLED`, `SUPERSEDED` |
| `question` | `DRAFT`, `OPEN`, `ANSWERED`, `SKIPPED`, `CANCELLED`, `SUPERSEDED` |
| `adr` | `DRAFT`, `PROPOSED`, `WAITING_DECISION`, `ACCEPTED`, `REJECTED`, `SUPERSEDED` |
| `decision` | `ACCEPTED`, `REJECTED`, `SUPERSEDED` |
| `adapter_profile` | `DRAFT`, `VALIDATED`, `ACTIVE`, `SUSPENDED`, `DEPRECATED`, `RETIRED` |
| `bootstrap_plan` | `DRAFT`, `PROPOSED`, `APPROVED`, `EXECUTING`, `COMPLETED`, `BLOCKED`, `FAILED_RECOVERABLE`, `STALE`, `CANCELLED`, `SUPERSEDED` |
| `brownfield_intake` | `CREATED`, `SOURCE_PENDING`, `INVENTORY_PENDING`, `INVENTORY_READY`, `RECONCILING`, `BASELINE_PROPOSED`, `WAITING_APPROVAL`, `ACCEPTED`, `BLOCKED`, `CANCELLED`, `SUPERSEDED` |
| `brownfield_baseline` | `DRAFT`, `PROPOSED`, `ACCEPTED`, `STALE`, `SUPERSEDED` |
| `brownfield_route_item` | `PROPOSED`, `ACCEPTED`, `DEFERRED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `SUPERSEDED` |
| `conflict` | `OPEN`, `ANALYZING`, `RESOLVED`, `ACCEPTED_AS_RISK`, `SUPERSEDED` |
| `constraint` | `DRAFT`, `PROPOSED`, `ACTIVE`, `WAIVED`, `RETIRED`, `SUPERSEDED` |
| `parallel_batch` | `DRAFT`, `PLANNED`, `READY`, `IN_PROGRESS`, `INTEGRATING`, `PARTIAL`, `BLOCKED`, `COMPLETED`, `STALE`, `CANCELLED`, `SUPERSEDED` |
| `project_profile` | `DRAFT`, `PROPOSED`, `CONFIRMED`, `ACTIVE`, `STALE`, `SUPERSEDED` |
| `requirement` | `DRAFT`, `PROPOSED`, `ACCEPTED`, `REJECTED`, `STALE`, `SUPERSEDED` |
| `test_environment` | `DRAFT`, `PROVISIONING`, `READY`, `IN_USE`, `STALE`, `FAILED`, `RETIRED` |
| `tool_invocation` | `PLANNED`, `RUNNING`, `SUCCESS`, `FAILED`, `BLOCKED`, `CANCELLED`, `TIMED_OUT` |
| `verification_profile` | `DRAFT`, `VALIDATED`, `ACTIVE`, `DEPRECATED`, `RETIRED` |
| `waiver` | `PROPOSED`, `ACTIVE`, `EXPIRED`, `REVOKED`, `SUPERSEDED` |
| `implementation_stage` | `PLANNED`, `ACTIVE`, `VERIFYING`, `ACCEPTED`, `BLOCKED`, `SUPERSEDED` |
| `project_execution` | `ACTIVE`, `BLOCKED`, `TARGET_LEVEL_REACHED`, `CANCELLED` |
| `sandbox_profile` | `DRAFT`, `VALIDATED`, `ACTIVE`, `SUSPENDED`, `DEPRECATED`, `RETIRED` |
<!-- /REGISTRY-MATRIX -->

#### Request

```text
RECEIVED, CLASSIFYING, CLASSIFIED, PLANNING, PLANNED,
READY, EXECUTING, WAITING_USER_INPUT, WAITING_APPROVAL,
PARTIAL, BLOCKED, FAILED_RECOVERABLE, COMPLETED,
CANCELLED, SUPERSEDED
```

#### Work Package

```text
DRAFT, PLANNED, READY, IN_PROGRESS, PARTIAL, BLOCKED,
COMPLETED, CANCELLED, SUPERSEDED
```

#### Task

```text
DRAFT, PLANNED, READY, CLAIMED, RUNNING, VERIFYING,
DONE, BLOCKED, FAILED_RECOVERABLE, SPLIT, STALE,
CANCELLED, SUPERSEDED
```

#### Run

```text
PLANNED, READY, RUNNING, VERIFYING, SUCCEEDED,
FAILED_RETRYABLE, FAILED_NON_RETRYABLE, BLOCKED,
CANCELLED, TIMED_OUT
```

#### Public Result

```text
ANSWERED, COMPLETED, PARTIAL, WAITING_DECISION,
BLOCKED, FAILED_RECOVERABLE, NO_ACTION, CANCELLED
```

#### Compensation

```text
NOT_REQUIRED, PENDING, COMPLETE, PARTIALLY_COMPENSATED, FAILED
```

#### Change Pack

```text
RECEIVED, QUARANTINED, ANALYZED, PROPOSED, VALIDATED,
APPROVED, APPLIED, CANARY, ACTIVE, REJECTED,
ROLLED_BACK, FAILED_RECOVERABLE
```

Prompt, Context, Skill, Technology Baseline, Lease and Questionnaire status groups are also defined in the machine registry.

### 9. Status semantics

- `COMPILED` belongs only to Compiled Prompt Bundle.
- `DONE` belongs to Task.
- `SUCCEEDED` belongs to Run.
- `COMPLETED` belongs to Request, Work Package or public Result.
- `PARTIALLY_COMPENSATED` belongs to compensation status only.
- `STALE` means invalidated input revision, not implementation failure.
- public Result status is a projection of internal lifecycle, not a replacement for it.

### 10. Request Routing Registry

Request Class, Request Mode and internal Operation are separate enum groups. Полный generated registry view:

<!-- REGISTRY-MATRIX: request_routing -->
```yaml
request_classes:
  - QUERY
  - PROJECT_START
  - DEVELOPMENT_REQUEST
  - PROJECT_EVOLUTION
  - PROJECT_CONTROL_MAINTENANCE
  - HARNESS_DISTRIBUTION_MAINTENANCE
  - CONTROL_REQUEST
request_modes:
  - READ_ONLY
  - PLAN
  - EXECUTE
internal_operations:
  - ANSWER
  - INSPECT_SOURCES
  - START_INTAKE
  - ASK_QUESTION_BATCH
  - RECONCILE_PROJECT
  - DEFINE_PROJECT
  - PROPOSE_ARCHITECTURE
  - BUILD_TECHNOLOGY_BASELINE
  - PREPARE_SKILLS
  - BOOTSTRAP_PROJECT
  - PLAN_WORK
  - COMPILE_TASK
  - RUN_TASK
  - VALIDATE_RESULT
  - UPDATE_DOCUMENTATION
  - RESUME_ROUTE
  - REPORT_STATUS
  - PUBLISH_CHANGE
  - APPLY_CHANGE_PACK
```
<!-- /REGISTRY-MATRIX -->

An operation such as `COMPILE_TASK` is never treated as user intent. `QUERY` does not create Tasks unless the user explicitly requests a side effect.

### 11. Capability Registry

Capability keys are deny-by-default. `PROJECT_CONTROL_WRITE` and `HARNESS_DISTRIBUTION_WRITE` are separate and cannot be implied by `FILESYSTEM_WRITE`. Unknown capability is denied.

<!-- REGISTRY-MATRIX: capabilities -->
```text
FILESYSTEM_READ
FILESYSTEM_WRITE
COMMAND_EXECUTE
NETWORK_READ
NETWORK_WRITE
SECRET_REFERENCE
MODEL_EXTERNAL_EGRESS
GIT_COMMIT
GIT_PUSH
PR_CREATE
EXTERNAL_SYSTEM_WRITE
DEPLOY
DATA_MIGRATE
DATA_DELETE
RELEASE_PUBLISH
PROJECT_CONTROL_WRITE
HARNESS_DISTRIBUTION_WRITE
```
<!-- /REGISTRY-MATRIX -->

### 12. Migration from v0.2

```text
REQST → RQ
DECMP → WP or a non-persistent decomposition step
ACTOR → ACT
PDF → PJD
CTXP → CTP
GRANT → CGR
LEASE → LSE
PRM → PSP/PMD/PPL depending on entity
ECP → CMP
EV evidence collision → EVD for Evidence, EVT for Event
Attempt entity → Run.attempt_no
contract_set → contract read/write sets
```

Aliases exist only in migration parser. New v0.3 generated artifacts must use canonical prefixes.

### 13. Contract completeness rule

Every persistent canonical entity must declare:

- schema key and schema version;
- ID prefix;
- lifecycle/status group;
- storage path;
- source/provenance fields;
- revision/hash semantics;
- authority and mutability;
- migration policy;
- reference examples;
- semantic validation rules.

If an entity is internal and non-persistent, documentation must explicitly say so.

### 14. Canonical Contract Catalog

`registries/contracts.yaml` классифицирует каждый standalone contract example как lifecycle-managed, immutable record или external config и связывает его с ID prefix, logical storage path и revision policy.

Нормализованные field rules:

| Entity | Канонические поля | Запрещённые aliases |
|---|---|---|
| `Request` | `idempotency_key` хранится в Request record; transport metadata отображается в это поле | отсутствие key при repeatable call |
| `Project Definition` | common `success_criterion_refs`; `DRAFT/PROPOSED` используют `scope` + `proposed_profile_refs`; `ACCEPTED` использует `scope_ref` + `profile_ref` + `accepted_by` | `success_criteria_refs`; смешение draft и accepted fields |
| `Task` | `documentation` object с `source_refs`, `impact`, `required_updates` | `documentation_refs` как альтернативная top-level schema |
| `Brownfield Baseline` | `accepted_actual_structure_ref` | `actual_structure_ref` |
| `Brownfield Route Item` | `estimated_risk` | `risk` |
| `Parallel Batch` | `lease_refs` | `leases` |
| `Change Pack` | `normalized_changes`, `required_capabilities` | `proposed_changes`, `requested_capabilities` |

Draft/accepted variants являются версиями одной schema, а не конкурирующими контрактами. Переход в `ACCEPTED` обязан нормализовать draft-only fields в accepted references.

### 15. Extension rules

Project/profile extensions:

- use an allocated namespace;
- may add values but cannot redefine baseline semantics;
- declare compatibility range;
- include migration and rollback;
- pass collision and schema validation;
- are recorded in Project Lock.

### 16. Критерии приёмки

1. All profile lists are generated from one registry.
2. ID prefix has exactly one meaning.
3. Request Plan and Run Plan have contracts and storage paths.
4. Run is one attempt; retry creates a new Run.
5. Status values are valid only for declared entity types.
6. `PARTIALLY_COMPENSATED` is not used as Change Pack lifecycle status.
7. Unknown enum/prefix breaks semantic validation.
8. Migration aliases do not appear in new generated artifacts.
9. Context and Commit prefixes do not collide.
10. Registry hashes are included in distribution validation and Project Lock.
11. Standalone contract examples match `contracts.yaml`, including lifecycle binding, ID prefix and canonical field names.

---

<!-- SOURCE: 12_Implementation_Specifications/19_Semantic_Documentation_Validation.md -->

## Semantic documentation validation

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Проверка ссылок и checksum недостаточна. Documentation CI должен обнаруживать смысловые расхождения: неизвестные enum, разные profile lists, entity без contract catalog binding, lifecycle/status mismatch, неканонические field aliases, capability вне registry, конфликтующие roadmap IDs и route без Result Envelope.

### 2. Validator pipeline

```text
Parse metadata and Markdown structure
→ load machine registries
→ extract declared entities/enums/contracts
→ resolve internal links and stable anchors
→ run semantic rules
→ build combined documents
→ compare generated/index/checksum outputs
→ emit Validation Report
```

### 3. Обязательные semantic rules

```text
SEM-001 Every declared enum value exists in a registry.
SEM-002 Every canonical entity has a schema or explicit internal-only marker.
SEM-003 Every lifecycle entity has allowed transitions.
SEM-004 Every persistent entity has a storage path and revision policy.
SEM-005 Every ID prefix exists and is unambiguous.
SEM-006 Every profile reference exists in Profile Registry.
SEM-007 Every generated artifact declares canonical sources and retention.
SEM-008 Every user-facing route returns Result Envelope.
SEM-009 Every executable task schema contains documentation and verification blocks.
SEM-010 Every required artifact has a producer or accepted external source.
SEM-011 Every material decision class maps to ADR/Decision policy.
SEM-012 Every blocker example contains options and resume condition.
SEM-013 Prompt artifact status matches its entity type.
SEM-014 No separate Attempt entity exists in v0.3 baseline.
SEM-015 Combined guides are generated from current source files.
SEM-016 Version/date metadata is consistent.
SEM-017 No broken relative links or duplicate stable section IDs.
SEM-018 No forbidden mixed-plane Change Pack example.
SEM-019 No provider billing/token accounting fields in core schemas.
SEM-020 Questionnaire and brownfield workflows lead to readiness gates.
SEM-021 Generated enum/matrix views exactly equal their machine registries.
SEM-022 Contract examples obey canonical fields and status-specific schema variants.
SEM-023 Every capability-bearing field resolves only to Capability Registry values.
SEM-024 Roadmap package IDs, names and dependencies are unique, aligned and acyclic.
SEM-025 Validation Report states the exact automated coverage and does not imply runtime conformance.
```

### 4. Severity

```text
ERROR
WARNING
INFO
```

- `ERROR` блокирует archive/release.
- `WARNING` требует explicit acknowledgement или issue.
- `INFO` показывает coverage/quality hints.

Unknown enum, broken link, mismatched combined guide, profile inconsistency и schema-less canonical entity являются `ERROR`.

### 5. Validation Report Contract

```yaml
validation_report:
  id: VAL-DOCS-20260807-001
  documentation_version: 0.5.0
  validator_version: 1.1.0
  source_tree_hash: sha256:...

  summary:
    errors: 0
    warnings: 0
    info: 3

  checks:
    - rule: SEM-006
      status: PASS
      evidence: "14 profile references resolved"

  generated_artifacts:
    - Project_Harness_User_and_Implementation_Guide_v0.5.0.md
    - Project_Harness_Architecture_v0.5.0_FULL.md
    - FILE_INDEX.md
    - MANIFEST.sha256

  result: PASS
```

### 6. Registry-driven extraction

Normative lists должны находиться либо:

- в machine-readable registry files при реализации;
- либо в одном designated Markdown registry section до появления code.

Остальные документы ссылаются на registry и могут показывать generated table. Validator сравнивает tables с source registry.

### 7. Contract example validation

YAML/JSON examples извлекаются по fenced code block markers и проверяются:

- syntax;
- required and forbidden canonical fields;
- status-specific draft/accepted variants;
- enum values;
- entity-specific ID prefix;
- references;
- lifecycle status applicability;
- capability values against `registries/capabilities.yaml`.

Illustrative ellipses `...` разрешены только в blocks, помеченных `illustrative: true`, либо исключённых explicit annotation.

### 8. Cross-document assertions

Примеры:

- profile count одинаков в overview and profile matrix;
- `COMPILED` не встречается как Prompt Plan status;
- `PARTIALLY_COMPENSATED` встречается только в compensation registry/fields;
- task lifecycle одинаков в planning, execution and contracts;
- user workflow references existing Request Classes;
- implementation roadmap begins with single-entry vertical slice;
- delivery roadmap and causal-sequence table use the same `WP-HARNESS-*` IDs and titles;
- roadmap dependencies reference existing packages and form an acyclic graph;
- project-local structure содержит `skills/`, `requests/`, `work-packages/` and traces.

### 9. Combined document generation

Combined guide не редактируется вручную. Generator:

1. читает index order;
2. вставляет source path markers;
3. нормализует heading levels;
4. сохраняет source path markers;
5. нормализует relative links к archive root;
6. сравнивает guide/full aggregate byte-for-byte с воспроизводимым output;
7. regenerates `FILE_INDEX.md` from current files;
8. fails CI при drift.

### 10. CI stages

```text
PR fast checks:
  metadata + links + registries + schemas + examples

Main/release checks:
  all semantic rules + combined build + checksums + archive integrity

Migration checks:
  old-version samples + alias mapping + regenerated views
```

### 11. Documentation coverage

Каждая implementation specification должна иметь:

- purpose;
- normative rules;
- contract/schema example;
- lifecycle/algorithm where applicable;
- error/blocker behavior;
- acceptance criteria;
- links to related canonical chapters.

Missing section является warning/error по configured completeness mode.

### 12. Reference validator interface

```text
python tools/validate_documentation.py <root>
  --zip <distribution.zip>
  --json <result.json>
  --write-report <VALIDATION_REPORT.md>
  --build-aggregates
```

Reference implementation reports validator version `1.1.0`, validates manifest automatically and verifies ZIP only when `--zip` is supplied. Отсутствующий ZIP является warning в local/fast run, но release invocation обязана передать archive path и получить zero warnings.

Implementation language runtime не является архитектурным решением Harness kernel; этот distribution validator реализован на Python как воспроизводимый packaging tool, а его output contract фиксирован.

### 13. Область значения PASS

`PASS` подтверждает только реально перечисленные автоматические проверки документационного комплекта: structure, links, YAML syntax, exact registry views, Contract Catalog coverage, entity-specific ID/status rules, canonical fields, capabilities, roadmap consistency, generated artifacts, manifest and ZIP.

`PASS` не подтверждает наличие реализованного runtime и не заменяет behavioral, security, adapter or executable conformance tests. Validation Report обязан повторять это ограничение.

### 14. Критерии приёмки

1. Validator обнаруживает profile, ID and entity-specific status inconsistencies.
2. Contract examples проходят syntax, required/forbidden field and status-variant checks.
3. Request Classes, Modes, Internal Operations and generated registry matrices сравниваются с registry exact-set/exact-order rules.
4. Capability-bearing fields отклоняют неизвестные aliases.
5. Roadmap package IDs/names совпадают в delivery and causal sequence; dependency graph acyclic.
6. Broken links and stale guide/full aggregate/file index блокируют release.
7. Every standalone entity example связан с Contract Catalog, storage/revision policy and lifecycle marker.
8. Validation Report перечисляет реальные checks, source tree hash and exact scope of PASS.
9. CI разделяет fast and release suites.
10. v0.2/v0.3 migration aliases тестируются, но новые normative examples используют canonical identifiers.

---

<!-- SOURCE: 12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md -->

## Подключение уже разрабатываемого проекта (Brownfield Onboarding)

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Harness должен безопасно подключать существующий проект, определить его фактическую структуру и подготовить систему продолжения разработки без скрытой перестройки. На выходе пользователь получает:

- подтверждённый brownfield baseline;
- систему prompts/routes/skills для существующего стека;
- ветку продолжения разработки;
- отдельную ветку улучшений;
- отдельную ветку исправления дефектов;
- список blockers and prerequisites.

### 2. Главный принцип

```text
Inspect first, reconcile second, propose third, modify only after approval/readiness.
```

Первичная инвентаризация выполняется read-only. Harness не запускает formatter, migrations, dependency upgrade или tests with writes до определения permissions and environment policy.

### 3. Входы

```yaml
brownfield_intake:
  id: BFI-20260806-001
  session_ref: SES-20260806-0005
  repository_sources:
    - url_or_path_ref: REP-APP-001
      access: READ_ONLY
  documentation_sources: []
  issue_sources: []
  deployment_sources: []
  user_goal: "Продолжить разработку и исправить известные ошибки"
  status: INVENTORY_PENDING
```

Минимум:

- доступ к repository snapshot или archive;
- ответ на обязательный вопрос о документации;
- цель подключения;
- ограничения на writes/commands/network.

### 4. Этапы onboarding

```text
1. Intake Session and documentation question
2. Read-only source/repository inventory
3. Build/test/runtime reconnaissance
4. Architecture, technology and contract extraction
5. Documentation ↔ code ↔ tests reconciliation
6. Material clarification batch
7. Brownfield Baseline Proposal
8. Brownfield Baseline Gate
9. Skill/context/verification preparation
10. Route portfolio generation
11. First READY task selection
```

### 5. Repository Inventory

Harness определяет:

- repository topology: single, monorepo, polyrepo;
- languages, runtimes, frameworks and versions;
- package/build systems and lockfiles;
- source/test/documentation/config paths;
- entry points and deployables;
- services/modules/packages and dependencies;
- API/contracts/schema definitions;
- database/migrations and current head;
- CI/CD and release configuration;
- environment requirements;
- logging/observability;
- security-sensitive boundaries;
- code ownership/Git policy;
- existing agent/project guidance;
- known failing tests and build state.

```yaml
repository_inventory:
  id: RIV-APP-001
  repository_ref: REP-APP-001
  revision: sha256:...
  topology: MONOREPO
  components: []
  technology_candidates: []
  build_commands: []
  test_commands: []
  database_refs: []
  documentation_refs: []
  confidence: 0.91
  unknowns: []
```

### 6. Safe reconnaissance

Разрешены read-only operations:

- listing files and metadata;
- parsing manifests/configs;
- reading docs/source/tests;
- static dependency graph extraction;
- Git history/status inspection;
- non-mutating commands proven safe by adapter.

Команда build/test может создавать caches/artifacts. До запуска она классифицируется как side effect и выполняется в isolated workspace после permission grant.

### 7. Reconciliation classes

Для каждого material fact:

```text
DOC_AND_CODE_AGREE
CODE_AHEAD_OF_DOCS
DOCS_AHEAD_OF_CODE
TESTS_DEFINE_OBSERVED_BEHAVIOR
CONFLICT_REQUIRES_DECISION
LEGACY_TOLERATED
UNKNOWN
```

Примеры:

- Документация описывает endpoint, которого нет → `DOCS_AHEAD_OF_CODE`; нужно решить, requirement это или устаревший текст.
- Код использует новую schema, docs старые → `CODE_AHEAD_OF_DOCS`; требуется проверить, было ли изменение принято.
- Test ожидает старое behavior, accepted docs новое → candidate `STALE_TEST`, но решение фиксируется formal route.

### 8. Brownfield Baseline

```yaml
brownfield_baseline:
  id: BFB-APP-001
  revision: 1
  repository_revision: sha256:...
  status: PROPOSED

  accepted_actual_structure_ref: RIV-APP-001
  project_definition_ref: PJD-APP-001
  architecture_baseline_ref: ARB-APP-001
  technology_baseline_ref: TBL-APP-001
  contract_refs: []
  test_baseline_ref: TSB-APP-001

  known_gaps: []
  known_defects: []
  technical_debt_items: []
  security_findings: []
  documentation_conflicts: []
  assumptions: []
  unknowns: []
```

Baseline Gate требует подтверждения material conflicts. Он не утверждает, что существующее состояние идеально; он фиксирует, что именно принято как starting point.

### 9. Route Portfolio

После gate Harness создаёт независимые, но связанные направления.

#### 9.1. Continuation Route

```text
CONTINUE_DEVELOPMENT
```

Содержит tasks, необходимые для реализации текущего product roadmap с учётом существующей архитектуры.

#### 9.2. Improvement Route

```text
IMPROVE_PROJECT
```

Кандидаты:

- architecture simplification;
- dependency/runtime upgrades;
- testability improvements;
- performance/reliability work;
- documentation recovery;
- security hardening;
- build/developer experience improvements.

Каждое улучшение имеет value, risk, dependencies, migration and rollback. Оно не смешивается автоматически с feature tasks.

#### 9.3. Bug-fix Route

```text
FIX_KNOWN_BUGS
```

Для каждого defect:

```text
reproduce
→ classify expected behavior
→ create targeted fix task
→ regression verification
→ documentation/known-issue update
```

#### 9.4. Stabilization Route

```text
STABILIZE_BASELINE
```

Создаётся, если build/test/environment настолько нестабильны, что continuation tasks нельзя проверять. Содержит минимальные prerequisites, а не полный refactoring.

### 10. Route item contract

```yaml
brownfield_route_item:
  id: BRI-FIX-001
  route: FIX_KNOWN_BUGS
  title: "Исправить потерю фильтра при пагинации"
  evidence_refs: [EVD-BUG-001]
  requirement_refs: [REQ-SEARCH-001]
  estimated_risk: MEDIUM
  value: HIGH
  dependencies: []
  proposed_work_package_ref: WP-FIX-SEARCH-001
  status: PROPOSED
```

### 11. Уточняющие вопросы

После анализа задаются только вопросы, которые нельзя надёжно вывести и которые material для baseline:

- какая документация authoritative;
- какие незакоммиченные/экспериментальные части считать baseline;
- какая production/runtime среда реально используется;
- какие known failures допустимы временно;
- какие branches/releases поддерживаются;
- можно ли менять stack/architecture;
- какой route имеет приоритет: continuation, fixes or improvements.

Вопросы содержат варианты and recommendation based on evidence.

### 12. Подготовка Harness infrastructure

После принятия baseline:

- создаётся `.harness/` project instance;
- импортируются accepted requirements/constraints/decisions;
- формируется Technology Baseline;
- выполняется Skill Gap Analysis;
- регистрируются existing build/test commands;
- создаются Verification Profiles and Test Environment policy;
- строятся Context Policies по структуре repository;
- генерируются Work Packages and routes;
- JIT prompts компилируются только для первых READY tasks.

### 13. Запрет скрытой перестройки

Harness не должен без отдельного approved Improvement/Change Pack:

- менять architecture style;
- заменять framework/database;
- массово перемещать directories;
- переписывать tests;
- обновлять все dependencies;
- форматировать весь repository;
- менять public contracts;
- исправлять unrelated defects в feature task.

### 14. First result

Пользователь получает:

```text
Проект распознан: monorepo, 3 компонента
Документация: частично актуальна, 4 material conflicts
Build: проходит; 2 известных test failures
Стек: ...
Предложенные маршруты:
  1. продолжение разработки — 5 Work Packages
  2. исправление ошибок — 3 Work Packages
  3. улучшения — 4 кандидата, не блокируют features
Рекомендуемый первый шаг: подтвердить API contract conflict
```

### 15. Критерии приёмки

1. Brownfield inspection начинается read-only.
2. Structure, stack, commands, tests, docs and contracts inventory зафиксированы с revision.
3. Code/docs/tests conflicts классифицированы, а не скрыты.
4. Baseline Gate предшествует new product prompts.
5. Continuation, Improvement, Bug-fix and Stabilization routes разделены.
6. Улучшения не внедряются автоматически вместе с feature task.
7. Existing known test failures имеют baseline classification.
8. После gate существует хотя бы один понятный next route или recovery option.

### 18. v0.4.1 explicit acceptance

Brownfield Baseline Gate является отдельным пятым approval для Brownfield/Hybrid. До него baseline может быть только proposal; Architecture/Technology proposals не активируют фактический baseline автоматически. Принятие создаёт immutable Decision и accepted successor revision либо initial accepted revision, в зависимости от route.

---

<!-- SOURCE: 12_Implementation_Specifications/21_Project_Start_Questionnaire.md -->

## Обязательный опрос при старте проекта

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Каждый первоначальный `PROJECT_START` для нового Project Instance начинается с короткого управляемого опроса. Опрос помогает собрать Project Definition, выбрать profile, подготовить architecture/technology decisions, skills, routes and prompt infrastructure.

Опрос обязателен и для greenfield, и для brownfield, но содержание адаптируется к исходным документам и repository evidence.

### 2. Первый обязательный вопрос

Первый вопрос всегда относится к документации проекта:

> Есть ли у проекта документация, техническое задание, требования, схемы, ADR, README или другие материалы, которые нужно принять за исходную основу?

Варианты:

```text
1. Да, приложу/укажу документы.
2. Есть частичная или устаревшая документация.
3. Документации нет — опишу проект ответами.
4. Не уверен, что считать документацией — покажу доступные материалы.
```

Harness объясняет, что документы сначала анализируются как sources, а не автоматически объявляются истинными.

### 3. Adaptive questionnaire flow

```text
Start Session
→ Documentation Question
→ Source Inventory and Analysis
→ Project Mode Detection: GREENFIELD / BROWNFIELD / HYBRID
→ Core Question Batch
→ Adaptive Material Questions
→ Answer Reconciliation
→ Project Definition Draft
→ Readiness Summary and Final Confirmation
→ Architecture/Technology/Skills/Bootstrap preparation
```

Вопросы, уже надёжно отвеченные документацией или repository, не задаются повторно. Harness показывает extracted answer и просит подтверждение только если он material или conflicting.

### 4. Question budget

Чтобы опрос не был избыточным:

- первый batch: 3–5 вопросов;
- следующий batch: только material gaps, обычно 3–5;
- целевой общий объём: 7–12 ответов для типового проекта;
- hard upper bound до первой Project Definition Draft: 15 вопросов без отдельного согласия;
- сложный regulated/multi-repo project может продолжить discovery после draft отдельными этапами;
- dependent/conditional вопросы не показываются заранее.

Количество не является целью: достаточно вопросов, закрывающих readiness dimensions.

### 5. Core question groups

Ниже — типовой bank. Harness выбирает только применимые вопросы.

#### 5.1. Цель и результат

**Вопрос:** Какую проблему решает проект и какой результат должен получить пользователь?

Варианты помощи:

- «Опишите одним-двумя предложениями»;
- «Пока есть только идея»;
- «Есть конкретный список функций»;
- «Нужно продолжить существующий продукт».

#### 5.2. Пользователи и масштаб

**Вопрос:** Кто будет пользоваться системой и примерно сколько пользователей/операций ожидается?

Понятные варианты:

```text
Личный/локальный инструмент
Небольшая команда или до сотен пользователей
Тысячи пользователей
Высокая нагрузка или пока неизвестно
```

Harness поясняет, что точное число не обязательно; диапазон помогает не переусложнить или недооценить архитектуру.

#### 5.3. Online/offline

**Вопрос:** Должна ли система работать без интернета?

```text
Только онлайн
Частично офлайн
Offline-first
Не знаю — предложите baseline
```

#### 5.4. Платформы и размещение

**Вопрос:** Где система должна работать?

```text
Web browser
Mobile devices
Desktop
CLI/server
On-premise
Cloud
Несколько вариантов
Пока неизвестно
```

#### 5.5. Данные и чувствительность

**Вопрос:** Какие данные хранит система и есть ли чувствительные/персональные/секретные данные?

Harness приводит простые примеры и предлагает `нет / да / не знаю` с последующим уточнением только material details.

#### 5.6. Интеграции

**Вопрос:** С какими внешними системами, API, файлами, устройствами или базами нужно работать?

Можно ответить списком или «пока нет/не знаю».

#### 5.7. Ограничения и обязательный stack

**Вопрос:** Есть ли технологии, платформы, лицензии, сроки или правила, которые обязательно использовать или нельзя использовать?

Для brownfield Harness сначала показывает обнаруженный stack и спрашивает, можно ли его менять.

#### 5.8. Критерии успеха

**Вопрос:** Как понять, что первый рабочий результат готов?

Предлагаются варианты:

- конкретный пользовательский сценарий;
- набор функций;
- performance/reliability target;
- demo/prototype;
- release/production readiness;
- «помогите сформулировать».

#### 5.9. Команда и эксплуатация

**Вопрос:** Кто будет разрабатывать и поддерживать проект и есть ли предпочтения по сложности эксплуатации?

Задаётся только когда влияет на technology/architecture selection.

#### 5.10. Приоритет

**Вопрос:** Что важнее на первом этапе: быстрее получить рабочий минимум, обеспечить масштабирование, строгую безопасность, offline или совместимость с существующей системой?

Пользователь может выбрать несколько приоритетов, Harness выявляет conflicts.

### 6. Questions derived from documentation

После анализа sources Harness создаёт:

```yaml
documentation_findings:
  confirmed_answers: []
  assumptions_to_confirm: []
  conflicts: []
  missing_material_dimensions: []
  adaptive_questions: []
```

Adaptive question создаётся, если:

- разные документы противоречат;
- важное значение отсутствует;
- формулировка неоднозначна;
- решение materially влияет на architecture/stack;
- source authority/revision непонятна;
- существующий code не соответствует docs.

### 7. Questionnaire Session Contract

```yaml
questionnaire_session:
  id: QNS-20260806-001
  intake_session_ref: SES-20260806-0006
  project_mode: GREENFIELD
  profile_candidates: [WEB_APPLICATION, API_SERVICE]

  source_inventory_ref: SIV-20260806-001
  question_budget:
    target: 10
    hard_limit_before_draft: 15
    asked: 4
    answered: 4

  dimensions:
    documentation: CONFIRMED
    purpose: CONFIRMED
    users_and_scale: ASSUMED_WITH_OWNER_AND_REVIEW_TRIGGER
    connectivity: CONFIRMED
    platforms: CONFIRMED
    data_and_security: UNKNOWN_WITH_DECISION_PLAN
    integrations: CONFIRMED
    constraints: CONFIRMED
    success_criteria: CONFIRMED

  open_question_refs: [QST-DATA-001]
  status: QUESTIONING
```

### 8. Answer Contract

```yaml
answer:
  id: ANS-QST-SCALE-001
  question_ref: QST-SCALE-001
  actor_ref: ACT-USER-001
  value: SMALL_TEAM
  free_text: "До 50 сотрудников"
  confidence: MEDIUM
  source_refs: []
  accepted_assumption: true
  review_trigger: "Перед внешним запуском"
  answered_at: 2026-08-06T15:00:00Z
```

Пользователь может исправить ответ; новая revision создаёт impact analysis, если baseline уже принят.

### 9. Понятное представление вопросов

Каждый вопрос содержит:

```text
Вопрос
Почему он важен
Короткие варианты
Рекомендуемый вариант, если есть evidence
Поле «не знаю / предложите вариант»
Пример ответа
```

Пример:

```text
Нужно ли приложению работать без интернета?
Это определит, потребуется ли локальное хранение и синхронизация.
A. Только онлайн — проще и быстрее для первого релиза.
B. Частично офлайн — часть данных доступна без сети.
C. Offline-first — большинство функций работает без сети.
D. Не знаю — используйте online-first как обратимый baseline.
Пример ответа: «A для первого релиза, offline рассмотрим позже».
```

### 10. Readiness summary

После ответов Harness не начинает реализацию молча. Он показывает draft:

- что понял о проекте;
- users and outcomes;
- in/out scope;
- assumptions and unknowns;
- profile candidate;
- material constraints;
- recommended architecture direction;
- decisions, которые нужны позже;
- что будет создано после подтверждения.

Пользователь подтверждает Project Definition Gate или корректирует ответы.

### 11. Автоматическая подготовка после опроса

После accepted Project Definition запускается последовательность:

```text
Requirements and Constraints normalization
→ Architecture options
→ Technology Baseline proposal
→ Material Decision Gate
→ Skill Gap Analysis
→ ACTIVE skill resolution and project configuration
→ Bootstrap Plan
→ Work Packages and causal DAG
→ Context/Verification policies
→ first READY task
→ JIT prompt infrastructure
```

«Подготовка промтов» означает создание reusable specs/modules and task routes; compiled prompts создаются JIT только для READY tasks.

### 12. Greenfield and brownfield differences

| Область | Greenfield | Brownfield |
|---|---|---|
| Documentation | Intent/docs are proposal sources | Docs reconcile with code/tests. |
| Stack | Candidate options | Existing stack inventory first. |
| Architecture | Designed from requirements | Actual architecture extracted and accepted/changed explicitly. |
| Questions | Core bank + source-derived | Conflicts/unknowns + user priorities. |
| Bootstrap | Create handoff skeleton | Build control plane in output handoff without modifying source repository. |
| First routes | Build foundation/features | Continue/improve/fix/stabilize. |

### 13. Ошибки и остановки

- Если пользователь не предоставил документы, опрос продолжается по типовым вопросам.
- Если documents unreadable, Harness объясняет проблему и предлагает другой формат или manual answers.
- Если ответ material conflict, Project Definition Gate остаётся `WAITING_DECISION`.
- Если пользователь не знает ответа, создаётся bounded assumption and review trigger, если безопасно.
- Нельзя бесконечно задавать вопросы до полной определённости; unknowns допускаются с owner and plan.

### 14. Initial-only lifecycle rule

Полный Project Start Questionnaire выполняется при первоначальном создании или подключении нового Project Instance.

При повторном запуске процесса Harness:

```text
reads PROJECT_LOCK
→ restores Session and current state
→ validates active revisions
→ returns exact current route
```

Questionnaire не начинается заново. Targeted questions создаются только при material gap, conflict, stale baseline или Project Evolution. Повторная отправка того же answer bundle является идемпотентной и не создаёт дубликаты Session, Questionnaire или Baseline.

Browser GPT обязан различать отсутствие ответа и уже принятый canonical answer. Он не должен повторять вопрос, на который отвечает normative source или accepted project entity.

### 15. Критерии приёмки

1. Каждый project start создаёт Questionnaire Session.
2. Первый вопрос всегда о документации.
3. Documents анализируются до adaptive questions.
4. Core bank покрывает purpose, users/scale, online/offline, platform, data, integrations, constraints and success.
5. Вопросы понятны, имеют варианты, explanation and `UNKNOWN` path.
6. Typical intake укладывается в 7–12 ответов и не превышает 15 до draft без согласия.
7. Answers создают Project Definition Draft and readiness summary.
8. Product prompts не создаются до Definition/Architecture/Technology readiness.
9. После gate разрешаются ACTIVE skills, routes, Work Packages and first READY task.
10. Brownfield questionnaire использует repository evidence и не повторяет известное.

### 19. v0.4.1 sensitivity rule

Questionnaire может предложить ответ «не знаю», но accepted `PROJECT_INPUT.data.sensitivity` не может оставаться `UNKNOWN`. До выбора `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`, `SECRET` или `REGULATED` readiness остаётся `WAITING_INPUT`.

---

<!-- SOURCE: 12_Implementation_Specifications/22_Browser_GPT_Preparation_and_Codex_Handoff.md -->

## Browser GPT Preparation and Codex Handoff

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

### 1. Назначение

Спецификация определяет Browser GPT как семантический подготовительный слой Project Harness и фиксирует детерминированную передачу подтверждённого проекта в Codex.

Browser GPT не является Agent Adapter исполняемого runtime.

Он не получает право самостоятельно изменять product repository после handoff.

Он выполняет анализ источников, диалог с пользователем и подготовку semantic input.

Project Harness выполняет канонизацию, проверки, компиляцию и packaging.

Codex выполняет только текущую atomic task.

### 2. Граница ответственности

```text
Browser GPT
→ understand natural language
→ analyze uploaded documentation
→ identify material gaps
→ ask adaptive questions
→ propose bounded alternatives
→ record confirmed semantic decisions

Deterministic Harness
→ assign stable IDs
→ validate registries and contracts
→ validate approvals
→ normalize task DAG
→ resolve ACTIVE skills
→ compile current prompt/context
→ generate lock, manifest and ZIP

Codex
→ read current bundle
→ change declared paths
→ run allowed checks
→ write Agent Task Result
```

Ни один слой не должен незаметно присваивать себе governance-функции другого слоя.

### 3. Режим операции

Canonical operation подготовительного слоя:

```text
PREPARE_FOR_CODEX
```

Operation относится к первоначальному `PROJECT_START` или к принятому Project Evolution.

Она не означает `EXECUTE_PRODUCT_TASK`.

Она завершается статусом:

```text
READY_FOR_CODEX
```

Она не может завершаться статусом `PROJECT_COMPLETED`, потому что product tasks ещё не исполнены.

### 4. Входной пакет

Минимальный вход содержит архив Project Harness Engine и описание проекта.

Рекомендуемый вход содержит:

- архив движка;
- документацию проекта;
- список нормативных источников;
- пользовательские ограничения;
- для brownfield — repository directory или ZIP;
- известные defects, gaps и technical debt;
- ожидаемый первый проверяемый outcome.

Browser GPT сначала различает:

```text
ENGINE_ARCHIVE
DOCUMENTATION_ARCHIVE
PROJECT_SOURCE
SUPPLEMENTAL_REQUIREMENT
UNKNOWN_FILE
```

Он не должен считать документационный архив исполняемым движком.

Он не должен утверждать, что видел repository structure, если загружен только README.

### 5. Distribution validation

Первое детерминированное действие:

```bash
python project-harness.py doctor
```

Browser GPT выводит фактический machine result.

При `FAIL` preparation останавливается с точным blocker.

Допустимые recovery routes:

```text
UPLOAD_COMPLETE_ENGINE_ARCHIVE
REPAIR_DISTRIBUTION
USE_MATCHING_DOCUMENTATION_VERSION
CANCEL_PREPARATION
```

Успешный doctor подтверждает registries, schemas, seed ACTIVE skills и entry points.

### 6. START_INTAKE

`START_INTAKE` создаёт provisional control workspace до project-local bootstrap.

Workspace не является product repository.

Для brownfield он обязан находиться вне target repository.

Пример greenfield:

```bash
python project-harness.py start-intake \
  --workspace ./work/project-intake \
  --project-name "Example Project" \
  --mode greenfield \
  --source ./input/requirements.md
```

Пример brownfield:

```bash
python project-harness.py start-intake \
  --workspace ./control/existing-intake \
  --project-name "Existing Project" \
  --mode brownfield \
  --source ./input/docs \
  --repository ./input/repository.zip
```

До accepted handoff исходный brownfield repository остаётся read-only.

### 7. Первый обязательный вопрос

Первый вопрос всегда относится к документации:

```text
Есть ли документация, ТЗ, схемы, ADR, README или другие материалы?
Какие материалы являются нормативными, частичными или устаревшими?
```

Browser GPT сначала анализирует доступные материалы.

Он не повторяет вопрос, если ответ достоверно найден.

При material interpretation он просит подтверждение интерпретации, а не повтор исходного вопроса.

### 8. Адаптивный опрос

Вопросы задаются пакетами по три–пять связанных пунктов.

Обычный целевой budget составляет семь–двенадцать ответов.

До первого Project Definition draft нельзя превышать пятнадцать вопросов без material reason.

Обязательные области:

- first user outcome;
- users;
- initial scale;
- connectivity;
- runtime platforms;
- deployment target;
- data sensitivity;
- integrations;
- scope and non-scope;
- mandatory and forbidden constraints;
- success criteria;
- architecture boundary;
- technology selections;
- minimal causal plan.

Неизвестное, которое не блокирует первый outcome, записывается как bounded unknown или assumption.

Material ambiguity блокирует соответствующий Gate.

### 9. Semantic input

Browser GPT заполняет `PROJECT_INPUT.yaml`.

Файл может использовать JSON syntax, совместимый с YAML 1.2.

Semantic input включает:

```text
metadata
project
profile
architecture
technology
skills
planning
brownfield
approvals
```

Browser GPT отвечает за смысл и grounding.

Harness отвечает за structural validity.

### 10. Project Definition Gate

До approval Browser GPT показывает:

- problem statement;
- primary outcome;
- users;
- scope;
- non-scope;
- constraints;
- success criteria;
- assumptions;
- unknowns.

Approval записывается отдельно от questionnaire answer.

Approval содержит actor и timestamp.

Молчание пользователя не считается approval.

### 11. Architecture Baseline Gate

Browser GPT формирует bounded architecture proposal.

Proposal содержит components, interfaces, data flow, quality attributes, risks и material decisions.

Пользователю показываются существенные alternatives.

Recommendation должна быть отделена от подтверждённого решения.

После approval Harness создаёт versioned Architecture Baseline.

Codex не может менять accepted Architecture Baseline обычной implementation task.

### 12. Technology Baseline Gate

Technology Baseline фиксирует selections, version ranges, build commands, test commands и lint commands.

Выбор не должен зависеть от ещё не проверенного future component.

Browser GPT не заявляет доступность runtime/toolchain без evidence.

Approval Technology Baseline является отдельным Gate.

### 13. Skill Gap Analysis

Последовательность resolution:

```text
documentation and answers
→ accepted Project Definition
→ accepted Architecture Baseline
→ accepted Technology Baseline
→ repeatable workflows
→ Skill Gap Analysis
```

Core actions:

```text
REUSE
CONFIGURE
TASK_ONLY
```

`CREATE` и `EXTEND` не выполняются из сырого questionnaire.

Новый PROJECT skill требует evaluation, validation и activation.

Для каждого проекта создаётся resolution и generated index, а не новая копия всей библиотеки skills.

### 14. Planning contract

Browser GPT предлагает минимальное число Work Packages.

Каждая executable task должна быть atomic.

Task содержит:

- purpose;
- expected result;
- dependency refs;
- requirement and constraint refs;
- read scope;
- write scope;
- forbidden scope;
- primary ACTIVE skill;
- required capabilities;
- acceptance criteria;
- verification commands or checks;
- documentation impact;
- rollback strategy.

Harness нормализует task aliases в canonical IDs.

Harness отклоняет dependency cycle.

Первая причинно доступная task получает `READY`.

Остальные получают `PLANNED`.

### 15. Prompt и Context preparation

Для всего DAG заранее создаются:

```text
Task Contracts
Prompt Plans
Context Plans
Verification Profiles
```

Для будущих tasks compiled bundle не создаётся.

Для текущей READY task Harness создаёт:

```text
Context Packet
Capability Grant
Compiled Prompt Bundle
Run Plan
pre-run Snapshot
NEXT_TASK
```

Compiled prompt связан с exact task revision и Run reservation.

### 16. Handoff approval

Перед packaging Browser GPT показывает:

- accepted Project Definition;
- Architecture Baseline;
- Technology Baseline;
- key decisions;
- constraints;
- unresolved unknowns;
- Skill Gap result;
- roadmap;
- first READY task;
- external sandbox limitations.

Только после explicit Handoff approval запускается `prepare`.

### 17. Deterministic prepare

```bash
python project-harness.py prepare \
  --workspace ./work/project-intake \
  --output ./output/Project_Codex_Handoff_v1.zip
```

Команда выполняет:

```text
validate semantic input
→ validate four Greenfield approvals or five Brownfield/Hybrid approvals
→ verify brownfield source digest
→ create handoff workspace
→ copy accepted product source when applicable
→ install project-local control plane
→ create canonical entities
→ build causal DAG
→ seed ACTIVE skills
→ create exact PROJECT_LOCK
→ compile first READY bundle
→ render human views
→ validate structure
→ generate MANIFEST.sha256
→ validate manifest
→ create deterministic ZIP
```

Исходный repository не изменяется.

### 18. Handoff archive

Обязательные root files:

```text
CODEX_START.md
AGENTS.md
HANDOFF_SUMMARY.md
PROJECT.md
ARCHITECTURE.md
TECHNOLOGY.md
ROADMAP.md
STATUS.md
VALIDATION_REPORT.json
MANIFEST.sha256
```

Обязательный control root:

```text
.harness/
```

В handoff находится embedded runtime, поэтому Codex не зависит от Browser GPT после каждого task transition.

### 19. PROJECT_LOCK

Lock содержит engine version и schema version.

Он фиксирует exact registry names:

```text
id_prefixes
project_profiles
statuses
request_routing
capabilities
contracts
```

Для каждого registry фиксируются version и SHA-256 digest.

Также фиксируются profile refs, adapter refs, skill refs, prompt spec refs и migrations applied.

### 20. Initial validation

До product changes выполняется:

```bash
python .harness/engine/project-harness.py validate-handoff --project .
```

Проверка включает immutable baseline manifest.

После начала разрешённых product changes используется:

```bash
python .harness/engine/project-harness.py validate-project --project .
```

`validate-project` проверяет contracts и runtime state без требования совпадения с исходным manifest.

### 21. Codex startup

Codex читает `CODEX_START.md` и `AGENTS.md`.

Он выполняет:

```bash
python .harness/engine/project-harness.py status --project .
python .harness/engine/project-harness.py next --project .
```

Codex не выбирает route или task самостоятельно.

Он читает prompt path из `NEXT_TASK.yaml`.

Он не редактирует `.harness/`, кроме exact Agent Task Result path.

### 22. Verification and completion

После implementation Codex запускает независимую проверку Harness:

```bash
python .harness/engine/project-harness.py verify \
  --project . \
  --allow-command-execution
```

Harness сравнивает pre-run snapshot и actual product tree.

Harness проверяет declared write scope и forbidden paths.

Commands выполняются без shell, в bounded cwd, с timeout и sanitized environment.

PASS verification не заменяет OS-level sandbox.

Codex записывает Agent Task Result.

Завершение:

```bash
python .harness/engine/project-harness.py complete \
  --project . \
  --result .harness/runtime/AGENT_RESULTS/<RUN-ID>.json
```

Declared changes должны точно совпасть с independently observed diff.

### 23. JIT progression

После accepted completion Harness создаёт immutable Run, Evidence и Task Report.

Task получает новую revision со статусом `DONE`; успешный Run фиксируется как `SUCCEEDED`.

Следующая причинно доступная task получает новую revision со статусом `READY`.

Только тогда компилируется её bundle.

Если задач больше нет, project status становится `COMPLETED`.

### 24. Blocker protocol

При material ambiguity Codex не импровизирует.

```bash
python .harness/engine/project-harness.py block \
  --project . \
  --reason "Precise material blocker" \
  --option "Safe recovery route"
```

Blocker сохраняет reason, recovery options и resume condition.

После решения:

```bash
python .harness/engine/project-harness.py resume \
  --project . \
  --resolution "Accepted resolution"
```

Создаётся новая Run attempt.

История предыдущей попытки не перезаписывается.

### 25. Brownfield guarantees

До handoff preparation:

- original repository remains byte-identical;
- `.harness/` is not installed into original repository;
- repository ZIP is extracted with path traversal protection;
- symlinks are not accepted as trusted archive entries;
- repository inventory and tree digest are recorded.

Handoff copy содержит route portfolio:

```text
CONTINUE_DEVELOPMENT
FIX_KNOWN_BUGS
IMPROVE_PROJECT
STABILIZE_BASELINE
```

### 26. Security boundary

Core runtime ограничивает logical scope.

Он не реализует kernel-level process sandbox.

External command может быть дополнительно ограничен контейнером, VM или managed sandbox.

Network access, writes outside repository и secret isolation должны обеспечиваться внешней средой исполнения.

Git push, deploy и release publication не входят в default Capability Grant.

### 27. Error statuses

Preparation возвращает structured status:

```text
WAITING_INPUT
WAITING_DECISION
INVALID
READY_FOR_CODEX
BLOCKED
FAIL
```

`WAITING_INPUT` означает, что semantic fields неполны.

`WAITING_DECISION` означает, что отсутствуют explicit approvals.

`INVALID` означает contract or registry violation.

`BLOCKED` означает material obstacle с recovery routes.

Browser GPT показывает status и exact next action без выдуманного успеха.

### 28. Idempotency

Повторный `next` при неизменном state возвращает тот же Run reservation и bundle.

Повторный `start-intake` для существующего valid workspace возвращает его readiness, если не указан controlled reset.

Run ID включает attempt number.

Retry не перезаписывает предыдущий Run.

### 29. Observability

Handoff сохраняет:

- Request;
- Request Plan;
- Session;
- Questionnaire;
- source and repository inventories;
- baselines;
- tasks and DAG;
- Prompt and Context plans;
- compiled bundles by Run;
- snapshots;
- Run records;
- Evidence;
- validation reports;
- task reports;
- events;
- current state.

Human-readable views являются generated projections canonical state.

### 30. Нормативные ограничения Browser GPT

Browser GPT не должен:

- заявлять выполнение команды без tool evidence;
- считать answers approvals;
- создавать PROJECT skill из одного ответа;
- precompile prompts для всего roadmap;
- скрывать material unknown;
- менять accepted architecture после approval;
- утверждать brownfield inventory без исходного repository;
- помещать provisional workspace внутрь target repository;
- возвращать `READY_FOR_CODEX`, если validator failed.

### 31. Критерии приёмки

Механизм считается реализованным, если одновременно выполнены следующие условия.

1. Browser GPT начинает с validation engine distribution.
2. Первый intake question относится к документации.
3. Provisional workspace создаётся до project-local bootstrap.
4. Brownfield workspace находится вне исходного repository.
5. Исходный brownfield repository не изменяется до handoff.
6. Semantic input содержит все required project fields.
7. Четыре material approvals записываются отдельно для Greenfield; Brownfield/Hybrid имеет отдельный пятый Brownfield Baseline approval.
8. Architecture Baseline имеет versioned persistent contract.
9. Session имеет lifecycle и persistent contract.
10. Skill Gap Analysis не создаёт новый skill автоматически.
11. Каждая task имеет atomic scope и verification.
12. Task DAG не содержит cycle и missing dependencies.
13. Exact registry versions and digests зафиксированы в Project Lock.
14. В initial handoff находится ровно один compiled prompt bundle.
15. Future tasks имеют plans, но не compiled bundles.
16. Handoff ZIP проходит safe extraction, CRC, structural и manifest validation.
17. Embedded runtime выполняет `status`, `next`, `verify`, `complete`, `block` и `resume`.
18. Повторный `next` идемпотентен.
19. Verification обнаруживает write outside declared scope.
20. Agent-declared diff сравнивается с independently observed diff.
21. Completed task создаёт Run, Evidence и Task Report.
22. Следующий bundle компилируется только после accepted transition.
23. Blocker сохраняет recovery routes и позволяет новую attempt.
24. Mutable project после product changes проходит `validate-project`.
25. Browser GPT возвращает архив только при `READY_FOR_CODEX`.

### 32. Definition of Done

Definition of Done включает greenfield и brownfield fixtures.

Greenfield fixture доказывает полный two-task JIT loop.

Brownfield fixture доказывает read-only discovery и exact four-route portfolio.

Conformance suite должна проверять explicit approvals, manifest tampering, unsafe ZIP, scope violation, Agent Task Result mismatch, Blocker/resume и final project completion.

Не реализованные hardening-механизмы перечисляются как ограничения и не имитируются.

---

<!-- SOURCE: 12_Implementation_Specifications/23_Contract_Hardening_v0.4.1.md -->

## Project Harness v0.4.1 — Contract Hardening

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION  

**Базовая версия:** Project Harness Engine v0.4.0  
**Целевая версия:** v0.4.1  
**Тип релиза:** PATCH / contract hardening  
**Статус документа:** NORMATIVE IMPLEMENTATION SPECIFICATION  
**Зависимости:** только v0.4.0  
**Порядок реализации:** первый документ серии

### 1. Назначение версии

v0.4.1 устраняет пять подтверждённых несоответствий между документацией, registries и фактическим runtime v0.4.0. Версия не добавляет новый пользовательский workflow и не автоматизирует Codex, Git, deployment, parallel execution или remote control plane.

В scope входят только:

1. нормализация Task и Run statuses;
2. отдельный Brownfield Baseline approval;
3. единая data sensitivity taxonomy;
4. строгая schema для `PROJECT_INPUT`;
5. проверяемые control-plane invariants.

После v0.4.1 существующий последовательный цикл остаётся тем же:

```text
START_INTAKE
→ Project Definition / Architecture / Technology approvals
→ PREPARE
→ JIT current Task bundle
→ manual Codex execution
→ VERIFY
→ COMPLETE / BLOCK / RESUME
```

### 2. Не входит в scope

v0.4.1 не должна включать:

- Implementation Levels или Stage Gates;
- автоматический вызов Codex CLI/API;
- container/VM sandbox;
- Git commit, push или Pull Request;
- deployment routes;
- создание новых PROJECT skills;
- parallel scheduler, worktrees или leases;
- server/API/multi-user режим;
- provider billing, token accounting или cost tracking;
- изменение JIT-принципа;
- переработку структуры проекта или документации с нуля.

Любая задача, необходимая только будущим версиям, должна остаться вне v0.4.1.

### 3. Подтверждённые дефекты v0.4.0

#### 3.1. Task/Run status mismatch

Registry `registries/statuses.yaml` определяет:

```text
Task successful terminal status: DONE
Run successful terminal status: SUCCEEDED
```

Runtime v0.4.0 фактически записывает:

```text
Task: COMPLETED
Run: COMPLETED
```

При этом `COMPLETED` остаётся допустимым публичным Result status и Work Package status. Ошибка заключается не в самом слове, а в использовании public/aggregate status внутри Task и Run lifecycles.

#### 3.2. Brownfield Baseline Gate не подтверждается отдельно

Документация требует Brownfield Baseline Gate, но `PROJECT_INPUT` содержит только четыре approvals:

```text
project_definition
architecture_baseline
technology_baseline
codex_handoff
```

Compiler создаёт `brownfield_baseline.status: ACCEPTED`, хотя отдельного подтверждения пользователя нет.

#### 3.3. Data sensitivity taxonomy расходится

Документация определяет canonical classes:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
SECRET
REGULATED
```

Runtime принимает только:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
UNKNOWN
```

`UNKNOWN` является состоянием незнания во время intake, а не data classification.

#### 3.4. `project_input.schema.json` слишком свободная

Schema v0.4.0 проверяет в основном top-level envelope и разрешает произвольные свойства. Фактические правила находятся в `project_input.py`, поэтому schema, template и Python validation могут расходиться.

#### 3.5. Control plane защищён инструкцией, но не invariant-проверкой

Product snapshot исключает `.harness/` и generated root files. Agent получает текстовый запрет изменять control plane, но `validate-project` не доказывает, что Task/Prompt/Lock/registries не были изменены между Run reservation и completion.

OS-level enforcement появится только в v0.5.1. В v0.4.1 требуется детерминированное обнаружение tampering и запрет завершения Run.

### 4. Нормализация statuses

#### 4.1. Canonical mapping

В v0.4.1 применяются следующие значения:

| Сущность | Успешный статус | Комментарий |
|---|---|---|
| Agent Task Result | `COMPLETED` | Provider/agent output contract; остаётся без переименования. |
| Task | `DONE` | Canonical task lifecycle. |
| Run | `SUCCEEDED` | Canonical run lifecycle. |
| Work Package | `COMPLETED` | Aggregate lifecycle; остаётся без изменения. |
| Result Envelope | `COMPLETED` | Public result; остаётся без изменения. |
| Project state | `COMPLETED` | До появления Implementation Levels в v0.5.0. |
| Verification | `PASS` | Не меняется. |

Нельзя заменять все occurrences `COMPLETED` глобальным search/replace. Изменение выполняется по типу сущности.

#### 4.2. Изменения runtime

В `src/project_harness/runtime.py`:

- `complete_current()` записывает `run.status = SUCCEEDED`;
- `_write_task_revision(... status="DONE")` завершает Task;
- `_update_wp_status()` считает успешными Task со status `DONE`;
- `_next_runnable()` продолжает использовать `completed_task_refs`, но текущая Task revision обязана иметь `DONE`;
- `project_status()` возвращает Task status без remapping;
- события могут сохранить имя `TASK_COMPLETED`, потому что event type описывает факт, а не lifecycle value;
- `Task Report.status` остаётся `COMPLETED`, если он трактуется как public/report status. Если в registry будет добавлен отдельный lifecycle отчёта, это относится к отдельной версии и не включается сюда.

В `src/project_harness/planner.py` начальные значения остаются `READY`/`PLANNED`.

В `src/project_harness/validation.py` добавляется проверка:

```text
Task current revision status ∈ registry.task
Run status ∈ registry.run
Work Package status ∈ registry.work_package
Agent Task Result status ∈ Agent Result schema enum
```

Validator должен отклонять новые v0.4.1 Task/Run records со status `COMPLETED`.

#### 4.3. Backward compatibility

v0.4.1 должна читать immutable v0.4.0 history. Для historical records действует compatibility mapping:

```text
historical Task COMPLETED → interpreted as DONE
historical Run COMPLETED  → interpreted as SUCCEEDED
```

Правила:

- исторический файл не переписывается;
- mapping применяется только при чтении schema/version v0.4.0;
- новая revision Task создаётся уже с canonical status;
- новый Run никогда не записывается с legacy value;
- validation report явно показывает `legacy_status_mappings`, а не скрывает преобразование.

### 5. Brownfield Baseline approval

#### 5.1. Условное обязательное approval

Для `GREENFIELD` обязательны четыре существующих approval.

Для `BROWNFIELD` и `HYBRID` обязательны пять:

```text
project_definition
brownfield_baseline
architecture_baseline
technology_baseline
codex_handoff
```

Порядок gate:

```text
Source/Repository Inventory
→ Project Definition approval
→ Brownfield Baseline proposal
→ Brownfield Baseline approval
→ Architecture approval
→ Technology approval
→ Handoff approval
```

Architecture/Technology могут быть подготовлены до финального подтверждения для user-facing comparison, но `prepare` не принимает их как active baseline до Brownfield approval.

#### 5.2. Input contract

Для brownfield/hybrid:

```yaml
approvals:
  brownfield_baseline:
    approved: true
    actor: ACT-USER-001
    approved_at: 2026-08-17T10:00:00Z
    notes: "Подтверждены фактическая структура, revision, known gaps и test baseline."
```

Обязательные поля при `approved: true`:

- `actor`;
- `approved_at` либо детерминированно установленный timestamp операции approval;
- `notes` optional.

Обычный текстовый ответ пользователя не считается approval, пока Browser GPT или CLI не запишет формализованный record.

#### 5.3. Canonical decision record

Compiler создаёт отдельный decision:

```yaml
decision:
  id: DEC-<PROJECT>-BROWNFIELD-001
  revision: 1
  kind: BROWNFIELD_BASELINE_APPROVAL
  actor: ACT-USER-001
  approved_at: <timestamp>
  subject_ref: BFB-<PROJECT>-001@1
  status: ACCEPTED
```

`brownfield_baseline` получает:

```yaml
accepted_by: DEC-<PROJECT>-BROWNFIELD-001
accepted_at: <timestamp>
```

Нельзя использовать `project_definition` approval как неявную замену Brownfield approval.

#### 5.4. Регистрация Decision contract

Prefix `DEC` уже существует в `id_prefixes.yaml`, а Compiler v0.4.0 уже создаёт entity `decision`, но `contracts.yaml` не содержит её нормативного storage contract. v0.4.1 обязана устранить это расхождение:

```yaml
decision:
  id_prefix: DEC
  persistence: PERSISTENT
  lifecycle: decision
  storage_path: .harness/canonical/DECISIONS/{id}@{revision}.yaml
  revision_policy: IMMUTABLE
```

В `statuses.yaml` добавить минимальную группу:

```yaml
decision:
  - ACCEPTED
  - REJECTED
  - SUPERSEDED
```

Decision создаётся только как итог формализованного выбора; отдельный `PROPOSED` record для этой сущности не нужен. Pending approval остаётся состоянием Gate/Session, а не незавершённым Decision.

Registry version changes относительно v0.4.0:

```text
REG-CONTRACT-CATALOG: 2 → 3
REG-STATUSES:         3 → 4
REG-ID-PREFIXES:      остаётся 1
REG-CAPABILITIES:     остаётся 1
```

Изменённые registries и их embedded copies должны совпадать по digest, а новые handoff фиксируют их exact versions/digests в `PROJECT_LOCK`.

#### 5.5. Readiness behavior

- missing semantic fields → `WAITING_INPUT`;
- complete semantic fields, но отсутствует Brownfield approval → `WAITING_DECISION`;
- `prepare` при missing approval поднимает `WaitingDecision`;
- greenfield не должен ждать Brownfield approval;
- Browser GPT должен показать baseline summary, repository revision, test evidence, known defects/gaps и documentation conflicts до запроса approval.

### 6. Единая sensitivity taxonomy

#### 6.1. Разделение classification и epistemic state

В коде создаются два набора:

```python
DATA_SENSITIVITY_CLASSES = {
    "PUBLIC",
    "INTERNAL",
    "CONFIDENTIAL",
    "RESTRICTED",
    "SECRET",
    "REGULATED",
}

DATA_SENSITIVITY_INPUT_VALUES = DATA_SENSITIVITY_CLASSES | {"UNKNOWN"}
```

`UNKNOWN` разрешён только как промежуточный answer во время intake.

#### 6.2. Handoff rule

`project.data.sensitivity = UNKNOWN` не является готовым canonical baseline. При таком значении:

- поле считается material unresolved;
- readiness остаётся `WAITING_INPUT`;
- Browser GPT предлагает определить класс по описанию данных;
- если пользователь не уверен, он должен явно принять консервативный класс, обычно `RESTRICTED`, либо предоставить решение владельца данных;
- engine не выбирает класс молча.

Это правило не вводит новую security subsystem. Оно только устраняет ложное принятие `UNKNOWN` как classification.

#### 6.3. Questionnaire и templates

`QST-DATA-001.options` обновляется:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
SECRET
REGULATED
UNKNOWN
```

Пояснение к `UNKNOWN`: «временный ответ; до handoff потребуется определить или явно принять консервативный класс».

#### 6.4. Validation

- любое другое значение → `INVALID`;
- `UNKNOWN` → `WAITING_INPUT`, а не `INVALID`;
- `SECRET`/`REGULATED` принимаются schema и Python validator;
- существующие policy/permission checks не расширяются в этой версии;
- запрет provider accounting остаётся независимым.

### 7. Строгая `PROJECT_INPUT` schema

#### 7.1. Versioning

Целевые версии:

```text
PROJECT_INPUT.schema_version: 2
SCHEMA-PROJECT-PREPARATION-INPUT@2
Harness canonical SCHEMA_VERSION: 5
```

`PROJECT_LOCK.schema_version` становится `5` для новых handoff.

Migration ID:

```text
MIG-ENGINE-0.4.0-TO-0.4.1
```

#### 7.2. Общие правила schema

`schemas/project_input.schema.json` использует JSON Schema Draft 2020-12 и:

- `additionalProperties: false` на каждом нормативном object;
- exact `required` fields;
- enum/const для controlled values;
- typed arrays and item objects;
- `minItems` для обязательных non-empty collections;
- conditional `if/then` для Brownfield approval;
- explicit extension points только там, где они действительно нужны;
- запрет accounting fields остаётся дополнительной semantic validation, потому что они могут появиться внутри extension object.

Разрешённые extension points:

- `metadata.notes` — строка/null;
- `skills.resolutions[].configuration` — object с project-specific параметрами;
- отдельный `metadata.extensions` не добавляется в v0.4.1, чтобы не создавать свободный обход schema.

#### 7.3. Top-level fields

Разрешены только:

```text
schema_version
metadata
project
profile
architecture
technology
skills
planning
brownfield
approvals
```

Любой неизвестный top-level key, включая provider accounting, приводит к `INVALID`.

#### 7.4. Project object

Schema обязана описывать:

- `name`, `slug`, `mode`;
- `documentation`;
- `problem_statement`, `primary_outcome`;
- `users`, `scale`, `connectivity`, `platforms`, `deployment`;
- `data`, `integrations`;
- `scope`, `constraints`;
- `success_criteria`, `assumptions`, `unknowns`;
- `ambiguity_mode`.

Нормативные collections должны иметь item schema. Там, где элемент допускает строку или structured statement, используется `oneOf` с явно описанным object, а не произвольный object.

#### 7.5. Planning objects

Для каждого Work Package обязательны:

```text
title
objective
tasks
```

Для каждой Task обязательны:

```text
title
type
purpose
expected_result
scope
acceptance_criteria
verification
```

Schema описывает:

- dependency aliases;
- `scope.read/write/forbidden` как arrays of safe relative patterns;
- route capabilities;
- documentation impact;
- verification commands, expected paths и manual checks;
- rollback object;
- запрет неизвестных Task fields.

Проверка path traversal и DAG остаётся semantic Python validation, потому что JSON Schema не заменяет resolution against repository/root.

#### 7.6. Internal validation without new dependency

v0.4.1 не добавляет обязательную runtime dependency `jsonschema`.

Реализация состоит из двух согласованных слоёв:

1. строгий machine-readable `project_input.schema.json` для Browser GPT, editors и external validators;
2. расширенный `validate_project_input()` с теми же required/allowed keys, types и controlled values.

Tests обязаны доказать соответствие schema и Python validator на общей fixture matrix. Нельзя считать schema «документацией», которая не проверяется тестами.

### 8. Control-plane invariants

#### 8.1. Цель

До v0.5.1 engine ещё не предотвращает OS-level write. v0.4.1 обязан обнаружить любое изменение защищённого control plane и не принять Run как успешный.

#### 8.2. Защищённая область

Во время product Run действует правило **default-protected**:

```text
.harness/**
```

Agent не может изменять ни один control-plane path, кроме exact output channel текущего Run, описанного в 8.3. Это автоматически охватывает configuration, registries, canonical baselines, intake, sessions, skills, Work Packages, Tasks, DAGs, prompts, context, verification profiles, Runtime state, Runs, Run Plans, blockers, evidence, reports и engine resources.

Kernel-owned записи во время `verify`/`complete` не являются глобальным исключением для директорий. Каждая операция формирует phase-specific allowlist exact paths, которые имеет право создать сам Kernel, и фиксирует их ожидаемые digests в operation journal. Неожиданная запись даже в `.harness/evidence` или `.harness/runtime` считается tampering.

Также защищены generated root control views:

```text
AGENTS.md
CODEX_START.md
HANDOFF_SUMMARY.md
PROJECT.md
ARCHITECTURE.md
TECHNOLOGY.md
ROADMAP.md
STATUS.md
MANIFEST.sha256
VALIDATION_REPORT.json
```

Task может менять обычную product documentation, например `README.md` или `docs/**`, только если она входит в declared write scope. Generated Harness views не являются product documentation.

#### 8.3. Единственный agent output channel

Agent может создать или заменить только:

```text
.harness/runtime/AGENT_RESULTS/<ACTIVE-RUN-ID>.json
```

Условия:

- exact active Run ID;
- regular file, не symlink/hardlink;
- путь после `resolve()` остаётся внутри `AGENT_RESULTS`;
- schema-valid JSON/YAML-compatible JSON;
- размер ограничен разумным distribution constant;
- никакой другой `PROJECT_CONTROL_WRITE` не выдаётся product Task.

`reserve_run()` добавляет `PROJECT_CONTROL_WRITE` в prohibited operations и отдельно описывает result channel как bounded protocol exception.

#### 8.4. Snapshot structure

Существующий Run snapshot расширяется:

```yaml
snapshot:
  task_ref: TSK-...@N
  run_ref: RUN-...
  product_files: {}
  protected_control_plane:
    files:
      <relative-path>:
        sha256: <digest>
        size: <bytes>
    expected_paths: []
    allowed_agent_output_path: .harness/runtime/AGENT_RESULTS/<RUN>.json
```

Новый отдельный lifecycle entity не вводится. Используется существующий snapshot record.

#### 8.5. Проверка по фазам

**Перед `verify`:**

1. сравнить protected files с Run snapshot;
2. обнаружить changed/deleted files;
3. обнаружить unexpected files в protected directories;
4. разрешить только exact Agent Result path;
5. при tampering не запускать verification commands;
6. записать `SAFETY_VIOLATION`/Blocker evidence через Kernel.

**Перед `complete`:**

1. повторить проверку protected snapshot относительно последней Kernel-signed phase boundary;
2. разрешить только exact files, созданные самим `verify` и перечисленные в operation journal/`active_run` с ожидаемыми digests;
3. запретить любое неожиданное новое/изменённое control-plane содержимое, независимо от директории;
4. убедиться, что verified product diff не изменился;
5. убедиться, что Agent Result не заменён symlink и соответствует digest, прочитанному при validation.

#### 8.6. Failure behavior

Control-plane violation:

```text
Run → BLOCKED или FAILED_NON_RETRYABLE по характеру нарушения
Task → BLOCKED
Project → BLOCKED
Result → BLOCKED
next_route → RESTORE_CONTROL_PLANE_FROM_TRUSTED_HANDOFF_OR_RESTART_RUN
```

Engine не должен автоматически доверять изменённому Task Contract или Prompt Bundle. Recovery использует исходный handoff/backup и создаёт новую Run attempt.

#### 8.7. Ограничение гарантии

v0.4.1 даёт tamper detection, а не OS isolation. Процесс всё ещё технически может попытаться обратиться к host filesystem/network. Полная boundary вводится в v0.5.1.

### 9. Изменения по файлам движка

#### 9.1. Существующие файлы

| Файл | Изменение |
|---|---|
| `src/project_harness/util.py` | `ENGINE_VERSION = 0.4.1`, `SCHEMA_VERSION = 5`. |
| `src/project_harness/project_input.py` | conditional approvals, sensitivity sets, strict shape/type checks, schema v2 migration. |
| `src/project_harness/runtime.py` | Task `DONE`, Run `SUCCEEDED`, control-plane checks before verify/complete. |
| `src/project_harness/workspace.py` | protected control snapshot/diff helpers; regular-file and unexpected-path checks. |
| `src/project_harness/prompting.py` | prohibited `PROJECT_CONTROL_WRITE`, exact result channel metadata. |
| `src/project_harness/compiler.py` | Brownfield approval decision, accepted_by refs, lock/schema migration. |
| `src/project_harness/validation.py` | registry-driven entity status checks; control-plane/state consistency. |
| `src/project_harness/intake.py` | updated readiness and conditional approval rendering. |
| `src/project_harness/registry.py` | enforce version/digest consistency for every changed registry. |
| `registries/contracts.yaml` | register persisted `decision`; version `2 → 3`. |
| `registries/statuses.yaml` | add minimal `decision` lifecycle; version `3 → 4`; existing Task/Run values remain unchanged. |
| `schemas/project_input.schema.json` | replace permissive @1 with strict @2. |
| `templates/PROJECT_INPUT_FIELD_GUIDE.md` | five-gate Brownfield flow and sensitivity classes. |
| `templates/GPT_PREPARATION_INSTRUCTIONS.md` | explicit Brownfield Gate and `UNKNOWN` behavior. |
| `examples/*`, `fixtures/*` | schema v2 and conditional approval examples. |
| `tests/test_engine.py` | regression and migration tests below. |

#### 9.2. Resource copies

Все изменённые registries/schemas/templates/skills, которые поставляются внутри wheel, должны быть синхронно обновлены в:

```text
src/project_harness/resources/**
```

Source и embedded resource copies обязаны иметь одинаковые SHA-256 digests.

### 10. Migration v0.4.0 → v0.4.1

#### 10.1. Intake workspace

Deterministic transform:

1. `schema_version: 1 → 2`;
2. для brownfield/hybrid добавить `approvals.brownfield_baseline` с `approved: false`, если отсутствует;
3. для greenfield не требовать это поле;
4. legacy `SECRET`/`REGULATED`, если уже присутствовали, сохраняются;
5. `UNKNOWN` остаётся input, но readiness становится `WAITING_INPUT`;
6. неизвестные properties не удаляются молча — migration выдаёт точный список и требует исправления.

#### 10.2. Уже созданный handoff/project

- immutable v0.4.0 archive остаётся валидируемым через compatibility mode;
- migration не переписывает historical Run/Evidence/Task revisions;
- legacy successful statuses интерпретируются mapping-слоем;
- новый active Run создаётся только после migration;
- brownfield project без explicit baseline approval получает `WAITING_DECISION` до нового product Run;
- migration нельзя применять при active Run; сначала Run должен быть завершён, заблокирован или отменён безопасным route.

#### 10.3. Idempotency

Повторное применение migration:

- не создаёт второй approval field;
- не создаёт duplicate decision;
- не меняет timestamps уже принятого explicit approval;
- не переписывает v0.4.1 records;
- возвращает `NO_ACTION`, если состояние уже соответствует версии.

### 11. Тестовый план

#### 11.1. Status tests

1. successful Agent Result `COMPLETED` создаёт Task `DONE` и Run `SUCCEEDED`;
2. Work Package остаётся `COMPLETED`;
3. public Result остаётся `COMPLETED`;
4. new Task/Run record с `COMPLETED` отклоняется;
5. legacy v0.4.0 history читается через mapping без rewrite.

#### 11.2. Brownfield approval tests

1. greenfield с четырьмя approvals готов;
2. brownfield с четырьмя approvals возвращает `WAITING_DECISION`;
3. explicit Brownfield approval разрешает `prepare`;
4. BFB содержит `accepted_by` на отдельный Decision;
5. обычный project-definition actor не подставляется автоматически;
6. `decision` зарегистрирован в contracts/statuses и валидируется по exact storage path.

#### 11.3. Sensitivity tests

1. шесть canonical classes проходят validation;
2. `UNKNOWN` даёт `WAITING_INPUT`;
3. неизвестное значение даёт `INVALID`;
4. questionnaire options и schema enum совпадают;
5. Browser GPT fixture не принимает `UNKNOWN` как готовый baseline.

#### 11.4. Strict schema tests

1. unknown top-level property отклоняется;
2. unknown nested project/task/approval property отклоняется;
3. неправильный type отклоняется;
4. empty mandatory collection отклоняется;
5. conditional Brownfield approval работает;
6. schema fixture matrix и Python validator дают одинаковый verdict;
7. provider accounting key внутри configuration всё равно обнаруживается semantic scan.

#### 11.5. Control-plane invariant tests

1. изменение Task Contract после `next` блокирует `verify`;
2. изменение `PROJECT_LOCK` блокирует Run;
3. удаление Prompt Bundle блокирует Run;
4. unexpected file в protected directory обнаруживается;
5. symlink вместо Agent Result отклоняется;
6. exact regular Agent Result разрешён;
7. Harness-generated Evidence/Report после verify не считается tampering;
8. product diff в declared scope по-прежнему проходит;
9. изменение product files после verification требует повторного verify.

#### 11.6. Regression suite

Все 14 tests v0.4.0 должны пройти после обновления expected statuses и schema fixtures. Нельзя удалить старую проверку, чтобы получить PASS.

### 12. Критерии приёмки v0.4.1

v0.4.1 считается готовой только если:

1. новые Task records используют только registry task statuses;
2. новые Run records используют только registry run statuses;
3. legacy v0.4.0 history читается без изменения файлов;
4. Brownfield/Hybrid не получает accepted baseline без отдельного approval;
5. sensitivity taxonomy совпадает в docs, template, schema и Python;
6. `UNKNOWN` не проходит Handoff Gate;
7. `PROJECT_INPUT@2` отклоняет неизвестные и неверно типизированные fields;
8. весь `.harness/**`, а не только избранные директории, проверяется до verify и complete;
9. Agent Result остаётся единственным разрешённым agent write в `.harness`;
10. Decision contract зарегистрирован и Brownfield approval ссылается на immutable Decision;
11. все v0.4.0 regression tests и новые tests проходят;
12. wheel, embedded runtime, source resources и manifests синхронизированы;
13. README/CHANGELOG/MIGRATION/TEST_REPORT явно описывают границы версии.

### 13. Рекомендуемый порядок реализации

1. Исправить status mapping и tests.
2. Ввести sensitivity constants и readiness rule.
3. Добавить conditional Brownfield approval и decision record.
4. Подготовить strict schema v2 и shape validation.
5. Ввести protected control snapshot/diff.
6. Обновить compiler, templates, fixtures и resource copies.
7. Реализовать migration и compatibility mapping.
8. Запустить полный regression, wheel и embedded-runtime tests.
9. Обновить manifests и release reports.

Переход к v0.5.0 разрешён только после полного PASS v0.4.1.

---

<!-- SOURCE: 12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md -->

## Project Harness v0.5.0 — Implementation Levels, Stage Planning и Brownfield Maturity

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

**Базовая версия:** Project Harness Engine v0.4.1  
**Целевая версия:** v0.5.0  
**Тип релиза:** MINOR / новый управляемый lifecycle реализации  
**Статус документа:** NORMATIVE IMPLEMENTATION SPECIFICATION  
**Зависимости:** полностью принятая v0.4.1  
**Порядок реализации:** второй документ серии

### 1. Назначение версии

v0.5.0 добавляет в Project Harness явное понятие **уровня реализации проекта** и связывает его с планированием, критериями приёмки и развитием существующего проекта.

Версия должна отвечать на четыре практических вопроса:

1. до какого уровня требуется довести проект в текущем цикле;
2. какая стадия должна выполняться сейчас;
3. по каким evidence стадия считается самостоятельной и работоспособной;
4. что делать с brownfield-проектом: завершать текущую стадию, поддерживать её или переходить к следующей.

Canonical последовательность уровней:

```text
PROTOTYPE → ALPHA → BETA → MVP → RELEASE
```

В рамках Harness `MVP` означает **Production MVP**: минимальный, но пригодный для реального production-использования продукт. Это устраняет неоднозначность между Beta и MVP.

Главный принцип:

> Уровень реализации определяет глубину реализации и проверки, но не расширяет утверждённый функциональный scope проекта.

Если target выбран как `MVP`, Harness формирует маршрут:

```text
PROTOTYPE → ALPHA → BETA → MVP
```

При этом будущие стадии описываются только крупными Stage Plans. Атомарные Task Contracts, Prompt Plans и JIT Prompt Bundle создаются только для активной стадии.

### 2. Что не входит в scope

v0.5.0 не должна включать:

- автоматический запуск Codex CLI или provider API;
- выполнение произвольных команд для автоматической maturity-проверки;
- OS-level sandbox;
- Git commit, push, Pull Request или deployment;
- создание новых PROJECT skills;
- parallel scheduler, worktrees или leases;
- remote control plane;
- автоматический выбор target level без подтверждения пользователя;
- привязку уровней к конкретным технологиям, облакам или архитектурным стилям;
- обязательные Kubernetes, microservices, Redis, Kafka, CI/CD либо SaaS;
- увеличение product scope под видом более высокой стадии;
- предварительную компиляцию prompts всех будущих стадий.

Brownfield assessment в этой версии остаётся read-only: он анализирует repository inventory, документы и предоставленные evidence. Без v0.5.1 он не запускает команды автоматически.

### 3. Термины и независимые оси

Нельзя объединять в одно поле разные характеристики проекта.

| Понятие | Отвечает на вопрос |
|---|---|
| `project_scope` | Что именно должно быть реализовано? |
| `implementation_level` | Насколько глубоко и надёжно это должно быть реализовано? |
| `project_profile` | Какие обязательные правила, риски и ограничения действуют? |
| `execution_mode` | Как Harness и агент выполняют работу? |
| `deployment_model` | Где и каким способом запускается продукт? |

Эффективные требования стадии рассчитываются так:

```text
effective_stage_requirements
=
level_defaults
+ accepted_project_constraints
+ profile_mandatory_controls
+ explicit_acceptance_criteria
```

Следствия:

- `PROTOTYPE` не отменяет hard constraints;
- `RELEASE` не добавляет функций, которых нет в Project Definition;
- небольшой CLI может иметь уровень `RELEASE`;
- большой сервис может оставаться `PROTOTYPE`;
- возможности самого Harness не определяют уровень пользовательского продукта.

### 4. Canonical уровни реализации

#### 4.1. PROTOTYPE

**Цель:** быстро доказать работоспособность основного сценария и получить минимально полезный вертикальный срез.

Минимально обязательны:

- один законченный end-to-end core flow;
- самая простая подходящая архитектура;
- понятный способ локального запуска;
- smoke-проверка основного сценария;
- короткое описание запуска;
- явный список ограничений;
- допустимая область использования.

Допустимы:

- local/single-user режим;
- in-memory, файл или простая локальная БД;
- mocks и stubs вне основного сценария;
- ограниченная обработка ошибок;
- минимальный UI;
- ручные вспомогательные действия, если они документированы.

По умолчанию не требуются:

- масштабирование;
- high availability;
- полноценный RBAC;
- развитая observability;
- полная backward compatibility;
- сложные abstractions «на будущее»;
- все edge cases.

Фраза «без продуктовой безопасности» не разрешает небезопасные действия Harness. Прототип по умолчанию ограничивается local execution, public/synthetic data и отсутствием публичной экспозиции. Secrets нельзя коммитить на любой стадии.

**Stage Gate:** проект запускается из чистого accepted baseline и основной сценарий работает в заявленной области использования.

#### 4.2. ALPHA

**Цель:** рабочая версия для разработчика или небольшой внутренней группы.

Минимально обязательны:

- основные сценарии Alpha scope;
- реальная persistence для ключевых данных, если persistence требуется продукту;
- реальные core-интеграции вместо критических mock;
- базовое разделение модулей;
- configuration через файлы/env согласно проекту;
- базовая обработка ошибок и понятные логи;
- automated tests критической логики;
- integration test основного потока;
- воспроизводимое dev/test окружение;
- secrets вне repository;
- документация запуска и известных ограничений.

Breaking changes допустимы, но фиксируются в Stage Acceptance Report.

**Stage Gate:** внутренний пользователь способен установить проект и выполнить основные операции без постоянного вмешательства автора кода.

#### 4.3. BETA

**Цель:** ограниченное пилотное использование реальными пользователями или заказчиком.

Минимально обязательны:

- почти полный целевой MVP scope без необязательных функций;
- обработка основных ошибочных и граничных сценариев;
- стабилизированные внешние контракты;
- versioned migrations для значимых данных;
- regression и end-to-end tests;
- performance baseline только там, где он нужен проекту;
- authentication/permissions и data handling пропорционально рискам;
- staging либо эквивалентная безопасная среда;
- базовый monitoring;
- backup/restore либо другой recovery-механизм для значимых данных;
- проверяемый rollback;
- известные проблемы и ограничения.

**Stage Gate:** пилотные пользователи выполняют основные сценарии, critical defects основного потока отсутствуют, а неудачное обновление можно безопасно отменить.

#### 4.4. MVP

**Цель:** минимальный production-продукт, который приносит заявленную ценность настоящим пользователям.

Минимально обязательны:

- полный минимальный business-value scope;
- production persistence и migrations, если применимо;
- security controls, соответствующие данным и риску;
- воспроизводимый production deployment;
- monitoring и actionable alerts;
- проверенный backup/restore либо обоснованный recovery route;
- процедура поддержки;
- назначенный operational owner;
- release regression;
- устойчивые публичные контракты;
- правила хранения, удаления и восстановления данных;
- документированная operating boundary.

MVP не включает nice-to-have функции автоматически.

**Stage Gate:** реальный пользователь получает обещанную ценность, а владелец может развернуть, наблюдать, восстанавливать и поддерживать систему.

#### 4.5. RELEASE

**Цель:** полностью подготовленная версия в рамках утверждённого release scope.

Минимально обязательны:

- все утверждённые release commitments;
- capacity и reliability checks по фактическим требованиям;
- compatibility policy;
- полный release regression;
- security review и compliance только там, где применимы;
- recovery/DR checks согласно risk profile;
- воспроизводимая публикация релиза;
- production runbooks;
- release notes;
- ownership и escalation paths;
- пользовательская и эксплуатационная документация;
- поддерживаемая migration/upgrade policy.

`RELEASE` не означает «реализовано всё возможное». Он означает, что принятый release scope завершён и доказан.

**Stage Gate:** release checklist закрыт, обязательные проверки прошли, approvals получены, unresolved critical defects отсутствуют.

### 5. Implementation Level Registry

Добавить distribution registry:

```text
registries/implementation_levels.yaml
```

Минимальная структура:

```text
schema_version: 1
registry:
  id: REG-IMPLEMENTATION-LEVELS
  version: 1
  status: ACTIVE
  progression_policy: SEQUENTIAL
  levels:
    - id: PROTOTYPE
      ordinal: 10
      next: ALPHA
      criteria_profile: PROTOTYPE
    - id: ALPHA
      ordinal: 20
      previous: PROTOTYPE
      next: BETA
      criteria_profile: ALPHA
    - id: BETA
      ordinal: 30
      previous: ALPHA
      next: MVP
      criteria_profile: BETA
    - id: MVP
      display_name: Production MVP
      ordinal: 40
      previous: BETA
      next: RELEASE
      criteria_profile: MVP
    - id: RELEASE
      ordinal: 50
      previous: MVP
      criteria_profile: RELEASE
```

Criteria profiles должны быть декларативными и храниться в том же registry под `criteria_profiles`, чтобы `criteria_profile` не был dangling string. Минимальная форма profile:

```yaml
criteria_profiles:
  PROTOTYPE:
    mandatory_dimensions:
      - FUNCTIONALITY
      - TESTING_VERIFICATION
      - DOCUMENTATION_SUPPORT
    criteria_refs:
      - PROTOTYPE_CORE_FLOW
      - PROTOTYPE_START_INSTRUCTIONS
      - PROTOTYPE_SMOKE_CHECK
      - PROTOTYPE_LIMITATIONS
```

Полные criterion definitions выражают требования раздела 4 через stable keys, `mandatory`, `applicability` и required evidence kinds. Они не содержат технологии или новые product features. Project-specific applicability и hard-constraint overrides материализуются в Stage Gate, а не редактируют distribution registry.

Registry должен проверяться `doctor()` на:

- уникальные IDs и ordinals;
- отсутствие циклов;
- единственную начальную и конечную стадию;
- согласованность `previous`/`next`;
- существование каждого criteria profile;
- exact digest в `PROJECT_LOCK`.

### 6. Изменение опросника

Первый обязательный вопрос документации сохраняется. Target level задаётся после анализа источников и определения core outcome, но до Architecture, Technology и Work Packages.

Рекомендуемый порядок:

```text
Documentation/source question
→ Source inventory
→ Greenfield/Brownfield/Hybrid confirmation
→ Project goal and core outcome
→ Target Implementation Level
→ Material adaptive questions
→ Architecture and Technology proposals
→ Stage Plans
```

Canonical вопрос:

> Какой целевой уровень реализации требуется для текущего цикла проекта?

Варианты:

```text
PROTOTYPE
ALPHA
BETA
MVP
RELEASE
UNSURE
```

`UNSURE` не является уровнем. При нём Harness формирует рекомендацию с rationale и остаётся в `WAITING_DECISION`, пока пользователь не подтвердит canonical value.

Для `BROWNFIELD`/`HYBRID` дополнительно:

> Какой уровень реализации вы считаете текущим?

Ответ записывается как `claimed_current_level` и не считается доказанным.

Нельзя задавать вопрос о каждой стадии отдельно, если target уже определяет маршрут. Дополнительный вопрос нужен только при material ambiguity.

### 7. PROJECT_INPUT contract

После migration v0.4.1 → v0.5.0 в `PROJECT_INPUT` добавляется:

```yaml
implementation:
  target_level: MVP
  claimed_current_level: UNKNOWN
```

Правила:

- `target_level` обязателен и должен быть одним из пяти canonical levels;
- `claimed_current_level` обязателен для brownfield/hybrid;
- для greenfield допускается только `NONE`;
- `UNKNOWN` допустим для claimed value, но не для target;
- derived/runtime fields не должны редактироваться пользователем внутри intake.

`PROJECT_INPUT` не хранит `active_stage`, `highest_accepted_level` и assessment conclusions как пользовательский факт. Эти значения создаются Compiler/Runtime из evidence.

До подготовки Project Instance current target внешнего intake workspace читается из текущего `PROJECT_INPUT.yaml`. Во время `prepare` approved input сохраняется как immutable `.harness/state/PROJECT_INPUT_ACCEPTED.yaml`; его `implementation.target_level` является initial accepted target и остаётся историческим фактом, а не mutable current-cycle projection.

Versioning для этой версии:

```text
PROJECT_INPUT.schema_version: 3
SCHEMA-PROJECT-PREPARATION-INPUT@3
Harness canonical SCHEMA_VERSION: 6
Migration: MIG-ENGINE-0.4.1-TO-0.5.0
```

Migration должна добавить секцию с `target_level: null` и вернуть `WAITING_INPUT`, а не угадывать уровень. Новые handoff фиксируют `SCHEMA_VERSION: 6` и digest Implementation Level Registry в `PROJECT_LOCK`.

### 8. Canonical Stage State

В project control plane создаётся:

```text
.harness/stages/STAGE_STATE.yaml
.harness/stages/plans/
.harness/stages/acceptance/
.harness/stages/assessments/
```

Минимальный state:

```yaml
schema_version: 1
implementation:
  scale_version: 1
  target_level: MVP
  claimed_current_level: NONE
  observed_candidate_level: NONE
  highest_accepted_level: NONE
  active_stage: PROTOTYPE
  progression_policy: SEQUENTIAL
  future_stage_work: FORBIDDEN
  stage_path:
    - PROTOTYPE
    - ALPHA
    - BETA
    - MVP
  revision: 1
```

Смысл полей:

- `claimed_current_level` — мнение пользователя;
- `observed_candidate_level` — вывод assessment до Gate;
- `highest_accepted_level` — самая высокая доказанная и принятая стадия;
- `active_stage` — стадия, задачи которой разрешено выполнять;
- `target_level` — цель текущего цикла.

Для подготовленного Project Instance `.harness/stages/STAGE_STATE.yaml -> implementation.target_level` является единственным canonical current-cycle target. `.harness/config/PROJECT.yaml -> project.target_implementation_level` и `.harness/state/CURRENT_STATE.yaml -> state.target_implementation_level` являются projections и обязаны совпадать с ним. При Stage mutation, изменяющей target, все три current projections входят в один crash-consistent write set. Historical `PROJECT_INPUT_ACCEPTED.implementation.target_level` не является projection, не переписывается при `level-up` и может отличаться после смены target cycle.

Нельзя заменять их одним `current_level`.


> **Canonical storage resolution for this release:** Contract Catalog paths in §9.1 are normative. Therefore persisted directories are `PLANS`, `GATES`, `ACCEPTANCE` and `ASSESSMENTS`; lowercase forms in the earlier explanatory tree are non-normative shorthand.

### 9. Stage Plan Contract

Stage Plan — отдельный immutable revisioned artifact. Для него добавить ID prefix `STG`, если такой prefix отсутствует:

```yaml
- prefix: STG
  entity: Implementation Stage Plan
  schema_key: stage_plan
  status: ACTIVE
```

Пример:

```yaml
stage_plan:
  id: STG-PROJECT-PROTOTYPE-001
  revision: 1
  level: PROTOTYPE
  status: ACTIVE
  target_level: MVP
  baseline_ref: PJD-PROJECT-001@1
  scope_refs:
    - SCP-PROJECT-001@1
  required_outcomes:
    - working_primary_flow
    - documented_local_start
  criteria_profile_ref: REG-IMPLEMENTATION-LEVELS#PROTOTYPE
  hard_constraint_overrides: []
  work_package_outlines:
    - title: Core vertical slice
      outcome: Main user flow works end to end
  deferred_to_next_stage:
    - production monitoring
    - multi-user access
```

Для всех стадий до target создаются Stage Plan outlines. Только active stage получает:

- детальные Work Packages;
- atomic Tasks;
- Context Plans;
- Prompt Plans;
- JIT Prompt Bundles.

Stage Plan будущей стадии имеет status `PLANNED` и пересматривается после принятия предыдущей стадии. Его outline не является обязательством реализовать заранее предположенные детали.

#### 9.1. Contract catalog и storage registration

В `contracts.yaml` зарегистрировать только реально persisted artifacts:

```yaml
stage_state:
  id_prefix: null
  persistence: PERSISTENT
  lifecycle: VERSIONED_CONFIG
  storage_path: .harness/stages/STAGE_STATE.yaml
  revision_policy: VERSIONED_CONFIG
stage_plan:
  id_prefix: STG
  persistence: PERSISTENT
  lifecycle: implementation_stage
  storage_path: .harness/stages/PLANS/{id}@{revision}.yaml
  revision_policy: VERSIONED
stage_gate:
  id_prefix: GATE
  persistence: PERSISTENT
  lifecycle: verification
  storage_path: .harness/stages/GATES/{id}@{revision}.yaml
  revision_policy: VERSIONED
stage_acceptance:
  id_prefix: VAL
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/stages/ACCEPTANCE/{id}@{revision}.yaml
  revision_policy: IMMUTABLE
maturity_assessment:
  id_prefix: VAL
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/stages/ASSESSMENTS/{id}@{revision}.yaml
  revision_policy: IMMUTABLE
verification_evidence:
  id_prefix: EVD
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/evidence/{id}.yaml
  revision_policy: IMMUTABLE
```

Expected registry versions после v0.5.0:

```text
REG-ID-PREFIXES:      1 → 2   # STG
REG-CONTRACT-CATALOG: 3 → 5  # Stage contracts + normalized verification_evidence
REG-STATUSES:         4 → 5   # implementation_stage, project_execution
REG-IMPLEMENTATION-LEVELS: new, version 1
```

Каждый изменённый registry обновляется в source и embedded resources; exact version/digest добавляется в `PROJECT_LOCK`.

### 10. Stage lifecycle и statuses

В `registries/statuses.yaml` добавить группы:

```yaml
implementation_stage:
  - PLANNED
  - ACTIVE
  - VERIFYING
  - ACCEPTED
  - BLOCKED
  - SUPERSEDED

project_execution:
  - ACTIVE
  - BLOCKED
  - TARGET_LEVEL_REACHED
  - CANCELLED
```

`STATE.yaml.project_status` для новых записей проверяется по `project_execution`. Legacy v0.4.x value `COMPLETED` читается compatibility layer, но после migration не переписывается напрямую в `TARGET_LEVEL_REACHED`: сначала требуется target/Stage assessment и acceptance evidence.

Дополнительный `SATISFIED_BY_BASELINE` допускается только для brownfield assessment и должен быть отдельным acceptance disposition, а не заменой lifecycle status. Предпочтительная запись:

```yaml
status: ACCEPTED
acceptance_method: SATISFIED_BY_BASELINE
```

Transition rules:

```text
PLANNED → ACTIVE
ACTIVE → VERIFYING
VERIFYING → ACCEPTED
VERIFYING → BLOCKED
BLOCKED → ACTIVE
PLANNED/ACTIVE → SUPERSEDED
```

Пропуск уровня не допускается. Brownfield может принять предыдущие стадии через baseline evidence по очереди в одной assessment transaction, но для каждой создаётся отдельный Stage Acceptance Report.

### 11. Stage Gate

Для каждой стадии создаётся `GATE` artifact с type `STAGE_ACCEPTANCE`.

Gate проверяет:

1. required outcomes стадии;
2. stage-specific acceptance criteria;
3. project hard constraints;
4. profile-mandatory controls;
5. завершённость обязательных Work Packages;
6. отсутствие OPEN critical blockers;
7. наличие evidence;
8. допустимую область использования.

Результаты критериев:

```text
PASS
PARTIAL
FAIL
UNKNOWN
NOT_APPLICABLE
```

`NOT_APPLICABLE` требует rationale и actor/validator. `PARTIAL`, `FAIL` и `UNKNOWN` не закрывают обязательный критерий.

Stage Gate не вычисляет средний балл. Один незакрытый обязательный критерий блокирует acceptance. Если formal approval structurally/exactly valid и честно содержит такой результат, `accept-stage` обязан persisted-atomically создать новые `BLOCKED` Gate/Plan revisions, exact diagnostics, distinct `STAGE_GATE_BLOCKER` и project route `RESOLVE_STAGE_GATE`; Acceptance Report и следующая Stage не создаются. Schema error, invalid N/A, wrong exact refs и invalid evidence остаются no-mutation validation failures.

#### 11.1. Gate evidence resolution contract

Formal approval определяет заявленные criterion statuses, но не делает произвольные строки доказательствами. Для каждого `PASS` criterion и каждого global approval/Gate `evidence_ref` до первой Stage mutation выполняется fail-closed exact resolution.

Gate-eligible ref обязан:

1. иметь canonical `EVD-*` id/ref;
2. разрешаться только в exact registered path `.harness/evidence/<EVD-ID>.yaml`;
3. указывать на regular non-symlink immutable artifact без duplicate conflicting file, заявляющего тот же internal id/ref;
4. иметь envelope `verification_evidence`, `schema_version: 1`, exact internal `id == ref`, allowed `kind` из `REG-IMPLEMENTATION-LEVELS.evidence_kinds` и closing `status: PASS`;
5. иметь non-empty provenance с source type/ref/producer и хотя бы один digest-verifiable immutable source/report/artifact binding;
6. иметь exact `base_revision` формы `tree:sha256:<64 lowercase hex>`, равный Gate/current accepted product baseline;
7. mapping’ить requested criterion в `criterion_refs`;
8. иметь kind, входящий хотя бы в один `required_evidence_kind` exact registry criterion либо explicit hard-constraint override.

Global refs также полностью разрешаются и должны mapping’ить хотя бы один current mandatory criterion с разрешённым kind. Один missing, legacy, malformed, wrong-kind, wrong-subject, stale, non-positive, USER_CLAIM-only, source-tampered или duplicate-conflicting ref блокирует весь Gate. Наличие файла не создаёт automatic `PASS`; formal approval остаётся обязательным.

Historical evidence без `schema_version` остаётся readable, но не Gate-eligible. Explicit unsupported schema version является malformed normalized record, а не legacy. Required outcomes и profile controls не материализуются этим шагом; их closure остаётся отдельной следующей частью G-01.

### 12. Stage Acceptance Report

При успешной Gate создаётся immutable report:

```yaml
stage_acceptance:
  id: VAL-PROJECT-PROTOTYPE-001
  revision: 1
  level: PROTOTYPE
  status: PASS
  acceptance_method: EXECUTED_STAGE_WORK
  baseline_revision: tree:sha256:...
  accepted_at: 2026-08-17T12:00:00Z
  decision_ref: DEC-PROJECT-STAGE-PROTOTYPE-001@1
  evidence_refs:
    - EVD-PROJECT-SMOKE-001
  evidence_bindings:
    - ref: EVD-PROJECT-SMOKE-001
      path: .harness/evidence/EVD-PROJECT-SMOKE-001.yaml
      sha256: sha256:89abcdef0123456789abcdef0123456789abcdef0123456789abcdef01234567
  permitted_use:
    users: [DEVELOPER]
    environments: [LOCAL]
    data_classes: [PUBLIC]
    data_constraints: [SYNTHETIC_ONLY]
  known_limitations:
    - no authentication
    - local storage only
  next_stage_gaps:
    - real persistence
    - critical integration tests
```

Четыре обязательных результата принятой стадии:

1. immutable baseline;
2. Stage Acceptance Report;
3. Known Limitations and Permitted Use Boundary;
4. Next Stage Gap Backlog.

Accepted Gate и report дополнительно сохраняют одинаковые sorted `evidence_refs` и immutable `{ref, path, sha256}` bindings. `validate-project` повторно разрешает accepted closure и возвращает `FAIL` при deletion, content/source tampering, digest mismatch либо Gate/Acceptance divergence. Accepted history автоматически не переписывается.

Это позволяет остановиться на любой стадии без ложного утверждения о более высокой готовности. `SYNTHETIC_ONLY` является ограничением происхождения данных, а не новым sensitivity class; canonical sensitivity taxonomy v0.4.1 остаётся неизменной.

#### 12.1. Exact immutable assessment binding

Для `acceptance_method: SATISFIED_BY_BASELINE` approval обязан содержать:

```yaml
assessment_ref: VAL-PROJECT-MATURITY-001@1
assessment_digest: sha256:<64 lowercase hex>
```

Нормативная grammar `assessment_ref` — `<assessment-id>@<positive-integer-revision>` с canonical decimal revision без leading zero. Единственный допустимый storage lookup:

```text
.harness/stages/ASSESSMENTS/<assessment-id>@<revision>.yaml
```

До recovery/new Stage mutation exact resolver обязан одновременно подтвердить:

1. requested ref является canonical и не содержит wildcard/prefix/suffix ambiguity;
2. filename exact path равен requested ref плюс `.yaml`;
3. document имеет ровно один top-level envelope `maturity_assessment`;
4. internal `id` равен requested assessment id;
5. internal `revision` имеет integer type и равен requested positive revision;
6. `assessment_digest` имеет canonical `sha256:<64 lowercase hex>` форму и равен SHA-256 exact file bytes.

Prefix glob, latest-candidate selection и lexicographic fallback запрещены. Любое нарушение отклоняется до Stage mutation. Каждый созданный Stage Acceptance Report получает exact canonical ref из validated resolver result, а не непроверенное исходное поле approval. Exact resolver не заменяет freshness/current-context validation из следующего раздела.

#### 12.2. Brownfield assessment freshness и exact current-context binding

Для `acceptance_method: SATISFIED_BY_BASELINE` exact resolved assessment допускает acceptance только после read-only preflight, выполненного до любого canonical acceptance write. Одновременно должны выполняться все условия:

1. `assessment.status == COMPLETED`;
2. `assessment.repository_revision == current canonical product-tree digest`;
3. `approval.baseline_revision` равен тому же current digest;
4. `assessment.target_level == STAGE_STATE.implementation.target_level`;
5. `assessment.previous_highest_accepted_level == STAGE_STATE.implementation.highest_accepted_level` до transaction;
6. `assessment.claimed_current_level` равен сохранённому accepted user claim из immutable `PROJECT_INPUT_ACCEPTED.yaml`;
7. `assessment.proposed_active_stage`, current `active_stage`, `stage_path` и requested accepted levels не противоречат sequential progression от current accepted baseline;
8. requested accepted level не превышает `highest_satisfied_candidate_level`;
9. mandatory criteria принимаемых levels не используют evidence, помеченное stale или связанное с другой base revision, включая соответствующие assessment warnings.

`highest_satisfied_candidate_level` не является доверенным shortcut: acceptance пересчитывает последовательный highest candidate по exact mandatory criteria из canonical implementation-level registry. `PASS` требует evidence refs; `NOT_APPLICABLE` требует rationale и validator. Это не расширяет Gate evidence model и не запускает repository commands.

Если хотя бы одно условие нарушено:

- command возвращает structured `STALE`/validation result с stable reason code, field, `actual`, `expected`, source assessment ref/digest и detected current context;
- Decision, Acceptance Report, accepted Stage Plan/Gate revisions и next-stage activation не создаются;
- `highest_accepted_level`, `active_stage` и их projections не изменяются;
- исходная immutable assessment revision остаётся byte-preserved;
- создаётся новая immutable assessment revision с `validation_kind: BROWNFIELD_BASELINE_FRESHNESS`, `source_assessment_ref`, `source_assessment_digest`, original `repository_revision`, detected current revision и полным списком причин.

Staleness revision является validation record в том же immutable contract family; она не подменяет source revision данными другого tree и не становится current assessment автоматически. Новый `assess-maturity` на current tree/context создаёт новую exact assessment revision, которая снова может авторизовать acceptance при валидном approval.

Для multi-level Brownfield acceptance один exact assessment обязан быть current для всего contiguous sequential slice. Все context и per-level closure checks выполняются до первого canonical replace; частичное принятие prefix levels запрещено.

### 13. Ограничение active-stage work

Каждый Work Package, Task, Run Plan и Prompt Plan получает поле:

```yaml
implementation_stage: PROTOTYPE
```

Runtime разрешает claim/compile/execute только если:

```text
artifact.implementation_stage == STAGE_STATE.active_stage
```

Prompt Compiler добавляет обязательный блок:

```text
CURRENT_IMPLEMENTATION_STAGE: PROTOTYPE
TARGET_IMPLEMENTATION_LEVEL: MVP

Реализуй только требования текущей стадии и Task Contract.
Не добавляй Alpha/Beta/MVP/Release механизмы без прямого hard constraint.
Все полезные будущие улучшения запиши в Next Stage Gap Backlog, но не реализуй.
```

Проверка scope должна классифицировать сознательную реализацию future-stage-only work как `STAGE_SCOPE_VIOLATION`.

Hard constraint может потребовать более сильный контроль раньше. Например, обработка regulated data может потребовать security controls уже в Prototype. Такой контроль записывается как explicit override, а не как скрытый переход стадии.

### 14. Brownfield Maturity Assessment

#### 14.1. Назначение

Assessment определяет не «красивое название версии», а фактически доказанную зрелость проекта.

Он анализирует измерения:

```text
FUNCTIONALITY
ARCHITECTURE_MAINTAINABILITY
DATA_MIGRATIONS
TESTING_VERIFICATION
SECURITY_PRIVACY
DEPLOYMENT_OPERABILITY
RECOVERY
DOCUMENTATION_SUPPORT
RELEASE_EVIDENCE
```

Для каждого уровня и измерения используются критерии registry.

#### 14.2. Источники evidence в v0.5.0

Допустимы:

- read-only repository inventory;
- существующие manifests и configuration;
- test directories и test reports;
- CI reports, предоставленные как source artifacts;
- release/deployment документы;
- runbooks;
- migration files;
- user answers с пометкой `USER_CLAIM`;
- внешние evidence с provenance.

Недопустимо автоматически запускать команды. Если evidence требует execution, criterion получает `UNKNOWN` и формируется точечный вопрос либо manual evidence request.

Assessment inventory может читать historical/legacy evidence, но новый Stage Gate принимает только normalized immutable artifact следующего минимального contract:

```yaml
verification_evidence:
  schema_version: 1
  id: EVD-PROJECT-PROTOTYPE-CORE-001
  ref: EVD-PROJECT-PROTOTYPE-CORE-001
  kind: TEST_REPORT
  status: PASS
  provenance:
    source_type: PROVIDED_TEST_REPORT
    source_ref: VAL-PROJECT-TEST-001
    producer: ACT-VALIDATOR-001
  base_revision: tree:sha256:<64 lowercase hex>
  criterion_refs: [PROTOTYPE_CORE_FLOW]
  outcome_refs: []
  profile_control_refs: []
  source_bindings:
    - ref: VAL-PROJECT-TEST-001
      sha256: sha256:<64 lowercase hex>
  created_at: 2026-08-18T12:00:00Z
```

`USER_CLAIM`, stale evidence, failed/blocked report и artifact другого product baseline не закрывают mandatory Gate item. Legacy record без `schema_version` остаётся readable, но должен быть normalized новым immutable evidence artifact с source binding; in-place historical rewrite запрещён.

#### 14.3. Алгоритм

Target загружается по workspace type: для prepared Project Instance — из canonical Stage State; для внешнего intake workspace без Stage State — из текущего `PROJECT_INPUT.yaml`. Assessment prepared project не использует immutable accepted input как current target.

1. Зафиксировать repository/base revision.
2. Собрать inventory и предоставленные evidence.
3. Оценить каждый criterion как `PASS/PARTIAL/FAIL/UNKNOWN/NOT_APPLICABLE`.
4. Для каждого уровня проверить все обязательные критерии.
5. Найти `highest_satisfied_candidate_level`: самый высокий последовательный уровень, где каждый обязательный criterion имеет `PASS` или обоснованный `NOT_APPLICABLE`.
6. Записать `observed_candidate_level` как описательную оценку текущей формы проекта; она может быть выше satisfied candidate, но не даёт acceptance.
7. Представить assessment пользователю, не изменяя `highest_accepted_level`.
8. Перед Brownfield Baseline acceptance повторно связать exact assessment с current product-tree digest, target, previous accepted level, accepted user claim и sequential Stage context.
9. Только после успешного freshness preflight и Brownfield Baseline approval создать отдельные Stage Acceptance Reports и атомарно повысить `highest_accepted_level` до подтверждённого satisfied candidate.

Нельзя:

- усреднять баллы;
- использовать номер версии как evidence;
- принимать `beta` в README как доказательство;
- считать наличие Dockerfile достаточным для MVP/Release;
- подменять отсутствующее evidence уверенным предположением.

#### 14.4. Результат assessment

```yaml
maturity_assessment:
  id: VAL-PROJECT-MATURITY-001
  revision: 1
  repository_revision: git:abc123
  claimed_current_level: BETA
  observed_candidate_level: BETA
  highest_satisfied_candidate_level: ALPHA
  previous_highest_accepted_level: NONE
  proposed_active_stage: BETA
  target_level: RELEASE
  confidence: MEDIUM
  criteria_results:
    PROTOTYPE: []
    ALPHA: []
    BETA:
      - criterion_ref: BETA_END_TO_END_REGRESSION
        mandatory: true
        status: UNKNOWN
        evidence_refs: []
        rationale: execution evidence was not supplied
  dimensions:
    FUNCTIONALITY: BETA
    ARCHITECTURE_MAINTAINABILITY: BETA
    TESTING_VERIFICATION: ALPHA
    SECURITY_PRIVACY: ALPHA
    DEPLOYMENT_OPERABILITY: PROTOTYPE
    RECOVERY: PROTOTYPE
    DOCUMENTATION_SUPPORT: BETA
  blocking_gaps:
    - end-to-end regression evidence missing
    - rollback not verified
    - backup restore evidence missing
  recommended_route: COMPLETE_CURRENT_STAGE
```

`confidence` является информативным полем и не заменяет criterion statuses. Assessment сам не записывает новый `highest_accepted_level`; это делает approval transaction на основании exact assessment revision/digest и exact current-context preflight. Для supplied evidence assessment сохраняет status, criterion refs, base revision и stale marker в evidence inventory.

При обнаружении drift старый assessment не редактируется. Новая immutable validation revision сохраняет source ref/digest и original repository revision, а в `staleness` записывает detected current revision, reason codes, assessment context и current context. Она имеет status `STALE` и не обновляет Stage State.

### 15. Brownfield decision routes

После assessment Harness выбирает один из маршрутов:

```text
COMPLETE_CURRENT_STAGE
MAINTAIN_CURRENT_STAGE
ADVANCE_TO_NEXT_STAGE
TARGET_ALREADY_REACHED
STABILIZE_CURRENT_STAGE
```

Правила:

- если текущая candidate stage не принята — `COMPLETE_CURRENT_STAGE`;
- если accepted stage требует багфиксов без повышения — `MAINTAIN_CURRENT_STAGE`;
- если accepted stage стабильна и target выше — `ADVANCE_TO_NEXT_STAGE`;
- если target уже достигнут или превышен — `TARGET_ALREADY_REACHED`;
- если evidence показывает деградацию accepted baseline — `STABILIZE_CURRENT_STAGE`.

Выбор target ниже уже принятого уровня не должен ухудшать проект. Harness сообщает, что target достигнут, либо пользователь создаёт отдельный fork вне этого lifecycle.

#### 15.1. Governed `MAINTAIN_CURRENT_STAGE` lifecycle

Same-level maintenance является публичным bounded route для уже принятого product scope. Он не является `accept-stage`, не повышает level и не изменяет accepted maturity.

Публичные operations:

```bash
project-harness start-maintenance  --project <root> --plan <record>
project-harness cancel-maintenance --project <root> --approval <record>
```

Tasks исполняются существующими `next`, `verify`, `complete`. Start plan проходит отдельную strict schema validation до mutation и exact-bound как минимум к:

- текущему `highest_accepted_level`;
- current target из canonical Stage State;
- `last_acceptance_ref`;
- accepted product scope ref;
- objective/rationale и formal `DEC-*`/`ACT-*` approval fields;
- одному atomic Work Package и atomic Tasks;
- verification, rollback и cancel constraints.

Start разрешён только при существующем accepted level, отсутствии active Run, active stage-planning application, Gate transition и другого open maintenance route. Requested `implementation_stage` плана, WP и каждой Task точно равен `highest_accepted_level`; next/future-stage work запрещён.

Governed start materializes immutable `MAINTAIN_CURRENT_STAGE` Decision, maintenance plan revision, WP, Tasks, DAG, Verification Profiles, Context Plans, Prompt Plans, indexes/current state/`NEXT_TASK` и ровно один idempotent first JIT bundle. Все maintenance executable artifacts содержат exact `implementation_stage`, `maintenance_route: MAINTAIN_CURRENT_STAGE` и `maintenance_plan_ref`. Canonical Stage State, target, acceptance reports, accepted Stage Plan/Gate revisions и completed Runs не входят в maintenance mutation set.

После PASS последней mandatory Task runtime не вызывает Gate readiness. Он переводит WP в `COMPLETED`, создаёт immutable `MAINTENANCE_COMPLETION` report с start Decision, Task/Task Report, Run и evidence refs, очищает maintenance current state и восстанавливает previous valid route/status (`TARGET_LEVEL_REACHED` либо waiting active-stage planning/Gate state).

Cancel требует strict exact-bound `CANCEL_MAINTENANCE` Decision. До completed product-changing Task open Tasks/WP могут получить новые terminal `CANCELLED` revisions и previous route восстанавливается. Если completed Task помечена product-changing, Task Report фиксирует product changes либо незавершённая попытка оставила product drift, silent cancel запрещён. Требуется completion или уже существующий governed compensation/rollback route; автоматический rollback не изобретается.

Повтор identical plan/Decision идемпотентен и не создаёт duplicate WP/Tasks/Runs/JIT. Reuse тех же immutable ids с другим request digest отклоняется. Historical maintenance plan/WP/Task/Run/report revisions сохраняются.

### 16. Level-up

После достижения target проект получает status:

```text
TARGET_LEVEL_REACHED
```

Это не окончательное «навсегда завершено». Команда level-up:

1. требует новый target выше `highest_accepted_level`;
2. сохраняет предыдущие accepted baselines;
3. строит sequential stage path до нового target;
4. создаёт/пересматривает Stage Plans;
5. активирует только следующую стадию;
6. не изменяет completed Runs;
7. помечает future Prompt Plans, построенные на старых assumptions, как `STALE`.

Canonical update выполняется одной Stage transaction: новый target записывается в `STAGE_STATE.implementation.target_level`, а `PROJECT.project.target_implementation_level` и `CURRENT_STATE.state.target_implementation_level` синхронизируются как projections того же значения. `PROJECT_INPUT_ACCEPTED.yaml` не переписывается и сохраняет initial accepted target.

Предлагаемые команды CLI:

```bash
project-harness stage-status --project <root>
project-harness assess-maturity --workspace <intake>
project-harness accept-stage --project <root> --level PROTOTYPE --approval <record>
project-harness level-up --project <root> --target MVP --approval <record>
project-harness start-maintenance --project <root> --plan <record>
project-harness cancel-maintenance --project <root> --approval <record>
```

`accept-stage` не принимает простое `--yes`; ему нужен формализованный approval record или безопасный интерактивный flow, создающий такой record.

### 17. Planner changes

В `planner.py`:

- добавить построение `stage_path` от начального уровня до target;
- создать Stage Plan для каждого уровня пути;
- детализировать Work Packages только активной стадии;
- маркировать все artifacts `implementation_stage`;
- после последней ordinary mandatory Task детерминированно оценивать exact final-baseline Gate readiness и создавать stable/idempotent Work Package/Task `STAGE_ACCEPTANCE_PREPARATION` только для реально missing evidence items;
- не добавлять продуктовые задачи только ради будущей стадии;
- не создавать Task DAG следующей стадии до acceptance текущей.

При переходе:

```text
accepted baseline
→ recompute next Stage Plan delta
→ explicit review if material change
→ create next-stage atomic plan
```

### 18. Runtime changes

В `runtime.py`:

- общий workspace-aware target loader читает prepared-project current target из Stage State, а intake target — из текущего `PROJECT_INPUT.yaml`;
- `_next_runnable()` фильтрует Tasks по active stage;
- `_update_wp_status()` не переводит проект целиком в `COMPLETED` при завершении промежуточной стадии;
- после завершения последней ordinary Task active stage запускается deterministic Gate-readiness evaluation: missing evidence создаёт один governed `STAGE_ACCEPTANCE_PREPARATION` route, complete evidence переводит Stage прямо в `VERIFYING`;
- успешный Stage Gate меняет `highest_accepted_level` и active stage;
- при достижении target возвращается `TARGET_LEVEL_REACHED`;
- same-level maintenance запускается public strict start operation, создаёт отдельный accepted-stage WP/Tasks/DAG/VFP/CTX/PPL и ровно один first JIT;
- maintenance scheduler использует accepted-level execution fence и выбирает только Tasks exact open maintenance plan;
- final mandatory maintenance Task создаёт immutable completion report, очищает maintenance current state и восстанавливает previous route без Gate acceptance/level change;
- strict cancel допускается только до completed/observed product-changing work и никогда не выполняет automatic rollback;
- переход должен быть atomic: acceptance report, Stage State revision и next-stage activation либо записываются вместе, либо не записываются.
- runtime verification evidence записывается в normalized `verification_evidence` form с exact product-tree revision после verification/scope checks;
- Task evidence mapping’ит runtime verification profile/control, но не объявляет automatically все Stage criteria;
- если после verification product tree изменился, раннее evidence остаётся immutable history и не считается fresh для final Stage Gate;
- preparation Task использует accepted Technology/Verification baseline, normal Task lifecycle и current-stage-only scope; после PASS kernel materializes immutable subject-mapped evidence bindings;
- structurally valid open formal review persists Gate-related BLOCKED transaction; dedicated `resume-stage-gate` revalidates baseline/evidence and creates new ACTIVE preparation or VERIFYING revisions;
- execution/safety blocker `block/resume` semantics не используются для Gate blocker.

#### 18.1. Crash-consistent local Stage transaction

Для stage-mutating commands local filesystem transaction до первого canonical replace сохраняет journal и immutable backups. Journal включает operation/request identity, полный ordered write set, existed-before markers, backup/staged paths, old/new digests, status/timestamps, result digest и per-entry apply/recovery state. Durable `PREPARED` journal, каждый required backup и каждый staged digest повторно проверяются до перехода в `APPLYING`.

`COMMITTED` допустим только после проверки всего new write set; `ROLLED_BACK` — только после проверки всего old write set. Derived rendering выполняется после canonical commit и при failure возвращает recoverable warning, не отменяя committed fact.

### 19. Compiler и artifact changes

Обновить:

- `compiler.py` — создание Stage State, Stage Plans и stage-aware Work Packages;
- `prompting.py` — current-stage fence;
- `render.py` — разделы Current Stage, current Target Level, initial accepted Target Level, Permitted Use и Deferred Work;
- `validation.py` — registry, transition, canonical-target projection и cross-reference checks; historical initial target не сравнивается как current projection;
- `archive.py` — включение `.harness/stages` в handoff;
- `project_input.schema.json` — новая `implementation` section;
- template и demo fixture — target level;
- `PROJECT_LOCK` — digest implementation levels registry.

Новые schemas:

```text
schemas/stage_state.schema.json
schemas/stage_plan.schema.json
schemas/stage_acceptance.schema.json
schemas/maturity_assessment.schema.json
schemas/gate_evidence.schema.json
```

Если проект избегает множества schema-файлов, допускается объединить Stage State/Plan/Acceptance в один `implementation_stage.schema.json`, но contracts должны остаться отдельными по смыслу.

### 20. Migration v0.4.1 → v0.5.0

Migration должна быть явной и идемпотентной.

Для intake workspace:

- добавить пустой `implementation.target_level`;
- для greenfield установить `claimed_current_level: NONE`;
- для brownfield/hybrid установить `claimed_current_level: UNKNOWN`;
- вернуть `WAITING_INPUT` до подтверждения target.

Для подготовленного проекта без выполнявшихся задач:

- потребовать target level;
- пересобрать plan и prompts;
- старые future planning artifacts пометить `SUPERSEDED`.

Для проекта с completed history:

- сохранить history;
- создать provisional assessment;
- не угадывать accepted level только по completed Tasks;
- потребовать Brownfield-style baseline review текущего состояния;
- активировать route после approval.

Migration не должна автоматически присваивать `RELEASE` старому проекту.

### 21. Failure и recovery

| Ситуация | Результат |
|---|---|
| Target level отсутствует | `WAITING_INPUT` |
| `UNSURE` без подтверждения | `WAITING_DECISION` |
| Будущая стадия пытается стать active | validation failure |
| Structurally valid formal review имеет mandatory `UNKNOWN/PARTIAL/FAIL` | persisted atomic Plan/Gate/project `BLOCKED`, exact diagnostics, `STAGE_GATE_BLOCKER`, `RESOLVE_STAGE_GATE`, no acceptance |
| Gate evidence ref отсутствует, legacy/malformed или находится не по exact canonical path | validation failure до Stage mutation |
| Evidence kind не удовлетворяет `required_evidence_kinds` exact criterion | validation failure |
| Evidence не mapping’ит requested criterion или provenance/source binding malformed | validation failure |
| Evidence имеет `FAIL`/`BLOCKED`/другой non-positive status | `BLOCKED` / validation failure |
| Accepted evidence/source удалено или изменено | `validate-project` `FAIL`; accepted records не переписываются |
| Evidence не соответствует base revision | assessment `STALE`; такое evidence не закрывает mandatory criteria |
| Assessment tree/target/previous accepted/claim context отличается от current | baseline preflight `STALE`, immutable validation revision, zero acceptance mutation |
| Hard constraint отсутствует в criteria profile | добавить explicit override; не игнорировать |
| Level-up target не выше accepted level | `NO_ACTION` или validation failure |
| Попытка downgrade | `TARGET_ALREADY_REACHED`; без изменений |
| Malformed formal approval: schema/N/A/exact-ref/evidence error | validation failure, zero mutation |
| `resume-stage-gate` при evidence gaps | new revisions, `BLOCKED → ACTIVE`, idempotent `STAGE_ACCEPTANCE_PREPARATION` |
| `resume-stage-gate` при закрытых evidence needs | new revisions, `BLOCKED → VERIFYING` |
| Ordinary `resume` применён к Gate blocker | validation failure; use dedicated recovery |
| Atomic transition оборван | deterministic full-new commit либо full-old rollback |

#### 21.1. Deterministic reconciliation

Перед любой новой Stage mutation и при `validate-project` non-terminal transaction reconciles до terminal state. Если все expected new digests уже присутствуют, recovery завершает commit; иначе при целых backups полностью восстанавливает old state. Повреждённый journal/backup или неоднозначная transaction sequence блокируют mutation и не допускают guess-based repair. Validation дополнительно сверяет current Stage indexes/files, Acceptance Reports, `CURRENT_STATE` и `NEXT_TASK` с последним completed transition. Повтор committed transaction id возвращает сохранённый idempotent result; rolled-back id требует нового formal approval.

### 22. Тестовый план

#### 22.1. Registry и schema

- порядок пяти уровней валиден;
- duplicate ordinal и cycle отклоняются;
- target принимает только canonical levels;
- `UNSURE` не проходит в approved input;
- greenfield claimed level не может быть Beta;
- brownfield без claimed value остаётся `WAITING_INPUT`.

#### 22.2. Greenfield planning

- target `PROTOTYPE` создаёт один Stage Plan;
- target `MVP` создаёт четыре Stage Plans в правильном порядке;
- только Prototype имеет detailed Task DAG;
- будущие stages не имеют compiled prompts;
- Task другой стадии не выдаётся через `next`;
- hard constraint может добавить обязательный early control без stage jump.

#### 22.3. Stage Gates

- last ordinary Task + missing final evidence создаёт один `STAGE_ACCEPTANCE_PREPARATION` WP и exactly one first JIT Task/bundle;
- repeated readiness evaluation не создаёт duplicate;
- complete preparation refresh’ит Gate revision и приводит к `VERIFYING`/exact draft;
- все mandatory PASS закрывают Gate;
- valid formal review с одним `UNKNOWN` atomically persists Gate/Plan/project BLOCKED без acceptance;
- malformed formal review не меняет state;
- evidence added + `resume-stage-gate` возвращает ACTIVE preparation либо VERIFYING и затем позволяет acceptance;
- `NOT_APPLICABLE` без rationale отклоняется;
- Stage Acceptance Report содержит permitted use и limitations;
- следующий уровень не активируется до commit Stage State transaction;
- preparation не содержит future-stage work; target stage после successful recovered Gate приводит к `TARGET_LEVEL_REACHED`.
- вымышленный `EVD-*` ref отклоняется;
- existing evidence wrong kind отклоняется;
- evidence без requested criterion mapping отклоняется;
- missing/malformed provenance отклоняется;
- evidence tree A при Gate tree B отклоняется;
- failed/blocked evidence отклоняется;
- exact normalized evidence нужного kind/base/mapping проходит;
- global Gate refs полностью разрешаются и wrong mapping/dangling ref блокируют acceptance;
- historical legacy evidence читается, но не закрывает новый Gate;
- explicit unsupported evidence schema version не маскируется как legacy;
- tampering/deletion evidence или source report после acceptance делает `validate-project` `FAIL`;
- runtime evidence использует exact post-verification baseline, не mapping’ит Stage criteria автоматически и становится stale после product change.

#### 22.4. Brownfield

- claimed и observed уровни хранятся отдельно;
- maturity не определяется по README/version name;
- отсутствие runtime evidence даёт `UNKNOWN`;
- самый слабый mandatory dimension ограничивает accepted level;
- несколько предыдущих стадий могут быть `ACCEPTED/SATISFIED_BY_BASELINE` с отдельными reports;
- при одновременно существующих assessment revisions `@1` и `@10` ref `@1` разрешается только в exact file `@1`; digest `@10` отклоняется без mutation;
- unversioned/wildcard-like ref, wrong envelope, internal id/revision mismatch и wrong/noncanonical digest отклоняются до Stage mutation;
- Stage Acceptance Report сохраняет exact validated assessment ref;
- assessment tree A после изменения product tree до B возвращает `STALE`, сохраняет source revision A и не создаёт Decision/Acceptance/Stage mutation;
- повторный assessment на tree B снова допускает acceptance с approval для B;
- изменение target, previous accepted level или accepted claimed context после assessment делает старую revision stale;
- stale/other-base external evidence не закрывает mandatory baseline criteria;
- multi-level baseline acceptance по одному exact current assessment либо принимает весь requested sequential slice, либо не принимает ни одной Stage;
- approval baseline, отличный от current product tree, возвращает `STALE` и не создаёт acceptance artifacts;
- assessment со status, отличным от `COMPLETED`, не может авторизовать acceptance;
- requested accepted level выше `highest_satisfied_candidate_level` возвращает `STALE`;
- current-stage completion и next-stage advance различаются.

#### 22.5. Level-up и maintenance

- bugfix остаётся на текущем уровне;
- level-up сохраняет старый baseline;
- level-up активирует только ближайшую следующую стадию;
- downgrade не создаёт destructive plan;
- prompts старой future-stage revision становятся stale;
- initial prepared project имеет одинаковый target в Stage State, PROJECT и CURRENT_STATE;
- после `PROTOTYPE → MVP` три current projections равны `MVP`, а immutable PROJECT_INPUT_ACCEPTED сохраняет initial `PROTOTYPE`;
- новое prepared-project assessment после level-up рассчитывает route относительно `MVP`, а external intake продолжает читать target из `PROJECT_INPUT.yaml`;
- `validate-project` отклоняет divergence PROJECT или CURRENT_STATE от Stage State, но не historical initial target;
- public `start-maintenance` exact-bound к accepted level/current target/last acceptance/scope и создаёт Decision/WP/Tasks/plans/one JIT без изменения Stage State;
- все maintenance executable artifacts содержат accepted `implementation_stage` и `maintenance_route: MAINTAIN_CURRENT_STAGE`;
- `next → verify → complete` закрывает maintenance отдельным immutable report и не запускает Stage Gate/acceptance;
- formal pre-product-change cancel восстанавливает previous route; completed/observed или uncommitted product changes блокируют silent cancel без history rewrite;
- level-up блокируется только open maintenance WP и разрешён после `COMPLETED`/valid `CANCELLED`/`SUPERSEDED`;
- exact replay maintenance plan/Decision не создаёт duplicate WP/Tasks/Runs/JIT, historical revisions сохраняются.

### 23. Критерии приёмки v0.5.0

Версия считается готовой, когда:

1. target implementation level обязателен перед product planning;
2. пять уровней определены единым registry и проходят doctor;
3. target `MVP` создаёт последовательный путь Prototype → Alpha → Beta → MVP;
4. только active stage получает атомарные задачи и JIT prompts;
5. Stage Gate не использует среднее значение и требует evidence по каждому mandatory criterion;
6. каждая принятая стадия создаёт immutable baseline, report, permitted-use boundary и next-stage gaps;
7. brownfield хранит claimed, observed и accepted maturity отдельно;
8. assessment не выполняет команды автоматически;
9. same-level maintenance и level-up являются разными routes;
10. historical Runs и accepted stages не переписываются;
11. tests покрывают greenfield, brownfield, Gate и level-up;
12. v0.4.1 workflows мигрируют без потери history;
13. prepared-project current target имеет одну authority в Stage State, а PROJECT и CURRENT_STATE проходят projection-consistency validation;
14. immutable PROJECT_INPUT_ACCEPTED сохраняет initial accepted target после level-up;
15. baseline acceptance разрешает только exact canonical assessment revision, digest exact file bytes и сохраняет тот же validated ref в Acceptance Report;
16. assessment freshness связывает acceptance с current product tree, target, previous accepted level, accepted claim и sequential context; drift создаёт immutable STALE validation revision без acceptance mutation;
17. stale/other-base evidence не может закрыть mandatory criteria, а multi-level baseline acceptance является all-or-nothing по одному exact current assessment.
18. каждый Gate-closing ref разрешается в normalized immutable `EVD-*` artifact по exact registered path и проходит status/provenance/source/base/subject/kind validation;
19. accepted Gate и Acceptance Report сохраняют одинаковые exact evidence refs и SHA-256 bindings, а `validate-project` обнаруживает последующее deletion/tampering;
20. historical legacy evidence остаётся readable, но не закрывает новый Gate без нового normalized immutable artifact;
21. runtime Task evidence связано с exact verification baseline, не promoted automatically в final Stage criterion evidence и становится stale после product-tree change;
22. public same-level maintenance start создаёт exact accepted-stage Decision/WP/Tasks/DAG/VFP/CTX/PPL и ровно один first JIT без изменения target/accepted maturity;
23. maintenance `next → verify → complete` создаёт immutable completion report и восстанавливает previous route без Stage acceptance;
24. level-up blocked только пока maintenance WP open и разрешён после terminal completion/cancel;
25. formal cancel после completed/observed либо uncommitted product-changing work отклоняется без history rewrite и automatic rollback;
26. identical maintenance plan/Decision replay не создаёт duplicate WP/Tasks/Runs/JIT, accepted reports и pre-existing completed Runs остаются byte/digest unchanged.

### 24. Порядок реализации

1. Зафиксировать registry и data model.
2. Обновить `PROJECT_INPUT`, questionnaire и migration.
3. Реализовать Stage State и schemas.
4. Добавить Stage Plan generation.
5. Сделать planner/runtime stage-aware.
6. Добавить Prompt Compiler stage fence.
7. Реализовать Stage Gate и Acceptance Report.
8. Реализовать read-only Brownfield Maturity Assessment.
9. Реализовать same-level maintenance и level-up.
10. Обновить render/archive/validation/doctor.
11. Добавить fixtures и полный test matrix.
12. Выпустить migration notes и обновлённую пользовательскую документацию.

Следующая версия v0.5.1 может использовать Stage requirements и active-stage Task Contract, но не должна менять смысл уровней реализации.
