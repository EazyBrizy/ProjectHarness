# Расширенные contracts: brownfield, parallelism, verification and trace

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Source Inventory

```yaml
source_inventory:
  id: SIV-20260806-001
  session_ref: SES-20260806-001
  sources:
    - ref: SRC-DOC-001
      kind: DOCUMENT
      authority: UNKNOWN
      trust: PROJECT_SUPPLIED
      revision: sha256:...
      readability: PASS
  conflicts: []
  missing_material_dimensions: []
```

## 2. Brownfield repository inventory

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

## 3. Brownfield Baseline

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
  test_baseline_ref: TSB-APP-001
  known_gaps: []
  known_defects: []
  technical_debt_items: []
  documentation_conflicts: []
```

## 4. Brownfield route item

```yaml
brownfield_route_item:
  id: BRI-FIX-001
  route: FIX_KNOWN_BUGS
  title: "Исправить потерю фильтра"
  evidence_refs: [EVD-BUG-001]
  requirement_refs: [REQ-SEARCH-001]
  estimated_risk: MEDIUM
  value: HIGH
  proposed_work_package_ref: WP-FIX-SEARCH-001
  status: PROPOSED
```

## 5. Parallel Batch

```yaml
parallel_batch:
  id: PBT-SEARCH-001
  work_package_ref: WP-SEARCH-001
  task_refs: [TSK-DB-020, TSK-BE-030, TSK-FE-040]
  frozen_inputs:
    - ref: CNT-SEARCH@2
      hash: sha256:...
  conflict_analysis_ref: CFA-PBT-SEARCH-001
  lease_refs: [LSE-WT-BE-001, LSE-WT-FE-001]
  integration_task_ref: TSK-INT-050
  failure_policy: CONTINUE_INDEPENDENT_TASKS
  status: READY
```

## 6. Verification Profile

```yaml
verification_profile:
  id: VFP-CODE-TARGETED-001
  revision: 1
  applies_to: [IMPLEMENT, FIX, REFACTOR]
  risk_level: MEDIUM
  required_checks:
    - TARGETED_TESTS
    - NEAREST_REGRESSION
    - STATIC_ANALYSIS
    - SCOPE_DIFF_CHECK
    - DOCUMENTATION_IMPACT_CHECK
  completion_rule: ALL_REQUIRED_PASS
  status: ACTIVE
```

## 7. Test Environment

```yaml
test_environment:
  id: TEN-APP-TEST
  revision: 5
  strategy: PREMIGRATED_TEMPLATE
  migration_set_hash: sha256:...
  fixture_version: 12
  isolation:
    mode: SCHEMA_PER_RUN
    cleanup: DROP_SCHEMA_ON_SUCCESS_OR_TTL
  reset_strategy: TRANSACTION_ROLLBACK
  rebuild_when: [MIGRATION_SET_CHANGED, TEMPLATE_INCOMPATIBLE, CORRUPTION_DETECTED]
  status: READY
```

## 8. Test Baseline

```yaml
test_baseline:
  id: TSB-20260806-001
  repository_revision: sha256:...
  environment_ref: TEN-APP-TEST@5
  selected_suite: NEAREST_REGRESSION
  passed: 124
  failed:
    - test_ref: TEST-LEGACY-007
      failure_hash: sha256:...
      classification: KNOWN_UNRELATED
```

## 9. Verification Evidence

```yaml
verification_evidence:
  schema_version: 1
  id: EVD-TSK-BE-SEARCH-020-001
  ref: EVD-TSK-BE-SEARCH-020-001
  kind: TEST_REPORT
  status: PASS
  provenance:
    source_type: PROJECT_HARNESS_VALIDATION_REPORT
    source_ref: VAL-RUN-20260806-0012
    producer: PROJECT_HARNESS_RUNTIME
  base_revision: tree:sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  criterion_refs: [PROTOTYPE_CORE_FLOW]
  outcome_refs: []
  profile_control_refs: []
  source_bindings:
    - ref: VAL-RUN-20260806-0012
      path: .harness/reports/VAL-RUN-20260806-0012.yaml
      sha256: sha256:abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
  created_at: 2026-08-18T12:00:00Z
  task_ref: TSK-BE-SEARCH-020@1
  run_ref: RUN-20260806-0012
  report_refs: [VAL-RUN-20260806-0012]
  validator: PROJECT_HARNESS_RUNTIME
