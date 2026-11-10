# Project Harness v0.5.0 — Implementation Levels, Stage Planning и Brownfield Maturity

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

## 1. Назначение версии

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

## 2. Что не входит в scope

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

## 3. Термины и независимые оси

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

## 4. Canonical уровни реализации

### 4.1. PROTOTYPE

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

### 4.2. ALPHA

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

### 4.3. BETA

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

### 4.4. MVP

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

### 4.5. RELEASE

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

## 5. Implementation Level Registry

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

## 6. Изменение опросника

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

## 7. PROJECT_INPUT contract

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

## 8. Canonical Stage State

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

## 9. Stage Plan Contract

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

### 9.1. Contract catalog и storage registration

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

## 10. Stage lifecycle и statuses

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

## 11. Stage Gate

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

### 11.1. Gate evidence resolution contract

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

## 12. Stage Acceptance Report

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

### 12.1. Exact immutable assessment binding

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

### 12.2. Brownfield assessment freshness и exact current-context binding

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

## 13. Ограничение active-stage work

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

## 14. Brownfield Maturity Assessment

### 14.1. Назначение

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

### 14.2. Источники evidence в v0.5.0

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

### 14.3. Алгоритм

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

### 14.4. Результат assessment

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

## 15. Brownfield decision routes

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

### 15.1. Governed `MAINTAIN_CURRENT_STAGE` lifecycle

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

## 16. Level-up

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

## 17. Planner changes

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

## 18. Runtime changes

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

### 18.1. Crash-consistent local Stage transaction

Для stage-mutating commands local filesystem transaction до первого canonical replace сохраняет journal и immutable backups. Journal включает operation/request identity, полный ordered write set, existed-before markers, backup/staged paths, old/new digests, status/timestamps, result digest и per-entry apply/recovery state. Durable `PREPARED` journal, каждый required backup и каждый staged digest повторно проверяются до перехода в `APPLYING`.

`COMMITTED` допустим только после проверки всего new write set; `ROLLED_BACK` — только после проверки всего old write set. Derived rendering выполняется после canonical commit и при failure возвращает recoverable warning, не отменяя committed fact.

## 19. Compiler и artifact changes

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

## 20. Migration v0.4.1 → v0.5.0

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

## 21. Failure и recovery

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

### 21.1. Deterministic reconciliation

Перед любой новой Stage mutation и при `validate-project` non-terminal transaction reconciles до terminal state. Если все expected new digests уже присутствуют, recovery завершает commit; иначе при целых backups полностью восстанавливает old state. Повреждённый journal/backup или неоднозначная transaction sequence блокируют mutation и не допускают guess-based repair. Validation дополнительно сверяет current Stage indexes/files, Acceptance Reports, `CURRENT_STATE` и `NEXT_TASK` с последним completed transition. Повтор committed transaction id возвращает сохранённый idempotent result; rolled-back id требует нового formal approval.

## 22. Тестовый план

### 22.1. Registry и schema

- порядок пяти уровней валиден;
- duplicate ordinal и cycle отклоняются;
- target принимает только canonical levels;
- `UNSURE` не проходит в approved input;
- greenfield claimed level не может быть Beta;
- brownfield без claimed value остаётся `WAITING_INPUT`.

### 22.2. Greenfield planning

- target `PROTOTYPE` создаёт один Stage Plan;
- target `MVP` создаёт четыре Stage Plans в правильном порядке;
- только Prototype имеет detailed Task DAG;
- будущие stages не имеют compiled prompts;
- Task другой стадии не выдаётся через `next`;
- hard constraint может добавить обязательный early control без stage jump.

### 22.3. Stage Gates

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

### 22.4. Brownfield

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

### 22.5. Level-up и maintenance

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

## 23. Критерии приёмки v0.5.0

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

## 24. Порядок реализации

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
