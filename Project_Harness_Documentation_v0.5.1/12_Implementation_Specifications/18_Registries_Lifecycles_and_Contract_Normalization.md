# Единые registries, lifecycles и нормализация contracts

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Profiles, ID prefixes, statuses, request classes и capability values не должны определяться независимо в разных документах. В реализации они загружаются из versioned machine-readable registries до parsing, planning, compilation и semantic validation.

Canonical files:

```text
registries/id_prefixes.yaml
registries/project_profiles.yaml
registries/statuses.yaml
registries/request_routing.yaml
registries/capabilities.yaml
registries/contracts.yaml
```

## 2. Registry loading contract

```text
Load distribution manifest
→ verify registry hashes/signature
→ validate registry schemas
→ reject duplicate keys/prefixes
→ build immutable runtime registry view
→ load project extension registries
→ verify namespace and compatibility
→ allow document/schema parsing
```

Registry load failure is a startup blocker. Runtime must not silently substitute hard-coded values.

## 3. Project Profile Registry

Baseline v1:

```text
BASE_SOFTWARE
WEB_APPLICATION
API_SERVICE
MOBILE_APPLICATION
DESKTOP_APPLICATION
CLI_TOOL
LIBRARY
DATA_PIPELINE
ML_SYSTEM
INFRASTRUCTURE
EMBEDDED_SYSTEM
AUTOMATION
MULTI_SERVICE_SYSTEM
CUSTOM
```

- `BASE_SOFTWARE` — neutral baseline when no more specific primary profile exists.
- Profiles may compose through registered extensions.
- Overview, questionnaire, profile matrix, MVP and schema enums are generated from the same registry.
- `CUSTOM` requires explicit extension namespace/schema; it is not a free-form escape hatch.

## 4. ID Prefix Registry

