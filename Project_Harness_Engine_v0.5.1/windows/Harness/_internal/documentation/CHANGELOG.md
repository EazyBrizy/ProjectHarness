## PH-LW-06 — 2026-11-07 (WIP / NOT RELEASED)

Добавлены typed опрос, actual questions/readiness, отдельный browser GPT_PREPARATION template, JSON envelope v2, ограниченные export parts с hashes, policy/consent, preview/diff/commit/cancel/recovery и unverified provenance. UNKNOWN connectivity/documentation и blocking unknowns больше не дают READY_FOR_HANDOFF; UNSURE сохраняет WAITING_DECISION. Formal approvals PH-LW-07 и automatic executor не включены. Глава 13 Local Web описывает контракт и границы; точные результаты сохраняются в новом PH_LW_06_TEST_REPORT.md.

## Windows manual migration remediation — 2026-11-07 (WIP / NOT RELEASED)

Добавлена глава 12 Local Web: Windows fsync миграции, partial-copy/read-only cleanup, real process-exit recovery, ограничения symlink и Linux-only suites. Это дополнение к PH-LW-05, не следующий функциональный этап; полная поставка не принята.

## Windows HTTP retest PH-LW-04/05 — 2026-11-07 (WIP / NOT RELEASED)

Исправлены project GET, HTTP replay admission, malformed action/CSRF, duplicate multipart fields, snapshot ancestor junction checks, raw ZIP budget, source UI busy state и Windows transaction fsync. Дополнены реальные Waitress/Edge/NTFS tests и воспроизводимые PowerShell 5.1/7 CI scripts с точным учётом skips. Прежние reports и normative contracts сохранены; полный release не объявляется. См. новый acceptance report и главу 11 Local Web.

## PH-LW-04 — 2026-11-03 (0.5.1 WIP, not released)

Документирован отдельный localhost-only server/session bootstrap, HTTP route allowlist, CSP/CSRF, WSGI limits, static UI shell и запуск `project-harness ui`; прежняя PH-LW-03 service/manual/auto NO-GO граница сохранена. Native Windows/browser/Podman acceptance не заявляется без фактического прогона.

## PH-051-11 — operator docs and Podman security validation (2026-10-29, WIP)

- Согласованы текущие public `executor-doctor`/`execute-current`/migration, wheel/source/bundled entrypoint, GPT preparation template, operator runbook, strict ADP/SBX examples и fail-closed network/secret/debug limitations.
- Введена воспроизводимая Podman security matrix с честным `NOT TESTED / NO GO` без non-root Podman и pinned image; unit mocks не засчитываются как OS аттестация.
- Выявлен pre-existing `prepare` blocker (`LOCAL_AUTOMATIC` → `AUTOMATIC_EXECUTOR_NOT_IMPLEMENTED`), не обойдён изменением signed PROJECT_LOCK. Он отражён в отчёте как внешний scope blocker PH-051-12.
- Исправлено одно прямое нарушение source `doctor` packaging smoke: обход дерева manifest исключал **все** `MANIFEST.sha256`, даже nested documentation manifest, который был включён в root manifest; теперь исключается лишь root manifest.
- Это **не** PH-051-12 release/GO; v0.5.0 Stage/Gate/Brownfield/maintenance и последние PH-051-01..10 contracts не менялись.

## 2026-10-26 — PH-051-10 миграция, orphan и cleanup (v0.5.1 WIP / NOT RELEASED)

- Реализован `MIG-ENGINE-0.5.0-TO-0.5.1` для persisted Project Instance: проверенный staged sibling swap, durable recovery pre/post commit, safe `MANUAL_HANDOFF` default с null profiles/network NONE, schema7 и exact registry locks; accepted input, manual Runs и Stage histories immutable.
- Новый `execution_origin` на новых manual/automatic Run records, signed cleanup receipt, безопасное прекращение rootless Podman containers и проектно-ограниченная проверка orphan labels; старые incomplete Run partial outputs не используются для retry.
- Interrupted apply journal reconciled до recovery/quarantine; post-commit cleanup idempotent без redispatch. Real Podman security matrix всё ещё NOT RUN; PH-051-11/12 GO gate остаётся будущим.

