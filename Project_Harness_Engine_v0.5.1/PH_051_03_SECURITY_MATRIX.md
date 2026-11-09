# PH-051-03 — security validation matrix (v0.5.1 WIP)

**Дата:** 2026-10-25  
**Статус:** `NO-GO` для Podman OS isolation acceptance: test runner — Linux/UID 0, `podman` отсутствует. **MOCK/Python unit tests не подтверждают OS sandbox.**

| Контроль | Проверка реализации | Реальная проверка Podman на этом стенде |
|---|---|---|
| Единственный backend `ROOTLESS_PODMAN`, no host Codex CLI | Unit/AST/argv: PASS | NOT RUN |
| Только локальный Podman `--remote=false`, rootless UID | Unit: PASS; actual host root → `SANDBOX_UNAVAILABLE` | NOT RUN (нет Podman) |
| Immutable `image@sha256` и `--pull=never` | Schema+unit: PASS | NOT RUN |
| Rootfs `ro`, control `ro`, product/output `rw` (mountinfo) | argv policy + actual mountinfo probe implemented | NOT RUN |
| `drop ALL`, `no-new-privileges`, non-root UID | argv/negative tests PASS; actual `/proc/self/status` probe implemented | NOT RUN |
| Нет host HOME, docker/podman sockets, SSH/credentials, arbitrary mounts | argv/path policy: PASS; in-container checks implemented | NOT RUN |
| `/tmp` и HOME — bounded tmpfs | argv+mountinfo probe implemented | NOT RUN |
| `NONE` network, outbound IPv4/IPv6 blocked | argv: PASS; socket/default route probe implemented | NOT RUN |
| `EXPLICIT_APPROVED_EGRESS` без per-Run approvals | Reject: PASS, `NETWORK_NOT_APPROVED` | NOT RUN |
| cgroup CPU/memory/pids hard limits | argv: PASS; kernel cgroup probe implemented | NOT RUN |
| Bounded process runtime/output, stop/rm, no child survivor | timeout/output fake/argv tests PASS; real container termination probe implemented | NOT RUN |
| Configured executable inside pinned image | contract/probe implemented | NOT RUN |
| Podman CLI start failure (125/126/127), bad info, missing image | Negative unit tests PASS/fail closed | NOT RUN |
| Integration with disposable snapshot and public `execute-current` | DEFERRED PH-051-04 and PH-051-09 per plan | NOT IMPLEMENTED (out of scope) |

`RootlessPodmanRunner.doctor()` returns `PASS` **only after real probes**. On this host the actual result is `BLOCKED / SANDBOX_UNAVAILABLE / isolation_verified=false` (see `PH_051_03_LOGS/SANDBOX_FAIL_CLOSED_ENVIRONMENT.json`).

**Воспроизведение на пригодном стенде:** запустить под **не-root** пользователем с установленным rootless Podman, активными cgroups, локальным image с реальным `@sha256` digest, `/bin/sh` и `python3` и configured executable:

```bash
export PH_TEST_PODMAN_IMAGE='registry.example/runtime@sha256:<actual-local-image-digest>'
export PH_TEST_CONTAINER_EXECUTABLE=python3
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_03_rootless_podman
```

Строка `<actual-local-image-digest>` — placeholder, не существующий image. Этот тест должен смениться со `skipped` на реальную проверку и **PASS** до признания security acceptance.
