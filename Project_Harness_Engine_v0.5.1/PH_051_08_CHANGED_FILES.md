# PH-051-08 — Перечень изменений (v0.5.1 WIP)

**Дата:** 2026-10-26. **Исходная пара:** последние Engine/Documentation `PH_051_07`; **scope:** bounded diff / write-scope fence / secret scan / crash-consistent product apply / Apply Evidence. Не является релизом v0.5.1.

## Новые файлы

| Файл | Изменение |
|---|---|
| `src/project_harness/apply.py` | Отдельный kernel-owned сервис `apply_verified_diff()`/`recover_apply()`: exact Run+verification binding, file diff/Task scope, controlled secret scan, baseline double-check, durable PREPARED/COMMITTED journal, rollback, immutable Apply Evidence. |
| `build/lib/project_harness/apply.py` | Синхронизированная source distribution/build mirror нового модуля. |
| `tests/test_ph_051_08_atomic_apply.py` | 25 targeted unit/negative/integration tests; fault-injection, symlink/hardlink/special file, scope, secrets, baseline, replay, evidence, recovery. |
| `docs/Project_Harness_Documentation_v0.5.1/05_Updates/11_Validated_Diff_and_Crash_Consistent_Apply_v0.5.1_WIP.md` | Встроенная операторская документация API, границ доверия и восстановлений. |
| `PH_051_08_CHANGED_FILES.md`, `PH_051_08_TEST_REPORT.md`, `PH_051_08_LOGS/` | Отчётность и фактические test/smoke/validation logs. |

## Синхронизация дистрибутива

- `CHANGELOG.md` — запись PH-051-08, без изменения старых записей.
- `docs/Project_Harness_Documentation_v0.5.1/CHANGELOG.md`, `FILE_INDEX.md`, `Project_Harness_Architecture_v0.5.0_FULL.md`, `MANIFEST.sha256` — обновление embedded документации с новым разделом.
- `src/project_harness_engine.egg-info/SOURCES.txt` — список включённых исходных файлов.
- `dist/project_harness_engine-0.5.1-py3-none-any.whl` — пересобранный wheel из финальных исходников; версия остаётся `0.5.1-WIP` на уровне поставки.
- `MANIFEST.sha256` — новый SHA-256 inventory конечного Engine ZIP (сам manifest исключён).

Отдельный Documentation ZIP содержит аналогичные изменения: новый `05_Updates/11_Validated_Diff_and_Crash_Consistent_Apply_v0.5.1_WIP.md`, обновлённые `CHANGELOG.md`, `FILE_INDEX.md`, `Project_Harness_Architecture_v0.5.0_FULL.md`, `MANIFEST.sha256`.

## Сохранённые ограничения

- **Не изменялись** существующие production runtime/stage/maintenance/gate/approval/verification/adapters/sandbox modules, схемы и реестры. Новые public `execute-current`, `executor-doctor`, unified Run lifecycle относятся к PH-051-09, не этому пакету.
- Agent не получает write-mount canonical product или `.harness`. Сам сервис не запускает Codex и не переводит Task в DONE, не выполняет Stage acceptance и не подменяет human approval.
- Общесистемный orphan cleanup, автоматическое восстановление при новом запуске и миграции остаются PH-051-10.
- Rootless Podman security integration **NOT RUN** в текущей среде; GO v0.5.1 запрещён до PH-051-11/12.
