# Нормализованные требования Project Harness

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

Эта матрица описывает требования к самому Harness. Она не является requirements registry создаваемого project instance.

**Активных требований:** 226. Namespace намеренно разрежен: пропущенные номера зарезервированы для расширения тематических групп и не означают отсутствующее покрытие.

## 1. Product positioning and scope

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-001 | Harness является project-agnostic engine для software и software-infrastructure проектов. | [`00_Overview/01_Product_Vision.md`](00_Overview/01_Product_Vision.md) |
| HNS-REQ-002 | Universal kernel не содержит domain/path/stack конкретного project instance. | [`00_Overview/03_Project_Agnostic_Foundation.md`](00_Overview/03_Project_Agnostic_Foundation.md) |
| HNS-REQ-003 | Project profile предоставляет defaults, но не скрытые hard constraints. | [`00_Overview/05_Project_Lifecycle_and_Profiles.md`](00_Overview/05_Project_Lifecycle_and_Profiles.md) |
| HNS-REQ-004 | `CUSTOM` profile поддерживается без изменения universal kernel. | [`11_Appendices/02_Project_Profile_Matrix.md`](11_Appendices/02_Project_Profile_Matrix.md) |
| HNS-REQ-005 | Greenfield creation является обязательным end-to-end workflow. | [`02_Intake/02_Greenfield_and_Brownfield_Workflows.md`](02_Intake/02_Greenfield_and_Brownfield_Workflows.md) |
| HNS-REQ-006 | Brownfield workflow сохраняет reconciliation между docs и code. | [`02_Intake/02_Greenfield_and_Brownfield_Workflows.md`](02_Intake/02_Greenfield_and_Brownfield_Workflows.md) |
| HNS-REQ-007 | Material decisions остаются human-governed. | [`00_Overview/02_Scope_Principles_and_Non_Goals.md`](00_Overview/02_Scope_Principles_and_Non_Goals.md) |
| HNS-REQ-008 | Completeness измеряется независимыми dimensions, а не переносом одного source project. | [`11_Appendices/03_Independent_Completeness_Model.md`](11_Appendices/03_Independent_Completeness_Model.md) |
| HNS-REQ-009 | Product scope и non-goals зафиксированы явно. | [`00_Overview/02_Scope_Principles_and_Non_Goals.md`](00_Overview/02_Scope_Principles_and_Non_Goals.md) |

## 2. Intent, intake and Project Definition

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-010 | Harness принимает краткий Project Intent без готовой документации или repository. | [`02_Intake/01_Project_Intake_and_Readiness_Gates.md`](02_Intake/01_Project_Intake_and_Readiness_Gates.md) |
| HNS-REQ-011 | Все supplied sources инвентаризируются, хешируются и классифицируются. | [`02_Intake/01_Project_Intake_and_Readiness_Gates.md`](02_Intake/01_Project_Intake_and_Readiness_Gates.md) |
| HNS-REQ-012 | Отсутствие полной документации запускает discovery, а не обязательный blocker. | [`02_Intake/01_Project_Intake_and_Readiness_Gates.md`](02_Intake/01_Project_Intake_and_Readiness_Gates.md) |
| HNS-REQ-013 | Project Definition предшествует architecture and implementation. | [`02_Intake/04_Project_Definition_and_Discovery.md`](02_Intake/04_Project_Definition_and_Discovery.md) |
| HNS-REQ-014 | Project Definition содержит problem, users, outcomes, goals и success criteria. | [`02_Intake/04_Project_Definition_and_Discovery.md`](02_Intake/04_Project_Definition_and_Discovery.md) |
| HNS-REQ-015 | Scope разделён на in, out и deferred. | [`02_Intake/04_Project_Definition_and_Discovery.md`](02_Intake/04_Project_Definition_and_Discovery.md) |
| HNS-REQ-016 | Confirmed, assumed, proposed, unknown и conflicting различаются машинно. | [`00_Overview/04_Terminology_and_Roles.md`](00_Overview/04_Terminology_and_Roles.md) |
| HNS-REQ-017 | Assumption имеет owner, impact, validation plan и expiry/gate. | [`02_Intake/04_Project_Definition_and_Discovery.md`](02_Intake/04_Project_Definition_and_Discovery.md) |
| HNS-REQ-018 | Unknown имеет materiality, owner и resolution route. | [`02_Intake/04_Project_Definition_and_Discovery.md`](02_Intake/04_Project_Definition_and_Discovery.md) |
| HNS-REQ-019 | Project Definition проходит formal user gate. | [`00_Overview/05_Project_Lifecycle_and_Profiles.md`](00_Overview/05_Project_Lifecycle_and_Profiles.md) |

## 3. Requirements, constraints and decisions

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-020 | Requirement, Constraint, Invariant, Policy, Preference, Assumption, Decision и Waiver являются разными сущностями. | [`01_Architecture/05_Constraints_Policies_and_Decisions.md`](01_Architecture/05_Constraints_Policies_and_Decisions.md) |
| HNS-REQ-021 | Constraint имеет stable ID, source, scope, strength, precedence, enforcement и evidence refs. | [`01_Architecture/05_Constraints_Policies_and_Decisions.md`](01_Architecture/05_Constraints_Policies_and_Decisions.md) |
| HNS-REQ-022 | Constraints наследуются по workspace/project/environment/repository/track/task/run scope. | [`01_Architecture/05_Constraints_Policies_and_Decisions.md`](01_Architecture/05_Constraints_Policies_and_Decisions.md) |
| HNS-REQ-023 | Локальное правило не ослабляет ancestor hard constraint без waiver. | [`01_Architecture/05_Constraints_Policies_and_Decisions.md`](01_Architecture/05_Constraints_Policies_and_Decisions.md) |
| HNS-REQ-024 | Два несовместимых hard rules создают conflict/blocker, а не silent choice. | [`10_Contracts/02_Source_Precedence_and_Conflict_Resolution.md`](10_Contracts/02_Source_Precedence_and_Conflict_Resolution.md) |
| HNS-REQ-025 | Waiver ограничен authority, scope, reason и expiry. | [`01_Architecture/05_Constraints_Policies_and_Decisions.md`](01_Architecture/05_Constraints_Policies_and_Decisions.md) |
| HNS-REQ-026 | Constraints применяются на intake, architecture, planning, compile, route, runtime и release phases. | [`01_Architecture/05_Constraints_Policies_and_Decisions.md`](01_Architecture/05_Constraints_Policies_and_Decisions.md) |
| HNS-REQ-027 | User message не supersede ADR/security policy без decision route. | [`10_Contracts/02_Source_Precedence_and_Conflict_Resolution.md`](10_Contracts/02_Source_Precedence_and_Conflict_Resolution.md) |
| HNS-REQ-028 | Requirement связан с goals, constraints, architecture, tasks, checks и evidence. | [`03_Planning/01_Requirements_Traceability.md`](03_Planning/01_Requirements_Traceability.md) |
| HNS-REQ-029 | Constraint coverage проверяется отдельно от requirement coverage. | [`03_Planning/01_Requirements_Traceability.md`](03_Planning/01_Requirements_Traceability.md) |

