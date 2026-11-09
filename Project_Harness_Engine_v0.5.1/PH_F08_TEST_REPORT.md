# Project Harness v0.5.0 — PH-F08 финальный тестовый отчёт

**Дата:** 2026-10-25  
**Цель:** точечная финальная интеграционная приёмка и выпуск согласованных Engine/Documentation ZIP.  
**Решение:** **GO для функциональной v0.5.0** в границах preparation/governance runtime с внешним агентом.  
**Итог:** I-01–I-14 = 14/14 PASS; старый регрессионный набор и новые тесты = **168/168 PASS**, 0 failures/errors.

## 1. Входная нормативная база и источник поставки

- Использованы ненумерованные Engine/Documentation ZIP после PH-F07, а не более ранние пронумерованные архивы PH-F06.
- Нормативная спецификация `02_Project_Harness_v0.5.0_Implementation_Levels.md` использована как immutable baseline; версия Engine остаётся `0.5.0`, canonical schema/registries не повышались.
- Входные SHA-256:
- Engine PH-F07 ZIP: `953b70d722cbf3948f8f1c3854ea959da8064d77004cdf679d4f275701bfef46`
- Documentation PH-F07 ZIP: `d2d6fd617b22ba0852db04f371d1490ab2bc873a4f5c01e7c33fbd7855865102`
- Normative v0.5.0 specification: `ca487d3e978af116418a597b5d05cd890d11e2e93855c9f7a312e21f083dd16f`

## 2. Фактические проверки и команды

1. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python tests/run_tests.py` (из корня Engine) → **168 tests, OK**, 548.767s; лог `PH_F08_LOGS/full_suite_final.log`.
2. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest tests.test_ph_f08_release_acceptance -v` (отдельно до полного прогона) → **2/2 PASS**; source `PH_F08_LOGS/f08_targeted_initial.log`.
3. Fresh virtual environment: `python -m venv <tmp>/venv`; `<tmp>/venv/bin/python -m pip install --no-index --no-deps dist/project_harness_engine-0.5.0-py3-none-any.whl` → PASS (isolated wheel, no `PYTHONPATH`).
4. Installed `<tmp>/venv/bin/project-harness --version`, `doctor`, `demo --output-dir <tmp>/demo --keep-directory`, `validate-handoff --project <zip>`, `validate-project --project <dir>`, `next --project <dir>`, `stage-status --project <dir>` → PASS; точные аргументы, статусы, stdout и exit codes: `PH_F08_LOGS/wheel_smoke.json`.
5. `PYTHONPATH=src:. python project-harness.py doctor` → PASS (schemas, registries, skills, resources, manifest); `PH_F08_LOGS/doctor_final.json`.
6. `python tools/validate_documentation.py . --zip <final-doc-zip> --json <external-report>` → PASS, no WARN; `PH_F08_LOGS/doc_zip_final.json`.
7. `zipfile.testzip()` на обоих финальных ZIP, сверка exact zip member set, SHA-256 по manifest каждого дерева и source/embedded docs byte equality → PASS; `PH_F08_LOGS/zip_integrity.json`. Внешний `SHA256SUMS.txt` содержит digest двух финальных ZIP.

## 3. Матрица сквозной приёмки

См. `PH_F08_ACCEPTANCE_MATRIX.md` и `PH_F08_RELEASE_MATRIX.json` с точными test IDs и expected outcome. Каждая строка **I-01–I-14** отмечена PASS только по реально выполненным тестам или отдельному distribution smoke.

## 4. Контроль сохранённых исправлений

| Issue IDs | Проверенная область | Результат |
|---|---|---|
| `B-01/Q-04` | PH-F03 active-stage planning / PH-F04 reachable continuation / I-03 and I-04 | PASS |
| `B-02` | Stage transaction journal/recovery / I-11 | PASS |
| `B-03/B-04` | Brownfield exact ref and freshness / I-08, I-09 | PASS |
| `G-01` | Exact evidence, semantic subject/source, digest, tamper / I-05, I-06, I-08 | PASS |
| `L-01` | Canonical Stage State target and immutable initial input / I-04 | PASS |
| `M-01` | Public same-level maintenance / I-10 | PASS |
| `U-01` | Self-contained exact Stage approval drafts / I-06, I-07 | PASS |
| `Q-01/Q-02` | Stage readiness, persisted BLOCKED, recovery / I-05, I-07 | PASS |
| `Q-03` | Strict formal approval schema before mutation / I-06, I-08 | PASS |

Проверено, что исторические Acceptance Reports, завершённые Runs и исходный принятый `PROJECT_INPUT` не переписываются; Stage State остаётся canonical target, нет future-stage Task/Run до governed transition, нет `PLAN_ACTIVE_STAGE` dead end, а семантически не подтверждённый generic PASS не становится evidence для документа/внешнего источника.

## 5. Изменения PH-F08, дефекты и ограничения

- **Production code:** никаких дополнительных изменений не потребовалось после PH-F07; скрытые механизмы, workaround в private Python или новые public operations не добавлены.
- **Новые проверки:** `tests/test_ph_f08_release_acceptance.py` — I-01 и I-03/I-12 на публичном CLI; сохранены все 166 прежних тестов и инварианты предыдущих этапов. Тесты используют отдельные synthetic fixtures и ограниченные case-specific sources, а не фиктивное повышение maturity.
- **Интеграционные дефекты PH-F08:** runtime regressions после PH-F07, требующих Python patch, не обнаружено. Первый unpack потерял исполняемый mode `0755` у `bin/project-harness`, что вызвало **8 ошибок `PermissionError`** в первоначальном полном прогоне (168, 8 errors). После исправления прав в release tree затронутые CLI-тесты пересданы (6 + 2 PASS), и отдельный заключительный полный прогон стал зелёным. Исходный неуспех сохранён в `PH_F08_LOGS/full_suite.log` и `permissions_rerun*.log`, без сокрытия или изменения тестов.
- **Сборка:** два согласованных ZIP, release report/matrix/logs и обновлённые SHA-256 manifests; операторские инструкции PH-F07 и нормативные документы сохранены.
- **Не реализовано и не считается release blocker:** автоматическое исполнение Codex (v0.5.1), OS sandbox, Git/PR/deployment (v0.6.x), удалённый control plane. Human review обязателен при formal approvals и semantic Gate acceptance. Рабочая проверка синтетического локального CLI не сертифицирует внешний production продукт.

**Смысл GO:** можно готовить собственные Project Instances и управляемо проходить Stage maturity до RELEASE **при предоставлении реальных внешних результатов Tasks, проверок и operator-approved evidence**. GO не равен автоматическому production deployment.
