"""One CODEX_CLI_LOCAL adapter, pinned ADP/SBX and sandbox-only dispatch.

PH-051-05 binds the active, immutable, revisioned project profiles to a
PH-051-04 disposable Run and the PH-051-03 rootless Podman runner. This is
not a public automatic Run route, Agent Result approval, or product apply.
No host execution primitives or shell calls are permitted in this module.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path, PurePosixPath
import os
import re
import stat
from typing import Any, Mapping

from project_harness.errors import ValidationFailure
from project_harness.hashing import sha256_file
from project_harness.project_input import exact_execution_profile_bindings, execution_policy_issues
from project_harness.serialization import load_data
from project_harness.sandbox.podman_rootless import RootlessPodmanRunner
from project_harness.sandbox.profiles import SandboxPolicyError, validate_sandbox_profile

from .base import SandboxTransport
from .result import (classify_process_result, normalize_exact_execution_result,
                     resolve_execution_environment, ResultChannelError)

ALLOWED_PLACEHOLDERS = frozenset({
    "prompt_bundle_path", "context_packet_path", "agent_result_path",
    "workspace_path", "run_id", "task_id",
})
_PATH_CONTROLS = ("prompt_bundle_path", "context_packet_path")
_ID_PATTERN = re.compile(r"(?:RUN|TSK)-[A-Z0-9][A-Z0-9-]*(?:@[1-9][0-9]*)?")
_EXECUTABLE_PATTERN = re.compile(r"[A-Za-z0-9_./-]+")
_ENV_PATTERN = re.compile(r"[A-Z_][A-Z0-9_]*")
_REF_PATTERN = re.compile(r"ENV:[A-Z_][A-Z0-9_]*")
_PLACEHOLDER_PATTERN = re.compile(r"\{([a-z_]+)\}")
_FORBIDDEN_SHELL = re.compile(r"[|&;<>`$\\\x00-\x1f\x7f]")
_BAD_LITERAL = re.compile(r"(?:^|[-_])(api[-_]?key|token|password|secret|credential)(?:$|[-_=])", re.I)
_CONTEXT_KEYS = ALLOWED_PLACEHOLDERS | {"adapter_profile"}
# Never forward ambient credential-bearing or process-control host variables.
_UNSAFE_AMBIENT_ENV = frozenset({
    "HOME", "PATH", "ENV", "SHELL", "BASH_ENV", "PYTHONPATH", "PYTHONHOME",
    "LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES", "SSH_AUTH_SOCK",
    "GIT_ASKPASS", "GIT_SSH_COMMAND",
})
_SECRET_LIKE_ENV = re.compile(r"(?:^|_)(?:API|KEY|TOKEN|SECRET|PASSWORD|PASS|CREDENTIAL|COOKIE|AUTH|SSH|AWS|AZURE|GCP|GOOGLE|OPENAI|CODEX|GITHUB)(?:_|$)")
_PROFILE_KEYS = frozenset({
    "id", "revision", "status", "kind", "executable", "argv_template",
    "working_directory", "timeout_seconds", "stdin_mode",
    "environment_allowlist", "secret_environment_refs", "sandbox_profile_ref",
})


def _bad(message: str) -> ValidationFailure:
    return ValidationFailure("Unsafe CODEX_CLI_LOCAL invocation", message)


def _profile(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _bad("adapter_profile must be an object")
    if set(value) == {"agent_adapter_profile"}:
        value = value["agent_adapter_profile"]
    if not isinstance(value, dict):
        raise _bad("agent_adapter_profile must be an object")
    if set(value) != _PROFILE_KEYS:
        raise _bad("adapter profile is not the exact strict contract; raw secrets/extra fields forbidden")
    if not isinstance(value["id"], str) or re.fullmatch(r"ADP-[A-Z0-9][A-Z0-9-]*", value["id"]) is None:
        raise _bad("invalid adapter profile ID")
    if type(value["revision"]) is not int or value["revision"] < 1:
        raise _bad("invalid adapter profile revision")
    if value.get("kind") != "CODEX_CLI_LOCAL" or value.get("status") != "ACTIVE":
        raise _bad("only an ACTIVE CODEX_CLI_LOCAL adapter profile may prepare argv")
    if value.get("stdin_mode") != "CLOSED" or value.get("working_directory") != "/workspace/product":
        raise _bad("stdin must be CLOSED and workdir /workspace/product")
    if not isinstance(value.get("timeout_seconds"), int) or isinstance(value["timeout_seconds"], bool) or not 1 <= value["timeout_seconds"] <= 86400:
        raise _bad("invalid bounded timeout_seconds")
    if not isinstance(value.get("sandbox_profile_ref"), str) or re.fullmatch(
        r"SBX-[A-Z0-9][A-Z0-9-]*@[1-9][0-9]*", value["sandbox_profile_ref"]
    ) is None:
        raise _bad("sandbox_profile_ref must be an exact revisioned SBX ref")
    for field, pattern, max_items in (("environment_allowlist", _ENV_PATTERN, 32),
                                      ("secret_environment_refs", _REF_PATTERN, 16)):
        items = value.get(field)
        if (not isinstance(items, list) or len(items) > max_items or
                any(not isinstance(x, str) or pattern.fullmatch(x) is None for x in items) or
                len(set(items)) != len(items)):
            raise _bad(f"invalid {field}; only allowlisted environment *names*/refs are permitted")
    allowed_names = set(value["environment_allowlist"])
    secret_names = {ref[4:] for ref in value["secret_environment_refs"]}
    if allowed_names & secret_names:
        raise _bad("secret refs cannot be passed as unprotected host environment allowlist")
    if any(name in _UNSAFE_AMBIENT_ENV or _SECRET_LIKE_ENV.search(name) for name in allowed_names):
        raise _bad("unsafe or credential-bearing ambient environment variable")
    if any(name in _UNSAFE_AMBIENT_ENV for name in secret_names):
        raise _bad("secret refs cannot modify process-control environment variables")
    executable = value.get("executable")
    if not isinstance(executable, str) or not 1 <= len(executable) <= 256 or _EXECUTABLE_PATTERN.fullmatch(executable) is None:
        raise _bad("executable must be an exact binary name or absolute container path")
    # Relative paths with a slash, traversal, and dot components are forbidden.
    path = PurePosixPath(executable)
    if ("/" in executable and not path.is_absolute()) or any(part in (".", "..") for part in executable.split("/")) or "//" in executable:
        raise _bad("relative/traversing executable paths are forbidden")
    template = value.get("argv_template")
    if not isinstance(template, list) or not 1 <= len(template) <= 64:
        raise _bad("argv_template must be a bounded list of arguments, not a command string")
    if template[0] != executable:
        raise _bad("argv_template[0] must exactly equal the allowed executable")
    for i, arg in enumerate(template):
        if not isinstance(arg, str) or not 1 <= len(arg) <= 4096:
            raise _bad(f"argv_template[{i}] must be a nonempty bounded string")
        placeholder = _PLACEHOLDER_PATTERN.fullmatch(arg)
        if placeholder:
            if i == 0 or placeholder.group(1) not in ALLOWED_PLACEHOLDERS:
                raise _bad(f"unknown or executable-position placeholder at argv_template[{i}]")
            continue
        if "{" in arg or "}" in arg:
            raise _bad(f"embedded, malformed or unknown placeholder in argv_template[{i}]")
        if _FORBIDDEN_SHELL.search(arg) or '\"' in arg or "'" in arg:
            raise _bad(f"shell/redirection/command-substitution syntax in argv_template[{i}]")
        if any(ch.isspace() for ch in arg):
            raise _bad(f"argv_template[{i}] contains a shell-style compound argument")
        if i > 0 and (arg.startswith("/") or arg.startswith("@")):
            raise _bad(f"only placeholders may name file paths at argv_template[{i}]")
        if _BAD_LITERAL.search(arg):
            raise _bad(f"credential-like literal flag is not allowed in argv_template[{i}]")
    return value


def _container_value(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise _bad(f"missing/invalid trusted {name}")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise _bad(f"control characters in {name}")
    if name in {"run_id", "task_id"}:
        expected_prefix = "RUN-" if name == "run_id" else "TSK-"
        if _ID_PATTERN.fullmatch(value) is None or not value.startswith(expected_prefix):
            raise _bad(f"invalid canonical {name}")
        return value
    if name == "workspace_path":
        if value != "/workspace/product":
            raise _bad("workspace_path must be /workspace/product inside the sandbox")
        return value
    if name == "agent_result_path":
        if value != "/output/agent-result.json":
            raise _bad("agent_result_path must be /output/agent-result.json")
        return value
    if name in _PATH_CONTROLS:
        # Do not accept paths from the host/canonical product, or path escapes.
        p = PurePosixPath(value)
        if (not p.is_absolute() or not value.startswith("/workspace/control/") or
                any(part in (".", "..") for part in value.split("/")) or
                "//" in value or value.endswith("/")):
            raise _bad(f"{name} must be inside the sandbox read-only control projection")
        return value
    raise _bad("unsupported placeholder")


def prepare_argv(run_context: Mapping[str, Any]) -> list[str]:
    """Expand only entire placeholder argv elements from trusted Run bindings."""
    if not isinstance(run_context, dict) or set(run_context) - _CONTEXT_KEYS:
        raise _bad("run_context has forbidden keys (no raw text, secrets or host environment)")
    profile = _profile(run_context.get("adapter_profile"))
    # Even unused supplied bindings must not carry host paths or secret text
    # across the runner boundary.
    for name in ALLOWED_PLACEHOLDERS & set(run_context):
        _container_value(name, run_context[name])
    out: list[str] = []
    for arg in profile["argv_template"]:
        match = _PLACEHOLDER_PATTERN.fullmatch(arg)
        out.append(_container_value(match.group(1), run_context.get(match.group(1))) if match else arg)
    return out


def _project_record(root: Path, relative: str) -> dict[str, Any]:
    """Read an exact single-link project record without following symlinks."""
    current = root
    for part in Path(relative).parts:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise _bad(f"missing exact project record: {relative}") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise _bad(f"symlink in exact project record: {relative}")
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise _bad(f"project record must be a unique regular file: {relative}")
    try:
        record = load_data(current)
    except (ValueError, OSError) as exc:
        raise _bad(f"invalid project record: {relative}") from exc
    if not isinstance(record, dict):
        raise _bad(f"project record is not an object: {relative}")
    return record


def load_active_codex_profiles(project_root: Path) -> dict[str, Any]:
    """Resolve pinned ACTIVE ADP/SBX via exact project lock, never latest/glob.

    The existing PH-051-01 strict schema/profile resolver provides revisioned
    refs and source hashes; neither accepted input nor project lock is mutated.
    An unactivated/manual project cannot silently opt into local execution.
    """
    try:
        canonical = Path(project_root).expanduser().resolve(strict=True)
    except (OSError, ValueError) as exc:
        raise _bad("canonical project root unavailable") from exc
    if not canonical.is_dir():
        raise _bad("project root is not a directory")
    lock = _project_record(canonical, ".harness/config/PROJECT_LOCK.yaml").get("project_lock")
    if not isinstance(lock, dict):
        raise _bad("missing project_lock envelope")
    policy = lock.get("execution")
    if execution_policy_issues(policy) or policy["mode"] != "LOCAL_AUTOMATIC":
        raise _bad("LOCAL_AUTOMATIC must be explicitly accepted in PROJECT_LOCK")
    if policy["network_mode"] != "NONE":
        raise _bad("egress has no governed per-Run approval in PH-051-05")
    # Exact schema, status, revision, ADP->SBX ref and digest verification.
    bindings = exact_execution_profile_bindings(canonical, policy)
    if lock.get("execution_profile_bindings") != bindings:
        raise _bad("PROJECT_LOCK profile refs/digests differ from current exact records")
    profiles = {}
    for label, folder, envelope in (
        ("adapter", "ADAPTERS", "agent_adapter_profile"),
        ("sandbox", "SANDBOXES", "sandbox_profile"),
    ):
        reference = bindings[label]["ref"]
        name = f".harness/config/{folder}/{reference}.yaml"
        record = _project_record(canonical, name)
        file_path = canonical / name
        if "sha256:" + sha256_file(file_path) != bindings[label]["digest"]:
            raise _bad(f"profile digest drift: {reference}")
        profile = record.get(envelope)
        profiles[label] = _profile(profile) if label == "adapter" else validate_sandbox_profile(profile)
    if profiles["adapter"]["sandbox_profile_ref"] != bindings["sandbox"]["ref"]:
        raise _bad("ADP references another SBX")
    return {"project_root": canonical, "adapter_profile": deepcopy(profiles["adapter"]),
            "sandbox_profile": deepcopy(profiles["sandbox"]), "profile_bindings": deepcopy(bindings)}


class CodexCliLocalAdapter:
    """Only pinned project profiles may obtain a real production Podman runner.

    An injected protocol double remains available to PH-051-02 unit tests, but
    is never treated as a real rootless security attestation. The public
    execute-current/doctor CLI and Run transitions belong to PH-051-09.
    """

    def __init__(self, sandbox_runner: SandboxTransport | None = None):
        self._sandbox_runner = sandbox_runner
        self._bound: dict[str, Any] | None = None
        self._prepared: dict[str, Any] | None = None
        self._dispatched = False
        self._trusted_process_result: dict[str, Any] | None = None
        self._secret_snapshot: dict[str, str] = {}

    @classmethod
    def from_project(cls, project_root: Path) -> "CodexCliLocalAdapter":
        """Read pinned ACTIVE profiles, then use ONLY the trusted Podman backend."""
        bound = load_active_codex_profiles(project_root)
        adapter = cls(RootlessPodmanRunner(configured_executable=bound["adapter_profile"]["executable"]))
        adapter._bound = bound
        return adapter

    @staticmethod
    def _environment_preflight(profile: dict[str, Any]) -> None:
        # Only exact ENV:NAME refs of the already pinned ADP can be resolved.
        # Values are never placed in plan/request/log/argv diagnostics.
        resolve_execution_environment(profile)

    def doctor(self, profile: dict[str, Any]) -> dict[str, Any]:
        try:
            active = _profile(profile)
            if self._bound is not None and active != self._bound["adapter_profile"]:
                raise _bad("adapter does not match pinned active ADP revision")
        except ValidationFailure as exc:
            return {"status": "BLOCKED", "reason_code": "SANDBOX_POLICY_FAILURE", "message": str(exc)}
        if self._bound is None or type(self._sandbox_runner) is not RootlessPodmanRunner:
            return {
                "status": "BLOCKED", "reason_code": "SANDBOX_UNAVAILABLE",
                "profile_validation": "PASS",
                "message": "No pinned project profile with a trusted RootlessPodmanRunner",
            }
        try:
            self._environment_preflight(active)
        except ResultChannelError as exc:
            return {"status": "BLOCKED", "reason_code": exc.reason_code,
                    "profile_validation": "PASS", "message": "required execution environment unavailable"}
        try:
            health = self._sandbox_runner.doctor(self._bound["sandbox_profile"])
        except (OSError, ValueError, SandboxPolicyError):
            return {"status": "BLOCKED", "reason_code": "SANDBOX_UNAVAILABLE",
                    "profile_validation": "PASS"}
        if not isinstance(health, dict):
            return {"status": "BLOCKED", "reason_code": "SANDBOX_UNAVAILABLE"}
        # A real Podman doctor must itself prove isolation; do not advertise
        # success when checks were skipped/unknown or backend was substituted.
        if (health.get("status") != "PASS" or health.get("backend") != "ROOTLESS_PODMAN" or
                health.get("isolation_verified") is not True or
                health.get("network_mode") != "NONE" or
                not isinstance(health.get("checks"), dict) or
                not health["checks"] or any(x != "PASS" for x in health["checks"].values())):
            if health.get("status") == "PASS":
                return {"status": "BLOCKED", "reason_code": "SANDBOX_UNAVAILABLE",
                        "profile_validation": "PASS", "message": "incomplete Podman attestation"}
            return {**health, "profile_validation": "PASS"}
        return {**health, "profile_validation": "PASS"}

    def prepare_invocation(self, run_context: dict[str, Any]) -> list[str]:
        if self._bound is not None and (not isinstance(run_context, dict) or
                                        run_context.get("adapter_profile") != self._bound["adapter_profile"]):
            raise _bad("Run invocation is not bound to the pinned ACTIVE ADP")
        return prepare_argv(run_context)

    def prepare_current_run(self, runtime_root: Path, *, run_ref: str | None = None) -> dict[str, Any]:
        """Prepare exact JIT/Task/Run bindings and disposable mounts, without launch.

        This internal API composes the PH-051-04 root builder; it never writes
        an agent result, applies product changes, or authorizes a Run.
        """
        if self._bound is None or type(self._sandbox_runner) is not RootlessPodmanRunner:
            raise _bad("prepare_current_run requires exact pinned project profiles")
        if self._dispatched:
            raise _bad("Run already dispatched by this adapter; new immutable retry requires PH-051-09")
        # Recheck profile source hashes/refs, also at execution time.
        current = load_active_codex_profiles(self._bound["project_root"])
        if current != self._bound:
            raise _bad("active execution profiles changed since adapter creation")
        from project_harness.execution_roots import prepare_execution_root
        root = prepare_execution_root(self._bound["project_root"], Path(runtime_root), run_ref=run_ref)
        state = _project_record(self._bound["project_root"], ".harness/state/CURRENT_STATE.yaml").get("state")
        active = state.get("active_run") if isinstance(state, dict) else None
        if not isinstance(active, dict) or root["run_ref"] != active.get("run_ref"):
            raise _bad("prepared root is not the active Run")
        task_ref = active.get("task_ref")
        if not isinstance(task_ref, str) or not task_ref.startswith("TSK-"):
            raise _bad("current Task binding absent")
        c = {
            "adapter_profile": deepcopy(self._bound["adapter_profile"]),
            "prompt_bundle_path": "/workspace/control/prompt-bundle.md",
            "context_packet_path": "/workspace/control/context-packet.json",
            "agent_result_path": "/output/agent-result.json",
            "workspace_path": "/workspace/product",
            "run_id": active["run_ref"], "task_id": task_ref,
        }
        invocation = self.prepare_invocation(c)
        p = self._bound["sandbox_profile"]
        request = {
            "run_context": c, "sandbox_profile": deepcopy(p),
            "execution_root": root["execution_root"],
            "canonical_project_root": str(self._bound["project_root"]),
            "product_dir": root["product_dir"], "control_dir": root["control_dir"],
            "output_dir": root["output_dir"], "stdin_mode": "CLOSED",
            "network_mode": "NONE",
            "timeout_seconds": min(self._bound["adapter_profile"]["timeout_seconds"],
                                   p["limits"]["timeout_seconds"]),
        }
        self._prepared = {"invocation": deepcopy(invocation), "request": deepcopy(request),
                          "runtime_root": Path(runtime_root), "run_ref": root["run_ref"]}
        return {"invocation": invocation, "sandbox_request": request,
                "run_ref": root["run_ref"], "status": "PREPARED"}

    def execute(self, invocation: list[str], sandbox_request: dict[str, Any]) -> dict[str, Any]:
        # Re-derive exact argv from trusted bindings; arbitrary argv cannot be
        # smuggled into a runner even if caller bypasses prepare_invocation.
        if not isinstance(sandbox_request, dict) or any(
            key in sandbox_request for key in ("shell", "command", "host_env", "host_environment", "env", "secret_values", "argv")
        ):
            return {"status": "BLOCKED", "reason_code": "SANDBOX_POLICY_FAILURE"}
        try:
            expected = self.prepare_invocation(sandbox_request.get("run_context"))
            if invocation != expected:
                raise _bad("invocation differs from exact prepared argv")
            if self._bound is not None:
                if self._dispatched:
                    raise _bad("same Run cannot be dispatched twice by this adapter")
                if self._prepared is None or (invocation != self._prepared["invocation"] or
                        sandbox_request != self._prepared["request"]):
                    raise _bad("invocation/request was not built from exact active JIT binding")
                if load_active_codex_profiles(self._bound["project_root"]) != self._bound:
                    raise _bad("active project profiles/bindings are stale")
                # Fail-closed on changed canonical tree, Run binding, projection,
                # output channel or execution snapshot before starting process.
                from project_harness.execution_roots import prepare_execution_root
                prepare_execution_root(self._bound["project_root"], self._prepared["runtime_root"],
                                       run_ref=self._prepared["run_ref"])
                self._environment_preflight(self._bound["adapter_profile"])
        except ResultChannelError as exc:
            return {"status": "BLOCKED", "reason_code": exc.reason_code}
        except ValidationFailure:
            return {"status": "BLOCKED", "reason_code": "SANDBOX_POLICY_FAILURE"}
        if self._sandbox_runner is None:
            return {"status": "BLOCKED", "reason_code": "SANDBOX_UNAVAILABLE"}
        profile = sandbox_request.get("sandbox_profile")
        if not isinstance(profile, dict):
            return {"status": "BLOCKED", "reason_code": "SANDBOX_POLICY_FAILURE"}
        if self._bound is not None and profile != self._bound["sandbox_profile"]:
            return {"status": "BLOCKED", "reason_code": "SANDBOX_POLICY_FAILURE"}
        try:
            health = self.doctor(self._bound["adapter_profile"]) if self._bound is not None else self._sandbox_runner.doctor(profile)
        except Exception:
            return {"status": "BLOCKED", "reason_code": "SANDBOX_UNAVAILABLE"}
        if (not isinstance(health, dict) or health.get("status") != "PASS" or
                health.get("backend") != "ROOTLESS_PODMAN" or
                health.get("isolation_verified") is not True):
            return {"status": "BLOCKED", "reason_code": (health.get("reason_code") or "SANDBOX_UNAVAILABLE")
                    if isinstance(health, dict) else "SANDBOX_UNAVAILABLE"}
        request = dict(sandbox_request)
        request["argv"] = list(invocation)
        request["stdin_mode"] = "CLOSED"
        try:
            resolved, secrets = (resolve_execution_environment(self._bound["adapter_profile"])
                                 if self._bound is not None else ({}, {}))
            if self._bound is not None:
                # Create the *only* permitted result file with owner-only mode
                # before Podman. Agent's normal open('w') preserves 0600.
                output = Path(self._prepared["request"]["output_dir"])
                fd = os.open(output / "agent-result.json", os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                             getattr(os, "O_NOFOLLOW", 0), 0o600)
                os.close(fd)
                self._dispatched = True
                self._secret_snapshot = secrets
            # Resolved values are transient function arguments, NEVER request
            # fields. A pinned RootlessPodmanRunner re-verifies references.
            response = (self._sandbox_runner.run(request, resolved_environment=resolved)
                        if self._bound is not None else self._sandbox_runner.run(request))
        except ResultChannelError as exc:
            return {"status": "BLOCKED", "reason_code": exc.reason_code}
        except OSError:
            return {"status": "BLOCKED", "reason_code": "SANDBOX_UNAVAILABLE"}
        except ValueError:
            return {"status": "BLOCKED", "reason_code": "SANDBOX_POLICY_FAILURE"}
        except Exception:
            return {"status": "BLOCKED", "reason_code": "SANDBOX_UNAVAILABLE"}
        if not isinstance(response, dict):
            return {"status": "BLOCKED", "reason_code": "SANDBOX_POLICY_FAILURE"}
        if self._bound is not None:
            self._trusted_process_result = deepcopy(response)
        # PH-051-06 result schema validation follows explicitly; agent exit 0
        # remains not verified, not applied, not Task COMPLETE.
        return response

    def normalize_result(self, process_result: dict[str, Any], output_dir: Path) -> dict[str, Any]:
        # Unbound PH-051-02 test doubles retain the harmless preliminary
        # classifier; they can never publish to a project control plane.
        if self._bound is None:
            return classify_process_result(process_result, output_dir)
        if self._prepared is None or not self._dispatched:
            # Bound-but-not-dispatched negative fixtures can only classify
            # process failures; they cannot publish a validated result.
            return classify_process_result(process_result, output_dir)
        if (self._trusted_process_result is None or
                process_result != self._trusted_process_result or
                Path(output_dir) != Path(self._prepared["request"]["output_dir"])):
            return {"status": "BLOCKED", "reason_code": "SANDBOX_POLICY_FAILURE",
                    "result_validated": False}
        try:
            from project_harness.execution_roots import _root_contents_digest
            root = self._prepared["request"]
            digest = _root_contents_digest(Path(root["product_dir"]))
            if not digest.startswith("tree:sha256:"):
                raise ValueError("execution root digest not canonical")
            # A read-only exact-secret scan helper for PH-051-08 is present in
            # safety.py; this phase doesn't compute or apply a product diff.
            result = normalize_exact_execution_result(
                process_result, Path(output_dir), run_ref=self._prepared["run_ref"],
                task_ref=root["run_context"]["task_id"],
                adapter_profile_ref=self._bound["profile_bindings"]["adapter"]["ref"],
                sandbox_profile_ref=self._bound["profile_bindings"]["sandbox"]["ref"],
                execution_root_digest=digest.removeprefix("tree:"),
                project_root=self._bound["project_root"],
                secret_values=self._secret_snapshot)
        except (OSError, ValueError):
            result = {"status": "FAILED_RETRYABLE", "reason_code": "RESULT_INVALID",
                      "result_validated": False}
        finally:
            self._secret_snapshot = {}
            self._trusted_process_result = None
        return result
