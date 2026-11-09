## Windows manual migration remediation — 2026-11-07 (WIP / NOT RELEASED)

v0.5.0→v0.5.1 file fsync использует write-capable Windows descriptor. Partial copy и read-only staging cleanup исправлены без изменения source attributes, accepted history или automatic opt-in. Добавлены native manual/crash/recovery tests; symlink capability skips отделены от hardlink/malformed cases. См. новый manual remediation report; прежние отчёты сохранены.

## Windows HTTP retest PH-LW-04/05 — 2026-11-07 (WIP / NOT RELEASED)

Исправлены project GET, HTTP replay admission, malformed action/CSRF, duplicate multipart fields, snapshot ancestor junction checks, raw ZIP budget, source UI busy state и Windows transaction fsync. Дополнены реальные Waitress/Edge/NTFS tests и воспроизводимые PowerShell 5.1/7 CI scripts с точным учётом skips. Прежние reports и normative contracts сохранены; полный release не объявляется. См. новый acceptance report и главу 11 Local Web.

## PH-LW-05 — 2026-11-04 (0.5.1 WIP / NOT RELEASED)

Added safe Markdown/ZIP quarantine + immutable source snapshots, bounded ZIP/Windows path/UTF-8/CRC checks, governed `refresh_intake_sources`, service-owned intake and documented upload/preview/no-doc/recovery HTTP flows. Source updates reset provisional approvals but never rewrite accepted history. Targeted tests, regression and build evidence: `PH_LW_05_TEST_REPORT.md`. Native Windows and real HTTP browser security acceptance not asserted; automatic Podman/egress NO-GO preserved. No v0.6.x functionality added.

## PH-LW-04 — 2026-11-03 (0.5.1 WIP / NOT RELEASED)

- Added `project-harness ui` lazy optional Flask+Waitress launcher with prebound exclusive loopback socket and bounded WSGI limits, one-time CSPRNG fragment bootstrap, server session/CSRF/strict Host+Origin, CSP, static packaged HTML/CSS/JS. No automatic executor or browser terminal.
- Exposed read-only authenticated project catalog/status and bounded owned operation/artifact retrieval via LocalWebService. Existing service allowlist only; no direct `.harness` writes from web routes, no extra governance routes. Later forms remain disabled.
- Added HTTP/Waitress/browser negative tests and Windows 11 x64 NTFS CI entrypoint; running tests on host without pinned Flask/Waitress or native Windows must be reported NOT RUN (not fake PASS). Full v0.5.1 NO-GO unchanged.

## PH-LW-03 — manual Local Web application service (2026-11-02, v0.5.1 WIP)

- Introduced bounded `LocalWebService` and `OperationRequest`, opaque registered workspace/project IDs, exact read-only status/fingerprint/action availability, external catalog and digest-checked non-authoritative operation records.
- Added strictly allowlisted provisional draft-update API with one-file atomic mutation, draft approvals invalidation and schema/readiness revalidation; HTTP/UI still absent.
- Shared cross-process OS operation guard protects public manual, Task, Stage, maintenance and migration APIs in addition to existing nested Stage transaction lock.
- One local worker, durable idempotency keys, fail-closed stale/core conflicts, proof-bound reconciliation, no verification replay or host Codex fallback; Windows/NTFS and Podman security remain NOT TESTED/NO-GO.

## PH-051-11 — operator docs and Podman security validation (2026-10-29, WIP)

- Согласованы текущие public `executor-doctor`/`execute-current`/migration, wheel/source/bundled entrypoint, GPT preparation template, operator runbook, strict ADP/SBX examples и fail-closed network/secret/debug limitations.
- Введена воспроизводимая Podman security matrix с честным `NOT TESTED / NO-GO` без non-root Podman и pinned image; unit mocks не засчитываются как OS аттестация.
- Выявлен pre-existing `prepare` blocker (`LOCAL_AUTOMATIC` → `AUTOMATIC_EXECUTOR_NOT_IMPLEMENTED`), не обойдён изменением signed PROJECT_LOCK. Он отражён в отчёте как внешний scope blocker PH-051-12.
- Исправлено одно прямое нарушение source `doctor` packaging smoke: обход дерева manifest исключал **все** `MANIFEST.sha256`, даже nested documentation manifest, который был включён в root manifest; теперь исключается лишь root manifest.
- Это **не** PH-051-12 release/GO; v0.5.0 Stage/Gate/Brownfield/maintenance и последние PH-051-01..10 contracts не менялись.