```

Artifact хранится только по `.harness/evidence/EVD-TSK-BE-SEARCH-020-001.yaml`. Historical evidence без `schema_version` остаётся readable, но не закрывает новый Stage Gate.

## 10. Request Trace

```yaml
request_trace:
  id: TRT-COR-20260806-0001
  correlation_id: COR-20260806-0001
  project_ref: project-example
  actor_ref: ACT-USER-001
  spans:
    - id: SPN-001
      type: REQUEST_RECEIVED
      entity_ref: RQ-20260806-0001
      status: OK
    - id: SPN-002
      parent_span_ref: SPN-001
      type: REQUEST_CLASSIFIED
      entity_ref: RQ-20260806-0001
      status: OK
    - id: SPN-003
      parent_span_ref: SPN-001
      type: TASK_RUN
      entity_ref: RUN-20260806-0012
      status: OK
  result_ref: RES-20260806-0001
  terminal_status: COMPLETED
```

## 11. Tool Invocation

```yaml
tool_invocation:
  id: TIV-20260806-0042
  run_ref: RUN-20260806-0012
  task_ref: TSK-BE-SEARCH-020@1
  adapter_ref: ADP-FILESYSTEM@2
  capability_grant_ref: CGR-RUN-0012
  operation: WRITE_FILE
  normalized_target: src/backend/search/service.ts
  actual_write_paths: [src/backend/search/service.ts]
  status: SUCCESS
```

## 12. Documentation reference/result

```yaml
documentation_ref:
  entity_ref: REQ-SEARCH-001
  document: docs/requirements/search.md
  section_id: search-by-name
  heading_hint: "Поиск по названию"
  revision: 2
  content_hash: sha256:...
  relation: SOURCE
```

```yaml
documentation_result:
  status: UPDATED
  updated:
    - entity_ref: DOC-API-SEARCH
      previous_revision: 2
      resulting_revision: 3
      path: docs/api/search.md
      sections: [endpoint-search]
  validation_evidence_refs: [EVD-DOC-LINKS-001]
```

## 13. Agent Task Result

```yaml
agent_task_result:
  schema_version: 1
  task_ref: TSK-BE-SEARCH-020@1
  run_ref: RUN-20260806-0012
  execution_status: COMPLETED
  summary: "Реализован search service"
  changes:
    added: []
    modified: [src/backend/search/service.ts]
    removed: []
  verification_claims:
    - criterion_ref: AC-SEARCH-BE-001
      result: PASS
  assumptions: []
  questions: []
  blockers: []
```

## 17. v0.4.1 Brownfield acceptance records

Accepted Brownfield Baseline содержит `accepted_by`, `accepted_at` и, для successor revision, `previous_revision_ref`. `accepted_by` указывает на отдельный immutable Decision с lifecycle `decision` и status `ACCEPTED`. Compiler не имеет права присвоить `ACCEPTED` только потому, что остальные approvals уже подтверждены.

## 18. Stage State v0.5.0

```yaml
stage_state:
  scale_version: 1
  target_level: MVP
  claimed_current_level: NONE
  observed_candidate_level: NONE
  highest_accepted_level: NONE
  active_stage: PROTOTYPE
  progression_policy: SEQUENTIAL
  future_stage_work: FORBIDDEN
  stage_path: [PROTOTYPE, ALPHA, BETA, MVP]
  revision: 1