## 4. Architecture and bootstrap

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-030 | Architecture proposer запускается после Project Definition readiness. | [`02_Intake/03_Architecture_Proposal_and_Approval.md`](02_Intake/03_Architecture_Proposal_and_Approval.md) |
| HNS-REQ-031 | Material architecture choice имеет alternatives или rationale отсутствия альтернативы. | [`02_Intake/03_Architecture_Proposal_and_Approval.md`](02_Intake/03_Architecture_Proposal_and_Approval.md) |
| HNS-REQ-032 | Architecture option показывает goal/requirement/constraint coverage, risks и reversibility. | [`02_Intake/03_Architecture_Proposal_and_Approval.md`](02_Intake/03_Architecture_Proposal_and_Approval.md) |
| HNS-REQ-033 | Inference-generated architecture остаётся candidate до gate. | [`01_Architecture/01_System_Architecture.md`](01_Architecture/01_System_Architecture.md) |
| HNS-REQ-034 | Accepted architecture фиксируется baseline и ADR/Decision. | [`02_Intake/03_Architecture_Proposal_and_Approval.md`](02_Intake/03_Architecture_Proposal_and_Approval.md) |
| HNS-REQ-035 | Material architecture update не переписывает старые decisions. | [`05_Updates/02_Impact_and_Replanning.md`](05_Updates/02_Impact_and_Replanning.md) |
| HNS-REQ-036 | Greenfield project имеет отдельный Bootstrap Plan. | [`08_Distribution/04_Project_Bootstrap.md`](08_Distribution/04_Project_Bootstrap.md) |
| HNS-REQ-037 | Bootstrap поддерживает dry-run, capabilities, checks и cleanup/rollback. | [`08_Distribution/04_Project_Bootstrap.md`](08_Distribution/04_Project_Bootstrap.md) |
| HNS-REQ-038 | Repository creation не выполняется до approved bootstrap capability. | [`06_Git/01_Git_Architecture.md`](06_Git/01_Git_Architecture.md) |
| HNS-REQ-039 | Brownfield bootstrap не перегенерирует existing project молча. | [`08_Distribution/04_Project_Bootstrap.md`](08_Distribution/04_Project_Bootstrap.md) |

## 5. Canonical model and compiled artifacts

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-040 | Harness хранит one canonical project model. | [`01_Architecture/02_Canonical_Model_and_Generated_Artifacts.md`](01_Architecture/02_Canonical_Model_and_Generated_Artifacts.md) |
| HNS-REQ-041 | Canonical, generated и immutable-history artifacts различаются. | [`01_Architecture/02_Canonical_Model_and_Generated_Artifacts.md`](01_Architecture/02_Canonical_Model_and_Generated_Artifacts.md) |
| HNS-REQ-042 | Generated artifacts имеют compiler/source revisions и hashes. | [`01_Architecture/02_Canonical_Model_and_Generated_Artifacts.md`](01_Architecture/02_Canonical_Model_and_Generated_Artifacts.md) |
| HNS-REQ-043 | Generated artifacts не редактируются как canonical source. | [`01_Architecture/02_Canonical_Model_and_Generated_Artifacts.md`](01_Architecture/02_Canonical_Model_and_Generated_Artifacts.md) |
| HNS-REQ-044 | Stable IDs не зависят от filenames или line numbers. | [`01_Architecture/02_Canonical_Model_and_Generated_Artifacts.md`](01_Architecture/02_Canonical_Model_and_Generated_Artifacts.md) |
| HNS-REQ-045 | Prompt представлен цепочкой Module → Spec → Plan → Bundle → Run. | [`01_Architecture/06_Prompt_IR_and_Compilation.md`](01_Architecture/06_Prompt_IR_and_Compilation.md) |
| HNS-REQ-046 | Instruction layers имеют формальный precedence. | [`01_Architecture/06_Prompt_IR_and_Compilation.md`](01_Architecture/06_Prompt_IR_and_Compilation.md) |
| HNS-REQ-047 | Untrusted content не попадает в trusted instruction layer. | [`07_Security/01_Security_Trust_and_Supply_Chain.md`](07_Security/01_Security_Trust_and_Supply_Chain.md) |
| HNS-REQ-048 | Prompt compilation детерминирована для одинаковых canonical inputs. | [`01_Architecture/06_Prompt_IR_and_Compilation.md`](01_Architecture/06_Prompt_IR_and_Compilation.md) |
| HNS-REQ-049 | Prompt Bundle имеет source map, output schema и hash. | [`10_Contracts/03_Extended_Contracts_Examples.md`](10_Contracts/03_Extended_Contracts_Examples.md) |
| HNS-REQ-050 | Unresolved variable/hard conflict/stale source блокируют compile. | [`01_Architecture/06_Prompt_IR_and_Compilation.md`](01_Architecture/06_Prompt_IR_and_Compilation.md) |
| HNS-REQ-051 | Prompt artifacts имеют lifecycle, canary и rollback. | [`04_Execution/06_Prompt_Evaluation_and_Release.md`](04_Execution/06_Prompt_Evaluation_and_Release.md) |
| HNS-REQ-052 | Deterministic kernel отделён от inference workers. | [`01_Architecture/01_System_Architecture.md`](01_Architecture/01_System_Architecture.md) |

