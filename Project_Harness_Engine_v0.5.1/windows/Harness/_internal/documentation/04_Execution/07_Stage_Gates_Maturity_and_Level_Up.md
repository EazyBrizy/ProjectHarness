# Stage Gates, Brownfield Maturity и Level-up

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE THEMATIC VIEW

## 1. Stage lifecycle

```text
PLANNED → ACTIVE ── readiness closed ─────────────→ VERIFYING → ACCEPTED
             └──── missing evidence → ACTIVE / STAGE_ACCEPTANCE_PREPARATION ─┘
VERIFYING ── valid open formal review → BLOCKED
BLOCKED ── resume-stage-gate → ACTIVE preparation | VERIFYING
PLANNED/ACTIVE ───────────────────────────────────→ SUPERSEDED
```

Последняя ordinary mandatory Task active stage запускает deterministic Gate-readiness evaluation на exact final product tree. Она не завершает Project Instance и не обязана сразу переводить Stage в manual review. При missing final-baseline evidence runtime создаёт governed preparation WP/Task; при полном evidence coverage Stage переходит в `VERIFYING` напрямую. Проект остаётся управляемым до successful closed Gate и formal acceptance transaction.

## 2. Stage Gate

Gate type `STAGE_ACCEPTANCE` проверяет required outcomes, stage criteria, hard constraints, profile controls, mandatory Work Packages, critical blockers, evidence и permitted-use boundary.

Criterion statuses:

```text
PASS | PARTIAL | FAIL | UNKNOWN | NOT_APPLICABLE
```

Mandatory criterion закрывается только `PASS` или `NOT_APPLICABLE` с rationale и validator/actor. `PARTIAL`, `FAIL` и `UNKNOWN` блокируют acceptance. Average score не вычисляется: один незакрытый mandatory criterion блокирует Stage.

### 2.1. Exact evidence trust contract

Каждый ref, которым formal approval закрывает `PASS`, обязан разрешаться в existing immutable normalized artifact по exact canonical path `.harness/evidence/<EVD-ID>.yaml`. Resolver проверяет exact internal id/ref, normalized schema, allowed `kind`, positive status, provenance/source binding, requested criterion mapping, exact current product-tree `base_revision` и SHA-256 persisted/source bytes. Per-criterion kind сверяется с `required_evidence_kinds` exact criterion или hard-constraint override из Implementation Level Registry.

Global approval/Gate `evidence_refs` проходят тот же resolver и должны mapping’ить current mandatory criterion с разрешённым kind. Один dangling, legacy, malformed, stale, wrong-kind, wrong-subject, failed/blocked, source-tampered либо duplicate-conflicting ref блокирует всю acceptance transaction. `USER_CLAIM` без требуемого corroboration mandatory item не закрывает.

Formal approval остаётся обязательным: существование файла не создаёт criterion `PASS`. Historical evidence без `schema_version` читается как legacy, но не закрывает новый Gate. Accepted Gate и Stage Acceptance Report фиксируют одинаковые exact `evidence_refs` и `{ref, path, sha256}` bindings; `validate-project` обнаруживает последующее удаление, изменение либо подмену source-bound evidence.

Ordinary runtime Task verification пишет normalized evidence для exact post-verification product revision, но не mapping’ит автоматически все Stage results. После следующего product change такое evidence остаётся историческим и становится stale для final Stage baseline. После последней ordinary Task readiness evaluator использует exact compatible final-baseline candidates; при gaps создаётся `STAGE_ACCEPTANCE_PREPARATION`, а после PASS verification kernel материализует **только действительно доказанные** subject-mapped immutable evidence bindings. No-op PASS сам по себе не подтверждает другие kinds: недостающие subject остаются gap/`BLOCKED` с recovery. `prepare-stage-approval` перечисляет current candidates и unresolved gaps, но не превращает candidate в formal `PASS` и не выдаёт approval автоматически.

## 3. Formal approval и bounded preparation flow

`accept-stage` требует отдельный approval record; простой `--yes` отсутствует. Поддерживаемый операторский цикл является самодостаточным и не требует читать private Python code, вручную вычислять product digest или разбирать internal Gate files:

