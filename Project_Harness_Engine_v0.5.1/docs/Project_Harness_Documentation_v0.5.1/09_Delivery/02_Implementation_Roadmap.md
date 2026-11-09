# Implementation Roadmap v0.4.1

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Roadmap principle

Implementation follows causal vertical slices. Every work package produces artifacts needed by the next one; no package assumes a subsystem that is planned later.

`HNS-REQ-*` остаётся namespace документационных требований. Реализационные Work Packages используют только `WP-HARNESS-*`, то есть зарегистрированный prefix `WP`.

## 2. Release cut

Roadmap IDs остаются стабильными, но каждый package может иметь отдельный `CORE_MVP` и `HARDENING` acceptance slice.

- `CORE_MVP`: `WP-HARNESS-000`–`040`; Core subset `WP-HARNESS-050` (ACTIVE skill resolution, minimal bootstrap and one Verification Profile); single-task subset `WP-HARNESS-060`; `WP-HARNESS-070`; governed local-runtime subset `WP-HARNESS-080`; basic verification/documentation subset `WP-HARNESS-090`; Blocker/resume subset `WP-HARNESS-100`; core fixture/package subset `WP-HARNESS-120`.
- `HARDENING`: create/extend/evaluate skill lifecycle in `WP-HARNESS-050`; parallel batches/worktrees/leases in `WP-HARNESS-060`; provider-specific dispatch and broader runtime isolation in `WP-HARNESS-080`; extended environments/integration in `WP-HARNESS-090`; full Change Packs in `WP-HARNESS-100`; all `WP-HARNESS-110`; extended pilots/release automation in `WP-HARNESS-120`.

Core `WP-HARNESS-120` depends on the Core critical path only. Hardening `WP-HARNESS-120` additionally depends on `WP-HARNESS-110`. Hardening не может изменить принятые Core contracts.

## 3. Work packages

### WP-HARNESS-000 — Core registries, schemas and storage

**Dependencies:** none.  
**Produces:** registry loader, ID/profile/status registries, schema validation, revision/hash store, event append interface.

Tasks:

- define directory/package skeleton;
- implement registry schemas and collision validation;
- implement canonical entity envelope/revisions;
- implement append-only events and current-state materialization;
- add v0.2 alias migration fixtures;
- add structural tests.

**Acceptance:** unknown ID/status/profile rejected; event/state revision reproducible.

### WP-HARNESS-005 — Single Entry, Request and Result contracts

**Dependencies:** WP-HARNESS-000.  
**Produces:** natural-language entry API, Request/Request Plan/Route/Result schemas, public status mapper, correlation context.

Tasks:

- request ingestion/idempotency;
- Request Class/Mode classification interface;
- deterministic control/query rules;
- Request lifecycle;
- minimal Result Envelope renderer;
- query fixture with no task creation.

**Acceptance:** ordinary question returns `ANSWERED`; development input creates a planned route; every outcome returns schema-valid result.

### WP-HARNESS-010 — First end-to-end walking skeleton

**Dependencies:** WP-HARNESS-005.  
**Produces:** input → one mock Work Package/Task → mock bundle/run → evidence → result/state.

Tasks:

- minimal Work Package/Task schemas;
- one deterministic READY rule;
- minimal Prompt Spec/Plan/Bundle;
- mock Agent/Tool Adapter;
- Run-as-attempt model;
- one verification evidence object;
- cold-start status.

**Acceptance:** complete vertical fixture runs without bypassing kernel.

### WP-HARNESS-020 — Questionnaire and Project Definition

**Dependencies:** WP-HARNESS-005, WP-HARNESS-010.  
**Produces:** Intake/Questionnaire Sessions, Source Inventory, core/adaptive question bank, Project Definition Gate and human summary.

Tasks:

- mandatory documentation question;
- source parsers interface;
- 3–5 question batching and budget;
- answer/assumption/unknown contracts;
- materiality and strict/pragmatic policy;
- Project Definition generator/gate;
- greenfield fixture.

**Acceptance:** typical fixture creates draft in ≤15 questions and does not ask source-known answers.

### WP-HARNESS-030 — Brownfield inventory and reconciliation

**Dependencies:** WP-HARNESS-020.  
**Produces:** read-only repository inventory, build/test/technology discovery, conflict ledger, Brownfield Baseline and route portfolio.

Tasks:

- repository topology/manifests/static parsing;
- safe command classification/isolation;
- docs/code/tests reconciliation;
- existing test baseline;
- continuation/fix/improvement/stabilization route proposals;
- no-hidden-restructure tests.

**Acceptance:** existing fixture yields accepted/proposed baseline and separated route branches without product writes.

### WP-HARNESS-040 — Requirements, ADR, architecture and Technology Baseline

**Dependencies:** WP-HARNESS-020; uses WP-HARNESS-030 for brownfield.  
**Produces:** requirements/constraints/quality, material decision classification, ADR, architecture options/baseline, technology candidates/baseline/compatibility.

Tasks:

- traceability model;
- constraint evaluator;
- ADR materiality and gates;
- technology selection/compatibility;
- source/documentation links;
- impact hooks.

**Acceptance:** material stack/public-contract choice cannot be accepted without decision; task-local choice creates no ADR.

### WP-HARNESS-050 — Skill Registry, bootstrap and verification baselines

**Dependencies:** WP-HARNESS-040.  
**Produces:** Core ACTIVE-skill resolution/minimal bootstrap and hardening skill lifecycle, Verification Profiles, Test Environment/Test Baseline.

Tasks:

