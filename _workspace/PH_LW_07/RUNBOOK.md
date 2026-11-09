# Рабочие команды

Выполнять из корня общего workspace. PowerShell; env задаются только для текущего процесса. Не менять системную execution policy или защиту ОС.

Все рабочие файлы проекта хранить в распакованных каталогах workspace, включая отчёты и evidence. **Engine/Documentation ZIP не собираются после каждого этапа или правки. Архивы создаются только по явному запросу пользователя для передачи в ChatGPT на анализ, когда это требуется.** Указание пользователя от 2026-11-07 заменяет прежнюю обязательную упаковку в сохранённых планах/prompts; исторические архивы и inputs сохраняются. Наличие старого ZIP не означает, что он соответствует текущим рабочим файлам.

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

Документационный validator запускать по распакованному каталогу после обновления aggregate/index/manifests; обычная проверка не требует ZIP. Без `--zip` validator выдаёт ожидаемое предупреждение `ZIP archive: zip path not supplied`: это отсутствие проверки архива, а не ошибка рабочих файлов. Только при явно запрошенной упаковке передавать точный Documentation ZIP и проверять финальный Engine ZIP после распаковки. Wheel пересобирать при изменении его входных файлов; применимую wheel acceptance выполнять в независимой venv из другой CWD без source PYTHONPATH. Новые reports должны сохранять исходные исторические reports.

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

## Проверка рабочих файлов без архивов

Для docs-only изменений обновить aggregates/index, manifests и побайтовое зеркало без вызова `package_acceptance.py` как команды упаковки:

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$python = Join-Path $PWD '.venv/Scripts/python.exe'
& $python -B -c "import runpy, shutil; from tools.package_acceptance import DOCS, ENGINE, manifest; v = runpy.run_path(str(DOCS / 'tools/validate_documentation.py')); v['build_aggregates'](DOCS); manifest(DOCS); shutil.copytree(DOCS, ENGINE / 'docs' / DOCS.name, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc')); manifest(ENGINE)"
& $python -B Project_Harness_Documentation_v0.5.1/tools/validate_documentation.py Project_Harness_Documentation_v0.5.1
```

Импорт helper-функций в этой команде не запускает упаковку и не пересобирает wheel. Проверить отсутствие лишних файлов в зеркале и сохранить logs/hashes отдельными файлами нового run. Для изменений кода дополнительно выполнить применимые tests и wheel checks. Само завершение этапа не является запросом на архивы.

## Архивы для ChatGPT — только по явному запросу пользователя

Следующий блок применять только при явном запросе архивов для анализа в ChatGPT. Это пример воспроизведения прежней поставки; для нового запроса задать новый каталог и имя hash-файла, не перезаписывая существующие результаты.

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

При явно запрошенной упаковке `package_acceptance.py` пересобирает wheel и aggregates, обновляет manifests/mirror и два полных ZIP. Он удаляет только проверенные generated `Engine/build`, `Engine/dist`, `Engine/local_web/windows_ci_logs`; evidence заранее сохранять вне этих каталогов. `--no-wheel` допустим только если code/resources/build inputs wheel не менялись. В рамках этого запроса после отчётов сформировать финальные ZIP и проверить точную пару; без запроса архивы не создавать.

`tools/run_logged.py --log ... --cwd ... --timeout ... -- COMMAND` сохраняет raw log и command/exit/time/hash; по timeout завершает только запущенное им дерево процесса. `tools/verify_installed.py` проверяет package path, doctor, реальный console launcher и 27 HTTP/import/browser tests; запускать из отдельной CWD через независимую venv с установленным wheel и пустым PYTHONPATH. Это developer acceptance, не чистая машина и не installer acceptance.

Полный legacy suite на этой Windows-среде содержит Unix/Podman/symlink requirements. Их FAIL/SKIP сохраняются и не превращаются в PASS. Каждый повторный прогон хранить отдельно; итоговая матрица должна явно указывать выбранный более свежий run.

Для повторения только manual migration: `tools/run_regressions.py --output <новый каталог> tests.test_windows_manual_migration tests.test_ph_051_10_migration_recovery.V051MigrationTests`. Весь PH-051-10 модуль смешанный: его automatic recovery failures не означают отказ этих пяти migration cases. `verify_installed.py --manual-migration` добавляет 15 migration/cleanup tests к 27 HTTP/import/browser tests (42 всего). Временные проекты fixtures не являются пользовательскими проектами; автоматический executor в этом scope не активировать.

Параметры `--output` и `--hash-name` обязательны для явно запрошенной архивной поставки: выбрать отдельный каталог, не перезаписывать исторические ZIP. `tools/finalize_evidence.py` относится к предыдущему PH-LW-04/05 retest; `tools/finalize_manual_evidence.py` — к Windows manual remediation. Для PH-LW-06 использовать отдельный сборщик ниже.

## PH-LW-06: воспроизведение без ZIP

Полный scope и результаты — [PH-LW-06 report](../Project_Harness_Engine_v0.5.1/PH_LW_06_TEST_REPORT.md). Native stage06 включает 64 runtime methods; отдельный installed-wheel run — 62 methods (27 HTTP/import/Edge + 15 migration + 20 exchange/TCP/Edge). Всю regression matrix запускать отдельно; известные FAIL/SKIP не заменять зелёным subset.

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$python = Join-Path $PWD '.venv/Scripts/python.exe'
& $python tools/sync_working_tree.py --build-wheel
& $python tools/check_workspace.py
powershell.exe -NoProfile -File Project_Harness_Engine_v0.5.1/local_web/ci_ph_lw_06_windows.ps1 -PythonExecutable $python -LogDirectory (Join-Path $PWD '_scratch/ph_lw_06-new/native') -SkipRegressions
& $python tools/run_regressions.py --output _scratch/ph_lw_06-new/regressions --jobs 3 --timeout 900
```

