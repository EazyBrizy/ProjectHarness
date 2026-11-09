# Implementation decisions — Project Harness Engine v0.5.0

**Release:** 0.5.0  
**Date:** 2026-08-20  
**Scope:** only requirements of the v0.5.0 implementation specification

## Decisions applied

1. **Canonical path spelling.** The exact uppercase Contract Catalog paths are normative: `.harness/stages/PLANS`, `GATES`, `ACCEPTANCE`, and `ASSESSMENTS`. Lowercase forms appearing in explanatory prose are treated as non-normative examples.
2. **Level graph.** The only implementation levels are `PROTOTYPE`, `ALPHA`, `BETA`, `MVP`, and `RELEASE`, with strict sequential progression. `MVP` is displayed as Production MVP.
3. **`UNSURE` semantics.** `UNSURE` remains an intake decision state. Validation returns `WAITING_DECISION` and a recommendation while preserving the supplied value; no target is auto-selected.
4. **Independent axes.** Implementation level controls depth and evidence only. Product scope, profile, execution mode, and deployment model remain independent and are not inferred from the level.
5. **Active-stage detail.** All stages through the target receive outlines and Gates. Only the active stage receives detailed Work Packages, atomic Tasks, Prompt/Context Plans, and executable JIT bundles.
6. **Gate closure.** Mandatory criteria close only with `PASS` plus evidence or `NOT_APPLICABLE` plus rationale and validator. No average or aggregate score can override a failed, partial, or unknown mandatory criterion.
7. **Acceptance history.** Each accepted stage receives an immutable report with exact baseline, permitted use, limitations, next-stage gaps, approval, and evidence references. Accepted maturity never decreases in place.
8. **Brownfield assessment.** Assessment uses static inventory and supplied evidence, does not automatically execute repository commands, and stores claimed, observed, satisfied-candidate, and accepted maturity separately.
9. **Baseline acceptance.** `SATISFIED_BY_BASELINE` is restricted to Brownfield/Hybrid, requires exact assessment reference/digest, preserves sequential acceptance reports, and atomically supersedes any unexecuted route for accepted stages.
10. **Stage completion.** The last Task in a stage transitions the Stage to `VERIFYING`. The current target cycle ends at `TARGET_LEVEL_REACHED`, not legacy project `COMPLETED`.
11. **Level-up.** A higher target requires formal approval and activates only the nearest next stage. Equal/lower targets are non-destructive. Open same-level maintenance blocks level-up.
12. **Migration.** v0.4.1→v0.5.0 is an explicit isolated-copy transaction. Legacy history is preserved byte-for-byte where immutable, and legacy `COMPLETED` is never inferred as an accepted implementation level.
13. **Historical prompt validation.** Historical bundles are validated against their own persisted target assumptions, not a later level-up target.
14. **No scope expansion.** Automated executor/sandbox, Git publication, deployment execution, PROJECT skill authoring, parallel worktrees, and remote control plane remain out of v0.5.0.
15. **Crash-consistency boundary.** Stage transactions are local-filesystem transactions only. No database, daemon, remote control plane, multi-host lock or distributed commit protocol is introduced.
16. **Journal-before-apply.** A complete ordered write set, existed-before markers, immutable backups, staged paths, old/new digests, request/result digests, timestamps and per-entry state are durable before the first canonical replace.
17. **Terminal truth.** `COMMITTED` is written only after full-new digest verification; `ROLLED_BACK` only after full-old digest verification. API result, journal status and canonical state must describe the same fact.
18. **Deterministic recovery.** The unique latest non-terminal transaction commits only when the entire new write set is already digest-confirmed; otherwise it restores the entire old write set. Corrupt journals/backups block mutation instead of being guessed around.
19. **Approval idempotency.** Exact committed approval replay returns the persisted result without a second transition. A rolled-back transaction id requires a new formal approval.
20. **Derived views.** Post-commit rendering cannot invalidate a committed transition; render failure is returned as an explicit recoverable warning with an idempotent regeneration route.
21. **Current target authority.** Before preparation, current target is read from the external workspace `PROJECT_INPUT.yaml`. After preparation, `STAGE_STATE.implementation.target_level` is the sole canonical current-cycle target; PROJECT and CURRENT_STATE are synchronized projections, while `PROJECT_INPUT_ACCEPTED.implementation.target_level` remains immutable initial-target history.
22. **Exact immutable maturity binding.** `SATISFIED_BY_BASELINE` accepts only canonical `<assessment-id>@<positive-integer-revision>` and `sha256:<64 lowercase hex>`. Resolution is one exact `ASSESSMENTS/<ref>.yaml` lookup; glob/latest/lexicographic fallback is forbidden. Filename, exact envelope, internal id/revision and file-byte digest are verified before Stage mutation, and the Acceptance Report stores the resolver result.
23. **Freshness/current-context binding.** Exact resolution is necessary but not sufficient. Before baseline acceptance the assessment must be `COMPLETED` and match the current product tree, approval baseline, Stage State target, previous accepted level, immutable accepted claim and sequential candidate context. Candidate closure is recomputed from mandatory criteria; stale/other-base evidence cannot authorize accepted criteria. Failure writes only an immutable STALE validation revision linked to the source assessment and performs zero acceptance mutation.

