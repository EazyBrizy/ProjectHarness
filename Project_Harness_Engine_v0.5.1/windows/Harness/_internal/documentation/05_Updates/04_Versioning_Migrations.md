# Версионирование Harness и migrations

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION BASELINE

## 1. Independent version domains

```text
Harness Distribution
Canonical Schema
Project Model
Registries
Prompt Modules/Specs
Skills
Project Profiles
Agent and Tool Adapters
Policies/Evaluators
Evaluation Suites
Human-view Generator
```

## 2. Exact Project Lock

`PROJECT_LOCK.yaml` использует canonical registry names без aliases и фиксирует version и SHA-256 digest каждого registry.

```text
project_lock:
  harness_distribution: 0.4.1
  schema_version: 5
  registry_versions:
    id_prefixes: 1
    project_profiles: 1
    statuses: 4
    request_routing: 2
    capabilities: 1
    contracts: 3
  registry_digests:
    id_prefixes: sha256:<digest>
    project_profiles: sha256:<digest>
    statuses: sha256:<digest>
    request_routing: sha256:<digest>
    capabilities: sha256:<digest>
    contracts: sha256:<digest>
  profile_refs:
    - PRF-CLI-TOOL@1
  adapter_refs:
    - ADP-CODEX@1
  skill_refs:
    - SKL-UNIVERSAL-IMPLEMENT@3
  prompt_spec_refs:
    - PSP-CODEX-TASK@1
  migrations_applied:
    - MIG-DOC-031-040
    - MIG-ENGINE-0.4.0-TO-0.4.1
```

`ADP` обозначает Agent Adapter Profile. Repository/Git adapters не маскируются под `ADP-GIT` без отдельного зарегистрированного contract/prefix.

## 3. SemVer

MAJOR означает несовместимое изменение contracts или semantics. MINOR добавляет backward-compatible entity/capability. PATCH исправляет совместимый defect. Activation всё равно требует validation/evaluation, а существующий Project Instance не обновляется молча.

## 4. Migration contract

Migration фиксирует:

```text
from/to versions
preconditions
deterministic transform
registry and schema mappings
validation
snapshot
reversibility or compensation
affected generated artifacts
recompile/evaluation requirements
recovery route
```

Исторические immutable Runs и Evidence не переписываются. Migration создаёт новую интерпретирующую view или successor revision.

## 5. Compatibility check

Engine проверяет readable schema range, registry names/versions/digests, profile/adapter/Prompt IR compatibility, ACTIVE skill digests и required migrations. Любое несовпадение даёт точный Blocker до compilation/execution.

## 6. v0.3.1 → v0.4.0

Migration:

- разделяет external `START_INTAKE` и project bootstrap;
- добавляет canonical Session и Architecture Baseline contracts;
- нормализует Project Lock по шести registry names;
- определяет skill registry как generated index;
- вводит Browser GPT preparation и Codex Handoff;
- разделяет immutable handoff validation и mutable project validation;
- фиксирует Core/hardening release slices.

Полный порядок: [`../MIGRATION_FROM_v0.3.1.md`](../MIGRATION_FROM_v0.3.1.md).

## 7. v0.4.0 → v0.4.1

Direct project migration is explicit and preserves immutable history. Preconditions are exact engine v0.4.0/schema 4, no active Run and compatibility validation PASS. Greenfield uses the stored accepted input; Brownfield/Hybrid additionally requires an explicit `brownfield_baseline` approval in `PROJECT_INPUT@2`.

Legacy Task/Run files are not rewritten. A current legacy Task with `COMPLETED` receives a successor revision `DONE`; historical Run `COMPLETED` is compatibility-mapped to `SUCCEEDED`. Brownfield acceptance creates a successor baseline revision and immutable Decision. The original handoff manifest remains the initial baseline; mutable state is checked by `validate-project`.

Full procedure: [`../MIGRATION_FROM_v0.4.0.md`](../MIGRATION_FROM_v0.4.0.md).

## 10. Direct migration v0.4.1 → v0.5.0

Direct source: engine `0.4.1`, schema `5`, `PROJECT_INPUT@2`. Target: engine `0.5.0`, schema `6`, `PROJECT_INPUT@3`, migration `MIG-ENGINE-0.4.1-TO-0.5.0`.

Migration требует explicit target, сохраняет immutable history, stage-aware replans an unexecuted route и создаёт conservative assessment/review route для completed history. Source directory заменяется только после full validation isolated copy; повторный вызов возвращает `NO_ACTION` после проверки current state. Полная инструкция: [`../MIGRATION_FROM_v0.4.1.md`](../MIGRATION_FROM_v0.4.1.md).

## 11. v0.5.0 → v0.5.1 contract preparation (PH-051-01, WIP)

A v0.5.0 `PROJECT_INPUT@3` may be read and conservatively migrated into
`PROJECT_INPUT@4` for a **new** preparation, adding exactly the manual-only
`execution` policy. Existing accepted immutable `PROJECT_INPUT`, Stage reports
and Runs must not be rewritten. New locks are schema `7` and pin registries
`3/6/6` (SBX/statuses/contracts); the historical `REG-CONTRACT-CATALOG@5`
forces catalog revision **6** rather than overwriting 5.

PH-051-01 introduced only in-memory v3→v4 compatibility (no persisted root
migration at that point). **PH-051-10 now implements the separate explicit
`MIG-ENGINE-0.5.0-TO-0.5.1` migration** for existing valid v0.5.0/6
Project Instances. It preserves historical accepted input, Runs and Stage
reports unchanged; uses a durable sibling journal and defaults to manual-only
execution. See [migration/recovery details](13_Migration_Cleanup_Orphan_Recovery_v0.5.1_WIP.md).
No implicit activation of LOCAL_AUTOMATIC is permitted.
