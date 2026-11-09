# Change Pack — протокол входящих изменений

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Назначение

Any material change to accepted state becomes an immutable quarantined Change Pack before side effects.

## 2. One target plane

```text
PRODUCT
PROJECT_CONTROL
HARNESS_DISTRIBUTION
```

A Change Pack has exactly one target plane. Mixed product/control/distribution change is split into ordered packs with explicit dependencies.

## 3. Sources

- user project-evolution request;
- accepted answer/decision;
- changed documentation/contract/repository evidence;
- defect/finding/regression;
- prompt/context/skill/policy/adapter change;
- environment/dependency change;
- Harness migration.

## 4. Contract

```yaml
change_pack:
  id: CHP-20260806-001
  request_ref: RQ-20260806-020
  kind: PROJECT_CONTROL_MAINTENANCE
  target_plane: PROJECT_CONTROL
  target_project_ref: project-example
  target_revision: sha256:...
  source_refs: []
  objective: "..."
  normalized_changes: []
  conflicts: []
  impact_analysis_ref: null
  migration_plan_ref: null
  rollback_plan_ref: null
  required_capabilities: []
  status: RECEIVED
```

## 5. Normalization/quarantine

Incoming files/archives are inventoried and hashed; scripts are not executed. Raw sources, normalized candidate, impact, apply plan and evidence are separate immutable revisions.

## 6. Formal decisions

Conversation becomes canonical material change only through answer/decision/approval record with actor, authority, scope and affected refs.

## 7. Maintenance

One natural-language request may initiate the full maintenance protocol, but validation/approval/activation remain explicit internal stages. See [`../12_Implementation_Specifications/16_Harness_Maintenance_Plane.md`](../12_Implementation_Specifications/16_Harness_Maintenance_Plane.md).