## 2026-10-26 — PH-051-10 (v0.5.1 WIP / NOT RELEASED)

- Implemented crash-recoverable `MIG-ENGINE-0.5.0-TO-0.5.1` for existing Project Instances; strictly manual default, exact registry schema7, immutable accepted input/historical Runs/Stages.
- Added exact Project/Run-labeled rootless Podman orphan cleanup/termination; local secret transient files contained within the trusted execution root and never archived.
- Added Run `execution_origin`, immutable per-Run cleanup receipts, old partial result quarantine and retry blocking; interrupted apply journal recovered before retry, including post-commit verified cleanup without redispatch. No host fallback and no Stage maturity changes.
- Unit simulated Podman is not OS isolation proof: real rootless security tests remain NOT RUN and v0.5.1 release remains NO-GO before PH-051-11/12.

## 2026-10-26 — PH-051-09 public governed automatic runtime (v0.5.1 WIP / NOT RELEASED)

- Public `executor-doctor` / `execute-current` CLI and Python API for current READY Task only, signed Run phase status, next/status continuations and structured fail-closed failure codes.
- Compose exact ADP/SBX, rootless Codex CLI, immutable ART/log result, independent SANDBOXED verification, crash-consistent apply and Apply Evidence; optional AUTO_AFTER_PASS versus explicit complete, neither is Stage acceptance.
- Read-only failure for unsupported network/adapter overrides/manual opt-out; verified execution and Run retry preserve historical records. Project validator confirms actual PASS `validation_report` and sandbox Apply Evidence (legacy envelope bug corrected).
- PH-051-10 global orphan/recovery and PH-051-11/12 real Podman security/release acceptance are not implemented. Real rootless Podman NOT RUN; v0.5.1 NO-GO.

## 2026-10-26 — PH-051-08 validated diff, secret scan and crash-consistent apply (0.5.1 WIP / NOT RELEASED)

- Implemented a bounded host-kernel `project_harness.apply` service; exact actual-vs-Task scope, expected artifacts, independent sandbox verification and normalized Run identity must agree before any canonical product write.
- Reject unsafe product paths/types/modes, stale baseline and literal secret leaks in changed files, Agent Result, bounded logs and verification diagnostics; no recursive copy or host executor fallback.
- External per-Run durable journal/backups, atomic same-directory file replacement, crash rollback/recovery and immutable Apply Evidence `EVD-APPLY-*` with signed control-plane boundary. Post-commit cleanup failure is not mislabeled rollback.
- No public `execute-current`, automatic completion, migration/orphan recovery or real Podman security GO; see `05_Updates/11_Validated_Diff_and_Crash_Consistent_Apply_v0.5.1_WIP.md`.

## 2026-10-26 — PH-051-06 Exact result channel, secrets/logs (0.5.1 WIP / NOT RELEASED)

- Accept only exact single-link pre-created owner-only `/output/agent-result.json` (1 MiB, UTF-8, no duplicate JSON keys) matching `SCHEMA-AGENT-TASK-RESULT@1` and current Run/Task. Undeclared output and invalid types/modes are blocked.
- Kernel-owned normalized immutable ART + bounded/redacted log refs and exact `AGENT_RESULTS` copy; original v0.5.0 Run identity preserved, ART Run @1 projection only where needed.
- Resolve only pinned `ENV:NAME` secret refs; protected short-lived Podman env-file, literal leak detection in logs/result and read-only changed-file scanner for PH-051-08. No host environment dump or fallback.
- No independent verifier, diff/atomic apply, public automatic CLI or real Podman security GO. Earlier PH-051-05 reports/historical accepted artifacts preserved.

