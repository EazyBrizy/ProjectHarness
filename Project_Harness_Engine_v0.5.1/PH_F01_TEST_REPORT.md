# Project Harness v0.5.0 — PH-F01 Test Report

**Дата тестирования:** 2026-10-23  
**Компонент:** Project Harness Engine + Documentation 0.5.0  
**Состояние:** BASELINE (117 GREEN) + expected regression RED; **НЕ** релизная приёмка.

## Тестовый объект

Исходные ZIP `Project_Harness_Engine_v0.5.0.zip` и `Project_Harness_Documentation_v0.5.0.zip`; спецификация `02_Project_Harness_v0.5.0_Implementation_Levels.md` из предоставленного архива; план исправлений `Project_Harness_v0.5.0_Remediation_Plan_RU.md`, PH-F01. Базовый код runtime/CLI/API/модели остаётся неизменным; PH-F01 добавляет fixtures, тесты, матрицу и отчёты.

## Фактически выполненные команды и результаты

| Команда / проверка | Итог | Детали |
|---|---|---|
| `cd Project_Harness_Engine_v0.5.0 && python tests/run_tests.py` | **PASS** | 117 tests in 759.000s; `OK`; запуск исходной discovery-suite до добавления новых PH-F01 tests. Исходный runtime не изменялся |
| `PYTHONPATH=src:. python -m unittest -v tests.test_ph_f01_planner_regression tests.test_ph_f01_gate_semantics_regression` | **EXPECTED RED** | 9 тестовых методов, 4 GREEN, 5 failing methods / 8 failing assertions including subtests; `FAILED (failures=8)`, **повторный прогон на финальной структуре fixtures — 69.113s** (предыдущий — 101.464s), нет unexpected ERROR |
| `tests.test_ph_f01_planner_regression` green fixture tests | **PASS** | Greenfield MVP, Brownfield, accept Prototype and MVP target reached, real CLI `stage-status`, `next`, `level-up`, API persisted statuses and historical digests |
| `tests.test_ph_f01_gate_semantics_regression` green precondition fixture test | **PASS** | Genuine preparation route, all four missing Gate kinds selected, current Stage Scope and product baseline unchanged |
| PH-F01 full discovery count | 126 collected tests | 117 исходных + 9 новых; целевой общий GREEN до PH-F02/PH-F03 **не заявлен** |

Полные журналы команд сохранены в Engine архиве:
- `tests/reports/PH_F01_existing_117_tests.log`;
- `tests/reports/PH_F01_regressions_expected_red.log`.

## Ожидаемые падающие регрессии (не помечаются `expectedFailure`)

| Test ID / subtest | Фактически обнаружено | Исправляющий этап |
|---|---|---|
| `PHF01FixtureAndPlannerTests.test_ph_f03_accept_prototype_to_first_alpha_ready_jit` | Нет публичной CLI-команды `prepare-active-stage-plan`; route `PLAN_ACTIVE_STAGE`, `STAGE_PLANNING_REQUIRED`, Alpha JIT недоступен | PH-F03 |
| `PHF01FixtureAndPlannerTests.test_ph_f03_level_up_mvp_to_first_release_ready_jit` | MVP→RELEASE формально меняет active Stage, но нет planner/первого Release READY JIT | PH-F03 |
| `PHF01FixtureAndPlannerTests.test_ph_f03_route_is_actionable_in_public_status_api` | `stage_status.next_operator_route.command == null` для `PLAN_ACTIVE_STAGE` | PH-F03 (status hardening PH-F04) |
| `PHF01GateSemanticsTests.test_ph_f02_noop_pass_cannot_fabricate_semantically_unverified_kinds` (`ARCHITECTURE_RECORD`) | Нет специализированного доказательства архитектуры; общий PASS создаёт `PASS` EVD | PH-F02 |
| То же (`LIMITATIONS_RECORD`) | Нет предметного доказательства известных ограничений | PH-F02 |
| То же (`PERMITTED_USE_RECORD`) | Нет предметного подтверждения permitted-use | PH-F02 |
| То же (`EXTERNAL_EVIDENCE`) | Нет независимого внешнего источника; общий PASS превращён в external evidence | PH-F02 |
| `PHF01GateSemanticsTests.test_ph_f02_noop_pass_keeps_gate_unclosed_without_subject_proofs` | При no-change PASS готовность Gate ошибочно становится `VERIFYING` | PH-F02 |

Детали reproducer: исходные Tasks выполняются через `verify_current(..., allow_command_execution=True)` и `complete_current(...)`; preparation Task не вносит ни единого изменения в product tree, а `verification.expected_paths=[]`, `manual_checks=[]`. PASS report отвечает только за общие команды. Текущий `materialize_preparation_task_evidence()` создаёт все перечисленные kinds из одного verification report. Физический `sha256`, canonical evidence schema и exact Gate subject binding сами по себе не устанавливают истинность семантического предмета доказательства.

Текущее правильное поведение, закрепляемое RED: для каждого неподтверждённого item должны остаться UNKNOWN/BLOCKED либо быть получены реальные подходящие источники; в PH-F01 исправление не вносится.

## Выполненные проверки сборки и дистрибутива

| Проверка/реальная команда | Фактический результат |
|---|---|
| `bin/project-harness doctor --root <извлечённый Engine>` | **PASS**, 6/6 checks: registries, schemas, skills, entry points, resource mirrors, Engine manifest |
| `python tools/validate_documentation.py <извлечённая Documentation> --zip <собранный Documentation ZIP>` | **PASS**, 36/36 checks, 0 errors, 0 warnings; 109 files in Documentation ZIP |
| Python `unittest.defaultTestLoader.discover('tests', pattern='test_*.py').countTestCases()` | **126** discovered, 117 existing + 9 PH-F01 regressions |
| ZIP `testzip()` / exact tree binary diff for both ZIPs | **PASS**, no CRC errors, every packed member matches source bytes; Engine 234 files (Documentation mirror included) |
| Engine `MANIFEST.sha256` + Documentation `MANIFEST.sha256` validation | **PASS**, engine doctor validates 232 project entries according to existing manifest exclusions; docs validator validates 108 entries |
| Existing runtime source/wheel/registries/schemas/skills/templates and original tests | **Byte-identical** to original input ZIP, checked before rebuilding it in place; no existing runtime contract updated |
| Documentation in Engine vs standalone Documentation tree | **Byte-identical** for every embedded file; standalone validator PASS |

Все проверки выполнялись на фактических локальных каталогах, полученных из загруженных ZIP, и на пересобранных архивах; PH-F01 intentional RED не считается общим PASS версии 0.5.0.

## Ограничения, scope и обнаруженные соседние вопросы

- PH-F02 / PH-F03 намеренно RED, не исправлены.
- PH-F04: `validate-project` не ловит dead-end `PLAN_ACTIVE_STAGE` как недопустимый публичный route, хотя `stage-status` не выдаёт исполнимую команду. Зарегистрировано в интеграционной матрице, **без изменения validation.py**.
- Fixture `TARGET_LEVEL_REACHED` строится через публичный Brownfield assessment и formal `SATISFIED_BY_BASELINE` на *синтетических тестовых input/evidence*. Это проверка механики accepted-level и следующего planner boundary, не свидетельство фактического production MVP.
- Вне v0.5.0 никакие Executor/Git/deployment/parallel features не создавались.

См. `PH_F01_INTEGRATION_MATRIX.md` для 12 прежних issue IDs и 14 E2E сценариев.
