# Политика ADR и material decisions

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Harness обязан фиксировать важные инженерные решения, но не должен превращать ADR-каталог в журнал каждой выполненной задачи. Разные типы информации сохраняются в разных артефактах:

| Вопрос | Артефакт |
|---|---|
| Какое долговременное решение принято и почему? | ADR / Decision Record |
| Что требуется сделать? | Work Package / Task Contract |
| Что исполнялось? | Run Trace |
| Что изменено и как проверено? | Task Report / Evidence |
| Как изменилось состояние? | State Event |
| Что выполнять дальше? | DAG / Result Envelope |

## 2. Material decision

Решение является material, если оно способно заметно изменить хотя бы одно из следующего:

- границы системы или компонентов;
- публичный API, event, data или integration contract;
- модель данных и миграционный путь;
- security/trust boundary;
- обработку чувствительных данных;
- deployment topology;
- поддерживаемые платформы;
- ключевой язык, runtime, framework, database или инфраструктурный provider;
- consistency, availability, performance или scalability strategy;
- необратимость, rollback или migration risk;
- universal/project-local routing, prompt, skill или permission semantics;
- обязательный quality gate.

## 3. Когда ADR обязателен

ADR создаётся или обновляется для:

```text
SYSTEM_BOUNDARY
ARCHITECTURE_STYLE
TECHNOLOGY_SELECTION
PUBLIC_CONTRACT
DATA_MODEL
SECURITY_BOUNDARY
DEPLOYMENT_TOPOLOGY
MATERIAL_MIGRATION
CROSS_REPOSITORY_OWNERSHIP
HARNESS_ROUTING_SEMANTICS
HARNESS_PROMPT_OR_SKILL_SEMANTICS
MATERIAL_POLICY_OR_WAIVER
```

Примеры:

- выбор PostgreSQL вместо SQLite;
- переход от monolith к нескольким services;
- принятие cursor pagination как публичного API contract;
- выбор session storage model;
- изменение стратегии multi-tenant isolation;
- изменение правила parallel execution или capability enforcement.

## 4. Когда ADR не нужен

ADR обычно не создаётся для:

- обычной реализации endpoint по принятому contract;
- исправления дефекта без изменения expected behavior;
- локального refactoring;
- переименования символа;
- обновления документации;
- добавления или корректировки теста;
- создания каталога;
- изменения generated view;
- повторного использования уже принятого ADR;
- operational retry или blocker recovery, не меняющего baseline.

Такие действия фиксируются Task Contract, Task Report, Evidence и State Event.

## 5. Decision classification

```text
MATERIAL_ARCHITECTURE
MATERIAL_PRODUCT
MATERIAL_SECURITY
MATERIAL_TECHNOLOGY
MATERIAL_HARNESS
OPERATIONAL_APPROVAL
TASK_LOCAL_CHOICE
ASSUMPTION
```

- Первые пять типов требуют ADR или formal Decision Record.
- `OPERATIONAL_APPROVAL` фиксирует разрешение на конкретный side effect и не становится ADR.
- `TASK_LOCAL_CHOICE` может быть записан в Task Report, если обратим и не влияет на другие tasks.
- `ASSUMPTION` управляется Assumption Contract и review trigger.

## 6. Алгоритм определения необходимости ADR

```text
1. Does the choice alter accepted requirement, constraint or public contract?
2. Does it affect more than one task, component, repository or release?
3. Is the choice expensive or risky to reverse?
4. Does it create a new long-lived dependency or technology?
5. Does it alter security, data, deployment or operational boundaries?
6. Will a future contributor reasonably ask "why was this chosen"?

If any material rule is true → ADR candidate.
Otherwise → task-local record.
```

Inference worker может предложить classification, но Decision Policy evaluator принимает итог по формальным правилам.

## 7. ADR Contract

