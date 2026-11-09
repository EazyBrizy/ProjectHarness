## Текущий build — Windows manual migration remediation, 2026-11-07

Исправлена Windows-миграция v0.5.0→v0.5.1 и очистка частичного staging; automatic executor остаётся выключен, PH-LW-06 не выполнялся. [Новый фактический отчёт](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_TEST_REPORT.md) содержит разбор прежних 9 FAIL-модулей и точные повторные tests/limitations. Ниже сохранены предыдущие checkpoints. Полный release — **NO GO / NOT RELEASED**.

## Предыдущий build — Windows HTTP retest PH-LW-04/05, 2026-11-07

База PH-LW-05 перенесена в native Windows workspace и исправлена по результатам HTTP/importer приёмки. [Текущая область, команды и ограничения](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/11_PH_LW_04_05_Windows_HTTP_Acceptance.md). Фактический verdict и регрессии — `PH_LW_04_05_WINDOWS_ACCEPTANCE_TEST_REPORT.md` в Engine. Ниже сохранены исторические checkpoints: их NOT RUN относится к прежним сборкам. Полный `LOCAL_WEB_MANUAL`, automatic executor и v0.5.1 — **NO-GO / NOT RELEASED**; PH-LW-06 не выполнялся.

## PH-LW-05 — MD/ZIP import and source revisions (0.5.1 WIP / NOT RELEASED)

Authenticated Local Web «Документы» supports initial GREENFIELD intake, multiple `.md` and `.zip` files with Markdown, escaped text preview, exact source revisions, append/replace and conscious «Документации нет». Uploads are quarantined, validated and published as immutable source snapshots; intake refresh invalidates old draft approvals and does not use `start_intake(force=True)`. It never activates automatic Codex, shell, Git/PR/deploy or network transfer. Real Windows 11/Waitress/Edge acceptance and PH-051-12 Podman/egress remain **NOT RUN / NO-GO**, not PASS. See [PH-LW-05 runbook](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/10_PH_LW_05_Document_Import_and_Source_Revisions.md).

## PH-LW-04 — Local Web HTTP/UI shell (WIP, not released)

`project-harness ui` / `python project-harness.py ui` starts an authenticated loopback-only Flask+Waitress manual shell **only when pinned optional web dependencies are installed**. In this build, `ui` never enables Codex automatic execution or provider access. Static HTML/CSS/JS are included in the wheel. Secure localhost bootstrap → HttpOnly session/CSRF, read-only project list/status and exact-bound existing `check-intake`/`prepare`/`next`/`validate-project`/`verify` routes are implemented; imports, GPT/forms/approvals and future UI actions are explicitly disabled. See [PH-LW-04 security/runbook](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/09_PH_LW_04_Loopback_HTTP_Session_and_UI_Shell.md). **No Windows 11 native session / real Waitress/browser acceptance is claimed until tested; full v0.5.1 automatic remains NO-GO.**

> **PH-LW-01 (2026-11-01; WIP, Windows NOT RUN):** [Additive Windows Local Web manual contract](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/00_Entry_And_Base.md), 26-command map, fixture/schema suite and Windows CI entrypoint. No Web server or automatic execution enabled. The supplied base is PH-051-11, not the PH-051-12 snapshot named by the prompt.

> **АКТУАЛЬНО — PH-051-11, Project Harness 0.5.1-WIP / NOT RELEASED.** Версия Python package `0.5.1`, project schema `7`, strict `PROJECT_INPUT@4`, registry versions `id_prefixes@3`, `statuses@6`, `contracts@6`. Публичные `executor-doctor` и `execute-current` появились в PH-051-09; `migrate-project` для 0.5.0→0.5.1 — в PH-051-10. См. [operator runbook](docs/Project_Harness_Documentation_v0.5.1/05_Updates/14_Operator_Runbook_v0.5.1_WIP.md), [Podman security procedure](docs/Project_Harness_Documentation_v0.5.1/05_Updates/15_Podman_Security_Validation_v0.5.1_WIP.md) и `PH_051_11_TEST_REPORT.md`. **В текущей поставке нет подтверждённого real rootless Podman security PASS.** Старые PH-051-01..10 секции ниже — исторические срезы, не актуальный перечень доступных команд. В частности, `prepare` всё ещё отклоняет новый `LOCAL_AUTOMATIC` intake с `AUTOMATIC_EXECUTOR_NOT_IMPLEMENTED`; публичный opt-in на подготовке нового проекта остаётся blocker PH-051-12, и его нельзя обходить ручной правкой PROJECT_LOCK.

> **PH-051-10 (v0.5.1 WIP / NOT RELEASED):** Current `migrate-project` supports exact 0.5.0/schema6 → 0.5.1/schema7 in `MANUAL_HANDOFF` mode, with immutable history; automatic crash/orphan cleanup requires verified rootless Podman and never runs host Codex. See `docs/Project_Harness_Documentation_v0.5.1/05_Updates/13_Migration_Cleanup_Orphan_Recovery_v0.5.1_WIP.md`. Full v0.5.1 release/OS security remains NO-GO until PH-051-11/12.

## v0.5.1 WIP / PH-051-09 governed automatic Run (NOT RELEASED)

The public `project-harness executor-doctor --project <root>` and `project-harness execute-current --project <root>` commands are now available for an **explicitly opted-in** project with pinned `CODEX_CLI_LOCAL` + `ROOTLESS_PODMAN` profiles. The bounded route composes an exact current READY JIT, disposable Podman agent process, separate Podman verification process, PH-051-08 checked/atomic product apply and policy-gated Task completion. `next`, `status`, `stage-status`, and `validate-project` expose/validate the public continuation; default `MANUAL_HANDOFF` is unchanged. Without a passing **real** Podman doctor, no automatic agent process launches; host fallback and egress approval overrides are forbidden. On this packaging host live Podman security tests are **NOT RUN**, so **v0.5.1 remains WIP/NO-GO**. See [PH-051-09 governed runtime](docs/Project_Harness_Documentation_v0.5.1/05_Updates/12_Governed_Automatic_Run_and_Public_CLI_v0.5.1_WIP.md) and `PH_051_09_TEST_REPORT.md`.

## v0.5.1 WIP / PH-051-06 exact result channel (NOT RELEASED)

