# Подключение уже разрабатываемого проекта (Brownfield Onboarding)

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Harness должен безопасно подключать существующий проект, определить его фактическую структуру и подготовить систему продолжения разработки без скрытой перестройки. На выходе пользователь получает:

- подтверждённый brownfield baseline;
- систему prompts/routes/skills для существующего стека;
- ветку продолжения разработки;
- отдельную ветку улучшений;
- отдельную ветку исправления дефектов;
- список blockers and prerequisites.

## 2. Главный принцип

```text
Inspect first, reconcile second, propose third, modify only after approval/readiness.
```

Первичная инвентаризация выполняется read-only. Harness не запускает formatter, migrations, dependency upgrade или tests with writes до определения permissions and environment policy.

## 3. Входы

```yaml
brownfield_intake:
  id: BFI-20260806-001
  session_ref: SES-20260806-0005
  repository_sources:
    - url_or_path_ref: REP-APP-001
      access: READ_ONLY
  documentation_sources: []
  issue_sources: []
  deployment_sources: []
  user_goal: "Продолжить разработку и исправить известные ошибки"
  status: INVENTORY_PENDING
```

Минимум:

- доступ к repository snapshot или archive;
- ответ на обязательный вопрос о документации;
- цель подключения;
- ограничения на writes/commands/network.

## 4. Этапы onboarding

```text
1. Intake Session and documentation question
2. Read-only source/repository inventory
3. Build/test/runtime reconnaissance
4. Architecture, technology and contract extraction
5. Documentation ↔ code ↔ tests reconciliation
6. Material clarification batch
7. Brownfield Baseline Proposal
8. Brownfield Baseline Gate
9. Skill/context/verification preparation
10. Route portfolio generation
11. First READY task selection
```

## 5. Repository Inventory

Harness определяет:

- repository topology: single, monorepo, polyrepo;
- languages, runtimes, frameworks and versions;
- package/build systems and lockfiles;
- source/test/documentation/config paths;
- entry points and deployables;
- services/modules/packages and dependencies;
- API/contracts/schema definitions;
- database/migrations and current head;
- CI/CD and release configuration;
- environment requirements;
- logging/observability;
- security-sensitive boundaries;
- code ownership/Git policy;
- existing agent/project guidance;
- known failing tests and build state.

```yaml
repository_inventory:
  id: RIV-APP-001
  repository_ref: REP-APP-001
  revision: sha256:...
  topology: MONOREPO
  components: []
  technology_candidates: []
  build_commands: []
  test_commands: []
  database_refs: []
  documentation_refs: []
  confidence: 0.91
  unknowns: []
```

## 6. Safe reconnaissance

Разрешены read-only operations:

- listing files and metadata;
- parsing manifests/configs;
- reading docs/source/tests;
- static dependency graph extraction;
- Git history/status inspection;
- non-mutating commands proven safe by adapter.

Команда build/test может создавать caches/artifacts. До запуска она классифицируется как side effect и выполняется в isolated workspace после permission grant.

## 7. Reconciliation classes

Для каждого material fact:

```text
DOC_AND_CODE_AGREE
CODE_AHEAD_OF_DOCS
DOCS_AHEAD_OF_CODE
TESTS_DEFINE_OBSERVED_BEHAVIOR
CONFLICT_REQUIRES_DECISION
LEGACY_TOLERATED
UNKNOWN
```

Примеры:

- Документация описывает endpoint, которого нет → `DOCS_AHEAD_OF_CODE`; нужно решить, requirement это или устаревший текст.
- Код использует новую schema, docs старые → `CODE_AHEAD_OF_DOCS`; требуется проверить, было ли изменение принято.
- Test ожидает старое behavior, accepted docs новое → candidate `STALE_TEST`, но решение фиксируется formal route.

## 8. Brownfield Baseline

```yaml
brownfield_baseline:
  id: BFB-APP-001
  revision: 1
  repository_revision: sha256:...
  status: PROPOSED

  accepted_actual_structure_ref: RIV-APP-001
  project_definition_ref: PJD-APP-001
  architecture_baseline_ref: ARB-APP-001
  technology_baseline_ref: TBL-APP-001
  contract_refs: []
  test_baseline_ref: TSB-APP-001

  known_gaps: []
  known_defects: []
  technical_debt_items: []
  security_findings: []
  documentation_conflicts: []
  assumptions: []
  unknowns: []
```

