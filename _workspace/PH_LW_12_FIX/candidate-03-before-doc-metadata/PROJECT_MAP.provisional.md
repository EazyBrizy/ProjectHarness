Актуальный PH-LW-12: **GO с принятыми ограничениями, все три blockers CLOSED; LOCAL_WEB_MANUAL: GO.** Только Windows. [Новый отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_12_FIX_TEST_REPORT.md), [verdicts/matrices](../Project_Harness_Engine_v0.5.1/PH_LW_12_FIX_LOGS/VERDICTS.json), [операторская глава 23](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/23_PH_LW_12_Blocker_Fixes.md), [CURRENT_TASK](CURRENT_TASK.md). Native IO — `platform_fs.py` и доказанные manual sites; client transport/card — `resources/local_web/assets/app.js`, multipart — `tasks.js`; regressions — `tests/test_ph_lw_12_blockers.py`; actual driver — `local_web/windows/final_acceptance.py`. Automatic executor выключен; full v0.5.1 NOT RELEASED; ZIP не собирать. Ниже — история checkpoints.

Актуальный PH-LW-12: **NO-GO**, Windows-only. [Отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_12_TEST_REPORT.md), [verdicts/matrices](../Project_Harness_Engine_v0.5.1/PH_LW_12_LOGS/VERDICTS.json), [операторская глава 22](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/22_PH_LW_12_Operator_Acceptance.md), [CURRENT_TASK](CURRENT_TASK.md). Deep app-data intake, maintenance result-upload и stale project card не закрыты. Automatic executor выключен; ZIP не собирать. Ниже — история checkpoints.

Актуальные условия PH-LW-11: [решение пользователя](../Project_Harness_Engine_v0.5.1/PH_LW_11_ACCEPTANCE_SCOPE_DECISION.md). Четыре NOT RUN не блокируют этап; текущий PH-LW-11 GO с принятыми ограничениями. [CURRENT_TASK](CURRENT_TASK.md); ниже — история прежних checkpoints.

Актуальный PH-LW-11: [long app-data ZIP-import](../Project_Harness_Engine_v0.5.1/PH_LW_11_ZIP_PATH_TEST_REPORT.md), [глава 21](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/21_PH_LW_11_Long_App_Data_ZIP_Import.md). Verified hashes/scope — [CURRENT_TASK](CURRENT_TASK.md). Предыдущие checkpoints ниже сохранены.

Актуальный PH-LW-11 long-path fix: [новый отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_TEST_REPORT.md), [глава 20](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/20_PH_LW_11_Long_Path_Preparation.md). Scope и verified hashes — [CURRENT_TASK](CURRENT_TASK.md). Предыдущие checkpoints ниже сохранены.

Актуальный PH-LW-11: [полный prompt r2](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_11.md), [операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/19_PH_LW_11_Windows_Installation.md), [отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_11_TEST_REPORT.md), [изменения](../Project_Harness_Engine_v0.5.1/PH_LW_11_CHANGED_FILES.md). База и разрешения — [CURRENT_TASK](CURRENT_TASK.md); ниже — предыдущие checkpoints.



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

Текущий checkpoint — повторная PH-LW-09 acceptance с Task-level manual evidence intake: [полный prompt r2](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_09.md), проверенная база [PH-LW-08](../Project_Harness_Engine_v0.5.1/PH_LW_08_TEST_REPORT.md). PH-LW-10 требует отдельного задания.


