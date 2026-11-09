# Result Envelope, reports, evidence и validation

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE THEMATIC VIEW

## 1. Three output layers

| Layer | Purpose |
|---|---|
| Result Envelope | Stable user-facing status, summary, changes, verification, blockers and next step. |
| Task Report | Detailed engineering account of a completed/blocked task. |
| Request/Run Trace and Evidence | Machine-auditable provenance, tools, checks and state transitions. |

## 2. Result Envelope

Every route returns:

```yaml
result:
  request_ref: RQ-...
  status: COMPLETED
  summary: "..."
  changes: {added: [], changed: [], removed: []}
  verification: {status: PASS, checks: []}
  documentation: {status: UPDATED, updated_refs: []}
  blockers: []
  recovery_options: []
  next_step: {route: RUN_NEXT_READY_TASK, task_ref: TSK-...}
```

For incomplete result, blockers/options/recommendation/resume condition are mandatory.

## 3. Task Report

Contains:

- Task/Work Package/Request refs and revisions;
- expected vs actual result;
- files/contracts/docs added/changed/removed;
- commands/tool calls summary;
- verification and baseline comparison;
- assumptions/questions/blockers;
- scope deviations (must be zero or approved);
- rollback/compensation;
- documentation update;
- evidence and exact next-route candidates.

## 4. Normalized verification evidence

Gate-eligible evidence является отдельным immutable project-local artifact с canonical `EVD-*` id/ref. Contract Catalog v5 регистрирует единственный storage path:

```text
.harness/evidence/<EVD-ID>.yaml
```

Непустая строка, report path или произвольный YAML-файл не являются Gate evidence. Новый artifact использует `SCHEMA-GATE-EVIDENCE@1` и как минимум содержит:

```yaml
verification_evidence:
  schema_version: 1
  id: EVD-PROJECT-PROTOTYPE-CORE-FLOW-001
  ref: EVD-PROJECT-PROTOTYPE-CORE-FLOW-001
  kind: TEST_REPORT
  status: PASS
  provenance:
    source_type: PROJECT_HARNESS_VALIDATION_REPORT
    source_ref: VAL-PROJECT-RUN-001
    producer: PROJECT_HARNESS_RUNTIME
  base_revision: tree:sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  criterion_refs: [PROTOTYPE_CORE_FLOW]
  outcome_refs: []
  profile_control_refs: []
  source_bindings:
    - ref: VAL-PROJECT-RUN-001
      path: .harness/reports/VAL-PROJECT-RUN-001.yaml
      sha256: sha256:abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
  created_at: 2026-08-18T12:00:00Z
```

Нормализатор проверяет exact internal `id == ref`, canonical `EVD-*` grammar, allowed semantic `kind` из `REG-IMPLEMENTATION-LEVELS.evidence_kinds`, status, provenance, exact product-tree `base_revision`, non-empty subject mapping, source bindings, timezone-aware RFC 3339 timestamp, unknown fields и duplicate values. Project-local source `path` обязан оставаться внутри Project Instance, быть regular non-symlink file и совпадать с записанным SHA-256. External source может быть digest-bound без local path.

`status: PASS` является единственным positive closing status текущего contract revision. `FAIL`, `BLOCKED`, `PARTIAL`, `UNKNOWN` и `NOT_APPLICABLE` сохраняются как evidence history, но не закрывают mandatory Gate item. `USER_CLAIM` может быть источником assessment, однако без требуемого corroboration не закрывает mandatory Gate criterion.

## 5. Legacy compatibility

Historical evidence без поля `schema_version` остаётся readable и видимым в validation inventory как `LEGACY`, но не является Gate-eligible. Legacy record не модернизируется in place: для нового Gate требуется новый normalized immutable `EVD-*` artifact, source-bound к historical report/artifact.

Record с явно указанной, но неподдерживаемой `schema_version` не считается legacy. Он malformed и приводит к validation failure. Это предотвращает downgrade через подмену schema marker.

## 6. Exact Gate evidence resolution

Formal approval остаётся обязательным и единственным источником заявленного criterion status. Resolver не делает criterion `PASS` из-за наличия файла; он проверяет достоверность каждого ref, которым approval пытается обосновать уже заявленный `PASS`.

