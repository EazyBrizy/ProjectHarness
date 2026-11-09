# Политика неоднозначностей, вопросов и предположений

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Harness не должен молча угадывать material требования, но также не должен останавливать разработку из-за каждой мелкой детали. Неоднозначность сначала классифицируется по влиянию, и только затем выбирается действие.

## 2. Materiality levels

```text
MATERIAL
NON_MATERIAL_REVERSIBLE
TRIVIAL
```

### 2.1. Material ambiguity

Неоднозначность material, если ответ может изменить:

- product scope или user outcome;
- architecture/technology baseline;
- public contract;
- security/privacy/data handling;
- irreversible migration;
- supported platform;
- permissions/side effects;
- acceptance criteria;
- существенный срок, capacity или reliability target;
- ownership между repositories/components.

Affected route обязан остановиться.

### 2.2. Non-material reversible ambiguity

Примеры:

- локальное имя внутренней функции;
- расположение небольшого private helper в пределах разрешённого scope;
- formatting choice;
- обратимая implementation detail, не влияющая на contract.

В `PRAGMATIC` режиме можно применить default и зафиксировать assumption/task-local choice.

### 2.3. Trivial ambiguity

Решается существующими style guides, formatter, linter или deterministic policy без отдельной записи.

## 3. Project ambiguity mode

```text
STRICT
PRAGMATIC
```

- `STRICT`: любая неразрешённая non-trivial ambiguity возвращается пользователю.
- `PRAGMATIC`: material ambiguity останавливает; non-material reversible ambiguity разрешается default с прозрачной записью.

Default для нового проекта — `PRAGMATIC`, если пользователь не выбрал strict governance и profile не требует strict mode.

## 4. Question Contract

```yaml
question:
  id: QST-ARCH-001
  intake_or_request_ref: RQ-20260806-0003
  project_ref: project-example

  text: "Должна ли система работать без подключения к интернету?"
  why_asked: "Ответ влияет на storage, sync и authentication architecture"
  materiality: MATERIAL
  affects:
    - ARCHITECTURE_BASELINE
    - TECHNOLOGY_BASELINE
    - REQUIREMENTS

  answer_type: SINGLE_CHOICE
  options:
    - id: ONLINE_ONLY
      label: "Только онлайн"
      explanation: "Проще инфраструктура; без сети функции недоступны"
    - id: LIMITED_OFFLINE
      label: "Часть функций офлайн"
      explanation: "Нужны локальный cache и синхронизация"
    - id: OFFLINE_FIRST
      label: "Полноценная offline-first работа"
      explanation: "Самая сложная модель данных и конфликтов"
    - id: UNKNOWN
      label: "Пока не знаю"
      explanation: "Harness предложит безопасный baseline и review trigger"

  recommendation:
    option_ref: ONLINE_ONLY
    rationale: "В исходной документации нет требования offline"

  blocking_scope:
    work_package_refs: [WP-BOOTSTRAP-001]
    task_refs: []

  response_required: true
  status: OPEN
```

## 5. Требования к формулировке вопроса

Пользователь должен понимать:

- о чём спрашивают;
- зачем это важно;
- как ответ повлияет на проект;
- какие варианты допустимы;
- что выбрать, если он не уверен;
- какой вариант рекомендует Harness и почему.

Запрещены вопросы без контекста вроде «Выберите consistency model» без пояснения понятным языком.

## 6. Question batching

Чтобы не перегружать пользователя:

- задаётся не более 3–5 связанных material вопросов за один batch;
- вопросы сортируются по blocking impact;
- зависимый вопрос не задаётся раньше ответа на родительский;
- ответы из документации не спрашиваются повторно;
- типовые вопросы, не влияющие на ближайший gate, откладываются;
- одна тема не размазывается на множество микровопросов.

## 7. Ответ «не знаю»

`UNKNOWN` является допустимым ответом. Harness обязан предложить:

1. reversible default;
2. последствия default;
3. owner unknown;
4. review trigger или срок пересмотра;
5. какие решения остаются отложенными;
6. может ли разработка продолжаться безопасно.

Пример:

```yaml
assumption:
  id: ASM-SCALE-001
  statement: "Первый релиз рассчитан до 1 000 активных пользователей в сутки"
  epistemic_status: ASSUMED
  owner_ref: ACT-PRODUCT-001
  impact_if_false: MEDIUM
  review_trigger: "Перед production launch или при уточнении capacity"
  reversible: true
```

## 8. Stop protocol

При material ambiguity agent обязан:

```text
1. Stop only the affected operation before unsafe side effects.
2. Preserve completed safe changes and evidence.
3. Record exact ambiguity and affected artifacts.
4. Return structured question/options/recommendation.
5. Mark task/request WAITING_DECISION.
6. Expose independent READY tasks.
7. Resume from stored checkpoint after answer.
```

Нельзя продолжать affected task «наиболее вероятным» способом без policy authorization.

## 9. Non-material defaults

Допустимый default должен быть:

- обратимым;
- локальным;
- соответствующим accepted style/policy;
- не расширяющим scope;
- не ослабляющим security/quality constraints;
- явно отмеченным в Task Report, если он не trivial.

```yaml
local_choice:
  statement: "Private helper размещён рядом с service implementation"
  basis_ref: PLC-CODE-STYLE-001
  reversible: true
```

## 10. Конфликты источников

Если documentation, user answer и current code расходятся:

- конфликт фиксируется как `CONFLICTING`;
- precedence применяется только там, где уже существует accepted policy;
- material semantic conflict требует reconciliation question/decision;
- code не считается автоматически источником истины;
- supplied documentation не считается автоматически current, пока не проверена revision/authority.

## 11. Examples

| Неоднозначность | Класс | Действие |
|---|---|---|
| Сколько пользователей ожидается? | Material для capacity, если влияет на architecture | Спросить или принять bounded assumption. |
| Как назвать private method? | Trivial | Style policy. |
| Offset или cursor pagination? | Material public contract | Decision question. |
| В какой папке разместить внутренний helper? | Non-material reversible | Default в pragmatic mode. |
| Можно ли отправлять данные во внешний model adapter? | Material security/data | Обязательное approval/policy. |

## 12. Критерии приёмки

1. Materiality оценивается до остановки.
2. Material ambiguity никогда не разрешается молча.
3. Non-material reversible choice не создаёт ненужный blocker в pragmatic mode.
4. Вопрос содержит объяснение, варианты, recommendation и `UNKNOWN` path.
5. Batch ограничен и не повторяет уже известные ответы.
6. Остановка затрагивает только зависимый scope.
7. Ответ создаёт event и пересчитывает readiness.
8. Assumptions имеют owner и review trigger.
