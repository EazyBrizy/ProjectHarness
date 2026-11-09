# Project Harness v0.4.1 — Contract Hardening

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

## 1. Назначение версии

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

## 2. Не входит в scope

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

## 3. Подтверждённые дефекты v0.4.0

### 3.1. Task/Run status mismatch

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

### 3.2. Brownfield Baseline Gate не подтверждается отдельно

Документация требует Brownfield Baseline Gate, но `PROJECT_INPUT` содержит только четыре approvals:

```text
project_definition
architecture_baseline
technology_baseline
codex_handoff
```

Compiler создаёт `brownfield_baseline.status: ACCEPTED`, хотя отдельного подтверждения пользователя нет.

### 3.3. Data sensitivity taxonomy расходится

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

### 3.4. `project_input.schema.json` слишком свободная

Schema v0.4.0 проверяет в основном top-level envelope и разрешает произвольные свойства. Фактические правила находятся в `project_input.py`, поэтому schema, template и Python validation могут расходиться.

### 3.5. Control plane защищён инструкцией, но не invariant-проверкой

Product snapshot исключает `.harness/` и generated root files. Agent получает текстовый запрет изменять control plane, но `validate-project` не доказывает, что Task/Prompt/Lock/registries не были изменены между Run reservation и completion.

OS-level enforcement появится только в v0.5.1. В v0.4.1 требуется детерминированное обнаружение tampering и запрет завершения Run.

## 4. Нормализация statuses

### 4.1. Canonical mapping

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

### 4.2. Изменения runtime

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

### 4.3. Backward compatibility

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

## 5. Brownfield Baseline approval

### 5.1. Условное обязательное approval

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

### 5.2. Input contract

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

### 5.3. Canonical decision record

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

### 5.4. Регистрация Decision contract

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

### 5.5. Readiness behavior

- missing semantic fields → `WAITING_INPUT`;
- complete semantic fields, но отсутствует Brownfield approval → `WAITING_DECISION`;
- `prepare` при missing approval поднимает `WaitingDecision`;
- greenfield не должен ждать Brownfield approval;
- Browser GPT должен показать baseline summary, repository revision, test evidence, known defects/gaps и documentation conflicts до запроса approval.

## 6. Единая sensitivity taxonomy

### 6.1. Разделение classification и epistemic state

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

### 6.2. Handoff rule

`project.data.sensitivity = UNKNOWN` не является готовым canonical baseline. При таком значении:

- поле считается material unresolved;
- readiness остаётся `WAITING_INPUT`;
- Browser GPT предлагает определить класс по описанию данных;
- если пользователь не уверен, он должен явно принять консервативный класс, обычно `RESTRICTED`, либо предоставить решение владельца данных;
- engine не выбирает класс молча.

Это правило не вводит новую security subsystem. Оно только устраняет ложное принятие `UNKNOWN` как classification.

### 6.3. Questionnaire и templates

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

### 6.4. Validation

- любое другое значение → `INVALID`;
- `UNKNOWN` → `WAITING_INPUT`, а не `INVALID`;
- `SECRET`/`REGULATED` принимаются schema и Python validator;
- существующие policy/permission checks не расширяются в этой версии;
- запрет provider accounting остаётся независимым.

## 7. Строгая `PROJECT_INPUT` schema

### 7.1. Versioning

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

### 7.2. Общие правила schema

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

### 7.3. Top-level fields

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

### 7.4. Project object

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

### 7.5. Planning objects

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

### 7.6. Internal validation without new dependency

v0.4.1 не добавляет обязательную runtime dependency `jsonschema`.

Реализация состоит из двух согласованных слоёв:

1. строгий machine-readable `project_input.schema.json` для Browser GPT, editors и external validators;
2. расширенный `validate_project_input()` с теми же required/allowed keys, types и controlled values.

Tests обязаны доказать соответствие schema и Python validator на общей fixture matrix. Нельзя считать schema «документацией», которая не проверяется тестами.

## 8. Control-plane invariants

### 8.1. Цель

До v0.5.1 engine ещё не предотвращает OS-level write. v0.4.1 обязан обнаружить любое изменение защищённого control plane и не принять Run как успешный.

### 8.2. Защищённая область

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

### 8.3. Единственный agent output channel

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

### 8.4. Snapshot structure

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

### 8.5. Проверка по фазам

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

### 8.6. Failure behavior

Control-plane violation:

```text
Run → BLOCKED или FAILED_NON_RETRYABLE по характеру нарушения
Task → BLOCKED
Project → BLOCKED
Result → BLOCKED
next_route → RESTORE_CONTROL_PLANE_FROM_TRUSTED_HANDOFF_OR_RESTART_RUN
```

