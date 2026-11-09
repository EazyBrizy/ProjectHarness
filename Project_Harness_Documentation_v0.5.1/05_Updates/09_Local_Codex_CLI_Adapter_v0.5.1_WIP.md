# PH-051-05 — Local Codex CLI Adapter, exact ADP binding (v0.5.1 WIP)

**Документ:** Project Harness — Local Codex CLI Adapter PH-051-05.  
**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25 (дата серии v0.5.1 WIP).  
**День реализации:** 2026-10-26.  
**Статус:** точечный implementation slice, **NOT RELEASED / BLOCKED для automatic execution**.  
**Нормативная база:** `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`, §§4–5, 10–11, 15, 23.1–23.3.  
**Зависимости:** PH-051-01–04, особенно [Executor Protocol](06_Executor_Protocol_v0.5.1_WIP.md), [Podman Sandbox](07_Rootless_Podman_Sandbox_v0.5.1_WIP.md), [Disposable Root](08_Disposable_Execution_Root_v0.5.1_WIP.md).

## Реализованная граница

`CodexCliLocalAdapter.from_project(project_root)` разрешает ровно один `CODEX_CLI_LOCAL`: читает **активные, exact revisioned** `.harness/config/ADAPTERS/ADP-*@<revision>.yaml` и `.harness/config/SANDBOXES/SBX-*@<revision>.yaml` согласно `PROJECT_LOCK.execution`. Требуются explicit `LOCAL_AUTOMATIC`, `NONE` network, строгие schema/identity/status, совпадающая `ADP.sandbox_profile_ref`, **полное совпадение** refs/digests с `PROJECT_LOCK.execution_profile_bindings`, отсутствие symlink/hardlink в project records. Нет glob/latest, mutable container image, host executable из user input или обхода manual default.

Внутренний Python API `prepare_current_run(runtime_root, run_ref=...)` использует существующий PH-051-04 builder и связывает текущие Run/Task/JIT с `prompt-bundle.md`, `context-packet.json` из `/workspace/control:ro`, единственным destination `/output/agent-result.json` и `/workspace/product:rw`. В результате возвращаются **только подготовленные** `invocation` (список argv) и `sandbox_request`, содержащий отдельный per-Run disposable mount root; это **не** формальное одобрение запуска. `execute(invocation, sandbox_request)` заново проверяет bound profiles/Run/product baseline/projection и не принимает произвольный argv, другой runner/mount/timeout, raw `env`, shell или подмену проекта. Повторный dispatch того же Run через один экземпляр adapter блокируется; persisted retry governance — PH-051-09/10.

`doctor(active_adp)` для bound `RootlessPodmanRunner` проверяет реальный `ROOTLESS_PODMAN` с pinned image и exact `profile.executable` **внутри контейнера**. `status=PASS` разрешён только при полном OS isolation self-test; нет Podman либо critical `UNKNOWN` → `BLOCKED`, **без host Codex**. `execute` передаёт argv runner через container `--entrypoint <binary>` без `shell=True`, `stdin` закрыт. Effective timeout равен минимуму ADP и SBX timeouts; PH-051-03 runner ограничивает stdout+stderr, Podman children, exit/timeout/termination и memory/CPU/PIDs. Полученный process result — **не** `COMPLETED` Task: `normalize_result` лишь выдаёт `PENDING_RESULT_VALIDATION` для предварительного синтаксического JSON при exit 0; `EXECUTOR_EXIT_NONZERO`, `EXECUTOR_TIMEOUT`, `OUTPUT_LIMIT_EXCEEDED`, `SANDBOX_UNAVAILABLE`, `RESULT_MISSING/INVALID` классифицируются отдельно.

**Окружение/секреты:** Podman uses `--unsetenv-all`, fixed non-host `LANG=C`, `LC_ALL=C`, `HOME` в tmpfs. До PH-051-06 этот adapter **не пересылает** host variables; ADP `environment_allowlist` вне `LANG,LC_ALL` либо непустые `secret_environment_refs` дают `BLOCKED/SANDBOX_POLICY_FAILURE`, а не молчаливую потерю нужного credentials. В `PROJECT_LOCK`, result, logs и manifests нет secret values. `EXPLICIT_APPROVED_EGRESS` заблокирован до governed per-Run approval PH-051-09.

## Profile argv, без фиксации CLI syntax в Kernel

Валидируемый `argv_template` — массив до 64 аргументов, `argv_template[0]` точно равен `executable`. Допустимы только отдельные аргументы-плейсхолдеры `{prompt_bundle_path}`, `{context_packet_path}`, `{agent_result_path}`, `{workspace_path}`, `{run_id}`, `{task_id}`; arbitrary user text и shell interpolation отвергаются. Пример из нормативной спецификации `codex exec --prompt-file ...` — **иллюстрация profile**, а не доказательство, что такие flags поддерживает установленный реальный Codex CLI. Для конкретного pinned image оператор/PH-051-11 должен проверить `codex --help` **в контейнере** и зафиксировать поддерживаемый `argv_template` без редактирования Kernel. В этом стенде Codex CLI/image и rootless Podman отсутствуют, поэтому фактическая совместимость flags **NOT TESTED**.

Один и тот же protocol test double `tests/fixtures/fake_codex_cli.py` имеет свой строго известный `argparse` интерфейс (`--scenario`, `--workspace-path`, `--control-path`, `--result-file`, `--run-id`, `--task-id`). Для real integration test применяется `python3 -m fake_codex_cli` **только внутри pinned Podman image** с файлом модуля в disposable product; для этого доступны все required args/paths и отдельный `agent-result.json`. Это не второй production adapter, не проверка настоящего Codex CLI flags и не host subprocess.

## Диагностика и acceptance boundary

Проверка target unit/negative контрактов из извлечённого Engine (без запуска fake CLI на host):

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v \
  tests.test_ph_051_05_codex_adapter tests.test_ph_051_02_executor_protocol \
  tests.test_ph_051_03_rootless_podman tests.test_ph_051_04_disposable_roots
```

Optional **реальная** container integration (только подходящий non-root Linux Podman+cgroups, локально загруженный immutable digest image с `python3`, `/bin/sh` и OS self-test dependencies):

```bash
export PH_TEST_PODMAN_IMAGE='registry.example/codex-runtime@sha256:<real-64-hex-digest>'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_05_codex_adapter
```

`<real-64-hex-digest>` заменяют реальным immutable image reference; без image/Podman интеграционный test честно `skipped / NOT RUN`. Моки runner/recording tests не подтверждают OS isolation. В PH-051-05 **не добавлены** публичные `executor-doctor`/`execute-current`, механизм secrets/logs/result acceptance, независимая sandbox verification, diff/apply, automatic `complete`, migration/recovery, Git или deployment. До PH-051-09/12 manual `next → verify → complete` остаётся единственным публичным execution route; PH-051-05 не активирует автоматическое исполнение проектного продукта даже при unit PASS.