```text
complete last ordinary mandatory Task
→ deterministic Gate-readiness evaluation
→ [STAGE_ACCEPTANCE_PREPARATION through next → verify → complete, only for exact gaps]
→ VERIFYING
→ stage-status
→ prepare-stage-approval
→ добавить/проверить evidence и formal fields
→ accept-stage
→ [resume-stage-gate after persisted honest BLOCKED review]
```

### 3.0.1. Exact current status

```bash
project-harness stage-status --project <root>
```

Для current active Stage команда возвращает:

- active level и canonical target;
- exact Stage Plan ref/path/revision/status;
- exact Gate ref/path/revision/status и SHA-256 exact Gate file;
- canonical current product `baseline_revision`/`baseline_digest`;
- counts по required outcomes, level criteria, hard constraints, profile controls, required WPs и critical blockers;
- current refs/statuses обязательных Work Packages и blockers;
- `next_operator_route`.

Когда current Plan и Gate находятся в `VERIFYING`, `next_operator_route.route == PREPARE_STAGE_APPROVAL`. Для persisted Gate-related `BLOCKED` route равен `RESUME_STAGE_GATE`; сначала требуется dedicated recovery. Console status предназначен для ориентации; formal operator record создаётся отдельной командой ниже.

### 3.0.2. Deterministic strict DRAFT

```bash
project-harness prepare-stage-approval \
  --project <root> \
  --output ../operator-records/<stage>-approval.yaml
```

Команда и API работают для current active Stage, когда exact current Plan и Gate имеют status `VERIFYING` или Gate-related `BLOCKED`. В BLOCKED состоянии draft отражает immutable blocked snapshot, но не заменяет обязательный `resume-stage-gate`; supported next route остаётся recovery. Output может находиться вне Project Instance либо внутри exact safe subtree `.harness/operator/APPROVALS/`. Существующий пользовательский файл не перезаписывается без explicit `--force`; directory/symlink output отклоняется. Для неизменных Gate и product baseline bytes результата детерминированы.

Generated record обязан проходить `SCHEMA-STAGE-APPROVAL@1` уже в draft state:

```text
stage_approval:
  schema_version: 1
  schema_ref: SCHEMA-STAGE-APPROVAL@1
  record_kind: STAGE_APPROVAL
  record_state: DRAFT
  id: null
  approved: false
  actor: null
  approved_at: null
  level: PROTOTYPE
  target_level: MVP
  acceptance_method: EXECUTED_STAGE_WORK
  stage_plan_ref: STG-PROJECT-PROTOTYPE-001@2
  stage_plan_path: .harness/stages/PLANS/STG-PROJECT-PROTOTYPE-001@2.yaml
  stage_plan_revision: 2
  stage_plan_digest: sha256:<exact-plan-file-digest>
  gate_ref: GATE-PROJECT-PROTOTYPE-001@2
  gate_path: .harness/stages/GATES/GATE-PROJECT-PROTOTYPE-001@2.yaml
  gate_revision: 2
  gate_digest: sha256:<exact-gate-file-digest>
  baseline_revision: tree:sha256:<exact-current-product-tree-digest>
  outcome_results:
    - outcome_ref: working_primary_flow
      status: UNKNOWN
      evidence_refs: []
      rationale: null
      validator: null
  criteria_results:
    - criterion_ref: PROTOTYPE_CORE_FLOW
      status: UNKNOWN
      evidence_refs: []
      rationale: null
      validator: null
  hard_constraint_results: []
  profile_control_results: []
  permitted_use:
    status: UNCONFIRMED
    users: [DEVELOPER]
    environments: [LOCAL]
    data_classes: [PUBLIC]
    data_constraints: [SYNTHETIC_ONLY]
```

Полный record дополнительно содержит:

1. exact active/target и acceptance method;
2. exact Plan/Gate refs, paths, revisions, digests, source statuses и Gate base;
3. current canonical product baseline;
4. last accepted report/baseline context;
5. complete required-outcome definitions и one-to-one result skeletons;
6. complete level-criterion definitions и result skeletons;
7. hard-constraint definitions/results;
8. profile-control definitions/results;
9. exact required WP refs с current refs/paths/statuses;
10. exact current critical blocker refs/statuses/reasons;
11. current permitted-use template;
12. compatible normalized evidence candidates с kind, status, base, provenance, source bindings/digests и mapped subjects;
13. unresolved gaps;
14. exact preparation fingerprint.

