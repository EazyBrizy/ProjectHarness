# JIT-компиляция task-specific prompts

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Harness не должен хранить огромное количество заранее скомпилированных промтов. Canonical backlog состоит из Work Packages и Task Contracts. Prompt bundle создаётся непосредственно перед исполнением только для READY task или утверждённого safe parallel batch.

Принцип:

```text
Store tasks, policies and reusable prompt modules.
Compile execution prompt just in time.
Retain immutable bundle only for an actual run.
```

## 2. Уровни Prompt IR

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

## 3. Минимальный набор Prompt Specs

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

## 4. Условия компиляции

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

## 5. Prompt Plan Contract

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

## 6. Compiled Prompt Bundle

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

## 7. Обязательное содержание task prompt

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

## 8. Lifecycle prompt artifacts

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

## 9. Invalidation

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

## 10. Retention policy

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

## 11. Алгоритм compiler

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

## 12. Ошибки компиляции

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

## 13. Критерии приёмки

1. Неисполненные future tasks не имеют обязательных compiled bundles.
2. READY task компилируется reproducibly из canonical inputs.
3. Любое material изменение инвалидирует plan/bundle.
4. Один base Prompt Spec обслуживает множество tasks без копирования.
5. Bundle содержит task purpose, result, verification, documentation duty и stop protocol.
6. Silent context truncation невозможен.
7. Compiled bundle привязан к одному run и не переписывается.
8. Compiler errors являются structured blockers, а не свободным текстом.
