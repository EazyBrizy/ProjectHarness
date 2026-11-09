# PH-051-08 — Отчёт о реализации, тестировании и сохранении инвариантов

**Дата:** 2026-10-26. **Версия:** Project Harness v0.5.1 WIP / NOT RELEASED. **Статус пакета:** реализация bounded diff/apply completed; релизный GO v0.5.1 **не заявлен**.

## Исходные данные и нормативный контракт

- Engine: `Project_Harness_Engine_v0.5.1_PH_051_07.zip`, SHA-256 `f59329deffc4cfa042222df0a307c696c5865b453f7b5189aabd9233c4849000`.
- Documentation: `Project_Harness_Documentation_v0.5.1_PH_051_07.zip`, SHA-256 `8c294ee346f5d035c5c7d7ea222b66d1fcb8127067036603820c13cf63352561`.
- `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`: SHA-256 распакованного нормативного файла `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e`. Реализованы только §§12–13, 18–19, 22–23 в границах PH-051-08.
- Входные ZIP и их SHA-256 manifests проверены перед изменениями; входным деревом является PH-051-07, не более старый архив с тем же номером версии.

## Что реализовано

1. `src/project_harness/apply.py`: kernel-owned API `apply_verified_diff(...)`, `recover_apply(...)`, `ApplyFailure.reason_code`, без новой публичной команды или выполнения agent на host.
2. Trusted exact Run/JIT/project control bindings; принудительный независимый `SANDBOXED`-verification PASS, соответствие actual diff и Agent Result, разрешённым/запрещённым Task paths и expected artifacts. Reject unsafe symlinks/hardlinks/FIFO/special files и неизвестные path/mode changes.
3. Scan exact secret values в изменённых продуктовых файлах, persist Agent Result, bounded logs и verification diagnostics; нет ложного утверждения о произвольной DLP. Missing configured secret values / unsupported mandatory scan policy — отказ.
4. Recheck saved canonical baseline, content-hash write plan, PREPARED journal со staging+backups вне canonical root, protected create/replace/delete, fsync, rollback on interruption, immutable Apply Evidence (`EVD-*`) и durable COMMITTED marker. Recovery all-old или all-new; post-commit cleanup failure не выдаётся за rollback. Проверен replay.
5. Новые 25 targeted тестов, обновлённая встроенная/standalone документация и пересобранный wheel. **Не** реализованы PH-051-09 автоматический CLI/Run lifecycle, PH-051-10 discovery/orphan recovery/cleanup и v0.6.0 функционал.

## Запуски и результаты

| Проверка | Фактическая команда / метод | Результат |
|---|---|---|
| Негативные и интеграционные PH-051-08 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -q tests.test_ph_051_08_atomic_apply` | **PASS, 25/25**, `PH_051_08_LOGS/PH_051_08_TARGETED_FINAL.log` |
| Полная последовательная регрессия PH-F/PH-051 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python tests/run_tests.py` | **PASS, 300 tests executed, skipped=2**; запущена до финальной точечной доработки; финальная редакция отдельно проверена следующим прогоном |
| Все `test_*.py` на окончательных исходниках | `python -m unittest -q tests.<module> ...`, разбиение всех 27 модулей на 10 групп | **PASS, 305 тестов в 27 модулях, 2 skipped, 10/10 групп exit code 0**. Проверено на финальном исходном коде; `PH_051_08_LOGS/PH_051_08_FINAL_SHARDED_SUMMARY.json` и `PH_051_08_FINAL_SHARD_01..10.log` |
| Standalone Documentation validator + ZIP CRC/manifest | `python tools/validate_documentation.py <documentation-root> --zip <documentation-zip> --json <report.json>` | **PASS, 36 checks, 0 errors, 0 warnings**, 124 файлов, `PH_051_08_LOGS/documentation_validation.json` |
| Source entrypoint `project-harness.py` / installed wheel | `python -m pip wheel --no-deps --no-build-isolation .`; `pip install --no-index --no-deps <wheel>`; `project-harness --version`, `doctor`, API import | **PASS после финального MANIFEST**, установленный пакет в virtualenv с system-site-packages; без скачивания/переустановки зависимостей |
| Exact standalone и embedded docs | Byte-level `diff -rq` по деревьям | **PASS**, копии полностью одинаковы |
| Rootless Podman security / live Codex-in-container | `podman` в окружении отсутствует; процесс выполняется с UID 0 | **NOT RUN / NO-GO для release**, нельзя заменять mock checks результатами изолированного запуска |

## Fault injection и отрицательная матрица

Проверены: неподписанный/неподходящий independent verdict; несовпадение changed paths с Task scope или Agent Result; attempts на `.harness`, `.git`, symlink/hardlink/FIFO; missing expected artifact; baseline drift; неподтверждённая automatic policy; нестандартные mode-only changes; exact-secret leak в продукт/normalized result/логи; недостаточные secret env bindings; отказ на стадиях PREPARED, после отдельных file mutations, после evidence, перед COMMITTED и после COMMITTED; tampered backup; отказ cleanup после фиксации; сохранение mode существующего canonical файла; immutable evidence replay.

*Важно:* Crash-consistency означает детерминированное восстановление к all-old/all-new при начале следующей controlled recovery. Поскольку операции над несколькими файлами выполняются последовательно, процесс, наблюдающий дерево **до** recovery, может увидеть временно частично изменённый набор. Нет заявления о глобальной snapshot isolation для посторонних host readers.

## Сохранённые инварианты

- Не изменялись существующие runtime, Stage/Gate/approval, Brownfield, maintenance, schema/registry, executor, sandbox, verification production modules; предыдущие immutable artefacts и исторические отчёты сохранены.
- Manual `next → verify → complete`, gated Stage acceptance/level-up, Brownfield read-only, maintenance, exact evidence/target contracts остаются действующими; отдельный apply сервис не делает их автоматическими и не изменяет зрелость.
- Только independent PASS может дать право на apply; agent `exit_code=0`/`COMPLETED` недостаточен.
- Изменённый продукт перед write-plan должен иметь exact baseline; Race и unexpected external writes приводят к отказу/quarantine, без бесконтрольного recursive copy.
- Не введён public `execute-current` или unsandboxed fallback. Подключение этих компонентов, recovery на старте нового Run и реальные Podman acceptance tests остаются следующими отдельными этапами.

## Known limitations и честный статус

- Реальный rootless Podman security/self-test **NOT RUN**, автоматический маршрут в CLI ещё отсутствует, v0.5.1 остаётся **WIP / NOT RELEASED**.
- Сканирование секретов обеспечивает проверку только exact переданных значений; универсальная DLP/semantic scanner не заявлена.
- Для this package per-Run recovery явно вызывается через Python API; глобальный orphan/container discovery и retry-resume будут PH-051-10.
- SQLite/Git/distributed atomic transaction, PR/deployment и другие v0.6.x capabilities в scope не входят.

Приложения: `PH_051_08_CHANGED_FILES.md`, `PH_051_08_LOGS/*` в Engine ZIP; standalone Documentation ZIP с тем же новым 05_Updates/11 документом.