Для каждого criterion-level `evidence_ref` resolver до Stage mutation обязан подтвердить одновременно:

1. exact canonical ref и существование `.harness/evidence/<ref>.yaml`;
2. отсутствие symlink и duplicate conflicting artifact, заявляющего тот же internal id/ref;
3. normalized schema, exact internal id/ref и digest-verifiable persisted bytes;
4. positive closing status;
5. non-empty provenance и source binding;
6. exact `base_revision`, равный current Gate/accepted product baseline;
7. присутствие requested criterion в `criterion_refs`;
8. `kind`, входящий хотя бы в один `required_evidence_kind` этого exact criterion либо hard-constraint override.

Все global approval/Gate `evidence_refs` разрешаются по тем же правилам и дополнительно должны mapping’ить хотя бы один current mandatory criterion с допустимым kind. Resolver fail-closed: dangling, malformed, stale, failed/blocked, wrong-kind, wrong-subject, duplicate conflicting или source-tampered ref блокирует всю acceptance transaction, даже если другие refs валидны.

Required outcomes и profile controls не материализуются этим contract slice. Их отдельное subject-level closure остаётся следующим шагом G-01.

## 7. Runtime evidence freshness

Runtime verification writer создаёт normalized evidence после independent verification и scope checks, с exact product snapshot для соответствующей проверки. Kernel-owned `.harness/**` и protected generated root views не входят в product-tree digest.

Task evidence сохраняет `profile_control_refs: [RUNTIME_TASK_VERIFICATION]` и не объявляет все Stage criteria автоматически. Governed Gate preparation может позднее создать criterion-mapped evidence, source-bound к runtime report, но такой exporter/preparation route не реализуется в этом шаге. Если после проверки product tree меняется, ранний Task evidence остаётся immutable history и становится stale для final Stage baseline.

Safety evidence записывается со status `BLOCKED` и не может закрывать Gate.

## 8. Accepted evidence bindings и tamper detection

Accepted Stage Gate и immutable Stage Acceptance Report сохраняют одинаковый sorted snapshot:

```yaml
evidence_refs:
  - EVD-PROJECT-PROTOTYPE-CORE-FLOW-001
evidence_bindings:
  - ref: EVD-PROJECT-PROTOTYPE-CORE-FLOW-001
    path: .harness/evidence/EVD-PROJECT-PROTOTYPE-CORE-FLOW-001.yaml
    sha256: sha256:89abcdef0123456789abcdef0123456789abcdef0123456789abcdef01234567
```

`validate-project` повторно разрешает closure accepted Gate, перепроверяет source bindings и сравнивает current exact bytes с Gate/Acceptance binding snapshot. Удаление evidence, изменение его content, подмена source report, divergence Gate/Acceptance refs или digest mismatch переводят validation в `FAIL`; accepted history не переписывается автоматически.

## 9. Independent validation

Deterministic validators check schemas, IDs/refs, DAG, statuses, scope/writes, permissions, freshness, requirement/constraint/documentation coverage, evidence closure, accepted digest bindings and manifest. Behavior validators run fixtures/regressions. LLM self-review is never the only evidence for security/state transitions.

## 10. Sufficiency

Evidence is sufficient only for the exact current product revision, requested subject and registry-required kind. Dependency/requirement/product change makes affected evidence stale until an explicit new verification artifact is created. File existence alone is never evidence sufficiency.

## 11. Request Trace

One correlation ID links Request, Plan, Work Package, Task, Run, Tool Invocation, Evidence, Event and Result. Secrets, hidden reasoning and provider billing/token usage are excluded.

Full specifications: [`../12_Implementation_Specifications/02_Result_Envelope_and_Statuses.md`](../12_Implementation_Specifications/02_Result_Envelope_and_Statuses.md), [`../12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md`](../12_Implementation_Specifications/11_Verification_Testing_and_Test_Data.md), [`../12_Implementation_Specifications/12_Request_Trace_and_Logging.md`](../12_Implementation_Specifications/12_Request_Trace_and_Logging.md), [`../12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md`](../12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md).
