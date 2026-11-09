# Context Planning, приоритеты и overflow

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Назначение

Context Planning определяет, какие canonical documents, contracts, code fragments и evidence войдут в конкретный Run. Его задача — обеспечить достаточный, проверяемый и безопасный контекст без копирования всей документации и repository.

## 2. Три сущности

```text
Context Policy (CTP)
→ Context Plan (CTX)
→ Context Packet (CPK)
```

### Context Policy

Versioned правило для класса задач. Определяет:

- обязательные source classes;
- authority/ranking rules;
- retrieval и section selection;
- deduplication;
- сохранение конфликтов;
- допустимую summarization;
- redaction и egress;
- freshness checks;
- overflow behavior;
- обязательное логирование исключений.

### Context Plan

Task/run-specific решение: какие exact sources включены, исключены или преобразованы и почему.

### Context Packet

Материализованный minimal view, передаваемый executor adapter.

## 3. Классы включения

```text
MANDATORY_INSTRUCTION
MANDATORY_EVIDENCE
TASK_REQUIRED
CONDITIONALLY_REQUIRED
OPTIONAL_SUPPORTING
EXCLUDED_BY_POLICY
```

К `MANDATORY_INSTRUCTION` относятся effective constraints, scope, permissions, output schema, blocker protocol и critical invariants. Они не могут быть удалены из-за overflow.

## 4. Context Plan Contract

```yaml
context_plan:
  id: CTX-TSK-BACKEND-040-R1
  revision: 1
  task_ref: TSK-BACKEND-040@3
  run_plan_ref: RNP-RUN-20260806-0001@1
  policy_ref: CTP-TASK-STANDARD@2

  sources:
    included:
      - ref: PJD-PROJECT-001@4
        section_ids: [project-purpose, accepted-scope]
        class: TASK_REQUIRED
        reason: "Определяет цель и границы проекта"
      - ref: CST-DATA-001@2
        class: MANDATORY_INSTRUCTION
        reason: "Effective data boundary"
      - ref: CNT-SEARCH@2
        class: MANDATORY_EVIDENCE
        reason: "Принятый API contract"
      - ref: DOC-API-SEARCH@2
        section_ids: [search-endpoint]
        class: TASK_REQUIRED
        reason: "Документационный результат должен остаться синхронным"
    excluded:
      - ref: DOC-LEGACY-004
        class: OPTIONAL_SUPPORTING
        reason: "Superseded и не относится к текущему task"

  code_selection:
    repository: backend
    base_revision: abc123
    paths:
      - services/backend/src/search/**
      - services/backend/tests/search/**
    symbol_refs: []

  transformations:
    - type: EXTRACT_SECTIONS
      source_ref: ADR-API-004@1
      parameters:
        section_ids: [decision, consequences]

  conflicts_preserved: []
  redactions: []
  compatibility_result_ref: CMP-RUN-0001
  source_hash: sha256:...
  status: READY
```

## 5. Алгоритм построения

```text
1. Load Task Contract and required artifacts
2. Resolve effective constraints/policies/decisions
3. Resolve exact documentation sections and revisions
4. Select relevant code/tests/contracts
5. Preserve open material conflicts
6. Classify data and apply redaction/egress policy
7. Rank and deduplicate sources
8. Evaluate executor compatibility
9. Apply overflow policy if required
10. Emit source map and immutable Context Plan
```

Любое включение должно иметь reason. Любое исключение обязательного candidate source должно иметь recorded reason.

## 6. Source ranking

Ranking учитывает:

1. applicability to task;
2. accepted authority and canonical status;
3. direct requirement/contract/documentation linkage;
4. exact revision/freshness;
5. repository and symbol proximity;
6. known contradiction status;
7. usefulness for verification.

Краткость, удобство или более поздняя дата сами по себе не повышают authority.

## 7. Безопасная компрессия

Summarization разрешена, только если:

- source class допускает это;
- сохраняются source refs, section IDs и hashes;
- material constraints, negations и exceptions не теряются;
- acceptance criteria остаются проверяемыми;
- conflicting statements не объединяются в ложный consensus;
- summary имеет transformation record;
- validator или reviewer может восстановить provenance.

Canonical contract, hard constraint, permission scope и exact acceptance criterion предпочтительно включаются структурированно или дословно в пределах необходимого фрагмента.

## 8. Overflow policy

Порядок действий:

```text
1. REMOVE_DUPLICATES
2. DROP_OPTIONAL_SUPPORTING
3. EXTRACT_RELEVANT_SECTIONS
4. APPLY_APPROVED_SUMMARY
5. SPLIT_TASK
6. SELECT_COMPATIBLE_EXECUTOR
7. WAITING_DECISION
```

Запрещены silent truncation и удаление mandatory instructions/evidence. Если task требует слишком широкого контекста, это сигнал неправильной декомпозиции или несовместимого executor profile.

## 9. Конфликты источников

Material conflict сохраняется как отдельный conflict object. Context builder не выбирает удобную сторону автоматически. Для non-material observed discrepancy допускается явно зарегистрированная reversible assumption по project ambiguity policy.

## 10. Privacy, security и prompt injection

До inclusion выполняются:

- trust classification;
- instruction/data separation;
- secret and sensitive-data redaction;
- egress authorization;
- path and source scope checks;
- size/parser limits;
- marking untrusted excerpts.

Repository text, comment или external tool output не становится system instruction.

## 11. Verification

Context Plan считается валидным, если:

- все mandatory refs разрешены и существуют;
- required artifact revisions совпадают;
- нет unresolved material conflict, блокирующего task;
- excluded sources имеют reason;
- packet fits selected adapter profile;
- source map полностью связывает output с input revisions;
- no forbidden data crosses egress boundary.

## 12. Неучёт provider economics

Harness не хранит token usage, стоимость model calls или provider billing. Compatibility preflight проверяет только техническую вместимость и поддерживаемые features executor adapter.

## 13. Связанные спецификации

- [`05_Context_Packets.md`](05_Context_Packets.md)
- [`../12_Implementation_Specifications/04_JIT_Prompt_Compilation.md`](../12_Implementation_Specifications/04_JIT_Prompt_Compilation.md)
- [`../12_Implementation_Specifications/05_Documentation_Traceability.md`](../12_Implementation_Specifications/05_Documentation_Traceability.md)
- [`../12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md`](../12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md)
