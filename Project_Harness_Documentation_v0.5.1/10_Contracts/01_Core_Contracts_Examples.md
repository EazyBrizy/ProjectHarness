# Примеры ключевых машинных контрактов v0.5.0

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

Примеры нормативны по структуре и enum, но machine schemas должны дополнительно задавать types, required fields, patterns, conditional rules and compatibility.

## 1. Project config

```yaml
project:
  id: project-example
  name: Example Project
  harness_schema_version: 6
  lifecycle_mode: GREENFIELD
  profile_ref: PRF-API-SERVICE@1
  project_definition_ref: PJD-PROJECT-001@1
  architecture_baseline_ref: ARB-PROJECT-001@1
  technology_baseline_ref: TBL-PROJECT-001@1
  state_ref: .harness/state/PROJECT_STATE.yaml
  ambiguity_mode: PRAGMATIC
  project_lock_ref: .harness/config/PROJECT_LOCK.yaml
```

## 2. Request

```yaml
request:
  id: RQ-20260806-0001
  schema_version: 1
  project_ref: project-example
  session_ref: SES-20260806-0001
  correlation_id: COR-20260806-0001
  idempotency_key: sha256:client-scope-and-normalized-request
  input:
    raw_text: "Добавь поиск по названию"
    source_refs: []
    actor_ref: ACT-USER-001
    received_at: 2026-08-06T09:00:00Z
  classification:
    request_class: DEVELOPMENT_REQUEST
    mode: EXECUTE
    confidence: 0.96
    material_ambiguity_refs: []
  status: CLASSIFIED
```

## 3. Request Plan

```yaml
request_plan:
  id: RQP-20260806-0001
  request_ref: RQ-20260806-0001
  project_ref: project-example
  base_project_revision: sha256:...
  objective: "Добавить поиск по названию"
  request_class: DEVELOPMENT_REQUEST
  mode: EXECUTE
  routes:
    - id: RTE-PLAN-001
      sequence: 10
      operation: PLAN_WORK
      output_ref_type: WORK_PACKAGE
      depends_on: []
    - id: RTE-RUN-001
      sequence: 20
      operation: RUN_TASK
      output_ref_type: TASK_REPORT
      depends_on: [RTE-PLAN-001]
  expected_result_schema_ref: SCHEMA-RESULT-ENVELOPE@1
  status: PLANNED
```

## 4. Result Envelope

```yaml
result:
  id: RES-20260806-0001
  request_ref: RQ-20260806-0001
  correlation_id: COR-20260806-0001
  project_ref: project-example
  work_package_ref: WP-SEARCH-001
  task_ref: TSK-BE-SEARCH-020
  run_ref: RUN-20260806-0012
  status: COMPLETED
  title: "Поиск по названию реализован"
  summary: "Добавлен endpoint, обновлена документация и пройдены проверки"
  changes:
    added: []
    changed: []
    removed: []
  verification:
    status: PASS
    checks: []
  documentation:
    status: UPDATED
    updated_refs: [DOC-API-SEARCH@3]
  blockers: []
  recovery_options: []
  next_step:
    route: RUN_NEXT_READY_TASK
    task_ref: TSK-FE-SEARCH-030
    requires_user_action: false
```

## 5. Questionnaire Session and Question

```yaml
questionnaire_session:
  id: QNS-20260806-0001
  intake_session_ref: SES-20260806-0001
  project_mode: GREENFIELD
  source_inventory_ref: SIV-20260806-0001
  question_budget:
    target: 10
    hard_limit_before_draft: 15
    asked: 4
    answered: 4
  status: QUESTIONING
```

```yaml
question:
  id: QST-CONNECTIVITY-001
  session_ref: QNS-20260806-0001
  text: "Должна ли система работать без интернета?"
  why_asked: "Ответ влияет на storage and synchronization architecture"
  materiality: MATERIAL
  answer_type: SINGLE_CHOICE
  options:
    - {id: ONLINE_ONLY, label: "Только онлайн"}
    - {id: LIMITED_OFFLINE, label: "Часть функций офлайн"}
    - {id: OFFLINE_FIRST, label: "Offline-first"}
    - {id: UNKNOWN, label: "Не знаю"}
  recommendation: {option_ref: ONLINE_ONLY, rationale: "Нет offline requirement"}
  status: OPEN
```

## 6. Project Definition

```yaml
project_definition:
  id: PJD-PROJECT-001
  revision: 1
  status: ACCEPTED
  session_ref: SES-20260806-0001
  source_refs: [SRC-DOC-001]
  problem_statement: "Команде нужен каталог оборудования"
  user_refs: [ACT-USER-GROUP-001]
  outcome_refs: [OUT-CATALOG-001]
  goal_refs: [GOL-CATALOG-001]
  success_criterion_refs: [SUC-CATALOG-001]
  scope_ref: SCP-PROJECT-001
  constraint_refs: [CST-DATA-001]
  assumption_refs: [ASM-SCALE-001]
  unknown_refs: []
  profile_ref: PRF-WEB-APPLICATION@1
  ambiguity_mode: PRAGMATIC
  accepted_by: DEC-PROJECT-001
```