## 6. Context, adapters and compatibility

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-060 | Agent, model и tool adapters/profiles разделены. | [`01_Architecture/03_Agent_Model_Tool_Adapters_and_Context_Recovery.md`](01_Architecture/03_Agent_Model_Tool_Adapters_and_Context_Recovery.md) |
| HNS-REQ-061 | Новый агент восстанавливает context без истории чата. | [`01_Architecture/03_Agent_Model_Tool_Adapters_and_Context_Recovery.md`](01_Architecture/03_Agent_Model_Tool_Adapters_and_Context_Recovery.md) |
| HNS-REQ-062 | Context Packet содержит previous/current/next и exact plan refs. | [`03_Planning/05_Context_Packets.md`](03_Planning/05_Context_Packets.md) |
| HNS-REQ-063 | Context Policy задаёт required classes, ranking, redaction и overflow. | [`03_Planning/06_Context_Planning_and_Overflow.md`](03_Planning/06_Context_Planning_and_Overflow.md) |
| HNS-REQ-064 | Context Plan показывает included/excluded sources и reasons. | [`03_Planning/06_Context_Planning_and_Overflow.md`](03_Planning/06_Context_Planning_and_Overflow.md) |
| HNS-REQ-065 | Mandatory constraints/acceptance/output contract нельзя silent truncate. | [`03_Planning/06_Context_Planning_and_Overflow.md`](03_Planning/06_Context_Planning_and_Overflow.md) |
| HNS-REQ-066 | Context conflict и source provenance сохраняются. | [`03_Planning/06_Context_Planning_and_Overflow.md`](03_Planning/06_Context_Planning_and_Overflow.md) |
| HNS-REQ-067 | Compatibility Plan проверяет capabilities, data policy, context, output и permissions. | [`01_Architecture/07_Execution_Compatibility.md`](01_Architecture/07_Execution_Compatibility.md) |
| HNS-REQ-068 | Fallback не расширяет data boundary или permissions. | [`01_Architecture/07_Execution_Compatibility.md`](01_Architecture/07_Execution_Compatibility.md) |
| HNS-REQ-069 | Отсутствие compatible executor создаёт blocker/options, а не silent degradation. | [`01_Architecture/07_Execution_Compatibility.md`](01_Architecture/07_Execution_Compatibility.md) |

## 7. Planning, routing and tasks

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-070 | Существует единая entry point и request decomposition. | [`03_Planning/04_Routing_and_Skills.md`](03_Planning/04_Routing_and_Skills.md) |
| HNS-REQ-071 | Каждый atomic route имеет один primary intent. | [`03_Planning/04_Routing_and_Skills.md`](03_Planning/04_Routing_and_Skills.md) |
| HNS-REQ-072 | Routing Decision показывается до side effects. | [`03_Planning/04_Routing_and_Skills.md`](03_Planning/04_Routing_and_Skills.md) |
| HNS-REQ-073 | Skill имеет inputs, outputs, capabilities, side effects, failures и eval fixtures. | [`03_Planning/04_Routing_and_Skills.md`](03_Planning/04_Routing_and_Skills.md) |
| HNS-REQ-074 | Roadmap является DAG и поддерживает decision/bootstrap/integration tasks. | [`03_Planning/02_Roadmap_DAG_Tracks_and_Parallelism.md`](03_Planning/02_Roadmap_DAG_Tracks_and_Parallelism.md) |
| HNS-REQ-075 | READY вычисляется с учётом constraints, plans, compatibility и ownership. | [`03_Planning/02_Roadmap_DAG_Tracks_and_Parallelism.md`](03_Planning/02_Roadmap_DAG_Tracks_and_Parallelism.md) |
| HNS-REQ-076 | При нескольких READY tasks применяется versioned deterministic tie-breaker. | [`03_Planning/02_Roadmap_DAG_Tracks_and_Parallelism.md`](03_Planning/02_Roadmap_DAG_Tracks_and_Parallelism.md) |
| HNS-REQ-077 | Task имеет один проверяемый expected result и explicit out-of-scope. | [`03_Planning/03_Task_Contract.md`](03_Planning/03_Task_Contract.md) |
| HNS-REQ-078 | Task Contract содержит constraints, prompt/context refs, capabilities, idempotency и rollback. | [`03_Planning/03_Task_Contract.md`](03_Planning/03_Task_Contract.md) |
| HNS-REQ-079 | Verification phases различают now/merge/release/optional. | [`03_Planning/03_Task_Contract.md`](03_Planning/03_Task_Contract.md) |

## 8. Permissions, execution and reliability

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-080 | Runtime permissions используют deny-by-default capability grants. | [`07_Security/02_Data_Classification_and_Runtime_Permissions.md`](07_Security/02_Data_Classification_and_Runtime_Permissions.md) |
| HNS-REQ-081 | Capability availability не означает permission. | [`07_Security/02_Data_Classification_and_Runtime_Permissions.md`](07_Security/02_Data_Classification_and_Runtime_Permissions.md) |
| HNS-REQ-082 | Grant ограничен task/run/resource scope, authority и expiry. | [`07_Security/02_Data_Classification_and_Runtime_Permissions.md`](07_Security/02_Data_Classification_and_Runtime_Permissions.md) |
| HNS-REQ-083 | Tool invocation проверяет grant технически до action. | [`07_Security/02_Data_Classification_and_Runtime_Permissions.md`](07_Security/02_Data_Classification_and_Runtime_Permissions.md) |
| HNS-REQ-084 | Task и Run имеют отдельные lifecycles. | [`04_Execution/01_State_Machine.md`](04_Execution/01_State_Machine.md) |
| HNS-REQ-085 | Run фиксирует exact Prompt/Context/Compatibility/revision hashes. | [`04_Execution/05_Run_Trace_Retry_and_Idempotency.md`](04_Execution/05_Run_Trace_Retry_and_Idempotency.md) |
| HNS-REQ-086 | Tool calls имеют side-effect and idempotency classification. | [`04_Execution/05_Run_Trace_Retry_and_Idempotency.md`](04_Execution/05_Run_Trace_Retry_and_Idempotency.md) |
| HNS-REQ-087 | Automatic retry разрешён только при safe retry conditions. | [`04_Execution/05_Run_Trace_Retry_and_Idempotency.md`](04_Execution/05_Run_Trace_Retry_and_Idempotency.md) |
| HNS-REQ-088 | Unknown idempotency трактуется как non-idempotent для automatic retry. | [`04_Execution/05_Run_Trace_Retry_and_Idempotency.md`](04_Execution/05_Run_Trace_Retry_and_Idempotency.md) |
| HNS-REQ-089 | Timeout не считается доказательством отсутствия external side effect. | [`04_Execution/05_Run_Trace_Retry_and_Idempotency.md`](04_Execution/05_Run_Trace_Retry_and_Idempotency.md) |
| HNS-REQ-090 | Cancellation использует safe points и сохраняет partial trace. | [`04_Execution/04_Blockers_Recovery.md`](04_Execution/04_Blockers_Recovery.md) |
| HNS-REQ-091 | External partial side effects имеют compensation/reconciliation path. | [`04_Execution/05_Run_Trace_Retry_and_Idempotency.md`](04_Execution/05_Run_Trace_Retry_and_Idempotency.md) |
| HNS-REQ-092 | Task Report, Run Trace, Evidence и State обновляются согласованно. | [`04_Execution/03_Reports_Evidence_and_Validation.md`](04_Execution/03_Reports_Evidence_and_Validation.md) |
| HNS-REQ-093 | Blocker содержит options, recommendation и resume condition. | [`04_Execution/04_Blockers_Recovery.md`](04_Execution/04_Blockers_Recovery.md) |
| HNS-REQ-094 | Task `DONE` требует PASS всех `REQUIRED_NOW`; merge/release checks представлены отдельными gates/tasks. | [`04_Execution/01_State_Machine.md`](04_Execution/01_State_Machine.md) |
| HNS-REQ-095 | Concurrent state writes используют lease/CAS/revision check. | [`04_Execution/01_State_Machine.md`](04_Execution/01_State_Machine.md) |

