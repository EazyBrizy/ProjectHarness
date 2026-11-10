"""Run from a separate Unicode CWD and venv, importing only the installed wheel."""
from __future__ import annotations
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import unittest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--manual-migration', action='store_true', help='Include manual migration/recovery suite')
    parser.add_argument('--ph-lw-06', action='store_true', help='Include PH-LW-06 exchange and real Edge/TCP acceptance')
    parser.add_argument('--ph-lw-07', action='store_true', help='Include PH-LW-07 approval/recovery and real Edge/TCP acceptance')
    parser.add_argument('--ph-lw-08', action='store_true', help='Include PH-LW-08 native publication/recovery and Edge/TCP acceptance')
    parser.add_argument('--ph-lw-09', action='store_true', help='Include PH-LW-09 Task/Run/result/verification and Edge/TCP acceptance')
    parser.add_argument('--ph-lw-10', action='store_true', help='Include PH-LW-10 Stage/planning/maintenance/migration and real Edge/TCP')
    parser.add_argument('--ph-lw-11', action='store_true', help='Include PH-LW-11 native desktop/installer helper tests')
    parser.add_argument('--case', action='append', help='Explicit focused recheck after a recorded full run; preserves installed-build/launcher checks')
    args = parser.parse_args()
    import project_harness
    module = Path(project_harness.__file__).resolve()
    assert module.is_relative_to(Path(sys.prefix).resolve()), module
    assert not module.is_relative_to(args.engine.resolve()), module
    assert 'src' not in (os.environ.get('PYTHONPATH') or '')
    installed_metadata = json.loads((module.parent/'resources/local_web/metadata_v1.json').read_text('utf-8'))
    expected_metadata = json.loads((args.engine/'src/project_harness/resources/local_web/metadata_v1.json').read_text('utf-8'))
    assert installed_metadata == expected_metadata, 'Installed package build metadata differs from requested source build'
    print(json.dumps({'package': str(module), 'interpreter': sys.executable,
                      'cwd': str(Path.cwd()), 'source_import': False,
                      'engine_build_digest':installed_metadata['engine_build_digest']}), flush=True)
    console = Path(sys.executable).with_name('project-harness.exe')
    for command in ([str(console), 'doctor'], [str(console), 'ui', '--help']):
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        print(result.stdout, flush=True)
        assert result.returncode == 0, result.stderr
    # Start the actual installed console launcher; no bootstrap credential is exposed.
    child = subprocess.Popen([str(console), 'ui', '--no-browser', '--app-data', str(Path.cwd() / 'launcher-data')],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines = queue.Queue()
    def read_lines():
        for line in child.stdout:
            lines.put(line)
    threading.Thread(target=read_lines, daemon=True).start()
    try:
        first = lines.get(timeout=25)
        match = re.search(r'http://127\.0\.0\.1:(\d+)/', first)
        assert match and 'bootstrap' not in first, first
        connection = http.client.HTTPConnection('127.0.0.1', int(match[1]), timeout=10)
        connection.request('GET', '/health')
        response = connection.getresponse()
        assert response.status == 200 and json.loads(response.read()) == {'status': 'ok'}
        connection.close()
        print('Installed console launcher: loopback health PASS; direct access without local login', flush=True)
    finally:
        subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True, timeout=15)
        child.wait(timeout=15)
    # Add only the test package directory, never engine/src.
    sys.path.insert(0, str(args.engine.resolve()))
    modules = ['tests.test_ph_lw_05_import', 'tests.test_ph_lw_05_http', 'tests.test_ph_lw_04_05_acceptance']
    if args.manual_migration:
        modules += ['tests.test_windows_manual_migration', 'tests.test_ph_051_10_migration_recovery.V051MigrationTests']
    if args.ph_lw_06:
        modules += ['tests.test_ph_lw_06_exchange', 'tests.test_ph_lw_06_http']
    if args.ph_lw_07:
        modules += ['tests.test_ph_lw_07_approvals', 'tests.test_ph_lw_07_http']
    if args.ph_lw_08:
        modules += ['tests.test_ph_lw_08_preparation', 'tests.test_ph_lw_08_http']
    if args.ph_lw_09:
        modules += ['tests.test_ph_lw_09_tasks', 'tests.test_ph_lw_09_http', 'tests.test_ph_lw_09_manual_evidence']
    if args.ph_lw_10:
        modules += ['tests.test_ph_lw_10_lifecycle', 'tests.test_ph_lw_10_http']
    if args.ph_lw_11:
        modules += ['tests.test_ph_lw_11_desktop']
    if args.case:
        assert all(name.startswith('tests.test_') for name in args.case)
        modules = args.case
    suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert not result.skipped, result.skipped
    print(json.dumps({'ran': result.testsRun, 'errors': len(result.errors),
                      'failures': len(result.failures), 'skips': len(result.skipped),
                      'installed_package': str(module)}, ensure_ascii=False), flush=True)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())

