# Capability and lifecycle coverage v0.5.0

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Coverage matrix

| Capability | Canonical artifacts | Gate/Evidence |
|---|---|---|
| Single entry | Request, Request Plan, Route, Result, Trace | Classification/Result schema |
| Start questionnaire | Session, Source Inventory, Questions/Answers | Questionnaire Readiness |
| Project definition | Definition, scope, assumptions, unknowns | Project Definition Gate |
| Brownfield | Repository Inventory, Reconciliation, Brownfield Baseline | Brownfield Baseline Gate |
| Requirements/constraints | REQ/QUA/CST/INV/PLC/Waiver | Coverage and evaluator evidence |
| Decisions | Decision/ADR | Material Decision Gate |
| Architecture/technology | Architecture and Technology Baselines | Architecture/Technology Gate |
| Skills/bootstrap | Skill Registry, Bootstrap, Test Environment | Skill/Bootstrap Readiness |
| Planning | Work Package, Task, Artifact DAG, Parallel Batch | Task Readiness |
| Prompt/context | Modules/Specs/Plans/Bundles, Context | JIT Compile/Context Gate |
| Adapter/permissions | Agent/Tool profiles, Capability Grants | Compatibility/Side-effect Gate |
| Execution | Run Plan, Run, Tool Invocations | Run result and trace |
| Verification/docs | Verification Profile, Evidence, Task Report, Documentation refs | Task/Integration/Release Gate |
| Recovery | Blocker, safe state, compensation, resume | Recovery condition |
| Evolution/maintenance | Plane-specific Change Pack, migration | Approval/Canary/Activation |
| Git/release | Worktrees, leases, commit/publish plan | Integration/Publish Gate |
| Documentation/distribution | Human views, semantic validation, manifest | Documentation/Archive Gate |

## 2. Completeness dimensions

```text
Request and User Experience
Questionnaire and Source Coverage
Project/Brownfield Definition
Requirements and Constraints
Architecture and Technology
Skills and Bootstrap
Causal Planning and Parallel Safety
Prompt/Context/Adapter Compatibility
Verification and Documentation
Security and Permissions
Runtime/Recovery/Observability
Evolution and Distribution
```

## 3. Result

```text
COMPLETE
COMPLETE_WITH_ASSUMPTIONS
PARTIAL
BLOCKED
NOT_APPLICABLE
```

No overall percentage may hide a material blocked dimension.
