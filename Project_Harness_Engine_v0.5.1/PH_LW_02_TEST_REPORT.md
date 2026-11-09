# PH-LW-02 — implementation и test report

**Дата:** 2026-11-01  
**Engine:** v0.5.1 WIP, текущие ZIP PH-LW-01 → PH-LW-02  
**Состояние:** исходники обновлены и Linux checks выполнены; **WINDOWS_NOT_TESTED**. Полный выпуск v0.5.1 — **NO-GO / NOT RELEASED**.

## 1. Preflight provenance и неизменная нормативная база

| Материал | SHA-256 | Проверка |
|---|---|---|
| Входной Engine `Project_Harness_Engine_v0.5.1_PH_LW_01.zip` | `bf2c01ef638e2ad3f41145288d44ba3deede73e9a4271211e2530402f2bee124` | ZIP CRC и 829 manifest file hashes PASS |
| Входная Documentation `Project_Harness_Documentation_v0.5.1_PH_LW_01.zip` | `fc58170c80d6b64d6ecbaa5a443faa7aea3646a804ca409c1e2ba7cce47ff3da` | ZIP CRC и 139 manifest file hashes PASS |
| Неизменная нормативная v0.5.1 (source doc) | `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e` | READ ONLY; unchanged |
| Неизменная нормативная v0.5.0 (source doc) | `ca487d3e978af116418a597b5d05cd890d11e2e93855c9f7a312e21f083dd16f` | READ ONLY; unchanged |

Actual PH-LW-01 — WIP-потомок предоставленного PH-051-11, а не невыданный PH-051-12 source snapshot. Отсутствие точной PH-051-12 базы/отчёта уже зафиксировано в `PH_LW_01_TEST_REPORT.md`. Это ограничение **не закрыто и не скрыто**. Никакие accepted input, Stage Reports, history или normative specs не переписывались.

## 2. Реализованная ограниченная область

1. **Native Windows manual import graph.** `runtime.py` не импортирует auto-only `apply`, executor/sandbox/execution-roots на Windows; `apply.py` загружает `fcntl` только по Linux automatic apply path. `import project_harness`, `cli`, intake, preparation/validation/Stage APIs доступны без обязательного Linux module import. Native Windows `executor_doctor`/`execute_current` возвращают structured `BLOCKED`, `SANDBOX_UNAVAILABLE`, `isolation_verified=false` без host subprocess; не добавлено автоматически включаемых backends.
2. **Root/relative path safety.** В `platform_fs.py` создан маленький platform boundary с запретом UNC/device/drive-relative, NTFS device/ADS/trailing-invalid forms, symlink/junction roots, casefold-colliding trees и read-only Stage targets. Unicode/пробелы сохраняются без изменения их bytes. `intake`, `compiler`, `archive`, `validation`, `runtime`, `util`, `stage_transactions` используют проверку до соответствующей операции. `safety.py` валидирует ZIP CRC, unsafe names, links и case aliases до extraction; intake проверяет source/repository ZIP до создания workspace.
3. **OS lock и Stage recovery.** `stage_project_lock` использует POSIX `flock`/Windows `msvcrt.locking(LK_NBLCK)`, а не глобальный in-memory lock или no-op. Stage writer и pending journal recovery защищены lock. Stage writes выполняют preflight перед journal, с сохранением прежнего rollback/recovery и фиксацией ошибки replace; на Windows `_fsync_directory` не заявляет несуществующую directory-fsync гарантию. Power-loss crash durability Windows не сертифицирована.
4. **Документация/проверки и упаковка.** Windows-only CI script, targeted negative tests, sync `src` ↔ `build/lib`, rebuilt wheel, updated README/MANUAL_INSTALL/embedded+standalone docs. Никаких Web routes, Flask/UI, Windows installer и нового sandbox/automatic execution не добавлено.

## 3. Фактическая test matrix

**Среда фактического запуска:** Linux x86_64, Python 3.13.5, POSIX filesystem; **НЕ** Windows 11/NTFS. Все абсолютные числа ниже относятся только к этой среде.

