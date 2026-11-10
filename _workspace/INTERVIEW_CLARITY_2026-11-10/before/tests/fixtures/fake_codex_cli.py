#!/usr/bin/env python3
"""PH-051-02 deterministic fake Codex *test double*, not a public adapter.

This file is meant to run ONLY inside the future rootless Podman test runner.
Unit tests may import the pure `agent_result` helper, but MUST NOT spawn this
program on host as an automatic-execution substitute.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SCENARIOS = frozenset({
    "success", "exit_nonzero", "timeout", "missing_output", "invalid_output",
    "output_flood", "child_process", "control_write", "wrong_paths",
    "secret_echo", "secret_product", "secret_result", "baseline_drift",
})


def agent_result(run_id: str, task_id: str, *, changed: str = "implemented.txt") -> dict:
    """A deliberately *untrusted* candidate AGENT-TASK-RESULT@1 object."""
    return {
        "schema_version": 1,
        "task_ref": task_id,
        "run_ref": run_id,
        "status": "COMPLETED",
        "summary": "fake CLI produced a candidate; independent verification is required",
        "changes": {"added": [changed], "modified": [], "deleted": []},
        "commands": [], "tests": [], "evidence": [], "blockers": [],
    }


def run_case(scenario: str, *, workspace: Path, control: Path, result: Path,
             run_id: str, task_id: str) -> int:
    if scenario not in SCENARIOS:
        raise ValueError("unknown fixture scenario")
    if scenario == "exit_nonzero":
        return 17
    if scenario == "timeout":
        time.sleep(3600)  # the trusted container runner must terminate on its own limit
        return 0
    if scenario == "child_process":
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3600)"],
                                 stdin=subprocess.DEVNULL)
        child.wait()  # container teardown must terminate process *and* children
        return 0
    if scenario == "output_flood":
        chunk = "F" * 65536
        for _ in range(256):
            sys.stdout.write(chunk)
            sys.stdout.flush()
        return 0
    if scenario == "missing_output":
        return 0
    if scenario == "invalid_output":
        result.parent.mkdir(parents=True, exist_ok=True)
        result.write_text('{"schema_version": 1,', encoding="utf-8")
        return 0
    if scenario == "control_write":
        # The real sandbox must deny this, rather than trusting fake CLI's exit.
        try:
            (control / "illicit.txt").write_text("illegal control write\n", encoding="utf-8")
        except OSError:
            return 13
    filename = "outside_allowed.txt" if scenario == "wrong_paths" else "implemented.txt"
    workspace.mkdir(parents=True, exist_ok=True)
    content = "deterministic fixture output\n"
    if scenario == "secret_product":
        content += os.environ.get("FAKE_CLI_SECRET", "")
    (workspace / filename).write_text(content, encoding="utf-8")
    candidate = agent_result(run_id, task_id, changed=filename)
    if scenario in {"secret_echo", "secret_result"}:
        value = os.environ.get("FAKE_CLI_SECRET", "")
        if scenario == "secret_echo":
            sys.stdout.write(value + "\n")
        else:
            candidate["summary"] += " " + value
    if scenario == "baseline_drift":
        # The *test orchestrator*, not the agent, mutates canonical product
        # after this result to assert the BASELINE_CHANGED apply fence.
        candidate["notes"] = ["test orchestrator must change canonical baseline externally"]
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps(candidate, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True, choices=sorted(SCENARIOS))
    parser.add_argument("--workspace-path", required=True, type=Path)
    parser.add_argument("--control-path", required=True, type=Path)
    parser.add_argument("--result-file", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--task-id", required=True)
    args = parser.parse_args(argv)
    control = args.control_path.parent if args.control_path.is_file() else args.control_path
    return run_case(args.scenario, workspace=args.workspace_path,
                    control=control, result=args.result_file,
                    run_id=args.run_id, task_id=args.task_id)


if __name__ == "__main__":
    raise SystemExit(main())
