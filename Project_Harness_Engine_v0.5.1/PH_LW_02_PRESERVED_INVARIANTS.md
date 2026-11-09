# PH-LW-02 — сохранённые инварианты и границы

**Дата:** 2026-11-01  
**Версия:** 0.5.1-WIP / PH-051-11-derived / PH-LW-01 → PH-LW-02  
**Решение:** Windows native acceptance `WINDOWS_NOT_TESTED`; full v0.5.1 `NO-GO / NOT RELEASED`.

- Canonical Implementation Levels: `PROTOTYPE → ALPHA → BETA → MVP → RELEASE`, без перескоков. Current target находится в Stage State; historical accepted input/Stage Reports/Run history неизменны.
- Existing strict schema/contracts, immutable refs, Brownfield read-only assessment, same-level maintenance, semantic Gate evidence, Stage approvals and exact-baseline integrity не упрощены. Прежние нормативные v0.5.0/v0.5.1 и registry versions НЕ менялись.
- Windows manual/import path не импортирует Linux-only automatic execution stack. `executor-doctor` и `execute-current` на native Windows отказывают `BLOCKED / SANDBOX_UNAVAILABLE` с `isolation_verified=false`: НЕТ запуска Codex или других агентов на host и НЕТ shell fallback. Linux automatic modules/lifecycle проверяются регрессиями, но реальная Podman security acceptance остаётся открытой.
- Linux Stage transactions сохраняют настоящий `flock`; Windows получает настоящий kernel byte-range lock через `msvcrt.locking`, без no-op, с отказом при contention. Stage journal/backup/recovery и read-only preflight сохраняются. Вне доказанной native Windows матрицы не утверждается ОС/power-loss durability.
- Source archives, product scopes and control records не нормализуются или переписываются ради Windows. Unsupported UNC/device/drive-relative/junction/unsafe names/case collisions отвергаются, а не автоматически переименовываются. ZIP paths/CRC preflight выполняется до extraction.
- `verify_current(allow_command_execution=True)` — существующий explicit manual verification; продуктовые SDK/инструменты не устанавливаются движком и не заменяются frozen launcher. Никакие Web UI/Flask routes, Windows installer, background server, provider API, Git/PR/deployment и новый sandbox не добавлены.
- Историческое provenance-ограничение PH-LW-01 сохраняется: actual baseline PH-051-11 WIP, promised PH-051-12 input/report отсутствуют. PH-LW-02 не объявляет окончательную v0.5.1 GO.

**Следующий обязательный шаг:** запустить `local_web/ci_ph_lw_02_windows.ps1` на настоящем Windows 11 x64 NTFS; при любых его ошибках статус Windows остаётся FAIL/NO-GO. На Linux есть только локальные regression/import contracts и POSIX lock tests.