## L-01 target boundary

This correction changes only target loading and consistency for existing v0.5.0 routes. It does not change the canonical scale, intake approval semantics, Brownfield evidence/freshness rules, or planner behavior beyond reading the canonical current target. `level-up` already owned a crash-consistent multi-file write set; that same transaction now remains the explicit authority for Stage State, PROJECT and CURRENT_STATE target projections.

## B-02 input boundary

The supplied engine archive exposes `accept-stage` and `level-up`, but does not contain a `plan-active-stage` command or implementation; it contains only the `PLAN_ACTIVE_STAGE` next-route marker. This B-02 patch does not invent planner semantics. The generic transaction helper is ready for that route, while the crash-consistency protocol is connected to the Stage mutation entry points actually present in the input archive.

## B-04 exact assessment reference boundary

The B-04 correction changed only immutable maturity-assessment reference resolution used by `SATISFIED_BY_BASELINE`; it did not itself change freshness/context semantics, target semantics, Gate evidence criteria, planner behavior, maintenance, level-up, or resolution rules for other artifact types.


## B-03 assessment freshness boundary

This correction consumes the exact B-04 resolver result and changes only Brownfield/Hybrid `SATISFIED_BY_BASELINE` preflight plus the immutable maturity-assessment validation record needed to explain staleness. It does not change the resolver, Gate approval template/model, active-stage planner, maintenance route, level-up behavior, repository command execution, or version number.

## G-01 evidence trust slice

This historical G-01 slice was intentionally limited to evidence resolution and integrity. At that step it did not materialize required outcomes or profile controls and did not add an approval exporter or Gate-preparation Work Package; the later U-01 section below adds only the bounded exporter while preserving that Gate scope.

Decisions:

1. **Canonical artifact identity.** New Gate-eligible evidence is one immutable `EVD-*` artifact at `.harness/evidence/{id}.yaml`. The immutable id is its revision boundary; prefix glob, alternate path, symlink and duplicate internal-id claims are rejected.
2. **Schema compatibility.** Missing `schema_version` means readable legacy history but not Gate eligibility. An explicit unsupported version is invalid normalized evidence, not a downgrade path.
3. **Semantic closure.** Every declared ref is fail-closed. `PASS`, exact criterion mapping, exact current `tree:sha256` baseline, provenance/source binding and intersection with the criterion or hard-constraint `required_evidence_kinds` are all mandatory. Global refs are not trusted shortcuts.
4. **Runtime scope.** Runtime verification evidence is written after verification/scope checks with the exact product snapshot and maps `RUNTIME_TASK_VERIFICATION`, not all Stage criteria. Subsequent product changes make it stale for final Gate closure. Safety evidence remains `BLOCKED`.
5. **Acceptance immutability.** Accepted Gate and Stage Acceptance Report store the same sorted `{ref, path, sha256}` snapshot. Project validation re-resolves evidence and sources, then reports deletion/tampering without rewriting accepted history.
6. **Product digest authority.** Gate and runtime evidence use the same canonical product snapshot algorithm, excluding `.harness/**`, VCS/environment directories and kernel-generated protected root views. This prevents kernel-owned report/status writes from invalidating an otherwise unchanged product baseline.
7. **Registry change.** Contract Catalog moves from version 4 to 5 because `verification_evidence` becomes a registered persistent immutable contract and accepted Stage artifacts gain evidence binding fields. Root, packaged and documentation copies, lock generation and doctor expectations move together.

U-01 does not alter the supplied Gate materialization semantics; it only exposes the exact current contract through a supported operator preparation flow.

## U-01 self-contained Stage approval preparation boundary