The single local sandbox-only adapter now validates `/output/agent-result.json`
against `SCHEMA-AGENT-TASK-RESULT@1`, exact active Run/Task, UID/mode,
symlink/hardlink, UTF-8 and 1 MiB bound. Kernel-owned normalized Agent Result,
immutable ART envelope and bounded/redacted logs are persisted without any
product apply or optimistic Task completion. Secret environment refs (`ENV:NAME`)
are resolved only from the exact ADP allowlist, sent through transient owner-only
Podman env-file, and exact-value leaks block the Run. The previous PH-051-05
"secret refs unsupported" note describes that earlier slice and is superseded.
There is still **no public execute-current**, no independent SANDBOXED verifier,
no atomic apply, and **real Podman security integration is NOT RUN/NO-GO**.
See [PH-051-06 channel contract](docs/Project_Harness_Documentation_v0.5.1/05_Updates/10_Exact_Result_Channel_v0.5.1_WIP.md)
and `PH_051_06_TEST_REPORT.md`.

## v0.5.1 WIP / PH-051-05 exact Local Codex CLI Adapter

The single CODEX_CLI_LOCAL adapter now binds exact ACTIVE ADP/SBX revisions and
PROJECT_LOCK digests to the PH-051-04 JIT/Task disposable Run, and forwards a
validated argv list only to PH-051-03 RootlessPodmanRunner. Host Codex/shell
fallback is forbidden. `stdin` is CLOSED; effective timeout is ADP/SBX bounded;
secret refs and nonfixed environment forwarding remain fail-closed until
PH-051-06. Local Podman/image/actual Codex flags were NOT TESTED here.
There is still no public `executor-doctor`/`execute-current`, no automatic
verification/apply and no v0.5.1 release. See
[PH-051-05 adapter note](docs/Project_Harness_Documentation_v0.5.1/05_Updates/09_Local_Codex_CLI_Adapter_v0.5.1_WIP.md)
and `PH_051_05_TEST_REPORT.md`.

> **PH-051-04 (0.5.1 WIP / NOT RELEASED).** Per-Run disposable
> product snapshots and bounded read-only control projection are now provided
> through `project_harness.execution_roots.prepare_execution_root()` as a
> Python API. Exact Task/JIT/baseline metadata is persisted only in
> `.harness/runtime/EXECUTION_BINDINGS/`, excluded from export/handoff.
> No automatic CLI, Codex run, verification or diff/apply was added.
> Real rootless Podman security integration is still NOT RUN / NO-GO.
> See `PH_051_04_TEST_REPORT.md` and
> `docs/Project_Harness_Documentation_v0.5.1/05_Updates/08_Disposable_Execution_Root_v0.5.1_WIP.md`.

> **PH-051-03 — v0.5.1 WIP (not released).**
> Contracts PH-051-01 and executor protocol PH-051-02 are retained. The single
> `ROOTLESS_PODMAN` Python runner/doctor and technical self-test contract are
> now included. **Real rootless Podman integration NOT RUN in this packaging
> environment; automatic execution remains disabled, manual handoff only.**
> Schema 7 / `PROJECT_INPUT@4`, registries ID@3, statuses@6, contracts@6.
> See [PH-051-03 report](PH_051_03_TEST_REPORT.md) and
> [sandbox note](docs/Project_Harness_Documentation_v0.5.1/05_Updates/07_Rootless_Podman_Sandbox_v0.5.1_WIP.md).

## PH-LW-02 — native Windows manual core (0.5.1 WIP, WINDOWS_NOT_TESTED)

Core import graph no longer requires Linux `fcntl` on Windows; native Windows `executor-doctor` and `execute-current` fail closed (`BLOCKED / SANDBOX_UNAVAILABLE`), without host agent execution. Preflight rejects UNC/device/drive-relative roots, Windows-unsafe relative paths, casefold collisions and unsafe ZIP extraction before writes; Stage transitions use genuine OS-level file locking with journal recovery. The same Python manual APIs (`start_intake → check_intake → prepare_handoff → validate_handoff → validate_project_directory → next_task → verify_current → complete_current`) are exercised by `tests/test_ph_lw_02_windows_core.py`. Native Windows/NTFS verification is **NOT RUN** in this Linux build; see `local_web/ci_ph_lw_02_windows.ps1`, `PH_LW_02_TEST_REPORT.md` and [PH-LW-02 technical boundary](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/07_PH_LW_02_Native_Windows_Manual_Core.md). No Web UI, Windows installer, approved egress or actual Podman security GO.

# Project Harness Engine v0.5.1-WIP

**Release date:** 2026-08-18  
**Python:** 3.11+  
**Canonical project schema:** 6  
**Preparation input:** `SCHEMA-PROJECT-PREPARATION-INPUT@3`

Project Harness is a deterministic Browser GPT preparation layer and governed project-local runtime for Codex handoffs. Version 0.5.0 adds implementation levels and stage-aware progression without expanding the accepted product scope.

## PH-F07 — Operator documentation and tested runbook (2026-10-25)

Начинайте с [единого runbook](docs/Project_Harness_Documentation_v0.5.1/08_Distribution/04_Operator_Runbook_v0.5.0.md): source/wheel install → GPT interview/explicit approvals → preparation → external Codex + verify/complete → semantic Gate proof/approval → governed next-stage planning → target reached → level-up или maintenance. Разобраны точные CLI flags, схемы operator records, expected status и reject/recovery. Это исправление документации **без** новых routes или изменения v0.5.0 contracts; финальная PH-F08 acceptance остаётся отдельным этапом.

## PH-F06 integration update — 2026-10-24

Проверенные границы зрелости, Brownfield evidence import и same-level maintenance:
[PH-F06 lifecycle notes](PH_F06_LIFECYCLE_NOTES.md).
Результаты отдельных и полных прогонов: [PH-F06 test report](PH_F06_TEST_REPORT.md).
Это scoped remediation v0.5.0, не финальная приёмка PH-F08.

## What v0.5.0 implements

The canonical implementation path is:

```text
PROTOTYPE → ALPHA → BETA → MVP → RELEASE
```

`MVP` means **Production MVP**. An implementation level controls implementation and verification depth; it does not add features, integrations, permissions, deployment targets, or architectural complexity outside the accepted Project Definition.

The release adds:

