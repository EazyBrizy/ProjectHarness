"""PH-051-03: single, fail-closed ROOTLESS_PODMAN runner and real self-tests.

This package is not wired into the public runtime until PH-051-09. Only the
Podman binary may be executed on the host; container argv is never executed as
host argv, and no alternative (Docker, shell fallback) is available.
"""

from __future__ import annotations

import json
import hashlib
import re
import os
from datetime import datetime, timezone
from typing import Mapping
from pathlib import Path
import secrets
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
from typing import Any

from project_harness.executors.result import (resolve_execution_environment, ResultChannelError)
from project_harness.safety import redact_exact_secrets, scan_exact_secret

from .profiles import (
    SandboxPolicyError, validate_argv, validate_container_executable,
    validate_execution_mounts, validate_sandbox_profile,
)


# Static probes are trusted distribution source, NEVER sourced from a Run/agent.
_BOUNDARY_PROBE = r'''
set -eu
uid="$(id -u)"
[ "$uid" -ne 0 ] || exit 41
[ "$HOME" = /home/harness ] || exit 42
[ -w /workspace/product ] || exit 43
[ -w /output ] || exit 44
[ -w /tmp ] || exit 45
[ -w "$HOME" ] || exit 46
[ -r /workspace/control/locked ] || exit 47
[ "$(cat /workspace/control/locked)" = locked ] || exit 48
if (printf forbidden > /.__harness_rootfs_probe 2>/dev/null); then exit 49; fi
if (printf forbidden > /workspace/control/locked 2>/dev/null); then exit 50; fi
[ "$(cat /workspace/control/locked)" = locked ] || exit 51
[ ! -e /var/run/docker.sock ] || exit 52
[ ! -e /run/podman/podman.sock ] || exit 53
[ ! -e /run/user/0/podman/podman.sock ] || exit 54
[ ! -e "/run/user/${uid}/podman/podman.sock" ] || exit 58
[ -r /proc/self/status ] || exit 55
cap=''; nnp=''
while IFS=: read -r key value; do
  case "$key" in
    CapEff) set -- $value; cap="${1:-}" ;;
    NoNewPrivs) set -- $value; nnp="${1:-}" ;;
  esac
done < /proc/self/status
[ "$cap" = 0000000000000000 ] || exit 56
[ "$nnp" = 1 ] || exit 57
printf ok > /workspace/product/probe-product
printf ok > /output/probe-result
printf ok > "$HOME/probe-home"
printf 'BOUNDARY_PASS\n'
'''

