# Project Harness v0.6.1 — Declarative PROJECT Skill Authoring, Evaluation и Activation

**Базовая версия:** Project Harness Engine v0.6.0  
**Целевая версия:** v0.6.1  
**Тип релиза:** PATCH / completion of PROJECT skill lifecycle  
**Статус документа:** NORMATIVE IMPLEMENTATION SPECIFICATION  
**Зависимости:** полностью принятые v0.4.1–v0.6.0  
**Порядок реализации:** пятый документ серии

## 1. Назначение версии

v0.6.1 реализует ранее заблокированные маршруты:

```text
EXTEND
CREATE
```

для **declarative PROJECT skills**.

Полный путь:

```text
Skill Gap Analysis
→ reuse/configure rejection with rationale
→ DRAFT
→ VALIDATING
→ VALIDATED or REJECTED
→ explicit activation approval
→ ACTIVE
→ dependent task readiness refresh
```

Skill остаётся повторно используемым project-local workflow. Одноразовая работа продолжает описываться Task Contract и не превращается в skill.

## 2. Не входит в scope

v0.6.1 не должна включать:

- authoring UNIVERSAL или PROFILE skills;
- публикацию skills в общий marketplace/registry;
- произвольный Python/JavaScript/plugin code внутри skill;
- загрузку binary/tool package из skill;
- автоматическую активацию без approval;
- автоматическое обучение/оптимизацию prompt по production outcomes;
- online A/B routing;
- создание skill для каждой Task;
- расширение Task capabilities через skill;
- remote multi-user authoring workflow;
- provider-specific executable hooks;
- изменение engine/runtime code как часть skill definition;
- автоматическую миграцию completed Runs на новую revision.

## 3. Допустимый тип skill

В v0.6.1 authoring разрешён только для:

```yaml
level: PROJECT
representation: DECLARATIVE
namespace: project:<project-id>
```

Skill является YAML/JSON contract, который собирает уже поддерживаемые элементы:

- applicability rules;
- input references;
- output schema reference;
- bounded procedure steps;
- stop conditions;
- required minimal capabilities;
- allowed/prohibited scope;
- prompt module references или project-local declarative prompt sections;
- verification profile;
- adapter compatibility;
- evaluation suite.

Skill не может исполнять код от имени Kernel. Все команды остаются в Task/Verification contracts и проходят обычный sandbox/capability control.

## 4. Когда разрешены CREATE и EXTEND

Skill Gap Analysis обязан применять порядок:

```text
REUSE → CONFIGURE → EXTEND → CREATE → TASK_ONLY
```

### 4.1. EXTEND

Разрешён, когда:

- существует ACTIVE base skill;
- общий workflow совпадает;
- проекту нужны ограниченные дополнительные steps, stop conditions, scope restrictions или verification;
- изменение не должно менять UNIVERSAL/PROFILE source.

### 4.2. CREATE

Разрешён, когда:

- workflow действительно повторяем в проекте;
- минимум две ожидаемые Task либо одна Task плюс обоснованная будущая повторяемость подтверждены;
- REUSE/CONFIGURE/EXTEND не выражают contract без искажения;
- есть owner;
- output и success criteria определимы.

### 4.3. TASK_ONLY

Обязателен, когда:

- работа одноразовая;
- процедура слишком специфична одной Task;
- repeatability не доказана;
- material workflow ещё не стабилен;
- безопасные boundaries не определены.

Harness не должен создавать DRAFT skill только потому, что пользователь использовал слово «skill».

## 5. Project Skill Contract

