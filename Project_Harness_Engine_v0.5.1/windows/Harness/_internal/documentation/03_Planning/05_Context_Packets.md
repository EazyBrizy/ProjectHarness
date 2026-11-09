# Контекстные пакеты previous/current/next

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Назначение

Context Packet — generated cold-start view для конкретного Run. Он позволяет Codex или другому executor adapter начать задачу без зависимости от истории диалога и без загрузки всей документации проекта.

Context Packet не является источником истины. Его источники — canonical Project Definition, requirements, constraints, decisions, Work Package, Task Contract, Context Plan и зафиксированные revisions.

## 2. Место в цепочке

```text
READY Task
→ Context Policy
→ Context Plan
→ Context Packet
→ JIT Prompt Bundle
→ Run
```

- **Context Policy** определяет постоянные правила отбора.
- **Context Plan** фиксирует, какие источники и почему нужны конкретному task/run.
- **Context Packet** материализует минимальный набор previous/current/next для executor.
- **Compiled Prompt Bundle** ссылается на неизменяемый Context Packet.

## 3. Contract

```yaml
context_packet:
  id: CPK-TSK-BACKEND-040-R1
  schema_version: 3
  generated_at: 2026-08-06T10:00:00Z
  harness_version: 0.4.1

  correlation_id: COR-20260806-0001
  request_ref: RQ-20260806-0001
  work_package_ref: WP-SEARCH-001@1
  task_ref: TSK-BACKEND-040@3
  run_plan_ref: RNP-RUN-20260806-0001@1

  project_model_revision: sha256:...
  project_definition_ref: PJD-PROJECT-001@4
  architecture_baseline_ref: ARB-PROJECT-002@1
  technology_baseline_ref: TBL-PROJECT-001@2
  roadmap_revision: sha256:...
  repository_revisions:
    backend: abc123

  effective_constraints_hash: sha256:...
  prompt_plan_ref: PPL-TSK-BACKEND-040-R1@1
  context_plan_ref: CTX-TSK-BACKEND-040-R1@1

  previous:
    task_ref: TSK-CONTRACT-030@1
    run_ref: RUN-20260806-0000
    result_status: COMPLETED
    report_ref: TRP-TSK-CONTRACT-030-001
    evidence_refs: [EVD-CONTRACT-SEARCH-001]
    produced_artifact_refs: [CNT-SEARCH@2]

  current:
    purpose: "Реализовать backend endpoint поиска"
    expected_result: "Endpoint соответствует CNT-SEARCH@2"
    requirement_refs: [REQ-SEARCH-001]
    documentation_refs: [DOC-API-SEARCH@2]
    constraint_refs: [CST-SEC-001]
    decision_refs: [ADR-API-004]
    contract_read_refs: [CNT-SEARCH@2]
    contract_write_refs: []
    allowed_write_paths:
      - services/backend/src/search/**
      - services/backend/tests/search/**
    capability_grant_refs: [CGR-RUN-0001]
    skill_refs: [SKL-UNIVERSAL-IMPLEMENT@2]
    verification_profile_ref: VFP-CODE-TARGETED-001@1
    blocker_protocol_ref: PLC-BLOCKER-001@1

  next:
    candidate_task_refs:
      - TSK-FRONTEND-050@1
      - TSK-INTEGRATE-060@1
    selected_by: KERNEL
    selection_policy_ref: PLC-NEXT-TASK-001@2
    readiness_gates: []

  unresolved_decision_refs: []
  unresolved_unknown_refs: []
  source_map_ref: SMP-CPK-BACKEND-040-R1
  packet_hash: sha256:...
  status: BOUND
```

## 4. Previous

Раздел `previous` содержит только релевантный непосредственный контекст:

- producer tasks для требуемых артефактов;
- их завершённые Run и результаты;
- evidence и принятые contracts;
- точные revisions.

Он не должен содержать всю историю проекта или полный previous prompt. Полные immutable bundles и reports остаются в run artifact store; packet хранит ссылки и hashes.

## 5. Current

Раздел `current` обязан однозначно отвечать Codex:

1. что именно сделать;
2. для чего это нужно;
3. какие требования, решения и разделы документации применимы;
4. какие входные артефакты уже существуют;
5. что разрешено читать и изменять;
6. какие действия запрещены;
7. какой результат ожидается;
8. как результат проверяется;
9. при каких условиях нужно остановиться.

В packet не включаются unrelated backlog, неактуальные документы и будущая функциональность, не являющаяся готовым dependency.

## 6. Next

`next` — подсказка для восстановления, а не право executor самостоятельно выбрать новую работу. После завершения Run kernel заново вычисляет READY candidates по DAG, revisions, leases, blockers и policy. Поэтому `next.candidate_task_refs` может быть устаревшим после любого material state change.

## 7. Staleness

Перед dispatch проверяются:

- project model revision;
- Project Definition, architecture и Technology Baseline;
- Task Contract revision;
- effective constraint/policy hash;
- required artifact revisions;
- repository base revisions;
- ownership and environment leases;
- Prompt Plan, Context Plan и Context Packet hashes;
- capability grant scope and expiry.

При mismatch packet получает `STALE`, не используется для side effects и пересобирается из canonical sources.

## 8. Безопасность

Context Packet:

- не содержит secret values;
- не повышает authority untrusted source;
- сохраняет source boundaries и conflict markers;
- включает только минимально необходимые данные;
- проходит egress check перед передачей external adapter;
- не содержит скрытые инструкции из repository text или tool output.

## 9. Хранение

Рекомендуемый путь:

```text
.harness/generated/context-packets/<task-id>/<run-id>.yaml
```

Executed packet сохраняется immutable вместе с Run. Packet для неисполненного Run может быть удалён и пересобран.

## 10. Связанные спецификации

- [`06_Context_Planning_and_Overflow.md`](06_Context_Planning_and_Overflow.md)
- [`../12_Implementation_Specifications/04_JIT_Prompt_Compilation.md`](../12_Implementation_Specifications/04_JIT_Prompt_Compilation.md)
- [`../12_Implementation_Specifications/12_Request_Trace_and_Logging.md`](../12_Implementation_Specifications/12_Request_Trace_and_Logging.md)
- [`../12_Implementation_Specifications/15_Codex_Agent_Adapter.md`](../12_Implementation_Specifications/15_Codex_Agent_Adapter.md)
