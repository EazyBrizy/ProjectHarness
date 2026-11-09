# Greenfield, brownfield и hybrid workflows

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Greenfield

```text
Idea / Documents
→ mandatory documentation question
→ adaptive questionnaire
→ Project Definition Draft and Gate
→ requirements/constraints
→ architecture options
→ Technology Baseline and decisions
→ Skill Gap Analysis
→ bootstrap
→ Work Packages and causal DAG
→ first READY task
```

Harness does not require a complete specification or repository. It does require explicit treatment of material unknowns before affected implementation.

## 2. Brownfield

```text
Existing Repository + Optional Documents + User Goal
→ mandatory documentation question
→ read-only repository/source inventory
→ build/test/runtime/technology discovery
→ architecture/contracts extraction
→ docs/code/tests reconciliation
→ material clarification batch
→ Brownfield Baseline Gate
→ skills/context/verification preparation
→ route portfolio
```

Route portfolio:

```text
CONTINUE_DEVELOPMENT
FIX_KNOWN_BUGS
IMPROVE_PROJECT
STABILIZE_BASELINE
```

Improvement and bug-fix work are separate Work Packages and do not silently expand feature scope.

## 3. Hybrid

Hybrid covers fork, replacement, replatforming, migration or new product reusing existing assets. It records:

- reusable and rejected assets;
- retained contracts;
- migration boundaries;
- data ownership transfer;
- compatibility window;
- decommission criteria;
- target architecture decisions.

## 4. Brownfield inventory

Minimum:

- repository topology and revisions;
- languages/runtimes/frameworks/exact versions;
- build/run/test commands and known failures;
- CI/release/deployment paths;
- schemas/migrations/data stores;
- APIs/events/integrations;
- source/test/docs/config paths;
- security/trust boundaries;
- Git state, ownership and active work;
- technical debt and undocumented behavior.

## 5. Reconciliation classes

```text
DOC_AND_CODE_AGREE
CODE_AHEAD_OF_DOCS
DOCS_AHEAD_OF_CODE
TESTS_DEFINE_OBSERVED_BEHAVIOR
CONFLICT_REQUIRES_DECISION
LEGACY_TOLERATED
UNKNOWN
```

Code, docs or tests do not automatically win. Accepted source precedence and user authority resolve material conflicts.

## 6. No hidden restructuring

Brownfield onboarding cannot automatically:

- replace framework/database;
- mass-move directories;
- update all dependencies;
- rewrite tests;
- change public contracts;
- run whole-repository formatting;
- fix unrelated issues.

Such work requires explicit Improvement/Change Pack.

## 7. Common output

Before implementation planning both greenfield and brownfield have:

- accepted Project/Brownfield Definition;
- effective constraints and policies;
- accepted architecture and Technology Baseline;
- active skills or prerequisite skill tasks;
- repository/bootstrap/test environment baseline;
- Work Packages/DAG and documentation traceability;
- current Result Envelope and exact next route.

## 9. v0.4.1 Brownfield Gate

Для Greenfield порядок gates остаётся четырёхчастным. Для Brownfield/Hybrid после proposal Brownfield Baseline требуется отдельное подтверждение пользователя. Принятие Project Definition, Architecture или Technology не считается принятием фактического repository baseline.

При успешном `prepare` accepted Brownfield Baseline ссылается через `accepted_by` на immutable Decision и фиксирует `accepted_at`. До этого проект остаётся `WAITING_DECISION`, а исходный repository не модифицируется.

## 9. v0.5.0 maturity route distinction

Greenfield всегда начинает с `claimed_current_level: NONE` и active `PROTOTYPE`. Brownfield/Hybrid хранит claimed value отдельно, выполняет read-only maturity assessment и принимает baseline только formal approval transaction. User claim или completed legacy Tasks не равны accepted level.