Engine не должен автоматически доверять изменённому Task Contract или Prompt Bundle. Recovery использует исходный handoff/backup и создаёт новую Run attempt.

### 8.7. Ограничение гарантии

v0.4.1 даёт tamper detection, а не OS isolation. Процесс всё ещё технически может попытаться обратиться к host filesystem/network. Полная boundary вводится в v0.5.1.

## 9. Изменения по файлам движка

### 9.1. Существующие файлы

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

### 9.2. Resource copies

Все изменённые registries/schemas/templates/skills, которые поставляются внутри wheel, должны быть синхронно обновлены в:

```text
src/project_harness/resources/**
```

Source и embedded resource copies обязаны иметь одинаковые SHA-256 digests.

## 10. Migration v0.4.0 → v0.4.1

### 10.1. Intake workspace

Deterministic transform:

1. `schema_version: 1 → 2`;
2. для brownfield/hybrid добавить `approvals.brownfield_baseline` с `approved: false`, если отсутствует;
3. для greenfield не требовать это поле;
4. legacy `SECRET`/`REGULATED`, если уже присутствовали, сохраняются;
5. `UNKNOWN` остаётся input, но readiness становится `WAITING_INPUT`;
6. неизвестные properties не удаляются молча — migration выдаёт точный список и требует исправления.

### 10.2. Уже созданный handoff/project

- immutable v0.4.0 archive остаётся валидируемым через compatibility mode;
- migration не переписывает historical Run/Evidence/Task revisions;
- legacy successful statuses интерпретируются mapping-слоем;
- новый active Run создаётся только после migration;
- brownfield project без explicit baseline approval получает `WAITING_DECISION` до нового product Run;
- migration нельзя применять при active Run; сначала Run должен быть завершён, заблокирован или отменён безопасным route.

### 10.3. Idempotency

Повторное применение migration:

- не создаёт второй approval field;
- не создаёт duplicate decision;
- не меняет timestamps уже принятого explicit approval;
- не переписывает v0.4.1 records;
- возвращает `NO_ACTION`, если состояние уже соответствует версии.

## 11. Тестовый план

### 11.1. Status tests

1. successful Agent Result `COMPLETED` создаёт Task `DONE` и Run `SUCCEEDED`;
2. Work Package остаётся `COMPLETED`;
3. public Result остаётся `COMPLETED`;
4. new Task/Run record с `COMPLETED` отклоняется;
5. legacy v0.4.0 history читается через mapping без rewrite.

### 11.2. Brownfield approval tests

1. greenfield с четырьмя approvals готов;
2. brownfield с четырьмя approvals возвращает `WAITING_DECISION`;
3. explicit Brownfield approval разрешает `prepare`;
4. BFB содержит `accepted_by` на отдельный Decision;
5. обычный project-definition actor не подставляется автоматически;
6. `decision` зарегистрирован в contracts/statuses и валидируется по exact storage path.

### 11.3. Sensitivity tests

1. шесть canonical classes проходят validation;
2. `UNKNOWN` даёт `WAITING_INPUT`;
3. неизвестное значение даёт `INVALID`;
4. questionnaire options и schema enum совпадают;
5. Browser GPT fixture не принимает `UNKNOWN` как готовый baseline.

### 11.4. Strict schema tests

1. unknown top-level property отклоняется;
2. unknown nested project/task/approval property отклоняется;
3. неправильный type отклоняется;
4. empty mandatory collection отклоняется;
5. conditional Brownfield approval работает;
6. schema fixture matrix и Python validator дают одинаковый verdict;
7. provider accounting key внутри configuration всё равно обнаруживается semantic scan.

### 11.5. Control-plane invariant tests

1. изменение Task Contract после `next` блокирует `verify`;
2. изменение `PROJECT_LOCK` блокирует Run;
3. удаление Prompt Bundle блокирует Run;
4. unexpected file в protected directory обнаруживается;
5. symlink вместо Agent Result отклоняется;
6. exact regular Agent Result разрешён;
7. Harness-generated Evidence/Report после verify не считается tampering;
8. product diff в declared scope по-прежнему проходит;
9. изменение product files после verification требует повторного verify.

### 11.6. Regression suite

Все 14 tests v0.4.0 должны пройти после обновления expected statuses и schema fixtures. Нельзя удалить старую проверку, чтобы получить PASS.

## 12. Критерии приёмки v0.4.1

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

## 13. Рекомендуемый порядок реализации

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