```yaml
skill:
  id: SKL-PROJECT-CSV-IMPORT
  revision: 1
  namespace: project:example
  level: PROJECT
  representation: DECLARATIVE
  status: DRAFT

  name: CSV import implementation
  purpose: Repeatable implementation and verification of project CSV imports
  owner_ref: ACT-MAINTAINER-001
  applies_to_task_types:
    - IMPLEMENT
    - FIX
    - VALIDATE
  technology_refs:
    - TEC-TYPESCRIPT
    - TEC-POSTGRES

  input_contract:
    required_refs:
      - TASK_CONTRACT
      - CONTEXT_PLAN
    optional_refs:
      - MIGRATION_BASELINE

  output_contract_ref: SCHEMA-AGENT-TASK-RESULT@1
  required_capabilities:
    - FILESYSTEM_READ
    - FILESYSTEM_WRITE
    - COMMAND_EXECUTE

  allowed_scope_patterns:
    - src/import/**
    - tests/import/**
  prohibited_operations:
    - GIT_PUSH
    - PR_CREATE
    - DEPLOY

  procedure:
    steps:
      - id: inspect_contract
        kind: READ_CONTEXT
        instruction: Read accepted import contract and current implementation.
        required_inputs: [TASK_CONTRACT, CONTEXT_PLAN]
      - id: implement_bounded_change
        kind: APPLY_TASK_CHANGE
        instruction: Implement only the task-defined import change.
      - id: verify_output
        kind: RUN_DECLARED_VERIFICATION
        instruction: Run verification from the task contract.
    stop_conditions:
      - MISSING_REQUIRED_CONTRACT
      - MATERIAL_SCHEMA_AMBIGUITY
      - REQUIRED_CAPABILITY_MISSING
      - WRITE_SCOPE_EXPANSION_REQUIRED

  verification_profile_ref: VFP-CODE-TARGETED-001
  adapter_compatibility:
    - ADP-CODEX-CLI-LOCAL-001
  evaluation_suite_ref: EVS-SKL-PROJECT-CSV-IMPORT-001@1

  provenance:
    action: CREATE
    gap_analysis_ref: VAL-PROJECT-SKILL-GAP-001
    created_by: ACT-USER-001
  version_policy: SEMANTIC
```

Ни `procedure.steps`, ни prompt sections не имеют права переопределять Task Contract, Project Profile или prohibited operations.

## 6. Declarative step vocabulary

Чтобы не превратить YAML в скрытый programming language, v0.6.1 поддерживает ограниченную модель step:

```text
READ_CONTEXT
CHECK_PRECONDITION
APPLY_TASK_CHANGE
RUN_DECLARED_VERIFICATION
PRODUCE_RESULT
STOP_WITH_BLOCKER
```

Human-readable `instruction` допускается, но `kind` определяет semantics. Нельзя добавлять loops, imports, arbitrary command, dynamic code expression или network call внутрь skill.

Пример:

```yaml
- id: verify_output
  kind: RUN_DECLARED_VERIFICATION
  source: TASK_CONTRACT
```

Команды всегда берутся из уже принятого Task/Verification contract.

## 7. EXTEND contract и composition

Project extension хранит ссылку на exact base revision:

```yaml
extension:
  base_skill_ref: SKL-PROFILE-DB-MIGRATION@2
  base_skill_digest: sha256:...
  composition_mode: APPEND_AND_RESTRICT
  additions:
    procedure_steps: []
    stop_conditions:
      - PROJECT_MIGRATION_WINDOW_UNKNOWN
    verification_refs:
      - VFP-PROJECT-MIGRATION-NAMING-001
  restrictions:
    allowed_scope_patterns:
      - db/migrations/**
    prohibited_operations:
      - DEPLOY
```

Composition rules:

- exact base revision/digest обязательны;
- extension может добавлять constraints;
- extension может сужать scope/capabilities;
- extension не может удалить base stop condition;
- extension не может удалить prohibited operation;
- extension не может расширить capabilities неявно;
- несовместимое изменение требует CREATE с rationale либо новой base revision;
- resolved effective skill materialизуется для validation, но source остаётся base + extension.

`APPEND_AND_RESTRICT` — единственный composition mode v0.6.1.

## 8. Storage layout

Использовать документированную структуру:

```text
.harness/skills/
├── registry.yaml
├── DRAFT/
├── VALIDATING/
├── VALIDATED/
├── REJECTED/
├── ACTIVE/
├── SUSPENDED/
├── DEPRECATED/
├── RETIRED/
├── EVALUATIONS/
└── MIGRATIONS/
```

Правила:

- один файл соответствует одной immutable revision;
- lifecycle transition создаёт новое state record/metadata, а не редактирует historical revision silently;
- ACTIVE directory содержит materialized accepted revision либо immutable reference;
- registry является generated index, а не единственным source of truth;
- DRAFT не попадает в routing READY Task;
- artifacts product plane и skills control plane не смешиваются.

## 9. Lifecycle

```text
DRAFT → VALIDATING → VALIDATED → ACTIVE
          ↘ REJECTED
ACTIVE → SUSPENDED
ACTIVE → DEPRECATED → RETIRED
```

### 9.1. DRAFT

Contract может редактироваться через новую revision. Не используется Task routing.

### 9.2. VALIDATING

Revision frozen. Создаётся Evaluation Run с exact inputs/digests. Изменение contract требует возврата через новую DRAFT revision.

### 9.3. VALIDATED

Все mandatory checks PASS. Skill ещё не active и не влияет на READY Tasks.