| Prefix | Entity | Schema key |
|---|---|---|
| `AC` | Acceptance Criterion | `acceptance_criterion` |
| `ACT` | Actor or role binding | `actor` |
| `ADP` | Executor/agent adapter profile | `adapter_profile` |
| `ADR` | Architecture or material Decision Record | `adr` |
| `ANS` | Questionnaire answer | `answer` |
| `ARB` | Architecture Baseline | `architecture_baseline` |
| `ART` | Generic produced artifact | `artifact` |
| `ASM` | Assumption | `assumption` |
| `BFB` | Brownfield Baseline | `brownfield_baseline` |
| `BFI` | Brownfield Intake | `brownfield_intake` |
| `BLK` | Blocker | `blocker` |
| `BRI` | Brownfield route item | `brownfield_route_item` |
| `BST` | Bootstrap Plan | `bootstrap_plan` |
| `CCS` | Coordinated multi-repository change set | `coordinated_change_set` |
| `CFA` | Conflict analysis | `conflict_analysis` |
| `CGR` | Capability Grant | `capability_grant` |
| `CHK` | Verification or policy check | `check` |
| `CHP` | Change Pack | `change_pack` |
| `CMD` | Command descriptor | `command` |
| `CMP` | Compatibility result or matrix | `compatibility` |
| `CNF` | Source/semantic conflict | `conflict` |
| `CNT` | Canonical product or integration contract | `contract` |
| `COR` | Correlation context | `correlation` |
| `CPB` | Compiled Prompt Bundle | `compiled_prompt_bundle` |
| `CPK` | Context Packet | `context_packet` |
| `CPL` | Commit Plan | `commit_plan` |
| `CST` | Constraint | `constraint` |
| `CTP` | Context Policy | `context_policy` |
| `CTX` | Context Plan | `context_plan` |
| `DAG` | Dependency graph | `dependency_graph` |
| `DEC` | Decision | `decision` |
| `DOC` | Documentation record or stable section | `documentation_record` |
| `ENV` | Logical execution environment resource | `environment_resource` |
| `EVD` | Evidence | `evidence` |
| `EVS` | Evaluation Suite | `evaluation_suite` |
| `EVT` | State or audit Event | `event` |
| `GATE` | Readiness or approval Gate | `gate` |
| `GOL` | Goal | `goal` |
| `HNS` | Documentation-level Harness requirement | `documentation_requirement` |
| `IMP` | Impact Analysis | `impact_analysis` |
| `IMPL` | Implementation artifact | `implementation_artifact` |
| `INV` | Invariant | `invariant` |
| `LOCK` | Shared lock or lockfile resource | `lock_resource` |
| `LSE` | Ownership or environment Lease | `lease` |
| `MIG` | Migration | `migration` |
| `OPT` | Decision, blocker, or recovery Option | `option` |
| `OUT` | Outcome | `outcome` |
| `PBT` | Parallel Batch | `parallel_batch` |
| `PJD` | Project Definition | `project_definition` |
| `PLC` | Policy | `policy` |
| `PMD` | Prompt Module | `prompt_module` |
| `PPL` | Prompt Plan | `prompt_plan` |
| `PRF` | Project Profile | `project_profile` |
| `PSP` | Prompt Spec | `prompt_spec` |
| `QNS` | Questionnaire Session | `questionnaire_session` |
| `QST` | Question | `question` |
| `QUA` | Quality Attribute | `quality_attribute` |
| `RBP` | Rollback or compensation Plan | `rollback_plan` |
| `REG` | Versioned Registry | `registry` |
| `REP` | Repository | `repository` |
| `REQ` | Requirement | `requirement` |
| `RES` | Public Result Envelope | `result_envelope` |
| `RIV` | Repository Inventory | `repository_inventory` |
| `RNP` | Run Plan | `run_plan` |
| `RQ` | Request | `request` |
| `RQP` | Request Plan | `request_plan` |
| `RTE` | Route | `route` |
| `RUN` | Run; one immutable execution attempt | `run` |
| `SCHEMA` | Schema identifier | `schema` |
| `SCP` | Scope definition | `scope` |
| `SEM` | Semantic documentation validation rule | `semantic_rule` |
| `SES` | User or intake Session | `session` |
| `SIV` | Source Inventory | `source_inventory` |
| `SKL` | Skill | `skill` |
| `SMP` | Source Map | `source_map` |
| `SPN` | Trace Span | `trace_span` |
| `SRC` | Source | `source` |
| `SUC` | Success Criterion | `success_criterion` |
| `SVC` | Shared/external service resource | `service_resource` |
| `TAD` | Tool Adapter | `tool_adapter` |
| `TBL` | Technology Baseline | `technology_baseline` |
| `TCN` | Technology Candidate | `technology_candidate` |
| `TEC` | Technology reference | `technology` |
| `TEN` | Test Environment contract | `test_environment` |
| `TEST` | Test Case | `test_case` |
| `TIV` | Tool Invocation | `tool_invocation` |
| `TRP` | Task Report | `task_report` |
| `TRT` | Request Trace | `request_trace` |
| `TSB` | Test Baseline | `test_baseline` |
| `TSK` | Atomic Task | `task` |
| `UNK` | Unknown | `unknown` |
| `VAL` | Validation run/report | `validation` |
| `VFP` | Verification Profile | `verification_profile` |
| `WP` | Work Package | `work_package` |
| `WVR` | Waiver | `waiver` |

`SHA-256` and enum names such as `SIDE-EFFECT` are not entity IDs and are excluded by the ID parser. Prefix cannot have two meanings. Project extensions use a registered namespace and collision check.

## 5. Normalized context and Git prefixes

Чтобы исключить collision:

```text
CTP = Context Policy
CTX = Context Plan
CPK = Context Packet
CPL = Commit Plan
```

Capability Grant uses `CGR`; Lease uses `LSE`; Project Definition uses `PJD`; Evidence uses `EVD`; State Event uses `EVT`.

## 6. Run и Attempt

Отдельная canonical entity `Attempt` отсутствует. Каждый `Run` — одна immutable execution attempt:

```yaml
run:
  id: RUN-20260806-0012
  task_ref: TSK-BE-SEARCH-030@1
  attempt_no: 2
  previous_run_ref: RUN-20260806-0011
  status: PLANNED
```

```text
Task → Run #1 → Run #2
```

Tool Invocations принадлежат Run. Retry всегда создаёт новый Run; существующий Run не изменяется в новую попытку.

## 7. Run Plan Contract

