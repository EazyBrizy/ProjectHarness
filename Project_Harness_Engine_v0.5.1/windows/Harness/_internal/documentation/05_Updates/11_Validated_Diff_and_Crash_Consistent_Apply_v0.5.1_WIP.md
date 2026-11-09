# PH-051-08 — Validated diff and crash-consistent product apply (v0.5.1 WIP)

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**День реализации:** 2026-10-26  

**Status:** implemented as a *kernel-owned Python service*; not a public automatic execution route. `PH-051-09` will integrate the service into `execute-current`, with Run statuses and completion policy; `PH-051-10` will handle global/orphan recovery and cleanup. This intermediate package is **NOT RELEASED**. No `execute-current` or `executor-doctor` CLI is claimed to be available here.

**Normative basis:** `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`, §§12–13, 18–19, 22–23; `Project_Harness_v0.5.1_Implementation_Plan_RU.md`, `PH-051-08` only. No v0.6.0 Git/PR/deployment or unsandboxed execution.

## Kernel API and trust boundary

`project_harness.apply` exposes:

- `apply_verified_diff(project_root, execution_root, *, verification, secret_values)` — checked, journaled transfer of changed product files, returning `APPLIED` with Apply Evidence ref or rejecting with an explicit `ApplyFailure.reason_code`. The `fault_hook` keyword is *test-only* for deterministic crash injection.
- `recover_apply(project_root, execution_root)` — recover a trusted current Run from a pre-commit journal to the **old** product baseline or recognize a durably **committed** all-new baseline. Its status is `NO_JOURNAL`, `ROLLED_BACK` or `APPLIED`; unsafe/corrupt backup or conflicting edits cause `APPLY_FAILED_RECOVERABLE` without optimistic recovery.

The caller is the trusted Harness kernel, not the agent, end-user YAML or Codex tool. `execution_root` must exactly match the current prepared Run's `EXECUTION_BINDINGS`, external runtime root digest, five projected JIT records and current Task revision. `.harness`, immutable input/history, accepted Stage Plan/Gate and the original Task are never writable by the agent or copied recursively. Automatic mode must have been explicitly accepted in PROJECT_LOCK; manual handoff cannot call this route as a shortcut. `normalize_exact_execution_result()` must already have persisted a kernel-owned, valid `COMPLETED` result and bounded logs. An Agent Result or process exit alone **does not** authorize apply. `verify_disposable()` must separately return `PASS` after actual SANDBOXED verification. A caller may not forge a verification object from an agent field.

## Deterministic diff and security checks

1. Recheck the saved `canonical_product_digest` (`tree:sha256:*`), Run/Task/JIT/projection binding, signed control-plane boundary, current execution policy and exact kernel-owned normalized execution result.
2. Walk and hash regular product files only; reject special files, FIFO, sockets, devices, symlinks, hardlinks, protected `.harness`/`.git`/generated-control paths and unsafe relative names. Do not follow untrusted path components on write. Compute exact create/replace/delete set and compare it with Task `scope.write` and `scope.forbidden`, the verifier's independent diff/scope result and Agent Result's declared file set.
3. Check `verification.expected_paths` independently for existence (they are expected **artifacts**, not invented mandatory file mutations); reject unwanted file-mode changes. Each changed source/backup is currently limited to **64 MiB**, and a product tree to **10,000 regular files**, to bound this version's staging. A larger product requires an explicitly revised, tested contract rather than silently unbounded copy.
4. Rescan actually modified/added file bytes, kernel-persisted Agent Result (raw and decoded), bounded kernel logs and verification diagnostics for exact supplied `ENV:NAME` secret values. All configured adapter secret names must be provided to the kernel's in-memory scan. The present Project Input / Task Contract does **not** define a further declarative DLP scanner; any unknown mandatory `secret_scan` policy is rejected rather than reported as PASS. This is not a universal DLP scanner.
5. Recheck canonical baseline before any product mutation and disposable source after staging. Refuse `BASELINE_CHANGED`, `SCOPE_VIOLATION`, `SECRET_LEAK_DETECTED`, `RESULT_INVALID` or `VERIFICATION_FAILED` as applicable, with no untrusted canonical write.

## Durable apply protocol

The per-Run durable journal is at **`<external execution_root>/apply-journal/`**, not in the canonical product or downloadable handoff. It contains an exact write plan, immutable old-file backups and staged new contents with SHA-256 digests. The PREPARED marker is persisted and fsynced *before the first canonical change*. Each canonical target uses an exclusively-created same-directory temporary file, fsync and atomic `replace`, or an exact `unlink` for deletion; directory changes are fsynced. The service rechecks post-apply canonical digest against the planned result before it writes a single immutable `.harness/evidence/EVD-APPLY-<RUN>-R<revision>.yaml` (`SCHEMA-APPLY-EVIDENCE@1`). The evidence binds exact Run, independent verification-result digest, full write set and before/after tree digests (encoded as `sha256:` fields per the schema). The signed Run operation boundary is updated only for the completed evidence record.

The journal's `COMMITTED` marker is durable only after the canonical product and evidence are validated and the control-plane boundary has passed. Cleanup atomically retires the journal directory before deleting old backup bytes. A crash or ordinary failure with PREPARED marker triggers repeatable rollback using backed-up bytes, followed by a new signed recovery boundary; an interrupted COMMITTED operation is recognized as **all-new** and never called a rollback. If cleanup alone fails after commit, the result remains `APPLIED` with `cleanup_pending`, not a false `APPLY_FAILED` assertion. A leftover retired cleanup tree is kept outside the canonical product and is handled in the later PH-051-10 orphan/cleanup route. Before a new apply for the *same* Run, pending journal recovery runs first; a recovered rollback requires a fresh verification/attempt.

**Concurrency boundary:** the service uses an advisory lock on the existing project `.harness/runtime` directory. It does not claim to prevent a foreign host process from editing files concurrently; unexpected changes are detected by exact baseline/target/postcondition checks and lead to refusal or quarantine. Durable all-old/all-new is a **recovery property**, not the claim that a reader observing an interrupted multi-file transaction before recovery cannot see intermediate files.

## What this package does not establish

- No automatic Run orchestration, Task DONE, Stage Gate acceptance or new CLI/API command is activated by PH-051-08; formal decisions remain separate.
- No real rootless Podman OS isolation or end-to-end security GO is established by mocked unit verification. Those mandatory checks remain for PH-051-11/12 on a suitable non-root host and pinned image.
- No raw external execution directories, backup payloads, raw secrets, raw logs or journal copies belong in project handoff/distribution ZIPs.
- `recover_apply` is a bounded **current Run** recovery API. Migration-wide journal discovery, old Run cleanup, orphan containers and retries are PH-051-10.

**Tested interface:** the new unit/negative/integration test suite `tests/test_ph_051_08_atomic_apply.py` runs the existing `prepare_demo` → exact PH-051-04 execution root → PH-051-06 normalized result → PH-051-07 verifier test double → PH-051-08 apply chain, with fault injection after individual file writes, evidence and commit boundaries. Actual Podman security remains `NOT RUN` unless separately evidenced.