### 9.4. ACTIVE

Получено explicit approval, lock обновлён, impact analysis применён. Разрешён как primary/supporting skill.

### 9.5. REJECTED

Evaluation не прошла. Причины и evidence сохраняются. Повторная попытка — новая revision.

### 9.6. SUSPENDED/DEPRECATED/RETIRED

- `SUSPENDED`: немедленно запрещает новые routing из-за defect/security issue;
- `DEPRECATED`: остаётся для history, новые Tasks получают replacement;
- `RETIRED`: не используется и не является migration target.

В v0.6.1 достаточно поддержать переходы CLI и validation; сложная organization governance не требуется.

## 10. Evaluation Suite

Использовать существующий prefix `EVS`.

```yaml
evaluation_suite:
  id: EVS-SKL-PROJECT-CSV-IMPORT-001
  revision: 1
  skill_ref: SKL-PROJECT-CSV-IMPORT@1
  fixtures:
    - id: happy_path
      kind: REPRESENTATIVE_TASK
      expected: PASS
    - id: ambiguity_stop
      kind: MATERIAL_AMBIGUITY
      expected_stop: MATERIAL_SCHEMA_AMBIGUITY
    - id: scope_violation
      kind: NEGATIVE_SCOPE
      expected: BLOCKED
    - id: capability_missing
      kind: NEGATIVE_CAPABILITY
      expected: BLOCKED
    - id: malformed_output
      kind: NEGATIVE_OUTPUT
      expected: FAIL
  required_pass_rate: ALL_MANDATORY
```

Минимум fixtures:

- happy path;
- material ambiguity stop;
- scope violation;
- missing capability;
- malformed output;
- representative project technology/profile case;
- regression fixture для каждого исправленного defect.

Нельзя использовать средний score, чтобы скрыть failure mandatory negative fixture.

## 11. Evaluation execution

Evaluation делится на детерминированные уровни.

### 11.1. Static checks

- schema;
- unique IDs;
- all refs resolvable;
- procedure completeness;
- stop conditions;
- capability minimization;
- scope normalization;
- prohibited operation preservation;
- output schema;
- adapter compatibility;
- base extension digest.

### 11.2. Compilation checks

Для каждой fixture Compiler строит effective Prompt Plan/Bundle и проверяет:

- Task constraints не потеряны;
- skill не расширил capabilities;
- current Implementation Stage fence сохранён;
- stop conditions включены;
- output contract указан;
- context refs bounded.

### 11.3. Behavioral fixtures

Используется deterministic fake executor/agent fixture, а не nondeterministic production model как единственный Gate. Fixture моделирует результат и проверяет routing/stop/validation behavior.

Дополнительный live evaluation через local Codex CLI может быть recorded evidence, но не заменяет deterministic suite и не должен автоматически отправлять sensitive project data.

## 12. Skill Readiness Gate

```yaml
skill_readiness:
  skill_ref: SKL-PROJECT-CSV-IMPORT@1
  checks:
    schema: PASS
    procedure_completeness: PASS
    capability_minimization: PASS
    scope_safety: PASS
    output_schema: PASS
    adapter_compatibility: PASS
    behavioral_fixtures: PASS
    negative_fixtures: PASS
    documentation: PASS
    base_integrity: NOT_APPLICABLE
  status: PASS
```

Для EXTEND `base_integrity` обязателен.

`VALIDATED` разрешён только при PASS всех mandatory checks. `UNKNOWN`, `PARTIAL` и missing fixture блокируют.

## 13. Activation approval

Activation является control-plane change.

Approval view показывает:

- skill ID/revision/digest;
- CREATE или EXTEND rationale;
- owner;
- capabilities;
- allowed/prohibited scope;
- base skill для EXTEND;
- evaluation results;
- dependent Tasks;
- invalidated Prompt Plans;
- rollback revision.

Canonical decision:

```yaml
decision:
  id: DEC-PROJECT-SKILL-ACTIVATE-001
  kind: PROJECT_SKILL_ACTIVATION
  subject_ref: SKL-PROJECT-CSV-IMPORT@1
  actor: ACT-USER-001
  approved_at: ...
  evaluation_ref: EVS-SKL-PROJECT-CSV-IMPORT-001@1
  status: ACCEPTED
```

Без этого decision skill остаётся `VALIDATED`.

## 14. Activation transaction

Atomic sequence:

