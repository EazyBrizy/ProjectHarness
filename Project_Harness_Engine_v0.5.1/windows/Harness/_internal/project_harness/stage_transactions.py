from __future__ import annotations

from copy import deepcopy
import errno
import os
from pathlib import Path
import shutil
from typing import Any, Callable, Iterable

from .errors import ValidationFailure
from .hashing import sha256_bytes, sha256_file
from .serialization import canonical_json_bytes, load_data, write_data
from .util import utc_now
from .platform_fs import (ensure_native_path, ensure_writable_target,
                          safe_relative, stage_project_lock)

STAGE_TRANSACTION_ROOT = Path(".harness/stages/TRANSACTIONS")
STAGE_TRANSACTION_JOURNAL = "TRANSACTION.yaml"
STAGE_TRANSACTION_SCHEMA_VERSION = 1
STAGE_TRANSACTION_STATUSES = {
    "PREPARED",
    "APPLYING",
    "ROLLING_BACK",
    "COMMITTED",
    "ROLLED_BACK",
    "RECOVERY_REQUIRED",
}
STAGE_TRANSACTION_TERMINAL_STATUSES = {"COMMITTED", "ROLLED_BACK"}
STAGE_TRANSACTION_INTERMEDIATE_STATUSES = {"PREPARED", "APPLYING", "ROLLING_BACK"}

# A Stage transaction is local-filesystem only. This callable is deliberately
# narrow so focused tests can inject failures at every canonical apply point.
CanonicalReplace = Callable[[Path, Path], None]


def digest_value(value: Any) -> str:
    """Return the canonical SHA-256 digest used by request/result journal fields."""
    return f"sha256:{sha256_bytes(canonical_json_bytes(value))}"


def _digest_file(path: Path) -> str:
    return f"sha256:{sha256_file(path)}"


def _fsync_directory(path: Path) -> None:
    """Persist a directory entry update where the platform supports it."""
    if os.name == "nt":
        # Python/Win32 offers file flush + same-volume os.replace but no
        # reliable directory-entry fsync. Windows power-loss durability is
        # NOT certified; OS errors on the actual file/replace still propagate.
        return
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        if exc.errno in {errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP, errno.EACCES}:
            return
        raise
    try:
        os.fsync(fd)
    except OSError as exc:
        if exc.errno not in {errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}:
            raise
    finally:
        os.close(fd)


def _fsync_file(path: Path) -> None:
    # Windows _commit/FlushFileBuffers requires a write-capable descriptor.
    # These are owned transaction staging/backup/journal files. Do not suppress
    # flush errors: a failed durable write must still block the transaction.
    fd = os.open(path, os.O_RDWR if os.name == 'nt' else os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _safe_relative_path(value: Path | str, *, field: str) -> Path:
    path = safe_relative(value, field=field)
    if path.is_absolute() or not path.parts or any(part in {"", ".."} for part in path.parts):
        raise ValidationFailure("Stage transaction contains an unsafe relative path", {"field": field, "path": str(value)})
    normalized = Path(*[part for part in path.parts if part != "."])
    if not normalized.parts:
        raise ValidationFailure("Stage transaction contains an empty relative path", field)
    return normalized


def _inside(root: Path, relative: Path, *, field: str) -> Path:
    relative = _safe_relative_path(relative, field=field)
    candidate = (root / relative).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValidationFailure("Stage transaction path escapes the project root", {"field": field, "path": relative.as_posix()}) from exc
    return candidate


def _transaction_dir(root: Path, transaction_id: str) -> Path:
    if not transaction_id or any(token in transaction_id for token in ("/", "\\", "..")):
        raise ValidationFailure("Stage transaction id is invalid", transaction_id)
    return root / STAGE_TRANSACTION_ROOT / transaction_id


def _journal_path(root: Path, transaction_id: str) -> Path:
    return _transaction_dir(root, transaction_id) / STAGE_TRANSACTION_JOURNAL


def _journal_envelope(journal: dict[str, Any]) -> dict[str, Any]:
    return {"stage_transaction": journal}


def _persist_journal(root: Path, journal: dict[str, Any]) -> None:
    """Atomically persist and fsync the complete journal snapshot."""
    transaction_id = str(journal.get("id") or "")
    path = _journal_path(root, transaction_id)
    journal["journal_revision"] = int(journal.get("journal_revision", 0)) + 1
    journal["updated_at"] = utc_now()
    write_data(path, _journal_envelope(journal))
    _fsync_file(path)
    _fsync_directory(path.parent)


def _load_journal(root: Path, transaction_id: str) -> dict[str, Any]:
    path = _journal_path(root, transaction_id)
    if not path.exists():
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: transaction directory has no durable journal",
            {"transaction_id": transaction_id, "journal_path": str(path)},
        )
    try:
        value = load_data(path)
    except Exception as exc:
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: transaction journal cannot be read",
            {"transaction_id": transaction_id, "journal_path": str(path), "error": str(exc)},
        ) from exc
    journal = value.get("stage_transaction") if isinstance(value, dict) else None
    if not isinstance(journal, dict):
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: stage_transaction envelope is invalid",
            {"transaction_id": transaction_id, "journal_path": str(path)},
        )
    return journal


def _write_set_digest(entries: Iterable[dict[str, Any]]) -> str:
    immutable = [
        {
            "ordinal": entry.get("ordinal"),
            "target": entry.get("target"),
            "existed_before": entry.get("existed_before"),
            "backup_path": entry.get("backup_path"),
            "staged_path": entry.get("staged_path"),
            "old_digest": entry.get("old_digest"),
            "expected_new_digest": entry.get("expected_new_digest"),
        }
        for entry in entries
    ]
    return digest_value(immutable)


