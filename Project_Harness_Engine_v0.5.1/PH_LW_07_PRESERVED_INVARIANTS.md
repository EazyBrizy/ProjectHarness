# PH-LW-07 — сохранённые инварианты

Дата: 2026-11-07. Scope: отдельные согласования provisional intake; v0.5.1 WIP / NOT RELEASED.

- Browser → LocalWebService / operation guard → public approval/draft/intake APIs. HTTP/UI не пишет `.harness`, не назначает Task/Run/Stage/Gate states.
- `PROJECT_INPUT@4`, schemas и registries не расширены. Intake использует только `approved`, `actor`, `approved_at`, `notes`; versioned companion receipts находятся отдельно. Stage DEC/ACT contracts/tests неизменны.
- `approvals_for_mode()` определяет четыре/пять решений и baseline order. Нет auto-approval, «одобрить всё», model consent или запуска команд из imported data.
- Subject validation, exact input/source revisions, fingerprints и receipt digests проверяются до mutation. Server timestamp и явно заданный local actor не принимаются из GPT. Receipt — audit binding, не подпись/identity proof.
- Idempotency и OS lock сохраняют одно решение при retry/concurrency. Durable intent и before/after reconciliation не повторяют commit после crash, ambiguous recovery не перезаписывает чужие bytes.
- Source/material edits сбрасывают только current draft approvals; rework сбрасывает выбранный и зависимые последующие subjects, сохраняя earlier confirmations. Immutable committed receipts и accepted Project history не редактируются.
- GET/polling только читает; check_intake/projections обновляются после явных mutations. Новые routes защищены session/CSRF/exact Host/Origin/port, содержимое выводится через textContent, без внешних fetch/CDN/telemetry.
- Brownfield/Hybrid repository читается без команд; live baseline drift блокирует согласование. Browser не принимает filesystem paths. Новый repository import/setup этап не добавлен.
- `PROTOTYPE → ALPHA → BETA → MVP → RELEASE`, accepted scope, target, separate approvals, evidence semantics и active-Stage-only Task/JIT не меняются.
- MANUAL_HANDOFF/network NONE — default и единственный flow новых approvals. Automatic executor, host Codex fallback, provider API, LAN listener, Podman/egress и generic shell/filesystem gateway не включены.
- Final handoff action возвращает `PREPARATION_PENDING_PH_LW_08`. Project Instance не создаётся; HTTP prepare отключён до отдельного этапа. PH-LW-08 не выполнялся.
- Старые inputs/specs/prompts/plans/reports/archives сохранены; build/lib/dist/egg-info сгенерированы из src; docs standalone/embedded побайтово равны. Engine/Documentation ZIP не создавались.

Фактические результаты — [отчёт](PH_LW_07_TEST_REPORT.md), точные invariant hashes — [внешняя аттестация](../_workspace/PH_LW_07/FINAL_WORKING_TREE_VERIFICATION.json). Полная regression matrix сохраняет прежние mixed Linux/automatic FAIL/SKIP; они не повышены до PASS. `LOCAL_WEB_MANUAL`, `AUTOMATIC_EXECUTOR` и полная v0.5.1 остаются NO-GO.
