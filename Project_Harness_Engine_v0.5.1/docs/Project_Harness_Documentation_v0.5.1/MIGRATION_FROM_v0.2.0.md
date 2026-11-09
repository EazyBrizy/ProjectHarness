# Migration notes: documentation v0.2.0 → v0.3.0

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE MIGRATION SPECIFICATION

## 1. Цель

Migration переводит v0.2 project/control artifacts в v0.3 без переписывания immutable history. До применения создаются backup, inventory и dry-run report.

## 2. Главные изменения модели

```text
User Input
→ Request + Request Plan
→ Work Package + atomic Tasks
→ READY/JIT Prompt Bundle
→ Run (one attempt)
→ Result Envelope + Request Trace
```

Добавлены questionnaire, brownfield baseline, Technology Baseline, Skill Registry, Verification Profiles, documentation traceability и maintenance target planes.

## 3. Identifier aliases

| v0.2 | v0.3 | Правило |
|---|---|---|
| `REQST-*` | `RQ-*` | Preserve source alias in migration metadata. |
| `DECMP-*` | `WP-*` или transient decomposition record | Convert to Work Package when it groups executable tasks. |
| `ACTOR-*` | `ACT-*` | Mechanical rename. |
| `PDF-*` | `PJD-*` | Project Definition. |
| `CTXP-*` | `CTP-*` | Context Policy. |
| `CTX-*` | `CTX-*` | Context Plan retained. |
| `GRANT-*` | `CGR-*` | Capability Grant. |
| `LEASE-*` | `LSE-*` | Lease. |
| `PRM-*` | `PMD-*`, `PSP-*` or `PPL-*` | Determine actual entity type. |
| `ECP-*` | `CMP-*` | Compatibility result. |
| `EV-*` evidence/event | `EVD-*` or `EVT-*` | Resolve collision by entity type. |
| `UPD-*` | `CHP-*` | Change Pack where applicable. |

Alias mapping is recorded; new artifacts never emit old prefixes.

## 4. Run/Attempt migration

```text
v0.2: Task → Attempt → Run
v0.3: Task → Run(attempt_no)
```

For each historical attempt:

- preserve original IDs in `migration_aliases`;
- create one Run record;
- set `attempt_no` by original order;
- set `previous_run_ref`;
- reparent Tool Invocations and Evidence;
- preserve timestamps/hashes/results unchanged.

## 5. Prompt artifacts

- Prompt Module/Spec lifecycles remain versioned.
- Existing execution bundles become immutable `CPB` records.
- Future precompiled bundles without a Run are invalidated or discarded.
- `COMPILED` is retained only as Compiled Prompt Bundle status.
- Backlog remains Task Contracts; JIT compilation is used after migration.

## 6. Task and decomposition migration

- Existing atomic tasks remain Tasks.
- Composite tasks are converted into Work Package + child Tasks.
- Parent grouping object is non-executable.
- Add `request_ref`, `work_package_ref`, required/produced artifact refs and documentation impact.
- Recompute DAG readiness; future placeholders do not satisfy dependencies.

## 7. Parallelism migration

Replace one `contract_set` with:

```yaml
contracts:
  read: []
  write: []
```

Also classify paths, documentation sections, database heads, lockfiles, generated artifacts and environments. Existing parallel tasks are paused until conflict analysis passes.

## 8. Status migration

- Task completion → `DONE`.
- Run success → `SUCCEEDED`.
- Request/Work Package terminal success → `COMPLETED`.
- `PARTIALLY_COMPENSATED` moves to `compensation.status`.
- Unknown or overloaded status requires explicit mapping; migration must not guess silently.

## 9. Project start and brownfield state

Existing projects receive:

- a reconstructed or confirmed Project Definition;
- Technology Baseline;
- Source/Repository Inventory;
- Test Baseline;
- Skill inventory;
- route portfolio for continuation/fixes/improvements;
- Questionnaire Session only for material missing dimensions.

Migration does not force users to answer information already reliably present in accepted sources.

## 10. Maintenance plane migration

Every existing Change Pack is classified as exactly one:

```text
PRODUCT
PROJECT_CONTROL
HARNESS_DISTRIBUTION
```

Mixed pack is split before application. Historical pack remains immutable and receives migration annotation.

## 11. Project-local structure

Create missing v0.3 paths without deleting v0.2 history:

```text
.harness/canonical/requests/
.harness/canonical/work-packages/
.harness/canonical/technology/
.harness/canonical/skills/
.harness/canonical/questionnaires/
.harness/generated/context-packets/
.harness/history/request-traces/
.harness/history/results/
.harness/registries/
```

## 12. Dry-run checks

Migration dry-run must report:

- unknown prefixes/statuses;
- composite tasks;
- orphaned attempts/runs/evidence;
- ambiguous Prompt entity types;
- unresolved contract/resource conflicts;
- missing documentation refs;
- mixed-plane Change Packs;
- invalid profile values;
- objects that would become stale.

## 13. Rollback

Before apply:

- copy project control tree;
- record source manifest/hash;
- freeze active runs;
- export alias map;
- verify restore procedure.

Rollback restores v0.2 control state and does not undo unrelated product changes. External effects use their original compensation plans.

## 14. Acceptance

Migration succeeds when:

1. all canonical objects validate against v0.3 registries/schemas;
2. immutable history hashes remain verifiable;
3. every active request/task has a valid route or blocker;
4. no new artifact uses v0.2 alias;
5. regenerated human views and prompts reference v0.3 entities;
6. semantic documentation validation passes;
7. rollback test passes on a fixture.