Все mandatory result statuses по умолчанию остаются `UNKNOWN`; `evidence_refs` пусты, `rationale/validator` равны `null`. Existing evidence candidate является только подсказкой. Команда `prepare-stage-approval` не запускает repository commands и не изменяет product tree, Stage State, Stage Plan, Gate, Work Packages или blockers; не создаёт Decision/Acceptance Report; не принимает Stage и сама не создаёт WP. Отдельный runtime route `STAGE_ACCEPTANCE_PREPARATION` создаётся до `VERIFYING` только deterministic readiness evaluator’ом при missing exact final-baseline evidence.

### 3.0.3. Formal completion and acceptance

Operator/validator редактирует только formal conclusion fields и evidence refs, сохраняя exact-bound context из generated record. Для submission требуется:

- `record_state: APPROVED`;
- canonical `id: DEC-*`;
- `approved: true`;
- canonical `actor: ACT-*`;
- valid UTC `approved_at` с suffix `Z`;
- `permitted_use.status: CONFIRMED`;
- every mandatory result: `PASS` либо применимый `NOT_APPLICABLE` с rationale/validator;
- every `PASS`: один или несколько exact compatible normalized `EVD-*` refs;
- explicit `known_limitations` и `next_stage_gaps`.

`PARTIAL`, `FAIL` и `UNKNOWN` блокируют acceptance. `NOT_APPLICABLE` без rationale/validator либо вопреки applicability блокируется. Evidence candidates не копируются в conclusions автоматически.

```bash
project-harness accept-stage \
  --project <root> \
  --level PROTOTYPE \
  --approval ../operator-records/prototype-approval.yaml
```

До первой Stage mutation strict preflight снова валидирует schema и exact binding: active/target, Plan/Gate refs, paths, revisions, digests/statuses, current product baseline, definitions/result set, required WP/blocker snapshot, permitted-use template и preparation fingerprint. Product-tree drift или новая Gate revision делает старый record stale; требуется новый `prepare-stage-approval`. Draft с `approved: false` возвращает waiting-decision semantics и не создаёт acceptance artifacts.

Malformed approval остаётся validation failure с zero state mutation. Structurally valid formal review с mandatory `UNKNOWN`, `PARTIAL` или `FAIL` conclusion атомарно создаёт новые BLOCKED Plan/Gate revisions, exact failed/missing items, candidate evidence diagnostics и distinct `STAGE_GATE_BLOCKER`; project route становится `RESOLVE_STAGE_GATE`. Decision/Acceptance Report и next-stage activation не создаются.

Для executed work requested level обязан совпадать с active Stage. `SATISFIED_BY_BASELINE` разрешён только Brownfield/Hybrid и только на основании immutable exact assessment.

### 3.0.4. Gate recovery

```bash
project-harness resume-stage-gate --project <root>
```

Route разрешён только для persisted Gate-related blocker. Recovery revalidates current canonical baseline и compatible evidence, создаёт новые immutable Plan/Gate/blocker revisions и:

- переводит `BLOCKED → ACTIVE`, создавая/связывая один idempotent preparation WP/Task, если gaps остаются;
- переводит `BLOCKED → VERIFYING`, если evidence needs уже закрыты;
- никогда не переписывает BLOCKED history и не использует ordinary Task `resume` semantics.

Repeated call after successful recovery returns the current route idempotently.

### 3.0.5. Public API

```python
from pathlib import Path
from project_harness import prepare_stage_approval, product_baseline_revision, resume_stage_gate, stage_status

root = Path('/project')
context = stage_status(root)
baseline = product_baseline_revision(root)
draft = prepare_stage_approval(root, Path('/operator/prototype-approval.yaml'))
  # Only when context['next_operator_route']['route'] == 'RESUME_STAGE_GATE':
recovery = resume_stage_gate(root)
```

`product_baseline_revision()` является public supported helper и использует тот же canonical product-tree algorithm, что acceptance preflight. Operator documentation и workflows не должны обращаться к private `_product_baseline_revision()`.

### 3.1. Exact immutable `assessment_ref`

