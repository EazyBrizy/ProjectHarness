# Verification, тестирование и test data policy

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Каждая выполненная задача должна иметь достаточное доказательство результата, но Harness не должен создавать бесполезные тесты ради формального наличия теста. Универсальное правило:

> Каждая task имеет пропорциональный Verification Profile, соответствующий типу изменения и риску.

## 2. Verification Profile

```yaml
verification_profile:
  id: VFP-CODE-TARGETED-001
  revision: 1
  applies_to: [IMPLEMENT, FIX, REFACTOR]
  risk_level: MEDIUM

  required_checks:
    - TARGETED_TESTS
    - NEAREST_REGRESSION
    - STATIC_ANALYSIS
    - SCOPE_DIFF_CHECK
    - DOCUMENTATION_IMPACT_CHECK

  conditional_checks:
    - when: "public_contract_changed"
      add: [CONTRACT_COMPATIBILITY]
    - when: "database_changed"
      add: [MIGRATION_FORWARD, DATA_INTEGRITY, RESTORE_OR_ROLLBACK]

  completion_rule: ALL_REQUIRED_PASS
  known_failure_policy_ref: PLC-KNOWN-FAILURES-001
  evidence_retention: PROJECT_LIFETIME
  status: ACTIVE
```

## 3. Матрица проверок по типу задачи

| Task type | Минимальная проверка |
|---|---|
| `CODE` | Targeted tests, nearest regression, static checks, diff/scope validation. |
| `BUG_FIX` | Reproduction fixture, fix verification, nearest regression. |
| `REFACTOR` | Behavior-preserving tests, static checks, public contract diff. |
| `API_OR_CONTRACT` | Schema validation, compatibility, provider/consumer checks. |
| `DATABASE_MIGRATION` | Forward migration, data integrity, repeatability/idempotency, rollback/restore plan. |
| `UI` | Component/browser/accessibility checks пропорционально риску. |
| `INFRASTRUCTURE` | Syntax/schema, plan/dry-run, policy, rollback. |
| `DOCUMENTATION` | Links, anchors, examples, references, schema consistency. |
| `DIRECTORY_OR_CONFIG` | Structure/schema/dry-run; отдельный unit test обычно не нужен. |
| `ARCHITECTURE_DECISION` | Completeness, alternatives, constraint coverage, approval. |
| `SKILL_OR_PROMPT` | Compiler/routing fixtures, behavioral and negative tests. |
| `SECURITY` | Positive + negative policy checks, boundary tests. |

## 4. Test selection

Harness не запускает полный suite на каждой мелкой task по умолчанию. Набор определяется:

```text
changed paths
+ affected requirements/contracts
+ dependency graph
+ risk level
+ task type
+ project policy
+ release phase
```

Уровни:

```text
TARGETED
NEAREST_REGRESSION
TRACK_INTEGRATION
PROJECT_REGRESSION
RELEASE_SUITE
```

Task completion обычно требует первых двух уровней. Полный project/release suite запускается на integration/release gates или при high-risk change.

## 5. Baseline failures

До выполнения code-changing task Harness по возможности фиксирует baseline:

```yaml
test_baseline:
  id: TSB-20260806-001
  repository_revision: sha256:...
  environment_ref: TEN-APP-TEST@5
  selected_suite: NEAREST_REGRESSION
  passed: 124
  failed:
    - test_ref: TEST-LEGACY-007
      failure_hash: sha256:...
      classification: KNOWN_UNRELATED
  captured_at: 2026-08-06T13:00:00Z
```

После изменения failure классифицируется:

```text
NEW_REGRESSION
EXPECTED_BEHAVIOR_CHANGE
STALE_TEST
KNOWN_UNRELATED
FLAKY_SUSPECTED
ENVIRONMENT_FAILURE
```

Новая регрессия, внесённая текущей task, блокирует completion. Known unrelated failure не приписывается текущей task, но остаётся видимой.

## 6. Политика устаревших тестов

Тест считается stale, если он проверяет behavior, который формально изменён accepted requirement/decision.

Правила:

1. Test update/delete выполняется в той же Work Package или mandatory dependent task.
2. Удаление требует ссылки на superseded requirement/decision или доказательство дублирования.
3. Нельзя удалить тест только ради зелёного результата.
4. Если тест выявляет реальную регрессию, изменение кода не считается завершённым.
5. Если test fixture несовместима с новой valid architecture, она обновляется с documentation/evidence.
6. Release gate не игнорирует known failures без policy/waiver.

```yaml
stale_test_resolution:
  test_ref: TEST-AUTH-OLD-SESSION
  action: UPDATE
  reason: "ADR-AUTH-003 superseded stateless session behavior"
  decision_ref: ADR-AUTH-003@1
  replacement_test_refs: [TEST-AUTH-REDIS-SESSION]
```

