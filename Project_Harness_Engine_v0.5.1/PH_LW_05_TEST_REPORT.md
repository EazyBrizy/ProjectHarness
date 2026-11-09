# PH-LW-05 — фактический тестовый и security-отчёт

**Дата:** 2026-11-04. **Версия:** 0.5.1 WIP / NOT RELEASED. **Вердикт:** код PH-LW-05 реализован; Linux core/ZIP/wheel/doc tests — PASS; **Windows 11 x64/NTFS, pinned Flask/Waitress real HTTP/browser и реальный Podman/per-Run egress — NOT RUN / NO-GO**. Это не финальный релиз v0.5.1 и не сертификат Windows readiness.

## 1. База и объём

- Входной Engine `Project_Harness_Engine_v0.5.1_PH_LW_04.zip`: SHA-256 `a6b99afe94c24b5dca08b5ab5d56ef308e6a5eaec3b2d35ead64e8e83320e79d`; Documentation `Project_Harness_Documentation_v0.5.1_PH_LW_04.zip`: SHA-256 `88f92ee2e41f7070c1099fd44ca6bebd69bd02c6d07017e7d69320cc37554eaf`. На входе ZIP CRC — PASS, все 1067/1067 Engine и 142/142 Docs file-manifest records совпали. Spec ZIP SHA-256 `56bca615b7da5a0f48d0479c2de24ccd151fcefbf453fdfea89eab0d2675219e` не изменён.
- Исполнялся **только PH-LW-05** из `PH_LW_05.md`: safe MD/ZIP importer, карантин, immutable snapshots, source revision/ledger + source refresh, контролируемый UI «Документы», защищённые операции API, документация, tests/fixtures. Новые PDF/DOCX/RAR/7z, OCR, remote URLs, terminal/shell, automatic execution, Stage/Gate/approval bypass и provider API не добавлены.
- Среда фактического выполнения: `Linux 6.18.57`, Python `3.13.5`. Native Windows 11 x64/NTFS **не доступен**, pinned Flask 3.1.3 / Waitress 3.0.2 **не установлены**. PowerShell `local_web/ci_ph_lw_05_windows.ps1` только подготовлен, **ни разу не выполнялся**.

## 2. Исполненные команды и итоги