## 9. Validation and evaluations

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-100 | Structural validator проверяет schemas, refs, DAG, state, coverage and freshness. | [`04_Execution/03_Reports_Evidence_and_Validation.md`](04_Execution/03_Reports_Evidence_and_Validation.md) |
| HNS-REQ-101 | LLM self-review не является единственным validator. | [`04_Execution/03_Reports_Evidence_and_Validation.md`](04_Execution/03_Reports_Evidence_and_Validation.md) |
| HNS-REQ-102 | Compiler, constraint, routing, context, behavior, adversarial и recovery evals разделены. | [`04_Execution/06_Prompt_Evaluation_and_Release.md`](04_Execution/06_Prompt_Evaluation_and_Release.md) |
| HNS-REQ-103 | Deterministic assertions имеют приоритет для security/state properties. | [`04_Execution/06_Prompt_Evaluation_and_Release.md`](04_Execution/06_Prompt_Evaluation_and_Release.md) |
| HNS-REQ-104 | Cross-profile fixtures обнаруживают project leakage. | [`04_Execution/06_Prompt_Evaluation_and_Release.md`](04_Execution/06_Prompt_Evaluation_and_Release.md) |
| HNS-REQ-105 | Prompt release требует regression/adversarial gate. | [`04_Execution/06_Prompt_Evaluation_and_Release.md`](04_Execution/06_Prompt_Evaluation_and_Release.md) |
| HNS-REQ-106 | Evidence имеет producer, revision, result, hash и applicable refs. | [`04_Execution/03_Reports_Evidence_and_Validation.md`](04_Execution/03_Reports_Evidence_and_Validation.md) |

## 10. Updates and migrations

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-110 | Любое входящее изменение нормализуется в Change Pack. | [`05_Updates/01_Change_Pack_Protocol.md`](05_Updates/01_Change_Pack_Protocol.md) |
| HNS-REQ-111 | Incoming content проходит quarantine и не применяется напрямую. | [`05_Updates/01_Change_Pack_Protocol.md`](05_Updates/01_Change_Pack_Protocol.md) |
| HNS-REQ-112 | Impact включает goals/scope/constraints/prompts/context/capabilities/evals. | [`05_Updates/02_Impact_and_Replanning.md`](05_Updates/02_Impact_and_Replanning.md) |
| HNS-REQ-113 | Completed history и старые run artifacts не переписываются. | [`05_Updates/02_Impact_and_Replanning.md`](05_Updates/02_Impact_and_Replanning.md) |
| HNS-REQ-114 | Active stale task останавливается и пересобирает plans. | [`05_Updates/02_Impact_and_Replanning.md`](05_Updates/02_Impact_and_Replanning.md) |
| HNS-REQ-115 | Update применяется transactionally в пределах local boundary. | [`05_Updates/03_Transactional_Application.md`](05_Updates/03_Transactional_Application.md) |
| HNS-REQ-116 | External side effects updates используют staged saga/compensation. | [`05_Updates/03_Transactional_Application.md`](05_Updates/03_Transactional_Application.md) |
| HNS-REQ-117 | Engine/schema/profile/prompt/adapters versioned independently. | [`05_Updates/04_Versioning_Migrations.md`](05_Updates/04_Versioning_Migrations.md) |
| HNS-REQ-118 | Migration имеет precheck, dry-run, recovery и immutable-history preservation. | [`05_Updates/04_Versioning_Migrations.md`](05_Updates/04_Versioning_Migrations.md) |

## 11. Git, security and distribution

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-120 | Harness обнаруживает existing Git до запроса URL. | [`06_Git/01_Git_Architecture.md`](06_Git/01_Git_Architecture.md) |
| HNS-REQ-121 | Dirty state не reset/clean автоматически. | [`06_Git/01_Git_Architecture.md`](06_Git/01_Git_Architecture.md) |
| HNS-REQ-122 | Writing task использует worktree/ownership lease. | [`06_Git/02_Worktrees_Ownership.md`](06_Git/02_Worktrees_Ownership.md) |
| HNS-REQ-123 | File, contract, exclusive-resource и side-effect overlap проверяются. | [`06_Git/02_Worktrees_Ownership.md`](06_Git/02_Worktrees_Ownership.md) |
| HNS-REQ-124 | Commit, push и PR являются отдельными capabilities. | [`06_Git/03_Commit_Publish_Policy.md`](06_Git/03_Commit_Publish_Policy.md) |
| HNS-REQ-125 | Polyrepo использует coordinated change sets. | [`06_Git/03_Commit_Publish_Policy.md`](06_Git/03_Commit_Publish_Policy.md) |
| HNS-REQ-126 | Archives проходят traversal/link/bomb/binary/integrity checks. | [`07_Security/01_Security_Trust_and_Supply_Chain.md`](07_Security/01_Security_Trust_and_Supply_Chain.md) |
| HNS-REQ-127 | Prompt injection не меняет instructions/authority/capabilities. | [`07_Security/01_Security_Trust_and_Supply_Chain.md`](07_Security/01_Security_Trust_and_Supply_Chain.md) |
| HNS-REQ-128 | Secrets не входят в canonical/generated/report/run artifacts. | [`07_Security/01_Security_Trust_and_Supply_Chain.md`](07_Security/01_Security_Trust_and_Supply_Chain.md) |
| HNS-REQ-129 | Data classes управляют storage, egress, redaction и allowed profiles. | [`07_Security/02_Data_Classification_and_Runtime_Permissions.md`](07_Security/02_Data_Classification_and_Runtime_Permissions.md) |
| HNS-REQ-130 | Distribution имеет version, manifest, checksums and validation. | [`08_Distribution/01_Universal_Archive_Structure.md`](08_Distribution/01_Universal_Archive_Structure.md) |
| HNS-REQ-131 | Project instance имеет versioned `.harness/` structure. | [`08_Distribution/02_Project_Local_Structure.md`](08_Distribution/02_Project_Local_Structure.md) |
| HNS-REQ-132 | Workspace-only mode поддерживается до repository bootstrap. | [`01_Architecture/04_Deployment_Models.md`](01_Architecture/04_Deployment_Models.md) |
| HNS-REQ-133 | Offline/vendored mode не требует central server. | [`01_Architecture/04_Deployment_Models.md`](01_Architecture/04_Deployment_Models.md) |