- strict `PROJECT_INPUT@3` with required `implementation.target_level` and `implementation.claimed_current_level`; external intake reads its current target there, while a prepared project uses Stage State as the sole current-cycle authority;
- seven exact registries, including `implementation_levels@1`;
- Stage State, Stage Plans, Stage Gates, immutable Stage Acceptance Reports, and Maturity Assessments;
- outlines for every stage through the target, but detailed Work Packages, Tasks, Prompt Plans, and executable JIT bundles only for the active stage;
- a runtime stage fence and `STAGE_SCOPE_VIOLATION` for future-stage work;
- read-only Brownfield maturity assessment with separate claimed, observed, satisfied-candidate, and formally accepted levels;
- crash-consistent, journaled and idempotent `accept-stage` and `level-up` transactions;
- normalized immutable Gate evidence artifacts with exact path, registry kind, positive status, provenance/source digest, subject mapping, product baseline and accepted binding validation;
- explicit, transactional, idempotent migration from v0.4.1/schema 5 to v0.5.0/schema 6;
- a public strict same-level maintenance route that executes accepted-stage Tasks without changing target or accepted maturity.

After the last ordinary mandatory Task in an active stage, the runtime deterministically evaluates Gate readiness against the final product tree. Missing exact-baseline evidence creates one idempotent `STAGE_ACCEPTANCE_PREPARATION` Work Package with an atomic READY Task and one JIT bundle; otherwise the stage becomes `VERIFYING` directly. A successful formal Stage Gate approval either activates the nearest next stage or, when the target stage is accepted, sets project status to `TARGET_LEVEL_REACHED`. A structurally valid review that reports an unclosed mandatory result is persisted as a distinct Gate-related `BLOCKED` state with an explicit recovery route.

## PH-F04: real runtime continuation and validation

For prepared v0.5.0 projects run `next`, `stage-status`, and `validate-project` to inspect the **actual** continuation. `next.next_operator_route` and `stage-status.next_operator_route` identify a public CLI command (and any reviewed follow-up), or a concrete external safety/human prerequisite. On `PLAN_ACTIVE_STAGE`, first run `prepare-active-stage-plan --project <root> --output <record>`, review the exact-bound plan, then `plan-active-stage --project <root> --plan <record>`; a boundary `next` is read-only. For a `STAGE_GATE_REVIEW` boundary use `prepare-stage-approval` and formal `accept-stage`, not a Task reservation. Gate `BLOCKED` uses `resume-stage-gate`, ordinary Task `BLOCKED` uses `resume`; a safety violation requires restoration from a trusted state. `TARGET_LEVEL_REACHED` offers formal `level-up` only below `RELEASE`; accepted `RELEASE` offers only optional same-level maintenance. The new project validator rejects unreachable routes, mismatched Stage/Gate/Task/Run references and future-stage Tasks while preserving the previous proof, approval and recovery contracts. See `docs/Project_Harness_Documentation_v0.5.1/08_Distribution/03_User_Workflows.md`.

## v0.5.1 WIP / PH-051-03 sandbox runner

A single `ROOTLESS_PODMAN` Python runner and strict fail-closed doctor are now
implemented in `src/project_harness/sandbox/`. The public CLI remains **manual
handoff only**: `execute-current`/`executor-doctor` are PH-051-09 tasks, not
commands available in this archive. This build environment had no real
rootless Podman; OS isolation acceptance is **NOT RUN / NO-GO**. No agent is
run on host when the sandbox is absent. See
`docs/Project_Harness_Documentation_v0.5.1/05_Updates/07_Rootless_Podman_Sandbox_v0.5.1_WIP.md`
and `PH_051_03_TEST_REPORT.md`.

## Scope boundary

v0.5.0 does **not** include an automated Codex CLI/API executor, rootless container sandbox, Git commit/push/PR adapters, deployment execution, declarative PROJECT skill authoring, parallel worktrees/leases, or a remote multi-user control plane. Maturity assessment does not automatically execute repository commands.

## Quick start

From the extracted engine archive:

```bash
python project-harness.py doctor
python project-harness.py --version
python project-harness.py --help
```

Build and validate the bundled demonstration handoff:

```bash
python project-harness.py demo \
  --output-dir ./demo-output \
  --keep-directory

python project-harness.py validate-handoff \
  --project ./demo-output/harness-demo-codex-handoff.zip
```

The demo target is `MVP`, but only the `PROTOTYPE` stage is detailed and executable in the initial handoff.

## Browser GPT preparation workflow

Upload the engine archive, project documentation, and—only for Brownfield/Hybrid—the existing repository directory or ZIP. Use [`templates/GPT_PREPARATION_INSTRUCTIONS.md`](templates/GPT_PREPARATION_INSTRUCTIONS.md) as the normative preparation instruction.

The required question order starts with documentation status, then the first verifiable user outcome, then the target implementation level before architecture and technology selection. Canonical target values are:

```text
PROTOTYPE | ALPHA | BETA | MVP | RELEASE
```

`UNSURE` is an intake decision state, not a stored implementation level. The engine returns `WAITING_DECISION` and a recommendation; the target is never substituted automatically.

Create an external intake workspace:

```bash
python project-harness.py start-intake \
  --workspace ./work/my-project-intake \
  --project-name "My Project" \
  --mode greenfield \
  --source ./input/requirements.md
```

For Brownfield/Hybrid, the intake workspace must remain outside the source repository:

```bash
python project-harness.py start-intake \
  --workspace ./control/existing-project-intake \
  --project-name "Existing Project" \
  --mode brownfield \
  --source ./input/product-docs \
  --repository ./input/existing-project.zip
```

Validate readiness:

```bash
python project-harness.py check-intake \
  --workspace ./work/my-project-intake
```

A Greenfield handoff requires four independent approvals: Project Definition, Architecture Baseline, Technology Baseline, and Codex Handoff. Brownfield/Hybrid additionally requires a separate Brownfield Baseline approval. Ordinary questionnaire answers never count as approvals.

Compile and validate the handoff:

```bash
python project-harness.py prepare \
  --workspace ./work/my-project-intake \
  --output ./output/My_Project_Codex_Handoff_v1.zip \
  --keep-directory ./output/My_Project_Codex_Handoff_v1

python project-harness.py validate-handoff \
  --project ./output/My_Project_Codex_Handoff_v1.zip
```

Successful preparation returns `READY_FOR_CODEX` and emits exactly one executable compiled bundle for the current READY Task.

## Brownfield maturity assessment

Assessment may run against a Brownfield/Hybrid intake workspace or an extracted prepared project. It inventories repository files and supplied evidence, but does not run build, test, deployment, or arbitrary repository commands:

