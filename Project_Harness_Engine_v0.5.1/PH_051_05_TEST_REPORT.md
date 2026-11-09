# PH-051-05 — отчёт об implementation / tests

**Дата:** 2026-10-26. **Версия:** Project Harness v0.5.1 **WIP / NOT RELEASED**. **Пакет PH-051-05:** код адаптера и его unit-интеграция реализованы, но **real rootless Podman integration = NOT RUN**. Статус automatic release gate: **NO-GO**; нет оснований считать завершённым PH-051-09/12.

## 1. Вход и нормативный контракт

- Latest Engine PH-051-04, SHA-256 `ce16bc45dac0dd29d9d848fcc1f8ef6eb248f1c588c47f346a77d12369e98355`, CRC PASS.
- Latest Documentation PH-051-04, SHA-256 `dcacfe81c2048e8e271540e5e55e3211be7bfe60ab760e6dd5d42a3a3df5fb05`, CRC PASS.
- Normative `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`, SHA-256 `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e`, совпадает с указанной в плане спецификацией; применены §§ 4–5, 10–11, 15, 23.1–23.3.
- План PH-051-05, области изменения: `executors/codex_cli_local.py`, profile resolution, invocation/exit classification, focused tests, package/docs mirrors. Существующий ExecutorAdapter protocol/Kernel orchestration/schema/registry и Stage lifecycle не изменены.

## 2. Выполненное изменение строго в scope

1. **Один активный `CODEX_CLI_LOCAL`.** `load_active_codex_profiles(project_root)` / `CodexCliLocalAdapter.from_project()` проверяют exact locked `LOCAL_AUTOMATIC`, `NONE`, `ADP-…@revision` и `SBX-…@revision`, `ACTIVE`, kind/backend, совпадение profile refs и SHA-256 источников с `PROJECT_LOCK.execution_profile_bindings`. Нет `glob`/latest, подмены revision, symlink/hardlink resolver, скрытой активации для `MANUAL_HANDOFF`.
2. **Trusted invocation.** `prepare_current_run(runtime_root)` переиспользует PH-051-04 disposable root и active Run/Task/JIT, строго привязывает prompt `/workspace/control/prompt-bundle.md`, context packet `/workspace/control/context-packet.json`, workspace `/workspace/product`, result path `/output/agent-result.json`. `argv_template` — массив с поэлементной заменой только уже разрешённых placeholders; никакого command string, shell/redirection, host path, arbitrary user interpolation. Код Kernel не задаёт предположительные Codex flags.
3. **Rootless-only dispatch.** `execute()` сравнивает exact prepared request/argv, перепроверяет lock/profile hashes, baseline, control projection и Run, не позволяет расширять timeout/mounts/env, повторно вызывает реальный `RootlessPodmanRunner.doctor()` и передаёт argv только в `ROOTLESS_PODMAN` (`shell=False`), а не как host CLI. Fake/неполная attestation и отсутствие Podman блокируют запуск. Effective timeout `min(ADP,Sandbox)`; stdin закрыт; SIGTERM/grace/kill, output cap/cgroups реализованы ранее PH-051-03 и не менялись.
4. **Environment fail-closed.** В PH-051-05 нет secret resolution и log redaction PH-051-06; `--unsetenv-all`, только фиксированные `LANG/LC_ALL/HOME` внутри контейнера. Неподдержанный allowlist или secret refs блокируются до запуска, egress всегда `NONE`. Нет обхода automatic policy.
5. **Правдивая классификация.** Nonzero, timeout, output limit, missing/invalid agent result дают отдельные fail statuses. Даже exit 0/синтаксический agent JSON ещё **не** independent verification, apply, Stage Gate PASS или Task COMPLETE.
6. Обновлён существующий fixture fake CLI только для работы с точным вложенным path `prompt-bundle.md`; реальный fake process допускается **только в контейнерном integration test**. Новые unit/negative тесты не запускают fake CLI на host. Добавлена scoped документация; синхронизированы `build/lib`, установленный wheel, embedded и standalone docs.

## 3. Фактические тесты и команды

