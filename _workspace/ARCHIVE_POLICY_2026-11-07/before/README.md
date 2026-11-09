# Project Harness в Codex

Workspace разработки движка Project Harness. Текущая база — Engine и Documentation v0.5.1 PH-LW-05, WIP / NOT RELEASED. Открывайте в Codex **этот общий каталог**, чтобы были доступны код, спецификации, планы и промпты.

- [AGENTS.md](AGENTS.md) — короткие обязательные правила работы.
- [Текущая задача и статус](_workspace/CURRENT_TASK.md) — точка продолжения следующего чата.
- [Карта кода, документации и промптов](_workspace/PROJECT_MAP.md).
- [Рабочие команды](_workspace/RUNBOOK.md).
- [Входной preflight](_workspace/PREFLIGHT_INPUTS.json).
- [Аудит исходного AGENTS.md](_workspace/AGENTS_REVIEW.md).
- [Фактическая Windows/HTTP приёмка PH-LW-04/05](Project_Harness_Engine_v0.5.1/PH_LW_04_05_WINDOWS_ACCEPTANCE_TEST_REPORT.md).
- [Windows manual migration: исправления и разбор девяти FAIL-модулей](Project_Harness_Engine_v0.5.1/PH_LW_05_WINDOWS_MANUAL_REMEDIATION_TEST_REPORT.md).
- [Текущая поставка и SHA-256](_deliverables/PH_LW_05_WINDOWS_MANUAL_REMEDIATION_2026-11-07/PH_LW_05_WINDOWS_MANUAL_REMEDIATION_SHA256.txt).

`_inputs/` хранит неизменные копии всех семи предоставленных файлов. Распакованные каталоги сохраняют оригинальные имена. `_scratch/` — временные проверки и логи; `_tools/` и `.venv/` — локальная среда разработчика; `_deliverables/` — проверенные поставки и фактические отчёты. Это инфраструктура разработки, не пользовательский Windows installer PH-LW-11.