- [README r2](../Harness_Local_Web_Prompts_RU_r2/README_RU.md), [baseline clarification](../Harness_Local_Web_Prompts_RU_r2/BASELINE_CLARIFICATION_R2.md), [план](../Harness_Local_Web_Prompts_RU_r2/IMPLEMENTATION_PLAN_RU.md) §§2–4,7–10.
- [Точный PH-LW-08](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_08.md), предыдущий [PH-LW-07](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_07.md), предыдущий [PH-LW-06](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_06.md), предыдущие [PH-LW-04](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_04.md) и [PH-LW-05](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_05.md), [acceptance matrix](../Harness_Local_Web_Prompts_RU_r2/ACCEPTANCE_MATRIX.md), [control map](../Harness_Local_Web_Prompts_RU_r2/CONTROL_MAP.md), [provenance](../Harness_Local_Web_Prompts_RU_r2/SOURCES_AND_BASELINE.md).
- [Норма v0.5.0](../Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0/02_Project_Harness_v0.5.0_Implementation_Levels.md): accepted scope, Stage State, approvals, evidence, active-stage planning. [Норма v0.5.1](../Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0/03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md): manual/automatic boundary и отсутствие host fallback.
- [Исторический PH-LW-04 report](../Project_Harness_Engine_v0.5.1/PH_LW_04_TEST_REPORT.md), [PH-LW-05 report](../Project_Harness_Engine_v0.5.1/PH_LW_05_TEST_REPORT.md). Их NOT RUN проверяются заново; исторические результаты остаются неизменными.

## Контракты → реализация → проверка

Пути к коду и tests ниже — относительно Engine; документация — относительно standalone Documentation.

| Область | Документация | Код | Проверки |
|---|---|---|---|
| PH-LW-09 Task/Run/result/verify/complete | `13_Local_Web_Manual_Companion/16_PH_LW_09_Task_Run_Manual_Console.md` | `manual_tasks.py`, `local_web_tasks.py`, service/HTTP/`assets/tasks.js`, точечные runtime/result fixes | `test_ph_lw_09_tasks.py`, `test_ph_lw_09_http.py`, `local_web/ci_ph_lw_09_windows.ps1`; `PH_LW_09_TEST_REPORT.md` |
| PH-LW-08 preparation/publication | `13_Local_Web_Manual_Companion/15_PH_LW_08_Preparation_and_Publication.md` | `materialization.py`, `local_web_preparation.py`, service/HTTP/`assets/preparation.js` | `test_ph_lw_08_preparation.py`, `test_ph_lw_08_http.py`, `local_web/ci_ph_lw_08_windows.ps1`; `PH_LW_08_TEST_REPORT.md` |
| PH-LW-07 separate approvals/receipts/recovery | `13_Local_Web_Manual_Companion/14_PH_LW_07_Separate_Approvals.md` | `local_web_approval_core.py`, `local_web_approvals.py`, service/HTTP/`assets/approvals.js` | `test_ph_lw_07_approvals.py`, `test_ph_lw_07_http.py`, `local_web/ci_ph_lw_07_windows.ps1`; `PH_LW_07_TEST_REPORT.md` |
| PH-LW-06 questions/GPT draft exchange | `13_Local_Web_Manual_Companion/13_PH_LW_06_Interview_and_GPT_Exchange.md` | `local_web_exchange.py`, `local_web_exchange_contract.py`, `project_input.py`, `resources/local_web/assets/interview.js`, envelope v2 и browser template | `tests/test_ph_lw_06_exchange.py`, `test_ph_lw_06_http.py`, `local_web/ci_ph_lw_06_windows.ps1`; `PH_LW_06_TEST_REPORT.md` |
| Windows manual migration v0.5.0→v0.5.1 | `13_Local_Web_Manual_Companion/12_Windows_Manual_Migration_Retest.md`, normative v0.5.1 §§21–22 | `src/project_harness/migration.py` | `test_windows_manual_migration.py`, класс `V051MigrationTests` в `test_ph_051_10_migration_recovery.py`; `PH_LW_05_WINDOWS_MANUAL_REMEDIATION_TEST_REPORT.md` |
| Платформа и блокировки | `13_Local_Web_Manual_Companion/07_PH_LW_02_Native_Windows_Manual_Core.md` | `src/project_harness/platform_fs.py`, `operation_guard.py` | `tests/test_ph_lw_02_windows_core.py` |
| Service, revisions, recovery | `13_Local_Web_Manual_Companion/08_PH_LW_03_Application_Service_and_Operation_Recovery.md` | `src/project_harness/local_web_service.py` | `tests/test_ph_lw_03_service.py` |
| HTTP/auth/loopback/UI | `13_Local_Web_Manual_Companion/09_PH_LW_04_Loopback_HTTP_Session_and_UI_Shell.md` | `src/project_harness/local_web_http.py`, `local_web_launcher.py`, `resources/local_web/assets/` | `tests/test_ph_lw_04_http.py`, `local_web/ci_ph_lw_04_windows.ps1` |
| MD/ZIP/provenance/refresh | `13_Local_Web_Manual_Companion/10_PH_LW_05_Document_Import_and_Source_Revisions.md` | `src/project_harness/local_web_imports.py`, `local_web_sources_service.py`, `local_web_source_refresh.py`, `intake.py` | `tests/test_ph_lw_05_import.py`, `test_ph_lw_05_http.py`, `local_web/ci_ph_lw_05_windows.ps1` |
| Security budgets/consent | `13_Local_Web_Manual_Companion/04_Threat_Model_And_Consent.md`, `05_Acceptance_CI_Baseline.md` | `src/project_harness/resources/local_web/` | `local_web/fixtures/`, PH-LW tests |
| Фактическая Windows HTTP приёмка | `13_Local_Web_Manual_Companion/11_PH_LW_04_05_Windows_HTTP_Acceptance.md` | тот же production `create_loopback_server` | `tests/test_ph_lw_04_05_acceptance.py`, `local_web/run_windows_acceptance.py`, новый `PH_LW_04_05_WINDOWS_ACCEPTANCE_TEST_REPORT.md` |
| Упаковка/схемы | `10_Contracts/`, README | `pyproject.toml`, `schemas/`, `registries/`, `src/project_harness/resources/` | doctor, wheel smoke, `tools/validate_documentation.py` внутри docs |