def _validate_digest(value: Any, *, field: str, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValidationFailure("Stage transaction digest is invalid", {"field": field, "value": value})
    try:
        int(value.removeprefix("sha256:"), 16)
    except ValueError as exc:
        raise ValidationFailure("Stage transaction digest is invalid", {"field": field, "value": value}) from exc


def _validate_journal_structure(root: Path, transaction_dir: Path, journal: dict[str, Any]) -> None:
    transaction_id = str(journal.get("id") or "")
    required = {
        "schema_version",
        "id",
        "operation_kind",
        "request_digest",
        "sequence",
        "status",
        "ordered_write_set",
        "entries",
        "write_set_digest",
        "result",
        "result_digest",
        "created_at",
        "prepared_at",
        "updated_at",
        "journal_revision",
    }
    missing = sorted(required - set(journal))
    if missing:
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: journal is missing required fields",
            {"transaction_id": transaction_id or transaction_dir.name, "missing": missing},
        )
    if journal.get("schema_version") != STAGE_TRANSACTION_SCHEMA_VERSION:
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: unsupported journal schema_version",
            {"transaction_id": transaction_id, "schema_version": journal.get("schema_version")},
        )
    if transaction_id != transaction_dir.name:
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: journal id differs from directory name",
            {"journal_id": transaction_id, "directory": transaction_dir.name},
        )
    operation_kind = journal.get("operation_kind")
    if not isinstance(operation_kind, str) or not operation_kind or operation_kind.upper() != operation_kind:
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: operation_kind must be a non-empty uppercase token",
            {"transaction_id": transaction_id, "operation_kind": operation_kind},
        )
    if not isinstance(journal.get("sequence"), int) or int(journal["sequence"]) < 1:
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: sequence must be a positive integer",
            {"transaction_id": transaction_id, "sequence": journal.get("sequence")},
        )
    if not isinstance(journal.get("journal_revision"), int) or int(journal["journal_revision"]) < 1:
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: journal_revision must be a positive integer",
            {"transaction_id": transaction_id, "journal_revision": journal.get("journal_revision")},
        )
    status = journal.get("status")
    if status not in STAGE_TRANSACTION_STATUSES:
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: unknown transaction status",
            {"transaction_id": transaction_id, "status": status},
        )
    for field in ("created_at", "prepared_at", "updated_at"):
        value = journal.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: required transaction timestamp is invalid",
                {"transaction_id": transaction_id, "field": field, "value": value},
            )
    for field in (
        "apply_started_at",
        "commit_verified_at",
        "committed_at",
        "recovery_started_at",
        "rolled_back_at",
    ):
        value = journal.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: optional transaction timestamp is invalid",
                {"transaction_id": transaction_id, "field": field, "value": value},
            )
    _validate_digest(journal.get("request_digest"), field="request_digest")
    _validate_digest(journal.get("write_set_digest"), field="write_set_digest")
    _validate_digest(journal.get("result_digest"), field="result_digest")
    if not isinstance(journal.get("result"), dict):
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: result must be an object",
            {"transaction_id": transaction_id},
        )
    if digest_value(journal["result"]) != journal["result_digest"]:
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: result digest mismatch",
            {"transaction_id": transaction_id},
        )

    ordered = journal.get("ordered_write_set")
    entries = journal.get("entries")
    if not isinstance(ordered, list) or not ordered or not all(isinstance(item, str) for item in ordered):
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: ordered_write_set must be a non-empty string array",
            {"transaction_id": transaction_id},
        )
    if not isinstance(entries, list) or len(entries) != len(ordered):
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: entries do not match ordered_write_set",
            {"transaction_id": transaction_id, "ordered": len(ordered), "entries": len(entries) if isinstance(entries, list) else None},
        )
    if len(set(ordered)) != len(ordered):
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: ordered_write_set contains duplicate targets",
            {"transaction_id": transaction_id},
        )
    if ordered != sorted(ordered):
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: ordered_write_set violates lexicographic order policy",
            {"transaction_id": transaction_id},
        )

    expected_ordinals = list(range(1, len(entries) + 1))
    actual_ordinals = [entry.get("ordinal") if isinstance(entry, dict) else None for entry in entries]
    if actual_ordinals != expected_ordinals:
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: entry ordinals are not contiguous",
            {"transaction_id": transaction_id, "ordinals": actual_ordinals},
        )

    tx_relative = transaction_dir.relative_to(root)
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: transaction entry is not an object",
                {"transaction_id": transaction_id, "ordinal": index},
            )
        target_rel = _safe_relative_path(str(entry.get("target") or ""), field=f"entries[{index}].target")
        if target_rel.as_posix() != ordered[index - 1]:
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: entry target differs from ordered_write_set",
                {"transaction_id": transaction_id, "ordinal": index},
            )
        if target_rel == tx_relative or tx_relative in target_rel.parents:
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: canonical write target overlaps transaction storage",
                {"transaction_id": transaction_id, "target": target_rel.as_posix()},
            )
        _inside(root, target_rel, field=f"entries[{index}].target")
        existed_before = entry.get("existed_before")
        if not isinstance(existed_before, bool):
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: existed_before must be boolean",
                {"transaction_id": transaction_id, "ordinal": index},
            )
        _validate_digest(entry.get("old_digest"), field=f"entries[{index}].old_digest", nullable=not existed_before)
        _validate_digest(entry.get("expected_new_digest"), field=f"entries[{index}].expected_new_digest")
        if existed_before and entry.get("old_digest") is None:
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: existing target has no old_digest",
                {"transaction_id": transaction_id, "ordinal": index},
            )
        if not existed_before and entry.get("old_digest") is not None:
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: absent target unexpectedly has old_digest",
                {"transaction_id": transaction_id, "ordinal": index},
            )

        staged_rel = _safe_relative_path(str(entry.get("staged_path") or ""), field=f"entries[{index}].staged_path")
        staged_path = _inside(root, staged_rel, field=f"entries[{index}].staged_path")
        try:
            staged_path.relative_to(transaction_dir)
        except ValueError as exc:
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: staged_path is outside its transaction directory",
                {"transaction_id": transaction_id, "ordinal": index, "path": staged_rel.as_posix()},
            ) from exc

        backup_value = entry.get("backup_path")
        if existed_before:
            backup_rel = _safe_relative_path(str(backup_value or ""), field=f"entries[{index}].backup_path")
            backup_path = _inside(root, backup_rel, field=f"entries[{index}].backup_path")
            try:
                backup_path.relative_to(transaction_dir)
            except ValueError as exc:
                raise ValidationFailure(
                    "STAGE_TRANSACTION_CORRUPT: backup_path is outside its transaction directory",
                    {"transaction_id": transaction_id, "ordinal": index, "path": backup_rel.as_posix()},
                ) from exc
            if not backup_path.is_file() or backup_path.is_symlink():
                raise ValidationFailure(
                    "STAGE_TRANSACTION_CORRUPT: required backup is missing or not a regular file",
                    {"transaction_id": transaction_id, "ordinal": index, "backup_path": backup_rel.as_posix()},
                )
            actual_backup = _digest_file(backup_path)
            if actual_backup != entry["old_digest"]:
                raise ValidationFailure(
                    "STAGE_TRANSACTION_CORRUPT: backup digest mismatch",
                    {
                        "transaction_id": transaction_id,
                        "ordinal": index,
                        "backup_path": backup_rel.as_posix(),
                        "expected": entry["old_digest"],
                        "actual": actual_backup,
                    },
                )
        elif backup_value is not None:
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: absent-before entry must not have a backup_path",
                {"transaction_id": transaction_id, "ordinal": index, "backup_path": backup_value},
            )

        if entry.get("apply_state") not in {"PENDING", "APPLIED", "VERIFIED"}:
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: invalid apply_state",
                {"transaction_id": transaction_id, "ordinal": index, "apply_state": entry.get("apply_state")},
            )
        if entry.get("recovery_state") not in {"NOT_REQUIRED", "PENDING", "RESTORED", "REMOVED", "VERIFIED"}:
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: invalid recovery_state",
                {"transaction_id": transaction_id, "ordinal": index, "recovery_state": entry.get("recovery_state")},
            )
        for field in ("applied_at", "recovered_at"):
            value = entry.get(field)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValidationFailure(
                    "STAGE_TRANSACTION_CORRUPT: per-entry timestamp is invalid",
                    {"transaction_id": transaction_id, "ordinal": index, "field": field, "value": value},
                )

    if _write_set_digest(entries) != journal["write_set_digest"]:
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: write_set_digest mismatch",
            {"transaction_id": transaction_id},
        )
    if status == "COMMITTED" and not journal.get("committed_at"):
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: COMMITTED journal lacks committed_at",
            {"transaction_id": transaction_id},
        )
    if status == "COMMITTED":
        if not journal.get("commit_verified_at") or not journal.get("apply_started_at"):
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: COMMITTED journal lacks apply/verification timestamps",
                {"transaction_id": transaction_id},
            )
        invalid_entries = [
            entry["ordinal"]
            for entry in entries
            if entry.get("apply_state") != "VERIFIED" or entry.get("recovery_state") != "NOT_REQUIRED"
        ]
        if invalid_entries:
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: COMMITTED entry states are not verified",
                {"transaction_id": transaction_id, "ordinals": invalid_entries},
            )
    if status == "ROLLED_BACK" and not journal.get("rolled_back_at"):
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: ROLLED_BACK journal lacks rolled_back_at",
            {"transaction_id": transaction_id},
        )
    if status == "ROLLED_BACK":
        if not journal.get("recovery_started_at"):
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: ROLLED_BACK journal lacks recovery_started_at",
                {"transaction_id": transaction_id},
            )
        invalid_entries = [
            entry["ordinal"] for entry in entries if entry.get("recovery_state") != "VERIFIED"
        ]
        if invalid_entries:
            raise ValidationFailure(
                "STAGE_TRANSACTION_CORRUPT: ROLLED_BACK entry states are not verified",
                {"transaction_id": transaction_id, "ordinals": invalid_entries},
            )