# Must verify actual kernel cgroup limits and network absence. A missing Python
# runtime or inaccessible kernel data is UNKNOWN, not successful isolation.
_KERNEL_PROBE = r'''
import errno
from pathlib import Path
import socket
import sys

memory = int(sys.argv[1]) * 1024 * 1024
pids = int(sys.argv[2])
cpu = float(sys.argv[3])

def data(path):
    f = Path(path)
    return f.read_text().strip() if f.is_file() else None

if data('/sys/fs/cgroup/cgroup.controllers') is not None:
    mem = data('/sys/fs/cgroup/memory.max')
    pid = data('/sys/fs/cgroup/pids.max')
    cp = data('/sys/fs/cgroup/cpu.max')
    if mem is None or pid is None or cp is None or 'max' in (mem,pid,cp):
        sys.exit(70)
    try:
        q, period = cp.split()
        enforced = int(mem) <= memory and int(pid) <= pids and int(q) / int(period) <= cpu + 0.01
    except (ValueError, ZeroDivisionError):
        sys.exit(70)
else:
    # Rootless cgroup v1 limits may be unavailable; do not silently pass.
    mem = data('/sys/fs/cgroup/memory/memory.limit_in_bytes')
    pid = data('/sys/fs/cgroup/pids/pids.max')
    quota = data('/sys/fs/cgroup/cpu/cpu.cfs_quota_us')
    period = data('/sys/fs/cgroup/cpu/cpu.cfs_period_us')
    if any(x is None for x in (mem,pid,quota,period)):
        sys.exit(70)
    try:
        enforced = (int(mem) <= memory and int(pid) <= pids and int(quota) > 0
                    and int(quota) / int(period) <= cpu + 0.01)
    except (ValueError, ZeroDivisionError):
        sys.exit(70)
if not enforced:
    sys.exit(71)

# A failed write alone cannot prove a read-only mount: the non-root user
# might lack DAC write permission even when the mount itself is rw.
mountinfo = data('/proc/self/mountinfo')
if mountinfo is None:
    sys.exit(77)
actual_mounts = {}
for line in mountinfo.splitlines():
    left, delim, right = line.partition(' - ')
    fields = left.split()
    if not delim or len(fields) < 6:
        sys.exit(77)
    point = fields[4]
    if point in ('/', '/workspace/product', '/workspace/control', '/output', '/tmp', '/home/harness'):
        actual_mounts[point] = (set(fields[5].split(',')), right.split()[0])
for point, needed_mode in (('/', 'ro'), ('/workspace/control', 'ro'),
                           ('/workspace/product', 'rw'), ('/output', 'rw')):
    if point not in actual_mounts or needed_mode not in actual_mounts[point][0]:
        sys.exit(78)
for point in ('/tmp', '/home/harness'):
    if point not in actual_mounts or actual_mounts[point][1] != 'tmpfs' or 'rw' not in actual_mounts[point][0]:
        sys.exit(79)

# NONE normally has only loopback and no default route. Require both the
# namespace route invariant and immediate kernel refusal of outbound sockets.
route = data('/proc/net/route')
if route is None:
    sys.exit(72)
for line in route.splitlines()[1:]:
    columns = line.split()
    if len(columns) > 1 and columns[1] == '00000000':
        sys.exit(73)
allowed = {errno.ENETUNREACH, errno.ENETDOWN, errno.EADDRNOTAVAIL, errno.EAFNOSUPPORT}
for family, address in ((socket.AF_INET, ('198.51.100.1', 443)),
                        (socket.AF_INET6, ('2001:db8::1', 443))):
    try:
        s = socket.socket(family, socket.SOCK_STREAM)
    except OSError as exc:
        if family == socket.AF_INET6 and exc.errno == errno.EAFNOSUPPORT:
            continue
        sys.exit(74)
    try:
        s.settimeout(2)
        s.connect(address)
    except OSError as exc:
        if exc.errno not in allowed:
            sys.exit(75)
    else:
        sys.exit(76)
    finally:
        s.close()
print('KERNEL_PASS')
'''


def _blocked(reason: str, message: str, checks: dict | None = None) -> dict[str, Any]:
    return {
        "status": "BLOCKED", "backend": "ROOTLESS_PODMAN",
        "reason_code": reason, "isolation_verified": False,
        "message": message, "checks": checks or {},
    }


_PROJECT_LABEL = "io.project-harness.project-sha256"
_RUN_LABEL = "io.project-harness.run"
_RUN_REF_RE = re.compile(r"RUN-[A-Z0-9]+(?:-[A-Z0-9]+)*\Z")


def _project_owner(project_root: Path) -> str:
    # Labels contain only deterministic project identity hash, never a path or
    # secret. Exact root ensures the recovery scanner cannot sweep other users.
    return hashlib.sha256(str(Path(project_root).resolve(strict=True)).encode("utf-8")).hexdigest()


def _container_name() -> str:
    return "ph-05103-" + secrets.token_hex(10)


