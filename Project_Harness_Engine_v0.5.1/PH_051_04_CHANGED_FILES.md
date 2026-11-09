# PH-051-04 — точный перечень изменённых файлов

**Scope:** disposable runtime root, safe product snapshot, bounded control projection, signed execution binding phase, exclusions from handoff, tests, release mirrors/docs/logs. Version 0.5.1 WIP.

**Сравнение:** SHA256 содержимого против последних Engine `(2)` и Documentation `(2)` ZIP; собственные `PH_051_04_CHANGED_FILES.md` и обновлённый `MANIFEST.sha256` включены в реестр. Переименований/удалений нет. Historical PH-051-01–03 и v0.5.0 reports не изменены.

## Engine ZIP

**Добавлено (30):**
- `PH_051_04_CHANGED_FILES.md`
- `PH_051_04_LOGS/DOC_VALIDATION_FINAL.json`
- `PH_051_04_LOGS/DOC_VALIDATION_FINAL.log`
- `PH_051_04_LOGS/REGRESSION_MODULE_GROUPS.txt`
- `PH_051_04_LOGS/REGRESSION_STATUS`
- `PH_051_04_LOGS/REGRESSION_group_1.log`
- `PH_051_04_LOGS/REGRESSION_group_2.log`
- `PH_051_04_LOGS/REGRESSION_group_2_LONG.log`
- `PH_051_04_LOGS/REGRESSION_group_3.log`
- `PH_051_04_LOGS/REGRESSION_group_4.log`
- `PH_051_04_LOGS/REGRESSION_group_5.log`
- `PH_051_04_LOGS/REGRESSION_group_6.log`
- `PH_051_04_LOGS/REGRESSION_group_7.log`
- `PH_051_04_LOGS/REGRESSION_group_8.log`
- `PH_051_04_LOGS/TARGETED_FINAL.log`
- `PH_051_04_LOGS/WHEEL_BUILD_FINAL.log`
- `PH_051_04_LOGS/WHEEL_DOCTOR_FINAL.log`
- `PH_051_04_LOGS/WHEEL_INSTALL_FINAL.log`
- `PH_051_04_LOGS/WHEEL_PROJECT_AFTER_FINAL.json`
- `PH_051_04_LOGS/WHEEL_PROJECT_BEFORE_FINAL.json`
- `PH_051_04_LOGS/WHEEL_ROOT_E2E_FINAL.log`
- `PH_051_04_LOGS/WHEEL_SNAPSHOT_API.log`
- `PH_051_04_LOGS/WHEEL_VERSION_FINAL.log`
- `PH_051_04_LOGS/run_regression_groups.sh`
- `PH_051_04_LOGS/run_slow_group.sh`
- `PH_051_04_TEST_REPORT.md`
- `build/lib/project_harness/execution_roots.py`
- `docs/Project_Harness_Documentation_v0.5.1/05_Updates/08_Disposable_Execution_Root_v0.5.1_WIP.md`
- `src/project_harness/execution_roots.py`
- `tests/test_ph_051_04_disposable_roots.py`

**Изменено (17):**
- `CHANGELOG.md`
- `MANIFEST.sha256`
- `MANUAL_INSTALL.md`
- `README.md`
- `build/lib/project_harness/archive.py`
- `build/lib/project_harness/safety.py`
- `dist/project_harness_engine-0.5.1-py3-none-any.whl`
- `docs/Project_Harness_Documentation_v0.5.1/CHANGELOG.md`
- `docs/Project_Harness_Documentation_v0.5.1/FILE_INDEX.md`
- `docs/Project_Harness_Documentation_v0.5.1/MANIFEST.sha256`
- `docs/Project_Harness_Documentation_v0.5.1/Project_Harness_Architecture_v0.5.0_FULL.md`
- `docs/Project_Harness_Documentation_v0.5.1/README.md`
- `docs/Project_Harness_Documentation_v0.5.1/VERSION.md`
- `src/project_harness/archive.py`
- `src/project_harness/safety.py`
- `src/project_harness_engine.egg-info/PKG-INFO`
- `src/project_harness_engine.egg-info/SOURCES.txt`

**Удалено:** нет

## Documentation ZIP

**Добавлено (1):**
- `05_Updates/08_Disposable_Execution_Root_v0.5.1_WIP.md`

**Изменено (6):**
- `CHANGELOG.md`
- `FILE_INDEX.md`
- `MANIFEST.sha256`
- `Project_Harness_Architecture_v0.5.0_FULL.md`
- `README.md`
- `VERSION.md`

**Удалено:** нет