Baseline Gate требует подтверждения material conflicts. Он не утверждает, что существующее состояние идеально; он фиксирует, что именно принято как starting point.

## 9. Route Portfolio

После gate Harness создаёт независимые, но связанные направления.

### 9.1. Continuation Route

```text
CONTINUE_DEVELOPMENT
```

Содержит tasks, необходимые для реализации текущего product roadmap с учётом существующей архитектуры.

### 9.2. Improvement Route

```text
IMPROVE_PROJECT
```

Кандидаты:

- architecture simplification;
- dependency/runtime upgrades;
- testability improvements;
- performance/reliability work;
- documentation recovery;
- security hardening;
- build/developer experience improvements.

Каждое улучшение имеет value, risk, dependencies, migration and rollback. Оно не смешивается автоматически с feature tasks.

### 9.3. Bug-fix Route

```text
FIX_KNOWN_BUGS
```

Для каждого defect:

```text
reproduce
→ classify expected behavior
→ create targeted fix task
→ regression verification
→ documentation/known-issue update
```

### 9.4. Stabilization Route

```text
STABILIZE_BASELINE
```

Создаётся, если build/test/environment настолько нестабильны, что continuation tasks нельзя проверять. Содержит минимальные prerequisites, а не полный refactoring.

## 10. Route item contract

```yaml
brownfield_route_item:
  id: BRI-FIX-001
  route: FIX_KNOWN_BUGS
  title: "Исправить потерю фильтра при пагинации"
  evidence_refs: [EVD-BUG-001]
  requirement_refs: [REQ-SEARCH-001]
  estimated_risk: MEDIUM
  value: HIGH
  dependencies: []
  proposed_work_package_ref: WP-FIX-SEARCH-001
  status: PROPOSED
```

## 11. Уточняющие вопросы

После анализа задаются только вопросы, которые нельзя надёжно вывести и которые material для baseline:

- какая документация authoritative;
- какие незакоммиченные/экспериментальные части считать baseline;
- какая production/runtime среда реально используется;
- какие known failures допустимы временно;
- какие branches/releases поддерживаются;
- можно ли менять stack/architecture;
- какой route имеет приоритет: continuation, fixes or improvements.

Вопросы содержат варианты and recommendation based on evidence.

## 12. Подготовка Harness infrastructure

После принятия baseline:

- создаётся `.harness/` project instance;
- импортируются accepted requirements/constraints/decisions;
- формируется Technology Baseline;
- выполняется Skill Gap Analysis;
- регистрируются existing build/test commands;
- создаются Verification Profiles and Test Environment policy;
- строятся Context Policies по структуре repository;
- генерируются Work Packages and routes;
- JIT prompts компилируются только для первых READY tasks.

## 13. Запрет скрытой перестройки

Harness не должен без отдельного approved Improvement/Change Pack:

- менять architecture style;
- заменять framework/database;
- массово перемещать directories;
- переписывать tests;
- обновлять все dependencies;
- форматировать весь repository;
- менять public contracts;
- исправлять unrelated defects в feature task.

## 14. First result

Пользователь получает:

```text
Проект распознан: monorepo, 3 компонента
Документация: частично актуальна, 4 material conflicts
Build: проходит; 2 известных test failures
Стек: ...
Предложенные маршруты:
  1. продолжение разработки — 5 Work Packages
  2. исправление ошибок — 3 Work Packages
  3. улучшения — 4 кандидата, не блокируют features
Рекомендуемый первый шаг: подтвердить API contract conflict
```

## 15. Критерии приёмки

1. Brownfield inspection начинается read-only.
2. Structure, stack, commands, tests, docs and contracts inventory зафиксированы с revision.
3. Code/docs/tests conflicts классифицированы, а не скрыты.
4. Baseline Gate предшествует new product prompts.
5. Continuation, Improvement, Bug-fix and Stabilization routes разделены.
6. Улучшения не внедряются автоматически вместе с feature task.
7. Existing known test failures имеют baseline classification.
8. После gate существует хотя бы один понятный next route или recovery option.

## 18. v0.4.1 explicit acceptance

Brownfield Baseline Gate является отдельным пятым approval для Brownfield/Hybrid. До него baseline может быть только proposal; Architecture/Technology proposals не активируют фактический baseline автоматически. Принятие создаёт immutable Decision и accepted successor revision либо initial accepted revision, в зависимости от route.
