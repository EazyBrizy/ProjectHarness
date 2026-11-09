# Рабочие команды

Выполнять из корня общего workspace. PowerShell; env задаются только для текущего процесса. Не менять системную execution policy или защиту ОС.

```powershell
# Read-only preflight оригинальных архивов; повторная распаковка не нужна.
.\.venv\Scripts\python.exe tools/workspace_preflight.py

# Подготовленная среда этого workspace:
$python = Join-Path $PWD '.venv\Scripts\python.exe'
$engine = Join-Path $PWD 'Project_Harness_Engine_v0.5.1'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = "$engine\src;$engine"
$env:PH_LW_04_BROWSER_CHANNEL = 'msedge'
Push-Location $engine
try {
  & $python -m unittest -v tests.test_ph_lw_04_http tests.test_ph_lw_05_import tests.test_ph_lw_05_http
  & $python tests/run_tests.py
  & $python project-harness.py doctor
} finally { Pop-Location }
```

CI scripts принимают прямой `-PythonExecutable`; `-PythonVersion` для venv не нужен. Для `py` скрипт сам добавляет `-3.14`. Windows PowerShell 5.1 и native stderr учитываются через точный exit дочернего Python. Результаты — только из сохранённых logs, а не из наличия команд в этом файле.

Точный runtime lock: `Engine/local_web/requirements-web-win_amd64-cp314.lock`; inventory: `wheel_inventory_v1.json`. Сначала загрузить wheelhouse с проверкой hashes, затем offline install через `--no-index --find-links ... --require-hashes`. Dev-only Playwright/build tools фиксировать отдельно. Не менять pins ради удобства и не использовать `pip install -U`.

Документационный validator запускать после обновления aggregate/index/manifests и формирования точного Documentation ZIP. Финальный Engine ZIP проверять после распаковки; wheel устанавливать в независимую venv и запускать из другой CWD без source PYTHONPATH. Новые reports должны сохранять исходные исторические reports.

## Воспроизведение среды

Локально подготовлен официальный portable CPython 3.14.10 x64 в `_tools/Python314`, без установки в систему и изменения PATH/registry. ZIP: [python.org](https://www.python.org/ftp/python/3.14.10/python-3.14.10-amd64.zip), SHA-256 `cc28026a650970cc1570bb127312f1f9634eb67abfe157ae6ca1acbbc627d091`. Сохранённая копия — `_scratch/setup/python-3.14.10-amd64.zip`; provenance — `python-release.json` в той же папке. Для нового компьютера загрузить именно этот официальный архив, сверить hash до распаковки и выбрать пустой локальный каталог.

```powershell
& .\_tools\Python314\python.exe -m venv .venv
& .\.venv\Scripts\python.exe -m pip download --only-binary=:all: --require-hashes -r .\Project_Harness_Engine_v0.5.1\local_web\requirements-web-win_amd64-cp314.lock -d .\_tools\wheelhouse
& .\.venv\Scripts\python.exe -m pip install --no-index --find-links .\_tools\wheelhouse --require-hashes -r .\Project_Harness_Engine_v0.5.1\local_web\requirements-web-win_amd64-cp314.lock
& .\.venv\Scripts\python.exe -m pip download --only-binary=:all: --require-hashes -r .\_workspace\requirements-dev-win_amd64-cp314.lock -d .\_tools\devwheelhouse
& .\.venv\Scripts\python.exe -m pip install --no-index --find-links .\_tools\devwheelhouse --require-hashes -r .\_workspace\requirements-dev-win_amd64-cp314.lock
```

Playwright использует уже установленный Edge (`msedge`), а не отдельную скачанную браузерную сборку. Dev lock отделён от runtime. Не активировать venv через policy bypass: всегда можно вызвать `.venv/Scripts/python.exe` напрямую.

## Сборка и приёмка

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$python = Join-Path $PWD '.venv/Scripts/python.exe'
$output = '_deliverables/PH_LW_05_WINDOWS_MANUAL_REMEDIATION_2026-11-07'
$hashName = 'PH_LW_05_WINDOWS_MANUAL_REMEDIATION_SHA256.txt'
$docsZip = Join-Path $PWD "$output/Project_Harness_Documentation_v0.5.1_PH_LW_05.zip"
& $python tools/package_acceptance.py --output $output --hash-name $hashName
& $python tools/check_workspace.py
powershell.exe -NoProfile -File Project_Harness_Engine_v0.5.1/local_web/ci_ph_lw_04_windows.ps1 -PythonExecutable $python -DocumentationZip $docsZip -LogDirectory (Join-Path $PWD '_scratch/ci04') -SkipRegressions
powershell.exe -NoProfile -File Project_Harness_Engine_v0.5.1/local_web/ci_ph_lw_05_windows.ps1 -PythonExecutable $python -DocumentationZip $docsZip -LogDirectory (Join-Path $PWD '_scratch/ci05') -SkipRegressions
& $python tools/run_regressions.py --output _scratch/regressions --jobs 3 --timeout 900
& $python tools/verify_final_archives.py --output $output --hash-name $hashName --manual-migration
```

`package_acceptance.py` пересобирает wheel и aggregates, обновляет manifests/mirror и два полных ZIP. Он удаляет только проверенные generated `Engine/build`, `Engine/dist`, `Engine/local_web/windows_ci_logs`; evidence заранее сохранять вне этих каталогов. `--no-wheel` допустим только если code/resources/build inputs wheel не менялись. После отчётов повторно сформировать ZIP и проверить точную финальную пару.

`tools/run_logged.py --log ... --cwd ... --timeout ... -- COMMAND` сохраняет raw log и command/exit/time/hash; по timeout завершает только запущенное им дерево процесса. `tools/verify_installed.py` проверяет package path, doctor, реальный console launcher и 27 HTTP/import/browser tests; запускать из отдельной CWD через независимую venv с установленным wheel и пустым PYTHONPATH. Это developer acceptance, не чистая машина и не installer acceptance.

Полный legacy suite на этой Windows-среде содержит Unix/Podman/symlink requirements. Их FAIL/SKIP сохраняются и не превращаются в PASS. Каждый повторный прогон хранить отдельно; итоговая матрица должна явно указывать выбранный более свежий run.

Для повторения только manual migration: `tools/run_regressions.py --output <новый каталог> tests.test_windows_manual_migration tests.test_ph_051_10_migration_recovery.V051MigrationTests`. Весь PH-051-10 модуль смешанный: его automatic recovery failures не означают отказ этих пяти migration cases. `verify_installed.py --manual-migration` добавляет 15 migration/cleanup tests к 27 HTTP/import/browser tests (42 всего). Временные проекты fixtures не являются пользовательскими проектами; автоматический executor в этом scope не активировать.

Параметры `--output` и `--hash-name` обязательны для новой поставки: выбрать отдельный каталог, не перезаписывать исторические ZIP. `tools/finalize_evidence.py` относится только к предыдущему PH-LW-04/05 retest; текущий сборщик evidence — `tools/finalize_manual_evidence.py`.
