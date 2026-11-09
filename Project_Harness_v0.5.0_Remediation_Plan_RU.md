# Project Harness v0.5.0 — план завершения функционала создания и развития проектов

**Основание:** повторное изучение `Project_Harness_Engine_v0.5.0.zip`, `Project_Harness_Documentation_v0.5.0.zip`, нормативной спецификации `02_Project_Harness_v0.5.0_Implementation_Levels.md` из архива спецификаций и выводов предыдущего интеграционного аудита.

**Статус:** предлагаемый implementation/remediation plan, **не отчёт о выполненных исправлениях**. Обозначения `PH-F01`–`PH-F08` — локальные идентификаторы работ этого плана, не новые нормативные issue IDs.

**Цель:** сделать исполнимым без тупиков публичный процесс `intake → approvals → prepare → handoff → Task/JIT → verify/complete → Stage Gate → next active Stage → target reached → level-up`, а также сохранить проверенные маршруты Brownfield и same-level maintenance.

## 1. Зафиксированные исходные факты

1. `start-intake`, `check-intake`, `prepare`, `validate-handoff`, `next`, `verify`, `complete`, `prepare-stage-approval`, `accept-stage`, `level-up`, `assess-maturity`, `start-maintenance`, `cancel-maintenance` присутствуют в публичном CLI.
2. По результатам независимого аудита целостность архивов, документационный validator и 117 тестов проходили; независимый Greenfield проект прошёл intake, handoff и две Prototype Task.
3. После `accept-stage` промежуточной стадии или `level-up` runtime выставляет `PLAN_ACTIVE_STAGE`/`STAGE_PLANNING_REQUIRED`, но в `cli.py` отсутствует публичная операция обработки этого маршрута. `planner.py` содержит `normalize_plan()` только для начального активного `PROTOTYPE`.
4. `stage_gate_lifecycle.materialize_preparation_task_evidence()` создаёт нормализованные `PASS` evidence из общего PASS verification report для разнородных mandatory subjects; у preparation Task могут быть `expected_paths: []` и `manual_checks: []`. Формальная проверка digest, kind и provenance не равна семантическому доказательству необходимого результата.
5. `validate-project` считает boundary route `PLAN_ACTIVE_STAGE` допустимым даже в поставке без вызываемого CLI/API действия; требуется end-to-end reachability и корректная диагностика.
6. Template `GPT_PREPARATION_INSTRUCTIONS.md` уже задаёт порядок опроса и 4/5 отдельные approvals. Не нужно заменять GPT-опрос новым движком естественного языка.

## 2. Непереговорные ограничения

- Рабочая цель — завершить **v0.5.0**, не реализовывать механизмы v0.5.1/v0.6.x.
- GPT — семантический интервьюер, анализирует источники и готовит строго валидный `PROJECT_INPUT@3`; Engine — детерминированный compiler/runtime/governance; внешний агент исполняет продуктовые Tasks.
- Canonical уровни: `PROTOTYPE → ALPHA → BETA → MVP → RELEASE`, без перескоков и неявного downgrade.
- Target изменяет глубину и проверяемость, **не расширяет** `accepted_project_scope`.
- Детальный DAG, Context/Prompt Plans и JIT генерируются **только для активной стадии**.
- Stage approval и level-up требуют формального подтверждения; `UNSURE` не превращается в canonical target автоматически.
- Stage State — единственный canonical current-cycle target у подготовленного Project Instance. Immutable input, Acceptance Reports и completed Runs не переписывать.
- Нельзя считать `PASS` универсальной verification task доказательством архитектуры, юридического соответствия, security, permitted use, внешнего требования и т.п.
- Crash recovery и idempotency обязательны для stage-mutating routes.

## 3. Очерёдность самостоятельных пакетов исправлений

### PH-F01 — Базовые регрессионные воспроизведения и матрица (P0, без нового функционала)

**Граница:** fixtures и tests, без изменения semantics.