```yaml
run_plan:
  id: RNP-RUN-20260806-0012
  revision: 1
  task_ref: TSK-BE-SEARCH-030@1
  request_ref: RQ-20260806-0004
  work_package_ref: WP-SEARCH-001@1

  base_revisions:
    project: sha256:...
    repository: sha256:...
    task: sha256:...

  prompt_bundle_ref: CPB-RUN-20260806-0012
  context_packet_refs: [CPK-TSK-BE-SEARCH-030-R2]
  adapter_ref: ADP-CODEX@1
  capability_grant_refs: [CGR-RUN-0012]
  lease_refs: [LSE-WT-0012]
  verification_profile_ref: VFP-CODE-TARGETED-001@1
  side_effect_class: REVERSIBLE
  idempotency_key: sha256:...
  status: READY
```

Run Plan имеет собственный schema/storage path и создаётся после readiness, compatibility and permission checks.

## 8. Lifecycle Status Registry

Normative values находятся в `registries/statuses.yaml`. Основные группы:

Ниже приведена generated matrix полного registry; ручное изменение этой таблицы без изменения YAML запрещено.

<!-- REGISTRY-MATRIX: statuses -->
| Status group | Допустимые значения |
|---|---|
| `public_result` | `ANSWERED`, `COMPLETED`, `PARTIAL`, `WAITING_DECISION`, `BLOCKED`, `FAILED_RECOVERABLE`, `NO_ACTION`, `CANCELLED` |
| `request` | `RECEIVED`, `CLASSIFYING`, `CLASSIFIED`, `PLANNING`, `PLANNED`, `READY`, `EXECUTING`, `WAITING_USER_INPUT`, `WAITING_APPROVAL`, `PARTIAL`, `BLOCKED`, `FAILED_RECOVERABLE`, `COMPLETED`, `CANCELLED`, `SUPERSEDED` |
| `questionnaire_session` | `CREATED`, `SOURCE_PENDING`, `ANALYZING_SOURCES`, `QUESTIONING`, `DRAFT_READY`, `WAITING_CONFIRMATION`, `ACCEPTED`, `CANCELLED`, `SUPERSEDED` |
| `session` | `CREATED`, `ACTIVE`, `WAITING_INPUT`, `WAITING_DECISION`, `READY`, `COMPLETED`, `BLOCKED`, `CANCELLED`, `SUPERSEDED` |
| `project_definition` | `DRAFT`, `PROPOSED`, `WAITING_DECISION`, `ACCEPTED`, `STALE`, `SUPERSEDED` |
| `architecture_baseline` | `DRAFT`, `PROPOSED`, `ACCEPTED`, `ACTIVE`, `STALE`, `SUPERSEDED` |
| `work_package` | `DRAFT`, `PLANNED`, `READY`, `IN_PROGRESS`, `PARTIAL`, `BLOCKED`, `COMPLETED`, `CANCELLED`, `SUPERSEDED` |
| `task` | `DRAFT`, `PLANNED`, `READY`, `CLAIMED`, `RUNNING`, `VERIFYING`, `DONE`, `BLOCKED`, `FAILED_RECOVERABLE`, `SPLIT`, `STALE`, `CANCELLED`, `SUPERSEDED` |
| `run_plan` | `DRAFT`, `READY`, `STALE`, `CANCELLED` |
| `run` | `PLANNED`, `READY`, `RUNNING`, `VERIFYING`, `SUCCEEDED`, `FAILED_RETRYABLE`, `FAILED_NON_RETRYABLE`, `BLOCKED`, `CANCELLED`, `TIMED_OUT` |
| `prompt_module` | `DRAFT`, `VALIDATED`, `ACTIVE`, `DEPRECATED`, `RETIRED` |
| `prompt_spec` | `DRAFT`, `VALIDATED`, `ACTIVE`, `DEPRECATED`, `RETIRED` |
| `prompt_plan` | `PLANNED`, `RESOLVED`, `CONSUMED`, `STALE`, `CANCELLED` |
| `compiled_prompt_bundle` | `COMPILED`, `DISPATCHED`, `EXECUTED`, `EXPIRED`, `CANCELLED` |
| `context_plan` | `DRAFT`, `READY`, `CONSUMED`, `STALE`, `CANCELLED` |
| `context_packet` | `GENERATED`, `BOUND`, `CONSUMED`, `STALE`, `EXPIRED` |
| `skill` | `DRAFT`, `VALIDATING`, `VALIDATED`, `REJECTED`, `ACTIVE`, `SUSPENDED`, `DEPRECATED`, `RETIRED` |
| `technology_baseline` | `DRAFT`, `PROPOSED`, `ACCEPTED`, `ACTIVE`, `STALE`, `SUPERSEDED` |
| `lease` | `REQUESTED`, `ACTIVE`, `RELEASED`, `EXPIRED`, `REVOKED` |
| `verification` | `NOT_RUN`, `RUNNING`, `PASS`, `FAIL`, `BLOCKED`, `NOT_APPLICABLE` |
| `change_pack` | `RECEIVED`, `QUARANTINED`, `ANALYZED`, `PROPOSED`, `VALIDATED`, `APPROVED`, `APPLIED`, `CANARY`, `ACTIVE`, `REJECTED`, `ROLLED_BACK`, `FAILED_RECOVERABLE` |
| `compensation` | `NOT_REQUIRED`, `PENDING`, `COMPLETE`, `PARTIALLY_COMPENSATED`, `FAILED` |
| `blocker` | `OPEN`, `MITIGATING`, `RESOLVED`, `SUPERSEDED` |
| `request_plan` | `DRAFT`, `PLANNED`, `READY`, `EXECUTING`, `PARTIAL`, `BLOCKED`, `COMPLETED`, `STALE`, `CANCELLED`, `SUPERSEDED` |
| `question` | `DRAFT`, `OPEN`, `ANSWERED`, `SKIPPED`, `CANCELLED`, `SUPERSEDED` |
| `adr` | `DRAFT`, `PROPOSED`, `WAITING_DECISION`, `ACCEPTED`, `REJECTED`, `SUPERSEDED` |
| `decision` | `ACCEPTED`, `REJECTED`, `SUPERSEDED` |
| `adapter_profile` | `DRAFT`, `VALIDATED`, `ACTIVE`, `SUSPENDED`, `DEPRECATED`, `RETIRED` |
| `bootstrap_plan` | `DRAFT`, `PROPOSED`, `APPROVED`, `EXECUTING`, `COMPLETED`, `BLOCKED`, `FAILED_RECOVERABLE`, `STALE`, `CANCELLED`, `SUPERSEDED` |
| `brownfield_intake` | `CREATED`, `SOURCE_PENDING`, `INVENTORY_PENDING`, `INVENTORY_READY`, `RECONCILING`, `BASELINE_PROPOSED`, `WAITING_APPROVAL`, `ACCEPTED`, `BLOCKED`, `CANCELLED`, `SUPERSEDED` |
| `brownfield_baseline` | `DRAFT`, `PROPOSED`, `ACCEPTED`, `STALE`, `SUPERSEDED` |
| `brownfield_route_item` | `PROPOSED`, `ACCEPTED`, `DEFERRED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `SUPERSEDED` |
| `conflict` | `OPEN`, `ANALYZING`, `RESOLVED`, `ACCEPTED_AS_RISK`, `SUPERSEDED` |
| `constraint` | `DRAFT`, `PROPOSED`, `ACTIVE`, `WAIVED`, `RETIRED`, `SUPERSEDED` |
| `parallel_batch` | `DRAFT`, `PLANNED`, `READY`, `IN_PROGRESS`, `INTEGRATING`, `PARTIAL`, `BLOCKED`, `COMPLETED`, `STALE`, `CANCELLED`, `SUPERSEDED` |
| `project_profile` | `DRAFT`, `PROPOSED`, `CONFIRMED`, `ACTIVE`, `STALE`, `SUPERSEDED` |
| `requirement` | `DRAFT`, `PROPOSED`, `ACCEPTED`, `REJECTED`, `STALE`, `SUPERSEDED` |
| `test_environment` | `DRAFT`, `PROVISIONING`, `READY`, `IN_USE`, `STALE`, `FAILED`, `RETIRED` |
| `tool_invocation` | `PLANNED`, `RUNNING`, `SUCCESS`, `FAILED`, `BLOCKED`, `CANCELLED`, `TIMED_OUT` |
| `verification_profile` | `DRAFT`, `VALIDATED`, `ACTIVE`, `DEPRECATED`, `RETIRED` |
| `waiver` | `PROPOSED`, `ACTIVE`, `EXPIRED`, `REVOKED`, `SUPERSEDED` |
| `implementation_stage` | `PLANNED`, `ACTIVE`, `VERIFYING`, `ACCEPTED`, `BLOCKED`, `SUPERSEDED` |
| `project_execution` | `ACTIVE`, `BLOCKED`, `TARGET_LEVEL_REACHED`, `CANCELLED` |
| `sandbox_profile` | `DRAFT`, `VALIDATED`, `ACTIVE`, `SUSPENDED`, `DEPRECATED`, `RETIRED` |
<!-- /REGISTRY-MATRIX -->

### Request

```text
RECEIVED, CLASSIFYING, CLASSIFIED, PLANNING, PLANNED,
READY, EXECUTING, WAITING_USER_INPUT, WAITING_APPROVAL,
PARTIAL, BLOCKED, FAILED_RECOVERABLE, COMPLETED,
CANCELLED, SUPERSEDED
```

### Work Package

```text
DRAFT, PLANNED, READY, IN_PROGRESS, PARTIAL, BLOCKED,
COMPLETED, CANCELLED, SUPERSEDED
```

### Task

```text
DRAFT, PLANNED, READY, CLAIMED, RUNNING, VERIFYING,
DONE, BLOCKED, FAILED_RECOVERABLE, SPLIT, STALE,
CANCELLED, SUPERSEDED
```

### Run

```text
PLANNED, READY, RUNNING, VERIFYING, SUCCEEDED,
FAILED_RETRYABLE, FAILED_NON_RETRYABLE, BLOCKED,
CANCELLED, TIMED_OUT
```

### Public Result

```text
ANSWERED, COMPLETED, PARTIAL, WAITING_DECISION,
BLOCKED, FAILED_RECOVERABLE, NO_ACTION, CANCELLED
```

### Compensation

```text
NOT_REQUIRED, PENDING, COMPLETE, PARTIALLY_COMPENSATED, FAILED
```

### Change Pack

```text
RECEIVED, QUARANTINED, ANALYZED, PROPOSED, VALIDATED,
APPROVED, APPLIED, CANARY, ACTIVE, REJECTED,
ROLLED_BACK, FAILED_RECOVERABLE
```

Prompt, Context, Skill, Technology Baseline, Lease and Questionnaire status groups are also defined in the machine registry.

## 9. Status semantics

- `COMPILED` belongs only to Compiled Prompt Bundle.
- `DONE` belongs to Task.
- `SUCCEEDED` belongs to Run.
- `COMPLETED` belongs to Request, Work Package or public Result.
- `PARTIALLY_COMPENSATED` belongs to compensation status only.
- `STALE` means invalidated input revision, not implementation failure.
- public Result status is a projection of internal lifecycle, not a replacement for it.

## 10. Request Routing Registry

Request Class, Request Mode and internal Operation are separate enum groups. Полный generated registry view:

<!-- REGISTRY-MATRIX: request_routing -->
```yaml
request_classes:
  - QUERY
  - PROJECT_START
  - DEVELOPMENT_REQUEST
  - PROJECT_EVOLUTION
  - PROJECT_CONTROL_MAINTENANCE
  - HARNESS_DISTRIBUTION_MAINTENANCE
  - CONTROL_REQUEST