## 7. Test Environment Contract

```yaml
test_environment:
  id: TEN-APP-TEST
  revision: 5
  strategy: PREMIGRATED_TEMPLATE
  database_engine_ref: TEC-POSTGRES@16
  migration_set_hash: sha256:...
  fixture_version: 12

  isolation:
    mode: SCHEMA_PER_RUN
    naming_template: "harness_${run_id}"
    cleanup: DROP_SCHEMA_ON_SUCCESS_OR_TTL

  reset_strategy: TRANSACTION_ROLLBACK
  shared_services:
    - ref: SVC-REDIS-TEST
      isolation: NAMESPACE_PER_RUN

  rebuild_when:
    - MIGRATION_SET_CHANGED
    - TEMPLATE_INCOMPATIBLE
    - CORRUPTION_DETECTED

  status: READY
```

## 8. Test database policy

Harness не пересоздаёт всю БД и не прогоняет все миграции на каждую task без необходимости.

Preferred flow:

```text
Maintain pre-migrated template/snapshot keyed by migration_set_hash
→ create isolated clone/schema for run
→ apply only pending migrations when hash changed
→ load versioned minimal fixtures
→ execute targeted tests
→ reset via transaction/clone disposal
```

Варианты isolation по приоритету:

1. database clone per run;
2. schema per run;
3. container/instance per parallel batch;
4. shared persistent test DB with exclusive lease — только если изоляция выше недоступна.

## 9. Миграции

Database-changing task обязана проверить:

- migration ordering;
- forward apply на current baseline;
- повторный запуск или explicit non-idempotency contract;
- data compatibility;
- application compatibility before/after rollout, если требуется;
- rollback либо restore procedure;
- template migration hash update;
- parallel migration-head conflicts.

Нельзя считать «миграция применена локально» достаточным evidence для shared/release gate.

## 10. Documentation and structural tasks

Для задач документации, каталогов и простых config changes не создаются искусственные unit tests. Достаточны:

- schema/format validation;
- link/anchor/reference checks;
- expected path existence;
- dry-run;
- generated-view consistency;
- diff scope check.

Verification Profile должен явно возвращать `NOT_APPLICABLE` для неуместных test categories, а не молча пропускать их.

## 11. Evidence Contract

```yaml
verification_evidence:
  schema_version: 1
  id: EVD-TSK-BE-SEARCH-030-001
  ref: EVD-TSK-BE-SEARCH-030-001
  kind: TEST_REPORT
  status: PASS
  provenance:
    source_type: PROJECT_HARNESS_VALIDATION_REPORT
    source_ref: VAL-RUN-20260806-0011
    producer: PROJECT_HARNESS_RUNTIME
  base_revision: tree:sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  criterion_refs: [PROTOTYPE_CORE_FLOW]
  outcome_refs: []
  profile_control_refs: []
  source_bindings:
    - ref: VAL-RUN-20260806-0011
      path: .harness/reports/VAL-RUN-20260806-0011.yaml
      sha256: sha256:abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
  created_at: 2026-08-18T12:00:00Z
  task_ref: TSK-BE-SEARCH-030@1
  run_ref: RUN-20260806-0011
  report_refs: [VAL-RUN-20260806-0011]
  validator: PROJECT_HARNESS_RUNTIME
  details:
    profile_ref: VFP-CODE-TARGETED-001@1
    environment_revision: TEN-APP-TEST@5
    checks:
      - id: CHK-TARGETED
        command_ref: CMD-NPM-TEST-SEARCH
        result: PASS
        exit_code: 0
        output_digest: sha256:abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
    baseline_comparison:
      new_failures: []
      resolved_failures: []
      unchanged_known_failures: [TEST-LEGACY-007]
```

Новые Gate используют только normalized immutable evidence. Historical record без `schema_version` остаётся readable, но не закрывает mandatory criterion без нового source-bound artifact.

## 12. Flaky tests

Flaky suspected test не отключается автоматически. Harness:

1. сравнивает failure signature с baseline/history;
2. выполняет bounded rerun по policy;
3. классифицирует как suspected flaky;
4. создаёт отдельную corrective task, если подтверждено;
5. не объявляет product task failed, если failure доказан как unrelated и policy разрешает;
6. сохраняет warning для release gate.

## 13. Критерии приёмки

1. Каждая task имеет Verification Profile, но не обязательно unit test.
2. Test selection зависит от impact и риска.
3. Новая регрессия блокирует completion; known unrelated failure не маскируется.
4. Stale test update/delete имеет formal rationale.
5. Test DB использует pre-migrated template и isolation, а не полный rebuild каждый раз.
6. Parallel runs не разделяют mutable test data без lease/isolation.
7. Documentation/config tasks проверяются пропорционально.
8. Evidence воспроизводимо связано с revisions и environment.
