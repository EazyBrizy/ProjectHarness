# PH-LW-04 — сохранённые инварианты и ограничения

**WIP, v0.5.1 — NO-GO / NOT RELEASED.** Реальные Windows/Waitress/browser acceptance и Podman security не были проведены.

1. PH-LW-01 — существующие 26 бизнес-команд и contract map без изменения; новая CLI `ui` только включает независимую HTTP оболочку, а не дополнительный governed kernel action.
2. PH-LW-02 — Win-native file/process safety и platform-gated тесты не переписаны и не объявлены проверенными на Windows.
3. PH-LW-03 — каталог, строго определённый набор операций, typed DTO, root/ownership/idempotency/stale fingerprint/recovery/worker locks. HTTP вызывает только public LocalWebService, а не редактирует `.harness` напрямую.
4. Accepted scope, уровни `PROTOTYPE → ALPHA → BETA → MVP → RELEASE`, Stage Gate, Brownfield, maintenance, immutability accepted input/Stage Acceptance Reports/completed Runs, exact revisions/baseline/evidence/strict approvals не изменены.
5. Manual GPT/Codex handoff остаётся default, все UI routes GET read-only, mutation requires explicit POST with session/Origin/CSRF/expected fingerprint/idempotency. Browser load/refresh/poll не выполняет автоматических Task/core actions.
6. Local UI не предоставляет `execute-current`, shell/FS gateway, network egress approval, provider API, Git/PR/deploy, second adapter/sandbox, remote listener или OS sandbox. Flask/Werkzeug development server fallback отсутствует.
7. Automatic mode PH-051-12 **NO-GO** по ещё не прошедшей реальной rootless Podman security matrix и отсутствующему позитивному governed per-Run egress; mock/unit зелёные тесты этого не снимают.
8. Нет подтверждения native Windows 11 x64 NTFS, firewall/LAN isolation, actual Waitress HTTP constraints/CSP, Edge browser, Windows package install. Скрипт `local_web/ci_ph_lw_04_windows.ps1` — непроведённая будущая проверка, не Windows evidence.
9. Версия Python package `0.5.1`, статус WIP, input historical artifacts не переименованы/перезаписаны; нормативные spec v0.5.0/v0.5.1 сохранены неизменными.
