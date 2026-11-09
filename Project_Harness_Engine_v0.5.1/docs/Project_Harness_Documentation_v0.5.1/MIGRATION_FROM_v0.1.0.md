# Migration notes: documentation v0.1.0 → v0.2.0

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## Breaking conceptual changes

1. Harness определяется как project-agnostic engine, а не обобщение конкретного project control plane.
2. Полная документация больше не является обязательным входом для greenfield: достаточно Project Intent.
3. Добавлен отдельный Project Definition Gate до architecture.
4. Constraints, invariants, policies, assumptions, unknowns и waivers стали самостоятельными сущностями.
5. Engine разделён на deterministic kernel, inference workers и execution runtime.
6. Prompt стал compiled IR artifact; Context Packet дополнен Context Policy/Plan.
7. Agent, model и tool adapters разделены.
8. Добавлены runtime permissions, Run Trace, retry/idempotency/cancellation/compensation.
9. Structural validation дополнена behavioral/adversarial/cross-profile evaluation.
10. Coverage определяется независимой capability/lifecycle model.
11. Двусмысленный `COMPLETED_WITH_DEFERRED_CHECKS` удалён; later verification моделируется отдельными gates/tasks.
12. Harness/provider billing, payments for model calls, model-call costs и token-usage accounting явно исключены.

## File changes

Удалены project-specific methodology и mapping documents как архитектурный baseline. Контрольные суммы исходных материалов перенесены в нейтральный provenance appendix. Добавлены:

- `00_Overview/03_Project_Agnostic_Foundation.md`;
- `00_Overview/05_Project_Lifecycle_and_Profiles.md`;
- `01_Architecture/05_Constraints_Policies_and_Decisions.md`;
- `01_Architecture/06_Prompt_IR_and_Compilation.md`;
- `01_Architecture/07_Execution_Compatibility.md`;
- `02_Intake/04_Project_Definition_and_Discovery.md`;
- `03_Planning/06_Context_Planning_and_Overflow.md`;
- `04_Execution/05_Run_Trace_Retry_and_Idempotency.md`;
- `04_Execution/06_Prompt_Evaluation_and_Release.md`;
- `07_Security/02_Data_Classification_and_Runtime_Permissions.md`;
- `10_Contracts/03_Extended_Contracts_Examples.md`;
- новые appendices по profiles, coverage, gap resolution и quality.

## Required implementation migration

Существующий prototype, если он следует schema v1, должен сначала экспортировать sources, requirements, decisions, tasks, state, reports and evidence, затем:

1. создать Project Intent/Definition;
2. классифицировать прежние context/constraints;
3. выделить assumptions/unknowns;
4. преобразовать prompt files в Prompt Specs/Modules;
5. создать Context Policies;
6. зарегистрировать adapter/capability profiles;
7. сохранить old reports as immutable history;
8. выполнить validation and coverage review.
