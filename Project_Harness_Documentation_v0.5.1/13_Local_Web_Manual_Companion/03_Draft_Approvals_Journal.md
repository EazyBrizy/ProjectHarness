# Внешний GPT draft, согласования и разделение состояний

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Этап подготовки:** PH-LW-01, 2026-11-01  
**Статус:** CONTRACT DESIGN / NOT IMPLEMENTED / NATIVE WINDOWS NOT RUN

## Схемы и ownership

- Core: `SCHEMA-PROJECT-PREPARATION-INPUT@4` в `src/project_harness/resources/schemas/project_input.schema.json`; не копировать в новую UI-схему и не менять core approval semantics. Core source of truth: `.harness` Stage State/Run/Gate/evidence/accepted input и valid intake workspace; provenance immutable.
- Draft-only exchange: `resources/local_web/gpt_exchange_reply_v1.schema.json`. Body `kind=LOCAL_WEB_GPT_DRAFT_ONLY`, `envelope_version=1`, `exchange_id`, `export_revision`, `export_sha256`, `project_ref`, `source_revision`, `source_inventory_sha256`, `input_revision`, `project_input_draft` (ref на **исходную core schema**, проверяется отдельно строго), `questions`, `uncertainties`. Внешний GPT **никогда не создаёт** approval, formal DEC/ACT, capabilities или owner/path authorization.
- UI operation receipt: `resources/local_web/operation_receipt_v1.schema.json`, `kind=LOCAL_WEB_OPERATION_RECEIPT`, отдельный `receipt_version=1`, `operation_id`, `project_ref`, `action_id`, `idempotency_key`, `request_sha256`, `expected_core_fingerprint`, `core_outcome`, `core_ref`, `created_at`, `notes`. Это local journal DTO и не новый `RUN`, `ACT`, `DEC` или Stage status.
- Derived view model: recalculated **read-only** projection of validated core records plus ephemeral UI progress; never authoritative for `PASS`, `COMPLETE`, `ACCEPTED`, maturity level or target. Journal records in separate app-data, not `.harness`.

## Приём внешнего draft, без неявного approval

Export содержит exact snapshot of source and user input. Перед экспортом оператор видит source names/sensitivity, подтверждает manual transfer; приложение **не** вызывает GPT provider и не делает outbound network. Import должен строго сравнить envelope kind/version, exact exchange UUID, project/owner, revision/digest of original exported body, source inventory, input revision; reject duplicate IDs/mismatched binding/unknown fields. Size/type/JSON schema validated before accepting draft.

Из `project_input_draft` запрещено переносить чужие `approved:true`, `actor`, `approved_at`, личные пути/секреты, `execution.mode=LOCAL_AUTOMATIC` или `EXPLICIT_APPROVED_EGRESS`, Stage/Gate refs, неожиданные capability flags. При импорте никаких auto-mutations: candidate только preview → user review → separately versioned provisional apply through core validated intake route. Даже schema-valid материал может быть семантически ложным — человеческое подтверждение обязательно. При изменении source/answer/target review fingerprint старые approvals становятся stale, а история не переписывается.

## Intake approval ≠ Stage approval

`project_input.py` фактически требует четыре независимых Greenfield key: `project_definition`, `architecture_baseline`, `technology_baseline`, `codex_handoff`; Brownfield/Hybrid содержит дополнительно `brownfield_baseline`. Каждый — `{approved,actor,approved_at,notes}` по исходной schema. Перед подписью показать точную версию / существенные поля и один отдельный confirmation gesture; `actor` — локальный formal ref, но не подтверждённая криптографическая личность.

Stage acceptance использует отдельную строгую `stage_approval.schema.json` с DEC/ACT exact-bound refs, последним baseline, Gate subjects/evidence; Level-up — отдельный formal approval route. Нельзя перенести 4/5 intake approvals как Stage Gate decision или принять модельный `approved:true` за любой из этих артефактов. Повтор ревизии/idempotency, если изменён product baseline или Stage State, требует stale reject без mutation.

## Mutations, receipt и восстановление

Каждому POST присваивается idempotency key, связанный с canonical JSON request SHA256, project ID и expected core revision. Один key с другим body — CONFLICT. Отдельное persistence before call (`PENDING`), после фактического core commit (`CONFIRMED_COMMITTED` с `core_ref`) либо core reject (`CONFIRMED_REJECTED`). При падении после commit, но до receipt, это `UNKNOWN_RECONCILE`, не rollback и не повтор. Публичные core read/status/Stage transaction journal используются для reconcile. Verify, external commands и non-idempotent `next` не повторяются автоматически без exact check.

Ни один UI-receipt не считается независимым evidence для Stage Gate. Stale frontend cache никогда не заменяет latest canonical state. Точная атомарность, DB locks и stage journal integration — реализация PH-LW-03, не предмет этого этапа.