## 2026-10-26 — PH-051-05 Local Codex CLI adapter (0.5.1 WIP / NOT RELEASED)

- Bind one ACTIVE CODEX_CLI_LOCAL ADP + ROOTLESS_PODMAN SBX by exact PROJECT_LOCK
  refs/digests and current JIT/Task/disposable Run; no independent Run approval.
- Real Podman-only doctor/argv dispatch (without host shell/Codex execution),
  fixed sanitized env, CLOSED stdin, bounded timeout and nonoptimistic exit mapping.
- No public automatic CLI, result acceptance/verification/apply, or release gate;
  Podman/image/actual Codex flags NOT TESTED on this packaging host.

## 2026-10-25 — PH-051-04 disposable Run root (v0.5.1 WIP)

- Added standalone per-Run product byte snapshots and read-only seven-artifact control projection with exact Run/Task/JIT/baseline bindings.
- Reject unsafe/special files, symlink paths, stale/forged metadata and orphan/replay ambiguities; exclude execution binding metadata from handoff ZIP.
- No automatic executor, verification, apply, migration or release acceptance; Podman integration remains NOT RUN.

## 2026-10-25 — PH-051-03 Rootless Podman runner and OS doctor (0.5.1 WIP; NOT RELEASED)

- Added one `ROOTLESS_PODMAN` sandbox package with strictly validated active
  SBX profile, digest-pinned image and disjoint disposable mounts.
- Podman-only, explicitly local (`--remote=false`) invocation with sealed
  non-root UID, readonly root, caps drop, NNP, cgroup limits, network none,
  tmpfs HOME, bounded process output/time and no host fallback.
- Real doctor checks rootless + image availability and performs container
  security, kernel cgroup/network, binary and termination self-tests.
- Build host has no real rootless Podman: mandatory OS security integration
  **NOT RUN**; no public auto runtime/CLI activation and NO-GO for v0.5.1.
- Registry, project_input@4, Stage/Gate, Brownfield, maintenance and manual
  lifecycle unchanged; see PH_051_03_TEST_REPORT.md.

## 2026-10-25 — PH-051-02 (0.5.1 WIP; NOT RELEASED)

- Minimal `ExecutorAdapter` protocol and `CODEX_CLI_LOCAL` static argv validator;
  sandbox-only dispatch, fail-closed doctor and preliminary nonoptimistic result mapping.
- Deterministic fake Codex CLI fixtures and 20+ negative/focused unit tests.
- No public automatic CLI command, host execution, OS isolation claim,
  full result-channel validation, independent verification or apply.
- Prior PH-051-01 contracts, manual v0.5.0 lifecycle and historic artifacts unchanged.

## 2026-10-25 — PH-051-01 (0.5.1 WIP; NOT RELEASED)

- Strict `PROJECT_INPUT@4` execution policy with safe manual default and conservative v3 reading;
  old accepted input/Stage reports/completed Runs remain immutable.
- Contract schemas: executor-profile (reuses ADP), dedicated sandbox-profile (SBX),
  immutable execution-result (ART) and apply-evidence (EVD), package-resource mirrors.
- Registry versions `id_prefixes=3`, `statuses=6`, `contracts=6` (real existing v0.5.0 was contracts=5).
- Metadata/schema 7 locks for new manual handoffs; old v0.5.0 lock read/manual continuity.
- No execution API, no CLI agent process, no OS-sandbox claims; release needs PH-051-12.

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

## 2026-10-24 — PH-F05 source/workspace safety and acceptance
- Reject overlapping intake workspace and any source, repository or initial input before a force reset.
- Add independent Greenfield documented/undocumented handoff, target/sensitivity/approval, repeat-intake and path-safety tests.
- Clarify external-workspace usage in bundled GPT instructions and operator documentation.
- No maturity, Stage Gate, planning, maintenance or approval policy changes.

# Changelog

## 2026-10-25 — PH-F08 final integration acceptance and release assembly

