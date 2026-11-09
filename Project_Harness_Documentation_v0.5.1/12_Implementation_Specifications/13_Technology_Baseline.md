# Technology Baseline и выбор стека технологий

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Architecture Baseline отвечает на вопрос «как устроена система», а Technology Baseline — «какими конкретными технологиями и версиями она реализуется». Harness не должен скрыто выбирать stack из шаблона или предпочтений модели.

Technology Baseline создаётся после Project Definition и architecture options, но до bootstrap и product implementation.

## 2. Области baseline

```text
LANGUAGES
RUNTIMES
FRAMEWORKS
DATABASES
MESSAGING
STORAGE
INFRASTRUCTURE
BUILD_TOOLS
PACKAGE_MANAGERS
TEST_TOOLS
OBSERVABILITY
SECURITY_TOOLS
DEPLOYMENT_TARGETS
SUPPORTED_PLATFORMS
```

Не все области обязательны для каждого profile; `NOT_APPLICABLE` фиксируется явно.

## 3. Technology Baseline Contract

```yaml
technology_baseline:
  id: TBL-TECH-001
  revision: 1
  project_ref: project-example
  status: ACCEPTED

  drivers:
    requirement_refs: [REQ-001]
    quality_attribute_refs: [QUA-001, QUA-002]
    constraint_refs: [CST-PLATFORM-001]
    architecture_refs: [ADR-ARCH-001]

  selections:
    - area: LANGUAGE
      technology_ref: TEC-TYPESCRIPT
      version_constraint: ">=5.6 <6"
      status: ACCEPTED
      decision_ref: ADR-TECH-001

    - area: RUNTIME
      technology_ref: TEC-NODE
      version_constraint: "22.x"
      status: ACCEPTED
      decision_ref: ADR-TECH-001

    - area: DATABASE
      technology_ref: TEC-POSTGRES
      version_constraint: "16.x"
      status: ACCEPTED
      decision_ref: ADR-DATA-002

  compatibility_matrix_ref: CMP-TECH-001
  lifecycle_risks: []
  license_constraints: []
  team_capability_assumptions: []
  verification_commands: []
  source_refs: []
  accepted_by: DEC-TECH-001
```

## 4. Technology Candidate Contract

```yaml
technology_candidate:
  id: TCN-DB-POSTGRES
  area: DATABASE
  label: "PostgreSQL"
  satisfies_refs: [REQ-DATA-001, QUA-RELIABILITY-001]

  evaluation:
    architecture_fit: HIGH
    operational_fit: MEDIUM
    team_fit: UNKNOWN
    ecosystem_maturity: HIGH
    portability: MEDIUM
    security_fit: HIGH
    migration_complexity: LOW

  constraints:
    violated: []
    assumptions: [ASM-TEAM-SQL-001]

  benefits: []
  tradeoffs: []
  risks: []
  required_skills: [SKL-POSTGRES-MIGRATIONS]
  bootstrap_impact: []
```

## 5. Процедура выбора

```text
1. Read Project Definition, constraints and quality attributes.
2. For brownfield, inventory existing technologies and versions.
3. Determine mandatory technology areas by profile/architecture.
4. Reuse accepted existing technology unless change has justified value.
5. Produce 2–4 realistic candidates for material selections.
6. Evaluate compatibility, lifecycle, operations, security and team impact.
7. Ask only material user questions.
8. Record ADR/Decision.
9. Build compatibility matrix.
10. Derive skill gaps, bootstrap tasks and verification commands.
```

## 6. Критерии оценки

- соответствие requirements and constraints;
- architecture fit;
- поддерживаемые deployment platforms;
- security/data boundaries;
- availability/reliability needs;
- performance/capacity assumptions;
- operational complexity;
- maintainability;
- team knowledge and hiring constraints;
- ecosystem/tooling;
- version compatibility;
- licensing and supply-chain policy;
- migration/rollback complexity;
- offline requirements;
- brownfield compatibility.

Cost/token optimization model providers не входит в Technology Baseline Harness. Бизнес-стоимость инфраструктуры создаваемого проекта может быть обычным project constraint, если пользователь её задал.

## 7. Пользовательские вопросы о stack

Пользователь не обязан знать конкретную технологию. Вопрос формулируется через последствия:

```text
Нужна ли работа без интернета?
Где будет размещаться система?
Есть ли у команды обязательный язык/платформа?
Нужна ли горизонтальная масштабируемость?
Есть ли существующая БД, которую нельзя менять?
```

Если пользователь отвечает «не знаю», Harness предлагает recommended baseline и объясняет, почему он подходит, какие assumptions приняты и когда их пересмотреть.

## 8. Brownfield baseline

Для существующего проекта технологии получают один из статусов:

```text
ACCEPTED_AS_IS
ACCEPTED_WITH_UPGRADE_TASK
LEGACY_TOLERATED
REPLACE_PROPOSED
UNSUPPORTED_BLOCKER
UNKNOWN_VERSION
```

Harness не заменяет framework или database автоматически. Улучшение оформляется отдельной improvement branch/Work Package с impact and migration plan.

## 9. Compatibility Matrix

```yaml
technology_compatibility:
  id: CMP-TECH-001
  combinations:
    - refs: [TEC-NODE@22, TEC-TYPESCRIPT@5.6, TEC-FRAMEWORK-X@4]
      status: VERIFIED
      evidence_refs: [EVD-TECH-COMPAT-001]
  unsupported: []
  unknown: []
```

Unknown material compatibility блокирует bootstrap или получает explicit validation task раньше dependent implementation.

## 10. Изменение baseline

Technology change после bootstrap проходит `PROJECT_EVOLUTION`:

```text
Change request
→ alternatives and ADR
→ impact map
→ migration/rollback plan
→ task and skill invalidation
→ staged implementation
→ compatibility and release gates
```

Нельзя изменить version/technology только редактированием config без canonical decision.

## 11. Связь со skills и prompts

Accepted selections создают требования к:

- project skills;
- tool adapters;
- verification profiles;
- bootstrap templates;
- context sources;
- Codex guidance.

Task не становится READY, если необходимый skill/tool для accepted technology отсутствует.

## 12. Критерии приёмки

1. Stack не выбирается до Project Definition и architecture drivers.
2. Каждая material selection имеет decision reference.
3. Version constraints and compatibility записаны явно.
4. Brownfield technology не заменяется скрыто.
5. Unknown compatibility создаёт prerequisite validation task.
6. Technology Baseline порождает skill gap and bootstrap plan.
7. Изменение baseline выполняется через Change Pack and migration.
8. Пользователь получает понятное объяснение вариантов без требования знать jargon.