## 2026-10-26 — PH-051-09 public governed automatic runtime (v0.5.1 WIP / NOT RELEASED)

- Added bounded project-scoped `executor-doctor` and `execute-current` CLI/Python APIs, current READY Task/Run phase journal, failure reason/status envelopes and read-only automatic/manual continuation in `next`/`status`/`stage-status`.
- Composed exact ADP/SBX Codex-in-Podman dispatch, independent SANDBOXED verifier, PH-051-08 committed apply/evidence and explicit/opt-in automatic Task completion. Validated Run/Apply Evidence binding before completion; preserved formal Stage Gate acceptance.
- Strictly reject manual automatic opt-in, unsupported egress/approval/debug overrides, missing sandbox doctor, secret leaks, invalid result, verification FAIL, write-scope/baseline mismatch and stale replay. No host fallback; unresolved crash/orphan recovery is PH-051-10.
- Integration Podman transport double does not count as a real container security test. Rootless Podman is unavailable on the packaging host; release remains NO GO pending PH-051-11/12.
- Detail: `05_Updates/12_Governed_Automatic_Run_and_Public_CLI_v0.5.1_WIP.md`.

## 2026-10-26 — PH-051-08 validated diff, secret scan and crash-consistent apply (0.5.1 WIP / NOT RELEASED)

- Implemented a bounded host-kernel `project_harness.apply` service; exact actual-vs-Task scope, expected artifacts, independent sandbox verification and normalized Run identity must agree before any canonical product write.
- Reject unsafe product paths/types/modes, stale baseline and literal secret leaks in changed files, Agent Result, bounded logs and verification diagnostics; no recursive copy or host executor fallback.
- External per-Run durable journal/backups, atomic same-directory file replacement, crash rollback/recovery and immutable Apply Evidence `EVD-APPLY-*` with signed control-plane boundary. Post-commit cleanup failure is not mislabeled rollback.
- No public `execute-current`, automatic completion, migration/orphan recovery or real Podman security GO; see `05_Updates/11_Validated_Diff_and_Crash_Consistent_Apply_v0.5.1_WIP.md`.

## 2026-10-26 — PH-051-06 exact Agent Result, secret ENV refs and bounded logs (0.5.1 WIP)

- One fixed `/output/agent-result.json`: reject unsafe file type, path, owner/mode, hardlinks, oversize, invalid UTF-8/JSON/schema or wrong current Run/Task.
- Kernel-published immutable Agent Result/ART metadata and bounded/redacted stdout/stderr, with control-plane fence; agent exit 0 alone is not independent PASS.
- Allowlisted `ENV:NAME` secret resolution, ephemeral protected Podman env-file, exact-value leak rejection in agent result/logs and read-only scan helper for later diff apply.
- No public automatic `execute-current`, no independent verifier/apply and no real Podman security acceptance; version remains WIP / NOT RELEASED. See `05_Updates/10_Exact_Result_Channel_v0.5.1_WIP.md`.

## 2026-10-26 — PH-051-05 Local Codex CLI Adapter (0.5.1 WIP)

- Bound ACTIVE CODEX_CLI_LOCAL ADP and ROOTLESS_PODMAN SBX through exact profile
  refs/digests in PROJECT_LOCK, current disposable Run/JIT argv, sandbox-only
  doctor/dispatch and bounded stdin/timeout/exit classification.
- Host environment/secret forwarding fails closed; result acceptance/verification,
  product apply, public CLI activation and formal release remain deferred.
- No real Podman security or Codex CLI flags validated in this environment;
  see `05_Updates/09_Local_Codex_CLI_Adapter_v0.5.1_WIP.md`.

## 2026-10-25 — PH-051-04 disposable execution root and control projection (0.5.1 WIP)

- Signed `EXECUTION_ROOT_PREPARED` journal boundary keeps `validate-project` PASS while rejecting prior tampering; product hardlinks are refused.