- Added two independent public-CLI e2e acceptance tests, the I-01–I-14 release matrix, complete regression log and distribution smoke results; no production-runtime change.
- Retained executable `bin/project-harness` permissions when rebuilding the ZIP; clean full suite PASS after correcting extraction-only mode loss. The initial permission-error run remains in PH-F08 logs.
- Synchronized Documentation, release manifests, version 0.5.0 and historical control-plane contracts; no v0.5.1/v0.6.x scope.


## 2026-10-24 — PH-F04 scoped runtime/status/validator hardening

- Real public continuation in `next` / `stage-status` and explicit maintenance/Gate/Task phase distinction.
- `validate-project` rejects dead-end boundary routes and inconsistent Stage/Gate, Run, blockers and future-stage Task bindings without treating human review as a defect.
- PH-F02 evidence, PH-F03 planner, accepted reports, migration and transactions preserved.


## 0.5.0 PH-F02 semantic Gate evidence — 2026-10-24

- Replaced generic PASS evidence promotion with fail-closed exact subject-specific document, selected-test, operator-review and external-source contracts.
- Readiness names the proof method for each missing Gate subject; repeated unproven preparation persists BLOCKED and follows `resume-stage-gate`.
- Formal acceptance and candidate inventories enforce identical semantic eligibility, baseline and immutable source digests.
- Updated positive/negative Gate fixtures to exercise actual subject-specific sources; PH-F03 planner remains deferred.


## 0.5.0 PH-F01 regression baseline — 2026-10-23

- Added isolated Greenfield MVP and Brownfield input fixtures, plus materialized accepted-Prototype and TARGET_LEVEL_REACHED states through supported public APIs.
- Added intentionally RED public planner-continuation regressions and semantic Gate evidence negative tests, alongside initial integration matrix and actual test report.
- Existing engine behavior, CLI/API, runtime semantics, schema and registry remain unchanged. PH-F02 (proof semantics) and PH-F03 (active-stage planning) are **NOT** implemented.
- Interim RED is intentionally not a v0.5.0 release pass. Original 117-test suite remains green; see `PH_F01_TEST_REPORT.md`.


## 0.5.0 M-01 same-level maintenance update — 2026-08-20

### Added

- public `start-maintenance --project <root> --plan <record>` and `cancel-maintenance --project <root> --approval <record>` CLI/API operations;
- strict `SCHEMA-MAINTENANCE-PLAN@1` and `SCHEMA-MAINTENANCE-CANCEL-APPROVAL@1` contracts with `additionalProperties: false` throughout;
- governed accepted-stage Decision/WP/Task/DAG/VFP/CTX/PPL/JIT materialization, maintenance indexes/current state, immutable completion/cancellation reports, and previous-route restoration;
- focused lifecycle coverage for start, execution, completion, level-up blocking/unblocking, safe cancel, fail-closed product-change cancel, stale/wrong/future bindings, idempotency, and immutable-history preservation.

### Changed

- replaced the private `create_maintenance_work_package()` stub with a supported bounded same-level route;
- runtime scheduling, prompt compilation, snapshots, capability grants, Run Plans, verification and Task Reports now retain exact `MAINTAIN_CURRENT_STAGE` binding;
- final maintenance Task closes maintenance instead of triggering Stage Gate readiness;
- `level-up` blocks only open maintenance WPs and permits terminal `COMPLETED`, valid `CANCELLED`, or `SUPERSEDED` history.

### Safety boundary

- maintenance never changes canonical target, `highest_accepted_level`, accepted Stage Plan/Gate/Acceptance revisions, or completed Run history;
- cancellation after completed/observed or uncommitted product-changing work is rejected without history rewrite or invented automatic rollback;
- no Change Packs, Git, deployment, executor, or future-stage functionality was added.

### Validation

- focused maintenance suite: 15 tests plus 4 subtests PASS;
- complete release matrix: 117/117 PASS across 11 modules;
- CLI maintenance smoke: normal completion and formal pre-execution cancellation PASS, including byte-identical Stage State, Acceptance Reports and pre-existing completed Runs;
- documentation validator: 36 checks, 0 errors, 0 warnings; source/embedded documentation trees are byte-identical.