- Зафиксировать независимый Greenfield fixture с target `MVP`, отдельный Brownfield fixture, accepted `PROTOTYPE` fixture и `TARGET_LEVEL_REACHED` fixture.
- Добавить red regression для `accept Prototype → PLAN_ACTIVE_STAGE → first Alpha READY JIT` и `level-up MVP → RELEASE → first Release READY JIT`.
- Добавить red regression для `no-change PASS verification → fabricated ARCHITECTURE_RECORD/LIMITATIONS_RECORD/PERMITTED_USE_RECORD/EXTERNAL_EVIDENCE`.
- Проверить реальные статусы CLI/API, а не только наличие артефактов.
- Зафиксировать контрольную матрицу существующих B-01/B-02/B-03/B-04/G-01/L-01/M-01/U-01/Q-01/Q-02/Q-03/Q-04, с явной пометкой что семантический дефект evidence найден дополнительно к прежней формальной проверке G-01.

**Критерий:** два дефекта воспроизводятся тестами; остальные текущие тесты остаются зелёными. Это разрешённый промежуточный red stage, **не финальный релиз**.

### PH-F02 — Семантическая достоверность Gate evidence (P0)

**Области:** `stage_gate_lifecycle.py`, `evidence.py`, `stages.py` и только необходимые schema/registry/doc/test изменения.

- Для каждого missing Gate subject вычислять допустимые kinds и **способ доказательства**: выполняемый тест, реальный product/document artifact, формальная проверка оператора, внешнее evidence.
- Отменить безусловное клонирование одного PASS verification report в evidence любых kinds. `materialize_preparation_task_evidence()` создаёт PASS только для явно проверенного subject, при соответствии semantic kind, source, coverage и baseline.
- Для `TEST_REPORT`/`MANUAL_VERIFICATION` сохранять ссылку на конкретный тест/проверку, фактический PASS и проверяемый предмет; просто «py_compile + pytest» недостаточно для других subjects.
- Для архитектуры, инструкций запуска, ограничений, permitted-use и иных документных kinds брать конкретные наличные artifacts (проверять path, digest и минимальный соответствующий contract), а не общий Test Report.
- Для `EXTERNAL_EVIDENCE` требовать настоящий supplied source с достоверным provenance и корректными subject bindings. Отсутствие источника остаётся gap/UNKNOWN.
- `STAGE_ACCEPTANCE_PREPARATION` создаёт bounded Tasks на недостающие доказательства; при невозможности доказать item оставляет `UNKNOWN/BLOCKED` с recovery, а не ложный `PASS`. Предотвращать бесконечное создание одинаковых tasks.
- `accept-stage` перепроверяет evidence не только по schema/digest/kind/subject, но и по contract-совместимости доказательства с видом проверяемого результата. Human validation остаётся обязательной там, где автоматическая достаточность недоказуема.
- Сохранить strict positive-only, exact ref, final-baseline, tamper protection и `NOT_APPLICABLE` applicability checks.

**Негативные тесты:** no-op PASS report не закрывает `ARCHITECTURE_RECORD`, `LIMITATIONS_RECORD`, `PERMITTED_USE_RECORD`, `EXTERNAL_EVIDENCE`; пользовательская декларация/неподходящий source не закрывает mandatory result; изменение source или product baseline блокирует acceptance.

**Позитивный тест:** Gate preparation с фактически полученными и подходящими proof artifacts завершается `VERIFYING`, draft approval содержит точные candidates, formal approval принимает Stage.

### PH-F03 — Публичный governed planner следующей active Stage (P0, B-01/Q-04)

**Области:** `planner.py`, `stages.py`, `compiler.py` (только переиспользуемая логика компиляции), `stage_transactions.py`, индексы/tasks/plans, CLI/API, тесты и docs.

**Предлагаемый публичный интерфейс** (имена рабочие; зафиксировать их в документации и тестах):

```sh
project-harness prepare-active-stage-plan --project <root> --output <record>
project-harness plan-active-stage --project <root> --plan <reviewed-record>
```

Read-only preparation возвращает draft точного current context и не принимает решения. Если material change отсутствует, по действующему контракту не нужно добавлять искусственное независимое formal approval; если material change есть, explicit review/approval и exact binding обязательны. Governed application никогда не выходит за accepted product scope.

