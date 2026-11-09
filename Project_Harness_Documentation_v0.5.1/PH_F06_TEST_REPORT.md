# PH-F06 — отчёт о реализации и интеграционных тестах

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Дата выполнения этого пакета:** 2026-10-24  
**Статус:** PH-F06 PASS; не финальный release gate PH-F08.

Дата 2026-08-18 выше — обязательная metadata документационного комплекта v0.5.0;
фактический прогон и исправления этого пакета выполнены 2026-10-24.

## 1. Зафиксированная входная база

Использованы последние архивы с PH-F01–PH-F05, а не ранние одноимённые поставки:

| Входной артефакт | SHA-256 |
|---|---|
| `Project_Harness_Engine_v0.5.0 (6).zip` | `218862b49294452306e9d1a6cbc66d19a40aa19d974bb049428327421887fd79` |
| `Project_Harness_Documentation_v0.5.0 (5).zip` | `9d98d5254bfdef728fe7d35cce0941f0f9d0e3389396343da5551922f4a92e69` |
| `Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0.zip` | `56bca615b7da5a0f48d0479c2de24ccd151fcefbf453fdfea89eab0d2675219e` |

Основание: раздел PH-F06 приложенного remediation plan и нормативная
`02_Project_Harness_v0.5.0_Implementation_Levels.md`, прежде всего разделы
14–16, 18, 21–23. Нормативная спецификация, version, registry и schemas не менялись.
Входной отчёт PH-F05 честно указывал незавершённый полный прогон. Здесь он выполнен
независимо: **исходные 153 теста прошли до изменения runtime**.

## 2. Исправленные интеграционные дефекты

### 2.1. Потеря semantic proof при публичном Brownfield evidence import

Ранее `assess-maturity --evidence` повторно оборачивал уже нормализованные records,
теряя `details.semantic_proof` и конкретные source bindings. Assessment мог показать
satisfying candidate, но последующий formal Gate не принимал такое доказательство.

Теперь полный existing normalized body импортируется без изменения provenance,
semantic proof, kind и bindings. До импорта normalized набора проверяются schema,
source paths/digests, subject compatibility, duplicate/conflicting immutable ids,
а для `NOT_APPLICABLE` — rationale и validator. Подмена позднего элемента набора
не оставляет ранее импортированных normalized artifacts. Legacy формат остаётся
совместимо читаемым, но не получает выдуманного semantic proof.
Stale input не переписывает immutable факт: только assessment-представление получает
`UNKNOWN`/stale. Gate по-прежнему обязан проверить exact final baseline.

### 2.2. Read-only assessment блокировал уже зарезервированный Run

Служебные assessment/observed-state writes считались незаявленным вмешательством
агента, и штатный `verify` возвращал `BLOCKED / SAFETY_VIOLATION` без исполнения.
Теперь **только при исходно чистом control-plane** фиксируется узкая trusted phase
для собственных assessment/evidence writes. Product tree, active Run identity,
completed Runs и accepted maturity не меняются. Предшествующее повреждение
control-plane не легализуется; неожиданные writes и изменение продукта во время
assessment не получают доверенный boundary.

### 2.3. Baseline acceptance обходил открытый maintenance

`SATISFIED_BY_BASELINE` мог принять следующую стадию, пока same-level maintenance
ещё имел открытые Tasks/Run. Добавлен отказ Stage acceptance и assessment при
open maintenance. Переход не может сбросить текущую maintenance работу.
Реализация maintenance и её transaction protocol не переписывались.

### 2.4. Новый level-up сбрасывал незавершённый текущий цикл

Новая formal decision могла заменить target, пока ранее выбранный MVP ещё
не принят. Теперь новый level-up требует accepted current target и idle boundary
`TARGET_LEVEL_REACHED / TARGET_ALREADY_REACHED`, без текущей Task/Run.
Exact committed replay остаётся идемпотентным; lower/equal target по-прежнему
no-op/rejection без изменения истории. Следующая active Stage всегда ближайшая.

Все четыре дефекта проверены также на оригинальном source-коде из входного ZIP:
два Brownfield regression tests дают ожидаемый FAIL; оригинальные level-up и
baseline acceptance принимают запрещённые переходы, которые новая версия
отклоняет без мутации. В release включены чистые подтверждающие логи, а не
промежуточные неудачи разработки тестовых fixtures.

## 3. Приёмочная матрица PH-F06