```

## 19. Stage Plan v0.5.0

```yaml
stage_plan:
  id: STG-PROJECT-PROTOTYPE-001
  revision: 1
  level: PROTOTYPE
  status: ACTIVE
  target_level: MVP
  baseline_ref: PJD-PROJECT-001@1
  scope_refs: [REQ-PROJECT-001@1]
  required_outcomes: [working_primary_flow, documented_local_start]
  criteria_profile_ref: REG-IMPLEMENTATION-LEVELS#PROTOTYPE
  hard_constraint_overrides: []
  work_package_outlines:
    - title: Core vertical slice
      outcome: Main user flow works end to end
  deferred_to_next_stage: [real persistence, critical integration tests]
```

## 20. Stage Gate v0.5.0

```yaml
stage_gate:
  id: GATE-PROJECT-PROTOTYPE-001
  revision: 2
  previous_revision_ref: GATE-PROJECT-PROTOTYPE-001@1
  type: STAGE_ACCEPTANCE
  level: PROTOTYPE
  stage_plan_ref: STG-PROJECT-PROTOTYPE-001@2
  status: RUNNING
  base_revision: tree:sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  criteria_results:
    - criterion_ref: PROTOTYPE_CORE_FLOW
      mandatory: true
      status: PASS
      evidence_refs: [EVD-PROJECT-SMOKE-001]
      rationale: Core flow verified from accepted baseline
      validator: ACT-VALIDATOR-001
  required_work_package_refs: [WP-PROJECT-001@1]
  critical_blocker_refs: []
  evidence_refs: [EVD-PROJECT-SMOKE-001]
  evidence_bindings:
    - ref: EVD-PROJECT-SMOKE-001
      path: .harness/evidence/EVD-PROJECT-SMOKE-001.yaml
      sha256: sha256:89abcdef0123456789abcdef0123456789abcdef0123456789abcdef01234567
  permitted_use:
    users: [DEVELOPER]
    environments: [LOCAL]
    data_classes: [PUBLIC]
    data_constraints: [SYNTHETIC_ONLY]
```

### 20.1. Strict Stage approval preparation record

The operator does not reconstruct this contract by reading `stage_gate` internals. For the current active `VERIFYING`/Gate-related `BLOCKED` Stage:

```bash
project-harness stage-status --project <root>
project-harness prepare-stage-approval \
  --project <root> \
  --output ../operator-records/prototype-approval.yaml
```

The command writes a complete exact-bound document conforming to `SCHEMA-STAGE-APPROVAL@1`. A generated excerpt:

```text
stage_approval:
  schema_version: 1
  schema_ref: SCHEMA-STAGE-APPROVAL@1
  record_kind: STAGE_APPROVAL
  record_state: DRAFT
  id: null
  approved: false
  actor: null
  approved_at: null
  level: PROTOTYPE
  target_level: PROTOTYPE
  acceptance_method: EXECUTED_STAGE_WORK
  stage_plan_ref: STG-PROJECT-PROTOTYPE-001@2
  stage_plan_path: .harness/stages/PLANS/STG-PROJECT-PROTOTYPE-001@2.yaml
  stage_plan_revision: 2
  stage_plan_digest: sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  prepared_from_stage_plan_status: VERIFYING
  gate_ref: GATE-PROJECT-PROTOTYPE-001@2
  gate_path: .harness/stages/GATES/GATE-PROJECT-PROTOTYPE-001@2.yaml
  gate_revision: 2
  gate_digest: sha256:89abcdef0123456789abcdef0123456789abcdef0123456789abcdef01234567
  prepared_from_gate_status: VERIFYING
  gate_base_revision: PJD-PROJECT-001@1
  baseline_revision: tree:sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  last_acceptance_ref: null
  last_acceptance_path: null
  last_accepted_baseline_revision: null
  assessment_ref: null
  assessment_digest: null
  required_outcomes:
    - outcome_ref: working_primary_flow
      mandatory: true
      applicability: ALWAYS
  outcome_results:
    - outcome_ref: working_primary_flow
      status: UNKNOWN
      evidence_refs: []
      rationale: null
      validator: null
  level_criteria:
    - criterion_ref: PROTOTYPE_CORE_FLOW
      dimension: FUNCTIONALITY
      description: One bounded end-to-end core flow works.
      mandatory: true
      applicability: ALWAYS
      required_evidence_kinds: [TEST_REPORT, MANUAL_VERIFICATION]
      execution_evidence_required: true
  criteria_results:
    - criterion_ref: PROTOTYPE_CORE_FLOW
      status: UNKNOWN
      evidence_refs: []
      rationale: null
      validator: null
  hard_constraints: []
  hard_constraint_results: []
  profile_controls: []
  profile_control_results: []
  required_work_packages: []
  critical_blockers: []
  permitted_use:
    status: UNCONFIRMED
    users: [DEVELOPER]
    environments: [LOCAL]
    data_classes: [PUBLIC]
    data_constraints: [SYNTHETIC_ONLY]
  evidence_candidates: []
  unresolved_gaps: []
  evidence_refs: []
  known_limitations: []
  next_stage_gaps: []
  notes: null
  preparation_fingerprint: sha256:fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210