## 0.5.0 Q-01/Q-02 maintenance update — 2026-08-20

### Added

- deterministic final-product-tree Gate-readiness evaluation after the last ordinary mandatory Task;
- governed, idempotent `STAGE_ACCEPTANCE_PREPARATION` Work Package/Task route with Context, Prompt and Verification Plans, DAG, current-task/index updates and exactly one first JIT bundle;
- kernel materialization of immutable exact-baseline outcome/criterion/hard-constraint/profile-control evidence after PASS verification;
- persisted `STAGE_GATE_BLOCKER` records and the dedicated `resume-stage-gate --project <root>` CLI/public API recovery route;
- focused regressions for preparation creation/idempotency/completion, malformed no-mutation, honest Gate BLOCKED persistence, both recovery branches, future-stage exclusion and target acceptance.

### Changed

- completion of the last ordinary Task now evaluates final-baseline evidence instead of unconditionally moving directly to manual Gate review;
- a structurally valid formal approval containing mandatory `UNKNOWN`, `PARTIAL` or `FAIL` conclusions atomically persists new BLOCKED Gate/Plan revisions, exact diagnostics and project route `RESOLVE_STAGE_GATE`, without Acceptance Report or next-stage activation;
- Gate recovery creates new immutable revisions and returns either to ACTIVE evidence preparation or VERIFYING formal review; ordinary Task blocker/resume semantics remain separate;
- accepted Gates now persist the complete strict outcome, criterion, hard-constraint and profile-control result sets used by the formal approval.

### Safety

- preparation Tasks are limited to accepted current-stage verification, tests and bounded documentation/limitations/permitted-use evidence; future-stage features and accepted-scope expansion are forbidden;
- malformed approval records and invalid evidence remain validation failures with zero state mutation;
- readiness does not create duplicate preparation work and does not create a preparation Work Package when compatible final-baseline evidence already closes every evidence need.

### Validation

- complete regression/conformance/fault-injection matrix: 110/110 PASS across ten modules;
- focused Q-01/Q-02 lifecycle tests: 5/5 PASS, including malformed no-mutation and both Gate recovery branches;
- end-to-end CLI smoke: preparation → persisted BLOCKED → recovery → `TARGET_LEVEL_REACHED`, followed by `validate-project` PASS;
- documentation validation: 36 checks, 0 errors, 0 warnings.

## 0.5.0 U-01 maintenance update — 2026-08-20

### Added

- `prepare-stage-approval --project <root> --output <path> [--force]` and the public `prepare_stage_approval()` API;
- public `product_baseline_revision()` and enriched `stage_status()` exact Gate/baseline context;
- strict `SCHEMA-STAGE-APPROVAL@1` with explicit `DRAFT`/`APPROVED` states and `additionalProperties: false` throughout normative record levels;
- deterministic result skeletons for outcomes, level criteria, hard constraints and profile controls, plus WP/blocker snapshots, permitted-use template, evidence candidates and unresolved gaps;
- focused U-01 tests and a schema-valid generated draft example.

### Changed

- the supported operator cycle is now `stage-status → prepare-stage-approval → formal review/fill → accept-stage`;
- strict generated approvals are exact-bound to current Plan/Gate refs, revisions, paths, digests, product baseline, result definitions, WP/blocker snapshot and preparation fingerprint;
- Stage acceptance rejects stale generated records after product or Gate drift and validates formal result closure before mutation.
- strict outcome/profile-control evidence is validated pre-mutation without being misclassified as unrelated global Gate evidence in the persisted v0.5.0 Gate snapshot; post-acceptance `validate-project` remains PASS.

### Safety

- the `prepare-stage-approval` command never approves, creates a Decision/Acceptance Report, changes Stage/Gate state, executes repository commands, modifies the product tree or creates a Work Package;
- all generated mandatory statuses remain `UNKNOWN`; evidence candidates are hints only;
- output is limited to outside the project or `.harness/operator/APPROVALS/`, and existing files require explicit `--force`.


