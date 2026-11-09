# Project bootstrap и Codex handoff

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION BASELINE

## 1. Разделение операций

`START_INTAKE` не является bootstrap. Он создаёт только provisional control workspace для initial discovery.

`BOOTSTRAP_PROJECT` или целевой `PREPARE_FOR_CODEX` выполняется после material approvals и создаёт project-local control plane и handoff. Эта операция не реализует product features.

```text
Distribution startup
→ START_INTAKE
→ sources and questionnaire
→ accepted Project Definition
→ accepted Architecture and Technology Baselines
→ completed Skill Gap Analysis
→ explicit handoff approval
→ BOOTSTRAP_PROJECT / PREPARE_FOR_CODEX
→ first READY Task and one JIT bundle
```

## 2. Preconditions

Обязательны:

- accepted Project Definition;
- accepted Architecture Baseline;
- accepted Technology Baseline;
- completed Skill Gap Analysis;
- resolved ACTIVE seed skill для первой product task;
- causal task DAG;
- Verification Profile для каждой executable task;
- отдельный approval handoff.

Brownfield дополнительно требует accepted Brownfield Baseline. Полный authoring/evaluation lifecycle нового PROJECT skill не является precondition Core bootstrap; при `CREATE`/`EXTEND` Core возвращает Blocker и recovery route.

## 3. Bootstrap Plan

Plan содержит mode, source/base revision, repository actions, directory actions, control-plane actions, verification, rollback/compensation и exact output path. Dry-run показывает все writes до approval.

Статусы происходят из lifecycle `bootstrap_plan`:

```text
DRAFT → PROPOSED → APPROVED → EXECUTING → COMPLETED
```

Ошибки переводят Plan в `BLOCKED` или `FAILED_RECOVERABLE`; silent partial bootstrap запрещён.

## 4. Greenfield

Greenfield handoff создаёт:

- минимальный project skeleton, если он определён accepted task plan;
- human-readable views;
- `.harness/` canonical state;
- exact `PROJECT_LOCK`;
- Work Packages и atomic Task Contracts;
- Prompt/Context Plans и Verification Profiles;
- один Prompt Bundle/Context Packet для первой READY Task;
- embedded local Harness runtime;
- manifest и validation report.

Product implementation не выполняется на preparation stage.

## 5. Brownfield

До approval исходный repository read-only и не получает `.harness/`. Preparation работает с внешним inventory и digest.

Handoff содержит копию принятого repository state и добавляет control plane только внутри выходного package. Existing product files не нормализуются и не перемещаются. Любая restructuring/refactor оформляется отдельным Improvement Work Package.

Route portfolio включает:

```text
CONTINUE_DEVELOPMENT
FIX_KNOWN_BUGS
IMPROVE_PROJECT
STABILIZE_BASELINE
```

## 6. Dry-run, approval и side effects

Bootstrap показывает:

```text
input sources and digests
planned output tree
resolved registries, profile, adapter and skills
first READY Task
exact compiled bundle count
verification commands
known limitations
```

Git commit, push, PR, deployment и publication являются отдельными capabilities и не выполняются preparation command.

## 7. Readiness output

Успешный результат имеет public status `READY_FOR_CODEX` и содержит:

- handoff directory и ZIP;
- `PROJECT_LOCK`;
- manifest;
- validation result;
- current Task/Run references;
- exact `CODEX_START.md` route;
- known Blockers и assumptions.

`PROJECT_COMPLETED` на этом этапе недопустим: product tasks ещё не исполнены.

## 8. После handoff

Codex выполняет только текущую Task. Harness независимо проверяет observed diff, scope и commands. После `complete` следующая Task становится READY и получает новый JIT bundle. Исходный manifest валиден только для начального handoff; mutable state далее проверяется отдельной project-state validation.