```

The complete schema-valid generated fixture, including full definitions, candidate evidence and unresolved gaps, is stored at [`examples/stage_approval.draft.yaml`](examples/stage_approval.draft.yaml). It is illustrative: every real Project Instance must generate a fresh file because Plan/Gate refs, digests, product baseline, WP/blocker snapshot and fingerprint are exact-bound.

All mandatory generated results remain `UNKNOWN`; candidates never become conclusions automatically. Preparation creates no Decision or Acceptance Report and performs no Stage/product mutation.

### 20.2. Transition from DRAFT to formal APPROVED record

After independent review, the operator fills the same exact-bound record rather than creating a new hand-written contract:

```yaml
record_state: APPROVED
id: DEC-PROJECT-STAGE-PROTOTYPE-001
approved: true
actor: ACT-APPROVER-001
approved_at: 2026-08-20T12:00:00Z
permitted_use:
  status: CONFIRMED
  users: [DEVELOPER]
  environments: [LOCAL]
  data_classes: [PUBLIC]
  data_constraints: [SYNTHETIC_ONLY]
```

Every mandatory result becomes `PASS` with exact compatible normalized `EVD-*` refs or justified `NOT_APPLICABLE` with rationale/validator. Before mutation, `accept-stage` validates `SCHEMA-STAGE-APPROVAL@1` and rebinds the record to the exact current Plan/Gate/baseline contract. Product or Gate drift makes the record stale.

## 21. Stage Acceptance v0.5.0

```yaml
stage_acceptance:
  id: VAL-PROJECT-PROTOTYPE-001
  revision: 1
  level: PROTOTYPE
  status: PASS
  acceptance_method: EXECUTED_STAGE_WORK
  baseline_revision: tree:sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  accepted_at: 2026-08-18T00:00:00Z
  accepted_by: ACT-APPROVER-001
  decision_ref: DEC-PROJECT-STAGE-PROTOTYPE-001@1
  stage_plan_ref: STG-PROJECT-PROTOTYPE-001@2
  gate_ref: GATE-PROJECT-PROTOTYPE-001@2
  evidence_refs: [EVD-PROJECT-SMOKE-001]
  evidence_bindings:
    - ref: EVD-PROJECT-SMOKE-001
      path: .harness/evidence/EVD-PROJECT-SMOKE-001.yaml
      sha256: sha256:89abcdef0123456789abcdef0123456789abcdef0123456789abcdef01234567
  permitted_use:
    users: [DEVELOPER]
    environments: [LOCAL]
    data_classes: [PUBLIC]
    data_constraints: [SYNTHETIC_ONLY]
  known_limitations: [no authentication, local storage only]
  next_stage_gaps: [real persistence, critical integration tests]