## 12. Explicit exclusions

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-140 | Harness не обрабатывает provider billing и оплаты model calls. | [`00_Overview/02_Scope_Principles_and_Non_Goals.md`](00_Overview/02_Scope_Principles_and_Non_Goals.md) |
| HNS-REQ-141 | Harness не рассчитывает стоимость model calls. | [`00_Overview/02_Scope_Principles_and_Non_Goals.md`](00_Overview/02_Scope_Principles_and_Non_Goals.md) |
| HNS-REQ-142 | Harness не учитывает и не квотирует расход токенов. | [`00_Overview/02_Scope_Principles_and_Non_Goals.md`](00_Overview/02_Scope_Principles_and_Non_Goals.md) |
| HNS-REQ-143 | Routing не использует price/token-cost criteria. | [`01_Architecture/07_Execution_Compatibility.md`](01_Architecture/07_Execution_Compatibility.md) |
| HNS-REQ-144 | Context capacity preflight не превращается в usage accounting. | [`03_Planning/06_Context_Planning_and_Overflow.md`](03_Planning/06_Context_Planning_and_Overflow.md) |
| HNS-REQ-145 | Исключение provider accounting не ограничивает проекты, чья бизнес-предметная область включает платежи или финансовые операции. | [`00_Overview/02_Scope_Principles_and_Non_Goals.md`](00_Overview/02_Scope_Principles_and_Non_Goals.md) |

