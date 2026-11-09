# PH-051-01 — contract baseline v0.5.1 WIP (не release)

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Статус:** IMPLEMENTED CONTRACT SLICE / AUTOMATIC EXECUTION DISABLED.

## Граница пакета

Контрактный пакет v0.5.1: схемы, реестры, `PROJECT_INPUT@4` и metadata `PROJECT_LOCK`.
Это не реализация Executor Adapter, Podman Runner, `executor-doctor` или `execute-current`.
Публичный manual handoff, Stage Gate, Brownfield и same-level maintenance остаются v0.5.0 semantics.

## Фактические версии

| Contract | Было v0.5.0 | Теперь PH-051-01 |
|---|---|---|
| Harness `SCHEMA_VERSION` | `6` | `7` |
| `PROJECT_INPUT` | `@3` | `@4` |
| `REG-ID-PREFIXES` | `2` | `3`: отдельный `SBX` |
| `REG-LIFECYCLE-STATUSES` | `5` | `6`: `sandbox_profile` |
| `REG-CONTRACT-CATALOG` | `5` | **`6`**, не `5` повторно |

**Normative conflict / compatibility decision (PH-051-01).** §19.1 спецификации v0.5.1
указывает переход Contract Catalog `4 → 5`, однако исходные реально принятые ZIP v0.5.0
содержат **`REG-CONTRACT-CATALOG@5`**. Для сохранения уже закреплённых revision
выбран следующий свободный номер `5 → 6` — совместимая коррекция нумерации
без downgrade/overwrite. Сам текст нормативной спецификации не изменён.
Все новые locks закрепляют `contracts=6` с exact SHA-256; старые v0.5.0
locks сохраняют `contracts=5` и проверяются по собственным registry copies/digests.
Это зафиксированное implementation decision, а не фиктивное выполнение буквального `4 → 5`.

## Новые схемы / records

| Schema | Entity / storage |
|---|---|
| `executor_profile.schema.json` | существующий `agent_adapter_profile` / `ADP`, `.harness/config/ADAPTERS/{id}@{revision}.yaml` |
| `sandbox_profile.schema.json` | `sandbox_profile` / `SBX`, `.harness/config/SANDBOXES/{id}@{revision}.yaml` |
| `execution_result.schema.json` | immutable `ART`, `.harness/runtime/EXECUTION_RESULTS/{id}.yaml` |
| `apply_evidence.schema.json` | immutable `EVD`, `.harness/evidence/{id}.yaml` |

Все новые schemas запрещают неизвестные поля; profile schemas разрешают только
`CODEX_CLI_LOCAL`, `ROOTLESS_PODMAN`, digest-pinned image,
`READ_ONLY` root filesystem, non-root, dropped privileges и заданные mounts.
Это пока **проверяемый декларативный контракт**, не доказательство OS isolation.
`execution_result` и `apply_evidence` не создаются, пока нет runtime implementation.

## `PROJECT_INPUT` и safe default

```yaml
execution:
  mode: MANUAL_HANDOFF
  adapter_profile_ref: null
  sandbox_profile_ref: null
  network_mode: NONE
  completion_policy: EXPLICIT_AFTER_VERIFICATION
```

`LOCAL_AUTOMATIC` — только explicit opt-in; требует revisioned `ADP`/`SBX`
refs и реальных ACTIVE project-local records (без prefix glob/выбора latest).
`exact_execution_profile_bindings(root, policy)` проверяет точный id, revision,
record schema, status, связку adapter→sandbox, допустимость network, возвращает
refs и SHA-256 records, ничего не исполняя. Даже валидная пара профилей в
PH-051-01 **не активирует** execution: `prepare` fail-closed возвращает
`AUTOMATIC_EXECUTOR_NOT_IMPLEMENTED` до реализации следующих packages.
`EXPLICIT_APPROVED_EGRESS` не является разрешением Run network egress;
per-Run approval и doctor появятся позже. Raw credentials/argv/mounts
запрещены в `PROJECT_INPUT`. `AUTO_AFTER_PASS` не заменяет independent verification.

`start-intake` и `check-intake` мигрируют v3 input в v4 in memory / provisional
workspace и добавляют только безопасную ручную политику. Исторический
`.harness/state/PROJECT_INPUT_ACCEPTED.yaml` принятого проекта и completed Runs
**не переписываются**. Новый manual handoff выпускается на schema7 с
`execution_profile_bindings: {adapter: {ref: null, digest: null}, sandbox: {ref: null, digest: null}}`,
а legacy v0.5.0 lock остаётся read-compatible с exact registry digest validation.
Операция полноценной project migration `MIG-ENGINE-0.5.0-TO-0.5.1`
для persisted root реализована в PH-051-10; она отдельно сохраняет
исторические accepted records и ставит `MANUAL_HANDOFF`.
См. [PH-051-10](13_Migration_Cleanup_Orphan_Recovery_v0.5.1_WIP.md).

## Проверки / запреты

- Контрактные схемы и отрицательные тесты: unknown fields, missing exact refs,
  altered revision, mutable tag, DOCKER backend, suspended profile,
  secret data и forbidden network.
- Manual `prepare → validate-project` работает без Podman, сохраняет Stage planner
  и неизменяемые history.
- Нет `executor-doctor`, `execute-current`, host CLI execution или auto fallback.
- Не добавлены дополнительные provider API, Git/PR/deploy, VM или unrestricted mounts.

Окончательная security acceptance и release GO возможны только после PH-051-12.
