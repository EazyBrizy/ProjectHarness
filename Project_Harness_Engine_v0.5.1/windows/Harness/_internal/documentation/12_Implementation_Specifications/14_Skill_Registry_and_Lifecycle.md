# Skill Registry, создание и lifecycle скиллов

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Skills описывают повторяемые способы выполнения классов задач. Harness не должен создавать новый skill для каждой task. Сначала проверяется возможность повторного использования и настройки существующего skill.

Порядок предпочтения:

```text
REUSE
→ CONFIGURE
→ EXTEND
→ CREATE
```

## 2. Уровни skills

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

## 3. Skill Contract

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

## 4. Skill lifecycle

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

## 5. Skill Readiness Gate

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

## 6. Skill Gap Analysis

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

## 7. Создание нового skill

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

## 8. Routing policy

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

## 9. Project-local storage

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

## 10. Versioning and invalidation

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

## 11. Skill evaluation

Минимум:

- happy-path fixture;
- material ambiguity stop case;
- scope violation negative case;
- missing capability case;
- malformed output case;
- representative technology/profile case;
- regression fixture for every fixed skill defect.

## 12. Project resolution в Core v0.4.1

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

## 13. Критерии приёмки

1. Skill Registry различает universal/profile/project scopes.
2. Новый skill создаётся только после reuse/configure/extend analysis.
3. Primary skill ровно один на task.
4. `ACTIVE` требует readiness/evaluation PASS.
5. Skill capabilities минимальны и не расширяют Task Contract.
6. Skill update инвалидирует будущие prompt plans, но не history.
7. Project-local structure содержит registry and lifecycle directories.
8. Одноразовая работа остаётся Task Contract, а не skill.