## 13. v0.3 end-to-end, onboarding and implementation requirements

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-146 | Любой пользовательский ввод сначала нормализуется в Request. | [`12_Implementation_Specifications/01_Single_Entry_Request_Contract.md`](12_Implementation_Specifications/01_Single_Entry_Request_Contract.md) |
| HNS-REQ-147 | Request Class, Request Mode и internal Operation являются разными полями. | [`12_Implementation_Specifications/01_Single_Entry_Request_Contract.md`](12_Implementation_Specifications/01_Single_Entry_Request_Contract.md) |
| HNS-REQ-148 | Обычный read-only QUERY не создаёт Work Package или Task. | [`12_Implementation_Specifications/01_Single_Entry_Request_Contract.md`](12_Implementation_Specifications/01_Single_Entry_Request_Contract.md) |
| HNS-REQ-149 | Каждый executable Request имеет versioned Request Plan. | [`12_Implementation_Specifications/01_Single_Entry_Request_Contract.md`](12_Implementation_Specifications/01_Single_Entry_Request_Contract.md) |
| HNS-REQ-150 | Пользователь не обязан знать внутренние команды compile/run/resume. | [`08_Distribution/03_User_Workflows.md`](08_Distribution/03_User_Workflows.md) |
| HNS-REQ-151 | Каждый route возвращает единый Result Envelope. | [`12_Implementation_Specifications/02_Result_Envelope_and_Statuses.md`](12_Implementation_Specifications/02_Result_Envelope_and_Statuses.md) |
| HNS-REQ-152 | Незавершённый Result сообщает причины, безопасно выполненную часть, варианты и resume condition. | [`12_Implementation_Specifications/02_Result_Envelope_and_Statuses.md`](12_Implementation_Specifications/02_Result_Envelope_and_Statuses.md) |
| HNS-REQ-153 | Завершённый Result сообщает added/changed/removed, verification, documentation impact и next route. | [`12_Implementation_Specifications/02_Result_Envelope_and_Statuses.md`](12_Implementation_Specifications/02_Result_Envelope_and_Statuses.md) |
| HNS-REQ-154 | Один пользовательский outcome группируется в Work Package. | [`12_Implementation_Specifications/03_Work_Packages_Tasks_and_Subtasks.md`](12_Implementation_Specifications/03_Work_Packages_Tasks_and_Subtasks.md) |
| HNS-REQ-155 | Исполняются только atomic Tasks с одним проверяемым результатом. | [`12_Implementation_Specifications/03_Work_Packages_Tasks_and_Subtasks.md`](12_Implementation_Specifications/03_Work_Packages_Tasks_and_Subtasks.md) |
| HNS-REQ-156 | Large request декомпозируется минимально достаточным числом tasks. | [`12_Implementation_Specifications/03_Work_Packages_Tasks_and_Subtasks.md`](12_Implementation_Specifications/03_Work_Packages_Tasks_and_Subtasks.md) |
| HNS-REQ-157 | Parent/grouping entity не исполняется как дополнительный prompt. | [`12_Implementation_Specifications/03_Work_Packages_Tasks_and_Subtasks.md`](12_Implementation_Specifications/03_Work_Packages_Tasks_and_Subtasks.md) |
| HNS-REQ-158 | Prompt Plan и Compiled Bundle создаются JIT только для READY Task или approved parallel batch. | [`12_Implementation_Specifications/04_JIT_Prompt_Compilation.md`](12_Implementation_Specifications/04_JIT_Prompt_Compilation.md) |
| HNS-REQ-159 | Неисполненные массово скомпилированные prompts не являются canonical backlog. | [`12_Implementation_Specifications/04_JIT_Prompt_Compilation.md`](12_Implementation_Specifications/04_JIT_Prompt_Compilation.md) |
| HNS-REQ-160 | Codex prompt явно содержит purpose, expected result, verification, stop conditions и next-step contract. | [`12_Implementation_Specifications/15_Codex_Agent_Adapter.md`](12_Implementation_Specifications/15_Codex_Agent_Adapter.md) |
| HNS-REQ-161 | Task ссылается на canonical entities и точные documentation paths/section IDs/revisions. | [`12_Implementation_Specifications/05_Documentation_Traceability.md`](12_Implementation_Specifications/05_Documentation_Traceability.md) |
| HNS-REQ-162 | Task объявляет documentation impact и подтверждает его в Task Report. | [`12_Implementation_Specifications/05_Documentation_Traceability.md`](12_Implementation_Specifications/05_Documentation_Traceability.md) |
| HNS-REQ-163 | ADR создаётся только для material long-lived decision. | [`12_Implementation_Specifications/06_ADR_and_Decision_Policy.md`](12_Implementation_Specifications/06_ADR_and_Decision_Policy.md) |
| HNS-REQ-164 | Обычная реализация, fix или docs update фиксируется Task/Run/Report/Event без отдельного ADR. | [`12_Implementation_Specifications/06_ADR_and_Decision_Policy.md`](12_Implementation_Specifications/06_ADR_and_Decision_Policy.md) |
| HNS-REQ-165 | Task dependency связывается с exact required artifact и producer task. | [`12_Implementation_Specifications/07_Causal_Development_Sequence.md`](12_Implementation_Specifications/07_Causal_Development_Sequence.md) |
| HNS-REQ-166 | Task не становится READY, пока required artifact не существует в accepted revision. | [`12_Implementation_Specifications/07_Causal_Development_Sequence.md`](12_Implementation_Specifications/07_Causal_Development_Sequence.md) |
| HNS-REQ-167 | Implementation roadmap начинается с раннего end-to-end walking skeleton. | [`09_Delivery/02_Implementation_Roadmap.md`](09_Delivery/02_Implementation_Roadmap.md) |
| HNS-REQ-168 | Parallel safety оценивает read/write sets для paths, contracts, docs, DB, lockfiles и environments. | [`12_Implementation_Specifications/08_Safe_Parallel_Execution.md`](12_Implementation_Specifications/08_Safe_Parallel_Execution.md) |
| HNS-REQ-169 | Два Tasks могут читать один frozen accepted contract параллельно. | [`12_Implementation_Specifications/08_Safe_Parallel_Execution.md`](12_Implementation_Specifications/08_Safe_Parallel_Execution.md) |
| HNS-REQ-170 | Parallel batch имеет frozen inputs, leases, conflict analysis и integration task. | [`12_Implementation_Specifications/08_Safe_Parallel_Execution.md`](12_Implementation_Specifications/08_Safe_Parallel_Execution.md) |
| HNS-REQ-171 | Material ambiguity останавливает только affected task до решения. | [`12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md`](12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md) |
| HNS-REQ-172 | Non-material ambiguity обрабатывается STRICT или PRAGMATIC policy без silent assumptions. | [`12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md`](12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md) |
| HNS-REQ-173 | Clarification задаётся bounded batch и содержит варианты, recommendation и unknown path. | [`12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md`](12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md) |
| HNS-REQ-174 | Blocker всегда содержит evidence, recovery options, recommendation и resume condition. | [`12_Implementation_Specifications/10_Blockers_Recovery_and_Progression.md`](12_Implementation_Specifications/10_Blockers_Recovery_and_Progression.md) |
| HNS-REQ-175 | В проекте всегда существует следующий route, хотя он может менять approach/scope/defer/cancel исходную задачу. | [`12_Implementation_Specifications/10_Blockers_Recovery_and_Progression.md`](12_Implementation_Specifications/10_Blockers_Recovery_and_Progression.md) |
| HNS-REQ-176 | Independent READY work показывается при локальной блокировке. | [`12_Implementation_Specifications/10_Blockers_Recovery_and_Progression.md`](12_Implementation_Specifications/10_Blockers_Recovery_and_Progression.md) |
| HNS-REQ-177 | Каждая Task имеет пропорциональный Verification Profile. | [`12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md`](12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md) |
| HNS-REQ-178 | Documentation/config/directory tasks не требуют бессмысленных code tests. | [`12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md`](12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md) |
| HNS-REQ-179 | Test DB использует pre-migrated template/snapshot и rebuild только по определённым причинам. | [`12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md`](12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md) |
| HNS-REQ-180 | Parallel test runs используют isolated clone/schema/environment или exclusive lease. | [`12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md`](12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md) |
| HNS-REQ-181 | Known baseline failures отделяются от regressions текущей Task. | [`12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md`](12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md) |
| HNS-REQ-182 | Stale test обновляется/удаляется только со ссылкой на changed requirement/decision. | [`12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md`](12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md) |
| HNS-REQ-183 | Request Trace связывает input, classification, plan, work package, task, prompt, run, evidence, result и state. | [`12_Implementation_Specifications/12_Request_Trace_and_Logging.md`](12_Implementation_Specifications/12_Request_Trace_and_Logging.md) |
| HNS-REQ-184 | Все material state transitions и tool invocations имеют correlation IDs и structured events. | [`12_Implementation_Specifications/12_Request_Trace_and_Logging.md`](12_Implementation_Specifications/12_Request_Trace_and_Logging.md) |
| HNS-REQ-185 | Logs не содержат secrets, private chain-of-thought или неограниченные sensitive payloads. | [`12_Implementation_Specifications/12_Request_Trace_and_Logging.md`](12_Implementation_Specifications/12_Request_Trace_and_Logging.md) |
| HNS-REQ-186 | Architecture Gate включает versioned Technology Baseline. | [`12_Implementation_Specifications/13_Technology_Baseline.md`](12_Implementation_Specifications/13_Technology_Baseline.md) |
| HNS-REQ-187 | Technology selection учитывает requirements, compatibility, lifecycle/EOL, licensing, security, operations и team capability. | [`12_Implementation_Specifications/13_Technology_Baseline.md`](12_Implementation_Specifications/13_Technology_Baseline.md) |
| HNS-REQ-188 | Skill Registry определяет owner, version, applicability, permissions, evaluation и lifecycle. | [`12_Implementation_Specifications/14_Skill_Registry_and_Lifecycle.md`](12_Implementation_Specifications/14_Skill_Registry_and_Lifecycle.md) |
| HNS-REQ-189 | Skill choice следует порядку REUSE → CONFIGURE → EXTEND → CREATE. | [`12_Implementation_Specifications/14_Skill_Registry_and_Lifecycle.md`](12_Implementation_Specifications/14_Skill_Registry_and_Lifecycle.md) |
| HNS-REQ-190 | Task имеет один primary skill и только необходимые supporting skills. | [`12_Implementation_Specifications/14_Skill_Registry_and_Lifecycle.md`](12_Implementation_Specifications/14_Skill_Registry_and_Lifecycle.md) |
| HNS-REQ-191 | Codex является executor adapter и не принимает governance/scope/permission/next-task decisions. | [`12_Implementation_Specifications/15_Codex_Agent_Adapter.md`](12_Implementation_Specifications/15_Codex_Agent_Adapter.md) |
| HNS-REQ-192 | Codex возвращает structured Agent Task Result, который валидируется kernel. | [`12_Implementation_Specifications/15_Codex_Agent_Adapter.md`](12_Implementation_Specifications/15_Codex_Agent_Adapter.md) |
| HNS-REQ-193 | Change Pack имеет один target plane: PRODUCT, PROJECT_CONTROL или HARNESS_DISTRIBUTION. | [`12_Implementation_Specifications/16_Harness_Maintenance_Plane.md`](12_Implementation_Specifications/16_Harness_Maintenance_Plane.md) |
| HNS-REQ-194 | Mixed-plane Change Pack запрещён. | [`12_Implementation_Specifications/16_Harness_Maintenance_Plane.md`](12_Implementation_Specifications/16_Harness_Maintenance_Plane.md) |
| HNS-REQ-195 | Project Control Maintenance не исполняется как product feature task. | [`12_Implementation_Specifications/16_Harness_Maintenance_Plane.md`](12_Implementation_Specifications/16_Harness_Maintenance_Plane.md) |
| HNS-REQ-196 | Human-readable PROJECT/ARCHITECTURE/TECHNOLOGY/ROADMAP/STATUS views отделены от `.harness/` machine layer. | [`12_Implementation_Specifications/17_Documentation_Layers_and_Minimal_Mode.md`](12_Implementation_Specifications/17_Documentation_Layers_and_Minimal_Mode.md) |
| HNS-REQ-197 | MINIMAL, STANDARD, MULTI_REPO и REGULATED modes имеют явный обязательный artifact set. | [`12_Implementation_Specifications/17_Documentation_Layers_and_Minimal_Mode.md`](12_Implementation_Specifications/17_Documentation_Layers_and_Minimal_Mode.md) |
| HNS-REQ-198 | Profiles, IDs, statuses, routing values и capabilities происходят из versioned registries. | [`12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md`](12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md) |
| HNS-REQ-199 | Run является одной attempt; retry создаёт новый Run. | [`12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md`](12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md) |
| HNS-REQ-200 | Semantic documentation validation проверяет enums, prefixes, links, lifecycles, contracts и generated aggregates. | [`12_Implementation_Specifications/19_Semantic_Documentation_Validation.md`](12_Implementation_Specifications/19_Semantic_Documentation_Validation.md) |
| HNS-REQ-201 | Brownfield onboarding начинается read-only и фиксирует repository revision. | [`12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md`](12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md) |
| HNS-REQ-202 | Brownfield inventory определяет topology, stack, commands, tests, data, contracts, docs and known failures. | [`12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md`](12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md) |
| HNS-REQ-203 | Code/docs/tests discrepancies классифицируются и проходят Brownfield Baseline Gate. | [`12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md`](12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md) |
| HNS-REQ-204 | Brownfield route portfolio разделяет continuation, bug-fix, improvement и stabilization. | [`12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md`](12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md) |
| HNS-REQ-205 | Каждый старт greenfield/brownfield project создаёт Questionnaire Session. | [`12_Implementation_Specifications/21_Project_Start_Questionnaire.md`](12_Implementation_Specifications/21_Project_Start_Questionnaire.md) |
| HNS-REQ-206 | Первый обязательный вопрос относится к документации проекта. | [`12_Implementation_Specifications/21_Project_Start_Questionnaire.md`](12_Implementation_Specifications/21_Project_Start_Questionnaire.md) |
| HNS-REQ-207 | После анализа документации Harness задаёт только material source-derived и missing typical questions. | [`12_Implementation_Specifications/21_Project_Start_Questionnaire.md`](12_Implementation_Specifications/21_Project_Start_Questionnaire.md) |
| HNS-REQ-208 | Typical questionnaire покрывает users/scale, online-offline, platforms, architecture-affecting context, data, integrations, security, operations и success. | [`12_Implementation_Specifications/21_Project_Start_Questionnaire.md`](12_Implementation_Specifications/21_Project_Start_Questionnaire.md) |
| HNS-REQ-209 | Questionnaire задаёт 3–5 вопросов за batch, обычно 7–12 всего и не более 15 до первого draft. | [`12_Implementation_Specifications/21_Project_Start_Questionnaire.md`](12_Implementation_Specifications/21_Project_Start_Questionnaire.md) |
| HNS-REQ-210 | Каждый вопрос объясняет цель, формат ответа, варианты, recommendation и вариант «не знаю». | [`12_Implementation_Specifications/21_Project_Start_Questionnaire.md`](12_Implementation_Specifications/21_Project_Start_Questionnaire.md) |
| HNS-REQ-211 | После ответов Harness последовательно создаёт Project Definition, architecture, Technology Baseline, skills, bootstrap, routes и first READY task. | [`12_Implementation_Specifications/21_Project_Start_Questionnaire.md`](12_Implementation_Specifications/21_Project_Start_Questionnaire.md) |