- universal/profile/project skill namespaces;
- Core reuse/configure/task-only resolver;
- hardening reuse/configure/extend/create planner;
- hardening skill evaluation fixtures;
- project-local structure and human views;
- greenfield/brownfield bootstrap;
- pre-migrated test environment strategies;
- known/stale test classification.

**Acceptance:** product task cannot be READY with inactive skill or missing verification environment/profile.

### WP-HARNESS-060 — Work Packages, artifact DAG and safe parallelism

**Dependencies:** WP-HARNESS-040, WP-HARNESS-050.  
**Produces:** full Work Package/Task contracts, artifact dependencies, topological readiness, deterministic next task, read/write conflict planner, Parallel Batch and leases.

Tasks:

- decomposition/aggregation;
- artifact producer/consumer validation;
- causal layer calculation;
- contract/path/docs/DB/lockfile/environment access sets;
- worktree/lease contracts;
- integration task rules;
- runtime split/staleness.

**Acceptance:** missing future artifact blocks readiness; backend/frontend can share frozen read-only contract; conflicting writes rejected.

### WP-HARNESS-070 — JIT Prompt/Context compiler

**Dependencies:** WP-HARNESS-050, WP-HARNESS-060.  
**Produces:** Prompt IR registries/lifecycles, JIT compiler, Context Plans/Packets, source maps, invalidation and compatibility results.

Tasks:

- base Prompt Specs;
- deterministic module composition;
- required task purpose/scope/verification/docs/stop/output sections;
- context selection/overflow policy;
- bundle per actual Run only;
- compiler error → Blocker mapping;
- prompt/context regression fixtures.

**Acceptance:** no future mass bundles; same inputs yield same logical hash; material change invalidates plan.

### WP-HARNESS-080 — Codex Adapter, governed runtime and traces

**Dependencies:** WP-HARNESS-070.  
**Produces:** Codex Agent Adapter, Run Plan, Run/Tool Invocation, capability wrappers, Request/Run Trace, structured agent result normalization.

Tasks:

- Codex profile/rendering;
- AGENTS.md generator;
- worktree/tool mediation;
- actual write-scope enforcement;
- timeout/cancel/idempotency;
- structured stop signals;
- independent output/diff validation;
- cold-start recovery.

**Acceptance:** Codex cannot write out of scope or choose next task; malformed output/blocker normalized; retry creates new Run.

### WP-HARNESS-090 — Verification, documentation and integration

**Dependencies:** WP-HARNESS-080.  
**Produces:** verification selection, baseline comparison, stale-test policy, documentation sections/impact gate, Task Report, integration/release checks.

Tasks:

- targeted/nearest/integration/release suites;
- test DB clone/schema/lease strategy;
- known/new/stale/flaky failure classification;
- documentation update/anchor validation;
- evidence sufficiency/staleness;
- Work Package aggregation and completed Result Envelope.

**Acceptance:** completed feature fixture updates docs and evidence; known unrelated failure visible but not misattributed; new regression blocks completion.

### WP-HARNESS-100 — Blockers, resume and Change Packs

**Dependencies:** WP-HARNESS-080, WP-HARNESS-090.  
**Produces:** full Blocker/Recovery, safe state/compensation, resume, product/project-control/distribution Change Packs, impact/replanning and migrations.

Tasks:

- blocker classes/options/recommendation/resume condition;
- independent ready tasks;
- retry/recovery flows;
- target-plane separation;
- isolated apply/canary/rollback;
- one-prompt project-control patch fixture.

**Acceptance:** no blocker lacks route; mixed-plane pack rejected; maintenance does not mutate active bundle/history.

### WP-HARNESS-110 — Git/publication, security and evaluation suites

**Dependencies:** WP-HARNESS-080, WP-HARNESS-100.  
**Produces:** Git worktrees/commit plans/push separation, trust/data controls, adversarial/cross-profile/recovery/semantic docs suites.

Tasks:

- commit/push/PR/deploy capability separation;
- supply-chain and injection fixtures;
- secret redaction/egress;
- semantic documentation validator;
- combined documentation generator;
- archive integrity.

**Acceptance:** dangerous side effect needs approval; semantic registry drift fails CI; archive reproducible.

### WP-HARNESS-120 — Pilots and release

**Dependencies:** Core slice — Core critical path; Hardening slice — WP-HARNESS-110 and all hardening critical-path packages.  
**Produces:** greenfield API/CLI pilots, brownfield pilot, CUSTOM profile, offline/vendored scenario, migration and release archive.

Tasks:

- end-to-end acceptance fixtures;
- performance/recovery sanity;
- migration from v0.2 docs/sample state;
- user guide and implementation guide packaging;
- known limitations and rollback target.

**Acceptance:** all MVP journeys pass and documentation/manifest validate.

## 4. Critical path

```text
WP-HARNESS-000
→ WP-HARNESS-005
→ WP-HARNESS-010
→ WP-HARNESS-020
→ WP-HARNESS-040
→ Core WP-HARNESS-050
→ Core WP-HARNESS-060
→ WP-HARNESS-070
→ Core WP-HARNESS-080
→ Core WP-HARNESS-090
→ Core WP-HARNESS-100
→ Core WP-HARNESS-120
```

Hardening continuation:

```text
Core baseline
→ hardening slices WP-HARNESS-050/060/080/090/100
→ WP-HARNESS-110
→ Extended WP-HARNESS-120
```

WP-HARNESS-030 starts after WP-HARNESS-020 and joins before brownfield-dependent acceptance. Git/security/evaluation subtasks can proceed in parallel only after their required contracts exist.

## 5. Implementation task rule

Each `WP-HARNESS-*` Work Package must itself be decomposed using the v0.4.1 Task Contract. No implementation task may reference a schema, registry, adapter, environment or artifact scheduled in a later package.