```bash
python project-harness.py assess-maturity \
  --workspace ./control/existing-project-intake \
  --evidence ./input/maturity-evidence.yaml
```

Missing runtime proof remains `UNKNOWN`. Filenames, README labels, version strings, or a Dockerfile alone do not prove a level. For an external intake workspace the assessment reads target from the current `PROJECT_INPUT.yaml`; for an extracted prepared project it reads only `.harness/stages/STAGE_STATE.yaml`. The immutable accepted input remains the historical initial target. Supplied evidence is retained with status, criterion refs, base revision and stale marker. The assessment writes an immutable report and recommendation; it never changes `highest_accepted_level` without a separate formal approval.

## Project-local Codex cycle

In an extracted handoff:

```bash
python .harness/engine/project-harness.py validate-project --project .
python .harness/engine/project-harness.py status --project .
python .harness/engine/project-harness.py stage-status --project .
python .harness/engine/project-harness.py next --project .
```

Codex follows the current prompt, writes only within the Task Contract product scope, and records the exact Agent Task Result path from the Run Plan. Every other agent-side write under `.harness/**` is prohibited.

Verification and completion:

```bash
python .harness/engine/project-harness.py verify \
  --project . \
  --allow-command-execution

python .harness/engine/project-harness.py complete \
  --project . \
  --result .harness/runtime/AGENT_RESULTS/<RUN-ID>.json
```

`verify` only executes the fixed argv arrays accepted in the Verification Profile and only when `--allow-command-execution` is supplied. This is not an OS-level sandbox; the operator must trust or isolate the command environment. A successful Task report alone does not prove semantically different Gate subjects.

Blocking and resuming remain explicit:

```bash
python .harness/engine/project-harness.py block \
  --project . \
  --reason "material blocker" \
  --option "safe option"

python .harness/engine/project-harness.py resume \
  --project . \
  --resolution "approved resolution"
```

A control-plane safety violation cannot be resumed in place; restore a trusted handoff or restart through the prescribed recovery route.

## Stage Gate acceptance

The governed Stage-boundary cycle is:

```text
complete last ordinary mandatory Task
→ deterministic final-baseline Gate-readiness evaluation
→ [STAGE_ACCEPTANCE_PREPARATION Task through next → verify → complete, only when evidence gaps exist]
→ VERIFYING
→ stage-status
→ prepare-stage-approval
→ review/add exact evidence and formal conclusions
→ accept-stage
→ [resume-stage-gate when an honest formal review persists BLOCKED]
```

Start with the exact current context instead of opening private Gate files:

```bash
python .harness/engine/project-harness.py stage-status --project .
```

`stage-status` returns the active/target levels, exact Stage Plan and Gate refs/paths/revisions, Gate SHA-256, canonical product `baseline_revision`, result counts, required Work Package and critical blocker statuses, and `next_operator_route`. For `VERIFYING`, the route is `PREPARE_STAGE_APPROVAL`. For a persisted Gate-related `BLOCKED` state, the route is `RESUME_STAGE_GATE`; it never conflates that blocker with ordinary Task execution recovery.

Create a persistent operator file; console output is only a summary and never substitutes for the record:

```bash
python .harness/engine/project-harness.py prepare-stage-approval \
  --project . \
  --output ../operator-records/prototype-stage-approval.yaml
```

An output inside the Project Instance is allowed only below `.harness/operator/APPROVALS/`. Existing files are not replaced unless `--force` is supplied. For an unchanged exact Gate and product baseline, generated bytes are deterministic. The `prepare-stage-approval` command itself does not execute repository commands, change Stage/Gate status, create a Decision or Acceptance Report, accept a Stage, modify the product tree, or create a Work Package. This read-only operator-record command is distinct from the runtime `STAGE_ACCEPTANCE_PREPARATION` route created earlier only when deterministic Gate-readiness evaluation finds missing exact-baseline evidence.

The generated document validates against `SCHEMA-STAGE-APPROVAL@1` as an explicit non-approval:

```yaml
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
  target_level: PROTOTYPE
  acceptance_method: EXECUTED_STAGE_WORK
  stage_plan_ref: STG-MYPROJECT-PROTOTYPE-001@2
  stage_plan_path: .harness/stages/PLANS/STG-MYPROJECT-PROTOTYPE-001@2.yaml
  gate_ref: GATE-MYPROJECT-PROTOTYPE-001@2
  gate_path: .harness/stages/GATES/GATE-MYPROJECT-PROTOTYPE-001@2.yaml
  gate_digest: sha256:<exact-gate-file-digest>
  baseline_revision: tree:sha256:<exact-current-product-tree-digest>
  outcome_results:
    - outcome_ref: working_primary_flow
      status: UNKNOWN
      evidence_refs: []
      rationale: null
      validator: null
  criteria_results:
    - criterion_ref: <exact-current-level-criterion>
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

The actual file also contains the complete exact definitions and result skeletons for required outcomes, level criteria, hard constraints and profile controls; current required Work Packages and critical blockers; last accepted report/baseline context; compatible normalized evidence candidates with kind/base/provenance/digest/subject mappings; unresolved gaps; and a preparation fingerprint. Candidate evidence is guidance only. It never changes `UNKNOWN` to `PASS` and never creates a formal conclusion.

Before `accept-stage`, the responsible operator/validator must fill the generated record without deleting or changing its exact-bound context:

- set `record_state: APPROVED`, a canonical `DEC-*` `id`, `approved: true`, canonical `ACT-*` `actor`, and UTC `approved_at` ending in `Z`;
- close every mandatory result with `PASS`, or with an applicable and justified `NOT_APPLICABLE`; `PARTIAL`, `FAIL`, and `UNKNOWN` block acceptance;
- for `PASS`, add exact normalized `EVD-*` refs compatible with the subject and required evidence kind; add rationale and validator;
- set `permitted_use.status: CONFIRMED`, then document `known_limitations` and `next_stage_gaps`.

A malformed record—schema error, invalid `NOT_APPLICABLE`, stale/wrong exact refs, or invalid evidence binding—fails before mutation. A structurally valid formal review with any mandatory `UNKNOWN`, `PARTIAL`, or `FAIL` conclusion is different: `accept-stage` atomically writes new `BLOCKED` Stage Plan and Gate revisions, an immutable `STAGE_GATE_BLOCKER`, project route `RESOLVE_STAGE_GATE`, and no Acceptance Report or next-stage activation.

Recover only that blocker with:

```bash
python .harness/engine/project-harness.py resume-stage-gate --project .
```

Recovery revalidates the current product baseline and evidence. It creates new revisions and either returns to `ACTIVE` with one idempotent evidence-preparation Task or to `VERIFYING` when all evidence gaps are already closed. Blocked history is never rewritten. The ordinary `block`/`resume` Task route remains separate.

A non-empty string is not evidence. Every closing ref must resolve to an existing normalized immutable artifact at `.harness/evidence/<EVD-ID>.yaml`. Before any Stage mutation, `accept-stage` checks exact internal id/ref, schema version, allowed semantic kind, positive status, provenance and source digest, requested criterion/outcome/profile-control mapping, exact current product-tree `base_revision`, and criterion-specific `required_evidence_kinds`. Dangling, legacy, malformed, wrong-kind, wrong-subject, stale, failed/blocked, source-tampered, or duplicate-conflicting evidence blocks the whole acceptance. `USER_CLAIM` alone cannot close a mandatory result.

Normalized evidence example (the source report must already exist and its digest must match):

```yaml
verification_evidence:
  schema_version: 1
  id: EVD-MYPROJECT-001
  ref: EVD-MYPROJECT-001
  kind: TEST_REPORT
  status: PASS
  provenance:
    source_type: INDEPENDENT_VALIDATION_REPORT
    source_ref: VAL-MYPROJECT-PROTOTYPE-001
    producer: ACT-VALIDATOR-001
  base_revision: tree:sha256:<exact-current-product-tree-digest>
  criterion_refs: [<exact criterion from generated draft>]
  outcome_refs: [<exact outcome from generated draft>]
  profile_control_refs: []
  source_bindings:
    - ref: VAL-MYPROJECT-PROTOTYPE-001
      path: .harness/reports/VAL-MYPROJECT-PROTOTYPE-001.yaml
      sha256: sha256:<exact-source-file-digest>
  created_at: 2026-08-20T12:00:00Z
