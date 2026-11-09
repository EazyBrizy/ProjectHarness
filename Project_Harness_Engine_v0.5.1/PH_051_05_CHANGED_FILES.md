# PH-051-05 — перечень изменённых файлов

**Scope:** только реализация Local Codex CLI Adapter через профильный `argv_template`, exact ADP/SBX loading, JIT bindings и exit/termination classification, минимальные test fixtures, документация и package mirrors. **v0.5.1 WIP / NOT RELEASED**.

**Источник сравнения:** SHA-256 individual file bytes из `Project_Harness_Engine_v0.5.1_PH_051_04.zip` и `Project_Harness_Documentation_v0.5.1_PH_051_04.zip`. Ранее принятые файлы/отчёты не изменялись. Удалённых файлов нет. `bin/project-harness` сохраняет исходный mode `0755`.

## Engine — добавлено (21)

- `PH_051_05_CHANGED_FILES.md`
- `PH_051_05_LOGS/DOC_VALIDATION_FINAL.json`
- `PH_051_05_LOGS/DOC_VALIDATION_FINAL.log`
- `PH_051_05_LOGS/REGRESSION_FULL.exit`
- `PH_051_05_LOGS/REGRESSION_FULL.log`
- `PH_051_05_LOGS/REGRESSION_INTERRUPTED_CHMOD.log`
- `PH_051_05_LOGS/ROOTLESS_ENVIRONMENT.log`
- `PH_051_05_LOGS/TARGETED_FINAL.log`
- `PH_051_05_LOGS/WHEEL_ADAPTER_API.log`
- `PH_051_05_LOGS/WHEEL_BUILD.log`
- `PH_051_05_LOGS/WHEEL_DEMO.log`
- `PH_051_05_LOGS/WHEEL_DOCTOR.log`
- `PH_051_05_LOGS/WHEEL_INSTALL.log`
- `PH_051_05_LOGS/WHEEL_MANUAL_FAIL_CLOSED.log`
- `PH_051_05_LOGS/WHEEL_NEXT.log`
- `PH_051_05_LOGS/WHEEL_VALIDATE_HANDOFF.log`
- `PH_051_05_LOGS/WHEEL_VALIDATE_PROJECT.log`
- `PH_051_05_LOGS/WHEEL_VERSION.log`
- `PH_051_05_TEST_REPORT.md`
- `docs/Project_Harness_Documentation_v0.5.1/05_Updates/09_Local_Codex_CLI_Adapter_v0.5.1_WIP.md`
- `tests/test_ph_051_05_codex_adapter.py`

## Engine — изменено (16)

- `CHANGELOG.md`
- `MANIFEST.sha256`
- `MANUAL_INSTALL.md`
- `README.md`
- `build/lib/project_harness/executors/codex_cli_local.py`
- `dist/project_harness_engine-0.5.1-py3-none-any.whl`
- `docs/Project_Harness_Documentation_v0.5.1/CHANGELOG.md`
- `docs/Project_Harness_Documentation_v0.5.1/FILE_INDEX.md`
- `docs/Project_Harness_Documentation_v0.5.1/MANIFEST.sha256`
- `docs/Project_Harness_Documentation_v0.5.1/Project_Harness_Architecture_v0.5.0_FULL.md`
- `docs/Project_Harness_Documentation_v0.5.1/README.md`
- `docs/Project_Harness_Documentation_v0.5.1/VERSION.md`
- `src/project_harness/executors/codex_cli_local.py`
- `src/project_harness_engine.egg-info/PKG-INFO`
- `src/project_harness_engine.egg-info/SOURCES.txt`
- `tests/fixtures/fake_codex_cli.py`

## Documentation — добавлено (1)

- `05_Updates/09_Local_Codex_CLI_Adapter_v0.5.1_WIP.md`

## Documentation — изменено (6)

- `CHANGELOG.md`
- `FILE_INDEX.md`
- `MANIFEST.sha256`
- `Project_Harness_Architecture_v0.5.0_FULL.md`
- `README.md`
- `VERSION.md`

## Удалено

Нет. Historical acceptance, migration и предыдущие PH-051-01–04 reports сохраняют исходные хеши.
