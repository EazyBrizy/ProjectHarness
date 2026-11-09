# PH-LW-03 — сохранённые invariants и ограничение scope

**Дата:** 2026-11-02  
**Версия:** 0.5.1 WIP / NOT RELEASED

1. Canonical Stage State/accepted target, accepted project scope и последовательные уровни `PROTOTYPE → ALPHA → BETA → MVP → RELEASE` не меняются; active-stage planning только для текущей Stage.
2. Никаких изменений строгих формальных Stage/level-up/maintenance approvals, semantic Stage Gate evidence, Brownfield assessment, immutable accepted input/Stage Reports/Run history. Все существующие governance операции выполняются через исходные core APIs.
3. `MANUAL_HANDOFF` остаётся default. PH-LW-03 не добавляет запуск Codex с host, provider API, automatic executor, egress, HTTP routes, UI, Git, deploy, rootless substitute, VM, remote worker или произвольный CLI dispatcher.
4. Read-only `get_status`/polling не инициируют `next`, `check-intake`, восстановление Stage, команды проверки или какие-либо изменяющие проект diagnostics. Статус и Gate refs всегда читаются из canonical core.
5. Shared operation guard сериализует локальные public mutations с CLI на уровне OS; вложенные вызовы одного потока разрешены, Stage lock внутри. Никакого изменения Stage journaling/commit semantics.
6. `update-draft` ограничен строгими leaf fields, валидируется текущей схемой и записывается атомарно; approvals на semantic edit сбрасываются, но неподтверждённые решения не одобряются автоматически.
7. Operation journal вне проекта не является source of truth. Повторный idempotency key возвращает текущий receipt, stale fingerprint отклоняется; неоднозначный `next` после crash не признаётся committed без exact provenance и не переисполняется автоматически.
8. Windows 11 x64 NTFS native filesystem/ACL/race tests **NOT RUN**; rootless Podman/policy-bound egress также **NOT RUN / NO-GO**. Существующие PH-051-12 blockers и lineage PH-051-11 WIP остаются открытыми. Полный v0.5.1 release **NOT RELEASED**.