`sync_working_tree.py` без `--build-wheel` обновляет только docs aggregates/mirror/manifests и проверяет неизменность source build digest. При изменении source/resources нужен `--build-wheel`; исправлять build/lib вручную нельзя. Tool не создаёт Engine/Documentation ZIP. Native runner принимает `-DocumentationZip` только если архив отдельно запрошен; WARN об отсутствии ZIP соответствует рабочему режиму.

Для installed-wheel acceptance создать новую venv тем же CPython 3.14, установить обе hash-locked зависимости offline из `_tools/wheelhouse` и `_tools/devwheelhouse`, затем точный wheel через `pip install --no-deps --no-index <wheel>`. Из другой Unicode CWD с пустым PYTHONPATH и `PH_LW_04_BROWSER_CHANNEL=msedge` выполнить независимым interpreter:

```powershell
& $wheelPython $absoluteVerifyInstalledScript --engine $absoluteEngine --manual-migration --ph-lw-06
```

Проверка требует import из site-packages, console doctor/launcher и отсутствие skips. Точные исполненные команды и hashes лежат в `Engine/PH_LW_06_LOGS/runs`, не зависят от этих примерных переменных. `tools/run_logged.py` сохраняет command/exit/time/hash; для каждого нового run выбирать новый каталог.

`tools/finalize_ph_lw_06_evidence.py` публикует только завершённые logs из `_scratch/ph_lw_06`, проверяет полноту 40-модульной matrix и отделяет runtime/native, docs retest и installed wheel. Это сборщик данного checkpoint, не универсальный updater. Он сохраняет ранние FAIL и заменяет private paths только в опубликованных копиях. После отчётов выполнить `sync_working_tree.py` без rebuild и `tools/verify_ph_lw_06_working_tree.py`: exact manifests/mirrors/wheel, doctor/docs, неизменные inputs/history и внешняя аттестация в `_workspace/PH_LW_06`. Hashes не встраиваются в собственные хешируемые деревья.