**Preconditions:**

- current Stage State указывает на ближайший stage после `highest_accepted_level`; target и immutable acceptance history согласованы;
- имеется exact последний accepted Stage baseline/report и, если применимо, подтверждённый governed maintenance context;
- accepted scope/constraints и next-stage gaps фиксированы; текущий product tree digest проверен;
- нет active Run, незавершённого Stage Gate, несовместимой maintenance/Stage transaction или stale record;
- submitted reviewed plan exact-bound к revision Stage State, active Stage Plan/Gate, accepted baseline, canonical target, current product tree digest и scope.

**Application:**

1. Из last Stage Acceptance (`next_stage_gaps`, permitted use, limitations), accepted requirements, registry/profile controls и текущего product tree вычислить **дельту текущей стадии**.
2. При material divergence от ранее согласованного scope не применять автоматически; запросить governing decision существующего класса изменения.
3. Выпустить новую active Stage Plan revision (не переписывать историю) и синхронную Gate revision с exact outcome/criteria/profile/hard constraint/WP bindings.
4. Построить исполнимые Work Packages, atomic Tasks, dependencies/DAG, Verification Profiles, Context Plans, Prompt Plans **для текущей** стадии. Детализированные future-stage Tasks запрещены.
5. Обновить Task/WP indexes, `CURRENT_STATE`, `NEXT_TASK`, `stage-status`, projections и canonical route в одной crash-consistent transaction с durable journal/backups.
6. Сформировать один first READY JIT bundle; повтор той же команды идемпотентен; изменившийся product/Stage baseline делает draft stale и блокирует mutation.
7. Зафиксировать способ восстановления при interruption и reject конкурирующих решений.

**Приёмка:** после `accept-stage(PROTOTYPE)` для target MVP `plan-active-stage` даёт первую Alpha READY Task; после `level-up` с accepted MVP и target RELEASE — первую Release READY Task. Предыдущие reports, Runs, evidence и historical stage plans неизменны.

### PH-F04 — Runtime reachability, status и invariant validation (P1)

**Области:** `runtime.py`, `validation.py`, `stages.py`, `cli.py`, точечные tests.

- `next` и `stage-status` указывают фактически исполнимую следующую команду/операцию, без `command: null` для нужного `PLAN_ACTIVE_STAGE`.
- `validate-project` проверяет, что route на boundary status реализован и его data contracts самосогласованны. Ожидание explicit user review не считать ошибкой само по себе; отсутствие исполнимого continuation route — defect.
- Строго различать `STAGE_PLANNING_REQUIRED`, `READY`, `VERIFYING`, Gate-related `BLOCKED`, ordinary task `BLOCKED`, `TARGET_LEVEL_REACHED` и maintenance.
- Повторный `next`, повторный `plan-active-stage`, stale approval, прерывание до/после commit, восстановление транзакции — без дублирования задач, смешения Stage/Gate revision и мутации accepted history.
- Запретить запуск future-stage Tasks до успешного stage transition.

**Приёмка:** любой разрешённый неконечный persisted status имеет ясный CLI/API continuation или явно описанный внешний prerequisite, а валидаторы находят искусственный тупик.

### PH-F05 — Полная приёмка семантического опроса и создания Project Instance (P1)

**Области:** `intake.py`, `project_input.py`, GPT preparation template, docs/tests; менять код только при найденном дефекте.

- Проверить опрос **с документацией** и **без готовой документации**: первый вопрос о документации, source inventory, core outcome, затем target до Architecture/Technology.
- Проверить `UNSURE → WAITING_DECISION` и осознанное подтверждение target; `UNKNOWN` sensitivity и material unknowns → `WAITING_INPUT`.
- Подтвердить, что GPT не спрашивает доказанные исходными документами факты повторно, не смешивает claim/observed/accepted, не принимает обычный ответ за formal approval.
- Убедиться, что Greenfield требует 4 отдельных approvals, Brownfield/Hybrid — 5; readiness не пропускает неутверждённую архитектуру/technology/handoff.
- Проверить `start-intake → check-intake` при повторном изменении ответов, конфликтах документов, пустом источнике, path safety, повторных вызовах.
- `prepare` принимает только strict approved PROJECT_INPUT; handoff включает Stage outlines до target, detailed Tasks только для active stage, валидные forbidden/write/verification scopes и exactly one first READY JIT.
- Проверить работу через установленный wheel и через bundled entrypoint; исправить фактические ошибки в instructions/CLI responses.