- Added per-Run product-only byte snapshots outside the canonical project with exact current Run/Task/JIT and source baseline binding.
- Read-only seven-file control projection, metadata-only project-local `EXECUTION_BINDINGS`, and export exclusion; unsafe links, FIFO, staleness and replay tampering fail closed.
- No Codex invocation, verification, apply, public automatic CLI or real Podman isolation acceptance; v0.5.1 remains WIP / NOT RELEASED.
- See `05_Updates/08_Disposable_Execution_Root_v0.5.1_WIP.md`.

## 2026-10-25 — PH-051-03 Rootless Podman runner and fail-closed self-tests (0.5.1 WIP)

- Added one `ROOTLESS_PODMAN` sandbox runner with strict immutable-image, disjoint mounts and bounded Podman-only process contract.
- `doctor` requires *actual* rootless Podman, pinned image and OS self-tests (UID, mounts, caps/NNP, network, cgroups, executable, termination); mock PASS is not isolation acceptance.
- No Podman is available in the build environment and real security integration is **NOT RUN / NO GO**. Egress stays blocked and no automatic public CLI route is added.
- See `05_Updates/07_Rootless_Podman_Sandbox_v0.5.1_WIP.md`; prior v0.5.0 accepted records remain unchanged.

## 2026-10-25 — PH-051-02 executor protocol and fake CLI (0.5.1 WIP)

- Added a sandbox-only Python `ExecutorAdapter` / single `CODEX_CLI_LOCAL` adapter
  with exact argv-template validation and deterministic preliminary failure mapping.
- Added fake CLI test scenarios without enabling any public automatic execution.
- No host process invocation, real Podman isolation, automatic apply or Stage
  runtime changes. See `05_Updates/06_Executor_Protocol_v0.5.1_WIP.md`.

## 2026-10-25 — PH-051-01 contracts and execution policy (0.5.1 WIP)

- Added `PROJECT_INPUT@4` safe manual execution defaults, schema7 locks with null profile bindings, exact profile contract schemas and `SBX` lifecycle.
- Resolved contract-catalog collision by `5 → 6` (normative v0.5.1 text states `4 → 5`); see `05_Updates/05_Execution_Policy_Contract_v0.5.1_WIP.md`.
- Automatic runtime/sandbox execution remains disabled; v0.5.0 accepted history stays untouched.

## 2026-10-25 — PH-F08 final integration acceptance / release packaging

- Проверены 14 сценариев I-01–I-14 и все 168 source regression/e2e тестов (включая 166 прежних); подготовлены согласованные Engine/Documentation ZIP, манифесты и тестовый отчёт.
- Сохранены публичные Stage/Gate/level-up/maintenance и Brownfield маршруты, strict semantic evidence и подтверждённые ограничения v0.5.0; новый runtime функционал не добавлен.
- Операторские шаги приведены в `08_Distribution/05_PH_F08_Release_Acceptance.md`; реальные тестовые результаты — в `PH_F08_TEST_REPORT.md` архива движка.

## 2026-10-24 — PH-F06 maturity / Brownfield / maintenance integration

- Preserve supplied normalized semantic proof and immutable source bindings in the public maturity-evidence import path; reject invalid proofs before normalized import.
- Reject Stage acceptance/assessment during open same-level maintenance and new level-up decisions before the current target cycle is accepted and idle.
- Keep a clean reserved Run executable after read-only assessment through a narrow trusted phase; do not trust pre-existing control-plane tampering.
- Add public-CLI full Prototype-to-MVP, maintenance-to-Release-planning, Brownfield, negative and migration coverage. See `PH_F06_TEST_REPORT.md` and `PH_F06_LIFECYCLE_NOTES.md`.
- v0.5.0, existing schema/registry/transaction contracts and historical reports retained; no PH-F07/PH-F08 or later-version implementation.


## PH-F07 operator documentation — 2026-10-25 (0.5.0 remediation, not PH-F08 release)

- Published a single operator runbook connecting installation/doctor, documentation-first GPT intake, strict approvals, handoff, external Codex Task cycle, subject-specific Gate proof, Stage planning, target-reached/level-up, Brownfield maturity and same-level maintenance.
- Aligned source/wheel/test commands, exact draft/approval schemas, operator record locations and reject/recovery status behavior with the existing CLI/API.
- Corrected outdated text implying that any PASS Task verification proves all Gate evidence kinds or that valid handoff is already production implementation. No normative contract, schema, registry, production implementation or version change.
- Final PH-F08 release acceptance is out of this package.