Для `SATISFIED_BY_BASELINE` поле `assessment_ref` обязано быть exact canonical revisioned ref вида `<assessment-id>@<positive-integer-revision>` без пробелов, wildcard-символов, дополнительного suffix/prefix и leading zero в revision. Разрешается только один path: `.harness/stages/ASSESSMENTS/<assessment-id>@<revision>.yaml`; prefix glob, выбор latest candidate и lexicographic fallback запрещены.

До Stage recovery или новой Stage mutation preflight проверяет весь binding: canonical `assessment_digest` формы `sha256:<64 lowercase hex>`, exact filename, единственный top-level envelope `maturity_assessment`, совпадение internal `id`, integer `revision` и digest exact file bytes. Missing/unversioned/malformed/ambiguous ref, wrong envelope, internal mismatch или wrong digest завершают команду validation failure без изменения Stage state. Stage Acceptance Report получает `assessment_ref` из результата exact resolver, то есть сохраняет ровно ту revision, которая была проверена. Exact resolution является необходимым, но недостаточным условием: freshness/current-context binding проверяется отдельным preflight ниже.

### 3.2. Brownfield assessment freshness и current-context binding

Перед созданием Decision, Acceptance Report или новой Stage revision exact resolved assessment должен быть связан с текущим Project Instance, а не только существовать под правильным ref. Для `SATISFIED_BY_BASELINE` preflight одновременно требует:

1. `assessment.status == COMPLETED`;
2. `assessment.repository_revision` равен текущему canonical product-tree digest;
3. `approval.baseline_revision` равен тому же digest;
4. `assessment.target_level` равен canonical `STAGE_STATE.implementation.target_level`;
5. `assessment.previous_highest_accepted_level` равен `STAGE_STATE.implementation.highest_accepted_level` до transaction;
6. `assessment.claimed_current_level` равен immutable accepted user claim из `PROJECT_INPUT_ACCEPTED.yaml`;
7. `proposed_active_stage`, current `active_stage` и requested levels образуют один непрерывный sequential context от текущего accepted baseline;
8. requested accepted level не выше `highest_satisfied_candidate_level`, который дополнительно пересчитывается из mandatory registry criteria, а не доверяется как свободному полю;
9. evidence, помеченное `stale` либо имеющее другую `base_revision`, и соответствующие assessment warnings не используются для закрытия принимаемых mandatory criteria.

Любое расхождение возвращает structured `STALE` result с `reason_codes`, отдельными `issues` (`actual`/`expected`), source assessment ref/digest и assessment/current contexts. Acceptance write set при этом пуст: Decision, Acceptance Reports, accepted Plan/Gate revisions, `highest_accepted_level` и следующая active Stage не изменяются.

Staleness фиксируется новой immutable revision в `ASSESSMENTS`. Она ссылается на exact source assessment и его digest, сохраняет original `repository_revision`, записывает detected current revision и причины, но не переписывает source revision и не обновляет Stage State. После нового read-only `assess-maturity` для текущего tree/context новый exact assessment снова может быть принят при валидном approval.

Multi-level Brownfield acceptance использует один exact current assessment для всего contiguous level slice. Проверка всех уровней завершается до первого canonical write; либо вся transaction проходит, либо ни одна Stage не принимается.

## 4. Crash-consistent acceptance transaction

Успешный transition записывает согласованный canonical write set:

1. immutable Stage Acceptance Report;
2. accepted Stage Plan/Gate revisions и current indexes;
3. Stage State revision и history snapshot;
4. Decision record;
5. next-stage activation либо `TARGET_LEVEL_REACHED`;
6. `CURRENT_STATE` и `NEXT_TASK`;
7. supersession/staleness старого executable route, где это требуется.

До первого canonical replace service сохраняет complete ordered write set, existed-before markers, backups, staged candidates, old/new digests, operation/result digests, timestamps и per-entry state в `.harness/stages/TRANSACTIONS/<transaction-id>/TRANSACTION.yaml`.

### 4.1. Terminal truth

`COMMITTED` допустим только когда каждый canonical target существует в expected new state и digest совпадает. `ROLLED_BACK` допустим только когда каждый old target восстановлен по digest либо удалён, если до transaction он отсутствовал. Partial acceptance и mixed indexes/files недопустимы.

### 4.2. Automatic reconciliation

