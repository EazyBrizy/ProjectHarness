# PH-F01 — отчёт об изменённых файлах Project Harness v0.5.0

**Дата:** 2026-10-23  
**Версия:** 0.5.0 (не повышалась).  
**Scope:** только regression fixtures/tests, интеграционная матрица, документация результатов и manifests.

## Сводка на момент формирования отчёта

- Новых файлов в Engine ZIP: **14** (включая этот report и новый test report).
- Изменённых старых файлов в Engine ZIP: **10** (включая manifest после его пересборки).
- Удалённых файлов: **0**.
- Runtime/CLI/API `src/`, machine schemas/registries/skills/templates: **0 изменённых байтов** (verified SHA256 comparison against the original ZIP).
- Existing wheel: **без изменений**; ранее существовавшие тестовые файлы: **без изменений**.
- Embedded Documentation mirror и отдельный Documentation ZIP: **byte-identical content**, после синхронизации.

## Новые файлы

- `PH_F01_CHANGED_FILES.md`
- `PH_F01_INTEGRATION_MATRIX.md`
- `PH_F01_TEST_REPORT.md`
- `docs/Project_Harness_Documentation_v0.5.0/PH_F01_INTEGRATION_MATRIX.md`
- `tests/fixtures/ph_f01/brownfield_project_input.json`
- `tests/fixtures/ph_f01/brownfield_repository/README.md`
- `tests/fixtures/ph_f01/brownfield_repository/existing.py`
- `tests/fixtures/ph_f01/fixture_contracts.json`
- `tests/fixtures/ph_f01/greenfield_mvp_project_input.json`
- `tests/ph_f01_fixtures.py`
- `tests/reports/PH_F01_existing_117_tests.log`
- `tests/reports/PH_F01_regressions_expected_red.log`
- `tests/test_ph_f01_gate_semantics_regression.py`
- `tests/test_ph_f01_planner_regression.py`

## Изменённые исходные файлы

- `CHANGELOG.md`
- `MANIFEST.sha256`
- `README.md`
- `TEST_REPORT_v0.5.0.md`
- `docs/Project_Harness_Documentation_v0.5.0/CHANGELOG.md`
- `docs/Project_Harness_Documentation_v0.5.0/FILE_INDEX.md`
- `docs/Project_Harness_Documentation_v0.5.0/MANIFEST.sha256`
- `docs/Project_Harness_Documentation_v0.5.0/Project_Harness_Architecture_v0.5.0_FULL.md`
- `docs/Project_Harness_Documentation_v0.5.0/README.md`
- `docs/Project_Harness_Documentation_v0.5.0/VALIDATION_REPORT.md`

## Исключено из поставки

- Временные логи и scratch workspace вне Engine/Documentation archive, `.pyc`, `__pycache__`;
- В v0.5.0 runtime не добавлено ни одной новой команды/схемы, ни одна семантика не исправлена в PH-F01;
- Встроенный wheel оставлен прежним, поскольку изменения затрагивают только source test fixtures и документационные материалы.

**Примечание:** `MANIFEST.sha256` перегенерируется только после финализации отчёта; он включён в изменённые исходные файлы, но не хэширует сам себя. Генерируемые файлы `FILE_INDEX.md`/агрегаты документации обновлены автоматически.
