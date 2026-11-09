# PH-051-06 — отчёт об implementation и проверке

**Дата:** 2026-10-26. **Поставка:** Project Harness v0.5.1 **WIP / NOT RELEASED**. **Только этап PH-051-06:** exact Agent Result, bounded logs, ENV secret refs и kernel-owned normalized execution-result records. **Automatic release / rootless isolation: NO-GO** до реальных тестов и PH-051-12.

## 1. Проверенные исходники и нормативная граница

- Engine PH-051-05: SHA-256 `e61c41c4e4d16f7596100f22b66c2f65b6a44a4b73917bcb020d7aef69ee5ccf`, ZIP CRC и полный исходный manifest **PASS** (534 entries).
- Documentation PH-051-05: SHA-256 `e35437b7185f7c6bc5f189fd05676a36bf61d356b9d27764fe2eed4673904d81`, ZIP CRC и исходный manifest **PASS** (121 entries).
- Нормативная `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`: SHA-256 `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e`, §§ 9, 11, 19, 23.1–23.2; implementation plan PH-051-06. Исходные schema/registry revisions не менялись.
- Разрешённые production areas: `executors/result.py`, binding минимально в `executors/codex_cli_local.py`, sandbox output/log/env binding в `sandbox/podman_rootless.py`, `safety.py`; адресные tests/README/changelog/docs, mirrors/wheel и manifests. Изменений `runtime.py`, `stages.py`, `maintenance.py`, `apply.py`, CLI, регистров и схем нет.

## 2. Реализованный PH-051-06 contract

1. **Единственный exact output** `/output/agent-result.json`: заранее зарезервированный host-owned файл `0600` c `O_EXCL`. Проверка всех компонентов пути на symlink, точного имени `output/agent-result.json`, регулярного файла, `nlink=1`, ownership/mode, inode через `lstat→O_NOFOLLOW→fstat`, отсутствия дополнительных неразрешённых файлов, размера ≤ 1 MiB, ограниченного UTF-8 и JSON без повторных ключей/nonfinite constants.
2. **Strict Agent Task Result.** Только поля существующего `SCHEMA-AGENT-TASK-RESULT@1`, обязательные свойства, типы, status enum и exact Run/Task текущего disposable Run; никакая строка JSON не исполняется как shell. Unbound test doubles остаются предварительными и не публикуют результат.
3. **Normalized immutable ART.** При подтверждённых trusted `ROOTLESS_PODMAN` metadata/UTC timestamps `CodexCliLocalAdapter.normalize_result` формирует `ART-EXECUTION-*`, сохраняет Agent JSON под `.harness/runtime/AGENT_RESULTS/<RUN>.json`, ограниченные stdout/stderr в `.harness/runtime/EXECUTION_LOGS/`, ART YAML в `.harness/runtime/EXECUTION_RESULTS/` последним и обновляет authenticated control-plane fence. Duplicate different bytes и частичный immutable replay отвергаются. Historical unrevisioned `RUN-…` не переписывается; только `execution_result.run_ref` приводится к `RUN-…@1` по уже существующей ART-schema.
4. **Secrets/logs.** Strict ADP allowlist и `ENV:NAME` host references без raw values в profile; отсутствующий required ref блокирует запуск. Доверенный Podman control process получает только перечисленные переменные через temporary host-only env-file с mode `0600`, без значений в argv/Run plan. При штатном завершении temporary file очищается/удаляется. Exact-value redaction и fail-closed `SECRET_LEAK_DETECTED` проверяют весь bounded stdout, stderr, raw и decoded Agent Result, до публикации. Логи ограничены ≤ 256 KiB каждый. `scan_changed_product_secrets` доступен только как read-only helper для будущего PH-051-08.
5. **Неоптимистическая семантика.** `COMPLETED` в сообщении агента и exit code 0 дают **только** `PENDING_INDEPENDENT_VERIFICATION`; нет Product apply, `Task DONE`, `VERIFICATION PASS`, формального Stage Gate acceptance или внешнего CLI `execute-current`. Fail cases возвращают `RESULT_MISSING`/`RESULT_INVALID`, `OUTPUT_LIMIT_EXCEEDED`, `SECRET_LEAK_DETECTED` или предшествующие sandbox/process blockers без optimistic success.

## 3. Фактически выполненные проверки