| Проверка | Фактически выполнено | Результат |
|---|---|---|
| Unit + negative PH-051-02–05 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_02_executor_protocol tests.test_ph_051_03_rootless_podman tests.test_ph_051_04_disposable_roots tests.test_ph_051_05_codex_adapter` | **80 tests; 78 PASS + 2 SKIP; 0 FAIL**, 16.031 s |
| Full existing + PH-051-05 regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python tests/run_tests.py` | **258 tests; 256 PASS + 2 SKIP; 0 FAIL**, 625.718 s; exit=0 |
| Engine wheel rebuild | `python -m pip wheel --no-deps --no-build-isolation --no-cache-dir -w dist .` | PASS, wheel source matches exact new `codex_cli_local.py` |
| Fresh wheel isolated install | `python -m venv <outside-tree-venv>`; `pip install --no-index --no-deps <wheel>`; import installed module | PASS; version 0.5.1; adapter source in installed site-packages |
| Installed CLI | `project-harness doctor`; `demo --output-dir <outside-root> --keep-directory`; `validate-handoff`, `validate-project`, `next` | **PASS**, `READY_FOR_CODEX`, unchanged manual route |
| Documentation validator | `python tools/validate_documentation.py <docs-root> --zip <PH-051-05-doc-zip> --json <log>` | **36 PASS; 0 errors; 0 warnings** |
| SHA/ZIP/mirrors | ZIP CRC, exact per-file manifest, `src↔build/lib↔wheel` code hash, standalone ↔ embedded docs, executable mode, immutable previous reports | PASS upon packaging |
| Real rootless Podman with fake Codex CLI inside pinned container | Environment has UID=0, `podman` absent, pinned image not provided; opt-in test skipped | **NOT RUN / BLOCKED**, **not** an isolation PASS |
| Actual Codex CLI syntax inside pinned image | No Codex binary/image/real container | **NOT TESTED**; configured argv flags require separate pinned-image verification |

В начале полного прогона `bin/project-harness` был распакован с неверным file mode `0644`, хотя исходный ZIP PH-051-04 содержит mode `0755`. Это артефакт extract tool: восемь старых subprocess CLI tests получили `PermissionError`. Выполнена byte-neutral коррекция mode на `0755` (точно как original ZIP); первый прогон остановлен и сохранён как `PH_051_05_LOGS/REGRESSION_INTERRUPTED_CHMOD.log`. Повторный полный прогон после восстановления mode завершился exit=0, без test errors/failures. Это не изменение функционала.

## 4. Test matrix PH-051-05

**Positive:** строгая проверка ACTIVE ADP/SBX и exact SHA refs, trusted argv из Task/Prompt Bundle/Context Packet текущего Run, ограниченный ADP/SBX timeout, повторная подготовка без host process, существующая PH-051-04 execution-root idempotence; корректная классификация process outcomes.

**Negative:** manual mode запрещает активацию, stale/ref/digest/revision mismatch, wrong ADP kind/status/SBX assignment, symlink/hardlink profile, network egress без approval, raw secrets/environment allowlist, unprepared/edited argv, altered timeout/mount/request, stale canonical baseline, incomplete Podman attestation или отсутствие Podman, stdout flood/nonzero/timeout не становятся оптимистическим PASS. Эти unit-mocks не равны реальному OS self-test.

## 5. Сохранённые инварианты и deferred

- Отчёты/артефакты v0.5.0 PH-F08 и PH-051-01–04 сохранены byte-for-byte. Уровни `PROTOTYPE → ALPHA → BETA → MVP → RELEASE`, единственный canonical target Stage State, accepted scope, independent semantic Stage Gate evidence, formal approvals, Brownfield assessment, maintenance, crash-consistent stage transactions, `next → verify → complete` без изменений.
- Не реализованы вне scope: public `executor-doctor`/`execute-current` (PH-051-09), PH-051-06 strict result channel/secrets/logs, PH-051-07 independent sandbox verifier, PH-051-08 diff/atomic apply, PH-051-10 cleanup/migration/orphans, Git/PR/deployment, новые adapters/providers, host fallback.
- Нельзя объявлять automatic execution готовым к использованию, пока не пройдены настоящие non-root Podman/image/network/cgroup/self-tests и release gate PH-051-12. Статус **WIP / NOT RELEASED; security NO-GO**.

## 6. Логи и артефакты

- `PH_051_05_LOGS/REGRESSION_FULL.log`, `TARGETED_FINAL.log`, `DOC_VALIDATION_FINAL.log/json`, `WHEEL_BUILD.log`, `WHEEL_INSTALL.log`, `WHEEL_DOCTOR.log`, `WHEEL_DEMO.log`, `WHEEL_VALIDATE_HANDOFF.log`, `WHEEL_VALIDATE_PROJECT.log`, `WHEEL_NEXT.log`, `ROOTLESS_ENVIRONMENT.log` — фактические outputs.
- `PH_051_05_CHANGED_FILES.md` — exact SHA file diff против двух входных PH-051-04 ZIP.
- Документация `Project_Harness_Documentation_v0.5.1_PH_051_05.zip` SHA-256 `e35437b7185f7c6bc5f189fd05676a36bf61d356b9d27764fe2eed4673904d81`.
- Engine `Project_Harness_Engine_v0.5.1_PH_051_05.zip` содержит source/build/wheel/docs/tests/reports и сохранённые предыдущие материалы; SHA-256 внешнего ZIP сообщается в итоговой выдаче (самореферентный хеш не может содержаться в архиве).
