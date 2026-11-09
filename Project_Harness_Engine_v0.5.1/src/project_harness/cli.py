from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

from .active_stage_planning import prepare_active_stage_plan, plan_active_stage
from .compiler import prepare_handoff
from .errors import HarnessError, ValidationFailure
from .intake import check_intake, start_intake
from .migration import migrate_project
from .maintenance import cancel_maintenance, start_maintenance
from .resources import distribution_root
from .runtime import (block_current, complete_current, execute_current, executor_doctor,
                      next_task, project_status, resume_blocked, verify_current)
from .serialization import load_data, write_data
from .stage_gate_lifecycle import resume_stage_gate
from .stages import accept_stage, assess_maturity, level_up, prepare_stage_approval, stage_status
from .util import ENGINE_VERSION
from .validation import doctor, validate_handoff, validate_project_directory


def _emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False))


def _exit_for_status(status: str | None) -> int:
    if status in {"WAITING_INPUT", "WAITING_DECISION", "BLOCKED", "TIMED_OUT", "FAILED_RETRYABLE"}:
        return 3
    if status in {"FAIL", "FAILED", "INVALID"}:
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project-harness",
        description="Project Harness v0.5.1 WIP — stage governance and opt-in rootless local execution.",
    )
    parser.add_argument("--version", action="version", version=ENGINE_VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    ui_parser = sub.add_parser("ui", help="Launch authenticated, offline, 127.0.0.1-only Local Web manual shell.")
    ui_parser.add_argument("--app-data", type=Path, help="Trusted local application-data directory, never a web request path.")
    ui_parser.add_argument("--no-browser", action="store_true", help="Headless diagnostics only; no browser session bootstrap.")

    doctor_parser = sub.add_parser("doctor", help="Validate distribution registries, schemas, skills and manifest.")
    doctor_parser.add_argument("--root", type=Path)
    doctor_parser.add_argument("--skip-manifest", action="store_true")

    start = sub.add_parser("start-intake", help="Create an external provisional intake workspace without modifying the target repository.")
    start.add_argument("--workspace", type=Path, required=True)
    start.add_argument("--project-name", required=True)
    start.add_argument("--mode", choices=["greenfield", "brownfield", "hybrid", "GREENFIELD", "BROWNFIELD", "HYBRID"], required=True)
    start.add_argument("--source", type=Path, action="append", default=[])
    start.add_argument("--repository", type=Path)
    start.add_argument("--input", type=Path)
    start.add_argument("--force", action="store_true")

    check = sub.add_parser("check-intake", help="Validate PROJECT_INPUT.yaml and regenerate missing questions/readiness.")
    check.add_argument("--workspace", type=Path, required=True)

    prepare = sub.add_parser("prepare", help="Compile a validated Codex Handoff ZIP from an approved intake workspace.")
    prepare.add_argument("--workspace", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--keep-directory", type=Path)

    validate = sub.add_parser("validate-handoff", help="Validate an immutable initial handoff directory or ZIP, including its baseline manifest.")
    validate.add_argument("--project", type=Path, required=True, help="Handoff root directory or ZIP archive.")

    validate_project = sub.add_parser("validate-project", help="Validate mutable project state after Codex execution without enforcing the original handoff manifest.")
    validate_project.add_argument("--project", type=Path, required=True, help="Extracted handoff/project root directory.")

    migrate = sub.add_parser("migrate-project", help="Migrate v0.4.1 or v0.5.0 Project Instances to the current compatible engine contract, preserving accepted history.")
    migrate.add_argument("--project", type=Path, required=True, help="Existing compatible v0.4.1 or v0.5.0 Project Instance directory.")
    migrate.add_argument("--input", type=Path, help="Optional approved input for v0.4.1 migration only (forbidden for v0.5.0 to v0.5.1).")

    status = sub.add_parser("status", help="Show persisted project/task/run state.")
    status.add_argument("--project", type=Path, required=True)

    nxt = sub.add_parser("next", help="Return or JIT-compile the current READY task bundle.")
    nxt.add_argument("--project", type=Path, required=True)

    # Both project-scoped automatic operations are explicit and opt-in only.
    # No CLI option can select a second sandbox/backend or host execution.
    for name, description in (
        ("executor-doctor", "Validate exact project ADP/SBX and real rootless Podman isolation without running a Task."),
        ("execute-current", "Governed current READY Task execution, independent sandbox verification and atomic apply."),
    ):
        auto = sub.add_parser(name, help=description)
        auto.add_argument("--project", type=Path, required=True)
        auto.add_argument("--adapter-profile", help="Only the exact pinned project ADP ref/path (no profile switching).")
        auto.add_argument("--network", choices=["NONE", "EXPLICIT_APPROVED_EGRESS"], default=None)
        auto.add_argument("--approval", type=Path, help="Exact per-Run approval; unimplemented egress cannot be enabled by this flag.")
        auto.add_argument("--keep-execution-root", action="store_true", help="Requires an explicit debug policy; rejected by current strict policy.")

    verify = sub.add_parser("verify", help="Independently check actual writes, expected paths and declared verification commands.")
    verify.add_argument("--project", type=Path, required=True)
    verify.add_argument("--allow-command-execution", action="store_true")
    manual_context = sub.add_parser('task-manual-context', help='Read exact Task manual-check binding and product source digests.')
    manual_context.add_argument('--project', type=Path, required=True)
    manual_intake = sub.add_parser('record-task-manual-evidence', help='Record explicit operator observations; never executes commands or completes a Task.')
    manual_intake.add_argument('--project', type=Path, required=True)
    manual_intake.add_argument('--input', type=Path, required=True)
    manual_intake.add_argument('--confirm', action='store_true')

    complete = sub.add_parser("complete", help="Accept a PASS-verified Agent Task Result and transition to the next task.")
    complete.add_argument("--project", type=Path, required=True)
    complete.add_argument("--result", type=Path, required=True)

    block = sub.add_parser("block", help="Record a material blocker and safe recovery routes.")
    block.add_argument("--project", type=Path, required=True)
    block.add_argument("--reason", required=True)
    block.add_argument("--option", action="append", default=[])

    resume = sub.add_parser("resume", help="Resolve an OPEN blocker and compile a new run attempt.")
    resume.add_argument("--project", type=Path, required=True)
    resume.add_argument("--resolution", required=True)
    resume.add_argument("--blocker")

    stage = sub.add_parser("stage-status", help="Show persisted target, active, observed and accepted implementation levels.")
    stage.add_argument("--project", type=Path, required=True)

    prepare_approval = sub.add_parser("prepare-stage-approval", help="Write a deterministic exact-bound Stage approval draft without approving or mutating the Stage.")
    prepare_approval.add_argument("--project", type=Path, required=True)
    prepare_approval.add_argument("--output", type=Path, required=True)
    prepare_approval.add_argument("--force", action="store_true")

    prepare_active = sub.add_parser("prepare-active-stage-plan", help="Write a read-only exact-bound draft for the next active Stage, without activating Tasks.")
    prepare_active.add_argument("--project", type=Path, required=True)
    prepare_active.add_argument("--output", type=Path, required=True)
    prepare_active.add_argument("--force", action="store_true")

    apply_active = sub.add_parser("plan-active-stage", help="Governed application of a reviewed, exact-bound active Stage work plan.")
    apply_active.add_argument("--project", type=Path, required=True)
    apply_active.add_argument("--plan", type=Path, required=True)

    resume_gate = sub.add_parser("resume-stage-gate", help="Revalidate and recover only a persisted Stage Gate blocker.")
    resume_gate.add_argument("--project", type=Path, required=True)

    assess = sub.add_parser("assess-maturity", help="Run a read-only Brownfield maturity assessment without executing repository commands.")
    assess.add_argument("--workspace", type=Path, required=True)
    assess.add_argument("--evidence", type=Path)

    accept = sub.add_parser("accept-stage", help="Atomically accept a VERIFYING Stage using a formal approval record.")
    accept.add_argument("--project", type=Path, required=True)
    accept.add_argument("--level", choices=["PROTOTYPE", "ALPHA", "BETA", "MVP", "RELEASE"], required=True)
    accept.add_argument("--approval", type=Path, required=True)

    level = sub.add_parser("level-up", help="Set a higher target and activate only the nearest next Stage using a formal approval record.")
    level.add_argument("--project", type=Path, required=True)
    level.add_argument("--target", choices=["PROTOTYPE", "ALPHA", "BETA", "MVP", "RELEASE"], required=True)
    level.add_argument("--approval", type=Path, required=True)

    start_maint = sub.add_parser("start-maintenance", help="Atomically start an exact-bound governed same-level maintenance route.")
    start_maint.add_argument("--project", type=Path, required=True)
    start_maint.add_argument("--plan", type=Path, required=True)

    cancel_maint = sub.add_parser("cancel-maintenance", help="Cancel open maintenance before any completed product-changing Task.")
    cancel_maint.add_argument("--project", type=Path, required=True)
    cancel_maint.add_argument("--approval", type=Path, required=True)

    demo = sub.add_parser("demo", help="Build the bundled greenfield handoff fixture.")
    demo.add_argument("--output-dir", type=Path, required=True)
    demo.add_argument("--keep-directory", action="store_true")
    return parser


def _demo(output_dir: Path, keep: bool) -> dict[str, Any]:
    root = distribution_root()
    fixture = root / "fixtures/demo_project_input.json"
    if not fixture.exists():
        raise ValidationFailure("Bundled demo fixture is missing", str(fixture))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    workspace = output_dir / "demo-intake"
    if workspace.exists():
        shutil.rmtree(workspace)
    start_intake(
        workspace,
        project_name="Harness Demo Task CLI",
        mode="GREENFIELD",
        initial_input=fixture,
        force=True,
    )
    output = output_dir / "harness-demo-codex-handoff.zip"
    keep_directory = output_dir / "harness-demo-codex-handoff" if keep else None
    return prepare_handoff(workspace, output, keep_directory=keep_directory)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "ui":
            from .local_web_launcher import run_local_web
            return run_local_web(app_data=args.app_data, open_browser=not args.no_browser)
        elif args.command == "doctor":
            result = doctor(args.root, check_manifest=not args.skip_manifest)
        elif args.command == "start-intake":
            result = start_intake(
                args.workspace,
                project_name=args.project_name,
                mode=args.mode,
                sources=args.source,
                repository=args.repository,
                initial_input=args.input,
                force=args.force,
            )
        elif args.command == "check-intake":
            result = check_intake(args.workspace)
        elif args.command == "prepare":
            result = prepare_handoff(args.workspace, args.output, keep_directory=args.keep_directory)
        elif args.command == "validate-handoff":
            result = validate_handoff(args.project)
        elif args.command == "validate-project":
            result = validate_project_directory(args.project)
        elif args.command == "migrate-project":
            result = migrate_project(args.project, input_path=args.input)
        elif args.command == "status":
            result = project_status(args.project)
        elif args.command == "next":
            result = next_task(args.project)
        elif args.command == "executor-doctor":
            result = executor_doctor(args.project, adapter_profile=args.adapter_profile,
                                     network=args.network, approval=args.approval,
                                     keep_execution_root=args.keep_execution_root)
        elif args.command == "execute-current":
            result = execute_current(args.project, adapter_profile=args.adapter_profile,
                                     network=args.network, approval=args.approval,
                                     keep_execution_root=args.keep_execution_root)
        elif args.command == "verify":
            result = verify_current(args.project, allow_command_execution=args.allow_command_execution)
        elif args.command == 'task-manual-context':
            from .task_manual_evidence import manual_evidence_context
            result = manual_evidence_context(args.project)
        elif args.command == 'record-task-manual-evidence':
            from .task_manual_evidence import record_manual_evidence, parse_document, MAX_BYTES
            try:
                with args.input.open('rb') as stream: document = parse_document(stream.read(MAX_BYTES+1))
            except OSError as exc:
                raise ValidationFailure('Cannot read Task manual evidence input', str(exc)) from exc
            result = record_manual_evidence(args.project, document, confirmed=args.confirm)
        elif args.command == "complete":
            result = complete_current(args.project, args.result)
        elif args.command == "block":
            result = block_current(args.project, args.reason, options=args.option or None)
        elif args.command == "resume":
            result = resume_blocked(args.project, resolution=args.resolution, blocker_ref=args.blocker)
        elif args.command == "stage-status":
            result = stage_status(args.project)
        elif args.command == "prepare-stage-approval":
            result = prepare_stage_approval(args.project, args.output, force=args.force)
        elif args.command == "prepare-active-stage-plan":
            result = prepare_active_stage_plan(args.project, args.output, force=args.force)
        elif args.command == "plan-active-stage":
            result = plan_active_stage(args.project, args.plan)
        elif args.command == "resume-stage-gate":
            result = resume_stage_gate(args.project)
        elif args.command == "assess-maturity":
            result = assess_maturity(args.workspace, evidence_path=args.evidence)
        elif args.command == "accept-stage":
            result = accept_stage(args.project, args.level, args.approval)
        elif args.command == "level-up":
            result = level_up(args.project, args.target, args.approval)
        elif args.command == "start-maintenance":
            result = start_maintenance(args.project, args.plan)
        elif args.command == "cancel-maintenance":
            result = cancel_maintenance(args.project, args.approval)
        elif args.command == "demo":
            result = _demo(args.output_dir, args.keep_directory)
        else:  # pragma: no cover
            parser.error("unknown command")
            return 2
        _emit(result)
        return _exit_for_status(result.get("status") if isinstance(result, dict) else None)
    except HarnessError as exc:
        payload = {
            "status": exc.code,
            "message": exc.message,
            "details": exc.details,
        }
        _emit(payload)
        return exc.exit_code
    except KeyboardInterrupt:
        _emit({"status": "CANCELLED", "message": "Interrupted"})
        return 130
    except Exception as exc:  # Last-resort structured failure; never fabricate success.
        _emit({"status": "INTERNAL_ERROR", "message": str(exc), "type": type(exc).__name__})
        return 70


if __name__ == "__main__":
    raise SystemExit(main())
