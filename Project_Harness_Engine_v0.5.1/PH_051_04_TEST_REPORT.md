# PH-051-04 — отчёт о точечной реализации и тестировании

**Дата:** 2026-10-25  
**Engine / Documentation:** v0.5.1 **WIP / NOT RELEASED**; пакет **PH-051-04 IMPLEMENTED**.  
**Security release gate:** **NO-GO** для всего автоматического v0.5.1: реальный rootless Podman не установлен/недоступен на этом стенде; mandatory OS isolation tests не запускались. Это не дефект ручного v0.5.0 workflow и не симуляция успешного Podman doctor.

## 1. Exact inputs и нормативный контракт

- Последний Engine `(2)` ZIP SHA256 `5c47c2aa6217b64a07cc8e116b0e8a56e72e441353d2e798797c0d2f3f4527a0` — CRC **PASS**.
- Последний Documentation `(2)` ZIP SHA256 `7ba8d389a56c5fe0708cf6f601058c91d12dcbd5aab971551c0eba027f6b3653` — CRC **PASS**.
- Нормативная `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md` SHA256 `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e` — точное совпадение с plan; §§3,8,12,18.
- Локальная зона **PH-051-04** из `Project_Harness_v0.5.1_Implementation_Plan_RU.md`. Предыдущие PH-051-01, 02, 03 не переписаны.

## 2. Что изменено

1. Создан `src/project_harness/execution_roots.py` — `prepare_execution_root(project_root, runtime_root, *, run_ref=None)`, `check_execution_baseline(project_root, binding)`; без CLI/Run execution. Единственный **текущий persisted active Run**; строгие точные Run/Task/Bundle/Context/RunPlan refs; раздельный внепроектный путь `/<runtime-root>/<project-id>/executions/<RUN-ID>/(product|control|output)`.
2. В `safety.py` добавлен безопасный product-only snapshot: byte equality и отдельные inode; symlink, hardlink и special files не пересекают boundary. Для digest добавлен nonblocking nofollow regular-only reader, чтобы FIFO не блокировал Snapshot. Canonical product baseline проверяется до и после и совпадает с копией.
3. В `control/` ровно семь допустимых материалов: Prompt Bundle markdown+record, Context Packet, Task Contract, Run Plan, очищенная execution policy и schema Agent Task Result; `chmod 0444/0555`, Podman `control:ro` mount policy из PH-051-03 повторно валидирована в Python. **Без полного `.harness`, host env, абсолютных путей, других секретов, дополнительных control files.**
4. В `.harness/runtime/EXECUTION_BINDINGS/<RUN-ID>.yaml` только ограниченные metadata/ref и SHA-256 canonical product/control + snapshot/projection. Отсутствие root, corrupt output, stale refs/baseline, changed snapshot, metadata tamper блокируют replay. Второй вызов не дублирует root, запись или journal.
5. Обнаруженная pre-release regression: штатный `validate-project` считал новый binding несанкционированным. Решено **только** через существующий signed operation journal `EXECUTION_ROOT_PREPARED` после preflight `check_control_plane=PASS`; ранее подменённые control sources НЕ переподписываются. `archive.zip_directory()` исключает bindings из handoff/export; `PROJECT_LOCK`/accepted records и canonical files неизменны.
6. Точечная документация, mirrors `build/lib` + `docs/`, wheel, 21 новый regression/security test. Для всего остального код/семантика v0.5.1 не менялись.

## 3. Фактические тесты (логи прилагаются)

