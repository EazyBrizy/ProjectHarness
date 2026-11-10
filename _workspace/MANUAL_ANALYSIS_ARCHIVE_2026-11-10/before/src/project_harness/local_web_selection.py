"""Explicit native folder selection: no HTTP path/command/file-browser API."""
from __future__ import annotations
from pathlib import Path
import os
import ctypes
import subprocess
from .errors import ValidationFailure
from .operation_guard import project_operation_guard
from .platform_fs import ensure_native_path
from .serialization import load_data, write_data


def choose_directory() -> Path | None:
    if os.name != 'nt': raise ValidationFailure('Native folder selection requires Windows')
    # Fixed UI invocation. No request value is interpolated as shell code.
    script = """Add-Type -AssemblyName System.Windows.Forms
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = 'Project Harness: select an existing repository or Harness project'
$dialog.ShowNewFolderButton = $false
try { if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { [Console]::Write($dialog.SelectedPath) } } finally { $dialog.Dispose() }
"""
    system = ctypes.create_unicode_buffer(32768)
    size = ctypes.windll.kernel32.GetSystemDirectoryW(system, len(system))
    if not size or size >= len(system): raise ValidationFailure('Windows system directory unavailable')
    powershell = Path(system.value) / 'WindowsPowerShell/v1.0/powershell.exe'
    result = subprocess.run([str(powershell), '-NoProfile', '-STA', '-Command', script],
        capture_output=True, timeout=180, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode or len(result.stdout) > 32768: raise ValidationFailure('Native folder selection failed')
    value = result.stdout.decode('utf-8-sig').strip()
    return Path(value) if value else None


def select(service, *, purpose, project_name, mode, idempotency_key, picker=None):
    if not isinstance(purpose, str) or not isinstance(mode, str) or purpose not in {'repository', 'project'} or mode not in {'BROWNFIELD', 'HYBRID'}:
        raise ValidationFailure('Selection purpose/mode invalid')
    if (not isinstance(project_name, str) or not project_name.strip() or len(project_name) > 120
            or any(ord(c) < 32 or c in '/\\' for c in project_name)):
        raise ValidationFailure('Project name required (up to 120 characters)')
    from .local_web_service import _KEY
    if not isinstance(idempotency_key, str) or not _KEY.fullmatch(idempotency_key): raise ValidationFailure('Selection key invalid')
    digest = service._hash({'purpose': purpose, 'name': project_name, 'mode': mode, 'key': idempotency_key})
    base = service.app_data / 'selections'; base.mkdir(exist_ok=True, mode=0o700)
    path = base / (service._hash(idempotency_key).split(':')[1] + '.json')
    with project_operation_guard(base):
        ensure_native_path(base, tree=True)
        if path.exists():
            record = load_data(path)
            if record['digest'] != digest: raise ValidationFailure('OPERATION_CONFLICT: selection key changed')
            if record['state'] != 'COMMITTED': raise ValidationFailure('Selection interrupted; inspect the existing intake before a new selection')
            return record['result']
        if len(list(base.glob('*.json'))) >= 1000: raise ValidationFailure('Selection receipt limit reached')
        selected = (picker or choose_directory)()
        if selected is None: return {'status': 'CANCELLED'}
        ensure_native_path(selected, tree=True)
        root = selected.resolve(strict=True)
        if not root.is_dir() or root == service.app_data or service.app_data in root.parents or root in service.app_data.parents:
            raise ValidationFailure('Selected directory must be separate from app data')
        record = {'digest': digest, 'state': 'PREPARED'}; write_data(path, record)
        if purpose == 'project':
            from .lifecycle_forms import migration_preview
            preview = migration_preview(root)
            if not preview['supported']: raise ValidationFailure('Unsupported project; no repair performed', preview['validation'])
            current = preview['source_engine'] == preview['target_engine'] and preview['source_schema'] == preview['target_schema']
            pid = service.register_existing(root, kind='project' if current else 'migration')
        else:
            if (root / '.harness').exists(): raise ValidationFailure('Select this Harness instance with Open project; a repository intake cannot overwrite it')
            from .intake import start_intake
            from .local_web_imports import _private_directory
            managed = _private_directory(service.app_data.parent / (service.app_data.name + '-workspaces'))
            session = _private_directory(managed / ('session-' + path.stem[:24].upper()))
            _private_directory(session / 'imports')
            workspace = session / 'intake'
            if workspace.exists(): raise ValidationFailure('Incomplete selection requires explicit inspection; no overwrite')
            start_intake(workspace, project_name=project_name.strip(), mode=mode, sources=[], repository=root)
            pid = service.register_existing(workspace, kind='workspace')
        result = {'status': 'SELECTED', 'project_id': pid, 'purpose': purpose}
        record.update(state='COMMITTED', result=result); write_data(path, record)
        return result