## PH‑F02 — semantic Gate evidence hardening (2026-10-24)

- Documented proof methods, required source contracts, human review and `BLOCKED → resume-stage-gate → VERIFYING` recovery.
- Clarified that a no-op/generic PASS does not certify document, test or external evidence; PH‑F03 remains separate.

# Changelog Project Harness

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** VERSION HISTORY


## 0.5.0 PH‑F04 — runtime reachability and status validation — 2026-10-24

- `next` and `stage-status` report the real public CLI continuation at Stage boundaries, including two-step `prepare-active-stage-plan` / `plan-active-stage`, formal Gate review, Gate/Task blocker recovery, target-reached and maintenance routes.
- New `validate-project` runtime reachability check rejects fabricated/unreachable routes, mismatched Stage Plan/Gate, future-stage READY Tasks, and inconsistent Run/blocker bindings; user review and external safety recovery remain explicit prerequisites rather than silent auto-approvals.
- Preserved PH‑F02 proof requirements, PH‑F03 idempotent current-stage planner, v0.4.1 compatibility, stage transaction recovery, formal approvals and accepted history.

## 0.5.0 PH‑F01 — baseline regression matrix — 2026-10-23

- Added `PH_F01_INTEGRATION_MATRIX.md` with normative issue-ID coverage, I-01–I-14 scenarios, four deterministic test fixture descriptions, known PH‑F02/PH‑F03 expected RED and PH‑F04 deferred reachability diagnosis.
- Kept the v0.5.0 requirements and documented operator contracts unchanged; runtime semantic fixes are explicitly deferred.
- PH‑F01 is a **pre-release expected RED** state, not renewed engine acceptance. Engine test logs/reports are distributed in the Engine archive.

## 0.5.0 M-01 documentation update — 2026-08-20

### Added

- public governed `start-maintenance` and `cancel-maintenance` operator workflow;
- strict exact-bound maintenance plan/cancel contracts and examples;
- accepted-stage WP/Task/DAG/VFP/CTX/PPL/JIT lifecycle using the existing `next → verify → complete` runtime;
- immutable completion/cancellation reports, explicit previous-route restoration and terminal-only level-up unblocking.

### Changed

- removed the private-stub model and documented `MAINTAIN_CURRENT_STAGE` as a supported public route;
- clarified that maintenance preserves target, accepted level, Stage Acceptance Reports, accepted Stage Plan/Gate revisions and completed Runs;
- clarified fail-closed cancel semantics after completed/observed or uncommitted product-changing work, with no invented automatic rollback;
- distinguished same-level product maintenance from Harness Distribution Maintenance Change Packs.


## 0.5.0 Q-01/Q-02 documentation update — 2026-08-20

### Added

- deterministic final-baseline Gate-readiness lifecycle and governed `STAGE_ACCEPTANCE_PREPARATION` WP/Task flow;
- persisted `STAGE_GATE_BLOCKER` semantics, exact diagnostics and dedicated `resume-stage-gate` recovery;
- explicit distinction between malformed no-mutation approval failures and honest valid formal reviews that persist BLOCKED;
- current-stage-only preparation scope, idempotency, immutable revision history and operator workflows for both recovery branches.

### Changed

- final ordinary Task documentation no longer claims an unconditional direct transition to `VERIFYING`;
- Gate-related BLOCKED now routes to `RESUME_STAGE_GATE`, while `prepare-stage-approval` remains the read-only record generator for VERIFYING/current snapshots;
- clarified that the command `prepare-stage-approval` creates no Work Package, while the runtime readiness evaluator may create one governed preparation WP only for exact missing evidence.

## 0.5.0 U-01 documentation update — 2026-08-20

### Added

- self-contained Stage approval workflow `stage-status → prepare-stage-approval → add/review evidence and formal fields → accept-stage`;
- exact `stage-status` contract for Plan/Gate refs, revisions, digests, baseline, result counts, WPs, blockers and next operator route;
- strict deterministic `SCHEMA-STAGE-APPROVAL@1` DRAFT contract, safe output/`--force` semantics, public API and full generated example;
- evidence-candidate and unresolved-gap guidance with an explicit prohibition on automatic PASS/Decision/acceptance.

