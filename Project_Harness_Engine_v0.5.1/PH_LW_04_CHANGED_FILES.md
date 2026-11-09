# PH-LW-04 — фактически изменённые файлы относительно PH-LW-03

**Дата:** 2026-11-03. **Ветка:** v0.5.1-WIP / manual Local Web; не финальный релиз. Сравнение по SHA-256 содержимого каждого файла входных ZIP; списки ниже включают source/build mirrors. В конце добавлены отчётные записи, отсутствовавшие в сравнении начального stage.

**Допустимые области:** Local Web HTTP/auth, защищённый launcher и `ui` CLI, application service read-only catalog/download, package data/assets, security tests и Windows test script, operator docs, sync/wheel/manifests. Изменение одного исторического PH-LW-01 теста ограничено учётом новой команды `ui`, не изменяет его 26 бизнес-команд. Реестр, стадийный runtime, sandbox/Podman и нормативные спецификации не изменялись.

**Input provenance:** Engine PH-LW-03 SHA-256 `586ea587afa47bf787861c577480762547f36ff8849374917a3911a8ef3d3860`; Docs PH-LW-03 SHA-256 `e7adc0ab63bb86c0a798398f6deef38fecc848941c3fabe5e9afd0dbd1c18510`. Нормативные v0.5.0/v0.5.1 SHA-256 `ca487d3e978af116418a597b5d05cd890d11e2e93855c9f7a312e21f083dd16f` / `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e` (из неизменного specifications ZIP).

## Engine — существовавшие и новые path

**Добавлены (13):**

- `build/lib/project_harness/local_web_http.py`
- `build/lib/project_harness/local_web_launcher.py`
- `build/lib/project_harness/resources/local_web/assets/app.css`
- `build/lib/project_harness/resources/local_web/assets/app.js`
- `build/lib/project_harness/resources/local_web/assets/index.html`
- `docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/09_PH_LW_04_Loopback_HTTP_Session_and_UI_Shell.md`
- `local_web/ci_ph_lw_04_windows.ps1`
- `src/project_harness/local_web_http.py`
- `src/project_harness/local_web_launcher.py`
- `src/project_harness/resources/local_web/assets/app.css`
- `src/project_harness/resources/local_web/assets/app.js`
- `src/project_harness/resources/local_web/assets/index.html`
- `tests/test_ph_lw_04_http.py`

**Изменены (20):**

- `CHANGELOG.md`
- `MANUAL_INSTALL.md`
- `README.md`
- `build/lib/project_harness/cli.py`
- `build/lib/project_harness/local_web_service.py`
- `build/lib/project_harness/resources/local_web/metadata_v1.json`
- `dist/project_harness_engine-0.5.1-py3-none-any.whl`
- `docs/Project_Harness_Documentation_v0.5.1/CHANGELOG.md`
- `docs/Project_Harness_Documentation_v0.5.1/FILE_INDEX.md`
- `docs/Project_Harness_Documentation_v0.5.1/MANIFEST.sha256`
- `docs/Project_Harness_Documentation_v0.5.1/Project_Harness_Architecture_v0.5.0_FULL.md`
- `docs/Project_Harness_Documentation_v0.5.1/README.md`
- `pyproject.toml`
- `src/project_harness/cli.py`
- `src/project_harness/local_web_service.py`
- `src/project_harness/resources/local_web/metadata_v1.json`
- `src/project_harness_engine.egg-info/PKG-INFO`
- `src/project_harness_engine.egg-info/SOURCES.txt`
- `src/project_harness_engine.egg-info/requires.txt`
- `tests/test_ph_lw_01_contract.py`

**Удалены (0):**

Нет.

## Documentation — существовавшие и новые path

**Добавлены (1):**

- `13_Local_Web_Manual_Companion/09_PH_LW_04_Loopback_HTTP_Session_and_UI_Shell.md`

**Изменены (5):**

- `CHANGELOG.md`
- `FILE_INDEX.md`
- `MANIFEST.sha256`
- `Project_Harness_Architecture_v0.5.0_FULL.md`
- `README.md`

**Удалены (0):**

Нет.

## Артефакты сборки / отчётность

После исходного file diff в Engine добавлены `PH_LW_04_CHANGED_FILES.md`, `PH_LW_04_TEST_REPORT.md`, `PH_LW_04_PRESERVED_INVARIANTS.md`, `PH_LW_04_LOGS/`; обновлён `MANIFEST.sha256` с хэшами всех итоговых файлов, кроме самого манифеста. `dist/*.whl` действительно пересобран и проверен в изолированном virtualenv. В Documentation обновлены агрегаты, `FILE_INDEX.md`, `MANIFEST.sha256`, встроенный Engine mirror синхронизирован побайтово. В standalone Docs архив не добавлены произвольные служебные логи, чтобы не менять контракт документационного каталога. Промежуточные Python `.pyc`/`__pycache__` не поставляются.
