# PH-051-09 — Governed automatic Run, public CLI/API (v0.5.1 WIP)

**Дата:** 2026-10-25.  **Дата реализации:** 2026-10-26.  **Версия:** 0.5.1-WIP / NOT RELEASED.  **Область:** PH-051-09, normative `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`, §§15–18, 20; implementation plan PH-051-09. Operator migration, global orphan cleanup, full security certification and final release remain **PH-051-10–12**. This document describes implemented behavior, not an OS security attestation.

## Public CLI and Python API

```bash
project-harness executor-doctor --project <root> [--adapter-profile <exact-id-or-project-path>] [--network NONE|EXPLICIT_APPROVED_EGRESS] [--approval <file>] [--keep-execution-root]
project-harness next --project <root>
project-harness execute-current --project <root> [--adapter-profile <exact-id-or-project-path>] [--network NONE|EXPLICIT_APPROVED_EGRESS] [--approval <file>] [--keep-execution-root]
project-harness status --project <root>
project-harness validate-project --project <root>
```

Python APIs exported by `project_harness`:
`executor_doctor(project_root, *, adapter_profile=None, network=None, approval=None, keep_execution_root=False)` and
`execute_current(project_root, *, adapter_profile=None, network=None, approval=None, keep_execution_root=False, runtime_root=None)`. `runtime_root` is an **internal/trusted Python-only storage location**, never a CLI mount option; it must be a private host directory outside the project. Both return structured result objects containing `status`, and where applicable `reason_code`, `execution_mode`, `run_ref`, `next_command` and relevant evidence refs. `executor_doctor` is read-only; unlike distribution `doctor`, it verifies the project-scoped pinned ADP/SBX and Podman self-test. `status`, `next` and `stage-status` expose the applicable public continuation; no private Python is required for a normal Run.

Exit codes: `0` successful PASS/SUCCEEDED/COMPLETED and valid non-blocking status; `3` BLOCKED/TIMED_OUT/FAILED_RETRYABLE; `2` FAIL/INVALID or validation errors from raised public CLI exceptions. Captured JSON envelopes are not authorization records and must not be edited to grant capabilities.

## Preconditions and governed path

1. A prepared Project Instance with accepted `PROJECT_INPUT@4` execution policy and exact active, pinned `CODEX_CLI_LOCAL` `ADP-*` / `ROOTLESS_PODMAN` `SBX-*` refs/digests in `PROJECT_LOCK`; `mode: LOCAL_AUTOMATIC` must be an explicit project opt-in. The default remains `MANUAL_HANDOFF`.
2. A **current** implementation-stage `READY` Task, exact JIT/Run reservation via `next`, trusted context/prompt snapshot, Stage fence and no open blocker. If `next` has not reserved the first Run, `execute-current` can reserve that same current READY Task only after a successful doctor. Running Tasks from a future Stage is forbidden.
3. `executor-doctor` must return PASS for real rootless Podman pinned image and every mandatory isolation check. A missing image, rootless Podman unavailable, UNKNOWN self-test, wrong profile, missing secret environment ref or any rejected option means **no agent dispatch**. There is no unsandboxed or implicit manual fallback.
4. The kernel writes a signed journal boundary `AUTO_RUNNING`, invokes precisely the pinned Codex CLI argv in disposable `/workspace/product` under rootless Podman, and normalizes the exact `/output/agent-result.json` into bounded kernel-owned records (`ART-*`, logs, `AGENT_RESULTS`). A `COMPLETED` text or exit-0 alone cannot approve the Run.
5. A second, **independent** sandbox verifier executes the Task verification argv (potentially multiple separate Podman processes), checks actual diff/scope and canonical baseline, then the PH-051-08 service applies only independently PASS-verified changes through its durable journal. Immutable Apply Evidence binds exact Run and before/after digests. Task verification is recorded as an exact `SANDBOXED` `validation_report` and `TEST_REPORT` evidence; it is **not** generalized Stage Gate/architecture/legal proof.
6. If project `completion_policy: AUTO_AFTER_PASS`, the kernel completes only the Task after independent PASS+apply; Stage Gate/level-up still require their separate formal approvals. With `EXPLICIT_AFTER_VERIFICATION`, output is `SUCCEEDED`, `completion_status: WAITING_EXPLICIT_COMPLETION`, and `next` routes to `complete --project <root> --result <exact-active-run-result-path>`. Never fabricate the result: use the path returned by the active Run/status. Completion checks verified post-apply product digest and signed result.