| Сценарий | Проверенный результат |
|---|---|
| Новый Greenfield target MVP | Реальный `intake → prepare → next/verify/complete`; четыре принятые стадии PROTOTYPE, ALPHA, BETA, MVP; отдельные immutable reports; target reached |
| Planner на каждой границе | Public preparation/review/application; первая READY JIT только текущей стадии; stage-bound verification и formal acceptance |
| Maintenance после MVP | Две исполняемые Tasks через публичный cycle; завершение без изменения bytes Stage State/accepted maturity; старые reports, plans, evidence, completed Runs сохранены |
| Повторный цикл после maintenance | `level-up RELEASE → PLAN_ACTIVE_STAGE → first Release READY JIT`; Stage State и PROJECT/CURRENT_STATE согласованы; initial accepted input сохраняет MVP |
| Повторы и незаконные переходы | Exact replay без дубликатов; lower/equal target без исторических изменений; executed-stage skip и competing/new level-up до завершения цикла отклоняются |
| Brownfield | Реальные supplied subject proofs; read-only assessment; отдельное formal baseline approval; последовательные PROTOTYPE и ALPHA с двумя reports; далее public Beta planner/READY JIT |
| Stale/fake/missing evidence | README «beta» не подтверждает зрелость; без execution proof обязательный результат UNKNOWN; changed tree/assessment digest/source digest/generic PASS/необоснованный N/A не принимаются |
| Concurrent maintenance | Второй несовместимый maintenance и level-up блокируются; baseline acceptance и assessment не обходят открытый maintenance |
| Assessment continuation | Повторный чистый assessment сохраняет usable reserved Run; verify/complete работают; искусственная prior control-plane tamper остаётся BLOCKED |
| Migration | Настоящий bundled legacy v0.4.1 completed-handoff fixture; public migration/restart/validation; historical completed Runs побайтно сохранены; повтор migration — NO_ACTION |

Positive lifecycle fixtures не редактируют Stage State, Gate, Task indices,
Acceptance Reports или Runs вручную и не вызывают private Python функции движка.
Operator records и реальные продуктовые изменения выполняет внешний test driver;
все governance transitions идут через публичный CLI parser/entrypoint. В отдельном
negative test control-plane намеренно повреждается для проверки fail-closed behavior.

## 4. Реальные прогоны

Среда: Linux, Python 3.13. Runtime/fixture код не подменялся mock success.

| Прогон | Команда / метод | Результат |
|---|---|---|
| Входная регрессия, до runtime patch | `python tests/run_tests.py` | **153/153 PASS**, 428.889 s |
| Новые сценарии из source | `PYTHONPATH=src:. python -m unittest tests.test_ph_f06_maturity_lifecycle -v` | **13/13 PASS**, 243.957 s |
| Полный набор после patch | `python tests/run_tests.py` | **166/166 PASS**, 668.610 s, failures=0, errors=0 |
| Сборка wheel | `python -m pip wheel . --no-deps --no-build-isolation -w dist` | PASS |
| Изолированный wheel | Установка в новый venv с `--no-index --no-deps`; затем тот же PH-F06 module | **13/13 PASS**, 167.628 s |
| Реальные дочерние CLI processes | Installed `project-harness demo`, `validate-handoff`; bundled `next`, `assess-maturity`, `verify`, `complete`, `stage-status`; installed `validate-project` | **8/8 commands PASS**, успешное продолжение после assessment |
| Installed wheel doctor | `project-harness doctor` из venv | PASS |
| Source/bundled distribution doctor | Проверка final извлечённого Engine ZIP, включая SHA-256 manifest | **6/6 checks PASS** |
| Documentation validator | Final standalone ZIP, generated aggregates, index и manifest | **36/36 checks PASS**, errors=0, warnings=0 |
| Final archive integrity | ZIP CRC обоих архивов, SHA-256 manifests, embedded/standalone docs, source/build/wheel equality | PASS |

Каждый из двух отдельных 13-test прогонов записал **274 публичных CLI invocations**,
включая проверки ожидаемых отказов. Это не 274 отдельных unit tests и не число
принятых стадий. Wheel действительно загружался из `site-packages`, без `src` в
PYTHONPATH; использовались packaged resources. Полный 166-test suite выполнен
на source; отдельный 13-test PH-F06 suite выполнен и на source, и на wheel.