def _load_validated_journal(root: Path, transaction_id: str) -> dict[str, Any]:
    transaction_dir = _transaction_dir(root, transaction_id)
    journal = _load_journal(root, transaction_id)
    _validate_journal_structure(root, transaction_dir, journal)
    return journal


def _entry_target(root: Path, entry: dict[str, Any]) -> Path:
    return _inside(root, Path(str(entry["target"])), field="entry.target")


def _entry_state(root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    target = _entry_target(root, entry)
    if target.is_symlink():
        return {"state": "OTHER", "digest": None, "exists": True, "reason": "SYMLINK"}
    if not target.exists():
        if entry["existed_before"]:
            return {"state": "OTHER", "digest": None, "exists": False, "reason": "MISSING_OLD_TARGET"}
        return {"state": "OLD", "digest": None, "exists": False, "reason": None}
    if not target.is_file():
        return {"state": "OTHER", "digest": None, "exists": True, "reason": "NOT_REGULAR_FILE"}
    actual = _digest_file(target)
    if actual == entry["expected_new_digest"]:
        return {"state": "NEW", "digest": actual, "exists": True, "reason": None}
    if entry["existed_before"] and actual == entry["old_digest"]:
        return {"state": "OLD", "digest": actual, "exists": True, "reason": None}
    return {"state": "OTHER", "digest": actual, "exists": True, "reason": "DIGEST_MISMATCH"}


def _canonical_snapshot(root: Path, journal: dict[str, Any]) -> dict[str, Any]:
    entries = []
    for entry in journal["entries"]:
        observed = _entry_state(root, entry)
        entries.append(
            {
                "ordinal": entry["ordinal"],
                "target": entry["target"],
                **observed,
            }
        )
    states = [item["state"] for item in entries]
    return {
        "all_new": bool(entries) and all(state == "NEW" for state in states),
        "all_old": bool(entries) and all(state == "OLD" for state in states),
        "mixed": len(set(states)) > 1 or any(state == "OTHER" for state in states),
        "entries": entries,
    }


def _replace_canonical(source: Path, target: Path) -> None:
    """Replace one canonical file and persist its directory entry."""
    os.replace(source, target)
    _fsync_directory(target.parent)


def _unlink_canonical(target: Path) -> None:
    target.unlink()
    _fsync_directory(target.parent)


def _next_sequence(root: Path) -> int:
    transaction_root = root / STAGE_TRANSACTION_ROOT
    maximum = 0
    if not transaction_root.exists():
        return 1
    for child in sorted(transaction_root.iterdir()):
        if not child.is_dir():
            continue
        path = child / STAGE_TRANSACTION_JOURNAL
        if not path.exists():
            continue
        try:
            value = load_data(path)
            journal = value.get("stage_transaction") if isinstance(value, dict) else None
            sequence = journal.get("sequence") if isinstance(journal, dict) else None
            if isinstance(sequence, int):
                maximum = max(maximum, sequence)
        except Exception:
            # Recovery/validation will surface the exact corrupt journal. Sequence
            # allocation never silently skips a readable invalid transaction.
            continue
    return maximum + 1


def _prepare_stage_transaction(
    root: Path,
    writes: dict[Path, Any],
    *,
    transaction_id: str,
    operation_kind: str,
    request_digest: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    if not writes:
        raise ValidationFailure("Stage transaction write set must not be empty", transaction_id)
    _validate_digest(request_digest, field="request_digest")
    # Reject unsupported paths, casefold aliases and immutable/read-only
    # targets *before* adding any transaction directory or canonical write.
    ensure_native_path(root, tree=True)
    seen_names: set[str] = set()
    for candidate in writes:
        relative = _safe_relative_path(candidate, field="writes.target")
        folded = relative.as_posix().casefold() if os.name == "nt" else relative.as_posix()
        if folded in seen_names:
            raise ValidationFailure("Stage transaction has duplicate/case-colliding write targets", relative.as_posix())
        seen_names.add(folded)
        target = _inside(root, relative, field="writes.target")
        ensure_writable_target(target)
    transaction_dir = _transaction_dir(root, transaction_id)
    if transaction_dir.exists():
        raise ValidationFailure("Stage transaction id already exists", transaction_id)
    transaction_root = transaction_dir.parent
    transaction_root.mkdir(parents=True, exist_ok=True)
    transaction_dir.mkdir(parents=False, exist_ok=False)
    backups_dir = transaction_dir / "backups"
    staged_dir = transaction_dir / "staged"
    recovery_dir = transaction_dir / "recovery"
    backups_dir.mkdir()
    staged_dir.mkdir()
    recovery_dir.mkdir()
    _fsync_directory(transaction_root)
    _fsync_directory(transaction_dir)

    entries: list[dict[str, Any]] = []
    ordered_items: list[tuple[Path, Any]] = []
    seen: set[str] = set()
    for relative, value in writes.items():
        normalized = _safe_relative_path(relative, field="writes.target")
        rel_text = normalized.as_posix()
        if rel_text in seen:
            raise ValidationFailure("Stage transaction has duplicate write targets", rel_text)
        seen.add(rel_text)
        ordered_items.append((normalized, value))
    ordered_items.sort(key=lambda item: item[0].as_posix())

    try:
        for ordinal, (relative, value) in enumerate(ordered_items, 1):
            target = _inside(root, relative, field=f"writes[{ordinal}].target")
            if target == transaction_dir or transaction_dir in target.parents:
                raise ValidationFailure("Stage transaction target overlaps transaction storage", relative.as_posix())
            if target.is_symlink():
                raise ValidationFailure("Stage transaction target must not be a symlink", relative.as_posix())
            if target.exists() and not target.is_file():
                raise ValidationFailure("Stage transaction target must be a regular file or absent", relative.as_posix())
            target.parent.mkdir(parents=True, exist_ok=True)

            existed_before = target.exists()
            backup_rel: str | None = None
            old_digest: str | None = None
            if existed_before:
                old_digest = _digest_file(target)
                backup = backups_dir / f"backup-{ordinal:03d}.old"
                shutil.copyfile(target, backup)
                _fsync_file(backup)
                backup_rel = backup.relative_to(root).as_posix()

            staged = staged_dir / f"staged-{ordinal:03d}.new"
            write_data(staged, value)
            _fsync_file(staged)
            entry = {
                "ordinal": ordinal,
                "target": relative.as_posix(),
                "existed_before": existed_before,
                "backup_path": backup_rel,
                "staged_path": staged.relative_to(root).as_posix(),
                "old_digest": old_digest,
                "expected_new_digest": _digest_file(staged),
                "apply_state": "PENDING",
                "recovery_state": "NOT_REQUIRED",
                "applied_at": None,
                "recovered_at": None,
            }
            entries.append(entry)
        _fsync_directory(backups_dir)
        _fsync_directory(staged_dir)

        now = utc_now()
        journal: dict[str, Any] = {
            "schema_version": STAGE_TRANSACTION_SCHEMA_VERSION,
            "id": transaction_id,
            "operation_kind": operation_kind,
            "request_digest": request_digest,
            "sequence": _next_sequence(root),
            "status": "PREPARED",
            "write_order_policy": "LEXICOGRAPHIC_RELATIVE_PATH_V1",
            "ordered_write_set": [entry["target"] for entry in entries],
            "entries": entries,
            "write_set_digest": _write_set_digest(entries),
            "result": deepcopy(result),
            "result_digest": digest_value(result),
            "created_at": now,
            "prepared_at": now,
            "apply_started_at": None,
            "commit_verified_at": None,
            "committed_at": None,
            "recovery_started_at": None,
            "rolled_back_at": None,
            "updated_at": now,
            "journal_revision": 0,
            "last_failure": None,
            "recovery_action": None,
        }
        _persist_journal(root, journal)
        return journal
    except Exception:
        # Before PREPARED is durably acknowledged no canonical replacement has
        # occurred. A controlled preparation failure can therefore remove its
        # private staging directory without guessing about canonical state.
        try:
            shutil.rmtree(transaction_dir)
            _fsync_directory(transaction_root)
        except OSError:
            pass
        raise


def _verify_staged_entry(root: Path, entry: dict[str, Any]) -> Path:
    staged = _inside(root, Path(str(entry["staged_path"])), field="entry.staged_path")
    if not staged.is_file() or staged.is_symlink():
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: staged file is missing before apply",
            {"ordinal": entry["ordinal"], "staged_path": entry["staged_path"]},
        )
    actual = _digest_file(staged)
    if actual != entry["expected_new_digest"]:
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: staged file digest mismatch",
            {
                "ordinal": entry["ordinal"],
                "staged_path": entry["staged_path"],
                "expected": entry["expected_new_digest"],
                "actual": actual,
            },
        )
    return staged