```

Run formal acceptance only after validation and review:

```bash
python .harness/engine/project-harness.py accept-stage \
  --project . \
  --level PROTOTYPE \
  --approval ../operator-records/prototype-stage-approval.yaml
```

`accept-stage` revalidates the strict schema before mutation and requires the stored Plan/Gate refs, revisions, paths, digests, baseline, definitions, current Work Package/blocker views and preparation fingerprint to match the current Project Instance exactly. A product-tree change or a new Gate revision makes the old record stale and requires a newly prepared draft. The accepted Gate revision and immutable Stage Acceptance Report store the same sorted evidence refs and exact `{ref, path, sha256}` bindings; `validate-project` re-resolves the closure and fails if accepted evidence or a bound project-local source is deleted or changed.

The supported public Python API exposes the same flow and baseline calculation; private helpers are not an operator contract:

```python
from pathlib import Path
from project_harness import prepare_stage_approval, product_baseline_revision, stage_status

root = Path('.')
status = stage_status(root)
baseline = product_baseline_revision(root)
result = prepare_stage_approval(root, Path('../operator-records/prototype-stage-approval.yaml'))
```

Runtime Task verification evidence remains bound to its exact post-verification product revision and does not automatically prove every Stage result. The preparation flow enumerates compatible candidates and gaps but does not promote evidence or issue approval automatically.

`SATISFIED_BY_BASELINE` is allowed only for Brownfield/Hybrid. `assessment_ref` must be a canonical `<assessment-id>@<positive-integer-revision>` (no wildcard/prefix/suffix or leading-zero revision), and `assessment_digest` must be `sha256:<64 lowercase hex>`. The engine opens only `.harness/stages/ASSESSMENTS/<assessment-id>@<revision>.yaml`; it never uses a prefix glob, latest candidate, or lexicographic fallback. Before Stage recovery/transaction it verifies the exact filename, sole `maturity_assessment` envelope, internal `id`, integer `revision`, and SHA-256 of the exact file bytes.

Exact resolution is followed by a zero-write freshness preflight. The assessment must be `COMPLETED` and match the current canonical product-tree digest, approval baseline, Stage State target, previous accepted level, immutable accepted user claim, and sequential active-stage context. Requested acceptance cannot exceed the candidate recomputed from mandatory criteria, and stale/other-base evidence cannot close accepted criteria. Any mismatch returns structured `STALE` reasons and creates only a new immutable validation revision that references the source assessment, preserves its original repository revision, and records the detected current revision/context. No Decision, Acceptance Report, accepted Stage revision, highest-level change, or next-stage activation occurs. A new assessment for the current tree/context can subsequently be accepted. Multiple prior stages remain one all-or-nothing transaction over one exact current assessment, with a separate report per accepted level.

## Same-level maintenance

Use the public governed route when the accepted product scope needs a bounded bugfix, documentation correction, refactoring, or stabilization without a maturity change:

```bash
python .harness/engine/project-harness.py start-maintenance \
  --project . \
  --plan ../operator-records/maintenance-plan.yaml

python .harness/engine/project-harness.py next --project .
python .harness/engine/project-harness.py verify --project . --allow-command-execution
python .harness/engine/project-harness.py complete \
  --project . \
  --result .harness/runtime/AGENT_RESULTS/<RUN-ID>.json
```

The strict `SCHEMA-MAINTENANCE-PLAN@1` record is exact-bound to the current `highest_accepted_level`, canonical target, `last_acceptance_ref`, and accepted scope. Its start Decision must approve `MAINTAIN_CURRENT_STAGE`, and its Work Package and every Task must use the accepted level as `implementation_stage` with `future_stage_work: FORBIDDEN`. Start is rejected while a Run, Stage-planning application, Gate transition, or another maintenance route is open.

A successful start preserves Stage State and acceptance history while creating the immutable plan and Decision, revisioned WP/Tasks, DAG, Verification Profiles, Context/Prompt Plans, maintenance index/current state, `NEXT_TASK`, and one idempotent first JIT reservation. Maintenance executable artifacts carry the exact route binding:

```yaml
maintenance_route: MAINTAIN_CURRENT_STAGE
maintenance_plan_ref: RQP-...@<revision>
implementation_stage: <highest_accepted_level>
```

The ordinary `next → verify → complete` lifecycle executes the Tasks. Completing the final mandatory Task closes the WP as `COMPLETED`, writes an immutable `MAINTENANCE_COMPLETION` report with Decision/Task Report/Run/evidence references, clears maintenance current state, and restores the previous valid route. It does not run Stage acceptance or change `highest_accepted_level`, target, accepted Stage Plan/Gate revisions, Stage Acceptance Reports, or pre-existing completed Runs.

Pre-execution cancellation requires a separate strict formal record:

```bash
python .harness/engine/project-harness.py cancel-maintenance \
  --project . \
  --approval ../operator-records/maintenance-cancel.yaml