В Engine: `PH_F06_LOGS/` содержит baseline, полный и два targeted лога,
CLI JSONL traces, wheel build/install/doctor и process smoke transcript.
Результаты документационного validator и финальной archive/manifest проверки
повторно подтверждены на извлечённых final ZIP. `PACKAGE_VALIDATION.json` рядом
с двумя выходными ZIP содержит machine-readable итог; `SHA256SUMS.txt` — их
контрольные суммы. Final validation не опирается только на рабочее дерево.

Для повторения installed-wheel сценариев из корня Engine:

```sh
ENGINE_ROOT="$PWD"
python -m venv ../phf06-venv
../phf06-venv/bin/python -m pip install --no-index --no-deps dist/project_harness_engine-0.5.0-py3-none-any.whl
PYTHONPATH="$ENGINE_ROOT" ../phf06-venv/bin/python -m unittest tests.test_ph_f06_maturity_lifecycle -v
```

Тесты, а не пользователь, формируют synthetic formal approvals. В рабочем проекте
эти approvals должен явно подтвердить уполномоченный человек.

## 5. Сохранение предыдущих исправлений

Полный suite включает существующие tests для B-02 crash/recovery, B-03 assessment
freshness/current context, B-04 exact revision resolution, L-01 canonical target,
M-01 maintenance start/complete/cancel, G-01 evidence and full Gate contract,
U-01 approval preparation, Q-01/Q-02 readiness/BLOCKED/recovery, Q-03 strict formal
schema, B-01/Q-04 active-stage planner и PH-F01–PH-F05.

Сравнение с входным ZIP показывает: **единственный изменённый production module —
`src/project_harness/stages.py`**. `stage_transactions.py`, `maintenance.py`,
`runtime.py`, `evidence.py`, planner, validation, intake, schemas и registries
не изменены. Existing tests не удалены, не ослаблены и не пропущены. Source,
`build/lib` и wheel содержат одинаковые bytes `stages.py`:
`sha256:aeb26fba405f36b58978e29600c35564a5a40b8342e720d7b28dbf238b9cf007`.

Wheel: `project_harness_engine-0.5.0-py3-none-any.whl`, SHA-256
`ec3c578623f71366d7d53fd12bbec43b58932113c0d1247e8bfe5bb13a9760b5`.

## 6. Документация и упаковка

Добавлены ограниченные integration notes и этот отчёт; общая переработка runbook
PH-F07 не выполнялась. Входной Documentation validator независимо обнаружил
пять packaging errors: отсутствующая metadata PH-F05 report, local remediation
label ошибочно распознавался как canonical entity ID, stale full aggregate/index
и отсутствующий/устаревший manifest entries. Выполнены только механические
поправки: обязательная metadata без изменения прежних результатов, написание
локальной метки в heading как `PH_F05`, регенерация агрегатов/индекса/manifest.
Ранее отсутствовавший в embedded docs PH-F05 report включён из актуального
standalone Documentation. Нормативный смысл intake не менялся.

Отдельный Documentation ZIP и embedded documentation tree в Engine синхронизированы.
Исторические core reports остаются историческими; они не заменяются заявлениями,
что новые исправления существовали в прежних поставках. Детальный перечень
изменённых/добавленных файлов находится в `PH_F06_CHANGED_FILES.md`.

## 7. Ограничения и итог

PH-F06 завершён для трёх требуемых маршрутов: новый проект, existing project,
повторный уровень после завершённого target/maintenance. Release в этом этапе
доходит до **первой READY Task/JIT**, а не заявляется уже принятым RELEASE.

Положительный fixture — узкий локальный single-user task CLI. Продуктовые тесты
фактически выполняются: core flow, persistence, ошибки/диагностика, backup/restore,
compatibility, локальная установка, ограниченная performance baseline и declared
regression. Документные/operator evidence явно привязаны к этому тестовому scope.
Это проверка machinery и governance integration, **не сертификация production,
security, юридического соответствия или реального внешнего продукта**.
Semantic sufficiency остаётся ответственностью human reviewer.

Read-only assessor не запускает commands и не изменяет product tree; допустимые
служебные assessment/observed-state records не следует путать с product mutation.
Новых executor/sandbox/Git/PR/deployment, parallelism или механизмов v0.5.1/v0.6.x
не добавлено. PH-F07 и финальный GO/NO-GO этап PH-F08 остаются отдельными работами.