**Приёмка:** два независимых Greenfield fixtures (минимальные документы и полноценные документы) превращаются из `WAITING_INPUT` в `READY_FOR_CODEX` и проходят `validate-handoff`; незаконные approvals и неверные targets отвергаются.

### PH-F06 — Повышение зрелости, Brownfield и maintenance end-to-end (P1)

**Области:** только интеграционные связки `stages.py`, `maintenance.py`, `runtime.py`, test fixtures, docs; не переписывать работающие B-02/B-03/B-04/L-01/M-01.

- `PROTOTYPE → ALPHA → BETA → MVP` с отдельными immutable Stage Acceptance Reports, verified gating и active-stage planner на каждой границе.
- `TARGET_LEVEL_REACHED → level-up(target RELEASE) → PLAN_ACTIVE_STAGE → first Release READY JIT`, с canonical target в Stage State и согласованными projections.
- `level-up` при target ≤ accepted highest возвращает no-op/rejection без исторических изменений; попытка skip Stage отклоняется; replay идемпотентен.
- `MAINTAIN_CURRENT_STAGE` в accepted target: выполнять `next → verify → complete`; не повышать maturity; допускается level-up после корректного завершения maintenance.
- Brownfield read-only assessment с exact revision/digest и current context; `SATISFIED_BY_BASELINE` только на подтверждённом evidence и отдельном formal baseline approval; принимать только последовательно, с отдельными reports.
- Проверить negative tests stale assessment, fake `README beta`, missing execution evidence, concurrent maintenance, migration historical Runs.

**Приёмка:** все 3 сценария (новый проект, existing project, повторный level-up) завершаются публичными командами без private Python и ручного редактирования control-plane.

### PH-F07 — Operator документация и примеры (P1)

**Области:** README, MANUAL_INSTALL, GPT preparation template, Stage/Gate/Planning/Execution sections, migration notes, examples; только реально имеющиеся interfaces.

- Упорядочить единый runbook: запуск engine/doctor → source/опрос → approvals → prepare → external Codex cycle → Stage Gate → stage planning → target reached → level-up/maintenance.
- Для новых public route фиксировать CLI flags, accepted input/draft schema, exact fields, location of operator records, next expected status, reject/recovery outcomes.
- Согласовать `pytest` instructions: установка wheel или `PYTHONPATH=src`, либо поддерживаемый `tests/run_tests.py`; не публиковать команду, не работающую из чистого извлечённого source tree.
- Удалить ложное обещание, что valid handoff означает автоматическое создание production-кода и что verification report доказывает любой evidence kind.
- Документировать человеческую responsibility за semantic Gate approval и ограничения без OS sandbox.
- Сохранить версию и нормативные boundaries; не переписывать историю документации как будто старые процедуры всегда существовали.

**Приёмка:** внешний оператор без знания private Python выполняет все поддерживаемые шаги по документации; команды прошли smoke test именно в их опубликованном виде.

### PH-F08 — Финальная интеграционная приёмка и сборка (P0 release gate)

**Сценарии:**

