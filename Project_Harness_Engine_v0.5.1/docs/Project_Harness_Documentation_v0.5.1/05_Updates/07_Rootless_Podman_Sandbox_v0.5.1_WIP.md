# PH-051-03 — Rootless Podman runner и fail-closed doctor (v0.5.1 WIP)

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Статус:** реализация ограниченного пакета PH-051-03. **Не является приёмкой безопасности** rootless Podman или релизом v0.5.1; real Podman security integration в среде сборки не запускалась. Нормативная база: `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`, §§6–8, 10, 14, 20, 23.3. Не путать с distribution `project-harness doctor` версии 0.5.0, которая проверяет Engine/registries/documentation, **не** контейнерную изоляцию.

## Доступный интерфейс (Python API, не public CLI)

`src/project_harness/sandbox/{__init__,base,podman_rootless,profiles}.py` предоставляет `SandboxRunner` (`doctor(profile)`, `run(request)`), `RootlessPodmanRunner(configured_executable=...)` и `validate_sandbox_profile(profile)`. Интеграция с `execute-current` и `executor-doctor` относится к отдельному PH-051-09; сейчас **этих CLI-команд нет**. `CodexCliLocalAdapter.doctor` PH-051-02 всё ещё сообщает `BLOCKED / SANDBOX_UNAVAILABLE` до последующего подключения trusted runner, что предотвращает преждевременную автоматическую активацию.

`profile` — ранее введённый strict `sandbox_profile.schema.json` (`sandbox_profile` envelope либо inner object). Допускается только `ACTIVE`, backend `ROOTLESS_PODMAN`, immutable image `name@sha256:<64 hex>`, `READ_ONLY`, non-root, drop all caps, no-new-privileges, **ровно** три writable scopes `/workspace/product`, `/output`, `/tmp`, и positive bounded limits. `configured_executable` — ожидаемое имя/абсолютный **внутриконтейнерный** binary, например `codex`; наличие проверяет реальный doctor в указанном image. Mutable tags и произвольные executable strings не допускаются.

Минимальная диагностика из извлечённого Engine (не утверждение об успешной изоляции):

```bash
PYTHONPATH=src python - <<'PY'
from project_harness.sandbox import RootlessPodmanRunner
from project_harness.serialization import load_data
profile = load_data('path/to/SBX-ROOTLESS-PODMAN-001@1.yaml')
status = RootlessPodmanRunner(configured_executable='codex').doctor(profile)
print(status)
assert status['status'] != 'PASS' or status['isolation_verified'] is True
PY
```

Пример требует **реального**, локально доступного, pinned image с `/bin/sh`, `python3` и заданным executable. Указанный в примере `path/to/...` заменяет оператор; sample не хранит creds и не запускает container, пока реальный doctor не разрешит это.

## Жёсткая sandbox policy

Runner вызывает на host **только локальный Podman CLI**, с `--remote=false`; обычный agent argv передаётся исключительно `podman run --entrypoint <validated executable> <pinned-image> ...`, без host `shell=True`, без второго backend и без fallback. Root UID на host блокирует auto; `podman info` должен явно показать `host.security.rootless=true`. Image должен существовать локально; `--pull=never` исключает неявную загрузку.