## 0.5.0 — 2026-08-18

Minor release adding a governed implementation-level lifecycle.

### Added

- canonical `PROTOTYPE → ALPHA → BETA → MVP → RELEASE` registry with declarative criteria profiles;
- strict `PROJECT_INPUT@3` implementation decision fields;
- Stage State, Stage Plans, Stage Gates, immutable Acceptance Reports, Maturity Assessments, state history, and transaction records;
- CLI routes `stage-status`, `assess-maturity`, `accept-stage`, and `level-up`;
- active-stage Task/Prompt fence and `STAGE_SCOPE_VIOLATION`;
- read-only Brownfield/Hybrid maturity assessment and governed baseline acceptance;
- explicit transactional migration `MIG-ENGINE-0.4.1-TO-0.5.0`;
- eight implementation-level conformance tests, five canonical-target regressions, five exact-assessment-ref regressions and ten Brownfield freshness/context regressions in addition to preserved regressions;
- deterministic Stage transaction journals with complete write-set metadata, immutable backups and automatic recovery;
- focused fault-injection coverage for every acceptance apply point, journal failures, abrupt termination, repeated recovery, idempotency, corruption blocking and level-up.
- normalized immutable `SCHEMA-GATE-EVIDENCE@1`, exact canonical `EVD-*` resolver, accepted evidence binding snapshots, and focused Gate evidence trust regressions.

### Changed

- canonical project schema is 6 and preparation input is `PROJECT_INPUT@3`;
- registry versions are id prefixes 2, statuses 5, contracts 5, and implementation levels 1;
- planner creates stage outlines through the target, but detailed executable work only for the active stage;
- completion of the final active-stage Task transitions to `VERIFYING`, not project `COMPLETED`;
- accepted target status is `TARGET_LEVEL_REACHED`;
- future stages are recomputed from each accepted baseline rather than precompiled;
- `validate-project` reconciles pending Stage transactions before semantic validation and verifies current canonical files/indexes against terminal journals;
- post-commit rendering returns a recoverable warning instead of turning committed canonical state into a false command failure.

### Fixed

- bound Brownfield baseline acceptance to the current product-tree digest, approval baseline, canonical Stage State target, previous accepted level, immutable accepted user claim and sequential candidate context;
- return structured `STALE` results and write a new immutable validation revision while preserving the source assessment/tree and making zero acceptance mutation;
- reject stale or other-base evidence for accepted mandatory criteria and make multi-level baseline acceptance all-or-nothing for one exact current assessment;
- replaced Brownfield `assessment_ref` prefix matching with exact canonical immutable revision resolution, so `@1` can never bind `@10`;
- validate exact assessment filename, sole envelope, internal id/revision, canonical digest format and exact file bytes before Stage mutation, then persist the resolver's exact ref in every baseline Acceptance Report;
- made Stage State the sole current target authority for prepared projects while preserving `PROJECT_INPUT_ACCEPTED` as immutable initial-target history;
- synchronized Stage State, PROJECT and CURRENT_STATE target projections in the same `level-up` transaction and made validation reject projection divergence;
- made prepared-project assessment, routing, status and rendering consume the Stage State target while external intake continues to consume current PROJECT_INPUT;
- removed the path that could report an API error and `ROLLED_BACK` journal after canonical files had already committed;
- eliminated best-effort mixed Stage State/Acceptance/index outcomes after apply interruption;
- made exact committed approval replay idempotent and blocked reuse of a rolled-back transaction id.
- rejected dangling, legacy, malformed, wrong-kind, wrong-subject, stale, failed/blocked, unprovenanced, source-tampered and duplicate-conflicting Gate evidence refs;
- bound every Gate-closing artifact to the exact current product baseline and criterion-specific `required_evidence_kinds`;
- persisted identical evidence ref/path/SHA-256 snapshots in accepted Gate and Acceptance Report and made `validate-project` detect later evidence/source deletion or tampering;
- kept historical evidence readable without allowing it to close a new Gate, and treated explicit unsupported schema versions as invalid rather than legacy;
- normalized runtime verification/safety evidence while preventing early Task evidence from automatically claiming final Stage criteria.

