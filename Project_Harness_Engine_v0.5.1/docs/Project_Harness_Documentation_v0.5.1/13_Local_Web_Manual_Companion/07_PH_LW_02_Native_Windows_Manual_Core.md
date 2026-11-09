# PH-LW-02 — Native Windows manual/preparation core: implementation boundary

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Этап реализации:** PH-LW-02, 2026-11-01  
**Статус:** Windows 11/NTFS **NOT RUN / WINDOWS_NOT_TESTED** до внешнего native run. **Web UI/installer:** ещё не реализованы. Основание — фактическая пара PH-LW-01 от PH-051-11 WIP, а не принятая PH-051-12; исторический full release остаётся **NO-GO**.

## Что изменено в manual core

- `project_harness` и `project_harness.cli` не загружают Linux-only automatic `apply`, sandbox и execution-root adapters во время импорта на Windows. У `apply.py` `fcntl` импортируется только в Linux automatic path. `executor_doctor()` и `execute_current()` на native Windows дают структурированный `BLOCKED / SANDBOX_UNAVAILABLE`, `isolation_verified=false` **до открытия проекта**, не выполняя Codex, shell, Podman или любые host-agent attempts. Это не positive approval для `LOCAL_AUTOMATIC`.
- Публичные manual/preparation API `start_intake`, `check_intake`, `prepare_handoff`, `validate_handoff`, `validate_project_directory`, `next_task`, `verify_current`, `complete_current` проверяют native root до работы с project tree. Поддержан обычный локальный absolute drive path (также относительный пользовательский путь, приведённый к абсолютному без Windows drive-relative интерпретации). Явные drive-relative `C:foo`, UNC, device namespace (`\\?\\`, `\\.\\`), reparse/junction roots и компоненты с NTFS ADS/reserved-device/trailing dot/space **отклоняются**. Пробелы и Unicode сохранены дословно, файл не переименовывается, immutable refs и content не «нормализуются».
- Intake/canonical tree с case-insensitive collisions или symlink/junction внутри поддерживаемого Windows root отклоняется до изменений. ZIP импорты проходят полный preflight (CRC, path/device/traversal, casefold collision) **до первого mkdir**, чтобы плохой член архива не создавал частично извлечённый проект.
- Stage write set проверяется на duplicate/case-colliding relative paths и known read-only targets до журнала. Единственная shared Stage transaction lock — OS-level flock (Unix) либо **`msvcrt.locking(..., LK_NBLCK, 1)`** (Windows), не no-op. Она находится в user-temp вне project/control/sandbox и удерживается до записи журнала, каждого replace, rollback/commit. Contention возвращает `VALIDATION_FAILED / STAGE_TRANSACTION_LOCKED`, не выполняет транзакцию. Journal recovery тоже захватывает lock при наличии pending состояния; terminal-only validation не создаёт lock-file в проекте.
- Python `atomic_write_text()` уже использует sibling temporary file, `flush + os.fsync(file)`, close handle перед same-volume `os.replace`, LF UTF-8. Access denied, busy/open file и read-only `os.replace` **не** трактуются как успех. В Stage transaction уже существующий журнал/backup реализует revalidation и deterministic all-old/all-new после fault; новые тесты проверяют отказ второго процесса и PermissionError между двумя canonical writes.

## Честная граница файловой прочности

На Windows возможен `fsync(file)` при закрытом перед `replace` handle, но Python не предлагает той же гарантии `fsync(directory)`, что Linux. `_fsync_directory` на native Windows помечает эту границу явно: **не обещается power-loss durability**. Проверяемая цель PH-LW-02 — recoverable **process-interruption** all-old/all-new при доступных backup/journal и OS replace semantics; crash with OS/power failure должен пройти **реальную NTFS fault matrix**, прежде чем утверждать более сильные свойства. Sharing violation даже во время rollback честно возвращает recovery error/blocked, а не ложный PASS. Другой Windows-user с доступом к temp не входит в threat model однопользовательской установки; ACL/security проверяются при native Windows тестах.

**Ограничение ручного `verify --allow-command-execution`:** явно согласованная команда проверок проекта может требовать отдельно установленную toolchain/SDK. Harness её не устанавливает автоматически, не подставляет собственный frozen `Harness.exe` вместо Python/SDK продукта и не запускает произвольный shell fallback; без указанного флага команда не выполняется.

## Reproduction

В Engine source root на Linux:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_lw_02_windows_core
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python tests/run_tests.py
python project-harness.py doctor
```

На **настоящем Windows 11 x64 + NTFS**, с обычным аккаунтом и Python test toolchain (не требуются для будущего frozen запуска):

```powershell
pwsh -NoProfile -File .\local_web\ci_ph_lw_02_windows.ps1 -DocumentationZip C:\path\Project_Harness_Documentation_v0.5.1_PH_LW_02.zip
```

Скрипт явно проверяет OS/NTFS, публичный import graph, фактический manual Greenfield `start_intake → check_intake → prepare_handoff → validate_handoff → validate_project_directory → next_task → verify_current → complete_current`, shared lock второй OS process, native read-only/open-handle replacement, полный regression suite, doctor и Docs ZIP validator. Его наличие в Linux release **не означает, что Windows тест выполнен**. При Windows-only failures фиксировать `FAIL`, не массовые `skip`. Реальные browser/launcher/Web/E2E появятся только в следующих PH-LW пакетах.

**Прежние открытые blockers v0.5.1:** полноценная Podman security isolation acceptance и положительный governed per-Run egress. Ни один из них не закрыт PH-LW-02. Accepted Stage State/Reports/Run history, semantic Gate, Brownfield/maintenance и normative v0.5.0/v0.5.1 не менялись.