## 14. Contract hardening v0.4.1

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-212 | Успешная Task использует `DONE`, успешный Run — `SUCCEEDED`; `COMPLETED` сохраняется только в применимых lifecycle groups. | [`12_Implementation_Specifications/23_Contract_Hardening_v0.4.1.md`](12_Implementation_Specifications/23_Contract_Hardening_v0.4.1.md) |
| HNS-REQ-213 | Validator применяет statuses registry по entity type и отклоняет новые Task/Run со status `COMPLETED`. | [`12_Implementation_Specifications/23_Contract_Hardening_v0.4.1.md`](12_Implementation_Specifications/23_Contract_Hardening_v0.4.1.md) |
| HNS-REQ-214 | Immutable v0.4.0 Task/Run history читается через явно отчётный compatibility mapping без перезаписи файлов. | [`MIGRATION_FROM_v0.4.0.md`](MIGRATION_FROM_v0.4.0.md) |
| HNS-REQ-215 | Brownfield/Hybrid readiness требует отдельного `brownfield_baseline` approval помимо четырёх Greenfield approvals. | [`02_Intake/01_Project_Intake_and_Readiness_Gates.md`](02_Intake/01_Project_Intake_and_Readiness_Gates.md) |
| HNS-REQ-216 | Accepted Brownfield Baseline ссылается на отдельный immutable Decision и фиксирует actor/time acceptance. | [`10_Contracts/03_Extended_Contracts_Examples.md`](10_Contracts/03_Extended_Contracts_Examples.md) |
| HNS-REQ-217 | Canonical sensitivity classes ограничены `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`, `SECRET`, `REGULATED`. | [`07_Security/02_Data_Classification_and_Runtime_Permissions.md`](07_Security/02_Data_Classification_and_Runtime_Permissions.md) |
| HNS-REQ-218 | `UNKNOWN` является temporary intake state и блокирует readiness, а не data classification. | [`12_Implementation_Specifications/21_Project_Start_Questionnaire.md`](12_Implementation_Specifications/21_Project_Start_Questionnaire.md) |
| HNS-REQ-219 | `PROJECT_INPUT@2` закрывает неизвестные properties нормативных objects и проверяет types, required fields и non-empty collections. | [`10_Contracts/01_Core_Contracts_Examples.md`](10_Contracts/01_Core_Contracts_Examples.md) |
| HNS-REQ-220 | Единственный открытый input extension point — `skills.resolutions[].configuration`; forbidden accounting semantics проверяются и внутри него. | [`12_Implementation_Specifications/23_Contract_Hardening_v0.4.1.md`](12_Implementation_Specifications/23_Contract_Hardening_v0.4.1.md) |
| HNS-REQ-221 | Run reservation фиксирует trusted snapshot product plane, `.harness/**` и generated root views после всех Kernel-owned writes. | [`04_Execution/02_Execution_Lifecycle.md`](04_Execution/02_Execution_Lifecycle.md) |
| HNS-REQ-222 | `verify` и `complete` блокируются при changed/deleted/unexpected/unsafe protected paths или exact Agent Result channel violation. | [`07_Security/01_Security_Trust_and_Supply_Chain.md`](07_Security/01_Security_Trust_and_Supply_Chain.md) |
| HNS-REQ-223 | Product digest, изменённый после successful verify, требует повторной verification до completion. | [`04_Execution/02_Execution_Lifecycle.md`](04_Execution/02_Execution_Lifecycle.md) |
| HNS-REQ-224 | Новый Run legacy проекта разрешается только после explicit v0.4.0 → v0.4.1 migration и current-state validation. | [`MIGRATION_FROM_v0.4.0.md`](MIGRATION_FROM_v0.4.0.md) |