| Проверка / команда | Фактический итог | Лог |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_lw_05_import` | **PASS**, 14/14. ZIP Slip, Windows/UNC/device/ADS, Unicode/case collisions, symlinks/special/reparse, encrypted/nested ZIP, CRC, budget, invalid UTF-8, revision, no-doc, no shell, interruption/recovery | `PH_LW_05_LOGS/PH_LW_05_TARGETED_FINAL.log`, `...AFTER_COLLISION.log` |
| PH-LW-01…05 combined `python -m unittest -q tests.test_ph_lw_01_contract tests.test_ph_lw_02_windows_core tests.test_ph_lw_03_service tests.test_ph_lw_04_http tests.test_ph_lw_05_import tests.test_ph_lw_05_http` | **70 ran, 16 SKIP, 0 FAIL**; skips — **NOT RUN**, не PASS | `PH_LW_05_LOGS/PH_LW_05_PREVIOUS_PLUS_TARGETED.log` |
| Отдельно все `tests/test_*.py` как `python -m unittest -q tests.<module>` с bounded timeout и последующим extended recheck | **36/36 modules PASS, 0 unresolved FAIL/TIMEOUT**; суммарно **412 ran, 18 skipped**. Это не один монолитный транзакционный прогон. | `PH_LW_05_LOGS/REGRESSION_MODULES/FINAL_MATRIX.json`, индивидуальные `.log` |
| Начальная regression matrix (до исправления executable permission распаковщика) | 31 PASS, 3 FAIL: только `PermissionError` для `bin/project-harness` (в исходном ZIP mode 755, staging extraction потерял mode), 2 TIMEOUT при лимите 75s. После восстановления mode 755 **3 modules PASS**, 2 extended modules **PASS** при 240s. Не объявляем начальный прогон зелёным. | `PH_LW_05_LOGS/REGRESSION_MODULES/MATRIX.json`, `*_RECHECK.log` |
| `python -m py_compile ...` + `node --check src/.../assets/app.js` | **PASS**, синтаксис Python и JavaScript | `PH_LW_05_LOGS/PH_LW_05_STATIC_CHECKS.log` |
| `python -m pip wheel --no-deps --no-build-isolation --no-index --wheel-dir <wheel-dir> .` | **PASS**, wheel `project_harness_engine-0.5.1-py3-none-any.whl`, SHA-256 `45660aec28c04260382c434e42657e9d5cc882dab36a6a60232369b240c1289e` | `PH_LW_05_LOGS/PH_LW_05_WHEEL_BUILD.log` |
| Новый Python venv + `pip install --no-index --no-deps` wheel; installed `project-harness --version`, `doctor`, `ui --help`; импорт новых modules/assets | **PASS** на Linux, без HTTP listener | `PH_LW_05_LOGS/PH_LW_05_WHEEL_INSTALL.log`, `...WHEEL_SMOKE.log`, `...WHEEL_MODULES.log` |
| Installed `project-harness ui --no-browser`, без pinned deps | **EXPECTED DENIAL**, exit 2, `VALIDATION_FAILED`, **не** HTTP PASS | `PH_LW_05_LOGS/PH_LW_05_UI_MISSING_DEP_FAILCLOSED.log` |
| Source-tree `PYTHONPATH=src:. python project-harness.py doctor` после regeneration manifest | **PASS**, resources, manifests, schemas/registries | `PH_LW_05_LOGS/PH_LW_05_SOURCE_DOCTOR_FINAL.log` |
| Documentation validator `python tools/validate_documentation.py <docs-root> --zip <docs-zip> --json <result>` | **PASS**, 36 checks, 144 files, 0 errors, 0 warnings, fresh aggregate/index and manifest | `PH_LW_05_LOGS/PH_LW_05_DOC_ZIP_VALIDATION.json` |
| `python -m unittest -v tests.test_ph_lw_05_http` | **3 tests SKIPPED: NOT RUN** (Flask unavailable) | `PH_LW_05_LOGS/PH_LW_05_HTTP_DEPENDENCY_RESULT.log` |
| Real Flask multipart, Waitress socket/session/CSRF/body limit, Microsoft Edge browser no-network/XSS | **NOT RUN**, HTTP dependencies and browser server unavailable | Windows/HTTP environment blocker |
| Native Windows 11 x64 NTFS path/reparse/race, pinned installed Windows wheel | **NOT RUN / WINDOWS_NOT_TESTED** | Requires native `ci_ph_lw_05_windows.ps1` execution |
| Rootless Podman security and governed positive per-Run egress | **NOT RUN / inherited NO-GO**; вне scope PH-LW-05 | Existing PH-051-12 blockers preserved |

## 3. Обнаруженные ограничения и точная семантика

- Import только для **provisional managed GREENFIELD intake**; существующие Project Instances, Brownfield/Hybrid project creation from this UI и silently changing accepted history — unsupported. Отдельный public `refresh_intake_sources` проверяет source revision + current draft digest и сбрасывает draft approvals, не вызывает `start_intake(force=True)`.
- `append` byte-identical = `UNCHANGED`; change source name collision rejects, controlled `replace` increments revision. Источники находятся вне `.harness` control plane. ZIP entries всех видов проходят path/CRC/budget validation; неподдерживаемые extensions учитываются как skipped, но не исполняются.
- Для post-prepare projects, которые подготовлены **через Local Web service**, импорт запрещён по recorded prepare action. Если подготовка была выполнена сторонним CLI вне service, UI не имеет отдельного receipt; исторические immutable accepted records всё равно не переписываются, однако оператор должен использовать формальный governed route и не принимать обновлённый intake за accepted baseline. Ограничение задокументировано.
- ZIP filename/path cases и fault-injection на Linux доказывают только реализованную Python policy. Windows NTFS reparse-escape / casefold / network-root and real WSGI checks необходимы до Windows/HTTP GO; нет ложного признания mock PASS.
- Отдельный full monolithic `tests/run_tests.py` в этом шаге **NOT RUN** (предыдущая PH-LW-04 попытка завершилась TIMEOUT 240s). Вместо этого пройдены все 36 modules с индивидуальными логами и extended timeouts.

## 4. Условия поставки и решение

Engine/Documentation mirrors и source/build/lib синхронизированы. SHA-256 manifests сгенерированы для конечного содержимого; ZIP CRC, manifest, source doctor и smoke на распакованном Engine проверяются отдельно в финальном packaging log. Внешние SHA-256 ZIP приведены в `PH_LW_05_SHA256.txt`, не вычисляются из исторических отчётов.

**PH-LW-05: implementation completed with platform acceptance gaps; full v0.5.1 remains WIP / NO-GO.** Зелёные unit-tests/installed wheel/ZIP **не** закрывают обязательные native Windows/browser HTTP проверки или прежний Podman/egress NO-GO.
