# Границы, принципы и нецели

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Scope версии 0.3

Baseline охватывает software and software-infrastructure projects и включает:

- single entry, Request/Request Plan and Result Envelope;
- mandatory greenfield/brownfield questionnaire;
- source/repository analysis and reconciliation;
- Project Definition, requirements, constraints, ADR, architecture and Technology Baseline;
- Work Packages, atomic tasks, DAG/readiness and safe parallel batches;
- Prompt IR, context planning, skill registry and JIT compilation;
- Codex Agent Adapter and governed tool execution;
- proportional verification, test environment policy, evidence and logging;
- blockers/recovery, Change Packs, Git/worktrees and documentation views;
- semantic documentation validation and versioned distribution.

## 2. Основные принципы

```text
one natural-language entry
canonical source of truth
human approval for material decisions
minimum sufficient tasks and prompts
causal readiness before execution
read/write conflict safety
proportionate verification
append-only history
recoverable blockers
project-agnostic kernel
```

## 3. Нецели

Harness не является:

- автономным владельцем product scope;
- заменой пользователю/approver для material decisions;
- универсальным средством физического управления неизвестным hardware без adapter/profile;
- системой, которая молча переписывает brownfield architecture;
- источником скрытых capabilities;
- provider billing или token-cost subsystem;
- системой, где LLM self-report является единственным evidence.

## 4. Граница Harness и создаваемого проекта

Hard-coded project stack, entities and architecture отсутствуют в universal kernel. Конкретный project может содержать payments, machine learning, embedded devices или другие domain concerns, если соответствующие requirements, profiles, tools and approvals определены.

## 5. Простота как обязательное свойство

Внутренние contracts могут быть подробными, но пользовательский UX остаётся компактным:

- один вход;
- небольшие question batches;
- один active outcome;
- один Result Envelope;
- generated human-readable views;
- отсутствие отдельного prompt для каждого файла или мелкой операции.

## 6. Нормативные ссылки

- single entry: [`../12_Implementation_Specifications/01_Single_Entry_Request_Contract.md`](../12_Implementation_Specifications/01_Single_Entry_Request_Contract.md);
- documentation modes: [`../12_Implementation_Specifications/17_Documentation_Layers_and_Minimal_Mode.md`](../12_Implementation_Specifications/17_Documentation_Layers_and_Minimal_Mode.md);
- non-goal validation: [`../12_Implementation_Specifications/19_Semantic_Documentation_Validation.md`](../12_Implementation_Specifications/19_Semantic_Documentation_Validation.md).
