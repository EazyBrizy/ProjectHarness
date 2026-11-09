# PH-051-11 — rootless Podman security validation и negative matrix

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Обновлено:** 2026-10-29 (PH-051-11)  

**Контракт:** normative v0.5.1 §§6–11, 20, 23.3–24; PH-051-11; статус `v0.5.1-WIP / NOT RELEASED`. Это процедура проверки реальных OS boundaries. **Mock/fake runner unit PASS никогда не равен rootless Podman PASS.**

## Необходимые условия стенда

Linux под **обычным non-root пользователем** (`id -u != 0`), локальный `podman` rootless с рабочими cgroups v2, пользовательскими namespaces и resource controls; container image **уже существует локально по immutable `@sha256:<64 hex>`** (pull во время теста запрещён). Image содержит `/bin/sh`, `id`, `cat`, `python3`, а в production image — реально проверяемый `codex` CLI. Не использовать выдуманный образ, mutable tag, тест с root UID либо команду на host с `sudo` как доказательство rootless. Фиксируйте `uname -srm`, `cat /etc/os-release`, `id -u`, `podman --version`, `podman info --format json`, `podman image exists <pinned-digest>` и `sha256` spec/image у себя в security evidence; никогда не сохраняйте raw environment/secrets.

```bash
id -u
podman --version
podman info --format json
  # Установите значение ТОЛЬКО после реальной локальной проверки точного image digest:
export PH_TEST_PODMAN_IMAGE='registry.example/harness-runtime@sha256:<actual-64-hex-digest>'
export PH_TEST_CONTAINER_EXECUTABLE='python3'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_03_rootless_podman
```

`<actual-64-hex-digest>` — обозначение реального значения, не копируйте его в автоматический запуск. Тест `test_19_real_rootless_doctor_and_container_run` **должен именно выполнить Podman и PASS**, а не `skipped`. Он запускает реальный doctor с probes и при `python3` проверяет output mount. Все остальные `test_ph_051_03_*` unit tests с моком или argv validation — полезны, но их PASS не является kernel attestation. Для smoke `execute-current` требуется ещё отдельный approved opt-in Project Instance и fake Codex **внутри** pinned image (нельзя запускать fixture Python на host и называть его E2E). Не хранить секретное содержимое stdout/stderr или root в отчёте.

## Подлежащие evidence контроли

| ID | Реальный сигнал PASS | При FAIL/UNKNOWN/отсутствии стенда |
|---|---|---|
| S01 | Kernel `/` `ro`; попытка создать rootfs file denied | `NOT TESTED / NO GO` |
| S02 | `/workspace/control` `ro`, попытка записи denied | `NOT TESTED / NO GO` |
| S03 | Effective container UID non-root, `CapEff=0`, `NoNewPrivs=1` | `NOT TESTED / NO GO` |
| S04 | Host home, Docker/Podman sockets, SSH/cloud credential mounts отсутствуют; ephemeral HOME tmpfs | `NOT TESTED / NO GO` |
| S05 | `--network=none`; outbound IPv4 и IPv6/DNS невозможны; kernel probe не UNKNOWN | `NOT TESTED / NO GO` |
| S06 | cgroup effective memory/pids/CPU ограничены и проверены внутри container | `NOT TESTED / NO GO` |
| S07 | Bounded runtime, stop→remove, no orphan/child survivor | `NOT TESTED / NO GO` |
| S08 | `/output` writable, exact result file действительно попал в host execution root | `NOT TESTED / NO GO` |
| S09 | `/tmp` и HOME ограничены, product root writable, real canonical root не mounted на запись | `NOT TESTED / NO GO` |
| S10 | Configured executable присутствует и запускается только внутри pinned image | `NOT TESTED / NO GO` |
| S11 | Result channel отвергает missing/oversize/non-regular/symlink/hardlink и unexpected outputs | Собрать реальные негативные кейсы, unit PASS отдельно |
| S12 | Diff rejects special file/unsafe symlink/out-of-scope/delete; secret echo/product leak blocks apply | Собрать реальные негативные кейсы, unit PASS отдельно |
| S13 | Independent SANDBOXED verifier FAIL/timeout не вызывает canonical apply | Проверить из реального Run; mocks отдельно |
| S14 | Crash, orphan/quarantine, atomic journal replay не создают mixed canonical bytes | Fault-injection отдельно, real container cleanup отдельно |
| S15 | Without Podman/missing pinned image: public `executor-doctor` BLOCKED; никакой host Codex invocation | Public negative smoke может быть PASS без Podman |

**Граница доверия:** `NONE` = реальный network isolation. `EXPLICIT_APPROVED_EGRESS` (нормативный режим) не имеет destination allowlist и требует двух capabilities (`NETWORK_WRITE`, `MODEL_EXTERNAL_EGRESS`), exact per-Run approval, sensitivity policy. Текущий backend fail-closed отклоняет **любое** egress (`NETWORK_NOT_APPROVED`), несмотря на CLI флаги. Успешный YAML validation **не** подтверждает network permission. `--keep-execution-root` также отвергается без действующей debug policy. Нет host CLI fallback и второго backend.

## Вызовы адресных негативных тестов (unit/functional, не OS)

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_03_rootless_podman
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_06_result_channel
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_07_sandbox_verification
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_08_atomic_apply
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_09_automatic_runtime
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_10_migration_recovery
```

Записывайте фактический return code и точный `testsRun/skipped/failures/errors` каждого. Если среда недоступна/privileged или `PH_TEST_PODMAN_IMAGE` не подтверждён, **не подставляйте фейковый digest и не отчитайтесь PASS**. Для incomplete security matrix итог `NO GO` до следующего real rootless стенда/PH-051-12.