### Safety and compatibility

- implementation level changes depth, never accepted product scope or agent permissions;
- assessment does not automatically execute repository commands;
- `SATISFIED_BY_BASELINE` is restricted to Brownfield/Hybrid and exact assessment evidence;
- accepted stages and v0.4.1 immutable history are preserved;
- target downgrade/equal requests are non-destructive;
- same-level maintenance remains separate and blocks level-up while open.

### Validation

- regression/conformance and fault-injection tests: 88/88 PASS across seven modules;
- documentation validation: 36 checks, 0 errors, 0 warnings;
- source distribution, wheel, embedded runtime, demo handoff, migration, and archive integrity are covered by release evidence.

## 0.4.1 — 2026-08-18

Patch release; the v0.4.0 user workflow was not expanded.

### Added

- strict `PROJECT_INPUT@2` Draft 2020-12 schema and dependency-free matching validation;
- idempotent input migration and explicit project migration `MIG-ENGINE-0.4.0-TO-0.4.1`;
- separate Brownfield/Hybrid `brownfield_baseline` approval and immutable Decision;
- six canonical sensitivity classes plus temporary `UNKNOWN` intake state;
- protected control-plane snapshots, exact Agent Result channel, phase-boundary journal, and tamper blocking;
- 30 contract-hardening/migration tests in addition to 14 preserved regressions.

### Changed

- successful Task status: `DONE`;
- successful Run status: `SUCCEEDED`;
- canonical schema: 5;
- statuses registry: 4;
- contracts registry: 3;
- verify/complete bind to exact product digests and protected state.

### Compatibility

- immutable v0.4.0 Task/Run history is not rewritten;
- explicit legacy status mappings are reported;
- a new Run is prohibited until legacy Project Instance migration completes.

### Validation

- unit/conformance suite: 44/44 PASS;
- documentation validator: 36/36 PASS;
- source, wheel, and embedded runtime smoke checks included in release evidence.

## 0.4.0 — 2026-08-17

- Implemented the executable Core engine for Browser GPT preparation and Codex handoff.
- Separated `START_INTAKE` and `BOOTSTRAP_PROJECT`.
- Added external provisional workspace and read-only Brownfield inventory.
- Formalized Session, Architecture Baseline, `PROJECT_LOCK`, and generated skill index.
- Added semantic input, explicit approvals, Task DAG, JIT prompt/context compilation, embedded runtime, scope verification, Blocker/resume, safe ZIP handling, and wheel distribution.

## 0.5.0 PH-F03 next active-stage planner — 2026-10-24

- Added public `prepare-active-stage-plan`/`plan-active-stage` CLI and Python APIs,
  strict reviewed-plan schema and exact current-state/acceptance/scope/digest bindings.
- Compiles atomic current-stage-only Task/WP/DAG/verification/context/prompt plans
  and single first READY JIT from an immutable accepted Stage baseline.
- New active Plan/Gate revisions, indexes, projections and NEXT_TASK use existing
  crash-consistent Stage journal; committed replay is idempotent and after
  rollback the fresh reviewed draft uses a new transaction ID.
- Safety: rejects stale records, active Run/Gate/maintenance, future-stage work,
  uncontrolled material scope changes and protected write paths.
- Preserved PH-F02 subject-specific semantic Gate proof and historical approvals,
  accepted baselines and completed Runs.

## PH-051-07 (v0.5.1 WIP)
Independent sandbox-only disposable Task verification helper, fail-closed negatives; no automatic apply or public execute route.

## PH-051-07 (v0.5.1 WIP)
Independent sandbox-only disposable Task verification helper, fail-closed negatives; no automatic apply or public execute route.

## PH-051-07 (v0.5.1 WIP)
Independent sandbox-only disposable Task verification helper, fail-closed negatives; no automatic apply or public execute route.
