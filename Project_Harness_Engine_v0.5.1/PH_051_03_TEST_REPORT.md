# PH-051-03 — implementation / test report

**Дата:** 2026-10-25  
**Версия:** `0.5.1 WIP / NOT RELEASED`  
**Область:** only PH-051-03 / `ROOTLESS_PODMAN` sandbox runner + honest doctor, focused tests/docs/distribution mirrors.  
**Итог:** реализация и регрессии **PASS**; реальная Podman security acceptance **NOT RUN / NO-GO**.

## 1. Проверенные входы и нормативная база

- Latest Engine ZIP `(1)` — SHA-256 `f4f3b639f0e71a5563a52f6f97bb714ff85b54e9b9ffdac6c1371eae6f80b149`.
- Latest Documentation ZIP `(1)` — SHA-256 `29de85c9db1604a731eaaa916f84890d0bb06f64b93f0cbe00974a4f58fd6b86`.
- Normative specification archive — SHA-256 `56bca615b7da5a0f48d0479c2de24ccd151fcefbf453fdfea89eab0d2675219e`; normative document `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md` §§ 6–8, 10, 14, 20, 23.3.
- Actual input archives CRC/manifest valid; preexisting PH-051-01/02 code, schemas, registries present.
- Engine/distribution `0.5.1`, Harness `SCHEMA_VERSION=7`, profiles/SBX registry from PH-051-01 unchanged. Contract Registry `@6`, ID Registry `@3`, Status Registry `@6` unchanged.

## 2. Реализация (only scoped changes)

- New `src/project_harness/sandbox/__init__.py`, `base.py`, `profiles.py`, `podman_rootless.py`: `SandboxRunner`, `RootlessPodmanRunner`, strict sandbox profile and disposable-mount boundary validation. No Docker/VM/remote/backend fallback.
- Podman host process only; local `--remote=false` and immutable `image@sha256` with `--pull=never`; no unsandboxed agent process. `--userns=keep-id`/non-root UID, `--cap-drop=ALL`, `no-new-privileges`, readonly rootfs, exact binds (`product:rw`, `control:ro`, `output:rw`), bounded tmpfs `/tmp`/HOME; no host home/agent sockets/implicit host env.
- CPU/memory/pids/time/output limits, bounded Podman process output and termination; real self-tests for mountinfo/rootfs/control permissions, non-root/CapEff/NNP, cgroup limits, IPv4/IPv6 no egress, configured executable and timeout/container stop. If any required probe unavailable or inconclusive, doctor BLOCKED; `EXPLICIT_APPROVED_EGRESS` blocks before governance exists.
- `run` has exact bound disposable directories and redoes doctor; CLI 125/126/127 Podman startup failures cannot masquerade as isolation success. No integration with `execute-current`, independently sandboxed verifier, snapshot or apply (reserved for PH-051-04–09).
- New focused `tests/test_ph_051_03_rootless_podman.py` and operator note `05_Updates/07_Rootless_Podman_Sandbox_v0.5.1_WIP.md`, Engine docs/mirrors/build wheel/README metadata synced.

## 3. Фактические тесты

Из Engine source tree, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests`:

| Group | Log | Tests | Actual result |
|---|---|---:|---|
| Existing regressions: PH-051-01/02, PH-F08, Stage transactions | `PREVIOUS_INVARIANTS.log` | 51 | PASS |
| Existing regressions: Engine/Gate evidence | `REGRESSION_02.log` | 24 | PASS |
| Existing regressions: maturity/target/PH-051-01 | `REGRESSION_03.log` | 28 | PASS |
| Existing regressions: intake, assessments, contract hardening | `REGRESSION_04.log` | 50 | PASS |
| Existing regressions: stage planning/levels | `REGRESSION_05.log` | 22 | PASS |
| Existing regressions: runtime/recovery/stage approval | `REGRESSION_06.log` | 32 | PASS |
| Existing regressions: semantic proof/Gate recovery | `REGRESSION_07.log` | 13 | PASS |
| Existing regressions: maintenance | `REGRESSION_08.log` | 7 | PASS |
| PH-051-03 focused tests | `TARGETED_FINAL.log` | 20 | **19 PASS, 1 SKIPPED** |

**202/202 уникальных прежних тестов PASS**, пройдены всеми модулями тестового набора раздельными группами. Запуски пересекаются по 25 старым тестам; нельзя суммировать числа в таблице без дедупликации. **Новые: 19 PASS + 1 SKIPPED / 20 discovered.** Совокупно: **221 PASS, 1 SKIPPED из 222 уникальных тестов** (202 + 20) — значения относятся к успешным scoped batch runs, а не к одному полному монолитному invocation.

Первая попытка монолитного `tests/run_tests.py`/unittest discovery была прервана по времени (`FULL_REGRESSION.log`), **она не засчитана как PASS**. Вместо неё последовательно доведены до `OK` все 202 существующих теста по группам. Это не отменяет пропуск реального rootless Podman security test.

Проверки distribution/docs:

- `python tools/validate_documentation.py . --zip ... --json ...` из standalone Documentation tree: **PASS, 36/36 checks, 0 errors, 0 warnings**, manifest и ZIP CRC валидны.
- `python -m pip wheel . --no-deps --no-build-isolation`, чистая установка wheel в тестовый virtualenv, installed `project-harness --version=0.5.1`: **PASS**.
- Installed `project-harness doctor`: **PASS** для distribution/registries; **это не проверка Podman isolation**.
- Installed sandbox API import: **PASS**, bundled `project_harness/sandbox/*.py` присутствуют в wheel.
- `tests.test_ph_051_03_rootless_podman`: 20 discovered, 19 PASS, 1 skipped; mocked process/argv tests прямо не засчитываются как реальная security acceptance.

## 4. Блокер стенда и честный status

`podman` отсутствует в `PATH`, Unix host UID=0. Результат фактического `RootlessPodmanRunner(...).doctor(valid_profile)` — `status=BLOCKED`, `reason_code=SANDBOX_UNAVAILABLE`, `isolation_verified=false`; **на host agent не запускался**. Отсутствие подлинных Podman probes оставляет матрицу изоляции `NOT RUN`, отдельно описанную в `PH_051_03_SECURITY_MATRIX.md`.

**Решение:** `PH-051-03 code/contracts: PASS (WIP)`; `real OS sandbox acceptance: NO-GO / NOT RUN`; `v0.5.1 release: NOT RELEASED` до PH-051-12. Следующая задача PH-051-04 остаётся самостоятельной, не подменяется фиктивной проверкой `doctor`.

## 5. Сохранённые ограничения v0.5.0 / PH-051-01/02

- Manual handoff и все публичные `next`, `verify`, `complete`, `prepare-stage-approval`, `accept-stage`, `plan-active-stage`, `level-up`, Brownfield assessment/maintenance продолжают работать; тесты зафиксированы в логах.
- Immutable input/report/run history, strict approvals, scope bounds, current canonical target, Stage Gate semantic evidence, stage transaction crash recovery не изменялись.
- Existing input@4/metadata/registry versions и executor profile normalization сохранены; PH-051-02 host-execution fallback остаётся закрыт.
- Не добавлены `executor-doctor`/`execute-current` CLI, automatic Run lifecycle, canonical root mutation, diff/apply, migration and cleanup. No v0.6.0 functionality.

## 6. Поставка

Архивы Engine/Documentation пересобраны с согласованными mirrors и `MANIFEST.sha256`. Конкретный список изменённых файлов: `PH_051_03_CHANGED_FILES.md`. Сырые логи и JSON доктора сохранены в `PH_051_03_LOGS/` внутри Engine ZIP.
