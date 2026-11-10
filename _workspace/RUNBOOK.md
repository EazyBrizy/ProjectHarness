**Обязательное правило пользователя от 2026-11-09: проверяем только то, что меняем, и доказанные прямые зависимости. Весь движок, полный core regression и всю PH-LW matrix при каждой правке не запускать. Полный прогон — только по отдельному явному запросу пользователя. Уже прошедшие проверки без новых изменений или конкретной причины не повторять.** Это правило имеет приоритет над историческими командами ниже. [Подробное правило](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/27_Targeted_Verification.md).

Актуальный PH-LW-12: **GO с принятыми ограничениями; три blockers CLOSED.** [Новый отчёт/команды](../Project_Harness_Engine_v0.5.1/PH_LW_12_FIX_TEST_REPORT.md), [evidence index](../Project_Harness_Engine_v0.5.1/PH_LW_12_FIX_LOGS/EVIDENCE_INDEX.json), [CURRENT_TASK](CURRENT_TASK.md). Только Windows; Linux/WSL/Docker не запускать. Automatic executor выключен; Engine/Documentation ZIP не создавать.

Read-only проверка текущих bytes: `.\.venv\Scripts\python.exe -B tools/ph_lw_12_fix_integrity.py`. Полная Windows matrix: `tools/ph_lw_12_fix_suite_05.py nonbrowser` и `browser`; fresh maturity — `tools/ph_lw_12_fix_maturity_driver_05.py`; реальные EXE/recovery — `tools/ph_lw_12_fix_runs_05.py delivery`. Это exact-command references выполненных runs, не команды для слепого повтора: raw helpers отказываются перезаписывать имена, для нового run выбрать новые directories/labels. Native launcher/frozen suites выполнять последовательно из-за SID mutex; браузерные scripts не открывают видимых окон.

После source/docs changes необходимы новый freeze/build и затронутая приёмка. После report-only изменений: `tools/sync_working_tree.py` без `--build-wheel`, затем `tools/ph_lw_12_fix_verify.py`. Artifact PASS не заменяет acceptance verdict. Четыре ранее принятых NOT RUN и два capability SKIP не открывать заново и не называть PASS. Исторические NO-GO и archives сохраняются; ниже — предыдущие checkpoints.

Актуальный PH-LW-12 — Windows-only, **NO-GO**: [фактические команды/logs](../Project_Harness_Engine_v0.5.1/PH_LW_12_TEST_REPORT.md), [evidence index](../Project_Harness_Engine_v0.5.1/PH_LW_12_LOGS/EVIDENCE_INDEX.json), [CURRENT_TASK](CURRENT_TASK.md). Linux/WSL/Docker jobs не запускать. Старые platform commands ниже — история, не разрешение их выполнить. Четыре принятых NOT RUN не открывать заново. Новые runs писать в новые directories; helpers отказываются перезаписывать logs. Native launcher/frozen suites выполнять последовательно из-за SID mutex. Automatic executor выключен; Engine/Documentation ZIP не создавать.

Read-only повтор целостности: `.\.venv\Scripts\python.exe -B tools/ph_lw_12_integrity.py`. После code/docs changes — новый freeze/build/acceptance; после report-only изменений — `tools/sync_working_tree.py` без `--build-wheel`, затем `tools/ph_lw_12_verify.py`. PASS verifier — целостность, не изменение NO-GO. Ниже — история checkpoints.

PH-LW-10: native Windows runner `Project_Harness_Engine_v0.5.1/local_web/ci_ph_lw_10_windows.ps1 -PythonExecutable <absolute Python 3.14> -LogDirectory <new log directory> -SkipRegressions`; remaining modules отдельно через `tools/run_regressions.py`. Installed wheel — `tools/verify_installed.py --engine <absolute Engine> --manual-migration --ph-lw-06 --ph-lw-07 --ph-lw-08 --ph-lw-09 --ph-lw-10` из независимой venv/Unicode CWD с пустым PYTHONPATH. [Результаты и точные команды](../Project_Harness_Engine_v0.5.1/PH_LW_10_TEST_REPORT.md). ZIP не создаются; PH-LW-11 не запускается.

# Рабочие команды

Для чистого Git checkout на другом компьютере: [REPOSITORY_RUNBOOK.md](REPOSITORY_RUNBOOK.md), затем `python -B tools/check_repository.py`. Следующие workspace commands проверяют также локальные inputs, generated build и прежние raw runs; Git preflight их не требует.

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

## PH-LW-07: отдельные согласования, без ZIP

[Операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/14_PH_LW_07_Separate_Approvals.md), [фактический отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_07_TEST_REPORT.md). Native stage07 включает PH-LW-04–07; installed-wheel suite дополнительно сохраняет manual migration. Source regressions выполняются отдельно целиком, с прежними FAIL/SKIP.

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$python = Join-Path $PWD '.venv/Scripts/python.exe'
& $python tools/sync_working_tree.py --build-wheel
powershell.exe -NoProfile -File Project_Harness_Engine_v0.5.1/local_web/ci_ph_lw_07_windows.ps1 -PythonExecutable $python -LogDirectory (Join-Path $PWD '_scratch/ph_lw_07-new/native') -SkipRegressions
& $python tools/run_regressions.py --output _scratch/ph_lw_07-new/regressions --jobs 3 --timeout 900
```

Для wheel создать отдельную venv, offline установить pinned runtime/dev deps с `--require-hashes`, затем точный wheel `--no-deps --no-index`. Из отдельной Unicode CWD и с пустым PYTHONPATH:

```powershell
& $wheelPython $absoluteVerifyInstalledScript --engine $absoluteEngine --manual-migration --ph-lw-06 --ph-lw-07
```

Все команды конкретного checkpoint, interpreter/deps/platform/exit и raw log hashes сохранены в `Engine/PH_LW_07_LOGS`; исходники logs — `_scratch/ph_lw_07`. В новых прогонах использовать новые каталоги. Native screenshot directory можно явно задать через `PH_LW_07_SCREENSHOT_DIR`; snapshots содержат только fixtures.

`tools/finalize_ph_lw_07_evidence.py` — сборщик завершённых runs именно этого checkpoint, не универсальный updater. Он проверяет полноту matrix и сравнение с PH-LW-06, публикует redacted copies без uploads/auth/venv, сохраняет ранние FAIL. `tools/verify_ph_lw_07_working_tree.py` аттестует exact распакованную пару после docs/reports/manifests и проверяет историю, исходные schemas/tests, wheel и raw/published evidence hashes. Для будущей задачи нужны новый output и новый baseline, а не перезапись исторической аттестации.

PH-LW-08 не запускать без отдельного задания. Final UI approval сейчас оставляет `PREPARATION_PENDING_PH_LW_08`; это не созданный Project Instance. Engine/Documentation ZIP в этих командах не создаются.

## PH-LW-08: подготовка и публикация, без архивов поставки

Назначение PH-LW-08 получено отдельным заданием. Предыдущие команды и результаты PH-LW-07 выше — история; PH-LW-09 требует следующего задания.

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$python = Join-Path $PWD '.venv/Scripts/python.exe'
& $python tools/sync_working_tree.py --build-wheel
powershell.exe -NoProfile -File Project_Harness_Engine_v0.5.1/local_web/ci_ph_lw_08_windows.ps1 -PythonExecutable $python -LogDirectory (Join-Path $PWD '_scratch/ph_lw_08-new/native') -SkipRegressions
& $python tools/run_regressions.py --output _scratch/ph_lw_08-new/regressions --jobs 3 --timeout 1800
```

Installed wheel: отдельная venv, offline runtime/dev locks с `--require-hashes`, точный wheel `--no-index --no-deps`, Unicode CWD и пустой source PYTHONPATH. К `verify_installed.py --engine <absolute-engine> --manual-migration --ph-lw-06 --ph-lw-07` добавить `--ph-lw-08`. Stage08 включает реальный Waitress/TCP/Edge, process crash, readonly/junction/locked-handle и no-clobber scenarios. Все результаты публикуются в новых `PH_LW_08_LOGS`, не заменяя PH-LW-07.

Runtime product handoff ZIP является output `prepare_handoff` и проверяется в fixtures. Engine/Documentation ZIP не создавать. Source/build/package inputs после начала финального native/wheel run не менять; metadata change закономерно делает pending preparation stale. `PH_LW_08_TEST_REPORT.md` связывает точные inputs/outputs и результаты. Автоматический executor выключен.

## PH-LW-09: Task/Run manual console, без ZIP

[Операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/16_PH_LW_09_Task_Run_Manual_Console.md). Использовать новый каталог логов; старые runs не перезаписывать.

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$python = Join-Path $PWD '.venv/Scripts/python.exe'
& $python tools/sync_working_tree.py --build-wheel
powershell.exe -NoProfile -File Project_Harness_Engine_v0.5.1/local_web/ci_ph_lw_09_windows.ps1 -PythonExecutable $python -LogDirectory (Join-Path $PWD '_scratch/ph_lw_09-new/native') -SkipRegressions
& $python tools/run_regressions.py --output _scratch/ph_lw_09-new/regressions --jobs 3 --timeout 1800
```

Native PH-LW-09 runner включает PH-LW-04–09 и требует настоящий non-admin Windows 11 x64/NTFS/Python 3.14, pinned Flask/Waitress и Edge. Test fixtures явно имитируют внешнего агента; это не Codex/Podman evidence. Browser suites в source и installed wheel выполнять последовательно. Проверка без consent не запускает product commands; повторный verify сохраняет предыдущие immutable reports/evidence.

Installed wheel: создать отдельную venv, установить pinned runtime/dev locks offline с `--require-hashes`, затем точный wheel `--no-deps --no-index`. Из отдельной Unicode CWD, с пустым PYTHONPATH, передать в `tools/verify_installed.py` флаги `--manual-migration --ph-lw-06 --ph-lw-07 --ph-lw-08 --ph-lw-09` и абсолютный `--engine`. `tools/setup_ph_lw_09_wheel.py` относится к этому checkpoint и не перезаписывает существующую среду.

`tools/finalize_ph_lw_09_evidence.py` публикует только завершённые выбранные runs, сохраняет ранние FAIL/INTERRUPTED, сверяет полную matrix с PH-LW-08 и frozen source/wheel. После report/navigation выполнить `sync_working_tree.py` без rebuild и `tools/verify_ph_lw_09_working_tree.py`: exact manifests/mirrors/wheel, doctor/docs, история, schemas/registries/старые tests, archive hashes и raw/published evidence. Engine/Documentation ZIP не создаются. PH-LW-10 — только после нового задания.

В текущем checkpoint PH-LW-09 выявлен новый PH-F06 manual lifecycle blocker: четыре метода не запускаются из-за setUpClass ERROR на missing manual proof. Сборщик evidence ожидает и явно сохраняет это отличие от PH-LW-08; integrity PASS не означает stage PASS. Для устранения blocker нужен новый output/baseline и отдельная работа над согласованным Task-level manual evidence путём; не удалять manual checks и не возвращать PASS по permission flag.

## PH-LW-09: Task manual evidence reacceptance

Предыдущее описание blocker — история первого NO-GO. [Новый report](../Project_Harness_Engine_v0.5.1/PH_LW_09_MANUAL_EVIDENCE_TEST_REPORT.md), [контракт/операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/17_PH_LW_09_Task_Manual_Evidence.md). Новые outputs: `_workspace/PH_LW_09_MANUAL_EVIDENCE`, Engine `PH_LW_09_MANUAL_EVIDENCE_LOGS`. Сохранять прежние outputs и каждый raw FAIL. Native current test matrix объединяет полный run и точечный повтор одного Edge case; installed current matrix — полный run и один import UI recheck. Монолитные exits остаются FAIL, не переписываются. Таймауты и semantic assertions не ослаблены. PH-F06 повторён отдельно после product-process timeout. Полная module matrix сохраняет семь прежних FAIL.

`tools/finalize_ph_lw_09_manual_evidence.py` требует точные исходные failed IDs и успешные соответствующие rechecks; `tools/verify_ph_lw_09_manual_evidence.py` проверяет источники, tests, source/wheel freeze, историю, manifests, mirror, raw/published hashes и doctor/docs. Эти helpers одноразовые для текущего checkpoint; новые задачи пишут новые evidence. `tools/verify_installed.py --case <exact-test-id>` повторяет один явно заданный failed case, сохраняя site-packages/build/console/health checks; он не заменяет исходный полный log. PH-LW-01 inventory-test теперь строго учитывает ровно две новые CLI команды сверх прежних 26 controls + launcher. Не отключать missing manual proof и не возвращать PASS по allow_manual. Automatic executor выключен, PH-LW-10 и ZIP — только по отдельному заданию.

## PH-LW-11 — отдельные build и acceptance

[Отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_11_TEST_REPORT.md) содержит NO-GO и completed/composite results. `Engine/local_web/windows/build_windows.py --output <NEW> --iscc <ABS_ISCC>` проверяет CPython 3.14.10/PyInstaller 6.22.3/Inno 6.7.4 и hash pins. Source runner `ci_ph_lw_11_windows.ps1`, actual installed EXE runner `windows/acceptance.py`, actual interruption/read-only/retry `installer_fault_acceptance.py` — разные evidence. Они управляют только own test fixtures; не запускать одновременно с личным Harness или mutex test. Для каждого run выбирать новый output.

`verify_installed.py --ph-lw-11` добавляет desktop tests, `--case` задаёт targeted suite. Пустой PYTHONPATH, независимые venv/CWD, explicit msedge. Legacy fixture tests могут быть длительными; timeout/abort не превращать в PASS. После наблюдаемого Edge close stall минимальный about:blank diagnostic сохранён; не ослаблять assertions и защиту Windows ради PASS.

`finalize_ph_lw_11.py` публикует allowlisted logs/JSON/screenshots и method-level composite matrix, без auth/private uploads. `report_ph_lw_11.py` пишет report/CURRENT_TASK/navigation. После reports: `sync_working_tree.py` без build-wheel и `verify_ph_lw_11.py`. Integrity PASS не означает stage GO. Source/docs изменения требуют новой frozen/wheel сборки и применимых rechecks. Исторические reports/archives не переписывать, ZIP без запроса не создавать.

## PH-LW-11 — long-path дополнение

Отдельный output/baseline: `_workspace/PH_LW_11_LONG_PATH`, `Engine/PH_LW_11_LONG_PATH_LOGS`; [отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_TEST_REPORT.md). Не перезаписывать прежнюю PH-LW-11 аттестацию.

Targeted source tests: `tests.test_ph_lw_11_long_path`. Independent installed wheel использует прежний `verify_installed.py --case ...`, empty PYTHONPATH/Unicode CWD/explicit msedge. `local_web/windows/long_path_acceptance.py` запускает прежние 4 EXE assertions, адаптируя startup roots и полный fixture snapshot IO; runtime-root должен быть новым длинным Unicode path, --app-data-root — отдельным новым коротким fixture path. Не менять registry/защиту Windows и не сокращать project path ради PASS. Первый длинный app-data ZIP-import FAIL сохраняется отдельно. Installer recovery — прежний `installer_fault_acceptance.py` с новым output.

`finalize_ph_lw_11_long_path.py` публикует только allowlisted evidence, `report_ph_lw_11_long_path.py` пишет новый report/navigation, затем `sync_working_tree.py` без rebuild и `verify_ph_lw_11_long_path.py`. Изменение wheel/frozen inputs требует новой сборки и применимых проверок. Никаких Engine/Documentation ZIP и перехода к PH-LW-12 без нового задания.

## PH-LW-11 — long app-data ZIP-import

Новое задание разрешило соседний ZIP IO fix: `_workspace/PH_LW_11_ZIP_PATH`, `Engine/PH_LW_11_ZIP_PATH_LOGS`, [новый отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_11_ZIP_PATH_TEST_REPORT.md). Старые LONG_PATH и исходные PH-LW-11 reports/attestations не перезаписывать.

Target `tests.test_ph_lw_11_zip_path` (7): public upload/replay/replace, old snapshots, hostile ZIP bytes/CRC/budgets, explicit recovery, deep tamper/junction/hardlink/copy-time guard. Независимый snapshot reader читает все deep files. `zip_path_acceptance.py` сохраняет прежние 4 installed-EXE assertions/deadlines; default app-data root находится внутри длинного output, длинный Unicode runtime-root новый для каждого run. Не применять прежний short app-data workaround для закрытия ZIP blocker, не менять registry/защиту Windows.

Wheel: fresh venv, pinned hash locks, empty PYTHONPATH/Unicode CWD/explicit msedge, `run_ph_lw_11_zip_path_wheel.py`. `check_ph_lw_11_zip_path_logic.py` — AST proof в дополнение к runtime tests. Build/freeze → applicable tests → `finalize_ph_lw_11_zip_path.py` → `report_ph_lw_11_zip_path.py` → sync manifests без rebuild → `verify_ph_lw_11_zip_path.py`. Source/docs/wheel inputs после freeze не менять; изменения требуют rebuild/retest. Evidence publisher использует allowlist и не публикует app-data/auth/raw uploads. Engine/Documentation ZIP и PH-LW-12 без отдельного задания запрещены.

Пользователь запретил новые видимые browser windows: ручной UI — в уже открытом авторизованном окне. Автотесты Edge headless. В zip_path_acceptance второй процесс запускается с --no-browser и должен получить точный отказ exit 1, сохранив first process/catalog; обычный browser-opening second launch — свежий NOT RUN. Не менять production launcher или ослаблять auth ради этой проверки.

## PH-LW-11 — принятые пользователем ограничения приёмки, 2026-11-08

[Решение](../Project_Harness_Engine_v0.5.1/PH_LW_11_ACCEPTANCE_SCOPE_DECISION.md), [decision JSON](PH_LW_11_ACCEPTANCE_SCOPE/DECISION.json), [проверка](PH_LW_11_ACCEPTANCE_SCOPE/VERIFICATION.json). Clean-machine Windows, physical offline, real disk-full и actual Unicode Windows username: фактически NOT RUN, но не блокируют PH-LW-11 и не являются обязательными будущими прогонами. Не требовать их как prerequisite без нового явного задания пользователя. Текущий PH-LW-11 GO — в согласованном объёме с принятыми ограничениями. Старые prompt/NO-GO/evidence не переписывать, NOT RUN не превращать в PASS.

Решение вынесено за runtime package: source/tests/docs mirrors/wheel/frozen/installer неизменны, runtime tests повторно не запускались. Проверяются ссылки, документационная связность, manifests, before/after hashes и сохранность старых evidence. LOCAL_WEB_MANUAL NO-GO до отдельно разрешённого PH-LW-12; automatic executor выключен, полная v0.5.1 NO-GO. Не открывать новые видимые browser windows; использовать открытое авторизованное окно для ручного UI. Engine/Documentation ZIP не собирать без явного запроса.