Перед новой Stage mutation и при `validate-project` unique latest non-terminal transaction reconciles deterministically:

- full digest-confirmed new write set → завершить `COMMITTED`;
- любое другое recoverable состояние → полностью восстановить old write set и подтвердить `ROLLED_BACK`;
- corrupt/missing journal или backup → заблокировать mutation точным diagnostic, не угадывать.

Если final commit marker временно не записался после всех replacements, API не сообщает ложный rollback. Marker восстанавливается из подтверждённых digests; при устойчивой невозможности записать commit весь old state сначала восстанавливается и только затем возвращается error.

## 5. Acceptance outputs

Каждая принятая стадия обязана иметь:

- immutable baseline revision;
- Stage Acceptance Report;
- permitted-use boundary;
- known limitations;
- next-stage gaps;
- Decision/approval reference;
- exact evidence references;
- immutable evidence bindings `{ref, path, sha256}` shared with the accepted Gate.

Acceptance не утверждает более высокий level и не скрывает ограничения. Система может безопасно остановиться на любой принятой стадии.

## 6. Project execution status

Новые schema-v6 Project States используют lifecycle:

```text
ACTIVE | BLOCKED | TARGET_LEVEL_REACHED | CANCELLED
```

`TARGET_LEVEL_REACHED` означает завершение текущего target cycle, а не вечное завершение проекта. Legacy v0.4.x `COMPLETED` читается через compatibility layer, но не преобразуется автоматически в accepted implementation level.

## 7. Read-only Brownfield assessment

Assessment фиксирует base revision, собирает repository inventory и предоставленные evidence, но не запускает commands. Sources могут включать manifests, configs, test sources/reports, CI artifacts, runbooks, migrations, deployment records, external evidence и user claims с provenance.

Источник target зависит от workspace boundary: внешний intake без Stage State использует текущий `PROJECT_INPUT.yaml`; подготовленный Project Instance использует только `.harness/stages/STAGE_STATE.yaml -> implementation.target_level`. Immutable `PROJECT_INPUT_ACCEPTED.yaml` предоставляет initial accepted facts и не является источником current target после `level-up`.

Если criterion требует runtime proof, которого нет, status равен `UNKNOWN`. Наличие Dockerfile, README label или version string не является достаточным evidence уровня.

## 8. Maturity dimensions

```text
FUNCTIONALITY
ARCHITECTURE_MAINTAINABILITY
DATA_MIGRATIONS
TESTING_VERIFICATION
SECURITY_PRIVACY
DEPLOYMENT_OPERABILITY
RECOVERY
DOCUMENTATION_SUPPORT
RELEASE_EVIDENCE
```

Для каждого level все mandatory criteria оцениваются отдельно. `highest_satisfied_candidate_level` — самый высокий последовательный level, где каждый mandatory criterion имеет `PASS` либо обоснованный `NOT_APPLICABLE`. Среднее между dimensions запрещено.

## 9. Claimed, observed и accepted maturity

- `claimed_current_level` — пользовательское мнение;
- `observed_candidate_level` — описательная форма проекта по inventory;
- `highest_satisfied_candidate_level` — вывод assessment по criteria;
- `highest_accepted_level` — formal accepted baseline после approval.

Assessment может обновить observed value и immutable report, но не accepted value. Acceptance ссылается на exact assessment revision и SHA-256 digest. External evidence inventory сохраняет status, criterion refs, base revision и stale marker, чтобы acceptance мог проверить, что принимаемые mandatory criteria не закрыты evidence другого tree.

## 10. Brownfield routes

```text
COMPLETE_CURRENT_STAGE
MAINTAIN_CURRENT_STAGE
ADVANCE_TO_NEXT_STAGE
TARGET_ALREADY_REACHED
STABILIZE_CURRENT_STAGE
```

Route зависит от accepted baseline, target, gaps и evidence. Degradation accepted baseline ведёт к stabilization, а не к молчаливому downgrade.

## 11. Baseline acceptance

Brownfield/Hybrid может доказать несколько предыдущих стадий в одной governed transaction. Для каждой стадии создаётся отдельный Acceptance Report; progression remains sequential. Один exact assessment должен быть fresh для всего requested slice, а все per-level Gate approvals проверяются до commit. Незавершённый старый route supersede’ится атомарно, чтобы runtime не выдал Task вне новой active stage.