```

Cancellation is allowed only before completed or observed product-changing work and only when the product still matches the trusted Run snapshot. It creates immutable `CANCEL_MAINTENANCE` Decision/report history and terminal Task/WP revisions; it never performs an automatic rollback. After a valid `COMPLETED`, `CANCELLED`, or `SUPERSEDED` maintenance WP, `level-up` is no longer blocked. Exact replay of the same plan/Decision is idempotent and cannot duplicate WP/Tasks/Runs or the first JIT bundle.

Python callers may use `project_harness.start_maintenance(root, plan_path)` and `project_harness.cancel_maintenance(root, approval_path)`. Stored route records live under `.harness/maintenance/PLANS/`, `.harness/maintenance/REPORTS/`, `.harness/maintenance/INDEX.yaml`, and `.harness/maintenance/CURRENT.yaml`.

## Level-up after the accepted target

A new target must be strictly above the highest accepted level and requires a separate Decision record. Open same-level maintenance work blocks level-up.

```json
{
  "level_up_approval": {
    "id": "DEC-MYPROJECT-LEVEL-UP-001",
    "approved": true,
    "actor": "ACT-USER-001",
    "approved_at": "2026-08-18T12:00:00Z",
    "target_level": "MVP",
    "rationale": "Approve a new progression cycle to Production MVP."
  }
}
```

```bash
python .harness/engine/project-harness.py level-up \
  --project . \
  --target MVP \
  --approval ./level-up-approval.json
```

Only the nearest next stage becomes active. In the same crash-consistent Stage transaction, `level-up` writes the canonical target to `STAGE_STATE.yaml` and synchronizes `.harness/config/PROJECT.yaml` plus `.harness/state/CURRENT_STATE.yaml`. `.harness/state/PROJECT_INPUT_ACCEPTED.yaml` is not rewritten and preserves the initial accepted target. Accepted baselines and completed Runs remain immutable. A target equal to or below the accepted level returns `TARGET_ALREADY_REACHED` without destructive changes.

## Canonical stage paths

```text
.harness/stages/STAGE_STATE.yaml
.harness/stages/PLANS/
.harness/stages/GATES/
.harness/stages/ACCEPTANCE/
.harness/stages/ASSESSMENTS/
.harness/stages/STATE_HISTORY/
.harness/stages/TRANSACTIONS/
```

The uppercase directory names are normative contract paths. For a prepared Project Instance, `.harness/stages/STAGE_STATE.yaml -> implementation.target_level` is the only canonical current-cycle target. `PROJECT.target_implementation_level` and `CURRENT_STATE.target_implementation_level` are validated projections; the initial target in `PROJECT_INPUT_ACCEPTED.yaml` may differ after level-up without constituting divergence.

## Stage transaction crash recovery

Every governed Stage mutation first reconciles `.harness/stages/TRANSACTIONS/`. Each transaction persists a complete ordered write set, immutable backups, staged candidates, old/new SHA-256 digests, operation/request identity, replayable result, timestamps, and per-entry apply/recovery state before the first canonical replacement. The durable `PREPARED` snapshot, every backup, and every staged digest are preflight-verified before `APPLYING`.

Terminal rules are strict:

- `COMMITTED` means every canonical target matches its expected new digest;
- `ROLLED_BACK` means every target matches its exact old digest or is absent when it did not exist before;
- corrupt or incomplete recovery evidence blocks mutation with `STAGE_TRANSACTION_CORRUPT` or `STAGE_TRANSACTION_RECOVERY_BLOCKED`.

`validate-project` runs automatic reconciliation before normal validation. A complete new write set with a missing commit marker is committed from verified digests; every other recoverable intermediate state is restored fully from backups. It also rejects mixed Stage indexes, Acceptance files, `CURRENT_STATE`, or `NEXT_TASK` against the latest completed transition. Re-running a committed approval returns the saved idempotent result. A rolled-back transaction id requires a new formal approval.

`ROADMAP.md` and `STATUS.md` render after canonical commit. Rendering failure returns committed success with `render_status: FAILED_RECOVERABLE`; repeating the identical command regenerates views without creating a second transition.

## Migration from v0.4.1

Only direct migration from a valid extracted v0.4.1/schema 5 Project Instance is supported. Supply a strict approved `PROJECT_INPUT@3` containing the canonical target:

```bash
python project-harness.py migrate-project \
  --project /path/to/extracted-v0.4.1-project \
  --input /path/to/PROJECT_INPUT_v3.yaml
```

Migration validates an isolated copy before replacing the source directory, preserves immutable historical Task/Run/Evidence/Decision files, does not infer accepted maturity from legacy `COMPLETED`, and is idempotent after full current-state validation. See [`MIGRATION_FROM_v0.4.1.md`](MIGRATION_FROM_v0.4.1.md).

The earlier v0.4.0→v0.4.1 guide remains in [`MIGRATION_FROM_v0.4.0.md`](MIGRATION_FROM_v0.4.0.md) for sequential upgrades.

## Distribution integrity and tests

```bash
python project-harness.py doctor
python tests/run_tests.py
PYTHONPATH=src:. python -m pytest -q tests/test_maintenance_lifecycle.py tests/test_implementation_levels.py  # optional: requires pytest
```

`doctor` verifies exact registry versions, schemas, ACTIVE seed skills, source/embedded resource parity, entry points, and—when present—the distribution manifest. The original v0.5.0 acceptance matrix contained 117 tests; PH-F06 ran 166 tests (see its dated test report). The PH-F07 documentation patch is separately verified and is not PH-F08 final release acceptance.

Release evidence is stored in:

- [`TEST_REPORT_v0.5.0.md`](TEST_REPORT_v0.5.0.md)
- [`ENGINE_VALIDATION_v0.5.0.json`](ENGINE_VALIDATION_v0.5.0.json)
- [`IMPLEMENTATION_DECISIONS_v0.5.0.md`](IMPLEMENTATION_DECISIONS_v0.5.0.md)

The synchronized documentation package is under [`docs/Project_Harness_Documentation_v0.5.1/`](docs/Project_Harness_Documentation_v0.5.1/).

## Canonical versions

```text
Engine distribution      0.5.0
Canonical schema         6
PROJECT_INPUT contract   SCHEMA-PROJECT-PREPARATION-INPUT@3
Project migration        MIG-ENGINE-0.4.1-TO-0.5.0

