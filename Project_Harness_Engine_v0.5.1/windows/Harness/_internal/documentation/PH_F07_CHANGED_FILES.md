# PH-F07 — журнал изменений операторской документации

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Пакет документации:** PH-F07, 2026-10-25

## Граница исправления

Реализована только документация/примеры оператора согласно PH-F07. Семантика и реализации v0.5.0 не менялись: нет новых CLI-команд, схем, реестров, feature flags, executor/sandbox, Git/PR/deploy и новых правил governance. Нормативная спецификация v0.5.0, исходный Python runtime и тесты сохранены без изменений. PH-F08 — отдельная приёмка.

## Документация

- `08_Distribution/04_Operator_Runbook_v0.5.0.md` — новый единый последовательный operator runbook для source/wheel/doctor, GPT intake, обязательных approvals, prepare/handoff, внешнего исполнения Task, verify/complete, семантического Stage Gate, active-stage planning, level-up, maintenance, Brownfield и migration, статусов, ошибок и recovery.
- `README.md`, `08_Distribution/03_User_Workflows.md` — единая точка входа и реальные доступные команды, без заявлений об автоматической генерации production-продукта.
- `03_Planning/07_Implementation_Levels_and_Stage_Plans.md`, `04_Execution/02_Execution_Lifecycle.md`, `04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md` — корректная граница человеческого approval, source-backed evidence и автоматического status routing.
- `MIGRATION_FROM_v0.4.1.md` — точный поддерживаемый entrypoint, проверяемый результат и ограничения исторических состояний.
- `CHANGELOG.md` — отдельная заметка PH-F07, не переписывающая историю старых процедур.
- Синхронно обновлены воспроизводимые `Project_Harness_Architecture_v0.5.0_FULL.md`, `Project_Harness_User_and_Implementation_Guide_v0.5.0.md`, `FILE_INDEX.md`, `VALIDATION_REPORT.md`, `MANIFEST.sha256`.

## Engine — только operator-facing ресурсы

- `README.md`, `MANUAL_INSTALL.md`, `MIGRATION_FROM_v0.4.1.md`, `CHANGELOG.md` — согласованы с доступными CLI/API и документационным runbook.
- `templates/GPT_PREPARATION_INSTRUCTIONS.md` и поставляемые зеркала в `src/project_harness/resources/templates/`, `build/lib/project_harness/resources/templates/` — уточнены действия GPT/оператора, real evidence и ответственность человека.
- `examples/browser_gpt_start.txt` — стартовые инструкции согласованы с реальным запуском.
- Пересобран существующий wheel `dist/project_harness_engine-0.5.0-py3-none-any.whl` только для включения обновлённого шаблона/metadata; **версия, Python-модули и бинарные интерфейсы не изменялись**.
- Обновлено поставляемое зеркало `docs/Project_Harness_Documentation_v0.5.0/`, manifest и отчёт PH-F07.

## Исправленные недостоверные инструкции

1. Команды source tests выполняются через `python tests/run_tests.py` либо с `PYTHONPATH=src:.` (а не `python -m unittest` из неустановленного дерева).
2. `--zip` документационного validator **проверяет** готовый архив и не создаёт его.
3. `READY_FOR_CODEX`/valid handoff — readiness к *внешнему* агенту, не наличие рабочего production-кода.
4. PASS общей verification Task — не универсальное доказательство architecture, security, constraints, permitted use или external evidence.
5. Отсутствует автоматический Codex Executor/OS sandbox, оператор отвечает за доверенность commands и достаточность formal semantic Stage Gate approval.
6. `level-up` использует реализованный formal approval record; отсутствующая отдельная `level_up_approval.schema.json` не документируется как существующая.
7. Промежуточная Stage требует двух действующих публичных planning commands и точного reviewed record, а не ручного редактирования `.harness`.