Podman argv принудительно включает `--userns=keep-id`, non-root `--user`, `--read-only` / `--read-only-tmpfs=false`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`, `--pid=private`, `--ipc=private`, `--network=none`, `--pids-limit`, `--memory`, `--cpus`, `--image-volume=ignore`, `--unsetenv-all` и `--log-driver=none`. Установка не привносит host `HOME`, SSH/socket/cloud credentials, host env или произвольный `--mount`. Container `HOME=/home/harness` — размерно ограниченный tmpfs, `/tmp` — tmpfs. Только три bind mounts: exact per-Run `/product:rw`, `/control:ro`, `/output:rw`. Их host источники должны быть real dirs под отдельным execution root, disjoint с canonical project и `.harness`; root builder появится только в PH-051-04.

Default network `NONE` обязателен и реально задаётся `--network=none`. **`EXPLICIT_APPROVED_EGRESS` полностью BLOCKED/NETWORK_NOT_APPROVED на этом этапе**: ни постоянный profile, ни потенциально подставленные поля Run не считаются formal approval. PH-051-09 обязан добавить per-Run capabilities `NETWORK_WRITE` и `MODEL_EXTERNAL_EGRESS`, exact formal approval и sensitivity checks, прежде чем разрешить egress. Нет destination allowlist, host networking, port mappings или privileged flags.

Runner принимает заранее подготовленную структуру: `sandbox_profile`, `argv`, `stdin_mode: CLOSED`, `network_mode: NONE`, `execution_root`, `canonical_project_root`, `product_dir`, `control_dir`, `output_dir`, опциональный **сужающий** `timeout_seconds`; `run_context` разрешён лишь как no-op forwarding metadata для ранее подготовленного Executor. Любые `shell`, raw `env`, `host_env`, credentials, arbitrary Podman flags, другие mounts и расширяющие limits отклоняются. Источники папок проверяются **до и после** doctor. Этапы PH-051-04/06 должны гарантировать доверенное создание snapshot, исключение unsafe links, binding Run и secret refs до вызова runner.

## Реальные self-tests doctor и fail-closed statuses

`doctor` выполняет только фактические container probes; schema-мок/вызов `doctor` distribution не может вернуть изоляционный PASS:

1. Наличие локального executable `podman`, его `info` с rootless=true и локального `@sha256` image (без pull).
2. В отдельном disposable container non-root UID, `/proc/self/status` `CapEff=0` и `NoNewPrivs=1`; запись в rootfs и control запрещена, host sockets отсутствуют; product/output writable и output bytes видны в host test directory, `HOME` отдельный tmpfs.
3. `python3` внутри pinned image проверяет cgroup CPU/memory/pids **по effective kernel values**, mountinfo root/control `ro`, product/output `rw`, `HOME`/`/tmp` как tmpfs и отсутствие default route/IPv4+IPv6 outbound при `NONE`. Отсутствие Python/cgroup/детерминированного network evidence даёт `UNKNOWN` и **BLOCKED**, а не PASS. Нельзя вывести isolation PASS из одного успешного `--network=none` флага.
4. Отдельный process проверяет configured executable; stop/timeout probe запускает бесконечную команду внутри container, timeout останавливает container (SIGTERM→bounded cleanup) и подтверждает отсутствие по `podman container exists`.

Каждый Run заново проходит реальный doctor; перепроверка mount sources, bounded stdout/stderr и время process ограничивают исполнение, при timeout/overflow `podman stop`/`rm --force` и kill процесса. Host crash/orphan durable recovery остаются PH-051-10. `doctor` выдаёт `status: PASS` и `isolation_verified: true` **только** если пройдены все probes. Иначе `BLOCKED` + `SANDBOX_UNAVAILABLE`, `SANDBOX_POLICY_FAILURE`, `EXECUTOR_UNAVAILABLE` либо `NETWORK_NOT_APPROVED`, без агентского запуска на host.

## Воспроизводимый тест на подходящем Linux host

Нужен настроенный rootless Podman с cgroup v2/ресурсными ограничениями и **уже загруженным по digest image**. Image обязан содержать `/bin/sh`, POSIX tools (`id`, `cat`), `python3` и configured executable. Не используйте tag-only image. Отдельная CI/offline security matrix запускается при явных переменных:

```bash
export PH_TEST_PODMAN_IMAGE='registry.example/codex-runtime@sha256:<real-64-hex-digest>'
export PH_TEST_CONTAINER_EXECUTABLE='python3'  # для test invocation; в реальном Codex image — codex
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_03_rootless_podman
```

`<real-64-hex-digest>` — обязательный **реальный digest**, пример не является допустимым image. Если Podman/доверенного image нет, `test_19_real_rootless_doctor_and_container_run` сообщает `skipped / NOT RUN`; это означает **NO GO для isolation/security acceptance**, а не пройденный тест. Mock/unit-only проверки валидируют контракт, **не подтверждают Linux sandbox**. В промежуточных ZIP нет production-run approvals и нет активации `execute-current`.

## Сохранённое и будущие границы

Не меняются `PROJECT_INPUT@4`, registries (`ID@3`, statuses@6, contract catalog@6), Stage/Gate/level-up/maintenance/Brownfield, exact evidence/approval, `next→verify→complete`, manual handoff, immutable history и ранее реализованный PH-051-02 adapter/argv contract. PH-051-04 создаст disposable root, PH-051-05 свяжет agent CLI, PH-051-06 подтвердит result/secret contract, PH-051-07 проведёт независимую sandboxed verification, PH-051-08 — atomic apply, PH-051-09 — public runtime. Ни один из этих шагов не реализуется в PH-051-03.