## 7. Technology Baseline

```yaml
technology_baseline:
  id: TBL-PROJECT-001
  revision: 1
  status: ACCEPTED
  driver_refs: [REQ-SEARCH-001, CST-PLATFORM-001]
  selections:
    - area: LANGUAGE
      technology_ref: TEC-TYPESCRIPT
      version_constraint: ">=5.6 <6"
      decision_ref: ADR-TECH-001
    - area: DATABASE
      technology_ref: TEC-POSTGRES
      version_constraint: "16.x"
      decision_ref: ADR-DATA-002
  compatibility_matrix_ref: CMP-TECH-001
  verification_commands: []
```

## 8. ADR

```yaml
adr:
  id: ADR-DATA-002
  revision: 1
  title: "Основная relational database"
  decision_type: MATERIAL_TECHNOLOGY
  status: ACCEPTED
  context:
    driver_refs: [REQ-DATA-001]
    constraint_refs: []
  options:
    - {id: OPT-POSTGRES, summary: "PostgreSQL"}
    - {id: OPT-SQLITE, summary: "SQLite"}
  decision:
    selected_option_ref: OPT-POSTGRES
    statement: "Использовать PostgreSQL"
    rationale: "Требуются concurrent users and server deployment"
  consequences:
    obligations: ["Определить migration/test database policy"]
  approved_by: ACT-ARCH-001
```

## 9. Work Package

```yaml
work_package:
  id: WP-SEARCH-001
  revision: 1
  request_refs: [RQ-20260806-0001]
  objective: "Пользователь ищет записи по названию"
  requirement_refs: [REQ-SEARCH-001]
  architecture_refs: [ADR-API-004]
  documentation_refs: [DOC-REQ-SEARCH@2]
  mandatory_task_refs:
    - TSK-CNT-SEARCH-010
    - TSK-BE-SEARCH-020
    - TSK-FE-SEARCH-030
    - TSK-INT-SEARCH-040
  dependency_graph_ref: DAG-WP-SEARCH-001@1
  aggregation_rule: ALL_MANDATORY_PASS
  status: READY
```

## 10. Task

```yaml
task:
  id: TSK-BE-SEARCH-020
  revision: 1
  work_package_ref: WP-SEARCH-001
  implementation_stage: PROTOTYPE
  title: "Реализовать backend search endpoint"
  type: IMPLEMENT
  track: BACKEND
  purpose: "Реализовать принятый search contract"
  expected_result: "Endpoint соответствует CNT-SEARCH@2"
  requirement_refs: [REQ-SEARCH-001]
  constraint_refs: []
  architecture_refs: [ADR-API-004]
  documentation:
    source_refs:
      - entity_ref: REQ-SEARCH-001
        document: docs/requirements/search.md
        section_id: search-by-name
        revision: 2
    impact: UPDATE_EXISTING
    required_updates:
      - document: docs/api/search.md
        section_id: endpoint-search
        reason: "Добавляется endpoint"
  depends_on_tasks: [TSK-CNT-SEARCH-010]
  requires_artifacts:
    - ref: CNT-SEARCH@2
      producer_task_ref: TSK-CNT-SEARCH-010
      required_status: ACCEPTED
      access: READ
  scope:
    read: [contracts/search/**]
    write: [src/backend/search/**, tests/search/backend/**]
    forbidden: [src/frontend/**]
  route:
    primary_skill_ref: SKL-UNIVERSAL-IMPLEMENT@3
    supporting_skill_refs: []
    required_capabilities: [FILESYSTEM_WRITE, COMMAND_EXECUTE]
  prompt_spec_ref: PSP-IMPLEMENT@1
  context_policy_ref: CTP-TASK-STANDARD@1
  verification_profile_ref: VFP-CODE-TARGETED-001@1
  acceptance_criteria: [AC-SEARCH-BE-001]
  rollback: {strategy: REVERT_WORKTREE}
  status: READY
```

## 11. Skill

```yaml
skill:
  id: SKL-UNIVERSAL-IMPLEMENT
  revision: 3
  namespace: harness
  level: UNIVERSAL
  status: ACTIVE
  purpose: "Bounded code implementation"
  applies_to_task_types: [IMPLEMENT]
  required_capabilities: [FILESYSTEM_READ, FILESYSTEM_WRITE, COMMAND_EXECUTE]
  prohibited_operations: [GIT_PUSH, DEPLOY]
  output_contract_ref: SCHEMA-AGENT-TASK-RESULT@1
  verification_profile_ref: VFP-CODE-TARGETED-001@1
  evaluation_suite_ref: EVS-SKL-IMPLEMENT@3
```

## 12. Prompt Plan and Bundle