## 12. Level-up

```bash
project-harness level-up   --project <root>   --target MVP   --approval <record>
```

Условия:

- есть canonical highest accepted level;
- новый target строго выше accepted level;
- formal approval валиден;
- same-level maintenance route не остаётся открытым;
- активируется только nearest next stage;
- accepted baselines и completed Runs сохраняются;
- future Prompt Plans старых revisions становятся stale/superseded.

В той же crash-consistent Stage transaction `level-up` атомарно записывает новый target в canonical Stage State и синхронизирует projections `.harness/config/PROJECT.yaml` и `.harness/state/CURRENT_STATE.yaml`. `.harness/state/PROJECT_INPUT_ACCEPTED.yaml` не входит в write set и сохраняет initial accepted target без изменений.

Target равный или ниже accepted level возвращает `TARGET_ALREADY_REACHED` без destructive changes.

## 13. Same-level maintenance

Maintenance is a governed product route, not a maturity disposition and not a level-up:

```bash
project-harness start-maintenance  --project <root> --plan <record>
project-harness next               --project <root>
project-harness verify             --project <root> --allow-command-execution
project-harness complete           --project <root> --result <exact-agent-result>
project-harness cancel-maintenance --project <root> --approval <record>
```

The strict start plan is exact-bound to the canonical Stage State and last accepted baseline. Start fails before mutation when accepted level is absent, requested stage differs from `highest_accepted_level`, target/acceptance/scope bindings are stale, future-stage work is present, an active Run/planning/Gate application exists, or another maintenance WP is open.

The bounded start operation creates one immutable `MAINTAIN_CURRENT_STAGE` Decision, maintenance plan revision, WP, atomic Tasks, DAG, Verification Profiles, Context/Prompt Plans, indexes/current state and one first JIT reservation. The command is idempotent: an exact replay returns the existing route/bundle; the same Decision id with different request bytes is rejected.

Every maintenance executable artifact carries exact `implementation_stage`, `maintenance_route` and `maintenance_plan_ref`. Runtime scheduling filters only that plan while the route is open, so ordinary/future-stage Tasks cannot be selected. Final mandatory completion writes a `MAINTENANCE_COMPLETION` report and restores the route that existed before maintenance (`TARGET_ALREADY_REACHED`, active-stage planning wait or Gate wait). It preserves canonical target, accepted level, Stage Acceptance Reports, accepted Stage Plan/Gate revisions and all completed Runs.

Cancel requires `SCHEMA-MAINTENANCE-CANCEL-APPROVAL@1` and an immutable `CANCEL_MAINTENANCE` Decision exact-bound to the open plan/WP, accepted level, target and last acceptance. Cancellation is allowed only before completed product-changing work and without uncommitted product drift. It creates terminal Task/WP revisions plus a cancellation report; it never deletes history or performs automatic rollback. After `COMPLETED` or valid `CANCELLED`, `level-up` is allowed again.

## 14. Failure semantics