```

Accepted Gate и Stage Acceptance сохраняют один и тот же sorted evidence binding snapshot. `validate-project` повторно разрешает refs и отклоняет deletion, content/source tampering или Gate/Acceptance divergence.

## 22. Brownfield Maturity Assessment v0.5.0

```yaml
maturity_assessment:
  id: VAL-PROJECT-MATURITY-001
  revision: 1
  repository_revision: tree:sha256:example
  claimed_current_level: BETA
  observed_candidate_level: BETA
  highest_satisfied_candidate_level: ALPHA
  previous_highest_accepted_level: NONE
  proposed_active_stage: BETA
  target_level: RELEASE
  confidence: MEDIUM
  criteria_results:
    PROTOTYPE: []
    ALPHA: []
    BETA:
      - criterion_ref: BETA_END_TO_END_REGRESSION
        mandatory: true
        status: UNKNOWN
        evidence_refs: []
        rationale: Runtime evidence was not supplied and commands were not executed
  dimensions:
    FUNCTIONALITY: BETA
    TESTING_VERIFICATION: ALPHA
    DEPLOYMENT_OPERABILITY: PROTOTYPE
  blocking_gaps: [end-to-end regression evidence missing, rollback not verified]
  recommended_route: COMPLETE_CURRENT_STAGE
```

Assessment does not change `highest_accepted_level`; approval references its exact revision and digest.

Для baseline disposition binding выглядит так:

```yaml
stage_approval:
  acceptance_method: SATISFIED_BY_BASELINE
  assessment_ref: VAL-PROJECT-MATURITY-001@1
  assessment_digest: sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

`assessment_ref` разрешается только в exact path `.harness/stages/ASSESSMENTS/VAL-PROJECT-MATURITY-001@1.yaml`. Resolver не выполняет glob и до Stage mutation сверяет filename, envelope `maturity_assessment`, internal `id: VAL-PROJECT-MATURITY-001`, integer `revision: 1` и SHA-256 exact file bytes. Соответствующий Stage Acceptance Report сохраняет тот же validated ref.

## 23. Same-level Maintenance records v0.5.0

### 23.1. Strict start plan

The operator supplies one exact-bound record. All normative object levels reject unknown properties. The identifiers below are examples; project-local ids must use the prepared project token.

```text
maintenance_plan:
  schema_version: 1
  schema_ref: SCHEMA-MAINTENANCE-PLAN@1
  record_kind: MAINTENANCE_PLAN
  id: RQP-MYPROJECT-MAINT-001
  revision: 1
  status: APPROVED
  route: MAINTAIN_CURRENT_STAGE
  highest_accepted_level: PROTOTYPE
  implementation_stage: PROTOTYPE
  target_level: MVP
  last_acceptance_ref: VAL-MYPROJECT-PROTOTYPE-001@1
  accepted_scope_ref: SCP-MYPROJECT-001@1
  objective: Repair accepted documentation without changing product scope or maturity.
  rationale: The accepted baseline requires a bounded same-level correction.
  decision:
    id: DEC-MYPROJECT-MAINT-001
    kind: MAINTAIN_CURRENT_STAGE
    approved: true
    actor: ACT-MAINTENANCE-APPROVER-001
    approved_at: 2026-08-20T12:00:00Z
  scope_boundary:
    future_stage_work: FORBIDDEN
    future_stage_refs: []
  work_package:
    id: WP-MYPROJECT-MAINT-001
    title: Governed same-level documentation repair
    objective: Apply and verify only the approved accepted-scope repair.
    implementation_stage: PROTOTYPE
    tasks:
      - id: TSK-MYPROJECT-MAINT-001-001
        title: Repair accepted operator guidance
        type: DOCUMENT
        priority: NORMAL
        purpose: Correct the accepted README workflow.
        expected_result: README contains the verified corrected workflow.
        implementation_stage: PROTOTYPE
        product_changing: true
        future_stage_work: FORBIDDEN
        depends_on_tasks: []
        requirement_refs: []
        constraint_refs: []
        architecture_refs: []
        produces_artifacts: [README.md]
        scope:
          read: [README.md]
          write: [README.md]
          forbidden: [.harness/**, src/future-stage/**]
        route:
          primary_skill_ref: SKL-UNIVERSAL-DOCUMENT@1
          supporting_skill_refs: []
          required_capabilities: [FILESYSTEM_READ, FILESYSTEM_WRITE, COMMAND_EXECUTE]
        prompt_spec_ref: PSP-IMPLEMENT@1
        verification:
          commands:
            - argv: [python, -m, unittest, discover, -s, tests, -v]
              cwd: .
              timeout_seconds: 300
          expected_paths: [README.md]
          manual_checks: []
          timeout_seconds: 300
          allow_manual: false
        documentation:
          source_refs: []
          impact: UPDATE_EXISTING
          required_updates: [README.md]
        acceptance_criteria:
          - Corrected workflow is present.
          - Existing tests pass.
        rollback:
          strategy: RESTORE_PRE_RUN_SNAPSHOT
  verification_constraints:
    independent_verification_required: true
    completion_requires_pass: true
  rollback_constraints:
    automatic_rollback: false
    strategy: RESTORE_PRE_RUN_SNAPSHOT
  cancel_constraints:
    before_product_change_only: true
    completed_product_change_action: REQUIRE_COMPLETION_OR_GOVERNED_COMPENSATION
```

