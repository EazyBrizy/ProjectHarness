# PH-051-10 — отчёт об имплементации, тестах и сохранённых инвариантах

**Исполнение:** 2026-10-26. **Версия:** `0.5.1-WIP / NOT RELEASED`. **Нормативная спецификация:** `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`, §§17, 19.1, 21–22; граница `PH-051-10` утверждена в плане.

## Проверенная входная база

- Engine PH-051-09 — SHA-256 `ea87aada1c590710092203f02b48c838db89930f0b04ac3f4f51ab994e1edc6d`.
- Documentation PH-051-09 — SHA-256 `fe50a9cb1c39c23635f7d5484d14a7ff307e74cd44383560c73cfe83c3fdf15f`.
- Нормативный документ v0.5.1, SHA-256 `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e`.
- Последовательность исправлений предыдущих этапов сохранилась; модификации вне PH-051-10 производились только в directly affected fixture `test_ph_051_06_result_channel.py`.

## Изменения

1. Публичная `migrate-project` мигрирует 0.5.0/schema6→0.5.1/schema7, `MIG-ENGINE-0.5.0-TO-0.5.1`; defaults: `MANUAL_HANDOFF`, null profile refs, `NONE`, `EXPLICIT_AFTER_VERIFICATION`. Совместима с историческими manual Runs и v0.4.1 migration route. Backup/journal + fsync + rename switch с двумя тестируемыми crash boundaries.
2. Новые Run records получают provenance `MANUAL_EXTERNAL | LOCAL_AUTOMATIC`; immutable historical Run и Stage artifacts не переписываются. Миграция не изменяет accepted maturity/target/product.
3. Bounded SIGTERM→grace→SIGKILL в host process-group/Podman container; Run- и project-bound labels, проверка rootless Podman и no optimistic cleanup success.
4. Orphan containers и disposable roots проверяются до retry, quarantine изолирует частичный output, восстановление apply journal предшествует новому Run. Post-commit cleanup recovery не повторяет agent execution и не откатывает валидный commit.
5. Bounded immutable cleanup receipt отдельно от independent PASS/apply; no execution roots/logs inside export/handoff. Синхронизированы wheel, source/build mirrors, embedded и отдельные docs.

## Проверка

**Адресная матрица PH-051-10:** **PASS — 17/17** (`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -q tests.test_ph_051_10_migration_recovery`; log `PH_051_10_LOGS/TARGETED_FINAL.log`). Покрыты migration/replay, negative controls, crash before/after directory swap, historical digests, origin, quarantine, rootless labels, unavailable Podman fail-closed, interrupted Run, completed post-commit cleanup replay, symlink attacks, secret and cleanup classifications.

**Регрессия предыдущих этапов:** **PASS — 335 PASS / 2 SKIP (337 тестов)**; доказательства: `PH_051_10_LOGS/REGRESSION_FINAL_MATRIX.json` и исходные `REGRESSION_SHARD_01..12.log` / `REGRESSION_RETRY_SHARD_01,02,05.log`. Исходный параллельный прогон: 335 тестов, 2 skip, FAIL в трёх группах. Две группы завершились тайм-аутами вложенных CLI-процессов при перегрузке; третья — из-за неактуального mock-fixture без обязательного `run_id`. После точечного исправления fixture и защиты приоритета `SECRET_LEAK_DETECTED` три группы перепроверены отдельно: shard 1 = 13 PASS, shard 2 = 2 PASS, shard 5 = 50 PASS. Остальные девять групп: PASS по первоначальным логам. Единый монолитный прогон 337 тестов в одном процессе отдельно не заявляется..

**Документация:** `python tools/validate_documentation.py . --zip <final-docs-zip> --json <report>` из embedded docs directory: `PASS`, 36 checks, 0 errors, 0 warnings; CRC PASS, tree exact, manifest digests match. Источник и embedded documentation byte-identical.

**Wheel и публичные интерфейсы:** `python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist` PASS; установленный wheel `project-harness --version = 0.5.1`, `doctor = PASS`. На legacy-fixture: `migrate-project` = MIGRATED → duplicate = NO_ACTION; `validate-project` = PASS; `next` = READY_FOR_CODEX.

**Environment/security:** `id -u = 0`, `podman` не установлен. Реальный non-root Podman security integration: **NOT RUN**. Negative/unit/mocked tests **не** подтверждают OS sandbox. Automatic executable routing не получает bypass или host fallback. Итог **NO-GO final release** до следующих PH-051-11/12 и real Podman tests, в рамках этого WIP этапа.

## Подтверждение scope / неизменности

- Изменения runtime: только migration/cleanup/Podman Run supervision + CLI help; mirror copies; одно обновление contract-valid mock fixture.
- `stages.py`, `stage_transactions.py`, `apply.py`, `maintenance.py`, `evidence.py`, registries и schemas не правились.
- Тесты сравнивают hashes `PROJECT_INPUT_ACCEPTED`, Stage Plans/Gates/Acceptance Reports, pre-existing completed manual Runs, accepted target/state; изменения источника product tree запрещены при migration. Historic PH-F08 / PH-051-01..09 отчёты оставлены оригинальными.
- No automatic opt-in on migration, no Git/PR/deployment, no second provider or sandbox backend, no changes to maturity sequencing.

**Артефакты:** `Project_Harness_Engine_v0.5.1_PH_051_10.zip`, `Project_Harness_Documentation_v0.5.1_PH_051_10.zip`, SHA-256 manifest внутри каждого, `PH_051_10_CHANGED_FILES.md`, `PH_051_10_PRESERVED_INVARIANTS.md`, `PH_051_10_LOGS/` с полным исходным и повторными прогонами, этот отчёт.