```yaml
prompt_plan:
  id: PPL-TSK-BE-SEARCH-020-R1
  task_ref: TSK-BE-SEARCH-020@1
  prompt_spec_ref: PSP-IMPLEMENT@1
  module_refs: [PMD-CORE-ROLE@3, PMD-TASK-CONTRACT@2, PMD-RESULT-SCHEMA@1]
  resolved_inputs:
    task_hash: sha256:...
    constraints_hash: sha256:...
    skill_hash: sha256:...
    context_plan_hash: sha256:...
  output_schema_ref: SCHEMA-AGENT-TASK-RESULT@1
  status: RESOLVED
```

```yaml
compiled_prompt_bundle:
  id: CPB-RUN-20260806-0012
  prompt_plan_ref: PPL-TSK-BE-SEARCH-020-R1
  task_ref: TSK-BE-SEARCH-020@1
  run_ref: RUN-20260806-0012
  adapter_profile_ref: ADP-CODEX@1
  context_packet_refs: [CPK-TSK-BE-SEARCH-020-R1]
  capability_grant_refs: [CGR-RUN-0012]
  compilation_hash: sha256:...
  status: COMPILED
```

## 13. Run Plan and Run

```yaml
run_plan:
  id: RNP-RUN-20260806-0012
  task_ref: TSK-BE-SEARCH-020@1
  request_ref: RQ-20260806-0001
  work_package_ref: WP-SEARCH-001@1
  base_revisions:
    project: sha256:...
    repository: sha256:...
  prompt_bundle_ref: CPB-RUN-20260806-0012
  adapter_ref: ADP-CODEX@1
  capability_grant_refs: [CGR-RUN-0012]
  verification_profile_ref: VFP-CODE-TARGETED-001@1
  idempotency_key: sha256:...
  status: READY
```

```yaml
run:
  id: RUN-20260806-0012
  task_ref: TSK-BE-SEARCH-020@1
  attempt_no: 1
  previous_run_ref: null
  run_plan_ref: RNP-RUN-20260806-0012
  status: RUNNING
  tool_invocation_refs: []
  evidence_refs: []
  compensation_status: NOT_REQUIRED
```

## 14. Blocker

```yaml
blocker:
  id: BLK-SEARCH-001
  request_ref: RQ-20260806-0001
  work_package_ref: WP-SEARCH-001
  task_ref: TSK-BE-SEARCH-020@1
  run_ref: null
  class: BLOCKED_ARTIFACT
  status: OPEN
  stopped_at: TASK_READINESS
  reason: "CNT-SEARCH not accepted"
  evidence_refs: []
  independent_ready_task_refs: []
  options:
    - id: OPT-ACCEPT-CONTRACT
      action: CREATE_OR_ACCEPT_ARTIFACT
      route: RTE-DECIDE-SEARCH-CONTRACT
    - id: OPT-DEFER
      action: DEFER_TASK
      route: RTE-DEFER-SEARCH
  recommendation: {option_ref: OPT-ACCEPT-CONTRACT}
  resume_condition:
    expression: "CNT-SEARCH.status == ACCEPTED"
```

## 15. Change Pack

```yaml
change_pack:
  id: CHP-20260806-001
  request_ref: RQ-20260806-0020
  kind: PROJECT_CONTROL_MAINTENANCE
  target_plane: PROJECT_CONTROL
  target_project_ref: project-example
  objective: "Добавить reproduction gate для bug-fix routes"
  affected_entities: [SKL-PROJECT-BUG-FIX@2]
  normalized_changes: []
  impact_analysis_ref: IMP-CHP-001
  migration_plan_ref: MIG-CHP-001
  rollback_plan_ref: RBP-CHP-001
  required_capabilities: [PROJECT_CONTROL_WRITE]
  status: PROPOSED
```


## 11. Session

Canonical fields:

```text
id: SES-...
revision: integer
mode: GREENFIELD | BROWNFIELD | HYBRID
status: lifecycle session
created_at / updated_at
source_inventory_ref
questionnaire_session_ref
provisional_workspace
```

До handoff Session хранится во внешнем provisional workspace. После handoff его accepted revisions переносятся в `.harness/sessions/{id}@{revision}.yaml`.

## 12. Architecture Baseline

Canonical fields:

```text
id: ARB-...
revision
status
project_definition_ref
style
components
interfaces
data_flow
accepted_by
constraints
quality_attributes
decision_refs
risks
```

Architecture Baseline не заменяется Technology Baseline и имеет отдельный lifecycle.

## 13. Project Lock

Canonical fields:

```text
harness_distribution
schema_version
registry_versions
registry_digests
profile_refs
adapter_refs
skill_refs
prompt_spec_refs
migrations_applied
```

Registry keys обязаны точно совпадать с canonical filenames без `.yaml`.

## 14. Skill Registry Index

`.harness/skills/registry.yaml` является generated index. Он воспроизводится из resolved skill refs и digests в Project Lock. Его ручное редактирование не меняет active skill resolution и обнаруживается validation.

## 16. PROJECT_INPUT@3 contract note

Machine input uses `SCHEMA-PROJECT-PREPARATION-INPUT@3` and `schema_version: 3`. Strict object closure from v0.4.1 remains. New required `implementation` section contains canonical `target_level` and mode-constrained `claimed_current_level`; runtime Stage values are forbidden as user facts.