Полные prompts в `prompts/` — рабочие точки входа. `ALL_IMPLEMENTATION_PROMPTS_RU.md` — сводная копия, не второй независимый набор правил. Документы PH-LW-01 с пометкой CONTRACT DESIGN описывают проектное решение на момент создания; главы 07–16 описывают реализацию, а report — фактическую приёмку. Не переписывать историю ради внешнего единства статусов. Предыдущий checkpoint: [report PH-LW-08](../Project_Harness_Engine_v0.5.1/PH_LW_08_TEST_REPORT.md), [его hashes](PH_LW_08/FINAL_WORKING_TREE_VERIFICATION.json). Правило ZIP пользователя в AGENTS.md/RUNBOOK имеет приоритет над архивным prompt.

Исторический первый PH-LW-09 checkpoint получил verdict **NO-GO** из-за manual lifecycle blocker: непустые manual checks больше не дают PASS по одному `allow_manual:true`, а поддержанного Task-level proof intake нет. Главы 07–16 отражают последовательные checkpoints, старые фразы о pending этапах сохранены как история. [Исторический report](../Project_Harness_Engine_v0.5.1/PH_LW_09_TEST_REPORT.md), [output hashes](PH_LW_09/FINAL_WORKING_TREE_VERIFICATION.json). Automatic executor выключен, Engine/Documentation ZIP не создаются. На тот момент продолжение требовало отдельного задания по blocker; оно выполнено текущим дополнением ниже. PH-LW-10 не начат.

Текущее дополнение по отдельному заданию: [глава 17](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/17_PH_LW_09_Task_Manual_Evidence.md), [новый report](../Project_Harness_Engine_v0.5.1/PH_LW_09_MANUAL_EVIDENCE_TEST_REPORT.md), [аттестация](PH_LW_09_MANUAL_EVIDENCE/FINAL_WORKING_TREE_VERIFICATION.json). PH-F06 13 PASS; PH-LW-09 PASS в назначенном scope по current matrix с явными rechecks. Прежний NO-GO выше — исторический checkpoint. PH-LW-10 не начат.