1. повторно проверить skill/evaluation digests;
2. записать activation decision;
3. materialize ACTIVE revision;
4. обновить `.harness/skills/registry.yaml`;
5. обновить exact skill digest в `PROJECT_LOCK`;
6. выполнить dependent impact analysis;
7. пометить future Prompt Plans/Bundles stale согласно status rules;
8. recompute readiness;
9. записать audit event.

При failure transaction восстанавливает предыдущий active registry/lock. Нельзя оставить ACTIVE file без lock update.

## 15. Routing и permission intersection

Task имеет ровно один primary skill:

```yaml
route:
  primary_skill_ref: SKL-PROJECT-CSV-IMPORT@1
  supporting_skill_refs: []
```

Effective capabilities:

```text
Task granted capabilities
∩ Project/Profile policy
∩ Skill required capabilities
∩ Adapter/Sandbox capabilities
```

Skill никогда не выдаёт capability. Если ему нужно то, чего Task не разрешает, Task остаётся BLOCKED или skill считается incompatible.

Allowed write scope также пересекается, а не объединяется без ограничений:

```text
Task write scope ∩ Skill allowed scope
```

## 16. Versioning и migration

Semantic policy:

- breaking input/output/procedure change → major revision;
- backward-compatible optional addition → minor revision;
- non-semantic editorial clarification → patch revision.

Каждое semantic изменение проходит новую evaluation/activation.

При active revision update:

- completed Runs сохраняют old exact ref;
- current RUNNING Run не переключается;
- READY/PLANNED dependent Tasks проходят compatibility analysis;
- queued Prompt Plans на old revision становятся `STALE`;
- migration record описывает opt-in/required transition;
- rollback активирует ранее validated revision через новый decision, не удаляя defect history.

## 17. CLI

Добавить:

```bash
project-harness skill-gap --project <root>
project-harness skill-draft --project <root> --definition <file>
project-harness skill-validate --project <root> --skill <ref>
project-harness skill-activate --project <root> --skill <ref> --approval <record>
project-harness skill-suspend --project <root> --skill <ref> --reason <text>
project-harness skill-deprecate --project <root> --skill <ref> --replacement <ref>
project-harness skill-status --project <root> [--skill <ref>]
```

`skill-draft` не генерирует skill из одного предложения без completed gap analysis. Browser preparation layer может подготовить definition, но Kernel validates provenance.

### 17.1. PROJECT_INPUT skill resolution contract

`skills.resolutions[]` для новых actions больше не может быть bare enum. Для `CREATE`/`EXTEND` требуется reference на полную definition/gap analysis:

```yaml
skills:
  resolutions:
    - requested_capability: CSV_IMPORT_WORKFLOW
      action: CREATE
      definition_ref: SKL-PROJECT-CSV-IMPORT@1
      gap_analysis_ref: VAL-PROJECT-SKILL-GAP-001@1
```

Для `EXTEND` дополнительно обязателен exact `base_skill_ref`. `REUSE`, `CONFIGURE` и `TASK_ONLY` сохраняют совместимые формы v0.6.0. Secret/executable fields не допускаются.

Versioning:

```text
PROJECT_INPUT.schema_version: 6
SCHEMA-PROJECT-PREPARATION-INPUT@6
Harness canonical SCHEMA_VERSION: 9
Migration: MIG-ENGINE-0.6.0-TO-0.6.1
```

## 18. Модули и schemas

Новые/обновлённые modules:

```text
skills/contracts.py
skills/storage.py
skills/composition.py
skills/evaluation.py
skills/lifecycle.py
skills/routing.py
```

Обновить:

- `compiler.py` — effective skill resolution;
- `planner.py` — skill authoring prerequisite/control Task;
- `prompting.py` — materialized procedure sections;
- `runtime.py` — readiness invalidation;
- `registry.py` — project-local registry/digests;
- `validation.py` — lifecycle and cross-plane checks;
- `cli.py` — authoring lifecycle commands;
- `archive.py` — project-local skill revisions/evaluations/migrations;
- `project_input.py` — разрешить `EXTEND`/`CREATE` только при complete definitions, не как bare enum answer.

Schemas:

```text
project_skill.schema.json
skill_extension.schema.json
skill_evaluation_suite.schema.json
skill_evaluation_result.schema.json
skill_activation_decision.schema.json
skill_migration.schema.json
```

### 18.1. Contract catalog и registry versions

В `contracts.yaml` добавить:

