# Impact analysis и replanning

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Impact dimensions

```text
REQUEST/RESULT CONTRACT
PROJECT DEFINITION/SCOPE
REQUIREMENT/CONSTRAINT/POLICY/WAIVER
ADR/ARCHITECTURE/TECHNOLOGY
CONTRACT/DATA/DOCUMENTATION
REPOSITORY/BOOTSTRAP/ENVIRONMENT
WORK PACKAGE/TASK/DAG/PARALLEL BATCH
PROMPT/CONTEXT/SKILL/ADAPTER/VERIFICATION
CAPABILITY/PERMISSION
RUN/EVIDENCE/EVALUATION
SECURITY/OPERATIONS/RELEASE
```

## 2. Impact Map

```yaml
impact_map:
  change_pack_ref: CHP-...
  direct_impacts: []
  transitive_impacts: []
  stale_artifacts: []
  affected_work_packages: []
  active_tasks: []
  active_runs: []
  required_decisions: []
  required_migrations: []
  recompile_targets: []
  evaluation_suites: []
  verdict: SAFE_AUTOMATIC | APPROVAL_REQUIRED | REPLAN_REQUIRED | REJECTED
```

## 3. Future vs history

Completed tasks, ADR, bundles, Runs, events and evidence remain immutable. New rules may make old evidence insufficient for current release, but do not rewrite historical truth.

## 4. Active work actions

```text
UNAFFECTED
REVALIDATE
RECOMPILE
PAUSE
REBASE
REPLAN
CANCEL
SUPERSEDE
```

Active immutable Run may finish under its bundle unless emergency security policy requires suspension. Queued plans become stale on material input change.

## 5. Replanning

Only affected subgraph is rebuilt. Stable IDs remain where meaning unchanged; changed meaning creates revision/successor. Artifact producer/consumer order and parallel conflicts are revalidated.

## 6. Approval

Required for material scope, hard constraint relaxation, architecture/technology/public contract, irreversible migration, dangerous permission, active run cancellation and control/distribution semantics.
