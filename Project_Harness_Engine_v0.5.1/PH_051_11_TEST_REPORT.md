# PH-051-11 — итоговый отчёт о выполнении, проверках и границе приёмки

**Дата:** 2026-10-29. **Версия:** `Project Harness v0.5.1 WIP / NOT RELEASED`. **Scope:** только PH-051-11 (операторская документация, ADP/SBX/policy примеры, фактическая Podman security matrix, CLI distribution smoke и непосредственно вызванный defect root manifest verification). **Не является PH-051-12 final release acceptance.**

## 1. Проверенные входные архивы и контракты

| Источник | SHA-256 / основание |
|---|---|
| `Project_Harness_Engine_v0.5.1_PH_051_10.zip` | `9e186f4e4116ce5de91b4254d5557fd132e90bfecdf6efb94beef2be020f9568` |
| `Project_Harness_Documentation_v0.5.1_PH_051_10.zip` | `28103b6043d82ad61becfcc9886d0616274feb50d6b5ae864c106866a7f920a4` |
| Нормативная `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md` | `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e` (SHA-256 самого документа) |
| План `Project_Harness_v0.5.1_Implementation_Plan_RU.md` | PH-051-11 §§3, 5; приоритет спецификации §§16, 20–24 |

Все три ZIP (`Engine`, `Documentation`, спецификации) прошли ZIP CRC (`testzip() is None`); исходные engine/docs/spec SHA-256 manifests полностью проверены до изменения файлов. В качестве работы приняты именно последние PH-051-10 архивы, не старые PH05109/непроверенные staging trees.

## 2. Реализовано в рамках PH-051-11

1. Обновлены Engine `README`, `MANUAL_INSTALL`, `CHANGELOG`, distributable GPT preparation template и mirrors. Убраны устаревшие обещания, что публичные automatic CLI пока отсутствуют, без ложной декларации готового automatic opt-in.
2. Добавлен воспроизводимый операторский `05_Updates/14_Operator_Runbook_v0.5.1_WIP.md`: external GPT-first questionnaire → `PROJECT_INPUT@4` и отдельные formal approvals → `prepare`/handoff → manual/default или prerequisites explicit automatic → `executor-doctor` → `next`/`execute-current` → независимая verification/atomic apply → continuation/Stage Gate/level-up/maintenance/migration. Везде сохранено различие Task completion и formal Stage acceptance.
3. Добавлена `05_Updates/15_Podman_Security_Validation_v0.5.1_WIP.md` с точными real rootless Podman prerequisites и S01–S15. Для недоступных OS security self-tests установлен честный `NOT TESTED / NO-GO`, а не unit/mock PASS.
4. Добавлены и в Engine/Documentation синхронизированы строгие примеры ADP/SBX, manual policy, явный **отвергаемый** egress-approval, инструкция по safe environment references. Примеры содержат только демонстрационный image digest, не подтверждённый OCI image, и не содержат секретных значений.
5. Исправлена **прямая найденная регрессия distribution doctor**: прежний `validation._manifest_check()` исключал все файлы с basename `MANIFEST.sha256`, в том числе вложенный docs manifest, хотя root manifest требует его digest. Теперь исключается только root manifest. Тест отдельно подтверждает PASS для правильного вложенного файла и FAIL на его подмену. Изменение точечно зеркалировано в build/lib; другие production modules не тронуты.
6. Rebuilt/smoke-tested packaged wheel, source и bundled entrypoint, embedded/standalone docs synchronized; агрегаты и два SHA256 manifest перегенерированы. Полный пофайловый scope см. `PH_051_11_CHANGED_FILES.md`.

## 3. Проверки и фактические результаты

