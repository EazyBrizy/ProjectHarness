PH-LW-12: **GO с принятыми ограничениями; все три blockers CLOSED. LOCAL_WEB_MANUAL: GO.** Только Windows. [Новый отчёт](Project_Harness_Engine_v0.5.1/PH_LW_12_FIX_TEST_REPORT.md), [CURRENT_TASK](_workspace/CURRENT_TASK.md), [операторская глава 23](Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/23_PH_LW_12_Blocker_Fixes.md). Windows: 461 PASS / 2 capability SKIP; actual EXE extended: 22 PASS; отдельный deep full manual E2E PASS. Четыре прежних NOT RUN сохранены. Automatic executor выключен; полная v0.5.1 NOT RELEASED; Engine/Documentation ZIP не создавались. Ниже — история checkpoints.

PH-LW-12: **NO-GO**, только Windows. [Отчёт](Project_Harness_Engine_v0.5.1/PH_LW_12_TEST_REPORT.md), [CURRENT_TASK](_workspace/CURRENT_TASK.md), [операторский маршрут](Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/22_PH_LW_12_Operator_Acceptance.md). Windows matrix: 449 PASS / 2 SKIP; actual EXE extended: 17 PASS / 1 FAIL. Deep app-data intake, maintenance result-upload и stale project-list projection открыты. Automatic executor выключен; Engine/Documentation ZIP не собирались. Ниже — история checkpoints.

Текущий PH-LW-11: **GO с принятыми пользователем ограничениями**. [Решение об условиях приёмки](Project_Harness_Engine_v0.5.1/PH_LW_11_ACCEPTANCE_SCOPE_DECISION.md), [CURRENT_TASK](_workspace/CURRENT_TASK.md). Ниже сохранены прежние checkpoints. LOCAL_WEB_MANUAL/automatic/full v0.5.1 не повышены до GO; PH-LW-12 не начат.

Текущий PH-LW-11: [long app-data ZIP-import report](Project_Harness_Engine_v0.5.1/PH_LW_11_ZIP_PATH_TEST_REPORT.md), [состояние](_workspace/CURRENT_TASK.md). Scoped ZIP fix PASS; полная acceptance NO-GO. Automatic executor выключен; PH-LW-12 не начат; ZIP не собирались.

Текущая работа — PH-LW-11 long-path fix: [состояние](_workspace/CURRENT_TASK.md), [новый отчёт](Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_TEST_REPORT.md). Long-path preparation PASS, полная acceptance NO-GO; automatic executor выключен, PH-LW-12 не начат, ZIP не создавались.

Текущая работа — PH-LW-11: Windows installer собран, acceptance NO-GO. [Состояние](_workspace/CURRENT_TASK.md), [отчёт](Project_Harness_Engine_v0.5.1/PH_LW_11_TEST_REPORT.md), [installer](Project_Harness_Engine_v0.5.1/windows/Harness-Setup-win-x64.exe). Automatic executor выключен, PH-LW-12 не начат, ZIP не создавались. Ниже — история checkpoints.



Текущий checkpoint: Task-level manual evidence intake реализован, PH-F06 закрыт; повторная составная PH-LW-09 acceptance — PASS в назначенном scope. [Отчёт](Project_Harness_Engine_v0.5.1/PH_LW_09_MANUAL_EVIDENCE_TEST_REPORT.md), [CURRENT_TASK](_workspace/CURRENT_TASK.md).

## Текущая работа — PH-LW-09

[Текущий статус](_workspace/CURRENT_TASK.md), [Task/Run console](Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/16_PH_LW_09_Task_Run_Manual_Console.md), [фактический отчёт](Project_Harness_Engine_v0.5.1/PH_LW_09_TEST_REPORT.md). Первый PH-LW-09 checkpoint имел NO-GO из-за отсутствующего Task proof intake; он сохранён как история. Актуальное дополнение и составная повторная приёмка описаны в новом отчёте выше. Automatic executor выключен, PH-LW-10 не выполняется, ZIP не собираются. Исторические checkpoints ниже сохраняются.

# Project Harness в Codex

Workspace разработки движка Project Harness. Текущие рабочие Engine и Documentation v0.5.1 — PH-LW-09 с Task-level manual evidence intake, WIP / NOT RELEASED; текущий Local Web checkpoint принят в назначенном scope по current matrix с точечными rechecks. Открывайте в Codex **этот общий каталог**, чтобы были доступны код, спецификации, планы и промпты.

Все рабочие файлы проекта хранятся в распакованных каталогах workspace. **После каждого этапа Engine/Documentation ZIP собирать не нужно: архивы создаются только по явному запросу пользователя для передачи в ChatGPT на анализ, когда это требуется.** Архивы — дополнительные снимки для передачи, а не единственное место хранения файлов. Правило принято 2026-11-07; прежние архивы и оригинальные inputs сохраняются неизменными.

- [AGENTS.md](AGENTS.md) — короткие обязательные правила работы.
- [Текущая задача и статус](_workspace/CURRENT_TASK.md) — точка продолжения следующего чата.
- [Карта кода, документации и промптов](_workspace/PROJECT_MAP.md).
- [Рабочие команды](_workspace/RUNBOOK.md).
- [Входной preflight](_workspace/PREFLIGHT_INPUTS.json).
- [Аудит исходного AGENTS.md](_workspace/AGENTS_REVIEW.md).
- [Фактическая Windows/HTTP приёмка PH-LW-04/05](Project_Harness_Engine_v0.5.1/PH_LW_04_05_WINDOWS_ACCEPTANCE_TEST_REPORT.md).
- [Windows manual migration: исправления и разбор девяти FAIL-модулей](Project_Harness_Engine_v0.5.1/PH_LW_05_WINDOWS_MANUAL_REMEDIATION_TEST_REPORT.md).
- [PH-LW-08: подготовка, публикация, tests и evidence](Project_Harness_Engine_v0.5.1/PH_LW_08_TEST_REPORT.md).
- [PH-LW-07: отдельные согласования, tests и evidence](Project_Harness_Engine_v0.5.1/PH_LW_07_TEST_REPORT.md).
- [Последняя архивная поставка и её SHA-256](_deliverables/PH_LW_05_WINDOWS_MANUAL_REMEDIATION_2026-11-07/PH_LW_05_WINDOWS_MANUAL_REMEDIATION_SHA256.txt) — исторический снимок, не автоматически обновляемая копия workspace.

`_inputs/` хранит неизменные копии всех семи предоставленных файлов. Распакованные каталоги сохраняют оригинальные имена. `_scratch/` — временные проверки и логи; `_tools/` и `.venv/` — локальная среда разработчика; `_deliverables/` — проверенные поставки и фактические отчёты. Это инфраструктура разработки, не пользовательский Windows installer PH-LW-11.