Run phase journal and `status.automatic_run`: `AUTO_RUNNING → RUNNING`; `AGENT_RESULT_NORMALIZED_UNVERIFIED` / `AUTO_VERIFYING` / `PRODUCT_APPLY_VERIFIED → VERIFYING`; `AUTO_VERIFIED → SUCCEEDED`. The persisted project remains `ACTIVE` until completion, or `BLOCKED` when a failure has a recorded blocker. `status.next_operator_route` and `next.next_operator_route` distinguish automatic from manual execution and never direct an in-flight automatic Run to host `verify`.

## Failure and retry matrix

- Preflight manual opt-out: `BLOCKED / EXECUTOR_UNAVAILABLE`, read-only, manual `next → external agent → verify → complete` remains valid. Doctor or option refusal likewise does not reserve/mutate a Run or its Task.
- Podman doctor: `BLOCKED / SANDBOX_UNAVAILABLE` or `SANDBOX_POLICY_FAILURE`, never retry on host. `NETWORK_NOT_APPROVED` for unapproved/unsupported egress, `SECRET_REFERENCE_MISSING` for missing exact ENV refs. `--keep-execution-root` is refused unless a governed debug policy exists; none is activated in this bounded package.
- Sandbox attempt: bounded `EXECUTOR_TIMEOUT → TIMED_OUT`; non-zero exit / incomplete/invalid output (`EXECUTOR_EXIT_NONZERO`, `RESULT_MISSING`, `RESULT_INVALID`, `OUTPUT_LIMIT_EXCEEDED`) → `FAILED_RETRYABLE` or `BLOCKED` according to classification.
- Scope violation, secret leak, stale baseline, independent verification failure and apply recovery error: `SCOPE_VIOLATION`, `SECRET_LEAK_DETECTED`, `BASELINE_CHANGED`, `VERIFICATION_FAILED`, `APPLY_FAILED_RECOVERABLE`. **No** successful Task verification/evidence without independent PASS and committed apply. Only the governed `resume --resolution` route produces a **new** Task revision and Run attempt after recorded blocker resolution; old Run history is immutable.
- Repeating the same *already verified* `execute-current` returns the same `SUCCEEDED` Run without dispatch; repeating an in-flight or interrupted `AUTO_RUNNING` / `AUTO_VERIFYING` refuses re-dispatch. Global interrupted-container/orphan reconciliation and cleanup are PH-051-10, not silently claimed here. Do not execute raw `recover_apply` or erase journals as an operator workaround.

## Strict precedence and current limitation

Effective capabilities never exceed exact project lock and pinned ADP/SBX profiles. `--adapter-profile` accepts the **same exact pinned** ref/path, not a profile switch. Both commands accept the normative `--network` and `--approval` flags; the currently implemented Podman backend from PH-051-03 is **NONE-only**, so `EXPLICIT_APPROVED_EGRESS` and any per-Run approval intended to broaden it **fail closed with `NETWORK_NOT_APPROVED`**. No unimplemented destination allowlist, per-Run privileged override, debug retention, additional backend or external provider is implied. `--network NONE` is the only executable setting. Do not silently promote a configured `EXPLICIT_APPROVED_EGRESS` project profile to an activated route: unsupported egress policies remain blocked.

Manual `verify --allow-command-execution` intentionally remains for the **manual** external-agent route. It is not an authorized substitute for the automatic sandbox verifier; `verify_current` rejects use on an already automatically-dispatched Run. The operator must explicitly select/approve manual mode rather than treating an automatic failure as a manual success.

## Test status

The PH-051-09 unit/integration suite mocks only the Podman **transport and attestation** to test orchestration and failure routing. No real rootless Podman is present on the packaging host and the process user has UID 0. Consequently **live Podman security / fake Codex actually inside Podman = NOT RUN**, and **v0.5.1 release GO is NOT authorized**. Full security matrix and fresh installed-wheel external smoke are release dependencies PH-051-11/12. Logs, manifest and scoped regression details are in `PH_051_09_TEST_REPORT.md` inside the matching Engine archive.
