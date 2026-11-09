# Реализационные спецификации Project Harness v0.5.0

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION BASELINE

## 1. Назначение раздела

Раздел является нормативным мостом между architecture, registries, schemas и executable runtime. Каждый файл описывает mechanism, contracts, states, errors, validation и acceptance criteria.

```text
Executable schema/conformance behavior
→ machine-readable registries
→ implementation specifications
→ thematic chapters
→ examples
→ explanatory prose
```

## 2. Сквозная модель v0.5.0

```text
Browser GPT / User Input
→ external START_INTAKE
→ documentation/source analysis
→ core outcome and target Implementation Level
→ material approvals
→ sequential Stage Plans to target
→ detailed DAG only for active stage
→ exactly one current JIT bundle
→ governed Codex Run
→ independent verification
→ Stage Gate
→ immutable accepted baseline
→ next stage or TARGET_LEVEL_REACHED
```

`START_INTAKE` не является `BOOTSTRAP_PROJECT`. Brownfield repository остаётся read-only до handoff; maturity assessment также не запускает команды автоматически.

## 3. Состав спецификаций

| № | Документ | Реализуемый механизм |
|---:|---|---|
| 01 | [Single Entry and Request Contract](01_Single_Entry_Request_Contract.md) | Единая entry point, Request и Request Plan. |
| 02 | [Result Envelope and Statuses](02_Result_Envelope_and_Statuses.md) | Понятный Result Envelope и entity-specific statuses. |
| 03 | [Work Packages, Tasks and Subtasks](03_Work_Packages_Tasks_and_Subtasks.md) | Atomic task decomposition. |
| 04 | [JIT Prompt Compilation](04_JIT_Prompt_Compilation.md) | Prompt только для текущей READY Task. |
| 05 | [Documentation Traceability](05_Documentation_Traceability.md) | Requirement/ADR/document refs. |
| 06 | [ADR and Decision Policy](06_ADR_and_Decision_Policy.md) | Material human-governed decisions. |
| 07 | [Causal Development Sequence](07_Causal_Development_Sequence.md) | Artifact-producing dependency order. |
| 08 | [Safe Parallel Execution](08_Safe_Parallel_Execution.md) | Future hardening for parallel ownership. |
| 09 | [Ambiguity and Clarification Policy](09_Ambiguity_and_Clarification_Policy.md) | Bounded material questions. |
| 10 | [Blockers, Recovery and Progression](10_Blockers_Recovery_and_Progression.md) | Blocker/recovery/resume. |
| 11 | [Verification, Testing and Test Data](11_Verification_Testing_and_Test_Data.md) | Independent proportional checks. |
| 12 | [Request Trace and Logging](12_Request_Trace_and_Logging.md) | Correlated trace and evidence. |
| 13 | [Technology Baseline](13_Technology_Baseline.md) | Technology selection and compatibility. |
| 14 | [Skill Registry and Lifecycle](14_Skill_Registry_and_Lifecycle.md) | Active skill resolution; future authoring lifecycle. |
| 15 | [Codex Agent Adapter](15_Codex_Agent_Adapter.md) | Codex as bounded executor. |
| 16 | [Harness Maintenance Plane](16_Harness_Maintenance_Plane.md) | Governed Harness changes. |
| 17 | [Documentation Layers and Minimal Mode](17_Documentation_Layers_and_Minimal_Mode.md) | Human views over canonical control data. |
| 18 | [Registries and Contract Normalization](18_Registries_Lifecycles_and_Contract_Normalization.md) | IDs, statuses, contracts and generated views. |
| 19 | [Semantic Documentation Validation](19_Semantic_Documentation_Validation.md) | Reproducible documentation validation. |
| 20 | [Brownfield Project Onboarding](20_Brownfield_Project_Onboarding.md) | Read-only onboarding and route families. |
| 21 | [Project Start Questionnaire](21_Project_Start_Questionnaire.md) | Documentation-first bounded intake. |
| 22 | [Browser GPT Preparation and Codex Handoff](22_Browser_GPT_Preparation_and_Codex_Handoff.md) | Semantic preparation plus deterministic archive. |
| 23 | [Contract Hardening v0.4.1](23_Contract_Hardening_v0.4.1.md) | Historical prerequisite: statuses, Brownfield approval, sensitivity, strict schema and control-plane invariants. |
| 24 | [Implementation Levels and Stage Planning v0.5.0](24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md) | Canonical levels, Stage Plans/Gates, maturity, maintenance, level-up and migration. |

## 4. First stage-aware vertical slice

1. `doctor` validates distribution, seven registries, schemas and seed skills.
2. `start-intake` creates external provisional workspace.
3. Browser GPT grounds `PROJECT_INPUT@3` in sources and user decisions.
4. Target level is explicit before architecture/planning.
5. `prepare` creates Stage State and outlines through target.
6. Only active stage gets Work Packages, Tasks, Context/Prompt Plans and one JIT bundle.
7. Codex changes only task scope; Harness independently verifies actual writes and commands.
8. Final Task moves Stage to `VERIFYING`.
9. `accept-stage` atomically creates immutable acceptance and activates nearest next stage.
10. Target acceptance sets `TARGET_LEVEL_REACHED`.
11. Brownfield assessment stays read-only and approval-gated.
12. `level-up` preserves baselines and opens only nearest next stage.

## 5. Implemented Core and excluded hardening

Implemented v0.5.0 includes sequential stage-aware planning/execution, formal Gates, Brownfield assessment, same-level maintenance, migration and deterministic packaging.

Excluded: automated executor, rootless sandbox, Git commit/push/PR, deployment execution route, declarative PROJECT skill authoring, parallel worktrees and remote control plane.

## 6. Definition of Done

- all persisted Stage artifacts are catalogued;
- exact seven registry versions/digests are locked;
- `PROJECT_INPUT@3` rejects noncanonical target and unresolved `UNSURE`;
- only active stage has atomic executable work;
- Gate mandatory criteria are evidence-based and non-averaged;
- every acceptance creates immutable baseline/use/limitations/gaps records;
- claimed, observed, satisfied and accepted maturity remain distinct;
- assessment executes no commands automatically;
- maintenance and level-up remain distinct;
- v0.4.1 history migrates without loss;
- documentation and engine conformance suites pass.