| Проверка | Фактическая команда / контекст | Результат |
|---|---|---|
| PH-051-04 targeted negative/positive | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_04_disposable_roots` | **21/21 PASS**, ~15 c |
| Existing regressions, семь обычных групп | `python -m unittest -v <exact modules in PH_051_04_LOGS/REGRESSION_MODULE_GROUPS.txt>` | **180 tests**, 1 `skipped`; 0 errors/failures |
| PH-F06 heavy group №2 | исходно `timeout 160s python -m unittest ...` дал `rc=124` (не assertion failure), повтор `timeout 480s python -m unittest -v tests.test_canonical_target tests.test_ph_051_02_executor_protocol tests.test_ph_f06_maturity_lifecycle` | **42/42 PASS**, 188.690 c, никакого unresolved timeout |
| Combined groups | 8 групп по final run, группа 2 — повтор с 480s | **222 tests run, 221 PASS + 1 SKIP** |
| All existing + new | 222 + 21 | **243 tests run, 242 PASS + 1 SKIP, 0 FAIL** |
| Wheel fresh build/install | `python -m pip wheel --no-deps --no-build-isolation .` + `pip install --force-reinstall --no-deps` | **PASS**, wheel rebuilt with PH-051-04 API |
| Installed CLI | `project-harness --version`; `project-harness doctor` | `0.5.1`, **PASS** |
| Installed API / Project Instance | Installed wheel: `demo --output-dir ... --keep-directory`, `validate-project` before, prepare root, replay, `validate-project` after | **PASS/PASS**, replay idempotent; phase signed |
| Documentation validation | `python tools/validate_documentation.py . --zip <new-documentation-zip> --json ...` | **36 checks PASS; 0 error, 0 warning** |
| ZIP/manifest | final archive content CRC and per-file SHA256 manifest (see final delivery metadata) | Проверяется при упаковке двух архивов |
| Physical rootless Podman sandbox security integration | Подходящий non-root Podman/image/cgroup стенд отсутствует; source previous PH-051-03 test skipped | **NOT RUN**; automatic mode remains disabled/NO-GO |

**Примечание к подсчёту:** семь быстрых групп = 180 тестов, одна тяжёлая группа = 42. Прежний групповой timeout (160s) не выдаётся за PASS: окончательная группа 2 прошла отдельно с более высоким лимитом. В group 3 `skipped` — один mandatory реальный Podman integration test без доступного Podman/image; rootless isolation нельзя объявлять доказанной.

## 4. Coverage PH-051-04

- Positive: source-product snapshot byte hash and distinct inodes, exact Task/JIT refs, seven-file bounded read-only projection, metadata storage, safe replay, valid `validate-project` before/after, immutable canonical product digest.
- Negative: source symlink directory/file escape, hardlink to outside secret, FIFO/special file safety without block, task/ref mismatch, symlinked runtime ancestor and source, stale/corrupt control/binding, altered snapshot/output, base drift, untrusted config, orphan root, unapproved control-plane writes cannot be re-sealed.
- Export: no `.harness/runtime/EXECUTION_BINDINGS` in handoff ZIP, no raw execution root or host absolute execution path in project lock; no canonical product apply.

## 5. Сохранённые ограничения / deferred

- **Не менялись**: Implementation Level sequence, canonical target, immutable accepted Project Input, acceptance reports/Runs, semantic Stage Gate evidence, strict approvals, Brownfield assessment, maintenance, active-stage planner and v0.5.0 crash-recovery logic.
- **Не добавлялись**: `execute-current`, `executor-doctor`, real Codex CLI, second adapter/provider, agent result ingestion, independent sandbox verification, secret outputs/logging, diff/apply, atomic apply, migration/orphan cleanup, Git/deployment. Эти обязательства принадлежат PH-051-05–12.
- Реальное `control:ro` обеспечивается Podman mount boundary PH-051-03 только после successful doctor; host chmod сам по себе не OS sandbox. Тесты unit/snapshot не считаются Podman security integration.
- Поставка остаётся **v0.5.1 WIP / NOT RELEASED**. **NO-GO** для активации автоматического исполнения до обязательной security integration / PH-051-12.

## 6. Артефакты

- Engine: `Project_Harness_Engine_v0.5.1_PH_051_04.zip` (новый implementation module, 21 test, wheel, mirrors, this report, changed-file inventory, logs).
- Documentation: `Project_Harness_Documentation_v0.5.1_PH_051_04.zip` (SHA256 `dcacfe81c2048e8e271540e5e55e3211be7bfe60ab760e6dd5d42a3a3df5fb05`; 36/36 validation).
- `PH_051_04_CHANGED_FILES.md` — exact diff от `(2)` входных архивов.
- Протоколы тестирования: `PH_051_04_LOGS/`; исходные отчёты PH-051-01/02/03 сохранены без перезаписи.