| Проверка | Лог/артефакт | Итог |
|---|---|---|
| Full regression, 32 unittest modules по final source | `PH_LW_02_LOGS/FULL_REGRESSION_FINAL.log`, `REGRESSION_MATRIX.json`, `REGRESSION_MODULES/*.log` | **PASS: 365 tests, 4 SKIP, 0 FAIL**, включая Stage/assessment/evidence/maintenance/Brownfield и automatic unit tests; Windows-specific и недоступные real Podman cases не засчитаны |
| Targeted PH-LW-02 import/paths/ZIP/lock/rollback/manual Greenfield | `PH_LW_02_LOGS/TARGETED_WINDOWS_CORE_LINUX.log`, `tests/test_ph_lw_02_windows_core.py` | **PASS: 14 tests, 2 Windows-only SKIP**, cross-process POSIX lock и fault rollback PASS |
| Manual public API Greenfield `start_intake → check_intake → prepare_handoff → validate_handoff → validate_project_directory → next_task → verify_current → complete_current` | `test_11_manual_greenfield_full_api_through_complete` | **PASS на Linux**: final project validate-project PASS, task verification PASS, completion accepted; НЕ нативная Windows приёмка |
| No `fcntl` import through full manual package graph and auto fail-closed | targeted `test_01`, `test_02` | **PASS на Linux с artificial `fcntl` unavailability**; actual Windows import NOT RUN |
| Unsafe/outside path, case collision, unsafe ZIP pre-write, busy/read-only replacement simulation | targeted `test_03..08` и `test_06b` | **PASS на Linux**, Windows NTFS attributes/sharing NOT RUN |
| Busy second real OS process and injected interrupted second Stage replace | targeted `test_09`, `test_10` | **PASS на Linux**, real Windows kernel-lock NTFS NOT RUN |
| Docs validator source + standalone | `PH_LW_02_LOGS/DOCUMENTATION_VALIDATION.json` | **PASS**, 36 checks; before ZIP packaging 1 expected warning `--zip not supplied` |
| Wheel build/install, installed `--version`, installed `doctor` | `PH_LW_02_LOGS/WHEEL_BUILD.log`, `WHEEL_INSTALL.log`, `WHEEL_CLI.log` | **PASS on Linux** (`project-harness-engine==0.5.1`, doctor PASS); Windows installed/frozen NOT RUN |
| Native Windows 11 x64 NTFS shared-lock, replace/open handles, readonly path, manual end-to-end | `local_web/ci_ph_lw_02_windows.ps1` prepared, `test_12`,`test_13` | **NOT RUN / WINDOWS_NOT_TESTED**, no Windows stand; presence of CI script is not test evidence |
| Rootless Podman full isolation and governed positive per-Run egress | Previously open PH-051-12 acceptance | **NOT RUN / NO-GO**, no simulated PASS |
| Local browser and offline native Windows installer | Outside PH-LW-02 scope | **NOT IMPLEMENTED / NOT RUN** |

The **initial** modular run showed 3 CLI-test module FAILs because `zipfile.extractall()` did not restore executable mode of the existing `bin/project-harness` (archived mode `0o100755`); this was **test extraction setup**, not fixed by changing core CLI. After restoring mode from the source ZIP, explicit reruns of all 3 modules passed (`PH_LW_02_LOGS/RERUN_EXEC_MODE_FAILURES/`). Initial logs/JSON retained under `REGRESSION_MODULES_INITIAL/` and `REGRESSION_MATRIX_INITIAL.json` for audit; final full rerun uses the correct executable bit and **all modules**. Earlier source `doctor` emitted FAIL before the engine `MANIFEST.sha256` was rebuilt, and is retained as preliminary evidence only. Final source doctor/ZIP verification and SHA-256 are recorded separately after manifest regeneration.

## 4. Непроверенное и решение

- `WINDOWS_NOT_TESTED`: platform-only `test_12/test_13`, Windows C: absolute roots, UNC/device rejection, ACL/NTFS casefold and reparse points, exclusive Win32 lock, sharing violation on `os.replace`, mounted read-only flags и process/crash recovery должны быть проверены на реальном Windows 11 x64 NTFS. **Linux simulation/mock = не PASS Windows.**
- Windows process interruption recovery проверяется отдельно, power-loss durability не заявлена (нет POSIX-style directory fsync), host full crash нужен отдельный native fault test. Если OS sharing denies even rollback, ошибка/блокировка должны остаться видимыми.
- Full PH-051-12 release remains **NO-GO**: no actual rootless Podman security acceptance, no positive governed per-Run egress, а также provenance PH-051-12 snapshot не предоставлен. PH-LW-02 не исправляет/обходит эти outside-scope blockers.
- `PH_LW_02_CHANGED_FILES.md`, `PH_LW_02_PRESERVED_INVARIANTS.md` и `PH_LW_02_LOGS/` входят в Engine ZIP; standalone Documentation ZIP содержит новый технический runbook. Финальные Archive CRC/manifests проверяются на exact files до выдачи.

**Verdict:** PH-LW-02 implemented for review with Linux-tested manual core and fail-closed Windows automatic boundary. **Native Windows acceptance BLOCKED (`WINDOWS_NOT_TESTED`); neither local Web nor full v0.5.1 release ready.**