`start-maintenance` re-resolves every exact binding from the current project. It creates the stored immutable plan and `MAINTAIN_CURRENT_STAGE` Decision plus maintenance WP/Tasks/DAG/VFP/CTX/PPL and one first JIT reservation. `implementation_stage` on every executable artifact is the exact accepted level; the current target and Stage acceptance history remain unchanged.

### 23.2. Strict cancel approval

```text
maintenance_cancel_approval:
  schema_version: 1
  schema_ref: SCHEMA-MAINTENANCE-CANCEL-APPROVAL@1
  record_kind: MAINTENANCE_CANCEL_APPROVAL
  id: DEC-MYPROJECT-MAINT-CANCEL-001
  revision: 1
  kind: CANCEL_MAINTENANCE
  approved: true
  actor: ACT-MAINTENANCE-APPROVER-001
  approved_at: 2026-08-20T13:00:00Z
  maintenance_plan_ref: RQP-MYPROJECT-MAINT-001@1
  work_package_ref: WP-MYPROJECT-MAINT-001@1
  highest_accepted_level: PROTOTYPE
  target_level: MVP
  last_acceptance_ref: VAL-MYPROJECT-PROTOTYPE-001@1
  rationale: Cancel before any product-changing Task is completed.
  cancel_mode: PRE_PRODUCT_CHANGE_ONLY
```

The approval must match the open route exactly. Valid cancellation writes an immutable `CANCEL_MAINTENANCE` Decision, terminal Task/WP revisions and `MAINTENANCE_CANCELLATION` report, then restores the previous route. Cancellation is fail-closed after completed or observed product-changing work and never deletes historical revisions or performs automatic rollback.

### 23.3. Completion report

The Kernel creates, rather than accepts from the operator, an immutable report under `.harness/maintenance/REPORTS/<VAL-...@1>.yaml`:

```text
maintenance_report:
  id: VAL-MYPROJECT-MAINT-COMPLETE-EXAMPLE
  revision: 1
  kind: MAINTENANCE_COMPLETION
  status: COMPLETED
  maintenance_route: MAINTAIN_CURRENT_STAGE
  maintenance_plan_ref: RQP-MYPROJECT-MAINT-001@1
  start_decision_ref: DEC-MYPROJECT-MAINT-001@1
  work_package_ref: WP-MYPROJECT-MAINT-001@3
  implementation_stage: PROTOTYPE
  highest_accepted_level: PROTOTYPE
  target_level: MVP
  last_acceptance_ref: VAL-MYPROJECT-PROTOTYPE-001@1
  task_refs: [TSK-MYPROJECT-MAINT-001-001@2]
  task_report_refs: [TRP-MYPROJECT-MAINT-001]
  run_refs: [RUN-MYPROJECT-120-A1]
  evidence_refs: [EVD-MYPROJECT-120-A1]
  completion_rule: ALL_MANDATORY_PASS
  completed_at: 2026-08-20T14:00:00Z
```
