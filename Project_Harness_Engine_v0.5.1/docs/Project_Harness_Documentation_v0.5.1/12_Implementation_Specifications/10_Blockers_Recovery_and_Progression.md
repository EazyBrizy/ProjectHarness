# Blockers, восстановление и гарантированный следующий маршрут

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Harness не гарантирует, что любой исходный подход выполним. Он гарантирует, что пользователь никогда не получает тупиковый статус без объяснения и следующего маршрута.

Инвариант:

> У каждого незавершённого состояния есть хотя бы один безопасный recovery route: исправить prerequisite, изменить подход, изменить scope, отложить, отменить или запросить разрешённое исключение.

## 2. Blocker classes

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

## 3. Blocker Contract

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

## 4. Разрешённые recovery actions

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

## 5. Отсутствие «100% blocker»

Даже если исходный запрос невозможен, Harness возвращает варианты:

- реализовать безопасную альтернативу;
- сузить scope;
- заменить технологию;
- подготовить недостающую среду;
- перенести выполнение;
- отменить task с сохранением причины;
- пересмотреть requirement через formal decision.

Это не означает обязательное ослабление hard constraint.

## 6. Scope блокировки

Blocker имеет минимально необходимый scope:

```text
TASK_LOCAL
WORK_PACKAGE_LOCAL
TRACK_LOCAL
PROJECT_WIDE
HARNESS_DISTRIBUTION
```

Project-wide blocker допустим только при нарушении global invariant, повреждении canonical state или отсутствии обязательного Project Definition/Architecture baseline. Обычная blocked task не останавливает независимые READY tasks.

## 7. Safe state and compensation

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

## 8. Retry policy

Retry допустим только если:

- ошибка классифицирована retryable;
- idempotency strategy известна;
- base revisions не изменились;
- capability grants ещё действуют;
- side effects отсутствуют или compensated;
- retry budget policy не превышена;
- повтор имеет отличимый `run_id` и увеличенный `attempt_no`.

Нельзя бесконечно повторять deterministic failure.

## 9. Resume workflow

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

## 10. Независимые задачи

При blocker Harness показывает:

- recommended recovery route;
- независимые READY tasks;
- риск переключения контекста;
- будет ли blocked work package оставаться current.

Автоматическое переключение допустимо только при project policy. Иначе пользователь получает выбор, но blocked state сохраняется.

## 11. User-facing blocked result

```text
Статус: BLOCKED
Остановлено на: проверке готовности backend-задачи
Причина: API-контракт ещё не принят
Уже сделано: изменений кода нет
Рекомендуется: выбрать формат пагинации и принять CNT-SEARCH@2
Другие варианты: уменьшить scope или отложить feature
Можно продолжить независимо: задача обновления glossary
```

## 12. Критерии приёмки

1. Каждый blocker имеет class, evidence, options, recommendation и resume condition.
2. Hard constraint не ослабляется автоматически.
3. Blocker scope минимален и не замораживает независимый проект без причины.
4. Runtime failure сохраняет safe state и compensation status.
5. Retry создаёт новый Run и проходит current revision checks.
6. Resume пересобирает stale prompt/context.
7. Даже невозможный подход имеет alternative/change-scope/cancel route.
8. Result Envelope понятно объясняет причину и варианты устранения.
