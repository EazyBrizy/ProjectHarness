# Result Envelope и пользовательские статусы

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

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

## 2. Публичные статусы

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

## 3. Result Envelope Contract

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

## 4. Обязательные блоки по статусам

### 4.1. `ANSWERED`

Обязательны:

- `summary` с самим ответом;
- `changes` пустой;
- `verification` может иметь `NOT_APPLICABLE`;
- source/document refs, если ответ основан на project state;
- `next_step` только если естественно следует из вопроса.

### 4.2. `COMPLETED`

Обязательны:

- понятное описание результата;
- `added`, `changed`, `removed`;
- verification status и evidence;
- documentation status;
- точный следующий route либо `NONE`.

### 4.3. `PARTIAL`

Обязательны:

- что уже завершено;
- что осталось;
- почему весь scope не завершён;
- сохранён ли safe state;
- следующий route;
- tasks, которые можно продолжать независимо.

### 4.4. `WAITING_DECISION`

Обязательны:

- один material question или компактная согласованная группа;
- объяснение влияния ответа;
- 2–4 понятных варианта;
- рекомендуемый вариант и его последствия;
- возможность ответа «не знаю»;
- exact resume condition.

### 4.5. `BLOCKED`

Обязательны:

- `stopped_at`;
- причина и evidence;
- затронутый scope;
- безопасно выполненная часть;
- recovery options;
- recommendation;
- independent ready tasks;
- resume condition.

### 4.6. `FAILED_RECOVERABLE`

Обязательны:

- классифицированная ошибка;
- номер попытки;
- были ли side effects;
- выполнена ли компенсация;
- допустим ли retry;
- альтернативный route, если retry нецелесообразен.

## 5. Mapping внутренних статусов

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

## 6. Правила формулировки

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

## 7. Агрегация Work Package

```text
All mandatory tasks DONE and acceptance PASS → COMPLETED
Some mandatory tasks DONE, remainder READY/BLOCKED → PARTIAL
No task executed, material decision required → WAITING_DECISION
No task executed, technical prerequisite absent → BLOCKED
All requested behavior already exists and verified → NO_ACTION
```

Optional task не препятствует `COMPLETED`, если aggregation rule явно помечает его optional.

## 8. Пример незавершённого результата

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

## 9. Версионирование и совместимость

- Result Envelope имеет независимый `schema_version`.
- Добавление optional поля является backward-compatible.
- Переименование статуса или изменение его смысла требует migration.
- Agent adapter может возвращать provider-specific payload, но kernel обязан нормализовать его в Result Envelope.
- Renderer для CLI, chat и API не меняет смысл полей.

## 10. Критерии приёмки

1. Каждый route возвращает schema-valid Result Envelope.
2. `COMPLETED` невозможен без удовлетворения mandatory acceptance criteria.
3. `BLOCKED` невозможен без recovery options и resume condition.
4. `WAITING_DECISION` содержит варианты и понятное объяснение.
5. Changes перечисляют добавленное, изменённое и удалённое.
6. Documentation status присутствует даже при `NOT_APPLICABLE`.
7. Work Package aggregation детерминирован и покрыт fixtures.
8. Пользовательский текст остаётся понятным без чтения внутренних reports.

## 14. v0.4.1 lifecycle clarification

Public `Result.status = COMPLETED` не является универсальным internal lifecycle status. Успешные Task и Run обязаны использовать соответственно `DONE` и `SUCCEEDED`; Work Package, Task Report, Agent Task Result и public Result сохраняют `COMPLETED`. Validator применяет status group из `registries/statuses.yaml` по contract type.
