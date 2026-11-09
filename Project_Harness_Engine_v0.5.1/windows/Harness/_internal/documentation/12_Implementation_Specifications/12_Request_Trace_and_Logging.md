# Сквозной Request Trace и логирование

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

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

## 2. Correlation model

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

## 3. Request Trace Contract

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

## 4. Event types

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

## 5. Логировать обязательно

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

## 6. Не логировать

- секреты, credentials, private keys, access tokens;
- полный sensitive context без необходимости;
- скрытый chain-of-thought модели;
- неограниченные raw dumps;
- содержимое файлов, если достаточно hash/path/diff summary;
- provider billing, monetary cost или token-usage accounting.

Допустимы технические context compatibility metrics, например размер materialized packet, только для предотвращения overflow. Они не образуют cost ledger.

## 7. Data classification и redaction

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

## 8. Append-only semantics

Исторические events, runs и evidence не переписываются. Исправление создаёт новый event:

```text
EVENT_RECORDED
→ CORRECTION_EVENT references original
```

Current state является materialized view поверх append-only event log и canonical snapshots.

## 9. Tool Invocation Contract

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

## 10. Логирование стадий проекта

Intake, architecture, planning, execution, integration, release и maintenance используют один event envelope. Для non-code stages evidence может быть:

- accepted answer batch;
- schema validation;
- decision approval;
- link/reference validation;
- dry-run output;
- source inventory hash.

«Все этапы покрыты логами» не означает запуск тестов для каждого Markdown-файла; это означает, что переходы и результаты доказуемы.

## 11. Status and recovery queries

Control request `status` читает trace/state и возвращает:

- current project phase;
- active Work Package;
- running/blocked tasks;
- last completed result;
- next recommended route;
- outstanding decisions;
- known failures/risks.

`resume` использует blocker and trace refs, а не свободное угадывание, где остановилась работа.

## 12. Retention

Рекомендуемые классы:

```text
PERMANENT_PROJECT_HISTORY
RELEASE_LIFETIME
ACTIVE_WORK_LIFETIME
EPHEMERAL_DEBUG
```

Canonical decisions, task reports, run summaries, evidence digests и state events сохраняются как project history. Большие raw tool outputs могут иметь TTL при наличии digest и policy.

## 13. Критерии приёмки

1. Один correlation ID связывает Request, Plan, Work Package, Task, Run, Evidence и Result.
2. Все state transitions имеют events.
3. Actual writes логируются и сравниваются со scope.
4. Секреты и hidden reasoning не попадают в trace.
5. History append-only; corrections не переписывают прошлое.
6. Status/resume восстанавливаются из state/trace после cold start.
7. Logging работает для code и non-code stages.
8. Token/cost accounting отсутствует в contracts и reports.