```yaml
evaluation_suite:
  id_prefix: EVS
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/skills/EVALUATIONS/SUITES/{id}@{revision}.yaml
  revision_policy: IMMUTABLE
skill_evaluation_result:
  id_prefix: VAL
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/skills/EVALUATIONS/RESULTS/{id}@{revision}.yaml
  revision_policy: IMMUTABLE
skill_migration:
  id_prefix: MIG
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/skills/MIGRATIONS/{id}@{revision}.yaml
  revision_policy: IMMUTABLE
```

`skill` и `decision` contracts уже существуют; extension хранится как часть exact PROJECT skill revision и не получает отдельный lifecycle entity.

Expected registry versions:

```text
REG-CONTRACT-CATALOG: 6 → 7
REG-ID-PREFIXES:      остаётся 4
REG-STATUSES:         остаётся 7
```

## 19. Migration v0.6.0 → v0.6.1

- существующие resolved REUSE/CONFIGURE/TASK_ONLY сохраняются;
- bare `EXTEND`/`CREATE` requests из старого input остаются `WAITING_INPUT` до полного contract;
- `.harness/skills` lifecycle directories создаются идемпотентно;
- active distribution skills не копируются как project-owned;
- PROJECT_LOCK расширяется exact refs/digests;
- ни один DRAFT не активируется автоматически.

## 20. Failure и recovery

| Ситуация | Результат |
|---|---|
| Base skill digest changed | EXTEND evaluation `STALE` |
| Mandatory fixture failed | `REJECTED` revision |
| Activation approval missing | `VALIDATED`, `WAITING_DECISION` |
| Lock update failed | activation rollback |
| ACTIVE skill later found unsafe | `SUSPENDED`, dependent Tasks blocked |
| Replacement incompatible | no automatic migration |
| One-off workflow requested as CREATE | `TASK_ONLY` recommendation |
| Skill requests broader capability | validation failure |

## 21. Тестовый план

### 21.1. Contract/static

- only PROJECT/DECLARATIVE accepted;
- executable code fields rejected;
- unknown steps rejected;
- missing owner/output/stop conditions rejected;
- capability expansion rejected;
- EXTEND exact base digest required;
- prohibited operation removal rejected;
- scope restrictions combine correctly.

### 21.2. Lifecycle

- DRAFT cannot route READY Task;
- frozen VALIDATING revision cannot mutate;
- fixture failure creates REJECTED evidence;
- VALIDATED requires all mandatory PASS;
- activation requires exact approval;
- transaction updates ACTIVE/registry/lock together;
- suspend immediately prevents new routing;
- completed Run remains reproducible with old revision.

### 21.3. Evaluation

- happy path;
- ambiguity stops correctly;
- scope violation blocked;
- missing capability blocked;
- malformed output fails;
- current-stage fence preserved;
- regression fixture required for defect fix;
- live model output is not trusted without deterministic checks.

### 21.4. Gap analysis

- REUSE preferred over CREATE;
- CONFIGURE preferred over EXTEND;
- EXTEND preferred over CREATE;
- one-off workflow remains TASK_ONLY;
- CREATE requires repeatability rationale.

## 22. Критерии приёмки v0.6.1

Версия готова, когда:

1. PROJECT declarative skill проходит полный DRAFT→ACTIVE lifecycle;
2. CREATE/EXTEND доступны только после Skill Gap Analysis;
3. arbitrary executable code в skill невозможен;
4. EXTEND использует exact base и режим `APPEND_AND_RESTRICT`;
5. skill не расширяет Task capabilities/scope;
6. deterministic evaluation содержит positive и negative fixtures;
7. все mandatory checks PASS до `VALIDATED`;
8. explicit approval обязателен до `ACTIVE`;
9. activation атомарно обновляет registry и PROJECT_LOCK;
10. future prompts инвалидируются, completed Runs остаются неизменными;
11. unsafe skill может быть suspended;
12. одноразовая работа не превращается в skill;
13. UNIVERSAL/PROFILE authoring остаётся вне scope.

## 23. Порядок реализации

1. Зафиксировать declarative contract и step vocabulary.
2. Реализовать immutable storage/lifecycle directories.
3. Реализовать Gap Analysis enforcement.
4. Реализовать EXTEND composition.
5. Реализовать static validation.
6. Реализовать deterministic fixture evaluator.
7. Реализовать Readiness Gate.
8. Реализовать activation transaction и lock update.
9. Интегрировать routing/readiness/prompt invalidation.
10. Добавить suspend/deprecate transitions.
11. Выполнить lifecycle/security/regression tests.
12. Обновить пользовательскую документацию без изменения UNIVERSAL/PROFILE scope.

v0.7.0 использует только ACTIVE skill revisions и не меняет этот lifecycle.
