"""PH-051-07: independent, fail-closed verification of disposable product.

Pure bounded service; PH-051-09 will connect it to the governed Run route.
Never writes to the canonical project or issues Stage Gate evidence.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from project_harness.workspace import snapshot_product, diff_snapshots, validate_scope
from project_harness.sandbox.profiles import SandboxPolicyError, validate_sandbox_profile, validate_container_executable
from project_harness.sandbox.podman_rootless import RootlessPodmanRunner


def verify_disposable(*, canonical_project_root: Path, execution_root: Path,
                      sandbox_profile: dict[str, Any], task_contract: dict[str, Any],
                      baseline_files: dict[str, Any], runner: RootlessPodmanRunner | None = None) -> dict[str, Any]:
    """Perform fresh kernel checks in separate Podman processes, never the agent process.

    The result is only a verification decision for a later governed apply step.
    A successful agent result is intentionally neither accepted nor consulted.
    """
    def fail(reason: str, **details: Any) -> dict[str, Any]:
        return {"status": "FAIL", "reason_code": reason, "apply_allowed": False, **details}

    canonical_project_root = Path(canonical_project_root).resolve()
    execution_root = Path(execution_root).resolve()
    try:
        profile = validate_sandbox_profile(sandbox_profile)
        if profile["network_mode"] != "NONE":
            return fail("NETWORK_NOT_APPROVED")
        if not isinstance(baseline_files, dict) or not isinstance(task_contract, dict):
            return fail("VERIFICATION_FAILED")
        verification = task_contract.get("verification") or {}
        commands = verification.get("commands") or []
        if not isinstance(commands, list) or not commands:
            return fail("VERIFICATION_FAILED", diagnostic="No independent verification commands")
        product = execution_root / "product"
        # The trusted snapshot must still bind the canonical product tree;
        # neither an agent PASS nor a stale disposable copy can substitute it.
        if snapshot_product(canonical_project_root) != baseline_files:
            return fail("BASELINE_CHANGED")
        # Avoid executing even a valid command before validating actual scope.
        before = snapshot_product(product)
        diff = diff_snapshots(baseline_files, before)
        scope = validate_scope(diff, task_contract.get("scope") or {})
        if scope.get("status") != "PASS":
            return fail("SCOPE_VIOLATION", scope=scope, diff=diff)
        expected = verification.get("expected_paths") or []
        if not isinstance(expected, list) or any(not isinstance(p, str) for p in expected):
            return fail("VERIFICATION_FAILED")
        from project_harness.util import resolve_inside
        if any(not resolve_inside(product, p).is_file() for p in expected):
            return fail("VERIFICATION_FAILED", diagnostic="Expected product artifact missing")
        if verification.get("manual_checks") and verification.get("allow_manual") is not True:
            return fail("VERIFICATION_FAILED", diagnostic="Independent human review still required")
        runner = runner or RootlessPodmanRunner()
        results = []
        for command in commands:
            # Automatic commands must be exact argv arrays: no shell strings.
            if not isinstance(command, dict) or not isinstance(command.get("argv"), list):
                return fail("VERIFICATION_FAILED", command_results=results)
            argv = command["argv"]
            executable = validate_container_executable(argv[0] if argv else None)
            cwd = command.get("cwd", ".")
            if not isinstance(cwd, str) or cwd != ".":
                # Alternate cwd requires its own trusted container-workdir contract.
                return fail("VERIFICATION_FAILED", diagnostic="Non-root cwd unsupported by bounded verifier")
            timeout = command.get("timeout_seconds", verification.get("timeout_seconds", 300))
            if type(timeout) is not int or timeout < 1 or timeout > profile["limits"]["timeout_seconds"]:
                return fail("VERIFICATION_FAILED", command_results=results)
            request = {
                "sandbox_profile": profile, "argv": argv, "stdin_mode": "CLOSED",
                "execution_root": execution_root, "canonical_project_root": canonical_project_root,
                "product_dir": product, "control_dir": execution_root / "control",
                "output_dir": execution_root / "output", "network_mode": "NONE",
                "timeout_seconds": timeout,
            }
            # A distinct runner invocation; no agent environment, secret refs or Run context.
            invocation = RootlessPodmanRunner(configured_executable=executable) if isinstance(runner, RootlessPodmanRunner) else runner
            outcome = invocation.run(request)
            results.append({"argv": argv, "exit_code": outcome.get("exit_code"),
                            "termination_reason": outcome.get("termination_reason"),
                            "stdout": outcome.get("stdout", ""), "stderr": outcome.get("stderr", "")})
            if outcome.get("isolation_verified") is not True or outcome.get("termination_reason") != "EXITED" or outcome.get("exit_code") != 0 or outcome.get("reason_code"):
                return fail("VERIFICATION_FAILED", command_results=results,
                            sandbox_reason=outcome.get("reason_code"))
        after = snapshot_product(product)
        if snapshot_product(canonical_project_root) != baseline_files:
            return fail("BASELINE_CHANGED", command_results=results)
        if after != before:  # verifier must not mutate the candidate under review
            return fail("VERIFICATION_FAILED", diagnostic="Verifier mutated disposable product", command_results=results)
        return {"status": "PASS", "reason_code": None, "apply_allowed": False,
                "command_results": results, "diff": diff, "scope": scope,
                "verified_product_files": after,
                "verified_subjects": ["RUNTIME_TASK_VERIFICATION"]}
    except (OSError, ValueError, TypeError, KeyError, SandboxPolicyError) as exc:
        return fail("VERIFICATION_FAILED", diagnostic=type(exc).__name__)
