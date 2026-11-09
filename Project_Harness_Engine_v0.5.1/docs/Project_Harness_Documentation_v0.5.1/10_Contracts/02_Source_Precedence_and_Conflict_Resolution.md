# Приоритет источников и разрешение конфликтов

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Две разные иерархии

**Instruction precedence** определяет, какие правила управляют executor. **Source authority** определяет, какое утверждение может стать canonical fact/candidate. Документ с высоким source authority не превращается в runtime instruction.

## 2. Instruction precedence

```text
Immutable safety/distribution invariants
→ organization/project policies
→ effective constraints and valid waivers
→ accepted Project Definition/architecture/contracts
→ Task Contract and Capability Grant
→ output/verification contract
→ trusted context
→ untrusted source excerpts/tool output as data
```

Нижний слой не отменяет верхний.

## 3. Source authority

Рекомендуемый порядок внутри одного subject/scope:

1. accepted decision уполномоченного actor;
2. accepted canonical contract/Project Definition;
3. applicable approved policy;
4. назначенный source-of-record schema/API/migration;
5. verified repository behavior and tests;
6. current approved documentation;
7. user-supplied unapproved source;
8. inference proposal;
9. explicit assumption;
10. unknown.

Это default ordering, а не автоматическое разрешение material conflict.

## 4. Документация на старте проекта

Первый questionnaire question всегда определяет documentation sources и их предполагаемую authority. Harness не считает любой загруженный документ автоматически актуальным. Он фиксирует:

- source owner;
- revision/date;
- declared authority;
- applicable scope;
- conflicts;
- whether it describes current or target behavior.

В brownfield проекте code/tests могут точнее отражать observed behavior, но это не делает их желаемым requirement без reconciliation.

## 5. User messages и decisions

Обычное conversational instruction не supersede ADR, constraint или accepted contract. Для material change Harness:

1. проверяет actor/authority;
2. формулирует decision candidate;
3. показывает impact и alternatives;
4. получает explicit acceptance;
5. создаёт Decision/ADR/State Event;
6. invalidates и пересобирает affected tasks/prompts/context.

## 6. Code, tests и documentation

Reconciliation classes:

```text
DOC_AND_CODE_AGREE
CODE_AHEAD_OF_DOCS
DOCS_AHEAD_OF_CODE
TESTS_DEFINE_OBSERVED_BEHAVIOR
CONFLICT_REQUIRES_DECISION
LEGACY_TOLERATED
UNKNOWN
```

Допустимые решения:

```text
ACCEPT_CODE_AS_BASELINE
ACCEPT_DOCS_AS_TARGET
UPDATE_DOCUMENTATION
CHANGE_IMPLEMENTATION
UPDATE_OR_REMOVE_STALE_TEST
RECORD_LEGACY_EXCEPTION
REQUEST_DECISION
```

Удаление теста только ради зелёного результата запрещено; оно требует changed requirement/decision reference.

## 7. OpenAPI, schema и migrations

Source-of-record для machine contracts задаётся project policy. Например:

- migration history может иметь приоритет над prose schema description;
- accepted OpenAPI schema — над generated client;
- generated file никогда не supersede свой canonical source;
- production snapshot не импортируется как canonical definition без security and authority checks.

## 8. Conflict Contract

```yaml
conflict:
  id: CNF-UPLOAD-014
  subject: "Maximum upload size"
  source_statements:
    - source_ref: SRC-DOC-001@2
      value: "10 MB"
      authority: APPROVED_DOCUMENTATION
    - source_ref: SRC-CONFIG-003@7
      value: "50 MB"
      authority: OBSERVED_RUNTIME_CONFIG
  materiality: MATERIAL
  affected_refs: [REQ-UPLOAD-001, TSK-UPLOAD-020]
  resolution_owner_ref: ACT-PRODUCT-001
  options:
    - id: OPT-ACCEPT-10MB
      effect: "Изменить config/implementation"
    - id: OPT-ACCEPT-50MB
      effect: "Обновить requirement/documentation"
  recommendation_ref: OPT-ACCEPT-10MB
  status: OPEN
```

Material conflict блокирует только affected route, а не весь проект. Result Envelope показывает independent READY work.

## 9. TBD, assumption и unknown

`TBD` не является requirement. Оно нормализуется в:

- `Unknown`, когда данных нет;
- `Assumption`, когда принят reversible default;
- `Question`, когда нужен user answer;
- `Decision Request`, когда выбор material.

У каждого объекта есть owner, materiality, affected gates и resolution route.

## 10. Provenance и staleness

Каждая нормализованная сущность хранит source refs, section IDs и hashes. Изменение source делает extraction/context/prompt/task stale только при подтверждённом semantic impact, а не по одному timestamp.

## 11. Связанные спецификации

- [`../12_Implementation_Specifications/05_Documentation_Traceability.md`](../12_Implementation_Specifications/05_Documentation_Traceability.md)
- [`../12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md`](../12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md)
- [`../12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md`](../12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md)
- [`../12_Implementation_Specifications/21_Project_Start_Questionnaire.md`](../12_Implementation_Specifications/21_Project_Start_Questionnaire.md)