| Условие | Результат |
|---|---|
| Target отсутствует | `WAITING_INPUT` |
| `prepare-stage-approval` до `VERIFYING`/Gate-related `BLOCKED` | validation failure, zero Stage/product mutation |
| Approval output уже существует без `--force` либо находится в запрещённом project path | safe validation failure; пользовательский файл не перезаписывается |
| Generated strict record остаётся `DRAFT`/`approved: false` | `WAITING_DECISION`; zero acceptance artifacts |
| Product tree или exact Gate revision изменились после preparation | stale/exact-binding validation failure; требуется новый draft |
| `UNSURE` не подтверждён | `WAITING_DECISION` |
| Task другой stage | `STAGE_SCOPE_VIOLATION` / validation failure |
| Structurally valid formal review has mandatory `UNKNOWN/PARTIAL/FAIL` | atomic persisted Plan/Gate/project `BLOCKED`, `STAGE_GATE_BLOCKER`, route `RESOLVE_STAGE_GATE`, no acceptance |
| `NOT_APPLICABLE` без rationale/validator | validation failure |
| Dangling или legacy evidence ref | validation failure до Stage mutation |
| Evidence kind не входит в `required_evidence_kinds` criterion | validation failure |
| Evidence не mapping’ит requested criterion | validation failure |
| Evidence provenance/source binding malformed или source digest изменён | validation failure |
| Claimed PASS evidence status `FAIL`/`BLOCKED`/non-positive | validation failure before mutation; an honest result conclusion remains `FAIL/PARTIAL/UNKNOWN` and persists Gate BLOCKED |
| Accepted evidence удалено или изменено | `validate-project` `FAIL`; accepted history не переписывается |
| Evidence base revision изменился | assessment/acceptance preflight `STALE`; immutable source assessment не переписывается |
| Target, accepted level или accepted claim изменились после assessment | `STALE` с exact actual/expected context; zero acceptance mutation |
| Stale/other-base evidence закрывает принимаемый mandatory criterion | `STALE`; criterion не может авторизовать baseline acceptance |
| Maintenance plan has wrong level/target/acceptance/scope or future-stage work | strict validation failure; zero maintenance mutation |
| Maintenance start while Run/planning/Gate application/another maintenance is open | validation failure; existing route unchanged |
| Cancel after completed/observed product-changing Task or uncommitted Run drift | validation failure; no history rewrite and no automatic rollback |
| Level-up while maintenance WP is open | validation failure until terminal maintenance status |
| Level jump/downgrade | validation failure либо `TARGET_ALREADY_REACHED` |
| Interrupted transaction | full-new commit recovery либо full-old rollback по verified digests |

## 15. Audit invariants

1. Assessment is read-only with respect to product and does not execute commands.
2. Every accepted stage has one immutable report.
3. Approval and assessment digests are exact and replay-detectable.
4. Stage acceptance and next activation are crash-consistent full-write-set transactions.
5. Journal status, API result and canonical state describe the same terminal fact.
6. Recovery runs before any new Stage mutation and during `validate-project`.
7. Maintenance and level-up are distinct routes.
8. Accepted maturity cannot decrease in-place.
9. Future-stage prompts are never executable before activation.
10. Gate has no averaged acceptance score.
11. Prepared-project routing, assessment, planning, status/rendering и validation читают current target из Stage State.
12. `PROJECT` и `CURRENT_STATE` совпадают с Stage State; historical initial target в `PROJECT_INPUT_ACCEPTED` может отличаться после `level-up`.
13. Every Gate-closing ref resolves at one exact canonical evidence path and internal id/ref.
14. Every Gate-closing artifact is normalized, positive, provenance-bound, subject-mapped, kind-compatible and bound to the exact accepted product baseline.
15. Accepted Gate and Acceptance Report carry identical evidence refs and SHA-256 binding snapshots.
16. `validate-project` fails on evidence/source deletion or tampering after acceptance.
17. Ordinary runtime Task evidence is not automatically promoted into final Stage results; only a PASS governed preparation Task may trigger explicit kernel materialization for its exact missing subjects.
18. Last ordinary Task completion performs deterministic final-baseline readiness and creates no duplicate preparation WP.
19. Preparation tasks are current-stage-only and cannot implement future-stage features or change accepted scope.
20. `stage-status` и `prepare-stage-approval` дают public exact Gate/baseline contract без чтения private implementation.
21. Generated Stage approval всегда начинается как strict non-approved DRAFT; neither draft generation nor evidence candidates create a Decision/Acceptance.
22. Unchanged Gate/baseline даёт deterministic draft; product/Gate drift делает старый record stale.
23. `prepare-stage-approval` itself changes only the explicitly requested safe output file; runtime `STAGE_ACCEPTANCE_PREPARATION` is a separate governed lifecycle route.
24. Honest valid open formal review persists immutable BLOCKED history; malformed review performs zero mutation.
25. Gate blocker recovery uses `resume-stage-gate`, creates new revisions and never shares ordinary Task blocker/resume semantics.
26. Maintenance completion/cancel restores the prior route without invoking Stage acceptance or changing accepted maturity.
27. Open maintenance alone blocks level-up; completed/cancelled maintenance history does not.
28. Every maintenance executable artifact is exact-bound to the accepted stage and plan.
29. Cancel after completed or uncommitted product-changing work fails without deleting Tasks, Runs, reports or product files.
30. Exact start replay creates no duplicate WP/Task/Run/JIT artifacts.

