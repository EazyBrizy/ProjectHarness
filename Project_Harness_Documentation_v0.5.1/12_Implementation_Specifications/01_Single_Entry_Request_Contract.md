# Единая точка входа и Request Contract

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

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

## 2. Разделение понятий

Маршрутизация строится по трём независимым осям.

### 2.1. Request Class

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

### 2.2. Request Mode

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

### 2.3. Internal Operation

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

## 3. Request Contract

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

### 3.1. Обязательные поля

- `raw_text` сохраняется неизменяемо как исходный source.
- `request_class`, `mode` и `correlation_id` обязательны до построения Request Plan.
- `idempotency_key` обязателен для повторяемых transport calls. Если adapter получает его в header/metadata, он сохраняет то же значение в Request record до planning.
- `project_ref` может отсутствовать только для общего вопроса или до выбора/создания Project Instance.
- Любая классификационная неопределённость фиксируется, а не скрывается.
- Полный chain-of-thought модели не сохраняется. Допускается только краткое проверяемое `rationale_summary`.

## 4. Request lifecycle

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

### 4.1. Правила переходов

1. `RECEIVED → CLASSIFYING` происходит без side effects.
2. `CLASSIFIED → PLANNING` допускается только после выбора Project Instance или Intake Session.
3. `PLANNED → READY` требует пройденных route gates.
4. `READY → EXECUTING` требует capability grants и current revision check.
5. `WAITING_*` не теряет уже подготовленный plan и имеет `resume_condition`.
6. Любой терминальный статус создаёт Result Envelope.
7. Повторная отправка одного и того же `idempotency_key` не создаёт дубликаты Work Package или side effects.

## 5. Классификация обычного сообщения

### 5.1. Правило по умолчанию

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

### 5.2. Алгоритм классификации

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

## 6. Request Plan Contract

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

### 6.1. Инварианты Request Plan

- Каждая route имеет одну операцию и один проверяемый output type.
- Зависимости routes образуют DAG.
- Side-effect route не может предшествовать планированию и readiness gates.
- `QUERY` обычно содержит одну route `ANSWER`.
- `PROJECT_START` обязательно содержит `START_INTAKE` и `ASK_QUESTION_BATCH`.
- Request Plan не создаёт заранее prompts для всех будущих tasks.
- Смена base project revision делает plan `STALE`, если затронуты его входы.

## 7. Единая точка входа как API

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

## 8. Ошибки и остановки

| Ситуация | Поведение |
|---|---|
| Не выбран project, но запрос явно относится к одному из нескольких | `WAITING_USER_INPUT`, показать короткий список проектов. |
| Запрос смешивает product change и Harness maintenance | Разделить на два Request Plan либо остановить и предложить выбор порядка. |
| Пользователь просит execute, но project не прошёл readiness | Перевести в intake/planning route, не выполнять write. |
| Запрос требует необратимого side effect | Добавить approval route. |
| Classification confidence низкая, но ambiguity нематериальна | Применить policy default и показать assumption. |
| Classification ambiguity меняет scope/архитектуру | Остановить affected route и задать уточнение. |

## 9. Пользовательское представление

Пользователь видит не внутренний список операций, а:

```text
Распознано: задача разработки
Режим: выполнение
План: 3 атомарные задачи, одна из них готова сейчас
Требуется решение: нет
Текущий шаг: реализация backend-поиска
```

Внутренние IDs показываются компактно и только когда полезны для traceability.

## 10. Критерии приёмки

1. Один natural-language endpoint обрабатывает все Request Classes.
2. Обычный вопрос не создаёт Work Package и Task.
3. Development request создаёт Request, Request Plan и correlation trace.
4. Mixed-plane request не выполняется одной неявной transaction.
5. Side effects не начинаются до режима `EXECUTE`, gates и grants.
6. Любой terminal или waiting state возвращает Result Envelope.
7. Повтор запроса с тем же idempotency key не дублирует изменение.
8. Classification и planning покрыты deterministic и behavioral fixtures.

## 11. Минимальные тестовые сценарии

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