request_modes:
  - READ_ONLY
  - PLAN
  - EXECUTE
internal_operations:
  - ANSWER
  - INSPECT_SOURCES
  - START_INTAKE
  - ASK_QUESTION_BATCH
  - RECONCILE_PROJECT
  - DEFINE_PROJECT
  - PROPOSE_ARCHITECTURE
  - BUILD_TECHNOLOGY_BASELINE
  - PREPARE_SKILLS
  - BOOTSTRAP_PROJECT
  - PLAN_WORK
  - COMPILE_TASK
  - RUN_TASK
  - VALIDATE_RESULT
  - UPDATE_DOCUMENTATION
  - RESUME_ROUTE
  - REPORT_STATUS
  - PUBLISH_CHANGE
  - APPLY_CHANGE_PACK
```
<!-- /REGISTRY-MATRIX -->

An operation such as `COMPILE_TASK` is never treated as user intent. `QUERY` does not create Tasks unless the user explicitly requests a side effect.

## 11. Capability Registry

Capability keys are deny-by-default. `PROJECT_CONTROL_WRITE` and `HARNESS_DISTRIBUTION_WRITE` are separate and cannot be implied by `FILESYSTEM_WRITE`. Unknown capability is denied.

<!-- REGISTRY-MATRIX: capabilities -->
```text
FILESYSTEM_READ
FILESYSTEM_WRITE
COMMAND_EXECUTE
NETWORK_READ
NETWORK_WRITE
SECRET_REFERENCE
MODEL_EXTERNAL_EGRESS
GIT_COMMIT
GIT_PUSH
PR_CREATE
EXTERNAL_SYSTEM_WRITE
DEPLOY
DATA_MIGRATE
DATA_DELETE
RELEASE_PUBLISH
PROJECT_CONTROL_WRITE
HARNESS_DISTRIBUTION_WRITE
```
<!-- /REGISTRY-MATRIX -->

## 12. Migration from v0.2

```text
REQST → RQ
DECMP → WP or a non-persistent decomposition step
ACTOR → ACT
PDF → PJD
CTXP → CTP
GRANT → CGR
LEASE → LSE
PRM → PSP/PMD/PPL depending on entity
ECP → CMP
EV evidence collision → EVD for Evidence, EVT for Event
Attempt entity → Run.attempt_no
contract_set → contract read/write sets
```

Aliases exist only in migration parser. New v0.3 generated artifacts must use canonical prefixes.

## 13. Contract completeness rule

Every persistent canonical entity must declare:

- schema key and schema version;
- ID prefix;
- lifecycle/status group;
- storage path;
- source/provenance fields;
- revision/hash semantics;
- authority and mutability;
- migration policy;
- reference examples;
- semantic validation rules.

If an entity is internal and non-persistent, documentation must explicitly say so.

## 14. Canonical Contract Catalog

`registries/contracts.yaml` классифицирует каждый standalone contract example как lifecycle-managed, immutable record или external config и связывает его с ID prefix, logical storage path и revision policy.

Нормализованные field rules:

| Entity | Канонические поля | Запрещённые aliases |
|---|---|---|
| `Request` | `idempotency_key` хранится в Request record; transport metadata отображается в это поле | отсутствие key при repeatable call |
| `Project Definition` | common `success_criterion_refs`; `DRAFT/PROPOSED` используют `scope` + `proposed_profile_refs`; `ACCEPTED` использует `scope_ref` + `profile_ref` + `accepted_by` | `success_criteria_refs`; смешение draft и accepted fields |
| `Task` | `documentation` object с `source_refs`, `impact`, `required_updates` | `documentation_refs` как альтернативная top-level schema |
| `Brownfield Baseline` | `accepted_actual_structure_ref` | `actual_structure_ref` |
| `Brownfield Route Item` | `estimated_risk` | `risk` |
| `Parallel Batch` | `lease_refs` | `leases` |
| `Change Pack` | `normalized_changes`, `required_capabilities` | `proposed_changes`, `requested_capabilities` |

Draft/accepted variants являются версиями одной schema, а не конкурирующими контрактами. Переход в `ACCEPTED` обязан нормализовать draft-only fields в accepted references.

## 15. Extension rules

Project/profile extensions:

- use an allocated namespace;
- may add values but cannot redefine baseline semantics;
- declare compatibility range;
- include migration and rollback;
- pass collision and schema validation;
- are recorded in Project Lock.

## 16. Критерии приёмки

1. All profile lists are generated from one registry.
2. ID prefix has exactly one meaning.
3. Request Plan and Run Plan have contracts and storage paths.
4. Run is one attempt; retry creates a new Run.
5. Status values are valid only for declared entity types.
6. `PARTIALLY_COMPENSATED` is not used as Change Pack lifecycle status.
7. Unknown enum/prefix breaks semantic validation.
8. Migration aliases do not appear in new generated artifacts.
9. Context and Commit prefixes do not collide.
10. Registry hashes are included in distribution validation and Project Lock.
11. Standalone contract examples match `contracts.yaml`, including lifecycle binding, ID prefix and canonical field names.