| Проверка | Реальная команда / источник лога | Результат |
|---|---|---|
| PH-051-02–06 unit/negative | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -q tests.test_ph_051_06_result_channel tests.test_ph_051_02_executor_protocol tests.test_ph_051_03_rootless_podman tests.test_ph_051_04_disposable_roots tests.test_ph_051_05_codex_adapter`; `PH_051_06_LOGS/TARGETED_FINAL.log` | **93 tests: 91 PASS, 2 SKIP, 0 FAIL**, 30.620 s |
| Полная regression + PH-F08 Stage/Gate/Brownfield/maintenance | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python tests/run_tests.py`; `PH_051_06_LOGS/REGRESSION_FULL.log` и `.exit` | **271 tests: 269 PASS, 2 SKIP, 0 FAIL**, 923.910 s, exit=0 |
| Повтор старых границ | SHA-256 по исходному PH-051-05 ZIP и текущим исходникам/документам, `PH_051_06_LOGS/PRESERVATION.json` | **230 previous reports, registry/schema, stage/maintenance/CLI и прочих out-of-scope files unchanged byte-for-byte**, PASS |
| Build wheel | `python -m pip wheel --no-deps --no-build-isolation --no-cache-dir -w dist .`; `PH_051_06_LOGS/WHEEL_BUILD.log` | PASS, src/build/lib/wheel code byte-identical |
| Installed wheel + CLI doctor | Fresh `python -m venv <outside-root>`; `pip install --no-index --no-deps <new-wheel>`; `project-harness --version`, `doctor` | **PASS**, version `0.5.1`, schema 7, 17 schemas, imports resolve to installed site-packages |
| Installed manual end-to-end smoke | `project-harness demo --output-dir <outside-root> --keep-directory`, `validate-handoff --project <demo-zip>`, `validate-project --project <demo-root>`, `next --project <demo-root>`, `stage-status --project <demo-root>` | **PASS**; `PH_051_06_LOGS/WHEEL_{DEMO,VALIDATE_HANDOFF,VALIDATE_PROJECT,NEXT,STAGE_STATUS}.log` |
| Documentation manifest and ZIP | `python tools/validate_documentation.py <docs-root> --zip <PH-051-06-doc-zip> --json <log>` | **36 PASS, errors=0, warnings=0**, 123 files, ZIP CRC and exact manifest PASS |
| Real non-root Rootless Podman security and fake CLI inside pinned image | Host UID=0; Podman binary absent; PH_TEST_PODMAN_IMAGE not configured; `PH_051_06_LOGS/ROOTLESS_ENVIRONMENT.log` | **NOT RUN / NO-GO**, mock negative tests are not proof of OS isolation |

**Regression comparison:** PH-051-05 full regression 258 tests → PH-051-06 full regression 271 tests (+13 new tests), still 2 environment-dependent skips. The full run was performed against the final PH-051-06 production code before packaging; reports/logs/manifest metadata were generated afterward, without modifying production code.

## 4. Addressed negative cases

- Missing/empty/oversized/wrong-run/wrong-task/malformed JSON, duplicate JSON keys, non-UTF-8, nonfinite numbers and unknown properties → no normalized PASS.
- Symlink parent/file, hardlink, FIFO, wrong UID/mode, undeclared `/output` files → rejected before reading as evidence.
- Secret echoes in stdout/stderr and Agent Result, including JSON Unicode escaping → no stored Agent/ART result; redaction never converts a leak into success.
- Unapproved ambient environment, missing `ENV:NAME`, raw-value reference injection and CR/LF env-file injection → blocked; no whole host environment transfer.
- Deliberately shell-looking `summary` remains inert text; tampering with persisted ART and replay mismatches rejected; canonical product digest unchanged after valid kernel publication.
- No-Podman case never falls back to host Codex CLI.

## 5. Preserved and deferred

- The previous PH-F08 v0.5.0 accepted route, Stage State canonical target, sequential `PROTOTYPE→ALPHA→BETA→MVP→RELEASE`, formal Gate evidence, Brownfield read-only assessment, maintenance, exact refs, crash-consistent Stage transactions and `next→verify→complete` are unchanged.
- Original PH-051-01–05 reports/logs and normative specification bytes untouched. Registry collision decision `REG-CONTRACT-CATALOG 5→6` from PH-051-01 preserved; `PROJECT_INPUT@4` and schema 7 unchanged.
- PH-051-07 independent SANDBOXED verification, PH-051-08 diff/write-scope/secret scan at apply + journal, PH-051-09 public `execute-current` and `executor-doctor`, PH-051-10 orphan recovery and PH-051-12 real release gate are **NOT IMPLEMENTED** here. No provider/HTTP API/Git/deployment/remote execution or host fallback.
- Until real non-root Podman security tests and remaining steps, this artifact is **v0.5.1 WIP / NOT RELEASED; automatic execution security = NO-GO**.

## 6. Distribution evidence

- `PH_051_06_CHANGED_FILES.md` lists exact file-level SHA-256 changes against both PH-051-05 ZIP inputs; previous stages’ accepted artifacts not rewritten.
- `PH_051_06_LOGS/` contains real negative/regression, wheel/build/install/smoke, final docs validator, environment blocker and preservation outputs.
- Documentation: `Project_Harness_Documentation_v0.5.1_PH_051_06.zip` SHA-256 `afd3e96999c1d728aa040a94c58ad02908ef2bc348de44223aff7748d00a1c83`; source and embedded documentation are byte-identical.
- Engine: `Project_Harness_Engine_v0.5.1_PH_051_06.zip`. Its own ZIP SHA-256 cannot be embedded inside it without self-reference; exact external digest is reported in delivery message / external SHA file.
