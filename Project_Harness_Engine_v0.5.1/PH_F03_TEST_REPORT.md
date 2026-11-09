# Project Harness v0.5.0 — отчёт по PH-F03

**Статус:** выполнен точечный PH-F03; **не** заявляется выполнение PH-F04–PH-F08 и не выдается финальный GO v0.5.0 до PH-F08.
**Основа:** Engine `(3)` / Documentation `(2)` после PH-F02; нормативная `02_Project_Harness_v0.5.0_Implementation_Levels.md`; remediation plan, раздел PH-F03.
**Scope:** только `PLAN_ACTIVE_STAGE` после промежуточного `accept-stage`/`level-up`, точное binding и компиляция детального плана **текущей** стадии.

## Что проверено

1. `PROTOTYPE` принят, target `MVP` → статус `STAGE_PLANNING_REQUIRED`, read-only draft `ALPHA`, governed application → `STAGE_PLANNED`, first `ALPHA` Task/JIT `READY_FOR_CODEX`; project validator PASS.
2. Accepted MVP → formal `level-up RELEASE` → read-only draft текущего `RELEASE` → apply → first Release JIT READY; initial accepted target остаётся в immutable `PROJECT_INPUT_ACCEPTED`, accepted reports, historical Runs/Stage revisions сохраняются.
3. Strict reviewed schema, stale product digest/ref rejection, запрет future-stage Task, запрет control-plane writes и посторонних requirements, обязательное human review для отредактированной Task и reject `material_change`.
4. Journaled pre-commit interruption → deterministic rollback → прежний ID отвергается, новый read-only draft с новым ID позволяет восстановиться; committed replay идемпотентен, повторный `next` не создаёт новую Task.
5. PH-F02 semantic Gate evidence, Brownfield exact assessment, B-02 Stage recovery, maintenance and prior implementation-regression tests не менялись; полная регрессия включена ниже.

## Реальные команды и результаты

| Проверка | Команда/маршрут | Итог |
|---|---|---|
| PH-F03 focused | `PYTHONPATH=src:. python -m unittest tests.test_ph_f03_active_stage_planning -v` | **8/8 PASS** |
| PH-F01 boundary regressions | `PYTHONPATH=src:. python -m unittest tests.test_ph_f01_planner_regression -v` | **6/6 PASS**, включая три ранее RED PH-F03 |
| Public installed wheel | `pip wheel . --no-deps --no-build-isolation` + `pip install --no-deps --target <directory> <wheel>` | **PASS** |
| Wheel CLI smoke | `python -m project_harness prepare-active-stage-plan → plan-active-stage → next → validate-project` | `DRAFT_PREPARED → STAGE_PLANNED → READY_FOR_CODEX → PASS` |
| Engine doctor | `PYTHONPATH=src:. python project-harness.py doctor` | **PASS** |
| Wheel doctor | `PYTHONPATH=<wheel-target> python -m project_harness doctor --skip-manifest` | **PASS** |
| Documentation validator | `python tools/validate_documentation.py . --build-aggregates` | **36/36 PASS**, без ошибок; финальный ZIP валидируется отдельно |
| Full existing + added regression suite | `PYTHONPATH=src:. python tests/run_tests.py` | **139/139 PASS** за **337.106 с**; **0 failures, 0 errors** |
| ZIP CRC + manifests | Independent `zipfile.testzip()` and `MANIFEST.sha256`/SHA-256 audit | **PASS**: оба ZIP имеют CRC PASS, точное дерево и согласованные sha256 manifests; Engine doctor и документационный validator проверены |

Логи полного прогона в `PH_F03_TEST_LOG.txt` внутри Engine ZIP. Реальные acceptance fixtures из модулей `tests.ph_f01_fixtures` и `tests.test_ph_f03_active_stage_planning`. Разные negative tests фиксируют отклонение до изменения Stage State; `validate-project` подтверждает сохранность mixed-state invariants после commit.

## Ограничения и отложенные этапы

- Генерируемые current-stage Tasks ориентированы на нормативные level criteria и accepted requirement bindings; их **семантическая** достаточность для конкретного продукта должна быть проверена оператором. Изменённый план требует формального review. Ни JIT, ни успешная Task verification сами по себе не служат Stage acceptance.
- PH-F02 остаётся strict subject-specific Gate evidence, без универсального `PASS`; PH-F04–PH-F08 остаются отдельными пакетами.
- В v0.5.0 отсутствуют локальный Executor Adapter, контейнерный sandbox, Git/PR/deploy и фоновое исполнение; их добавление этим патчем не производилось.

Итог: закрывается публичная возможность продолжить **только следующую активную** Stage после acceptance/level-up с точным review record и crash-consistent application; финальную интеграционную готовность версии следует проверять в PH-F08.