```yaml
adr:
  id: ADR-AUTH-003
  revision: 1
  title: "Хранение пользовательских сессий"
  decision_type: MATERIAL_ARCHITECTURE
  status: ACCEPTED

  context:
    problem: "Нужно обеспечить отзыв и горизонтальное масштабирование сессий"
    driver_refs: [REQ-AUTH-001, QUA-AVAIL-002]
    constraint_refs: [CST-SEC-001, CST-DATA-003]
    source_refs: [DOC-ARCH-AUTH@2]

  options:
    - id: OPT-JWT
      summary: "Stateless JWT"
      benefits: []
      costs: []
      risks: []
    - id: OPT-REDIS
      summary: "Server-side sessions in Redis"
      benefits: []
      costs: []
      risks: []

  decision:
    selected_option_ref: OPT-REDIS
    statement: "Использовать server-side sessions in Redis"
    rationale: "Требуется централизованный отзыв сессий"

  consequences:
    positive: []
    negative: []
    obligations:
      - "Добавить health and availability checks"
      - "Определить retention policy"

  affected_refs:
    work_packages: [WP-AUTH-001]
    contracts: [CNT-AUTH@1]
    documentation: [DOC-ARCH-AUTH]

  verification:
    acceptance_refs: [AC-ADR-AUTH-001]
    review_triggers:
      - "Рост требований к offline operation"
      - "Удаление Redis из technology baseline"

  supersedes: []
  superseded_by: null
  approved_by: ACT-ARCH-001
  decided_at: 2026-08-06T10:00:00Z
```

## 8. ADR lifecycle

```text
DRAFT → PROPOSED → ACCEPTED
                    ↘ REJECTED
ACCEPTED → SUPERSEDED
ACCEPTED → DEPRECATED
```

- `DRAFT` не может использоваться как обязательный input реализации.
- `PROPOSED` может блокировать dependent task, если решение material.
- `ACCEPTED` фиксирует baseline.
- Изменение принятого решения создаёт новую revision или superseding ADR; история не переписывается.

## 9. Decision Gate

Material decision route обязан показать пользователю:

- контекст и почему решение требуется сейчас;
- 2–4 реалистичных варианта;
- ограничения, выгоды и риски;
- рекомендуемый вариант;
- последствия откладывания;
- какие tasks будут разблокированы;
- возможность предложить свой вариант;
- возможность ответить «не знаю» и принять reversible default, если это разрешено policy.

После выбора Harness:

1. создаёт Decision/ADR;
2. обновляет Architecture/Technology Baseline;
3. выполняет impact analysis;
4. помечает затронутые tasks/prompts stale;
5. перестраивает readiness;
6. возвращает Result Envelope.

## 10. Связь ADR с задачами

Task Contract содержит:

```yaml
architecture_refs:
  - ADR-AUTH-003@1

decision_requirement:
  creates_new_decision: false
  required_decision_refs: [ADR-AUTH-003@1]
```

Если task обнаруживает необходимость нового material decision, она не должна принимать его скрыто. Task останавливается в `WAITING_DECISION`, а отдельный decision route создаёт ADR. После принятия task пересобирается и компилируется заново.

## 11. ADR и bug fixes

Bug fix не требует ADR, когда он возвращает код к уже принятому behavior. ADR или requirement change нужен, если:

- текущее documented behavior признано неверным;
- исправление меняет публичный contract;
- выбран workaround с долгосрочными последствиями;
- bug выявляет новую architecture/security boundary;
- необходима material migration.

## 12. Проверки

Semantic validator проверяет:

- каждая accepted material decision имеет ADR;
- ADR содержит минимум два варианта либо rationale, почему альтернативы отсутствуют;
- task не ссылается на `DRAFT/REJECTED/SUPERSEDED` ADR как на current baseline;
- supersession chain не содержит циклов;
- public contract change имеет decision/requirement update;
- обычные implementation tasks не создают ADR без materiality rationale.

## 13. Критерии приёмки

1. ADR создаётся только для material decisions.
2. Каждая material decision имеет контекст, варианты, rationale и consequences.
3. Task-local choices не загрязняют ADR registry.
4. Изменение accepted ADR запускает impact/replanning.
5. Agent не принимает material decision самостоятельно.
6. Result Envelope показывает созданные и повторно использованные decisions.
7. Semantic tests обнаруживают missing и избыточные ADR patterns.
