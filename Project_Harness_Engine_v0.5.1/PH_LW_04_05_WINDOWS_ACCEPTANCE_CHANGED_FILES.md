# PH-LW-04/05 Windows retest — изменения

Дата: 2026-11-07. База: точная входная пара PH-LW-05 из [отчёта](PH_LW_04_05_WINDOWS_ACCEPTANCE_TEST_REPORT.md). Исторические reports/logs не изменены.

| Группа | Файлы / назначение |
|---|---|
| HTTP и idempotency | `src/project_harness/local_web_http.py`, `local_web_service.py`: route argument, DTO/CSRF validation, duplicate multipart scalar rejection, receipt replay перед stale checks |
| Import boundary | `local_web_imports.py`, `local_web_sources_service.py`: native parent checks и отдельный raw ZIP budget |
| Production server/UI | `local_web_launcher.py`, `resources/local_web/assets/app.js`, `index.html`: общий production server factory, восстановление busy actions, точное описание лимитов |
| Прямой manual Windows regression | `stage_transactions.py`: write-capable fd для Windows fsync; без подавления flush errors |
| Runtime provenance | `resources/local_web/metadata_v1.json`, `local_web/wheel_inventory_v1.json`, comments lock: актуальный build/input hashes и фактическая установка pinned wheels; pins неизменны |
| Tests | `test_ph_lw_04_http.py`, `test_ph_lw_05_http.py`, `test_ph_lw_05_import.py`, новый `test_ph_lw_04_05_acceptance.py`; metadata assertions `test_ph_lw_01_contract.py`; переносимые Windows CLI/fault fixtures в `test_ph_f01_planner_regression.py`, `test_ph_f03_active_stage_planning.py`, `test_ph_f04_runtime_reachability.py` |
| Native CI | `local_web/ci_ph_lw_04_windows.ps1`, `ci_ph_lw_05_windows.ps1`, новый `run_windows_acceptance.py`: direct interpreter, среда, real Edge, skip accounting, exact exits |
| Docs/evidence | README/CHANGELOG, новая глава 11 Windows acceptance, generated aggregates/index, embedded mirror; новые report/changes/invariants/logs |
| Generated package | `build/lib`, wheel в `dist`, egg-info, manifests пересозданы из source; ручного patch build/lib нет |

Полный машинный список относительно исходного архива: [CHANGED_FILES.json](PH_LW_04_05_WINDOWS_ACCEPTANCE_CHANGED_FILES.json). Он включает generated artifacts и новые evidence files. Удалённых исходных файлов нет.

Вне Engine подготовлены root AGENTS/README, `_workspace` карта/статус/runbook/audit/input hashes/dev lock, `tools` preflight/linkage/logging/regression/packaging/installed-wheel/final-ZIP verification, локальная `.venv` и portable runtime. Исходные 7 файлов лежат неизменными в `_inputs`; specs/prompts/plans распакованы в отдельные каталоги. Эти workspace файлы не объявлены частью runtime wheel.