### Changed

- removed operator guidance that required manual digest calculation or reading private Gate implementation;
- documented stale-record rejection after product/Gate drift and the exact formal fields required before `accept-stage`;
- documented that the `prepare-stage-approval` command performs zero Stage/product mutation and itself does not create `STAGE_ACCEPTANCE_PREPARATION` work.

## 0.5.0 — 2026-08-18

Minor release: implementation levels and stage-aware progression.

### Added

- canonical `PROTOTYPE → ALPHA → BETA → MVP → RELEASE` registry with declarative criterion profiles;
- strict `PROJECT_INPUT@3` implementation section;
- Stage State, Stage Plans, Stage Gates, immutable Acceptance Reports and Maturity Assessments;
- `stage-status`, `assess-maturity`, `accept-stage` and `level-up` CLI routes;
- active-stage task/prompt fence and `STAGE_SCOPE_VIOLATION` classification;
- read-only Brownfield maturity assessment and baseline acceptance transaction;
- same-level maintenance route and target extension after `TARGET_LEVEL_REACHED`;
- explicit transactional migration from v0.4.1/schema 5;
- crash-consistent Stage transaction journal, immutable backups, deterministic recovery and committed-result replay;
- fault-injection conformance for canonical apply points, PREPARED/per-entry/COMMITTED journal failures, abrupt recovery, corruption/mixed-state blocking and level-up;
- `SCHEMA-GATE-EVIDENCE@1`, exact canonical `EVD-*` resolver and immutable evidence/source digest bindings for accepted Gates.

### Changed

- canonical schema is v6; statuses v5, contracts v5 and ID prefixes v2;
- planner creates outlines to target but detailed atomic work only for active stage;
- final Task of a stage leads to `VERIFYING`, not project `COMPLETED`;
- project execution terminal for the current cycle is `TARGET_LEVEL_REACHED`;
- future-stage plans are provisional and are recomputed from the accepted baseline;
- `validate-project` reconciles non-terminal Stage transactions before canonical validation and verifies Stage indexes, Acceptance, `CURRENT_STATE` and `NEXT_TASK` against the latest completed transition;
- derived render failure after commit is a recoverable warning, not a false transition failure.

### Fixed

- bound Brownfield baseline acceptance to the current product-tree digest, canonical Stage State target, previous accepted level, immutable accepted user claim and sequential candidate context;
- record freshness failures as new immutable `STALE` assessment revisions that preserve the source revision/tree and produce zero acceptance mutation;
- prevent stale or other-base evidence from closing accepted mandatory criteria and make multi-level baseline acceptance all-or-nothing for one exact current assessment;
- replaced Brownfield `assessment_ref` prefix-glob/latest fallback with exact canonical immutable revision resolution; `@1` cannot bind `@10`, and filename/envelope/internal id+revision/digest are verified before Stage mutation;
- made Stage Acceptance Reports persist the exact assessment ref returned by the resolver;
- made Stage State the sole prepared-project current target authority; synchronized PROJECT and CURRENT_STATE projections atomically during `level-up` while preserving immutable initial target in PROJECT_INPUT_ACCEPTED;
- made prepared-project maturity assessment, routing, status, rendering and validation consume the canonical Stage State target; external intake assessment still consumes current PROJECT_INPUT;
- prevented `ROLLED_BACK` journals from coexisting with fully committed canonical Stage state;
- prevented mixed Stage State, Acceptance Report, current indexes and `CURRENT_STATE` after interruption;
- made committed approval replay idempotent and rolled-back id reuse invalid.
- replaced string-only Gate evidence trust with fail-closed exact resolution, registry-kind, subject-mapping, provenance, positive-status and current-baseline checks;
- kept historical evidence readable while preventing legacy or unsupported-schema records from closing new Gates;
- persisted identical evidence ref/path/SHA-256 snapshots in accepted Gate and Acceptance Report, and made `validate-project` detect later evidence/source deletion or tampering;
- prevented runtime Task verification evidence from automatically claiming final Stage criteria or surviving product-tree changes as fresh evidence.