def _finalize_commit(root: Path, journal: dict[str, Any], *, recovery_action: str | None = None) -> dict[str, Any]:
    snapshot = _canonical_snapshot(root, journal)
    if not snapshot["all_new"]:
        raise ValidationFailure(
            "Stage transaction cannot be marked COMMITTED because the canonical write set is not fully new",
            {"transaction_id": journal["id"], "snapshot": snapshot},
        )
    now = utc_now()
    for entry in journal["entries"]:
        entry["apply_state"] = "VERIFIED"
        entry["recovery_state"] = "NOT_REQUIRED"
        entry["applied_at"] = entry.get("applied_at") or now
    journal["status"] = "COMMITTED"
    journal["commit_verified_at"] = now
    journal["committed_at"] = journal.get("committed_at") or now
    journal["recovery_action"] = recovery_action
    _persist_journal(root, journal)
    return journal


def _restore_old_entry(root: Path, transaction_dir: Path, entry: dict[str, Any]) -> None:
    target = _entry_target(root, entry)
    if entry["existed_before"]:
        backup = _inside(root, Path(str(entry["backup_path"])), field="entry.backup_path")
        if not backup.is_file() or backup.is_symlink():
            raise ValidationFailure(
                "STAGE_TRANSACTION_RECOVERY_BLOCKED: required backup is missing",
                {"transaction_id": transaction_dir.name, "ordinal": entry["ordinal"], "backup_path": entry["backup_path"]},
            )
        actual = _digest_file(backup)
        if actual != entry["old_digest"]:
            raise ValidationFailure(
                "STAGE_TRANSACTION_RECOVERY_BLOCKED: backup digest mismatch",
                {
                    "transaction_id": transaction_dir.name,
                    "ordinal": entry["ordinal"],
                    "backup_path": entry["backup_path"],
                    "expected": entry["old_digest"],
                    "actual": actual,
                },
            )
        recovery_dir = transaction_dir / "recovery"
        recovery_dir.mkdir(parents=True, exist_ok=True)
        restore = recovery_dir / f"restore-{int(entry['ordinal']):03d}.old"
        if restore.exists():
            restore.unlink()
        shutil.copyfile(backup, restore)
        _fsync_file(restore)
        target.parent.mkdir(parents=True, exist_ok=True)
        _replace_canonical(restore, target)
        entry["recovery_state"] = "RESTORED"
    else:
        if target.is_symlink():
            raise ValidationFailure(
                "STAGE_TRANSACTION_RECOVERY_BLOCKED: absent-before target became a symlink",
                {"transaction_id": transaction_dir.name, "ordinal": entry["ordinal"], "target": entry["target"]},
            )
        if target.exists():
            if not target.is_file():
                raise ValidationFailure(
                    "STAGE_TRANSACTION_RECOVERY_BLOCKED: absent-before target is not a regular file",
                    {"transaction_id": transaction_dir.name, "ordinal": entry["ordinal"], "target": entry["target"]},
                )
            _unlink_canonical(target)
        entry["recovery_state"] = "REMOVED"
    entry["recovered_at"] = utc_now()