id_prefixes              2
project_profiles         1
statuses                 5
request_routing          2
capabilities             1
contracts                5
implementation_levels    1
```

`PROJECT_LOCK` records exact versions and SHA-256 digests for all seven registries.

## PH-F01 interim regression baseline (2026-10-23)

This v0.5.0 archive preserves the `PH_F01_INTEGRATION_MATRIX.md` / `PH_F01_TEST_REPORT.md` artifacts. PH-F02 fixes the former semantic Gate evidence regression; `tests.test_ph_f01_gate_semantics_regression` must now PASS. The three `test_ph_f03_*` active-stage planner tests were intentionally RED at the historical PH-F02 checkpoint; PH-F03 now closes that separate gap. Full-suite results for this checkpoint are in `PH_F03_TEST_REPORT.md`. See `PH_F02_TEST_REPORT.md` for the PH-F02 filtered regression run and the expected PH-F03 failures. This package is not the final v0.5.0 release.

## PH-F02 — subject-specific Stage Gate proof (2026-10-24)

This patch closes the **semantic Gate evidence** portion of v0.5.0 only; it does not implement the deferred PH-F03 active-stage planner. `complete` of a Stage-acceptance preparation Task does **not** infer Gate PASS from generic Python commands or a no-change verification. Instead, every mandatory Gate subject requires its own independent, immutable normalized `EVD-*` artifact and the additional `details.semantic_proof` contract. The record is exact-bound to the subject, kind, source and final product-tree baseline; existing source and EVD digests are checked on every Gate review.

Proof methods depend on kind: `DOCUMENT_REVIEW` for actual architecture/startup/limitations/permitted-use and related documents, `EXECUTED_TEST` for selected test execution, `OPERATOR_VERIFICATION` for accountable manual or review records, and `EXTERNAL_SOURCE` for genuinely supplied evidence with issuer/origin. A proof names coverage, individual performed checks, and the pinned source ref. An ordinary `PASS` from `py_compile`, generic `pytest`, or any unspecified verification command is **not** enough to prove an unrelated criterion. An external record without independent source provenance is not a candidate. A human must still validate **semantic sufficiency** before formal approval; SHA-256 verifies integrity, not the truth of claims.

The supported fail-closed continuation is:

1. Complete the ordinary Stage Tasks; execute the bounded `STAGE_ACCEPTANCE_PREPARATION` Task through `next → verify → complete` if Gate readiness identifies missing subjects.
2. If authentic subject evidence is still absent, the Gate persists `BLOCKED` with `RESOLVE_STAGE_GATE`. No fake PASS evidence is minted and repeating the same completed, still-unproven preparation does not create another Task.
3. An accountable operator supplies actual product/document, selected-test, operator-review, or external source artifacts and the corresponding immutable normalized `EVD-*` records at their canonical `.harness/evidence/<EVD-ID>.yaml` paths. Source files are referenced with project-relative paths and SHA-256 digests; reviewed documents may be pinned in `.harness/operator/SOURCES/`. Historical artifacts are never rewritten.
4. Run `python project-harness.py resume-stage-gate --project <root>`. After every mandatory subject has compatible final-baseline proof, the Gate transitions to `VERIFYING`; otherwise it stays blocked with a specific gap/recovery route.
5. Run `prepare-stage-approval` and submit an independent **formal** reviewed Stage decision through `accept-stage`. A draft/candidate, even if exact-bound, never approves automatically.

`details.semantic_proof` is an object with `subject_ref`, `kind`, `status: PASS`, `method`, `coverage` (specific, nonempty description), `source_ref` (one of `source_bindings[].ref`) and `checked_items` (list of concrete checks). For `EXECUTED_TEST`, add `test_ref`, and bind an independent `test_execution` source recording the same exact subject and test ref, a selected command containing `test_ref`, exit code zero, executed checks and a PASS result. For `OPERATOR_VERIFICATION`, bind an `operator_verification` document recording actor, exact subject, checks and PASS. For `EXTERNAL_SOURCE`, use `EXTERNAL_EVIDENCE_IMPORT`, source `external_evidence` with exact subject/issuer/PASS, and `provenance.details.issuer` plus `.origin`. For `DOCUMENT_REVIEW`, bind a concrete substantive product document or an operator-supplied reviewed document (not a generic `.harness/reports/` result). Architecture, startup, limitations and permitted-use documents have basic kind-specific content checks. Never use a general verification report as a document or external evidence source.

`BASELINE` acceptance / Brownfield assessment remain independent read-only governance operations. Accepted history, strict positive-only Gate semantics, applicability checks, exact canonical refs, transactions and stage fences are unchanged. The missing public planner is implemented separately by PH-F03; PH-F02 Gate proof requirements are unchanged.

## PH-F03 — планирование следующей активной стадии через публичный CLI/API

Сразу после успешного `accept-stage`, когда target ещё не достигнут, или после
`level-up` из `TARGET_LEVEL_REACHED` Stage State устанавливает
`next_route: PLAN_ACTIVE_STAGE`; `next` показывает `STAGE_PLANNING_REQUIRED`.
Только **следующий последовательный уровень** разрешён: после принятого Prototype
активируется Alpha, после принятого MVP при `level-up RELEASE` — Release.
Предыдущий accepted baseline, last Acceptance Report и принятый product scope
не пересоздаются и не переписываются.

### Операторский runbook

В каталоге исходного Engine или через установленную команду `project-harness`:

```bash
project-harness stage-status --project /path/to/project
project-harness next --project /path/to/project
project-harness prepare-active-stage-plan --project /path/to/project --output /tmp/active-stage-review.json
# Проверьте строгое содержимое active_stage_plan_review и scope каждого Task.
project-harness plan-active-stage --project /path/to/project --plan /tmp/active-stage-review.json
project-harness next --project /path/to/project
project-harness validate-project --project /path/to/project
```

При запуске из распакованного Engine поддерживается равнозначный вариант:
`python project-harness.py <command> <flags>`. `--output` — файл JSON
(также принимается JSON-синтаксис с `.yaml` расширением) **вне** product root,
либо в `.harness/operator/`. Подготовка только записывает operator draft;
она не активирует Stage, не изменяет canonical state и не утверждает
решение. Повторный вывод в тот же путь с отличным содержимым требует
`--force`. Код API:
`project_harness.stages.prepare_active_stage_plan(root, output_path, force=False)`
и `project_harness.stages.plan_active_stage(root, plan_path)`.

### Contract `SCHEMA-ACTIVE-STAGE-PLAN-REVIEW@1`

Внешний record имеет один envelope `active_stage_plan_review`; JSON Schema
лежит в `schemas/active_stage_plan_review.schema.json`. Read-only preparation
формирует machine-validated поля:

- `schema_version: 1`, `schema_ref`, `record_kind: ACTIVE_STAGE_PLAN_REVIEW`,
  `id: RQP-...`, `revision: 1`, `route: PLAN_ACTIVE_STAGE`;
- `binding`: current Stage State revision и digest, `highest_accepted_level`,
  `active_stage`, canonical `target_level`, exact Stage Plan/Gate ref и digest,
  exact last Acceptance Report ref и digest, accepted/current product tree
  baselines, immutable scope/input digests и (при наличии) завершённую
  maintenance report ref/digest;
- `planning_basis`: `required_outcomes`, level criteria, profile controls,
  hard constraints, accepted requirements/constraints, scope in/out,
  predecessor `next_stage_gaps`, known limitations, permitted use и
  список существующих product files;
- `work_packages`: текущая Stage, атомарные Tasks с exact criterion refs,
  зависимостями, ограниченными path scopes, routes, verification и
  acceptance criteria; `candidate_work_digest` фиксирует исходное предложение;
- `review: {material_change: false, scope_confirmed: true, decision: null}`;
  `future_stage_work: FORBIDDEN`.

Для **неизменённого** draft отдельный формальный approval не создаётся:
вызов `plan-active-stage` считается явным принятием подготовленного
плана только внутри ранее принятого scope. Изменение `work_packages`
(например, Task purpose/verification) требует `review.decision` со
строгим `kind: ACTIVE_STAGE_PLAN_REVIEW`, canonical
`id: DEC-<record-id-without-RQP->-REVIEW`, `approved: true`,
`actor: ACT-*`, ISO date-time `approved_at` и непустым `rationale`.
Новые requirements, future-stage Tasks, защищённые paths и
`review.material_change: true` блокируются даже при формальном review:
изменение принятого scope должно проходить отдельный предусмотренный
процесс изменения, а не подменяться Stage planning.

### Application и продолжение

`plan-active-stage` перед любой записью перепроверяет все bindings,
текущий product-tree digest, согласованность last accepted history и
отсутствие текущего Run, незавершённого Gate, конкурирующего planning и
открытой maintenance. Если baseline изменился после принятого Stage,
требуется подтверждённая завершённая maintenance; её report связан
с exact last Acceptance и current draft. Stale/malformed records отклоняются
**без** Stage mutation.

Governed application делает один journaled `PLAN_ACTIVE_STAGE` commit:
новые revisioned active Stage Plan и Gate, Work Packages/Tasks,
dependency DAG, отдельные Verification/Context/Prompt Plans, indexes,
`STAGE_STATE`, `CURRENT_STATE` и `NEXT_TASK`. Gate сохраняет точные
outcome/criterion/profile/hard-constraint bindings; одна первая Task получает
`READY` и JIT bundle. Положительный результат: `STAGE_PLANNED` и
`first_jit.status: READY_FOR_CODEX`. Повтор идентичного `--plan` после
COMMITTED — идемпотентный replay; не создаёт повторный Run/Task/Gate.

При сбое **до commit** Stage transaction восстанавливается через
существующий `recover_stage_transactions`; ID `ROLLED_BACK` больше не
используется. После recovery оператор выпускает draft заново командой
`prepare-active-stage-plan --force`, получает новый ID с суффиксом
`-RETRY-NN`, проверяет его и запускает `plan-active-stage`.
При interruption **после commit** повтор того же `plan-active-stage`
получает persisted commit result и пытается восстановить первый JIT;
план/accepted history не дублируются. При recoverable ошибке JIT можно
выполнить `next --project <root>`.

План не исполняет продуктовые команды и не утверждает Stage Gate.
Внешний Codex/оператор последовательно выполняет `next → verify → complete`,
затем обязательную subject-specific Gate proof процедуру PH-F02 и
формальный `accept-stage`. Само наличие compiled JIT **не доказывает**
достижение criteria и не меняет highest accepted level.

## PH-F05 — intake source/workspace separation (2026-10-24)

`start-intake --force` now rejects a workspace that contains a supplied source,
initial PROJECT_INPUT file or repository, or is inside any of them (and vice versa).
This prevents accidental deletion during workspace reset and recursive source copying.
Use a separate external workspace. The rule applies to both CLI and Python API.

Acceptance tests: `PYTHONPATH=src:. python -m unittest tests.test_ph_f05_intake_acceptance -v`.
The browser GPT remains responsible for semantic interpretation and explicit approvals;
Engine readiness cannot itself prove that the interview asked each question.

## PH-LW-03 — локальный application service (2026-11-02, 0.5.1 WIP)

Без HTTP/UI реализован `project_harness.local_web_service.LocalWebService`: регистрация существующих intake/workspace roots доверенным оператором, read-only status с exact refs/fingerprint, typed allowlisted requests, отдельный `update_provisional_draft` с atomic update и invalidation approvals, per-project OS operation guard для service/CLI/public core API, один bounded worker, idempotent durable operation receipts и явная crash reconciliation. Публичные `next`, `check-intake`, `prepare`, `verify` (без host commands) и `validate-project` вызывают **ядро**, не web-интерпретацию state. Другие Web actions пока disabled, automatic executor не включён. Проверки: `PYTHONPATH=src:. python -m unittest -v tests.test_ph_lw_03_service`. Native Windows/NTFS **NOT RUN**, full v0.5.1 **NO-GO**; см. [PH-LW-03 technical contract](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/08_PH_LW_03_Application_Service_and_Operation_Recovery.md).
