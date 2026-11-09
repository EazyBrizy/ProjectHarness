# PH-F06 — интеграционные правила зрелости, Brownfield и maintenance

**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Пакет исправлений:** PH-F06  
**Дата проверки:** 2026-10-24  
**Область:** интеграция существующих публичных операций; не новая версия lifecycle.

## 1. Последовательность и граница level-up

Путь нового проекта до принятого target MVP остаётся `PROTOTYPE → ALPHA → BETA → MVP`.
После каждого `accept-stage` создаётся отдельный immutable Stage Acceptance Report.
На промежуточной границе следующий шаг — `prepare-active-stage-plan`, затем
`plan-active-stage` с reviewed record, и обычные `next → verify → complete`.
Принятие стадии требует подходящих exact-baseline доказательств и отдельного
formal approval. Успешный тест продукта не заменяет доказательства других видов.

Новая операция `level-up` разрешена после завершённого текущего цикла:
`TARGET_LEVEL_REACHED` / `TARGET_ALREADY_REACHED`, без текущей Task/Run и open maintenance.
Она не является способом отменить недоделанную Stage или обойти Gate.
При accepted MVP и target RELEASE последовательность следующая:

```sh
project-harness level-up --project <root> --target RELEASE --approval <record>
project-harness prepare-active-stage-plan --project <root> --output <draft>
  # Оператор проверяет и заполняет существующий reviewed-plan contract.
project-harness plan-active-stage --project <root> --plan <reviewed-record>
project-harness next --project <root>
```

Ожидаемые границы: `STAGE_PLANNING_REQUIRED` / `PLAN_ACTIVE_STAGE`, затем
одна первая Release READY Task/JIT. Цель хранится в Stage State; PROJECT и
CURRENT_STATE — согласованные projections. Initial accepted input остаётся
исторической записью прежней цели MVP. Повтор уже committed identical decision
идемпотентен. Target не выше accepted highest даёт no-op/rejection, не downgrade.
Новая competing decision во время незавершённого цикла отклоняется.

## 2. Same-level maintenance

При accepted target оператор подаёт существующий strict maintenance plan:

```sh
project-harness start-maintenance --project <root> --plan <maintenance-record>
project-harness next --project <root>
  # Внешний исполнитель изменяет только разрешённые продуктовые paths.
project-harness verify --project <root> --allow-command-execution
project-harness complete --project <root> --result <agent-result>
```

Повторять Task cycle до `MAINTENANCE_COMPLETED`. После завершения восстанавливается
прежний boundary route; accepted maturity, canonical target, принятые reports
и completed Runs не переписываются. Тогда разрешён следующий level-up.
Конкурирующий maintenance plan, новый level-up, maturity assessment и Stage acceptance
при open maintenance отклоняются. Это включает `SATISFIED_BY_BASELINE`: baseline
acceptance не должна уничтожать текущий maintenance Run или молча supersede его Tasks.
Formal cancellation по существующему контракту остаётся отдельной операцией.

## 3. Supplied evidence без потери semantic proof

Публичная операция не изменилась:

```sh
project-harness assess-maturity --workspace <root> --evidence <supplied-evidence.json>
```

Файл содержит объект с массивом `evidence`. Для подготовленного Project Instance
элемент массива может быть **полным normalized evidence body** существующей
`SCHEMA-GATE-EVIDENCE@1`, то есть содержимым `verification_evidence`,
без этого внешнего envelope. `schema_version: 1` выбирает normalized contract.
Необходимо передать реальные `id`/`ref`, `kind`, `status`, `provenance`,
`base_revision`, subject mappings, `source_bindings`, `created_at` и соответствующий
`details.semantic_proof`; поля и разрешённые виды остаются в существующей schema
и Implementation Level Registry. Новая schema и новая CLI-команда не вводились.

Фактические operator sources помещаются в предусмотренный `.harness/operator/SOURCES/`;
их refs, paths и SHA-256 передаются в `source_bindings`. Import record/approval
рекомендуется держать вне Project Instance. **Оператор не пишет canonical evidence,
Stage State, Gate, indices или Runs вручную**: canonical `.harness/evidence/<id>.yaml`
создаёт Engine после валидации предоставленного тела.

Для normalized positive evidence Engine сохраняет исходные provenance,
source bindings и semantic proof, проверяет schema, каждый source digest и
совместимость доказательства с каждым указанным subject. Неподходящий generic
PASS не принимается. Existing id нельзя перезаписать другим содержимым;
повтор идентичного normalized evidence не меняет его bytes. `NOT_APPLICABLE`
требует rationale и validator, а применимость дополнительно проверяется Gate.

Весь набор normalized entries проверяется до их импорта. Legacy assessment
records по прежнему формату читаются совместимо, но из них не выдумывается
Gate-eligible proof. Не смешивайте непроверенные legacy записи с normalized
пакетом ради обхода семантической проверки. Normalized source resolution
требует подготовленного Project Instance, а не внешнего intake workspace.

При несовпадении `base_revision` с текущим product digest исходное immutable
normalized evidence не переписывается. Его assessment-представление становится
`UNKNOWN` / stale, а assessment — `STALE`; это не основание для acceptance.
Сам `assess-maturity` не запускает repository commands, не меняет product tree
и accepted maturity. Проверки для supplied test evidence заранее выполняет
внешний исполнитель; assessor только читает предоставленные источники.

## 4. Продолжение после assessment и baseline approval

Read-only здесь означает отсутствие продуктовых изменений и автоматического
исполнения, а не отсутствие служебного assessment artifact. В Project Instance
пишутся новая immutable revision assessment и наблюдаемые поля Stage State.
Если заранее зарезервированный Run имеет чистый control-plane snapshot,
Engine фиксирует узкую trusted phase для собственных assessment/evidence writes.
Этот Run можно продолжить через `verify → complete`; completed Runs не меняются.
Предшествующее вмешательство в control-plane не становится доверенным: assessment
не исправляет и не скрывает его, `verify` продолжает блокировать такое выполнение.
Поступление новых operator sources во время уже зарезервированного Run само по себе
не является разрешением менять его защищённый snapshot; подготовьте источники
на соответствующей operator/Gate границе.

Для Brownfield baseline acceptance нужен отдельный formal approval с точными
`assessment_ref` вида `id@revision`, digest assessment, product baseline и current
maturity context. Последовательные satisfying levels могут быть приняты одной
governed baseline операцией только с **отдельными reports для каждой стадии**.
Неизменная claimed maturity пользователя, observed candidate и accepted maturity
остаются различными величинами. Надпись `beta` в README и наличие tests directory
не заменяют фактическое execution evidence. После acceptance следующая активная
стадия планируется обычными публичными командами.

## 5. Граница подтверждения

Автоматизированный PH-F06 fixture — ограниченный локальный single-user task CLI.
Он действительно выполняет Task cycle и предметные продуктовые тесты, использует
supplied документы и явного тестового оператора для formal review. Это проверка
lifecycle движка, **не сертификация production/security/compliance другого продукта**.
Реальные операторы сохраняют ответственность за семантическую достаточность evidence.

Нормативная спецификация v0.5.0, registry, schemas, transaction recovery protocol,
exact assessment resolver и maintenance implementation не изменены. PH-F07 и
финальный release gate PH-F08 этим пакетом не объявляются выполненными.
