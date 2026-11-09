# PH-051-11 — фактическая матрица проверки безопасности Podman / local execution

**Исполнено:** 2026-10-29. **Версия:** `0.5.1-WIP / NOT RELEASED`. **Нормативная база:** v0.5.1 §§6–11, 20, 23.3–24; PH-051-11. **Итог mandatory OS-boundary acceptance: NOT TESTED / NO-GO.** Нельзя объявлять rootless sandbox проверенным на этом стенде.

## Фактически доступный стенд и preflight

| Параметр | Факт |
|---|---|
| ОС | Debian GNU/Linux 13 (trixie), x86_64, Linux kernel `6.18.55` |
| `id -u` | `0` (root); не является подходящим rootless user namespace тестовым пользователем |
| `command -v podman` | нет бинарника (`not found`) |
| `podman --version` | NOT AVAILABLE — не подменён предполагаемой версией |
| `podman info`, effective rootless, cgroups v2 | NOT TESTED — Podman отсутствует |
| Реальный immutable pinned image digest | NOT PROVIDED / NOT VERIFIED; пример `sha256:aaaa…` не является image evidence |
| Self-test `test_19_real_rootless_doctor_and_container_run` | SKIPPED, не PASS |
| Fake Codex в **реальном** Podman | NOT TESTED — контейнерный стенд отсутствует |
| Host Codex запуск | НЕ ПРОИЗВОДИЛСЯ |

Фактические команды проверки среды: `id -u`, `uname -srmo`, `cat /etc/os-release`, `command -v podman`. Прогон `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_03_rootless_podman tests.test_ph_051_06_result_channel tests.test_ph_051_07_sandbox_verification tests.test_ph_051_08_atomic_apply tests.test_ph_051_09_automatic_runtime tests.test_ph_051_10_migration_recovery tests.test_ph_051_11_operator_docs` дал 104 теста: **103 PASS, 1 SKIP (real Podman)**; исходный `PH_051_11_LOGS/FOCUSED_NEGATIVE_AND_SECURITY.log`. Это доказывает только контрактные unit/integration/negative сценарии без реального OS-isolation, а не реальную защиту container.

## Security controls

| ID | Требование / проверяемая граница | Проверка в данном окружении | Фактический результат |
|---|---|---|---|
| S01 | Read-only container rootfs; actual write denied | Реальный Podman rootfs probe | **NOT TESTED — NO-GO** |
| S02 | Read-only `/workspace/control`; actual write denied | Реальный mount/write probe | **NOT TESTED — NO-GO** |
| S03 | Effective non-root UID, dropped caps, `NoNewPrivs=1` | Kernel `/proc/self/status` inside real container | **NOT TESTED — NO-GO** |
| S04 | No host home, SSH/cloud creds, Podman/Docker sockets | Реальный mount listing inside pinned image | **NOT TESTED — NO-GO** |
| S05 | `NONE`: IPv4, IPv6, DNS egress denied | Network isolation attempt inside real container | **NOT TESTED — NO-GO** |
| S06 | Actual cgroup CPU/memory/pids caps | Effective cgroup inspection & limits test | **NOT TESTED — NO-GO** |
| S07 | Timeout/kill, no surviving descendants/containers | Real Podman child process and bounded termination | **NOT TESTED — NO-GO**; fake/runner unit checks PASS отдельно |
| S08 | Product/output exact writable, result path bounded | Real write to `/output/agent-result.json` & copy check | **NOT TESTED — NO-GO**; result validator unit cases PASS |
| S09 | Ephemeral HOME/tmpfs; disposable product writable; canonical repo not writable | Actual mounts and UID checks | **NOT TESTED — NO-GO**; unit mount-command tests PASS |
| S10 | Configured Codex executable truly inside pinned image | Real image digest and `command -v` | **NOT TESTED — NO-GO** |
| S11 | Missing/malformed/oversize/extra output, unsafe links/type, secret echo | `test_ph_051_06_result_channel`, sandbox-output negative tests | **PASS (unit only)**; real container isolation NOT TESTED |
| S12 | Diff/write-scope fence, symlink/special-file protection, secret leak blocked | `test_ph_051_08_atomic_apply` | **PASS (unit/integration without Podman)**; OS side NOT TESTED |
| S13 | Independent sandbox verifier FAIL prevents apply | `test_ph_051_07_sandbox_verification`, apply negative tests | **PASS (mock runner only)**; real separate container verifier NOT TESTED |
| S14 | Crash-journal all-old/all-new, orphan/quarantine/retry | `test_ph_051_08_atomic_apply`, `test_ph_051_10_migration_recovery` | **PASS (fault injection/unit)**; real orphan container cleanup NOT TESTED |
| S15 | No Podman + default manual → explicit BLOCKED, no host execution or silent fallback | Installed wheel `executor-doctor`, `execute-current`, option negatives | **PASS (public CLI negative smoke)**; not an isolation attestation |

Отдельно выполнен публичный smoke установленного wheel и bundled entrypoint: **21/21 PASS**; журнал `PH_051_11_LOGS/PUBLIC_OPERATOR_SMOKE.log` и машинный результат `.json`. В частности `executor-doctor` и `execute-current` для manual-проекта отвечают ожидаемыми BLOCKED/exit3; попытки `EXPLICIT_APPROVED_EGRESS` и `--keep-execution-root` также fail-closed. Наличие опций `--approval` / `--network` **не** означает технически реализованную/утверждённую сеть. Не установлен и не проверялся any per-host egress allowlist.

## Запрет на ложный PASS и дальнейшая воспроизводимая приёмка

Запускать из корня Engine на **отдельном Linux-хосте с непривилегированным UID** и действительно установленным rootless Podman; указать уже существующий в локальном OCI storage образ с проверенным `@sha256:<64-hex>`, фактический Codex CLI или отдельный pinned fake Codex image для integration. Записать настоящие `podman --version`, `podman info`, exact pinned digest и self-test log; не заменять образ выдуманным digest или mutable tag.

```bash
id -u
podman --version
podman info --format json
podman image exists '<verified-repository@sha256:64hex>'
export PH_TEST_PODMAN_IMAGE='<verified-repository@sha256:64hex>'
export PH_TEST_CONTAINER_EXECUTABLE='python3'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_03_rootless_podman
```

В реальной security matrix необходимы негативные attempts root/control writes, host home/socket mount, network egress, resource exhaustion, children/kill, result channel abuse, symlink/secret leak, independent verifier FAIL и recoverable apply; после этого — approved automatic Project Instance через **публичный** contract (текущий `prepare` для `LOCAL_AUTOMATIC` является отдельным найденным blocker, не устранялся PH-051-11). Порядок и точные критерии: `05_Updates/15_Podman_Security_Validation_v0.5.1_WIP.md`.

**Решение PH-051-11:** документационные/unit/public smoke gates можно зачесть независимо, но mandatory real rootless Podman security acceptance = `NOT TESTED / NO-GO`. **PH-051-12 release GO не объявляется**.
