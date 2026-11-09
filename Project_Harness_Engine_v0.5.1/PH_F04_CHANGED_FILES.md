# PH-F04 — список точечных изменений

**Engine/Documentation:** v0.5.0. **Дата:** 2026-10-24.
**Контракт:** `Project_Harness_v0.5.0_Remediation_Plan_RU.md` / PH-F04; нормативная спецификация v0.5.0.

## Изменённая функциональная область

1. `src/project_harness/stages.py`: общая read-only операция `runtime_continuation` для фактически доступных операторских маршрутов, плюс расширение `stage_status` (`runtime_phase`, `maintenance_route`, exact `next_operator_route`). Стадийная cross-reference проверка допускает только governed exact-bound maintenance на уже принятом уровне.
2. `src/project_harness/runtime.py`: публичный `next` возвращает исполнимую CLI-команду на boundaries, отличает Gate-related и ordinary blockers, не резервирует future-stage Task и пересчитывает маршрут **после** резервирования Run; повторный вызов остаётся идемпотентным.
3. `src/project_harness/validation.py`: дополнительная проверка `Persisted runtime continuation and Stage boundary reachability`, actual CLI parser, exact Plan/Gate/revisions, accepted refs, statuses, Task/Run/DAG/maintenance/Gate blocker context, `NEXT_TASK` projections. Pre-migration v0.4.1 остаётся в своём режиме.
4. `tests/test_ph_f04_runtime_reachability.py`: десять регрессионных сценариев, включая заведомо недоступный route, проверку после резерва, false planning boundary, future-stage Task и ordinary/maintenance status.
5. Документация: README, CHANGELOG и операторские `08_Distribution/03_User_Workflows.md`, `08_Distribution/02_Project_Local_Structure.md`; производные FULL/GUIDE/FILE_INDEX/manifests пересобраны. Публикация не описывает несуществующие операции.

## Производные артефакты

- `build/lib/project_harness/{runtime,stages,validation}.py` синхронизированы с `src`.
- `dist/project_harness_engine-0.5.0-py3-none-any.whl` пересобран.
- Engine embeds standalone Documentation byte-identically; SHA-256 manifests пересчитаны.
- Engine отчёты `PH_F04_TEST_REPORT.md`, `PH_F04_CHANGED_FILES.md`, `PH_F04_TEST_LOG.txt` добавлены.

## Сохранённые границы

PH-F02 semantic subject-specific Gate evidence, PH-F03 governed active-stage planner, exact formal approvals, immutable Stage Acceptance Reports/old Runs, crash-consistent transactions, read-only Brownfield assessment, same-level maintenance and sequential stage fence не изменены по смыслу. Нового Executor Adapter, OS sandbox, Git/PR/deployment, nonlocal agents и v0.5.1+ функций нет. Это scoped PH-F04, **не** финальная PH-F08 приёмка.
