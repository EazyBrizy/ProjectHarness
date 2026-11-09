# PH-LW-03 — отчёт о реализации и проверках

**Дата:** 2026-11-02  
**Версия:** `0.5.1` **WIP / NOT RELEASED**; пакет **PH-LW-03 service-only**.  
**Execution host:** Linux x86_64, Python 3.13.5; НЕ Windows 11, НЕ NTFS, нет проверенного Windows-стенда.  
**Итог:** сервисный слой создан и протестирован на Linux; **WINDOWS_NOT_TESTED / Windows acceptance НЕ ПОДТВЕРЖДЕНА**; полный выпуск v0.5.1 **NO-GO / NOT RELEASED**.

## 1. Preflight provenance

| Материал | SHA-256 / статус |
|---|---|
| Входной Engine PH-LW-02 | `d2774a4f6af96809b0c875bd8d754865bab47bdc61f6536414ace1390e938e22`; CRC+925 manifest file hashes PASS |
| Входная Documentation PH-LW-02 | `5e65e5156a9514627711ff89054b764109056aaf51e375298e9770fce034cc50`; CRC+140 manifest file hashes PASS |
| Неизменная нормативная v0.5.0 | `ca487d3e978af116418a597b5d05cd890d11e2e93855c9f7a312e21f083dd16f` |
| Неизменная нормативная v0.5.1 | `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e` |
| Состояние lineage | PH-LW-02 WIP ← PH-LW-01 WIP ← PH-051-11 WIP; PH-051-12 релизный ZIP не поставлен, подтверждение v0.5.1 release отсутствует |

## 2. Что сделано (строго PH-LW-03)

- Новый `project_harness.local_web_service`: `LocalWebService`, typed `OperationRequest`, trusted project registration, локальный `LWP-*` catalog, allowlisted `update-draft/check-intake/prepare/next/validate-project/verify` с реальными public Python core APIs. Все остальные `LW-C01–26` отображаются только как disabled с причиной; `execute-current` **не активирован**.
- Новый bounded public `local_web_drafts.update_provisional_draft`: 45 allowlisted provisional fields, проверка strict `PROJECT_INPUT@4`+readiness, before SHA/revision fingerprint, atomic replace, сброс отдельно принятых draft approvals при изменении. Нет direct UI writes в `.harness`.
- Read-only status view: statuses/routes, done/current/blockers, точные Stage Plan/Gate/baseline/run refs, immutable fingerprint и доступные действия; повторный GET не меняет workspace или project bytes.
- Внешний per-user `app_data` journal `LWO-*`, SHA-256 record integrity, атомарные QUEUED/RUNNING/terminal receipts, ограниченные refs/status (без документации, prompts, ENV credentials), один локальный worker и дедупликация по idempotency key.
- Новый общий OS `project_operation_guard` вокруг затронутых mutations в core и CLI (POSIX flock / native Windows msvcrt branch, который НЕ запускался здесь). Cross-process conflict до core mutation, повторная проверка fingerprint под guard, lock order outer operation → inner Stage transaction.
- Explicit crash reconciliation: queued → INTERRUPTED; draft write, prepared valid handoff recover по exact artifacts; неоднозначный `next`/`verify` → BLOCKED с русским кодом и next action, без ложного attribution и без автоповтора. Cancellation только до mutation. Существующий Stage journal recovery вызывается только при явном reconciliation.
- Подготовлены `local_web/ci_ph_lw_03_windows.ps1` и реальный Windows-only test, но оба **NOT RUN** на Windows; они не являются Windows evidence.

## 3. Фактическая test matrix

| Проверка | Результат | Факт/лог |
|---|---|---|
| Последний targeted service, real core positive/negative | **PASS: 15 тестов, 1 Windows-only SKIP** | `PH_LW_03_LOGS/TARGETED_FINAL.log` |
| Combined PH-LW-01/02/03 contract+manual+service | **PASS: 38 тестов, 3 SKIP** (2 PH-LW-02 Windows, 1 PH-LW-03 Windows) | `PH_LW_03_LOGS/LOCAL_WEB_COMBINED_FINAL.log` |
| Regression, 33 unit modules включая Stage, Gate, Brownfield, maintenance, migration, executor | **Все модули подтверждены PASS после correction test setup**, но **это не один чистый полный прогон**: первоначально 379 tests / 5 skipped, 3 модуля имели `PermissionError` из-за исполняемого бита при распаковке; все 3 повторены после restore `0755`, exit 0 (24 tests) | `REGRESSION_MATRIX.json`, `REGRESSION_MODULES/*.log`, `RERUN/*.log` |
| Первоначальный monolithic `tests/run_tests.py` | **TIMEOUT / INCOMPLETE, НЕ PASS** (исполнение было прервано лимитом после частичного набора) | `PH_LW_03_LOGS/BASELINE_REGRESSION.log` |
| Wheel rebuild, fresh virtualenv wheel re-install, installed `--version`, `doctor`, service imports/resources | **PASS on Linux на финальном wheel** | `WHEEL_BUILD_FINAL.log`, `WHEEL_INSTALL_FINAL.log`, `WHEEL_CLI_FINAL.log` |
| Standalone documentation validator on final Docs ZIP | **PASS: 36/36 checks, 0 errors/warnings** | `DOCUMENTATION_FINAL_ZIP.json`, `DOCUMENTATION_FINAL_ZIP.log` |
| Native Windows 11 x64 / NTFS process mutex, reparse/ACL/sharing, script | **NOT RUN / WINDOWS_NOT_TESTED** | Windows host/volume unavailable; Linux test SKIP cannot satisfy Windows gate |
| Real rootless Podman security matrix and governed per-Run egress | **NOT RUN / NO-GO** | Pre-existing PH-051-12 blockers remain open; no test doubles claimed as real isolation |
| HTTP/UI browser/launcher/offline Windows installer | **NOT IMPLEMENTED / NOT RUN** | Explicitly outside PH-LW-03; PH-LW-04..12 |

### Исправление условий теста, не core regression

`zipfile.extractall` при подготовке Linux test tree не восстановил permission `0755` ранее исполняемого `bin/project-harness`. В исходном PH-LW-02 ZIP member имеет executable mode; после `chmod 0755` все три ранее упавших CLI модуля прошли повторно: `test_ph_f01_planner_regression` (6/6), `test_ph_f03_active_stage_planning` (8/8), `test_ph_f04_runtime_reachability` (10/10). Исходные FAIL logs сохранены, **не скрыты**. Это не означает, что 379 тестов выполнились в одном беспрерывном зелёном прогоне. Отдельный новый regression зафиксировал, что изменение Run ref после crash не доказывает принадлежности UI операции: теперь `next` остаётся `BLOCKED / AMBIGUOUS_COMMIT`, без false-positive reconciliation.

## 4. Неизменные инварианты / критерий приёмки

`PH_LW_03_PRESERVED_INVARIANTS.md` содержит список неизменных договоров. Native Windows acceptance BLOCKED, пока реальная Win11/NTFS матрица и launcher/install/HTTP (последующие пакеты) не подтверждены. Отсутствие Windows здесь **не считается PASS**. Полный v0.5.1 release NO-GO по отсутствующим Podman isolation/approved egress; функции PH-LW-03 не делают automatic execution и не закрывают release blockers.

Финальная пара ZIP содержит Engine+wheel+embedded docs и standalone docs, sha256 manifests. Внешние точные архивные SHA-256 приведены в сопровождающем `PH_LW_03_SHA256.txt` после упаковки. Исходный нормативный ZIP и historical PH-051/PH-LW-01/02 отчёты не модифицированы.