This correction adds a bounded operator preparation surface around the current v0.5.0 Stage Gate contract. It does not add a new lifecycle state, automatic approval, repository executor, generalized form engine, distributed workflow, or `STAGE_ACCEPTANCE_PREPARATION` Work Package.

Decisions:

1. **Persistent output is mandatory.** `prepare-stage-approval` always writes the requested operator record. CLI JSON is a summary only; it cannot replace the file consumed by `accept-stage`.
2. **Public baseline authority.** `product_baseline_revision(root)` is the supported public API for the canonical product-tree digest. Existing private alias remains only for v0.5.0 compatibility and is not documented as an operator route.
3. **Strict two-state record.** `SCHEMA-STAGE-APPROVAL@1` accepts only an explicit `DRAFT` with `approved: false` and null formal identity/time, or an explicit `APPROVED` record with canonical Decision/actor refs and UTC timestamp. Every normative object rejects additional properties.
4. **No inferred conclusions.** Preparation copies exact definitions and creates one-to-one result skeletons with `UNKNOWN`, empty evidence refs and no validator. Compatible evidence inventory is informational and never changes a result or formal state.
5. **Exact current binding.** The preparation fingerprint covers active/target levels, exact Plan/Gate refs, paths, revisions, digests/statuses, Gate base, product baseline, last accepted context, complete definitions, and current required WP/blocker views. It deliberately excludes mutable user conclusions and evidence-candidate inventory.
6. **Staleness before mutation.** Strict acceptance rebuilds the current bounded draft and compares the exact context before any transaction write. Product-tree or Gate drift, changed definitions, or changed required WP/blocker views invalidates the old record.
7. **Safe output boundary.** Output may be outside the Project Instance or under `.harness/operator/APPROVALS/`. Other in-project paths, symlink/directory targets and implicit overwrite are rejected; `--force` is the only replacement route.
8. **No preparation mutation.** Reading status, resolving existing evidence and calculating digests do not execute repository commands. The only write is the explicitly requested output file; no Stage/Gate/Decision/Acceptance/product artifacts are changed.
9. **Compatibility boundary.** Historical v0.5.0 approval records remain readable through the existing compatibility path. Records carrying strict markers must fully identify and validate against the supported strict schema; they cannot downgrade to legacy handling.
10. **Executed active Stage scope.** The generated U-01 draft is for current active executed work and therefore binds `acceptance_method: EXECUTED_STAGE_WORK`. Existing Brownfield exact-assessment acceptance semantics remain unchanged by this patch.
11. **Auxiliary evidence boundary.** Outcome/profile-control evidence from a strict approval is resolved and validated before mutation. Because the supplied v0.5.0 persisted Gate contract records criterion and hard-constraint closure only, auxiliary refs are not reclassified as unrelated global Gate evidence; accepted Gate/Acceptance bindings remain self-validating under `validate-project`.

## M-01 same-level maintenance boundary

- **Public route, not a private helper:** `start_maintenance`/`cancel_maintenance` and matching CLI commands are the only supported creation/cancellation entry points. The old direct-WP stub is removed.
- **Accepted-stage fence:** maintenance plan, WP, Tasks, context/prompt/verification artifacts, capability grant, Run Plan, JIT bundle, snapshots, verification records and Task Reports bind to `highest_accepted_level` with `maintenance_route: MAINTAIN_CURRENT_STAGE`; the canonical active Stage may already identify a later planning target.
- **No maturity mutation:** Stage State, current target, `highest_accepted_level`, Stage Acceptance Reports, accepted Stage Plan/Gate revisions and pre-existing completed Runs are outside the maintenance mutation set.
- **Governed start:** strict exact-bound plan validation precedes mutation. Start uses the crash-recovery Stage transaction service for canonical route artifacts and an idempotent deterministic first Run reservation; exact replay returns the existing route and cannot allocate a second first JIT.
- **Runtime closure:** final mandatory Task completion creates a revisioned `COMPLETED` WP and immutable completion report, clears maintenance current state and restores the captured previous valid route instead of invoking Gate readiness.
- **Fail-closed cancellation:** a separate strict `CANCEL_MAINTENANCE` Decision is required. Cancellation is permitted only before completed/observed product changes and without product drift from the trusted snapshot. No automatic compensation or rollback is synthesized.
- **Level-up interlock:** only open maintenance WP statuses block level-up. Terminal `COMPLETED`, valid `CANCELLED`, `SUPERSEDED`, or historical revisions do not.
- **Scope exclusion:** M-01 does not add Distribution Maintenance Change Packs, Git operations, deployment, executors, or next-stage implementation.