class RootlessPodmanRunner:
    """A real Podman runner: no mocks can be interpreted as acceptance proof.

    Constructor requires a configured executable present *inside* the pinned
    image. Profile doctor validates rootless/info/image and runs three real
    container probes (mounts, network/cgroups, timeout+container cleanup).
    """

    def __init__(self, *, configured_executable: str | None = None) -> None:
        self._configured_executable = configured_executable

    def _podman(self) -> str | None:
        exe = shutil.which("podman")
        # Never accept a name/command from project input as a host program.
        if not exe:
            return None
        resolved = os.path.realpath(exe)
        if Path(exe).name != "podman" or not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
            return None
        return resolved

    @staticmethod
    def _command(profile: dict[str, Any], sources: dict[str, Path], *,
                 podman: str, name: str, executable: str, argv: list[str],
                 uid: int, gid: int, environment_file: Path | None = None,
                 project_owner: str | None = None, run_ref: str | None = None) -> list[str]:
        """Single sealed Podman argv constructor, also used by doctor probes."""
        limits = profile["limits"]
        if uid <= 0 or gid < 0:
            raise SandboxPolicyError("rootless host identity required")
        cpu = str(limits["cpu_count"])
        command = [
            podman, "--remote=false", "run", "--rm", "--pull=never", "--log-driver=none", "--name", name,
            "--label", "io.project-harness.sandbox=PH-051-03",
            "--userns=keep-id", "--user", f"{uid}:{gid}",
            "--security-opt=no-new-privileges", "--cap-drop=ALL",
            "--read-only", "--read-only-tmpfs=false", "--image-volume=ignore", "--network=none",
            "--pid=private", "--ipc=private",
            "--pids-limit", str(limits["pids"]),
            "--memory", f"{limits['memory_mb']}m", "--cpus", cpu,
            "--mount", f"type=bind,src={sources['product_dir']},dst=/workspace/product,rw",
            "--mount", f"type=bind,src={sources['control_dir']},dst=/workspace/control,ro",
            "--mount", f"type=bind,src={sources['output_dir']},dst=/output,rw",
            "--tmpfs", "/tmp:rw,nosuid,nodev,notmpcopyup,mode=1777,size=64m",
            "--tmpfs", f"/home/harness:rw,nosuid,nodev,notmpcopyup,mode=0700,uid={uid},gid={gid},size=64m",
            "--workdir", "/workspace/product",
            "--env", "HOME=/home/harness",
            "--env", "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "--env", "LANG=C", "--env", "LC_ALL=C",
            "--unsetenv-all",
        ]
        if (project_owner is None) != (run_ref is None):
            raise SandboxPolicyError("Podman Run identity labels must be exact and paired")
        if project_owner is not None:
            if not re.fullmatch(r"[a-f0-9]{64}", project_owner) or not _RUN_REF_RE.fullmatch(run_ref or ""):
                raise SandboxPolicyError("Invalid Podman Run identity")
            command.extend(["--label", f"{_PROJECT_LABEL}={project_owner}",
                            "--label", f"{_RUN_LABEL}={run_ref}"])
        # Only a kernel-owned 0600 transient env-file is allowed. Never put
        # credentials into process argv (visible in host process tables).
        if environment_file is not None:
            command.extend(["--env-file", str(environment_file)])
        return [*command, "--entrypoint", executable, profile["image"], *argv]

    @staticmethod
    def _end_process(proc: subprocess.Popen[bytes], podman: str, name: str | None) -> bool:
        # Stop entire container, not just the Podman CLI (which could leave an
        # orphan agent/child). Orphan discovery across host crashes is PH-051-10.
        cleanup_ok = True
        if name:
            try:
                subprocess.run([podman, "--remote=false", "stop", "--time", "2", name],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=5, check=False)
            except (OSError, subprocess.TimeoutExpired):
                cleanup_ok = False
            try:
                subprocess.run([podman, "--remote=false", "rm", "--force", name],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=5, check=False)
            except (OSError, subprocess.TimeoutExpired):
                cleanup_ok = False
            try:
                exists = subprocess.run([podman, "--remote=false", "container", "exists", name],
                                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL, timeout=5, check=False)
                if exists.returncode != 1:
                    cleanup_ok = False
            except (OSError, subprocess.TimeoutExpired):
                cleanup_ok = False
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    cleanup_ok = False
        return cleanup_ok and proc.poll() is not None

    @classmethod
    def _spawn(cls, command: list[str], *, deadline_seconds: float, max_bytes: int,
               container_name: str | None = None) -> dict[str, Any]:
        """Bounded stdout+stderr, bounded time and process-group termination.

        Called only with the validated Podman executable and static control
        commands, never with an untrusted host executable or shell=True.
        """
        if not 0 < deadline_seconds <= 86400 or not 0 < max_bytes <= 52428800:
            raise SandboxPolicyError("invalid process bounds")
        started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            proc = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    close_fds=True, start_new_session=True)
        except (OSError, ValueError) as exc:
            return {"termination_reason": "SANDBOX_UNAVAILABLE", "exit_code": None,
                    "reason_code": "SANDBOX_UNAVAILABLE", "diagnostic": type(exc).__name__}
        stdout, stderr = bytearray(), bytearray()
        reason = "EXITED"
        cleanup_ok = None
        max_time = time.monotonic() + deadline_seconds
        try:
            with selectors.DefaultSelector() as sel:
                for name, pipe in (("stdout", proc.stdout), ("stderr", proc.stderr)):
                    if pipe is not None:
                        os.set_blocking(pipe.fileno(), False)
                        sel.register(pipe, selectors.EVENT_READ, name)
                while sel.get_map() or proc.poll() is None:
                    if time.monotonic() >= max_time:
                        reason = "TIMED_OUT"
                        break
                    for key, _ in sel.select(timeout=min(0.1, max(0.0, max_time - time.monotonic()))):
                        try:
                            chunk = os.read(key.fileobj.fileno(), 65536)
                        except BlockingIOError:
                            continue
                        if not chunk:
                            sel.unregister(key.fileobj)
                            continue
                        dest = stdout if key.data == "stdout" else stderr
                        room = max_bytes - len(stdout) - len(stderr)
                        if len(chunk) > room:
                            dest.extend(chunk[:max(0, room)])
                            reason = "OUTPUT_LIMIT_EXCEEDED"
                            break
                        dest.extend(chunk)
                    if reason != "EXITED":
                        break
            if reason != "EXITED":
                cleanup_ok = cls._end_process(proc, command[0], container_name)
            elif proc.poll() is None:
                proc.wait(timeout=max(0.05, max_time - time.monotonic()))
        except (OSError, subprocess.TimeoutExpired):
            reason = "SANDBOX_UNAVAILABLE"
            cleanup_ok = cls._end_process(proc, command[0], container_name)
        finally:
            for pipe in (proc.stdout, proc.stderr):
                if pipe is not None:
                    pipe.close()
            if proc.poll() is None:
                cleanup_ok = cls._end_process(proc, command[0], container_name)
        code = proc.returncode
        return {
            "termination_reason": reason, "exit_code": code,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "output_limit_exceeded": reason == "OUTPUT_LIMIT_EXCEEDED",
            "cleanup_status": ("NOT_REQUIRED" if cleanup_ok is None else
                               "PASS" if cleanup_ok is True else "FAILED"),
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    def _control(self, podman: str, args: list[str], *, timeout: float = 12.0) -> dict[str, Any]:
        return self._spawn([podman, "--remote=false", *args], deadline_seconds=timeout, max_bytes=2_097_152)

    def _selftest_container(self, podman: str, profile: dict, sources: dict,
                            *, executable: str, argv: list[str], timeout: float = 15.0) -> dict:
        name = _container_name()
        command = self._command(profile, sources, podman=podman, name=name,
                                executable=executable, argv=argv,
                                uid=os.geteuid(), gid=os.getegid())
        result = self._spawn(command, deadline_seconds=timeout,
                             max_bytes=min(profile["limits"]["output_bytes"], 1_048_576),
                             container_name=name)
        result["_container_name"] = name
        return result

    def doctor(self, profile: dict[str, Any]) -> dict[str, Any]:
        """No PASS from schema validity, mocked output or skipped probes."""
        checks: dict[str, Any] = {}
        try:
            p = validate_sandbox_profile(profile)
            executable = validate_container_executable(self._configured_executable)
        except SandboxPolicyError as exc:
            return _blocked("SANDBOX_POLICY_FAILURE", str(exc))
        if p["network_mode"] != "NONE":
            return _blocked("NETWORK_NOT_APPROVED",
                            "Per-Run egress capability + formal approval not supported before PH-051-09")
        if os.geteuid() == 0:
            return _blocked("SANDBOX_UNAVAILABLE", "Host is root; rootless Podman is mandatory")
        podman = self._podman()
        if podman is None:
            return _blocked("SANDBOX_UNAVAILABLE", "Podman binary missing/unusable; install rootless Podman")
        info = self._control(podman, ["info", "--format", "json"])
        if info["termination_reason"] != "EXITED" or info["exit_code"] != 0:
            return _blocked("SANDBOX_UNAVAILABLE", "podman info failed (rootless setup?)")
        try:
            parsed = json.loads(info["stdout"])
        except (ValueError, TypeError):
            return _blocked("SANDBOX_UNAVAILABLE", "podman info returned unparseable metadata")
        host = parsed.get("host") if isinstance(parsed, dict) else None
        security = host.get("security") if isinstance(host, dict) else None
        if not isinstance(security, dict) or security.get("rootless") is not True:
            return _blocked("SANDBOX_UNAVAILABLE", "Podman reports non-rootless or unknown rootless status")
        checks["rootless"] = "PASS"
        image_exists = self._control(podman, ["image", "exists", p["image"]])
        if image_exists["termination_reason"] != "EXITED" or image_exists["exit_code"] != 0:
            return _blocked("SANDBOX_UNAVAILABLE", "Pinned image digest not present locally; no implicit pull", checks)
        checks["image_digest_local"] = "PASS"
        try:
            with tempfile.TemporaryDirectory(prefix="ph-05103-sandbox-doctor-") as temp:
                root = Path(temp)
                sources = {}
                for key, child in (("product_dir", "product"), ("control_dir", "control"), ("output_dir", "output")):
                    path = root / child
                    path.mkdir(mode=0o755)
                    sources[key] = path
                (sources["control_dir"] / "locked").write_text("locked", encoding="utf-8")
                # Validate same static source/path rules as real process mounts.
                checks["mount_policy"] = "PASS"
                boundary = self._selftest_container(podman, p, sources,
                                                    executable="/bin/sh", argv=["-ec", _BOUNDARY_PROBE])
                if boundary["termination_reason"] != "EXITED" or boundary["exit_code"] != 0 or "BOUNDARY_PASS" not in boundary["stdout"]:
                    checks["mount_nonroot_caps_nnp_home_sockets"] = "FAIL"
                    return _blocked("SANDBOX_POLICY_FAILURE", "Rootfs/control/mount/capability/user security probe failed", checks)
                if (sources["control_dir"] / "locked").read_text(encoding="utf-8") != "locked":
                    checks["mount_nonroot_caps_nnp_home_sockets"] = "FAIL"
                    return _blocked("SANDBOX_POLICY_FAILURE", "Control projection was modified by test container", checks)
                if (sources["product_dir"] / "probe-product").read_text(encoding="utf-8") != "ok" or (
                        sources["output_dir"] / "probe-result").read_text(encoding="utf-8") != "ok":
                    checks["mount_nonroot_caps_nnp_home_sockets"] = "FAIL"
                    return _blocked("SANDBOX_POLICY_FAILURE", "Writable mounts did not persist test outputs", checks)
                checks["mount_nonroot_caps_nnp_home_sockets"] = "PASS"
                kernel = self._selftest_container(podman, p, sources,
                                                  executable="python3", argv=["-c", _KERNEL_PROBE,
                                                    str(p["limits"]["memory_mb"]),
                                                    str(p["limits"]["pids"]), str(p["limits"]["cpu_count"])])
                if kernel["termination_reason"] != "EXITED" or kernel["exit_code"] != 0 or "KERNEL_PASS" not in kernel["stdout"]:
                    checks["kernel_cgroups_and_none_network"] = "UNKNOWN"
                    return _blocked("SANDBOX_UNAVAILABLE", "Kernel network/cgroup probe failed or unavailable; cannot attest isolation", checks)
                checks["kernel_cgroups_and_none_network"] = "PASS"
                binary = self._selftest_container(podman, p, sources,
                                                  executable="/bin/sh", argv=["-ec", 'command -v "$1" >/dev/null', "sh", executable])
                if binary["termination_reason"] != "EXITED" or binary["exit_code"] != 0:
                    checks["configured_executable"] = "FAIL"
                    return _blocked("EXECUTOR_UNAVAILABLE", "Configured executor executable not found inside pinned image", checks)
                checks["configured_executable"] = "PASS"
                termination = self._selftest_container(podman, p, sources,
                                                       executable="/bin/sh", argv=["-ec", "while :; do :; done"], timeout=1.0)
                gone = self._control(podman, ["container", "exists", termination["_container_name"]])
                if termination["termination_reason"] != "TIMED_OUT" or gone["termination_reason"] != "EXITED" or gone["exit_code"] != 1:
                    checks["timeout_stop_cleanup"] = "FAIL"
                    return _blocked("SANDBOX_POLICY_FAILURE", "Timed container failed termination probe", checks)
                checks["timeout_stop_cleanup"] = "PASS"
        except (OSError, SandboxPolicyError, ValueError) as exc:
            return _blocked("SANDBOX_UNAVAILABLE", f"Self-test could not validate environment: {type(exc).__name__}", checks)
        return {"status": "PASS", "backend": "ROOTLESS_PODMAN",
                "reason_code": None, "isolation_verified": True,
                "network_mode": "NONE", "checks": checks}

    def project_orphan_containers(self, project_root: Path) -> dict[str, Any]:
        """Inspect and terminate only containers carrying this project's labels.

        Called under the host-only per-project operation lock. Never interprets
        output as a shell command. A missing Podman or unverifiable label set is
        UNKNOWN/BLOCKED, never proof that no orphan container exists.
        """
        podman = self._podman()
        if not podman or os.geteuid() <= 0:
            return _blocked("SANDBOX_UNAVAILABLE", "Cannot inspect rootless Podman orphan containers")
        try:
            owner = _project_owner(Path(project_root))
        except OSError:
            return _blocked("SANDBOX_POLICY_FAILURE", "Canonical project root unavailable")
        result = self._control(podman, ["ps", "--all", "--filter",
                                       "label=io.project-harness.sandbox=PH-051-03",
                                       "--filter", f"label={_PROJECT_LABEL}={owner}",
                                       "--format", "json"])
        if result.get("termination_reason") != "EXITED" or result.get("exit_code") != 0:
            return _blocked("SANDBOX_UNAVAILABLE", "Podman orphan listing failed")
        try:
            rows = json.loads(result.get("stdout", ""))
            if not isinstance(rows, list):
                raise ValueError("Not an array")
            checked: list[tuple[str, str]] = []
            for entry in rows:
                labels = entry.get("Labels") or entry.get("labels")
                if not isinstance(labels, dict):
                    raise ValueError("Uninspectable container labels")
                if (labels.get("io.project-harness.sandbox") != "PH-051-03" or
                        labels.get(_PROJECT_LABEL) != owner or
                        not _RUN_REF_RE.fullmatch(labels.get(_RUN_LABEL) or "")):
                    raise ValueError("Unbound Podman container in project filter")
                ident = entry.get("Id") or entry.get("ID") or entry.get("id")
                names = entry.get("Names") or entry.get("names")
                if not isinstance(ident, str) or not re.fullmatch(r"[a-f0-9]{12,64}", ident):
                    raise ValueError("Unidentifiable container")
                if isinstance(names, list):
                    names = names[0] if len(names) == 1 else None
                if not isinstance(names, str) or not re.fullmatch(r"ph-05103-[a-f0-9]{20}", names):
                    raise ValueError("Unexpected container name")
                checked.append((ident, labels[_RUN_LABEL]))
        except (TypeError, ValueError, AttributeError):
            return _blocked("SANDBOX_POLICY_FAILURE", "Podman orphan list has untrusted/missing identity labels")
        stopped: list[str] = []
        for ident, run_ref in checked:
            # Podman stop first signals SIGTERM, then kills after its bounded
            # grace interval. rm --force is a last-resort container reaper.
            self._control(podman, ["stop", "--time", "2", ident], timeout=8)
            removed = self._control(podman, ["rm", "--force", ident], timeout=8)
            check = self._control(podman, ["container", "exists", ident], timeout=6)
            if removed.get("termination_reason") != "EXITED" or check.get("termination_reason") != "EXITED" or check.get("exit_code") != 1:
                return _blocked("SANDBOX_UNAVAILABLE", "Cannot prove orphan container terminated",
                                {"stopped_runs": stopped, "unresolved_run": run_ref})
            stopped.append(run_ref)
        return {"status": "PASS", "backend": "ROOTLESS_PODMAN",
                "stopped_run_refs": stopped, "orphan_count": len(stopped)}

    def run(self, request: dict[str, Any], *,
            resolved_environment: Mapping[str, str] | None = None) -> dict[str, Any]:
        """Only a current verified profile permits in-container invocation.

        This is an isolation primitive, not a Run approval, verification or
        completion transition. No public execute-current route exists yet.
        """
        try:
            if not isinstance(request, dict) or set(request) - {
                "sandbox_profile", "argv", "run_context", "stdin_mode",
                "execution_root", "canonical_project_root", "product_dir", "control_dir",
                "output_dir", "network_mode", "timeout_seconds",
            }:
                raise SandboxPolicyError("unexpected sandbox request fields")
            p = validate_sandbox_profile(request.get("sandbox_profile"))
            if request.get("stdin_mode") != "CLOSED":
                raise SandboxPolicyError("stdin_mode must be CLOSED")
            if request.get("network_mode", "NONE") != "NONE" or p["network_mode"] != "NONE":
                return _blocked("NETWORK_NOT_APPROVED", "Per-Run egress approval does not exist at PH-051-03")
            executable = validate_container_executable(self._configured_executable)
            argv = validate_argv(request.get("argv"), executable)
            mounts = validate_execution_mounts(request)
            bindings = {key: (path.stat().st_dev, path.stat().st_ino) for key, path in mounts.items()}
            # A low-level caller cannot broaden sandbox resource limits.
            timeout = request.get("timeout_seconds", p["limits"]["timeout_seconds"])
            if type(timeout) not in (int, float) or not 0 < timeout <= p["limits"]["timeout_seconds"]:
                raise SandboxPolicyError("invalid bounded timeout override")
            run_context = request.get("run_context")
            if run_context is not None:
                if not isinstance(run_context, dict) or not isinstance(run_context.get("adapter_profile"), dict):
                    raise SandboxPolicyError("untrusted environment policy")
                from project_harness.executors.codex_cli_local import _profile
                active_profile = _profile(run_context["adapter_profile"])
                environment, secret_values = resolve_execution_environment(active_profile)
            else:
                environment, secret_values = {}, {}
            if resolved_environment is not None and dict(resolved_environment) != environment:
                raise SandboxPolicyError("resolved environment changed between preflight and dispatch")
        except ResultChannelError as exc:
            return _blocked(exc.reason_code, "required execution environment cannot be resolved")
        except (SandboxPolicyError, OSError, ValueError) as exc:
            return _blocked("SANDBOX_POLICY_FAILURE", f"invalid mount/profile binding: {type(exc).__name__}: {exc}")
        health = self.doctor(p)
        if health.get("status") != "PASS" or health.get("isolation_verified") is not True:
            return _blocked(health.get("reason_code", "SANDBOX_UNAVAILABLE"),
                            "Automatic execution blocked: Podman doctor did not PASS", health.get("checks"))
        podman = self._podman()
        if podman is None:
            return _blocked("SANDBOX_UNAVAILABLE", "Podman binary unavailable after doctor")
        try:
            current_mounts = validate_execution_mounts(request)
            if any(current_mounts[key] != path or
                   (current_mounts[key].stat().st_dev, current_mounts[key].stat().st_ino) != bindings[key]
                   for key, path in mounts.items()):
                raise SandboxPolicyError("mount directories changed during doctor")
        except (SandboxPolicyError, OSError):
            return _blocked("SANDBOX_POLICY_FAILURE", "disposable mount source changed during doctor")
        name = _container_name()
        # A temporary 0600 file is consumed by the host Podman control process,
        # never mounted into the container; secret *values* are not in argv or
        # returned diagnostics, and the file is deleted on all process exits.
        def spawn_with_environment() -> dict[str, Any]:
            # Keep transient host-only secret files inside this *disposable*
            # Run root, not a global shared /tmp namespace. They are never
            # mounted; crash cleanup/quarantine can discover and erase them.
            with tempfile.TemporaryDirectory(prefix=".ph05110-env-", dir=str(mounts["execution_root"])) as temporary:
                env_path = None
                if environment:
                    env_path = Path(temporary) / "environment"
                    fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    try:
                        with os.fdopen(fd, "wb") as stream:
                            data = "".join(f"{k}={v}\n" for k, v in sorted(environment.items()))
                            stream.write(data.encode("utf-8"))
                            stream.flush()
                            os.fsync(stream.fileno())
                    except BaseException:
                        env_path.unlink(missing_ok=True)
                        raise
                run_context = request.get("run_context")
                run_id = run_context.get("run_id") if run_context is not None else None
                if run_context is not None and not _RUN_REF_RE.fullmatch(run_id or ""):
                    raise SandboxPolicyError("Run label identity is invalid")
                sealed = self._command(p, mounts, podman=podman, name=name,
                                       executable=executable, argv=argv[1:],
                                       uid=os.geteuid(), gid=os.getegid(), environment_file=env_path,
                                       project_owner=_project_owner(Path(request["canonical_project_root"])) if run_context is not None else None,
                                       run_ref=run_id)
                try:
                    return self._spawn(sealed, deadline_seconds=float(timeout),
                                       max_bytes=p["limits"]["output_bytes"], container_name=name)
                finally:
                    if env_path is not None and env_path.exists():
                        # Best-effort erase, as well as unlink. Crash cleanup
                        # of transient files is PH-051-10, not a security PASS.
                        try:
                            with env_path.open("r+b") as stream:
                                length = env_path.stat().st_size
                                while length:
                                    block = min(length, 8192)
                                    stream.write(b"\0" * block)
                                    length -= block
                                stream.flush()
                                os.fsync(stream.fileno())
                        except OSError:
                            pass
        try:
            result = spawn_with_environment()
        except (OSError, ValueError, SandboxPolicyError):
            return _blocked("SANDBOX_UNAVAILABLE", "trusted execution environment could not be safely provisioned")
        # Agent raw logs must never leave the trusted runner. Exact-value
        # detection is stronger than redaction: any leak blocks this attempt.
        leaked = any(scan_exact_secret(result.get(k, ""), secret_values) for k in ("stdout", "stderr"))
        for label in ("stdout", "stderr"):
            if isinstance(result.get(label), str):
                result[label] = redact_exact_secrets(result[label], secret_values)
        if leaked:
            result["reason_code"] = "SECRET_LEAK_DETECTED"
        result["backend"] = "ROOTLESS_PODMAN"
        # Exit 125/126/127 is reserved by Podman for invocation/start errors.
        # A previous PASS doctor does not attest that this Run container started.
        startup_failure = (result["termination_reason"] == "EXITED" and
                           result.get("exit_code") in (125, 126, 127))
        result["isolation_verified"] = (result["termination_reason"] != "SANDBOX_UNAVAILABLE"
                                        and not startup_failure and result.get("cleanup_status") != "FAILED")
        # OS doctor success does not claim a container launched if Podman failed.
        if startup_failure or result.get("cleanup_status") == "FAILED":
            # SIGTERM/SIGKILL or Podman stop/rm not proven. A descendant
            # might still run: never normalize a PASS result from this host.
            # A detected secret leak retains its more specific failure reason.
            if not leaked:
                result["reason_code"] = "SANDBOX_UNAVAILABLE"
        elif result["termination_reason"] == "OUTPUT_LIMIT_EXCEEDED":
            result["reason_code"] = "OUTPUT_LIMIT_EXCEEDED"
        elif result["termination_reason"] == "TIMED_OUT":
            result["reason_code"] = "EXECUTOR_TIMEOUT"
        elif result["termination_reason"] != "EXITED":
            result["reason_code"] = "SANDBOX_UNAVAILABLE"
        return result
