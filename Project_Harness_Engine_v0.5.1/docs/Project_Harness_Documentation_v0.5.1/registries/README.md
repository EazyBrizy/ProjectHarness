> **Current v0.5.1 WIP registry overlay:** `id_prefixes=3`, `statuses=6`,
> `contracts=6` (not the already-used 5). See
> [`PH-051-01`](../05_Updates/05_Execution_Policy_Contract_v0.5.1_WIP.md).
> Table below records the historical accepted v0.5.0 baseline, not the active YAML versions.

# Canonical machine-readable registries

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE REGISTRY INDEX

Registries являются machine-readable source of truth для runtime enums, lifecycles, contract paths и implementation-level criteria. Markdown views не переопределяют YAML.

## Состав v0.5.0

| Registry | Version | Назначение |
|---|---:|---|
| `id_prefixes.yaml` | 2 | Stable entity ID prefixes, включая `STG` |
| `project_profiles.yaml` | 1 | Project profile enum/defaults |
| `statuses.yaml` | 5 | Entity lifecycles, `implementation_stage` и `project_execution` |
| `request_routing.yaml` | 2 | Request classes, modes and internal operations |
| `capabilities.yaml` | 1 | Runtime capabilities and target planes |
| `contracts.yaml` | 5 | Persisted entities, lifecycle bindings and exact storage paths |
| `implementation_levels.yaml` | 1 | Sequential scale, dimensions, criterion statuses/profiles/definitions |

## Loading and lock

```text
distribution manifest verification
→ YAML parse and semantic validation
→ cross-registry graph checks
→ exact version/digest lock in PROJECT_LOCK
→ runtime use
```

`doctor` отклоняет duplicate level IDs/ordinals, cycles, inconsistent previous/next links, dangling criteria profiles и digest mismatch. Contract Catalog v5 дополнительно регистрирует immutable `verification_evidence` в `.harness/evidence/{id}.yaml`; `PROJECT_LOCK` фиксирует новый exact registry digest.

## Change rule

Registry меняется только versioned release/change with compatibility analysis, schema/docs/tests updates and migration where required. Project-specific hard constraints материализуются в Stage Gate overrides; distribution implementation-level registry не редактируется под отдельный проект.
