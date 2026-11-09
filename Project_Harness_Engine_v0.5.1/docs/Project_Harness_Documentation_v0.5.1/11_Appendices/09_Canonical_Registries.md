# Canonical registries и их использование

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE REGISTRY VIEW

## 1. Назначение

Machine-readable registries устраняют расхождения между documentation, schemas, runtime enums, generated artifacts и `PROJECT_LOCK`.

## 2. Состав

| Файл | Version | Назначение |
|---|---:|---|
| [`../registries/id_prefixes.yaml`](../registries/id_prefixes.yaml) | 2 | Entity ID prefixes и schema keys; `STG` для Stage Plan |
| [`../registries/project_profiles.yaml`](../registries/project_profiles.yaml) | 1 | Project profile enum |
| [`../registries/statuses.yaml`](../registries/statuses.yaml) | 5 | Lifecycles/status groups, включая Stage/project execution |
| [`../registries/request_routing.yaml`](../registries/request_routing.yaml) | 2 | Request classes, modes, operations |
| [`../registries/capabilities.yaml`](../registries/capabilities.yaml) | 1 | Runtime capabilities and target planes |
| [`../registries/contracts.yaml`](../registries/contracts.yaml) | 5 | Persisted contracts, lifecycle and exact storage paths |
| [`../registries/implementation_levels.yaml`](../registries/implementation_levels.yaml) | 1 | Sequential scale and evidence criteria |

## 3. Stage-specific registrations

Contract Catalog v5 регистрирует:

```text
stage_state          .harness/stages/STAGE_STATE.yaml
stage_plan           .harness/stages/PLANS/{id}@{revision}.yaml
stage_gate           .harness/stages/GATES/{id}@{revision}.yaml
stage_acceptance     .harness/stages/ACCEPTANCE/{id}@{revision}.yaml
maturity_assessment  .harness/stages/ASSESSMENTS/{id}@{revision}.yaml
verification_evidence .harness/evidence/{id}.yaml
```

`verification_evidence` имеет lifecycle `IMMUTABLE_RECORD` и revision policy `IMMUTABLE`; Gate resolver допускает только exact canonical `EVD-*` path.

Statuses v5 добавляет `implementation_stage` и `project_execution`; Project State v6 использует `TARGET_LEVEL_REACHED`, а legacy `COMPLETED` остаётся compatibility-only historical value.

## 4. Loading order

```text
manifest/hash verification
→ individual registry validation
→ cross-registry refs and graph validation
→ exact Project Lock comparison
→ compiler/runtime startup
```

## 5. Change rules

Registry update требует version bump, compatibility analysis, source+embedded synchronization, schema/docs/test updates, digest refresh and migration where persisted semantics change.

## 6. Generated documentation

Generated matrices должны byte-for-byte совпадать с YAML registries. Markdown не является независимым enum source.

## 7. Implementation references

- base registry normalization: [`../12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md`](../12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md);
- implementation-level registry and checks: [`../12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md`](../12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md).
