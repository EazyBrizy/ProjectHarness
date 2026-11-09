# Codex Agent Adapter

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Codex является первым целевым agent executor, но не частью universal kernel. Harness подготавливает task, prompt, context, skills, permissions и verification; Codex выполняет bounded work и возвращает structured result.

Разделение ответственности:

```text
Harness decides what, why, scope, readiness and permissions.
Codex decides how to implement within that bounded contract.
Harness validates, records and selects the next route.
```

## 2. Что Codex получает

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

## 3. Что Codex не решает

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

## 4. Adapter Profile

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

## 5. Adapter execution protocol

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

## 6. Codex Task Result Contract

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

## 7. AGENTS.md

Harness генерирует короткий `AGENTS.md` для cold start:

- project identity and current baseline refs;
- как найти `.harness/` state;
- запрет выбирать tasks вне assigned contract;
- правила scope, decisions, blockers and result schema;
- команды проверки состояния;
- ссылки на более узкие nested guidance.

`AGENTS.md` не копирует всю документацию и не содержит mutable current task. Current task передаётся через bundle/context.

## 8. Tool mediation

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

## 9. Stop conditions

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

## 10. Verification separation

Codex может запускать targeted tests, но Harness:

- independently validates result schema;
- compares actual diff to declared scope;
- checks baseline/new failures;
- verifies documentation impact;
- computes task completion;
- chooses next route.

Для high-risk tasks Validator может быть отдельным run/agent or deterministic toolchain.

## 11. Errors and resume

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

## 12. Security and provenance

Adapter trace фиксирует:

- adapter/profile revision;
- rendered bundle digest;
- context packet digests;
- capability grants;
- tool calls;
- actual writes;
- normalized output digest.

Secrets передаются только через reference-based tool mechanism и не включаются в prompt text без explicit policy.

## 13. Browser handoff и local runtime v0.4.1

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

## 14. Критерии приёмки

1. Codex получает один bounded Task Contract и понимает purpose/result/verification.
2. Codex не выбирает governance decisions or next task.
3. Tool calls проходят через grants and scope checks.
4. Structured output обязателен и schema-valid.
5. Harness independently подтверждает claims and completion.
6. Material ambiguity вызывает stop signal, а не скрытый выбор.
7. Cold start восстанавливается из canonical state, не из памяти session.
8. Adapter version and provenance присутствуют в Run Trace.
