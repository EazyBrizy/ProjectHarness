# PH-LW-04/05 Windows retest — сохранённые инварианты

Дата: 2026-11-07. Версия: 0.5.1 WIP / NOT RELEASED.

- Normative v0.5.0/v0.5.1 specs и все исходные планы/prompts сохранены; приложенный prompt не назначает следующие этапы.
- PH-051-11 lineage и прежний Podman/positive per-Run egress NO-GO не изменены. Manual handoff остаётся default; automatic executor и host Codex fallback не включены.
- Accepted scope/target, последовательные уровни, exact refs/digests, отдельные approvals, semantic evidence, immutable history, Brownfield read-only и active-Stage JIT не изменены.
- HTTP → service/operation guard → public core API. Нет прямой canonical мутации из UI/HTTP, generic filesystem/shell gateway, LAN listener, provider API или внешних fetch.
- GET/poll/preview/refresh read-only; mutations защищены session, exact Origin/Host/port, CSRF, DTO и revision/replay. Новые операции перепроверяются worker под OS guard.
- Uploads и содержащиеся AGENTS/инструкции — данные, не control-plane authority. Preview textContent; исходные пользовательские файлы не меняются.
- Runtime dependency pins сохранены; инструменты разработчика отделены. System PATH/registry/firewall/Developer Mode/execution policy не менялись.
- Все 699 исторических PH report/log файлов сверены побайтово с исходным Engine. Старые NOT RUN/NO-GO не превращены задним числом в PASS.
- Новые ZIP полные; source/build/wheel/resources/docs согласованы. Raw failures/skips сохранены; final evidence указывает точные повторные runs.
- PH-LW-06, installer и полный release gate не выполнялись. Остаточные Windows legacy/automatic/migration ошибки открыто перечислены в [отчёте](PH_LW_04_05_WINDOWS_ACCEPTANCE_TEST_REPORT.md).
