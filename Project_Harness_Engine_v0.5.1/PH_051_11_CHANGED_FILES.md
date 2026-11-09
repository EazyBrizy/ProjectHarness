# PH-051-11 — перечень изменений (точная граница)

**Версия:** `0.5.1-WIP / NOT RELEASED`. **Вход:** подтверждённые Engine/Documentation PH-051-10 ZIP; normative `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`, PH-051-11. Ни один production executor/apply/stage/migration contract не расширялся.

## Engine (изменения исходных, runtime и distributable файлов)

| Файл / группа | Причина |
|---|---|
| `README.md`, `MANUAL_INSTALL.md`, `CHANGELOG.md` | Фактический v0.5.1-WIP entrypoint и wheel, запуск/установка, ручной default, публичные automatic CLI и запрет ложного OS PASS. Старые исторические описания не переписывались. |
| `templates/GPT_PREPARATION_INSTRUCTIONS.md` и точные mirrors `src/project_harness/resources/templates/`, `build/lib/project_harness/resources/templates/` | Устранено вводящее в заблуждение утверждение, что `executor-doctor`/`execute-current` ещё отсутствуют; согласованы `PROJECT_INPUT@4`, manual/default и ограничение public opt-in. |
| `src/project_harness/validation.py` и `build/lib/project_harness/validation.py` | **Единственная исправленная production-регрессия**: проверка source root `MANIFEST.sha256` ранее исключала вложенный `docs/.../MANIFEST.sha256` по совпадению basename; теперь исключается только фактический root manifest path; nested manifest проверяется по digest. |
| `examples/{README_v0.5.1_WIP.md,adapter_codex_cli_local.v0.5.1.example.yaml,sandbox_rootless_podman.v0.5.1.example.yaml,execution_policy_manual.v0.5.1.example.yaml,egress_request_REJECTED.v0.5.1.example.yaml}` | Контрактно проверенные безопасные примеры; pinned image в SBX является недействительным демонстрационным placeholder, egress-запрос — намеренно reject-only. |
| `tests/test_ph_051_11_operator_docs.py` | 5 focused tests: строгие schema + фактические profile validators, policy/manual samples и mirrors, CLI flags, tampered nested manifest, отсутствие ложной Podman аттестации. |
| `dist/project_harness_engine-0.5.1-py3-none-any.whl`, `src/project_harness_engine.egg-info/{PKG-INFO,SOURCES.txt}` | Wheel пересобран из актуальных файлов и установлен в отдельный venv; нет новых requirements. |
| `docs/Project_Harness_Documentation_v0.5.1/**` | Embedded, byte-identical standalone Documentation v0.5.1 PH-051-11, с генерацией `FILE_INDEX.md`, исторически названного aggregate и embedded SHA-256 manifest. |
| `PH_051_11_LOGS/`, `PH_051_11_TEST_REPORT.md`, `PH_051_11_SECURITY_MATRIX.md`, `PH_051_11_PRESERVED_INVARIANTS.md`, этот файл | Реальные команды, stdout/stderr и return codes, отдельная security матрица с explicit NOT TESTED, scope и traceability. |
| `MANIFEST.sha256` | Полный ре-хэш final Engine source tree, включая nested docs manifest, собранный wheel и новые отчёты. |

## Standalone Documentation

**Изменены:** `README.md`, `VERSION.md`, `CHANGELOG.md`, `01_Architecture/03_Agent_Model_Tool_Adapters_and_Context_Recovery.md`, `04_Execution/02_Execution_Lifecycle.md`.

**Добавлены:** `05_Updates/14_Operator_Runbook_v0.5.1_WIP.md`, `05_Updates/15_Podman_Security_Validation_v0.5.1_WIP.md`; `10_Contracts/examples/{README_v0.5.1_WIP.md,adapter_codex_cli_local.v0.5.1.example.yaml,sandbox_rootless_podman.v0.5.1.example.yaml,execution_policy_manual.v0.5.1.example.yaml,egress_request_REJECTED.v0.5.1.example.yaml}`.

**Перегенерированы автоматически:** `FILE_INDEX.md`, `Project_Harness_Architecture_v0.5.0_FULL.md` (имя сохранено согласно существующему generator — прежний historical aggregate), `MANIFEST.sha256`. Ни одна нормативная спецификация и исторический Stage/PH-Fxx/PH-051-01..10 отчёт не изменены.

## Проверка scope / отказ от расширения

Не изменены: `stages.py`, `stage_transactions.py`, `maintenance.py`, `evidence.py`, `apply.py`, `runtime.py`, `cli.py`, `compiler.py`, `project_input.py`, `sandbox/**`, `executors/**`, schemas/registries, migration implementation и существующие тесты. Единственная правка production logic — **необходимый для published distribution smoke manifest-check bugfix** `validation.py`. Новых commands, permissions, network modes, de facto approved egress, host fallback, Git/PR/deployment и auto activation не добавляли.

Предыдущие immutable records/приёмочные матрицы оставлены как исторические. Обнаруженный **внеобластной блокер** `prepare` для `LOCAL_AUTOMATIC` и недостающий публичный opt-in записан в `PH_051_11_TEST_REPORT.md`, а не обойдён путём мутации `PROJECT_LOCK`.