| Check | Команда/артефакт | Итог |
|---|---|---|
| Focused PH-051-11 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_11_operator_docs` | **PASS: 5/5**; `PH_051_11_LOGS/TARGETED_OPERATOR_DOCS.log` |
| Previous security/regression focused | `python -m unittest -v tests.test_ph_051_03_rootless_podman tests.test_ph_051_06_result_channel tests.test_ph_051_07_sandbox_verification tests.test_ph_051_08_atomic_apply tests.test_ph_051_09_automatic_runtime tests.test_ph_051_10_migration_recovery tests.test_ph_051_11_operator_docs` (`PYTHONPATH=src:.`, `PYTHONDONTWRITEBYTECODE=1`) | **PASS: 103/104, 1 SKIP** only real rootless Podman; log `PH_051_11_LOGS/FOCUSED_NEGATIVE_AND_SECURITY.log` |
| Public installed wheel + bundled/source CLI | `python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist`, clean venv `pip install --no-index --no-deps dist/project_harness_engine-0.5.1-py3-none-any.whl`; 21 public checks | **PASS: 21/21**, `PH_051_11_LOGS/PUBLIC_OPERATOR_SMOKE.json`, per-command logs |
| Source distribution doctor after direct regression fix | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python project-harness.py doctor` | **PASS**; source manifest digest verifies nested documentation manifest |
| Docs validator on **final** standalone docs ZIP | `PYTHONDONTWRITEBYTECODE=1 python tools/validate_documentation.py . --zip <docs PH05111 ZIP> --json <report>` | **PASS: 36 checks, 0 errors, 0 warnings**, ZIP/CRC/content manifest exact |
| Full Engine tests (including v0.5.0 and PH-051-01..11) | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python tests/run_tests.py` | **FINAL PASS: 342 tests, 340 PASS / 2 SKIP, 0 FAIL/ERROR** across 30 separately isolated test modules on corrected Engine (file mode `0755` restored); `PH_051_11_LOGS/SHARDED_REGRESSION_MATRIX.json` and `SHARDED_test_*.log`. Earlier single-process run on intermediate extraction: 342 tests, 8 `PermissionError` (bin executable bit inadvertently 0644), 2 SKIP; all other cases PASS. After restoring original input ZIP file permission 0755, all three affected modules separately PASS (24/24), and the complete 30-module sharded matrix completed without FAIL/ERROR. Both initial failure log and corrected retest logs are preserved transparently. |
| Real Podman rootless sandbox/egress/kill/cgroup security matrix | Requires non-root user, installed Podman, actual immutable local pinned image, real Podman self-tests | **NOT TESTED / NO-GO**: this host UID=0, `podman` binary not installed, real image unavailable |

**Опубликованные CLI smoke операции:** `--version`, `doctor`, public `executor-doctor --help` и `execute-current --help`, `start-intake` и `check-intake` (`WAITING_INPUT` с documented exit 3), `demo`, `validate-handoff`, `validate-project`, `status`, `stage-status`, `next`, actual `executor-doctor` и `execute-current` fail-closed for manual project, negative `EXPLICIT_APPROVED_EGRESS`/`--keep-execution-root`, bundled entrypoint `--version`/`status`/`executor-doctor` и source helps. Отличие `exit 0` от expected guarded `exit 3` учтено; успешная блокировка не переименована в successful automatic execution.

**Дистрибутивы:** standalone docs ZIP SHA-256 `17ab78d0412c713fabf957bd54e7cc65d0b8dc77d358fe0d7f9f2635bca172fd`; Final Engine ZIP SHA-256 is published *externally* in `PH_051_11_SHA256.txt` to avoid a circular self-hash; embedded/standalone docs 133 files byte-identical, final 0 CRC errors. Engine internal `MANIFEST.sha256` will contain exact SHA-256 for every release file except itself.. Embedded docs сравнивались по bytes со standalone, wheel rebuilt, `MANIFEST.sha256` entries перевычислены после всех тестовых логов/отчётов. SHA/CRC второй поставки подтверждены при упаковке.

## 4. Unresolved pre-existing blockers — без расширения scope

1. **Публичный opt-in automatic mode:** `compiler.prepare_handoff()` до сих пор отклоняет новый `PROJECT_INPUT@4 execution.mode=LOCAL_AUTOMATIC` с `AUTOMATIC_EXECUTOR_NOT_IMPLEMENTED`. Автоматический интеграционный тест использует test-only подготовку `PROJECT_LOCK`, а не исполнимый публичный approval route. Оператор **не может законно включить** end-to-end автоматический режим только опубликованными CLI; private Python/control-plane editing запрещены. В PH-051-11 не добавлялся отсутствующий activation lifecycle и не исправлялся `compiler.py`.
2. **Egress/runtime mode:** CLI `--network EXPLICIT_APPROVED_EGRESS`/`--approval` существуют как flags, но текущий backend поддерживает только `NONE` и возвращает `BLOCKED / NETWORK_NOT_APPROVED`; действующий exact per-Run egress approval format не поставлен. `--keep-execution-root` также denied без enabled debug policy. Данный этап документирует факты, а не имитирует реализацию.
3. **Real rootless security:** OS environment здесь не подходит для проверки isolation. Security S01–S14 не имеют реального PASS, S15 public negative fail-closed PASS. Наличие fake/mock unit-тестов и 21 public smoke не закрывает нормативное требование §24 о реальной security матрице. Подробная таблица и воспроизводимые команды — `PH_051_11_SECURITY_MATRIX.md`.

## 5. Решение PH-051-11

**Документационная/contract/negative functional часть: выполнена** с указанными тестами; input archives и previous invariants сохранены, за исключением описанного точечного исправления проверки манифеста. **Автоматический mode и финальная security acceptance: NO-GO / NOT TESTED.** Версия остаётся **v0.5.1 WIP / NOT RELEASED**. Не объявлен PH-051-12 GO; для полноценного релиза отдельно нужны public opt-in issue resolution, real rootless Podman self-tests, полный E-01–E-18 и нормативная §24 gate.

**Выдача:** `Project_Harness_Engine_v0.5.1_PH_051_11.zip` и `Project_Harness_Documentation_v0.5.1_PH_051_11.zip`, `PH_051_11_CHANGED_FILES.md`, `PH_051_11_PRESERVED_INVARIANTS.md`, `PH_051_11_SECURITY_MATRIX.md`, `PH_051_11_LOGS/`, внутренние SHA-256 manifests.

**Уточнение по shell entrypoint:** initial extracted `bin/project-harness` had mode `0644` because of the extraction tool (original PH-051-10 ZIP records `0755`). This was not a runtime Stage regression. Before final packaging mode was restored to `0755`; ZIP external attributes were checked.