def _rollback_transaction(
    root: Path,
    journal: dict[str, Any],
    *,
    failure: BaseException | None,
    recovery_action: str,
) -> dict[str, Any]:
    transaction_dir = _transaction_dir(root, str(journal["id"]))
    # Validate every required backup before starting a rollback. Recovery never
    # guesses after damaged journal/backups.
    _validate_journal_structure(root, transaction_dir, journal)
    journal["status"] = "ROLLING_BACK"
    journal["recovery_started_at"] = journal.get("recovery_started_at") or utc_now()
    journal["recovery_action"] = recovery_action
    if failure is not None:
        journal["last_failure"] = {"type": type(failure).__name__, "message": str(failure)}
    try:
        _persist_journal(root, journal)
    except Exception:
        # The durable PREPARED/APPLYING journal still contains the complete write
        # set and backups. Continue restoring old state; the terminal marker is
        # written only after full verification.
        pass

    progress_journal_failures: list[dict[str, Any]] = []
    for entry in reversed(journal["entries"]):
        _restore_old_entry(root, transaction_dir, entry)
        try:
            _persist_journal(root, journal)
        except Exception as exc:
            # Per-entry recovery progress is audit metadata, not permission to
            # stop halfway through restoring canonical state. Continue to the
            # full old-state verification; the terminal ROLLED_BACK snapshot is
            # still mandatory and must persist successfully.
            progress_journal_failures.append(
                {
                    "ordinal": entry["ordinal"],
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    snapshot = _canonical_snapshot(root, journal)
    if not snapshot["all_old"]:
        journal["status"] = "RECOVERY_REQUIRED"
        journal["last_failure"] = {
            "type": "ROLLBACK_VERIFICATION_FAILED",
            "message": "Canonical targets are not fully restored to the old write set.",
            "snapshot": snapshot,
        }
        try:
            _persist_journal(root, journal)
        finally:
            raise ValidationFailure(
                "STAGE_TRANSACTION_RECOVERY_BLOCKED: rollback verification failed",
                {"transaction_id": journal["id"], "snapshot": snapshot},
            )

    now = utc_now()
    for entry in journal["entries"]:
        entry["recovery_state"] = "VERIFIED"
    journal["status"] = "ROLLED_BACK"
    journal["rolled_back_at"] = now
    journal["recovery_action"] = recovery_action
    if progress_journal_failures:
        journal["recovery_progress_warnings"] = progress_journal_failures
    _persist_journal(root, journal)
    return journal


def _reconcile_transaction(
    root: Path,
    transaction_id: str,
    *,
    failure: BaseException | None,
) -> dict[str, Any]:
    journal = _load_validated_journal(root, transaction_id)
    status = journal["status"]
    if status == "COMMITTED":
        return {"status": "COMMITTED", "journal": journal, "action": "NO_ACTION"}
    if status == "ROLLED_BACK":
        return {"status": "ROLLED_BACK", "journal": journal, "action": "NO_ACTION"}
    if status == "RECOVERY_REQUIRED":
        raise ValidationFailure(
            "STAGE_TRANSACTION_RECOVERY_BLOCKED: transaction is marked RECOVERY_REQUIRED",
            {"transaction_id": transaction_id, "last_failure": journal.get("last_failure")},
        )

    snapshot = _canonical_snapshot(root, journal)
    if snapshot["all_new"]:
        try:
            committed = _finalize_commit(root, journal, recovery_action="COMMIT_COMPLETED_FROM_DIGESTS")
            return {"status": "COMMITTED", "journal": committed, "action": "COMMIT_COMPLETED_FROM_DIGESTS"}
        except Exception as commit_error:
            # A persistent inability to record COMMITTED cannot be reported as a
            # successful transition. Restore old state and durably mark rollback.
            try:
                rolled_back = _rollback_transaction(
                    root,
                    _load_validated_journal(root, transaction_id),
                    failure=commit_error,
                    recovery_action="ROLLBACK_AFTER_COMMIT_MARKER_FAILURE",
                )
            except Exception as rollback_error:
                raise ValidationFailure(
                    "STAGE_TRANSACTION_RECOVERY_BLOCKED: cannot durably finalize commit or rollback",
                    {
                        "transaction_id": transaction_id,
                        "commit_error": str(commit_error),
                        "rollback_error": str(rollback_error),
                    },
                ) from rollback_error
            return {
                "status": "ROLLED_BACK",
                "journal": rolled_back,
                "action": "ROLLBACK_AFTER_COMMIT_MARKER_FAILURE",
                "failure": commit_error,
            }

    rolled_back = _rollback_transaction(
        root,
        journal,
        failure=failure,
        recovery_action="ROLLBACK_TO_OLD_WRITE_SET",
    )
    return {"status": "ROLLED_BACK", "journal": rolled_back, "action": "ROLLBACK_TO_OLD_WRITE_SET"}


def _recover_stage_transactions_unlocked(root: Path) -> dict[str, Any]:
    """Reconcile every non-terminal Stage transaction before mutation/validation.

    Recovery is deterministic: a complete digest-confirmed new write set is
    committed; every other recoverable intermediate state is restored fully from
    backups. Missing/corrupt journal data or backups blocks recovery.
    """
    root = root.expanduser().resolve()
    transaction_root = root / STAGE_TRANSACTION_ROOT
    if not transaction_root.exists():
        return {"status": "PASS", "recovered": [], "transactions": 0}
    unexpected = [child.name for child in transaction_root.iterdir() if not child.is_dir()]
    if unexpected:
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: unexpected files exist in transaction root",
            {"path": str(transaction_root), "entries": sorted(unexpected)},
        )

    journals: list[dict[str, Any]] = []
    for transaction_dir in sorted(transaction_root.iterdir(), key=lambda path: path.name):
        journal = _load_journal(root, transaction_dir.name)
        _validate_journal_structure(root, transaction_dir, journal)
        journals.append(journal)
    sequences = [int(journal["sequence"]) for journal in journals]
    if len(sequences) != len(set(sequences)):
        raise ValidationFailure(
            "STAGE_TRANSACTION_CORRUPT: duplicate transaction sequence values",
            {"sequences": sequences},
        )
    journals.sort(key=lambda item: (int(item["sequence"]), str(item["id"])))
    pending = [journal for journal in journals if journal["status"] not in STAGE_TRANSACTION_TERMINAL_STATUSES]
    if pending:
        latest_sequence = max(sequences)
        unsafe = [journal["id"] for journal in pending if int(journal["sequence"]) != latest_sequence]
        if unsafe or len(pending) > 1:
            raise ValidationFailure(
                "STAGE_TRANSACTION_RECOVERY_BLOCKED: non-terminal transactions are not the unique latest transition",
                {"pending": [journal["id"] for journal in pending], "unsafe": unsafe},
            )

    recovered: list[dict[str, Any]] = []
    for journal in pending:
        if journal["status"] == "RECOVERY_REQUIRED":
            raise ValidationFailure(
                "STAGE_TRANSACTION_RECOVERY_BLOCKED: transaction requires manual repair",
                {"transaction_id": journal["id"], "last_failure": journal.get("last_failure")},
            )
        outcome = _reconcile_transaction(root, str(journal["id"]), failure=None)
        recovered.append(
            {
                "transaction_id": journal["id"],
                "status": outcome["status"],
                "action": outcome["action"],
            }
        )
    return {"status": "PASS", "recovered": recovered, "transactions": len(journals)}


def recover_stage_transactions(root: Path) -> dict[str, Any]:
    """Read-only when no recovery is required; OS-locked before any repair."""
    root = Path(root).expanduser().resolve()
    transaction_root = root / STAGE_TRANSACTION_ROOT
    if not transaction_root.exists():
        return {"status": "PASS", "recovered": [], "transactions": 0}
    # The first scan does not repair or write. A concurrent writer with a
    # PREPARED/APPLYING journal requires the *same* cross-process lock.
    for transaction_dir in transaction_root.iterdir():
        if not transaction_dir.is_dir():
            # The regular validation path will report corruption explicitly.
            continue
        journal_path = transaction_dir / STAGE_TRANSACTION_JOURNAL
        try:
            doc = load_data(journal_path)
        except ValidationFailure:
            # Corruption must be handled by the strict unlocked validator;
            # never erase it or silently consider the project recovered.
            with stage_project_lock(root):
                return _recover_stage_transactions_unlocked(root)
        body = doc.get("stage_transaction") if isinstance(doc, dict) else None
        if not isinstance(body, dict) or body.get("status") not in STAGE_TRANSACTION_TERMINAL_STATUSES:
            with stage_project_lock(root):
                return _recover_stage_transactions_unlocked(root)
    return _recover_stage_transactions_unlocked(root)


def committed_stage_transaction_result(
    root: Path,
    *,
    transaction_id: str,
    operation_kind: str,
    request_digest: str,
) -> dict[str, Any] | None:
    """Return the saved result for an exact committed transaction id."""
    root = root.expanduser().resolve()
    transaction_dir = _transaction_dir(root, transaction_id)
    if not transaction_dir.exists():
        return None
    journal = _load_validated_journal(root, transaction_id)
    if journal["operation_kind"] != operation_kind:
        raise ValidationFailure(
            "Stage transaction id was already used by another operation kind",
            {"transaction_id": transaction_id, "expected": operation_kind, "actual": journal["operation_kind"]},
        )
    if journal["request_digest"] != request_digest:
        raise ValidationFailure(
            "Stage transaction id was reused with a different request",
            {"transaction_id": transaction_id, "expected_request_digest": journal["request_digest"], "actual_request_digest": request_digest},
        )
    if journal["status"] == "COMMITTED":
        result = deepcopy(journal["result"])
        result["idempotent"] = True
        result["transaction_ref"] = transaction_id
        result["transaction_status"] = "COMMITTED"
        return result
    if journal["status"] == "ROLLED_BACK":
        raise ValidationFailure(
            "Stage transaction was rolled back; retry requires a new formal approval and transaction id",
            {"transaction_id": transaction_id, "operation_kind": operation_kind},
        )
    raise ValidationFailure(
        "Stage transaction is not terminal after recovery",
        {"transaction_id": transaction_id, "status": journal["status"]},
    )


def _apply_stage_transaction_locked(
    root: Path,
    writes: dict[Path, Any],
    *,
    transaction_id: str,
    operation_kind: str,
    request_digest: str,
    result: dict[str, Any],
    replace_canonical: CanonicalReplace | None = None,
) -> dict[str, Any]:
    """Prepare, apply, verify, and durably commit one Stage transition."""
    root = root.expanduser().resolve()
    _recover_stage_transactions_unlocked(root)
    existing = committed_stage_transaction_result(
        root,
        transaction_id=transaction_id,
        operation_kind=operation_kind,
        request_digest=request_digest,
    )
    if existing is not None:
        return {"status": "COMMITTED", "result": existing, "recovered": False, "action": "IDEMPOTENT_REPLAY"}

    journal = _prepare_stage_transaction(
        root,
        writes,
        transaction_id=transaction_id,
        operation_kind=operation_kind,
        request_digest=request_digest,
        result=result,
    )
    replace = replace_canonical or _replace_canonical
    try:
        # Re-read the durable PREPARED snapshot and verify every immutable
        # backup and staged candidate before the first canonical replacement.
        # A preparation artifact that cannot prove its own write set is never
        # allowed to enter APPLYING.
        journal = _load_validated_journal(root, transaction_id)
        for entry in journal["entries"]:
            _verify_staged_entry(root, entry)
        journal["status"] = "APPLYING"
        journal["apply_started_at"] = utc_now()
        _persist_journal(root, journal)
        for entry in journal["entries"]:
            staged = _verify_staged_entry(root, entry)
            target = _entry_target(root, entry)
            replace(staged, target)
            # Custom replacement hooks are required to preserve the same durability
            # contract as the default helper.
            if replace is not _replace_canonical:
                _fsync_directory(target.parent)
            entry["apply_state"] = "APPLIED"
            entry["applied_at"] = utc_now()
            _persist_journal(root, journal)
        committed = _finalize_commit(root, journal)
        output = deepcopy(committed["result"])
        output["idempotent"] = False
        output["transaction_ref"] = transaction_id
        output["transaction_status"] = "COMMITTED"
        return {"status": "COMMITTED", "result": output, "recovered": False, "action": "COMMITTED"}
    except Exception as exc:
        try:
            outcome = _reconcile_transaction(root, transaction_id, failure=exc)
        except Exception as recovery_error:
            raise ValidationFailure(
                "STAGE_TRANSACTION_RECOVERY_BLOCKED: transition failed and automatic reconciliation could not complete",
                {"transaction_id": transaction_id, "failure": str(exc), "recovery_error": str(recovery_error)},
            ) from recovery_error
        if outcome["status"] == "COMMITTED":
            output = deepcopy(outcome["journal"]["result"])
            output["idempotent"] = False
            output["transaction_ref"] = transaction_id
            output["transaction_status"] = "COMMITTED"
            output.setdefault("warnings", []).append(
                {
                    "code": "STAGE_TRANSACTION_COMMIT_RECOVERED",
                    "message": "The complete new write set was digest-verified and the missing/interrupted commit marker was recovered.",
                    "recovery_action": outcome["action"],
                }
            )
            return {"status": "COMMITTED", "result": output, "recovered": True, "action": outcome["action"]}
        # The old write set and ROLLED_BACK journal are now verified. Preserve the
        # original API error rather than reporting a false success.
        raise


def apply_stage_transaction(
    root: Path,
    writes: dict[Path, Any],
    *,
    transaction_id: str,
    operation_kind: str,
    request_digest: str,
    result: dict[str, Any],
    replace_canonical: CanonicalReplace | None = None,
) -> dict[str, Any]:
    """Serialize Stage mutation and recovery across native OS processes."""
    ensure_native_path(root, tree=True)
    with stage_project_lock(root):
        return _apply_stage_transaction_locked(
            root, writes, transaction_id=transaction_id,
            operation_kind=operation_kind, request_digest=request_digest,
            result=result, replace_canonical=replace_canonical,
        )


def _latest_writer_map(journals: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for journal in sorted(journals, key=lambda item: int(item["sequence"])):
        if journal["status"] == "COMMITTED":
            for entry in journal["entries"]:
                latest[str(entry["target"])] = {"journal": journal, "entry": entry, "terminal": "NEW"}
        elif journal["status"] == "ROLLED_BACK":
            for entry in journal["entries"]:
                latest[str(entry["target"])] = {"journal": journal, "entry": entry, "terminal": "OLD"}
    return latest


def _immutable_transaction_target(target: str) -> bool:
    """Return whether a transaction target must remain byte-identical.

    Mutable indexes and control-plane projections may receive a later governed
    revision. Immutable revision records, decisions, acceptance reports, and
    Stage history must never be rewritten in place. Keeping this policy narrow
    avoids treating ordinary later index advancement as transaction damage.
    """
    path = Path(target)
    if target.startswith(".harness/stages/") and target != ".harness/stages/STAGE_STATE.yaml":
        return not target.startswith(STAGE_TRANSACTION_ROOT.as_posix() + "/")
    if target.startswith(".harness/canonical/DECISIONS/"):
        return True
    if target.startswith((".harness/maintenance/PLANS/", ".harness/maintenance/REPORTS/")):
        return "@" in path.stem
    if target.startswith((".harness/tasks/", ".harness/work-packages/", ".harness/prompts/")):
        return "@" in path.stem
    return False


def _latest_committed_control_plane_errors(root: Path, journal: dict[str, Any]) -> list[str]:
    """Reconcile the current control-plane projection with a committed result.

    ``CURRENT_STATE`` and ``NEXT_TASK`` are mutable projections, so a permanent
    byte-for-byte digest pin would reject legitimate later Stage transactions.
    The latest completed transition nevertheless establishes exact semantic
    facts that must hold until another Stage transaction supersedes it.
    """
    errors: list[str] = []
    result = journal.get("result") or {}
    operation_kind = str(journal.get("operation_kind") or "")

    try:
        current_doc = load_data(root / ".harness/state/CURRENT_STATE.yaml")
        current = current_doc.get("state") if isinstance(current_doc, dict) else None
        if not isinstance(current, dict):
            raise ValidationFailure("CURRENT_STATE envelope is invalid")

        expected_fields = {
            "active_stage": result.get("active_stage"),
            "target_implementation_level": result.get("target_level"),
            "next_route": result.get("next_route"),
        }
        for field, expected in expected_fields.items():
            if expected is not None and current.get(field) != expected:
                errors.append(
                    f"{journal['id']}: CURRENT_STATE {field}={current.get(field)!r}, expected {expected!r}"
                )

        # accept-stage and level-up both end with no runnable task. Their saved
        # result is therefore sufficient to validate the mutable projection
        # without relying on the original CURRENT_STATE file digest.
        if operation_kind in {"ACCEPT_STAGE", "LEVEL_UP"}:
            if result.get("status") == "TARGET_LEVEL_REACHED":
                expected_project_status = "TARGET_LEVEL_REACHED"
            elif operation_kind == "ACCEPT_STAGE" and result.get("status") == "BLOCKED":
                expected_project_status = "BLOCKED"
            else:
                expected_project_status = "ACTIVE"
            if current.get("project_status") != expected_project_status:
                errors.append(
                    f"{journal['id']}: CURRENT_STATE project_status={current.get('project_status')!r}, "
                    f"expected {expected_project_status!r}"
                )
            for field in ("current_task_ref", "active_run"):
                if current.get(field) is not None:
                    errors.append(
                        f"{journal['id']}: CURRENT_STATE {field} must be null after {operation_kind}, "
                        f"observed {current.get(field)!r}"
                    )
    except Exception as exc:
        errors.append(f"{journal['id']}: CURRENT_STATE reconciliation failed: {exc}")

    try:
        next_doc = load_data(root / ".harness/state/NEXT_TASK.yaml")
        next_task = next_doc.get("next_task") if isinstance(next_doc, dict) else None
        if not isinstance(next_task, dict):
            raise ValidationFailure("NEXT_TASK envelope is invalid")

        expected_fields = {
            "active_stage": result.get("active_stage"),
            "next_route": result.get("next_route"),
        }
        for field, expected in expected_fields.items():
            observed = next_task.get(field)
            # Once the first JIT is reserved, NEXT_TASK uses the historical
            # implementation_stage field, not the pre-reservation active_stage.
            if field == "active_stage" and operation_kind == "PLAN_ACTIVE_STAGE" and observed is None:
                observed = next_task.get("implementation_stage")
            if expected is not None and observed != expected:
                errors.append(
                    f"{journal['id']}: NEXT_TASK {field}={observed!r}, expected {expected!r}"
                )
        if operation_kind in {"ACCEPT_STAGE", "LEVEL_UP"}:
            if operation_kind == "ACCEPT_STAGE" and result.get("status") == "BLOCKED":
                expected_next_status = "BLOCKED"
            else:
                expected_next_status = (
                    "TARGET_LEVEL_REACHED"
                    if result.get("next_route") == "TARGET_ALREADY_REACHED"
                    else "STAGE_PLANNING_REQUIRED"
                )
            if next_task.get("status") != expected_next_status:
                errors.append(
                    f"{journal['id']}: NEXT_TASK status={next_task.get('status')!r}, "
                    f"expected {expected_next_status!r}"
                )
            for field in ("task_ref", "run_ref"):
                if next_task.get(field) is not None:
                    errors.append(
                        f"{journal['id']}: NEXT_TASK {field} must be null after {operation_kind}, "
                        f"observed {next_task.get(field)!r}"
                    )
    except Exception as exc:
        errors.append(f"{journal['id']}: NEXT_TASK reconciliation failed: {exc}")

    acceptance_refs = result.get("acceptance_refs") or []
    if not isinstance(acceptance_refs, list):
        errors.append(f"{journal['id']}: saved result acceptance_refs is not an array")
        acceptance_refs = []
    entry_by_target = {str(entry["target"]): entry for entry in journal.get("entries") or []}
    for ref in acceptance_refs:
        reference = str(ref)
        target = f".harness/stages/ACCEPTANCE/{reference}.yaml"
        entry = entry_by_target.get(target)
        if entry is None:
            errors.append(f"{journal['id']}: acceptance_ref {reference!r} is absent from the committed write set")
            continue
        observed = _entry_state(root, entry)
        if observed["state"] != "NEW":
            errors.append(
                f"{journal['id']}:{target}: committed acceptance_ref is {observed['state']} "
                f"({observed.get('digest')}), expected NEW"
            )

    return errors


def validate_stage_transaction_journals(root: Path) -> dict[str, Any]:
    """Validate terminal journals and detect mixed current Stage canonical state."""
    root = root.expanduser().resolve()
    transaction_root = root / STAGE_TRANSACTION_ROOT
    if not transaction_root.exists():
        return {
            "status": "PASS",
            "transactions": 0,
            "committed": 0,
            "rolled_back": 0,
            "latest_completed_transition": None,
            "errors": [],
        }
    errors: list[str] = []
    journals: list[dict[str, Any]] = []
    for child in sorted(transaction_root.iterdir(), key=lambda path: path.name):
        if not child.is_dir():
            errors.append(f"{child.name}: unexpected non-directory entry")
            continue
        try:
            journal = _load_journal(root, child.name)
            _validate_journal_structure(root, child, journal)
            journals.append(journal)
        except Exception as exc:
            errors.append(f"{child.name}: {exc}")
    sequences = [int(item["sequence"]) for item in journals]
    if len(sequences) != len(set(sequences)):
        errors.append(f"duplicate transaction sequences: {sequences}")
    for journal in journals:
        if journal["status"] not in STAGE_TRANSACTION_TERMINAL_STATUSES:
            errors.append(f"{journal['id']}: unresolved status {journal['status']}")

    latest_writers = _latest_writer_map(journals)
    # Exact current digest checks cover immutable revision records, canonical
    # decisions, and Stage artifacts/indexes whose latest governed writer is
    # known from the journal sequence. Mutable cross-plane indexes and
    # control-plane projections are checked semantically below. STAGE_STATE
    # itself can receive a later maturity-assessment revision, so it is checked
    # by transition facts plus its immutable history revision.
    for target, info in sorted(latest_writers.items()):
        if not _immutable_transaction_target(target):
            continue
        entry = info["entry"]
        observed = _entry_state(root, entry)
        expected_state = info["terminal"]
        if observed["state"] != expected_state:
            errors.append(
                f"{info['journal']['id']}:{target}: expected terminal {expected_state}, observed {observed['state']} ({observed.get('digest')})"
            )

    committed = sorted(
        (journal for journal in journals if journal["status"] == "COMMITTED"),
        key=lambda item: int(item["sequence"]),
    )
    latest_committed = committed[-1] if committed else None
    if latest_committed is not None:
        try:
            stage_doc = load_data(root / ".harness/stages/STAGE_STATE.yaml")
            implementation = stage_doc.get("implementation") if isinstance(stage_doc, dict) else None
            if not isinstance(implementation, dict):
                raise ValidationFailure("Stage State envelope is invalid")
            result = latest_committed["result"]
            expected = {
                "target_level": result.get("target_level"),
                "active_stage": result.get("active_stage"),
                "highest_accepted_level": result.get("highest_accepted_level"),
            }
            for field, value in expected.items():
                if value is not None and implementation.get(field) != value:
                    errors.append(
                        f"{latest_committed['id']}: current Stage State {field}={implementation.get(field)!r}, expected {value!r}"
                    )
            state_entry = next(
                (entry for entry in latest_committed["entries"] if entry["target"] == ".harness/stages/STAGE_STATE.yaml"),
                None,
            )
            if state_entry is not None:
                staged_revision = None
                history_targets = [
                    entry for entry in latest_committed["entries"]
                    if str(entry["target"]).startswith(".harness/stages/STATE_HISTORY/STAGE_STATE@")
                ]
                for history_entry in history_targets:
                    history_path = _entry_target(root, history_entry)
                    if history_path.is_file() and _digest_file(history_path) == history_entry["expected_new_digest"]:
                        try:
                            history_doc = load_data(history_path)
                            staged_revision = int((history_doc.get("implementation") or {}).get("revision"))
                        except Exception:
                            pass
                if staged_revision is not None and int(implementation.get("revision", 0)) < staged_revision:
                    errors.append(
                        f"{latest_committed['id']}: current Stage State revision {implementation.get('revision')} precedes committed revision {staged_revision}"
                    )
            errors.extend(_latest_committed_control_plane_errors(root, latest_committed))
        except Exception as exc:
            errors.append(f"latest committed transition reconciliation: {exc}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "transactions": len(journals),
        "committed": sum(1 for item in journals if item["status"] == "COMMITTED"),
        "rolled_back": sum(1 for item in journals if item["status"] == "ROLLED_BACK"),
        "latest_completed_transition": latest_committed["id"] if latest_committed else None,
        "errors": errors,
    }