## 16. Источники

Нормативная спецификация: [`../12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md`](../12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md). Contract paths and lifecycles: [`../registries/contracts.yaml`](../registries/contracts.yaml) и [`../registries/statuses.yaml`](../registries/statuses.yaml).

## PH‑F02 — subject-specific Stage Gate proof (2026-10-24)

This patch closes the **semantic Gate evidence** portion of v0.5.0 only; it does not implement the deferred PH‑F03 active-stage planner. `complete` of a Stage-acceptance preparation Task does **not** infer Gate PASS from generic Python commands or a no-change verification. Instead, every mandatory Gate subject requires its own independent, immutable normalized `EVD-*` artifact and the additional `details.semantic_proof` contract. The record is exact-bound to the subject, kind, source and final product-tree baseline; existing source and EVD digests are checked on every Gate review.

Proof methods depend on kind: `DOCUMENT_REVIEW` for actual architecture/startup/limitations/permitted-use and related documents, `EXECUTED_TEST` for selected test execution, `OPERATOR_VERIFICATION` for accountable manual or review records, and `EXTERNAL_SOURCE` for genuinely supplied evidence with issuer/origin. A proof names coverage, individual performed checks, and the pinned source ref. An ordinary `PASS` from `py_compile`, generic `pytest`, or any unspecified verification command is **not** enough to prove an unrelated criterion. An external record without independent source provenance is not a candidate. A human must still validate **semantic sufficiency** before formal approval; SHA-256 verifies integrity, not the truth of claims.

The supported fail-closed continuation is:

1. Complete the ordinary Stage Tasks; execute the bounded `STAGE_ACCEPTANCE_PREPARATION` Task through `next → verify → complete` if Gate readiness identifies missing subjects.
2. If authentic subject evidence is still absent, the Gate persists `BLOCKED` with `RESOLVE_STAGE_GATE`. No fake PASS evidence is minted and repeating the same completed, still-unproven preparation does not create another Task.
3. An accountable operator supplies actual product/document, selected-test, operator-review, or external source artifacts and the corresponding immutable normalized `EVD-*` records at their canonical `.harness/evidence/<EVD-ID>.yaml` paths. Source files are referenced with project-relative paths and SHA-256 digests; reviewed documents may be pinned in `.harness/operator/SOURCES/`. Historical artifacts are never rewritten.
4. Run `python project-harness.py resume-stage-gate --project <root>`. After every mandatory subject has compatible final-baseline proof, the Gate transitions to `VERIFYING`; otherwise it stays blocked with a specific gap/recovery route.
5. Run `prepare-stage-approval` and submit an independent **formal** reviewed Stage decision through `accept-stage`. A draft/candidate, even if exact-bound, never approves automatically.

`details.semantic_proof` is an object with `subject_ref`, `kind`, `status: PASS`, `method`, `coverage` (specific, nonempty description), `source_ref` (one of `source_bindings[].ref`) and `checked_items` (list of concrete checks). For `EXECUTED_TEST`, add `test_ref`, and bind an independent `test_execution` source recording the same exact subject and test ref, a selected command containing `test_ref`, exit code zero, executed checks and a PASS result. For `OPERATOR_VERIFICATION`, bind an `operator_verification` document recording actor, exact subject, checks and PASS. For `EXTERNAL_SOURCE`, use `EXTERNAL_EVIDENCE_IMPORT`, source `external_evidence` with exact subject/issuer/PASS, and `provenance.details.issuer` plus `.origin`. For `DOCUMENT_REVIEW`, bind a concrete substantive product document or an operator-supplied reviewed document (not a generic `.harness/reports/` result). Architecture, startup, limitations and permitted-use documents have basic kind-specific content checks. Never use a general verification report as a document or external evidence source.

`BASELINE` acceptance / Brownfield assessment remain independent read-only governance operations. Accepted history, strict positive-only Gate semantics, applicability checks, exact canonical refs, transactions and stage fences are unchanged. The public next-stage planner has subsequently been implemented in PH‑F03. This PH‑F02 historical explanation records only the Gate proof scope; see the PH‑F07 [operator runbook](../08_Distribution/04_Operator_Runbook_v0.5.0.md) for the current tested operator route.

