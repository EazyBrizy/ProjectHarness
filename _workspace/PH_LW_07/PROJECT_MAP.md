# Карта проекта и источников

## Навигация

| Назначение | Путь от корня workspace |
|---|---|
| Код и tests | `Project_Harness_Engine_v0.5.1/` |
| Читаемая документация | `Project_Harness_Documentation_v0.5.1/` |
| Побайтовое зеркало docs | `Project_Harness_Engine_v0.5.1/docs/Project_Harness_Documentation_v0.5.1/` |
| Текущий план и полные prompts | `Harness_Local_Web_Prompts_RU_r2/` |
| Неизменные нормативные specs | `Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0/` |
| Предыдущие программы работ | `Project_Harness_v0.5.0_Remediation_Plan_RU.md`, `Project_Harness_v0.5.1_Implementation_Plan_RU.md` |

Старые планы PH-F и PH-051 объясняют историю и invariants; они не назначают текущие задачи PH-LW. Specs v0.6.0–v1.0 — будущий roadmap, не разрешение расширять реализацию.

## Что прочитать по текущей задаче

- [README r2](../Harness_Local_Web_Prompts_RU_r2/README_RU.md), [baseline clarification](../Harness_Local_Web_Prompts_RU_r2/BASELINE_CLARIFICATION_R2.md), [план](../Harness_Local_Web_Prompts_RU_r2/IMPLEMENTATION_PLAN_RU.md) §§2–4,7–10.
- [Точный PH-LW-06](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_06.md), предыдущие [PH-LW-04](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_04.md) и [PH-LW-05](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_05.md), [acceptance matrix](../Harness_Local_Web_Prompts_RU_r2/ACCEPTANCE_MATRIX.md), [control map](../Harness_Local_Web_Prompts_RU_r2/CONTROL_MAP.md), [provenance](../Harness_Local_Web_Prompts_RU_r2/SOURCES_AND_BASELINE.md).
- [Норма v0.5.0](../Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0/02_Project_Harness_v0.5.0_Implementation_Levels.md): accepted scope, Stage State, approvals, evidence, active-stage planning. [Норма v0.5.1](../Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0/03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md): manual/automatic boundary и отсутствие host fallback.
- [Исторический PH-LW-04 report](../Project_Harness_Engine_v0.5.1/PH_LW_04_TEST_REPORT.md), [PH-LW-05 report](../Project_Harness_Engine_v0.5.1/PH_LW_05_TEST_REPORT.md). Их NOT RUN проверяются заново; исторические результаты остаются неизменными.

## Контракты → реализация → проверка

Пути к коду и tests ниже — относительно Engine; документация — относительно standalone Documentation.

| Область | Документация | Код | Проверки |
|---|---|---|---|
| PH-LW-06 questions/GPT draft exchange | `13_Local_Web_Manual_Companion/13_PH_LW_06_Interview_and_GPT_Exchange.md` | `local_web_exchange.py`, `local_web_exchange_contract.py`, `project_input.py`, `resources/local_web/assets/interview.js`, envelope v2 и browser template | `tests/test_ph_lw_06_exchange.py`, `test_ph_lw_06_http.py`, `local_web/ci_ph_lw_06_windows.ps1`; `PH_LW_06_TEST_REPORT.md` |
| Windows manual migration v0.5.0→v0.5.1 | `13_Local_Web_Manual_Companion/12_Windows_Manual_Migration_Retest.md`, normative v0.5.1 §§21–22 | `src/project_harness/migration.py` | `test_windows_manual_migration.py`, класс `V051MigrationTests` в `test_ph_051_10_migration_recovery.py`; `PH_LW_05_WINDOWS_MANUAL_REMEDIATION_TEST_REPORT.md` |
| Платформа и блокировки | `13_Local_Web_Manual_Companion/07_PH_LW_02_Native_Windows_Manual_Core.md` | `src/project_harness/platform_fs.py`, `operation_guard.py` | `tests/test_ph_lw_02_windows_core.py` |
| Service, revisions, recovery | `13_Local_Web_Manual_Companion/08_PH_LW_03_Application_Service_and_Operation_Recovery.md` | `src/project_harness/local_web_service.py` | `tests/test_ph_lw_03_service.py` |
| HTTP/auth/loopback/UI | `13_Local_Web_Manual_Companion/09_PH_LW_04_Loopback_HTTP_Session_and_UI_Shell.md` | `src/project_harness/local_web_http.py`, `local_web_launcher.py`, `resources/local_web/assets/` | `tests/test_ph_lw_04_http.py`, `local_web/ci_ph_lw_04_windows.ps1` |
| MD/ZIP/provenance/refresh | `13_Local_Web_Manual_Companion/10_PH_LW_05_Document_Import_and_Source_Revisions.md` | `src/project_harness/local_web_imports.py`, `local_web_sources_service.py`, `local_web_source_refresh.py`, `intake.py` | `tests/test_ph_lw_05_import.py`, `test_ph_lw_05_http.py`, `local_web/ci_ph_lw_05_windows.ps1` |
| Security budgets/consent | `13_Local_Web_Manual_Companion/04_Threat_Model_And_Consent.md`, `05_Acceptance_CI_Baseline.md` | `src/project_harness/resources/local_web/` | `local_web/fixtures/`, PH-LW tests |
| Фактическая Windows HTTP приёмка | `13_Local_Web_Manual_Companion/11_PH_LW_04_05_Windows_HTTP_Acceptance.md` | тот же production `create_loopback_server` | `tests/test_ph_lw_04_05_acceptance.py`, `local_web/run_windows_acceptance.py`, новый `PH_LW_04_05_WINDOWS_ACCEPTANCE_TEST_REPORT.md` |
| Упаковка/схемы | `10_Contracts/`, README | `pyproject.toml`, `schemas/`, `registries/`, `src/project_harness/resources/` | doctor, wheel smoke, `tools/validate_documentation.py` внутри docs |

Полные prompts в `prompts/` — рабочие точки входа. `ALL_IMPLEMENTATION_PROMPTS_RU.md` — сводная копия, не второй независимый набор правил. Документы PH-LW-01 с пометкой CONTRACT DESIGN описывают проектное решение на момент создания; более поздние главы 07–13 описывают реализацию, а новый report — фактическую приёмку. Не переписывать историю ради внешнего единства статусов. [Новый report PH-LW-06](../Project_Harness_Engine_v0.5.1/PH_LW_06_TEST_REPORT.md), [внешние hashes рабочих деревьев](PH_LW_06/FINAL_WORKING_TREE_VERIFICATION.json). Новое правило ZIP пользователя находится в AGENTS.md/RUNBOOK и имеет приоритет над архивным prompt; PH-LW-07 требует отдельного задания.
