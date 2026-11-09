# Классификация данных и runtime permissions

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Классификация данных

Baseline classes:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
SECRET
REGULATED
```

Project policy может расширять taxonomy, но каждая extension class обязана иметь mapping к baseline.

## 2. Data Policy

Для класса задаются:

- allowed storage locations;
- allowed agent/model/tool adapters;
- local/external processing boundary;
- redaction and minimization;
- log/evidence handling;
- retention and deletion policy;
- geographic/compliance restrictions;
- approval requirements.

## 3. Capability Registry

Baseline capabilities:

```text
FILESYSTEM_READ
FILESYSTEM_WRITE
COMMAND_EXECUTE
NETWORK_READ
NETWORK_WRITE
SECRET_REFERENCE
MODEL_EXTERNAL_EGRESS
GIT_COMMIT
GIT_PUSH
PR_CREATE
EXTERNAL_SYSTEM_WRITE
DEPLOY
DATA_MIGRATE
DATA_DELETE
RELEASE_PUBLISH
PROJECT_CONTROL_WRITE
HARNESS_DISTRIBUTION_WRITE
```

`PROJECT_CONTROL_WRITE` изменяет только project-local `.harness/` control plane. `HARNESS_DISTRIBUTION_WRITE` изменяет universal kernel, schemas, routing, adapters или distribution content. Они не взаимозаменяемы.

## 4. Deny by default

Доступность tool не означает permission. Каждый side effect требует Capability Grant, привязанный к task/run, exact resources, target plane и effective policies.

```yaml
capability_grant:
  id: CGR-RUN-0001
  task_ref: TSK-BACKEND-040@3
  run_ref: RUN-20260806-0001
  capability: FILESYSTEM_WRITE
  target_plane: PRODUCT
  effect: ALLOW
  resources:
    - repository_ref: REP-BACKEND-001
      paths:
        - services/backend/src/search/**
        - services/backend/tests/search/**
  issued_by: kernel
  authority_ref: PLC-PERM-001
  approval_refs: []
  expires_at: 2026-08-06T12:00:00Z
  audit: REQUIRED
```

## 5. Enforcement points

Permissions применяются:

- при Request Plan и route validation;
- при Prompt Bundle compilation;
- при tool registration;
- перед каждым Tool Invocation;
- на filesystem/network/database wrappers;
- при Git/publication operation;
- при state transition;
- в post-run audit.

Instruction «не делай» без технического enforcement недостаточна для hard boundary.

## 6. Identity и approvals

Approval содержит actor identity, role, decision, scope, expiry и audit/signature reference. Обычное user message становится approval только после формализации material decision route.

Separation of duties может требовать разных actors для task execution и approval.

## 7. Egress

До передачи context внешнему adapter проверяются:

- data classes;
- effective constraints;
- redaction/minimization;
- approved adapter/provider profile;
- source authority and trust class;
- logging/evidence policy;
- explicit egress capability.

## 8. Maintenance plane isolation

Capability checker обязан отклонять:

- product task с `HARNESS_DISTRIBUTION_WRITE`;
- Harness maintenance task, изменяющий product code;
- mixed-plane Change Pack;
- project-local update, пытающийся изменить universal registry/schema;
- implicit privilege expansion через prompt или skill.

Подробная модель: [`../12_Implementation_Specifications/16_Harness_Maintenance_Plane.md`](../12_Implementation_Specifications/16_Harness_Maintenance_Plane.md).

## 9. Audit data minimization

Run Trace хранит operation metadata и hashes, но не secret values, private chain-of-thought или полные sensitive payloads. Harness не собирает provider billing, стоимость model calls или token usage.

## 8. v0.4.1 sensitivity and control-plane exception

Canonical data sensitivity classes: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`, `SECRET`, `REGULATED`. `UNKNOWN` описывает только отсутствие решения во время intake и не является classification.

Обычный Codex Run не получает `PROJECT_CONTROL_WRITE`. Единственное protocol-level исключение — запись exact Agent Task Result текущего Run в выданный `.harness/runtime/AGENT_RESULTS/<RUN-ID>.json`. Harness проверяет путь, тип файла, link count, размер, UTF-8 JSON, schema, inode и digest; исключение не даёт общего права изменять `.harness/**`.