### Safety and compatibility

- implementation level never grants new product scope or runtime permissions;
- maturity assessment never executes repository commands automatically;
- `SATISFIED_BY_BASELINE` is restricted to Brownfield/Hybrid and requires exact assessment evidence;
- immutable v0.4.1 history and accepted stage baselines are preserved;
- downgrade requests are non-destructive and return target-already-reached semantics.

### Validation

- preserved v0.4.1 contract-hardening regressions;
- added registry, stage planning, Gate, maturity, migration, maintenance, level-up and crash-recovery conformance tests;
- release suite: 88/88 PASS across seven modules, including ten Brownfield freshness/context regressions and two CLI Brownfield reproductions.

## 0.4.1 — 2026-08-18

Patch release: contract hardening without a new user workflow.

### Added

- strict Draft 2020-12 `PROJECT_INPUT@2` schema and idempotent v1 → v2 migration;
- separate `brownfield_baseline` approval for Brownfield/Hybrid and immutable Decision record;
- canonical sensitivity classes `SECRET` and `REGULATED`, with `UNKNOWN` restricted to intake uncertainty;
- protected control-plane snapshots, exact Agent Result channel checks and chained phase-boundary journal;
- direct `migrate-project` route from engine v0.4.0/schema 4;
- normative implementation specification 23 and v0.4.1 migration guide.

### Changed

- successful Task status is `DONE`; successful Run status is `SUCCEEDED`;
- statuses registry is v4 and contracts registry is v3;
- canonical project schema is v5;
- Brownfield Baseline carries `accepted_by`, `accepted_at` and revision linkage;
- `verify` and `complete` require exact product digests relative to the last trusted phase boundary;
- new Run creation is blocked until a legacy Project Instance is explicitly migrated.

### Compatibility

- immutable v0.4.0 Task/Run records remain byte-for-byte unchanged;
- legacy `Task: COMPLETED` and `Run: COMPLETED` are reported through explicit compatibility mappings;
- repeated migration returns `NO_ACTION` only after current-state validation passes.

### Validation

- preserved all 14 v0.4.0 regression tests;
- added 30 contract-hardening and migration tests;
- release suite: 44/44 PASS.

## 0.4.0 — 2026-08-17

### Added

- executable Core engine for Browser GPT preparation and governed Codex handoff;
- external `START_INTAKE` workspace and deterministic `prepare`;
- formal Session, Architecture Baseline, Project Lock and generated skill index contracts;
- specification 22 for Browser GPT → Codex Handoff;
- `validate-project` for mutable post-handoff state;
- conformance fixtures for greenfield and brownfield.

### Changed

- initial questionnaire now runs only for a new Project Instance, not every process restart;
- bootstrap follows accepted baselines and Skill Gap Analysis rather than full skill authoring;
- Core/hardening dependencies are slice-specific;
- `PROJECT_LOCK` uses six exact canonical registry names, versions and digests;
- skills are resolved per project rather than regenerated per project;
- future compiled prompts are prohibited by the JIT handoff rule.

### Fixed

- pre-bootstrap storage cycle;
- stale registry filenames and versions;
- missing startup contracts;
- brownfield route storage alignment;
- ambiguity between immutable handoff validation and mutable project-state validation.

## 0.3.1 — 2026-08-07

Patch release after final documentation audit. No new product subsystem is introduced.

### Fixed

- renamed implementation packages to `WP-HARNESS-*` and reserved `HNS-REQ-*` for documentation requirements;
- synchronized Internal Operations with `registries/request_routing.yaml`;
- added missing lifecycle groups and corrected invalid example statuses;
- replaced unknown capability aliases and corrected Test Baseline prefix;
- normalized conflicting Brownfield, Parallel Batch, Project Definition, Task and Change Pack fields;
- added Request-level `idempotency_key` and transport mapping rule;
- added `registries/contracts.yaml` as canonical contract catalog;
- strengthened semantic validator and corrected Validation Report claims;
- normalized questionnaire assumption status and clarified that intake runs on the initial `PROJECT_START`, not every runtime restart.

### Changed

