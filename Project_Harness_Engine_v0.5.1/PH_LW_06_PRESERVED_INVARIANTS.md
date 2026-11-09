# PH-LW-06 — сохранённые инварианты

Дата: 2026-11-07. Проверки и ограничения — в [фактическом отчёте](PH_LW_06_TEST_REPORT.md).

| Инвариант | Сохранение и проверка |
|---|---|
| Browser → service/guard → public Engine APIs → canonical state | HTTP/UI не пишут `.harness`, не назначают Task/Run/Stage/Gate states. Draft commit вызывает public API, check-intake — отдельную guarded mutation. Private exchange не является core evidence |
| GET/polling только read | Byte snapshots для interview/review/download/HTTP reads; GET не сохраняет reply, не восстанавливает intent и не запускает operation |
| Manual default, automatic NO-GO | Только exact MANUAL_HANDOFF/network NONE; forged execution/paths/actor/approvals rejected. Provider API, host fallback, LAN, shell gateway, Podman/egress activation не добавлены |
| Documentation/outcome/target перед architecture | Typed questions происходят из ядра; imported sources и replies — данные. UNKNOWN/material gaps остаются открытыми, UNSURE — WAITING_DECISION. Фикстура не выдаётся за semantic analysis |
| Exact refs/digests и source provenance | Envelope проверяет project/export/input/source и core fingerprint; stale/wrong/forged refs — no-write. Claims имеют per-field value digests и всегда unverified provenance |
| Separate approvals, accepted history | Reply содержит только pending records. Local approvals сохраняются по unchanged binding, material change даёт invalidation receipt. Никаких UI approvals PH-LW-07 или Stage acceptance; прежние core governance/history suites выполняются отдельно |
| Recovery/replay/concurrency | Общий OS lock; stale double preview не overwrite. Checksummed intent before/after; exact replay без дубля; cancel до commit. Child process exit и чужая CLI mutation проверяются без перезаписи чужих bytes |
| Brownfield read-only | Exchange ограничен managed Greenfield. Прежние service/Windows suites проверяют refusal/read-only Brownfield; анализа/записи в Brownfield не добавлено |
| Последовательность уровней и active-stage scope | PROTOTYPE→ALPHA→BETA→MVP→RELEASE не менялась; target не создаёт accepted scope. Выбранный target не заменяется GPT; Task/JIT/stage planning contracts не расширены |
| Local-only external transfer | Явные inventory/classification/consent/copy/download, no external fetch/CDN/telemetry. Scripts/HTML/docs/AGENTS отображаются как текст; JSON не выполняется |
| Источники и история | `_inputs`, normative specs, r2 prompts, прежние планы/архивы/reports/logs сохранены. Новое правило ZIP пользователя явно отмечено, архивный prompt не переписан |

Фактический PASS локального scope не закрывает `LOCAL_WEB_MANUAL` до PH-LW-12, `AUTOMATIC_EXECUTOR` или полную v0.5.1. Windows skips, Linux/automatic FAIL и mandatory NOT RUN остаются отдельными незакрытыми gates. Не заявляется power-loss, clean-machine installer или реальное общение с GPT.