| ID | End-to-end сценарий | Ожидаемый итог |
|---|---|---|
| I-01 | Greenfield минимальные исходные данные → уточнения/approvals → prepare | READY_FOR_CODEX, valid ZIP, 1 first JIT |
| I-02 | Greenfield target MVP, полный путь 4 стадий | accepted MVP, TARGET_LEVEL_REACHED |
| I-03 | Prototype acceptance → Alpha planning | first Alpha READY Task, no duplicate/missing plan |
| I-04 | Accepted MVP → level-up RELEASE → planning | first Release READY Task, old target remains historical |
| I-05 | No-op PASS Gate preparation без соответствующих источников | Gate остаётся unclosed; ложные kinds не materialized |
| I-06 | Реальные proof artifacts + formal Stage approval | Gate ACCEPTED с exact validated evidence |
| I-07 | Структурно valid review c UNKNOWN/FAIL | BLOCKED → recovery → revalidation |
| I-08 | Tampered/stale/dangling/wrong-kind evidence | rejection before acceptance mutation |
| I-09 | Brownfield assessment → baseline approval | accepted only satisfying levels, assessment remains read-only |
| I-10 | Maintenance после accepted level → complete → level-up | history immutable; correct resumed route |
| I-11 | Crash interruption во время stage planning/accept/level-up | deterministic recovery old or new, no mixed state |
| I-12 | Repeated commands / duplicate approvals / stale plan | no duplicate Runs/WPs/reports; conflict safely rejected |
| I-13 | Migration v0.4.1 + restart | immutable history and correct Stage State |
| I-14 | Fresh installation and distribution smoke | wheel/CLI, doctor, doc validator, handoff/project validation PASS |

**Release criteria:**

1. Все существующие 117 тестов (если они присутствуют в базовой поставке) и добавленные regression/e2e tests проходят на **финальных** файлах, без демонстрационных заглушек и фиктивного повышения maturity.
2. Нет `PLAN_ACTIVE_STAGE` dead end для допустимого active Stage; Alpha/Beta/MVP/Release могут получать задачи после предыдущего формального acceptance.
3. Ни один Gate не принимается на основании универсально переклеенного PASS report; каждый mandatory result имеет надлежащее доказательство или остаётся незакрытым.
4. Strict approval, exact canonical refs, baseline/digest, idempotency, crash recovery, accepted history, stage fence, Brownfield read-only semantics сохраняются.
5. Docs describe tested commands. `doctor`, installed wheel, both validators и sha256 manifest — PASS.
6. Архивы Engine и Documentation пересобраны с согласованными версиями и инструкциями, сопровождаются тестовым отчётом с реальными командами/результатами и описанием исправленных defects.

## 4. Правила работы над пакетами

1. **Каждый PH-Fxx выполнять в отдельном диалоге** на основе последних успешно собранных архивов Engine + Documentation и неизменной normative specification v0.5.0.
2. На входе: актуальные два ZIP, specification, точная область конкретного PH-Fxx и её тесты. Не переносить код из непроверенных промежуточных рабочих деревьев.
3. На выходе **каждого** шага: обновлённый `Project_Harness_Engine_v0.5.0.zip`, обновлённый `Project_Harness_Documentation_v0.5.0.zip`, короткий changelog, test report, список сохранённых ограничений.
4. Изменять только файлы, требуемые шагом. Правки соседних областей допускаются лишь для прямого regression caused by patch.
5. Любая новая CLI-команда обязана быть публичной, документированной, проверенной на реальном Project Instance, имеющей Python API и status/next-route semantics.
6. Если тест фиксирует новую проблему вне назначенной области — зарегистрировать как отдельное замечание; не расширять локальный scope без явного решения.

**Рекомендуемый порядок:** PH-F01 → PH-F02 → PH-F03 → PH-F04 → PH-F05 → PH-F06 → PH-F07 → PH-F08.

## 5. Что сознательно отложено

Автоматический локальный Codex Executor и rootless sandbox (`v0.5.1`), Git/PR/deployment (`v0.6.0`), declarative skill authoring (`v0.6.1`) и remote control plane — отдельные версии. Их отсутствие **не блокирует** v0.5.0 как управляемый preparation+governance runtime с внешним исполнителем.

## 6. Решение о готовности

**GO для функциональной v0.5.0** только после PH-F08, когда Greenfield и level-up последовательно переходят по всем запрошенным стадиям через публичный CLI/API, Stage Gate опирается на реальные evidence, а ни один промежуточный route не застревает в недоступном состоянии. Успешный `doctor`, положительное количество unit tests или валидный handoff без сквозного сценария для этого недостаточны.