- split delivery into Core MVP and Hardening without removing later mechanisms;
- assigned owner roles, resolve-before gates and ADR outputs to open implementation decisions.

## 0.3.0 — 2026-08-06

Сквозная переработка Project Harness как единой пользовательской точки входа и implementation-ready системы управления ИИ-агентами.

### Added

- Request Class, Request Mode, Request и Request Plan contracts;
- единый public Result Envelope и ограниченный набор понятных статусов;
- Work Package для группировки пользовательского outcome и atomic Task hierarchy;
- JIT Prompt compilation только для READY task/run;
- exact documentation refs, stable section IDs и documentation impact;
- ADR materiality policy;
- artifact-producing dependencies и causal readiness;
- read/write resource sets для parallel batches;
- ambiguity policy с materiality, bounded question batches и reversible assumptions;
- recovery route contract без тупиковых состояний;
- Verification Profiles, Test Environment и Test Baseline contracts;
- pre-migrated test database template/isolated clone policy;
- Request Trace и correlation IDs;
- Technology Baseline and Technology Candidate contracts;
- Skill Registry, lifecycle and reuse-before-create policy;
- Codex Agent Adapter and structured agent result contract;
- PRODUCT, PROJECT_CONTROL и HARNESS_DISTRIBUTION maintenance planes;
- human-readable and machine-control documentation layers;
- machine-readable ID/profile/status/routing/capability registries;
- semantic documentation validation rules;
- brownfield onboarding with continuation, bug-fix, improvement and stabilization routes;
- mandatory documentation-first adaptive questionnaire;
- 21 detailed implementation specifications and one consolidated user/implementation guide;
- early walking-skeleton implementation roadmap.

### Changed

- ordinary user query no longer creates a development task;
- intents, lifecycle phases and kernel operations are no longer mixed in one enum;
- Prompt Bundle is generated on demand rather than for the whole roadmap;
- shared read-only contracts are allowed in parallel execution;
- Run is one immutable attempt; retry creates a new Run;
- `PARTIALLY_COMPENSATED` is compensation status, not Change Pack lifecycle status;
- testing is proportional to task type and risk;
- brownfield repository is inspected read-only before any mutation;
- project start questions are derived from documentation and limited to material gaps;
- maintenance changes cannot be mixed with product changes;
- implementation roadmap is vertical and causal instead of subsystem-only;
- profile lists and identifier examples are normalized through registries.

### Removed or deprecated

- separate canonical `Attempt` entity;
- `REQST`, `DECMP`, `ACTOR`, `PDF`, `CTXP`, `GRANT`, `LEASE`, `ECP` and other v0.2 aliases in new artifacts;
- `contract_set(A) ∩ contract_set(B) = ∅` as the sole parallelism rule;
- creation of ADR for every implementation task;
- automatic bulk compilation of future prompts;
- assumption that every task must have a code test;
- mixed-plane Change Packs;
- complex command-driven UX as the primary interface.

## 0.2.0 — 2026-08-02

Architecture revision introducing project-agnostic canonical model, greenfield/brownfield lifecycle, constraints, Prompt IR, Context Planning, adapters, capabilities, Run/Tool Invocation, evaluations and Change Packs. Historical details remain in [`MIGRATION_FROM_v0.1.0.md`](MIGRATION_FROM_v0.1.0.md).

## 0.1.0 — 2026-08-02

Initial architecture specification: distribution, engine, project-local instance, intake, architecture gate, requirements traceability, DAG/tasks, routing, context packets, state/evidence, updates, Git, security and MVP roadmap.

## PH‑F03 — governed next active-stage planner (2026-10-24)

- Added read-only `prepare-active-stage-plan` and governed `plan-active-stage`
  with strict `SCHEMA-ACTIVE-STAGE-PLAN-REVIEW@1` and exact context bindings.
- Each accepted-stage transition builds only the next Stage WPs, Tasks,
  dependency DAG, verification/context/prompt plans and first READY JIT.
- Documented accepted-scope fence, review of edited plans, stale/no-op behavior,
  idempotent commit replay and post-rollback draft renewal.
- PH‑F02 proof semantics, highest accepted level and immutable history are preserved;
  PH‑F04 onward remain separate remediation packages.
