# PH-F07 — отчёт о проверке операторских инструкций

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Проверка:** PH-F07, 2026-10-25  
**Scope:** operator documentation, examples and distributable prompt template only; no production-runtime modification

## 1. Входная поставка и область доказательства

- Engine input: `Project_Harness_Engine_v0.5.0 (7).zip` — последняя поставка после PH-F06.
- Documentation input: `Project_Harness_Documentation_v0.5.0 (6).zip` — последняя поставка после PH-F06.
- Normative baseline: `02_Project_Harness_v0.5.0_Implementation_Levels.md` и embedded `12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md`.
- Production Python, тесты, схемы и registry представлены прежними байтами. Нового исполнителя, API или schema нет. Wheel пересобран для изменённого operator prompt/resource и README metadata без изменения Python-кода.

## 2. Подтверждённые smoke-сценарии

| Команда/сценарий | Результат | Проверено |
|---|---|---|
| `python project-harness.py --help`; `--version`; `doctor` | PASS | Все документированные public routes и версия `0.5.0` доступны; source doctor PASS после финального manifest |
| `project-harness --version`; `project-harness doctor` | PASS | Чистое окружение, wheel установлен `pip install --no-index --no-deps` |
| `project-harness demo --output-dir <dir> --keep-directory` | PASS | Встроенный Greenfield fixture успешно создаёт handoff |
| `project-harness validate-handoff --project <zip>`; `validate-project --project <dir>` | PASS | Initial handoff и mutable project проверены |
| `project-harness next --project <dir>`; `stage-status --project <dir>` | PASS | Возвращён первый Task/JIT, status ACTIVE/READY_FOR_CODEX |
| `project-harness start-intake --workspace ... --mode greenfield ...`; `check-intake` | ОЖИДАЕМЫЙ `WAITING_INPUT` | Exit code 3: отсутствие исходных подтверждённых approvals не замалчивается |
| `project-harness stage-status`/`next` на accepted Prototype | PASS | Граница `STAGE_PLANNING_REQUIRED`, указан actionable route |
| `project-harness prepare-active-stage-plan --project ... --output ...` | PASS | Read-only DRAFT_PREPARED с exact current binding |
| `project-harness plan-active-stage --project ... --plan ...` и повтор | PASS | `STAGE_PLANNED`, идемпотентность identical request |
| `project-harness next`; `validate-project` после Alpha planning | PASS | Первый Alpha READY_FOR_CODEX JIT, project validation PASS |

Smoke использует реально опубликованные CLI-флаги и реальные Project Instance fixtures. Формальные решения и evidence в fixture создаются тестом только для его собственного scenario, а не выдаются за действия пользователя или фактическую semantic production acceptance.

## 3. Регрессионные тесты

- `python tests/run_tests.py`: **166 tests, 165 OK и 1 FAIL при первом прогоне**. Неуспех вызван `subprocess.TimeoutExpired` (лимит 10 секунд) внутри локального product acceptance test `test_core_cli_contract`, который был запущен вторично через `test_ph_f06_maturity_lifecycle.PHF06BrownfieldTests.test_05_supplied_proofs_survive_assessment_then_sequential_baseline_reports_and_planner`. В этот момент параллельно выполнялся дополнительный тяжёлый operator smoke. Это не ошибка поля schema/документационного контракта и не результат изменения runtime.
- `PYTHONPATH=src:. python -m unittest tests.test_ph_f06_maturity_lifecycle.PHF06BrownfieldTests.test_05_supplied_proofs_survive_assessment_then_sequential_baseline_reports_and_planner -v`: **1/1 PASS** за 24.686 s без параллельного smoke; исходный case воспроизведён и успешно закрыт.
- **Заключительный отдельный source regression прогон** (без параллельного тяжёлого smoke): `PYTHONDONTWRITEBYTECODE=1 python tests/run_tests.py` — **166/166 PASS**, failures=0, errors=0, 851.693 s. Лог включён в `PH_F07_LOGS/final_full_suite.log`. Фактический первый timeout сохраняется в отдельном initial log, а не скрыт. Конечный PH-F08 release GO этим PH-F07 не утверждается.
- После заключительного уточнения текста GPT source template: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest tests.test_ph_f05_intake_acceptance -v` — **4/4 PASS**, 2.125 s; отсутствие `--source` при отсутствующей документации осталось поддерживаемым. Лог: `PH_F07_LOGS/f05_posttemplate.log`.

## 4. Сохранённые invariants / ограничения

- B-01/Q-04 active-stage planner, B-02 atomic journal recovery, B-03/B-04 exact Brownfield assessment, G-01 semantic evidence and source integrity, L-01 canonical target, M-01 maintenance, U-01 drafts, Q-01/Q-02 Gate readiness/recovery, Q-03 formal schemas, PH-F01–PH-F06 тесты и implementation-stage fence не изменены.
- Передача JIT внешнему агенту требуется; Engine не выполняет Codex самостоятельно. `verify --allow-command-execution` не предоставляет OS sandbox.
- `TEST_REPORT` с общим PASS не подменяет typed `EVD-*` с source-backed semantic proof. Formal approval остаётся решением человека.
- `prepare` и `validate-handoff` не гарантируют готовый production product. `doctor` подтверждает consistency поставки, а не завершение integration acceptance.
- Direct v0.4.0 migration или v0.5.1/v0.6.x functionality не добавлены.

## 5. Артефакты

Документация: единый `08_Distribution/04_Operator_Runbook_v0.5.0.md`, обновлённые связанные разделы и воспроизводимые aggregates/index. Движок: обновлённые инструкции, поставляемый prompt template, wheel (тот же v0.5.0), зеркальная Documentation. ZIPs снабжены SHA-256 manifest и прошли самостоятельную контрольную проверку; детали в JSON validation report и логах из `PH_F07_LOGS/` Engine.

Перечень изменений: `PH_F07_CHANGED_FILES.md`. Следующий этап PH-F08 должен выполнять самостоятельную полную release acceptance matrix.
