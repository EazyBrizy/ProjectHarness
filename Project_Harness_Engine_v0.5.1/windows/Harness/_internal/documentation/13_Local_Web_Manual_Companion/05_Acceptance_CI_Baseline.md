# Test baseline, Windows CI и acceptance без ложных PASS

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Этап подготовки:** PH-LW-01, 2026-11-01  
**Статус:** CONTRACT DESIGN / NOT IMPLEMENTED / NATIVE WINDOWS NOT RUN

## Правила интерпретации evidence

Статус `PASS` возможен только с реальными logs/exit, той же revision файла и тем же platform. Source manifests, unittest contract и Linux doctor не доказывают Windows importability, installed browser, NTFS locking, offline installer. Предыдущий PH-051-12 отчёт с 346 tests/2 skipped — **историческое описание из плана, его файлы не загружены**; недопустимо переносить этот счётчик в текущую фактическую строку.

## Запускаемые entrypoints PH-LW-01

Из Engine source root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_lw_01_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python tests/run_tests.py
PYTHONPATH=src:. python project-harness.py doctor
  # После сборки документации и отдельного ZIP:
python docs/Project_Harness_Documentation_v0.5.1/tools/validate_documentation.py docs/Project_Harness_Documentation_v0.5.1 --zip <absolute-docs-zip> --json <report.json>
```

На Windows из PowerShell (с исходным Engine source tree, затем в PH-LW-02/11 с wheel/frozen):

```powershell
pwsh -NoProfile -File .\\local_web\\ci_ph_lw_01_windows.ps1 -Python "py -3.14" -DocumentZip "C:\\path\\Project_Harness_Documentation_v0.5.1_PH_LW_01.zip"
```

Script должен реально проверить Windows/NTFS, source imports, dry-run contract, full regression, `doctor` и docs validator, возвращать nonzero при exception. Он не объявляет browser/installer/Podman PASS: их статус напечатан `NOT RUN` с перечислением этапов. В PH-LW-01 Linux script не выполняется как Windows proof.

## Раздельная acceptance matrix по плану r2

| Сценарии | PH-LW-01 evidence | Финальное ожидаемое подтверждение | Статус здесь |
|---|---|---|---|
| LW-E01–02 | Windows runtime/install/pinned deps decision, CI entrypoint, package-resource tests | Real Windows non-admin offline install, Unicode CWD, source/wheel/frozen starts | NOT RUN |
| LW-E03–05 | Greenfield MD / Unicode nested ZIP / no-doc fixtures | Real bounded upload, accepted/skipped inventory, no fabricated evidence | NOT RUN |
| LW-E06–10 | Strict draft-only schema, forged response, canonical approvals map | Browser/Flask validation with stale/unknown/consent negative tests | NOT RUN |
| LW-E11–13 | Existing compiler API boundaries + safe publish plan | Real approved handoff + destructive collision/Stage fence | NOT RUN |
| LW-E14–22 | 26-command API map, existing public fixture recipes | Real end-to-end manual run/Stage/Brownfield/maintenance/migration via web | NOT RUN |
| LW-E23–27 | Threat model and exact budgets | Browser+HTTP attack suite and unsafe ZIP rejection on NTFS | NOT RUN |
| LW-E28–31 | Receipt schema and core authoritative reconciliation contract | Real multi-tab/CLI concurrency/crash/restart on Windows | NOT RUN |
| LW-E32–36 | Port ownership contract, map test, version/manifest | Real second launcher, UI coverage, installer and artifact SHA | NOT RUN |
| v0.5.0/PH-051 applicable | Existing regression command, exact current baseline test log | Same source pair manual/Stage governance preserved | See external PH-LW-01 report |
| v0.5.1 Podman/egress | Historically missing real rootless self-tests, positive governed egress | Actual Podman security acceptance on its supported platform | NOT RUN / NO-GO |

**Ни один сценарий LW-E01…LW-E36 не получает E2E PASS только по наличию модели или fixtures в PH-LW-01.** Targeted contract tests подтверждают только schema/catalog/scope, а Linux legacy suite — ровно соответствующие unit/integration cases. Все изменения сугубо additive; production runtime не изменён.

## Версии/ресурсы

Wheel smoke доказывает наличие JSON companion resources без обязательного Flask import, но не frozen Windows packaging. `local_web/requirements-web-win_amd64-cp314.lock` — design pin, пока нет Windows hash-verified local wheelhouse. `local_web/wheel_inventory_v1.json` содержит exact names/hashes ожидаемых wheels. При конфликте locks/platform отказ и обновление с отдельным review, не `pip install latest`.

## Blocking readiness

1. PH-051-12 WIP zip SHA и test report не предоставлены, исходная версия PH-051-11 (внешняя контрольная запись).
2. `__init__` → `runtime` → `apply` → Unix `fcntl` blocker, и нет фактического Windows import/locking test.
3. Нет Web server, браузерного e2e, инсталлятора, офлайн wheelhouse, реальной Podman security проверки или разрешённого egress.

Ни один пункт не скрывается под `SKIP`. PH-LW-01 готовит интерфейсные требования для последующих независимых задач; `LOCAL_WEB_MANUAL=NO-GO`, `AUTOMATIC_EXECUTOR=NO-GO`, v0.5.1 release NOT RELEASED.