## 18. Implementation levels and Stage lifecycle v0.5.0

| ID | Requirement | Coverage |
|---|---|---|
| HNS-REQ-225 | Canonical implementation scale содержит только `PROTOTYPE`, `ALPHA`, `BETA`, `MVP`, `RELEASE` и последовательный graph. | [`registries/implementation_levels.yaml`](registries/implementation_levels.yaml) |
| HNS-REQ-226 | Implementation level изменяет depth/evidence burden, но не добавляет product scope. | [`03_Planning/07_Implementation_Levels_and_Stage_Plans.md`](03_Planning/07_Implementation_Levels_and_Stage_Plans.md) |
| HNS-REQ-227 | `PROJECT_INPUT@3` требует canonical target и разделяет claimed maturity от runtime conclusions. | [`02_Intake/01_Project_Intake_and_Readiness_Gates.md`](02_Intake/01_Project_Intake_and_Readiness_Gates.md) |
| HNS-REQ-228 | Target `UNSURE` остаётся `WAITING_DECISION` и не подставляется автоматически. | [`12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md`](12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md) |
| HNS-REQ-229 | Stage State хранит target, claimed, observed, accepted и active values раздельно. | [`04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md`](04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md) |
| HNS-REQ-230 | Planner создаёт outlines до target, но detailed atomic work только active stage. | [`03_Planning/07_Implementation_Levels_and_Stage_Plans.md`](03_Planning/07_Implementation_Levels_and_Stage_Plans.md) |
| HNS-REQ-231 | Каждый executable Work Package, Task, Run/Prompt Plan привязан к `implementation_stage`. | [`03_Planning/02_Roadmap_DAG_Tracks_and_Parallelism.md`](03_Planning/02_Roadmap_DAG_Tracks_and_Parallelism.md) |
| HNS-REQ-232 | Runtime не выдаёт Task другой стадии и классифицирует future-stage-only work как scope violation. | [`04_Execution/02_Execution_Lifecycle.md`](04_Execution/02_Execution_Lifecycle.md) |
| HNS-REQ-233 | Последняя Task стадии переводит Stage в `VERIFYING`, а не project в `COMPLETED`. | [`04_Execution/01_State_Machine.md`](04_Execution/01_State_Machine.md) |
| HNS-REQ-234 | Mandatory Stage Gate criterion закрывается только `PASS` или обоснованным `NOT_APPLICABLE`; averages запрещены. | [`04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md`](04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md) |
| HNS-REQ-235 | Каждая принятая Stage создаёт immutable baseline, permitted use, limitations и next-stage gaps. | [`10_Contracts/03_Extended_Contracts_Examples.md`](10_Contracts/03_Extended_Contracts_Examples.md) |
| HNS-REQ-236 | Stage acceptance и next-stage activation выполняются одной rollback-safe transaction. | [`04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md`](04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md) |
| HNS-REQ-237 | Brownfield maturity assessment read-only и не запускает repository commands автоматически. | [`04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md`](04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md) |
| HNS-REQ-238 | Claimed, observed, satisfied candidate и accepted maturity не сворачиваются в одно поле. | [`12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md`](12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md) |
| HNS-REQ-239 | Brownfield baseline acceptance разрешён только с exact assessment revision/digest и отдельным report по каждой Stage. | [`04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md`](04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md) |
| HNS-REQ-240 | Same-level maintenance не повышает target и остаётся отдельным route. | [`03_Planning/07_Implementation_Levels_and_Stage_Plans.md`](03_Planning/07_Implementation_Levels_and_Stage_Plans.md) |
| HNS-REQ-241 | Level-up сохраняет accepted history и активирует только ближайшую следующую Stage. | [`04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md`](04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md) |
| HNS-REQ-242 | Migration v0.4.1 → v0.5.0 сохраняет history, не угадывает accepted level и коммитит только validated copy. | [`MIGRATION_FROM_v0.4.1.md`](MIGRATION_FROM_v0.4.1.md) |
| HNS-REQ-243 | Brownfield baseline acceptance связывает exact assessment с current tree/target/accepted/claim/sequential context; drift и stale evidence дают immutable `STALE` record и zero acceptance mutation. | [`04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md`](04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md) |
| HNS-REQ-244 | Каждый Gate-closing `EVD-*` ref разрешается по exact canonical path в normalized immutable evidence artifact; dangling/legacy/malformed refs блокируют acceptance. | [`04_Execution/03_Reports_Evidence_and_Validation.md`](04_Execution/03_Reports_Evidence_and_Validation.md) |
| HNS-REQ-245 | Gate evidence проверяется по positive status, provenance/source binding, exact product baseline, requested subject mapping и criterion-specific `required_evidence_kinds`. | [`04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md`](04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md) |
| HNS-REQ-246 | Accepted Gate и Stage Acceptance Report сохраняют одинаковые exact evidence refs и SHA-256 bindings; `validate-project` обнаруживает deletion/tampering. | [`10_Contracts/03_Extended_Contracts_Examples.md`](10_Contracts/03_Extended_Contracts_Examples.md) |
| HNS-REQ-247 | Runtime Task evidence привязано к exact post-verification product revision и не считается автоматически доказательством final Stage criteria после дальнейших product changes. | [`04_Execution/03_Reports_Evidence_and_Validation.md`](04_Execution/03_Reports_Evidence_and_Validation.md) |

