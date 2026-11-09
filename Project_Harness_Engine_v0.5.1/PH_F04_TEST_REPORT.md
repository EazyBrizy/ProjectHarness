# Project Harness v0.5.0 — отчёт по PH-F04

**Дата:** 24 октября 2026. **Статус:** PH-F04 реализован и проверен; PH-F05–PH-F08 не заявляются завершёнными.

## Исходная база и границы

Использованы последние входные `Project_Harness_Engine_v0.5.0 (4).zip`, `Project_Harness_Documentation_v0.5.0 (3).zip`, неизменная нормативная спецификация `02_Project_Harness_v0.5.0_Implementation_Levels.md`, ремедиационный план PH-F04. Код изменялся исключительно в `runtime.py`, `stages.py`, `validation.py`; остальные изменения — адресные tests, operator docs и derived distribution outputs.

## Закрытые пункты PH-F04

1. `next` и `stage-status` публикуют **существующую** команду/операцию: двухшаговый PH-F03 planner, Task/JIT, Gate review, Gate recovery, ordinary blocker recovery, persisted Gate-readiness recovery, terminal target (без невозможного level-up при accepted RELEASE) и separate same-level maintenance. Для критического safety block требуется явно описанное внешнее восстановление, а не несуществующая команда.
2. `validate-project` отклоняет artificial unreachable boundary, mismatched current Stage/Gate/Run/Task/projections, premature future-stage READY Task и неверные blocker bindings. Проверка CLI ориентируется на реальные subcommands, не на придуманные названия. Не считает само ожидание formal review дефектом.
3. Различаются runtime phases `STAGE_PLANNING_REQUIRED`, `READY`, `READY_FOR_CODEX`, `VERIFYING`, `STAGE_GATE_BLOCKED`, `TASK_BLOCKED`, `TARGET_LEVEL_REACHED`, `MAINTENANCE` и migrated maturity review. `next` после реального Run reservation возвращает следующий `verify`, а не устаревший `next`.
4. Stage-boundary `next` read-only; повторные `next` и `plan-active-stage` не дублируют Runs/Tasks; accepted history и последний baseline не переписываются. Следующая Stage исполняется только после formal acceptance/level-up и reviewed current-stage planning.

## Тестирование на финальных файлах

| Проверка | Команда / сценарий | Итог |
| --- | --- | --- |
| Полная регрессия, включая PH-F01–PH-F04, Stage transactions, semantic Gate, Brownfield, maintenance, v0.4.1 | `PYTHONPATH=src:. python tests/run_tests.py` | **149/149 PASS**, 0 failures/errors, 345.279 с |
| Адресные PH-F04, включая red-to-green post-reservation route | `PYTHONPATH=src:. python -m unittest -v tests.test_ph_f04_runtime_reachability` | **10/10 PASS** |
| Отдельное повторное тестирование ранее выявленных стыков | legacy v0.4.1 compatibility + accepted-stage maintenance (4 existing tests) | **4/4 PASS** |
| Установленный wheel | `pip wheel . --no-deps --no-build-isolation` → `pip install --no-deps --target <dir> <wheel>` | **PASS** |
| Публичный CLI установленного wheel на реальном Alpha boundary | `next → stage-status → validate-project → prepare-active-stage-plan → plan-active-stage → next → validate-project → plan-active-stage(replay) → next(replay)` | **PASS**; `STAGE_PLANNING_REQUIRED → STAGE_PLANNED → READY_FOR_CODEX`, accepted history byte-identical |
| Wheel doctor | `PYTHONPATH=<wheel-install> python -m project_harness doctor --skip-manifest` | **PASS** |
| Документационный validator | `python tools/validate_documentation.py . --build-aggregates` + repeat on final ZIP | **36/36 PASS**, 0 errors; archive check PASS |
| Engine source doctor + manifest | `python project-harness.py doctor --root <Engine-root>` | **PASS** |
| Source vs embedded docs, manifests, два ZIP | independently compare SHA-256 + `zipfile.testzip()` | **PASS** |

Лог 149 тестов сохранён внутри Engine ZIP: `PH_F04_TEST_LOG.txt`. Встроенная Documentation byte-identical отдельному Documentation ZIP (с точностью до содержимого файлов; неизменность истории проверялась на Project Instance). Сам тестовый набор учитывает новые 10 тестов, поэтому его размер вырос по сравнению с 139 у входного PH-F03.

## Исправленные регрессии и отдельно сохранённые требования

- Предотвращён false positive при валидной same-level maintenance на последнем accepted Stage, даже если следующий Stage уже находится в `PLAN_ACTIVE_STAGE`; не допускается произвольная Task с future `implementation_stage`.
- Legacy v0.4.1 без Stage State продолжает проходить compatibility validation до явной migration, без перезаписи файлов.
- Отдельный тест воспроизвёл неверный `next_operator_route` после нового Run reservation; теперь возвращается `verify` для persisted active Run.
- PH-F02 evidence не возникает из generic PASS, PH-F03 immutable reviewed planner не переписан; строгие approvals, exact refs, transaction journals/recovery, Brownfield read-only и accepted Stage history остались инвариантами.
- PH-F04 сознательно не добавляет Codex executor/sandbox, Git/PR/deploy, parallel runners или новые product capabilities; PH-F05–PH-F08 требуют отдельных этапов и финальной интеграционной приёмки.

**Итог:** PH-F04 закрывает runtime reachability/diagnostics и stage-fenced task continuation; это не самостоятельное решение о полном release GO всей v0.5.0.
