"""PH-LW-05: bounded, inert Markdown source snapshots for the local manual UI.

Upload streams and ZIP entries are untrusted bytes.  This module never calls a
repository command, extracts a ZIP with extractall(), or follows a supplied
path.  The source ledger is outside the provisional intake workspace.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import stat
import unicodedata
from uuid import uuid4
import zipfile
from typing import BinaryIO, Iterable, Any

from .errors import SafetyViolation, ValidationFailure
from .hashing import sha256_file
from .platform_fs import ensure_native_path, safe_relative, _native_io_path
from .serialization import load_data, write_data, canonical_json_bytes
from .util import utc_now

HTTP_BODY_MAX = 64 * 1024 * 1024
ENTRY_MAX = 8 * 1024 * 1024
EXTRACTED_MAX = 128 * 1024 * 1024
ENTRY_COUNT_MAX = 1000
DEPTH_MAX = 16
RATIO_MAX = 200
CHUNK = 64 * 1024
MAX_UPLOADS = 100
_SNAPSHOT_REF = re.compile(r'^LWS-[A-F0-9]{32}$')
_SOURCE_REF = re.compile(r'^LSD-[A-F0-9]{24}$')
_MD_REF = re.compile(r'^LMD-[A-F0-9]{24}$')


def _private_directory(path: Path) -> Path:
    ensure_native_path(path, tree=True)
    if _native_io_path(path).is_symlink() or (_native_io_path(path).exists() and (not _native_io_path(path).is_dir() or
            bool(getattr(_native_io_path(path), 'is_junction', lambda: False)()))):
        raise SafetyViolation('UNSAFE_IMPORT_DIRECTORY')
    _native_io_path(path).mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != 'nt' and _native_io_path(path).stat().st_mode & 0o077:
        raise SafetyViolation('IMPORT_DIRECTORY_NOT_PRIVATE')
    return path


def _filename(raw: str) -> str:
    if not isinstance(raw, str) or not raw or len(raw.encode('utf-8', 'surrogatepass')) > 512:
        raise ValidationFailure('SOURCE_FILENAME_INVALID')
    if '/' in raw or '\\' in raw or raw in {'.', '..'}:
        raise SafetyViolation('UNSAFE_UPLOAD_FILENAME')
    _member(raw)
    return raw


def _member(raw: str) -> tuple[str, ...]:
    """Check every name as a portable Windows path *before* writing any part."""
    if not isinstance(raw, str) or not raw or '\\' in raw or '\x00' in raw:
        raise SafetyViolation('ZIP_UNSAFE_PATH')
    if len(raw.encode('utf-8', 'surrogatepass')) > 4096:
        raise SafetyViolation('ZIP_PATH_TOO_LONG')
    path = raw[:-1] if raw.endswith('/') else raw
    if not path or path.startswith('/') or path.endswith('/'):
        raise SafetyViolation('ZIP_UNSAFE_PATH')
    parts = path.split('/')
    if len(parts) > DEPTH_MAX:
        raise ValidationFailure('ZIP_DEPTH_LIMIT')
    if any(p in {'', '.', '..'} or any(unicodedata.category(ch) in {'Cc', 'Cf', 'Cs'} for ch in p)
           for p in parts):
        raise SafetyViolation('ZIP_UNSAFE_PATH')
    for part in parts:
        # NFKC can turn compatibility characters into device names or ADS syntax.
        canonical = unicodedata.normalize('NFKC', part)
        safe_relative(canonical, field='ZIP member', windows=True)
        safe_relative(part, field='ZIP member', windows=True)
        if part in {'', '.', '..'} or canonical in {'', '.', '..'}:
            raise SafetyViolation('ZIP_UNSAFE_PATH')
    safe_relative(path, field='ZIP member', windows=True)
    return tuple(parts)


def _fold(path: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(unicodedata.normalize('NFKC', c).casefold() for c in path)


def _document_allowed(parts: tuple[str, ...]) -> tuple[bool, str]:
    if any(p.casefold() == '.harness' for p in parts) or parts[-1].casefold() == 'agents.md':
        return False, 'CONTROL_NAME_NOT_IMPORTED'
    if parts[-1].casefold().endswith('.zip'):
        raise ValidationFailure('NESTED_ZIP_UNSUPPORTED')
    if not parts[-1].casefold().endswith('.md'):
        return False, 'UNSUPPORTED_ATTACHMENT_ONLY_MD'
    return True, ''


def _validate_utf8(path: Path) -> None:
    # Decoding whole <=8MiB entry is bounded, and BOM is explicitly supported.
    raw = _native_io_path(path).read_bytes()
    try:
        raw.decode('utf-8-sig', errors='strict')
    except UnicodeError as exc:
        raise ValidationFailure('MARKDOWN_ENCODING_UNSUPPORTED: expected UTF-8 or UTF-8 BOM') from exc


def _stream_to_file(stream: BinaryIO, target: Path, *, budget: int) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(_native_io_path(target), flags, 0o600)
    try:
        with os.fdopen(fd, 'wb') as output:
            while True:
                chunk = stream.read(min(CHUNK, budget - count + 1))
                if not chunk:
                    break
                if not isinstance(chunk, bytes):
                    raise ValidationFailure('UPLOAD_STREAM_NOT_BINARY')
                count += len(chunk)
                if count > budget:
                    raise ValidationFailure('UPLOAD_BODY_LIMIT')
                output.write(chunk)
                digest.update(chunk)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        _native_io_path(target).unlink(missing_ok=True)
        raise
    return count, 'sha256:' + digest.hexdigest()


def _extract_md_zip(raw_path: Path, destination: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    accepted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    extracted = 0
    _private_directory(destination)
    try:
        with zipfile.ZipFile(_native_io_path(raw_path), 'r') as zf:
            infos = zf.infolist()
            # Python's ZipInfo truncates embedded NUL in an archive name.
            # Inspect the original local-header filename bytes too, including
            # directory entries that would not be opened for CRC validation.
            with _native_io_path(raw_path).open('rb') as raw_file:
                for member_info in infos:
                    raw_file.seek(member_info.header_offset)
                    local = raw_file.read(30)
                    if len(local) != 30 or local[:4] != b'PK\x03\x04':
                        raise ValidationFailure('ZIP_LOCAL_HEADER_INVALID')
                    name_len = int.from_bytes(local[26:28], 'little')
                    filename_bytes = raw_file.read(name_len)
                    if len(filename_bytes) != name_len or b'\0' in filename_bytes:
                        raise SafetyViolation('ZIP_NUL_OR_INCONSISTENT_NAME')
                    try:
                        decoded = filename_bytes.decode('utf-8' if member_info.flag_bits & 0x800 else 'cp437')
                    except UnicodeError as exc:
                        raise ValidationFailure('ZIP_FILENAME_ENCODING_INVALID') from exc
                    if decoded != member_info.filename:
                        raise SafetyViolation('ZIP_LOCAL_CENTRAL_NAME_MISMATCH')
                    if int.from_bytes(local[6:8], 'little') != member_info.flag_bits:
                        raise SafetyViolation('ZIP_LOCAL_CENTRAL_FLAGS_MISMATCH')
            if not infos or len(infos) > ENTRY_COUNT_MAX:
                raise ValidationFailure('ZIP_ENTRY_COUNT_LIMIT')
            # Check whole central directory, parent aliases and file/dir clashes
            # before materializing even the first Markdown file.
            components: dict[tuple[str, ...], str] = {}
            indexed: dict[tuple[str, ...], bool] = {}
            rows: list[tuple[zipfile.ZipInfo, tuple[str, ...], bool, str]] = []
            total_expected = 0
            for info in infos:
                parts = _member(info.filename)
                key = _fold(parts)
                for depth, component in enumerate(parts):
                    prefix = key[:depth+1]
                    old = components.setdefault(prefix, component)
                    if old != component:
                        raise SafetyViolation('ZIP_UNICODE_OR_CASE_COLLISION')
                if key in indexed:
                    raise SafetyViolation('ZIP_DUPLICATE_PATH')
                indexed[key] = info.is_dir()
                if info.flag_bits & 1:
                    raise ValidationFailure('ZIP_ENCRYPTION_UNSUPPORTED')
                if info.is_dir() and (info.file_size != 0 or info.compress_size != 0):
                    raise SafetyViolation('ZIP_DIRECTORY_WITH_PAYLOAD')
                if info.file_size < 0 or info.file_size > ENTRY_MAX:
                    raise ValidationFailure('ZIP_ENTRY_SIZE_LIMIT')
                # The DOS reparse-point flag has no safe import interpretation.
                if info.external_attr & (0x400 << 16):
                    raise SafetyViolation('ZIP_REPARSE_OR_SPECIAL_FILE')
                mode = (info.external_attr >> 16) & 0xFFFF
                kind = stat.S_IFMT(mode)
                if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise SafetyViolation('ZIP_LINK_OR_SPECIAL_FILE')
                if (kind == stat.S_IFDIR and not info.is_dir()) or (kind == stat.S_IFREG and info.is_dir()):
                    raise SafetyViolation('ZIP_TYPE_MISMATCH')
                if not info.is_dir():
                    if info.compress_size == 0 and info.file_size:
                        raise ValidationFailure('ZIP_COMPRESSION_RATIO_LIMIT')
                    if info.compress_size and info.file_size > info.compress_size * RATIO_MAX:
                        raise ValidationFailure('ZIP_COMPRESSION_RATIO_LIMIT')
                    total_expected += info.file_size
                    if total_expected > EXTRACTED_MAX:
                        raise ValidationFailure('ZIP_EXTRACTED_BYTES_LIMIT')
                    allowed, reason = _document_allowed(parts)
                else:
                    allowed, reason = False, 'DIRECTORY'
                rows.append((info, parts, allowed, reason))
            for info, parts, _allow, _reason in rows:
                for length in range(1, len(parts)):
                    if indexed.get(_fold(parts[:length])) is False:
                        raise SafetyViolation('ZIP_FILE_AS_PARENT')
            for info, parts, allowed, reason in rows:
                if info.is_dir():
                    continue
                relative = '/'.join(parts)
                target = destination.joinpath(*parts)
                target_path: Path | None = None
                if allowed:
                    _native_io_path(target.parent).mkdir(parents=True, mode=0o700, exist_ok=True)
                    # Only private dirs created by this operation. Never follow symlinks.
                    if any(_native_io_path(p).is_symlink() or bool(getattr(_native_io_path(p), 'is_junction', lambda: False)())
                           for p in (target.parent, *target.parent.parents) if p == destination or destination in p.parents):
                        raise SafetyViolation('ZIP_DESTINATION_LINK')
                    target_path = target
                count, digest = 0, hashlib.sha256()
                try:
                    with zf.open(info, 'r') as stream:
                        output_fd = None
                        if target_path is not None:
                            output_fd = os.open(_native_io_path(target_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                                                getattr(os, 'O_NOFOLLOW', 0), 0o600)
                        try:
                            if output_fd is not None:
                                output = os.fdopen(output_fd, 'wb')
                                output_fd = None
                            else:
                                output = None
                            try:
                                while True:
                                    chunk = stream.read(CHUNK)
                                    if not chunk:
                                        break
                                    count += len(chunk)
                                    extracted += len(chunk)
                                    if count > ENTRY_MAX or extracted > EXTRACTED_MAX or count > info.file_size:
                                        raise ValidationFailure('ZIP_EXTRACTED_BYTES_LIMIT')
                                    digest.update(chunk)
                                    if output:
                                        output.write(chunk)
                                if output:
                                    output.flush(); os.fsync(output.fileno())
                            finally:
                                if output:
                                    output.close()
                        finally:
                            if output_fd is not None:
                                os.close(output_fd)
                except (RuntimeError, NotImplementedError, zipfile.BadZipFile, EOFError, OSError) as exc:
                    raise ValidationFailure('ZIP_CRC_OR_COMPRESSION_INVALID') from exc
                if count != info.file_size:
                    raise ValidationFailure('ZIP_SIZE_MISMATCH')
                if allowed:
                    _validate_utf8(target)
                    accepted.append({'relative_path': relative, 'byte_size': count,
                                     'sha256': 'sha256:' + digest.hexdigest(), 'encoding': 'UTF-8/BOM',
                                     'archive_entry': info.filename, 'compression': info.compress_type,
                                     'crc32': f'{info.CRC:08x}'})
                else:
                    skipped.append({'relative_path': relative, 'reason': reason})
    except (zipfile.BadZipFile, zipfile.LargeZipFile, UnicodeError) as exc:
        raise ValidationFailure('ZIP_INVALID_OR_CRC_FAILED') from exc
    return accepted, skipped, extracted


def _safe_upload_name(name: str) -> str:
    return _filename(name)


def _active_state(imports_root: Path) -> dict[str, Any]:
    target = imports_root / 'state.json'
    ensure_native_path(target, file_ok=True)
    if _native_io_path(target).is_symlink():
        raise SafetyViolation('SOURCE_LEDGER_SYMLINK')
    if not _native_io_path(target).exists():
        return {'version': 1, 'revision': 0, 'active_snapshot': None,
                'snapshot_digest': None, 'documentation_choice': 'UNANSWERED'}
    record = load_data(target)
    if (not isinstance(record, dict) or record.get('version') != 1
            or type(record.get('revision')) is not int or record['revision'] < 0
            or record.get('documentation_choice') not in ('UNANSWERED', 'PROVIDED', 'NONE')
            or (record.get('active_snapshot') is not None and not _SNAPSHOT_REF.fullmatch(str(record['active_snapshot'])))):
        raise ValidationFailure('SOURCE_LEDGER_INVALID')
    return record


def _snapshot(imports_root: Path, snapshot_ref: str) -> dict[str, Any]:
    if not isinstance(snapshot_ref, str) or not _SNAPSHOT_REF.fullmatch(snapshot_ref):
        raise ValidationFailure('INVALID_SOURCE_SNAPSHOT_REF')
    directory = imports_root / 'snapshots' / snapshot_ref
    # Read-only Windows preflight includes ancestors above the snapshot base.
    # No mkdir/recovery from inventory or preview GETs.
    ensure_native_path(directory, tree=True)
    manifest_path = directory / 'manifest.json'
    if _native_io_path(directory).is_symlink() or _native_io_path(manifest_path).is_symlink() or not _native_io_path(manifest_path).is_file():
        raise ValidationFailure('SOURCE_SNAPSHOT_NOT_FOUND')
    record = load_data(manifest_path)
    if (not isinstance(record, dict) or record.get('snapshot_ref') != snapshot_ref
            or type(record.get('revision')) is not int or record['revision'] < 1
            or not isinstance(record.get('sources'), list) or not isinstance(record.get('documents'), list)):
        raise ValidationFailure('SOURCE_SNAPSHOT_INVALID')
    digest = hashlib.sha256(canonical_json_bytes(record)).hexdigest()
    return {'directory': directory, 'record': record, 'digest': 'sha256:' + digest}


def _file_checked(base: Path, relative: str, expected: str, *, budget: int = ENTRY_MAX) -> Path:
    parts = _member(relative)
    candidate = base.joinpath(*parts)
    ensure_native_path(candidate, file_ok=True)
    if any(_native_io_path(p).is_symlink() or bool(getattr(_native_io_path(p), 'is_junction', lambda: False)())
           for p in [candidate, *candidate.parents] if p == base or base in p.parents):
        raise SafetyViolation('SOURCE_SNAPSHOT_LINK')
    if not _native_io_path(candidate).is_file():
        raise ValidationFailure('SOURCE_SNAPSHOT_FILE_MISSING')
    info = _native_io_path(candidate).stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > budget:
        raise SafetyViolation('SOURCE_SNAPSHOT_FILE_UNSAFE')
    if 'sha256:' + sha256_file(candidate) != expected:
        raise ValidationFailure('SOURCE_SNAPSHOT_DIGEST_MISMATCH')
    return candidate



def copy_verified_document(base: Path, relative: str, expected: str, destination: Path) -> None:
    """Open canonical source with O_NOFOLLOW on Unix, digest as actually copied.

    On native Windows, the existing PH-LW-02 reparse-aware path preflight is
    used; OS-level no-follow is not certified without a Windows NTFS test.
    This never reads another filesystem path from archive contents.
    """
    path = _file_checked(base, relative, expected)
    if _native_io_path(destination).is_symlink() or _native_io_path(destination).exists():
        raise SafetyViolation('SOURCE_DESTINATION_MUST_BE_NEW')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    # Keep the ordinary short-path open contract (including fault injection).
    # Only the long Windows spelling requires the private Win32 namespace.
    open_path = _native_io_path(path) if os.name == 'nt' and len(str(path.absolute())) >= 248 else path
    fd = os.open(open_path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > ENTRY_MAX:
            raise SafetyViolation('SOURCE_OPENED_FILE_UNSAFE')
        digest = hashlib.sha256()
        count = 0
        outfd = os.open(_native_io_path(destination), os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                        getattr(os, 'O_NOFOLLOW', 0), 0o600)
        try:
            with os.fdopen(outfd, 'wb') as output, os.fdopen(fd, 'rb') as stream:
                fd = -1
                while True:
                    chunk = stream.read(CHUNK)
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > ENTRY_MAX or count > info.st_size:
                        raise ValidationFailure('SOURCE_COPIED_BYTES_LIMIT')
                    digest.update(chunk)
                    output.write(chunk)
                output.flush(); os.fsync(output.fileno())
        except BaseException:
            _native_io_path(destination).unlink(missing_ok=True)
            raise
        if count != info.st_size or 'sha256:' + digest.hexdigest() != expected:
            _native_io_path(destination).unlink(missing_ok=True)
            raise ValidationFailure('SOURCE_SNAPSHOT_CHANGED_DURING_COPY')
    finally:
        if fd != -1:
            os.close(fd)

def verify_snapshot(imports_root: Path, snapshot_ref: str) -> dict[str, Any]:
    snapshot = _snapshot(imports_root, snapshot_ref)
    record = snapshot['record']; base = snapshot['directory']
    for doc in record['documents']:
        _file_checked(base, doc['storage_relative_path'], doc['sha256'])
    for source in record['sources']:
        _file_checked(base, source['raw_storage_path'], source['sha256'],
                      budget=HTTP_BODY_MAX if source['format'] == 'ZIP' else ENTRY_MAX)
    return snapshot


def build_snapshot(imports_root: Path, uploads: Iterable[tuple[str, BinaryIO]], *,
                   mode: str, expected_revision: int) -> dict[str, Any]:
    """Complete validation before immutable publication; no intake mutation.

    mode=append retains the exact previous source revision; replace discards it.
    Caller holds the shared intake guard while checking expected revision.
    """
    if mode not in ('append', 'replace') or type(expected_revision) is not int:
        raise ValidationFailure('SOURCE_IMPORT_REQUEST_INVALID')
    imports_root = _private_directory(Path(imports_root))
    state = _active_state(imports_root)
    if state['revision'] != expected_revision:
        raise ValidationFailure('STALE_SOURCE_REVISION')
    upload_list = list(uploads)
    if not upload_list or len(upload_list) > MAX_UPLOADS:
        raise ValidationFailure('UPLOAD_COUNT_LIMIT')
    old_sources = []; old_docs = []
    previous = None
    if mode == 'append' and state['active_snapshot']:
        previous = verify_snapshot(imports_root, state['active_snapshot'])
        old_sources = previous['record']['sources']
        old_docs = previous['record']['documents']
    pending_root = _private_directory(imports_root / 'quarantine')
    staging = _private_directory(pending_root / ('upload-' + uuid4().hex))
    _private_directory(staging / 'raw')
    _private_directory(staging / 'materialized')
    all_sources = deepcopy(old_sources)
    all_docs = deepcopy(old_docs)
    accepted = []; skipped = []
    total_uploaded = 0
    total_extracted = 0
    source_keys = {(item['original_name'], item['sha256']) for item in old_sources}
    seen_original: dict[str, str] = {unicodedata.normalize('NFKC', item['original_name']).casefold(): item['original_name']
                                     for item in old_sources} if mode == 'append' else {}
    try:
        if previous is not None:
            for old in old_sources:
                source = _file_checked(previous['directory'], old['raw_storage_path'], old['sha256'],
                                       budget=HTTP_BODY_MAX if old['format'] == 'ZIP' else ENTRY_MAX)
                target = staging / old['raw_storage_path']
                _native_io_path(target.parent).mkdir(parents=True, exist_ok=True)
                shutil.copyfile(_native_io_path(source), _native_io_path(target))
            for doc in old_docs:
                source = _file_checked(previous['directory'], doc['storage_relative_path'], doc['sha256'])
                target = staging / doc['storage_relative_path']
                _native_io_path(target.parent).mkdir(parents=True, exist_ok=True)
                shutil.copyfile(_native_io_path(source), _native_io_path(target))
        for original, stream in upload_list:
            name = _safe_upload_name(original)
            normalized = unicodedata.normalize('NFKC', name).casefold()
            if normalized in seen_original and seen_original[normalized] != name:
                raise SafetyViolation('UPLOAD_NAME_COLLISION')
            if normalized in seen_original and seen_original[normalized] == name and any(
                    unicodedata.normalize('NFKC', old['original_name']).casefold() == normalized
                    for old in old_sources):
                # A byte-identical replay is allowed after the digest check.
                pass
            elif normalized in seen_original:
                raise SafetyViolation('UPLOAD_NAME_COLLISION')
            seen_original[normalized] = name
            extension = Path(name).suffix.casefold()
            if extension not in ('.md', '.zip'):
                skipped.append({'original_name': name, 'reason': 'UNSUPPORTED_UPLOAD_ONLY_MD_ZIP'})
                continue
            temp = staging / 'raw' / ('upload-' + uuid4().hex + extension)
            remaining = HTTP_BODY_MAX - total_uploaded
            size, digest = _stream_to_file(stream, temp, budget=min(remaining, HTTP_BODY_MAX))
            total_uploaded += size
            if size > HTTP_BODY_MAX or total_uploaded > HTTP_BODY_MAX:
                raise ValidationFailure('UPLOAD_BODY_LIMIT')
            if (name, digest) in source_keys:
                _native_io_path(temp).unlink()
                skipped.append({'original_name': name, 'reason': 'IDENTICAL_SOURCE_ALREADY_PRESENT'})
                continue
            if any(item['original_name'] == name and item['sha256'] != digest for item in all_sources):
                raise ValidationFailure('SOURCE_NAME_CHANGED_USE_REPLACE')
            source_ref = 'LSD-' + uuid4().hex[:24].upper()
            raw_rel = 'raw/' + source_ref + extension
            _native_io_path(temp).rename(_native_io_path(staging / raw_rel))
            if extension == '.md':
                if size > ENTRY_MAX:
                    raise ValidationFailure('MARKDOWN_ENTRY_SIZE_LIMIT')
                _validate_utf8(staging / raw_rel)
                material_rel = 'materialized/' + source_ref + '.md'
                shutil.copyfile(_native_io_path(staging / raw_rel), _native_io_path(staging / material_rel))
                docs = [{'relative_path': name, 'byte_size': size, 'sha256': digest,
                         'encoding': 'UTF-8/BOM', 'archive_entry': None, 'compression': None, 'crc32': None}]
                total_extracted += size
            else:
                material_rel = 'materialized/' + source_ref
                docs, nested_skipped, extracted = _extract_md_zip(staging / raw_rel, staging / material_rel)
                total_extracted += extracted
                for rejected in nested_skipped:
                    skipped.append({'original_name': name, **rejected})
            if total_extracted > EXTRACTED_MAX:
                raise ValidationFailure('EXTRACTED_TOTAL_LIMIT')
            if not docs:
                raise ValidationFailure('ZIP_NO_SUPPORTED_MARKDOWN')
            source_keys.add((name, digest))
            source = {'source_ref': source_ref, 'original_name': name, 'safe_storage_name': source_ref,
                      'raw_storage_path': raw_rel, 'materialized_path': material_rel,
                      'byte_size': size, 'sha256': digest, 'format': extension[1:].upper(),
                      'import_revision': state['revision'] + 1}
            all_sources.append(source)
            for doc in docs:
                path = material_rel + (('/' + doc['relative_path']) if extension == '.zip' else '')
                metadata = {'document_ref': 'LMD-' + uuid4().hex[:24].upper(), 'source_ref': source_ref,
                            'original_name': name, 'storage_relative_path': path,
                            'source_relative_path': doc['relative_path'], 'byte_size': doc['byte_size'],
                            'sha256': doc['sha256'], 'import_revision': state['revision'] + 1,
                            'extraction_provenance': {'archive_ref': source_ref if extension == '.zip' else None,
                                       'archive_entry': doc['archive_entry'], 'compression': doc['compression'],
                                       'crc32': doc['crc32']}, 'encoding': doc['encoding']}
                all_docs.append(metadata)
                accepted.append({'document_ref': metadata['document_ref'], 'original_name': name,
                                 'relative_path': metadata['source_relative_path'], 'byte_size': metadata['byte_size']})
        if not all_docs:
            raise ValidationFailure('NO_SUPPORTED_DOCUMENTS')
        if len(all_docs) > ENTRY_COUNT_MAX or sum(d['byte_size'] for d in all_docs) > EXTRACTED_MAX:
            raise ValidationFailure('SOURCE_SET_BUDGET_LIMIT')
        if mode == 'replace' and state['active_snapshot']:
            prior = verify_snapshot(imports_root, state['active_snapshot'])['record']
            old_signature = sorted((s['original_name'], s['sha256']) for s in prior['sources'])
            new_signature = sorted((s['original_name'], s['sha256']) for s in all_sources)
            if old_signature == new_signature:
                return {'unchanged': True, 'snapshot_ref': state['active_snapshot'],
                        'revision': state['revision'], 'accepted': [], 'skipped': skipped,
                        'documents': prior['documents'], 'sources': prior['sources']}
        if mode == 'append' and not accepted:
            return {'unchanged': True, 'snapshot_ref': state['active_snapshot'],
                    'revision': state['revision'], 'accepted': [], 'skipped': skipped,
                    'documents': old_docs, 'sources': old_sources}
        snapshot_ref = 'LWS-' + uuid4().hex.upper()
        record = {'snapshot_ref': snapshot_ref, 'revision': state['revision'] + 1,
                  'created_at': utc_now(), 'sources': all_sources, 'documents': all_docs,
                  'skipped': skipped, 'status': 'IMPORTED_NOT_ANALYZED', 'trust': 'UNTRUSTED_PROJECT_DATA'}
        write_data(staging / 'manifest.json', record)
        destination = _private_directory(imports_root / 'snapshots') / snapshot_ref
        os.replace(_native_io_path(staging), _native_io_path(destination))
        return {'unchanged': False, 'snapshot_ref': snapshot_ref, 'revision': record['revision'],
                'accepted': accepted, 'skipped': skipped, 'documents': all_docs,
                'sources': all_sources, 'snapshot_digest': 'sha256:' + hashlib.sha256(canonical_json_bytes(record)).hexdigest()}
    finally:
        if _native_io_path(staging).exists():
            shutil.rmtree(_native_io_path(staging))


def sources_for_intake(imports_root: Path, snapshot_ref: str) -> list[Path]:
    current = verify_snapshot(imports_root, snapshot_ref)
    base = current['directory']
    rows = []
    for item in current['record']['sources']:
        target = base / item['materialized_path']
        if _native_io_path(target).is_symlink() or not _native_io_path(target).exists() or bool(getattr(_native_io_path(target), 'is_junction', lambda: False)()):
            raise SafetyViolation('SOURCE_SNAPSHOT_PATH_UNSAFE')
        rows.append(target)
    return rows


def source_state(imports_root: Path) -> dict[str, Any]:
    """Read-only metadata, not a semantic-analysis decision."""
    state = _active_state(imports_root)
    if state['active_snapshot']:
        current = verify_snapshot(imports_root, state['active_snapshot'])
        if current['digest'] != state['snapshot_digest']:
            raise ValidationFailure('SOURCE_LEDGER_DIGEST_MISMATCH')
        state = {**state, 'sources': current['record']['sources'],
                 'documents': current['record']['documents'], 'skipped': current['record']['skipped']}
    else:
        state = {**state, 'sources': [], 'documents': [], 'skipped': []}
    return state


def read_preview(imports_root: Path, doc_ref: str) -> dict[str, Any]:
    if not isinstance(doc_ref, str) or not _MD_REF.fullmatch(doc_ref):
        raise ValidationFailure('DOCUMENT_REF_INVALID')
    state = source_state(imports_root)
    doc = next((x for x in state['documents'] if x['document_ref'] == doc_ref), None)
    if doc is None:
        raise ValidationFailure('DOCUMENT_NOT_FOUND')
    full = _file_checked(imports_root / 'snapshots' / state['active_snapshot'],
                         doc['storage_relative_path'], doc['sha256'])
    with _native_io_path(full).open('rb') as file:
        content = file.read(32 * 1024)
    try:
        preview = content.decode('utf-8-sig', 'strict')
    except UnicodeDecodeError:
        # Truncation at a UTF-8 multi-byte character is expected and harmless.
        preview = content.decode('utf-8-sig', 'ignore')
    return {'document_ref': doc_ref, 'relative_path': doc['source_relative_path'],
            'preview_text': preview[:16_384], 'truncated': doc['byte_size'] > len(content),
            'rendering': 'ESCAPED_PLAIN_TEXT', 'analysis_status': 'NOT_ANALYZED'}
