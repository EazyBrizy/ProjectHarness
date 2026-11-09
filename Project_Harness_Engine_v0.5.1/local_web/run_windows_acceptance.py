"""Native PH-LW-04/05 runner: exact dependencies, real browser, explicit skips."""
from __future__ import annotations
import argparse
import ctypes
from datetime import datetime, timezone
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


def run_suite(names, output, *, reject_skips):
    started = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    with output.open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    row = {'modules': names, 'ran': result.testsRun, 'failures': len(result.failures),
           'errors': len(result.errors), 'skips': [{'test': t.id(), 'reason': why} for t, why in result.skipped],
           'elapsed_seconds': round(time.monotonic() - started, 3), 'log': output.name}
    row['status'] = 'PASS' if result.wasSuccessful() and not (reject_skips and result.skipped) else 'FAIL'
    output.with_suffix('.json').write_text(json.dumps(row, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps(row, ensure_ascii=False), flush=True)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('04', '05', '06', '07', '08', '09', '10'), required=True)
    parser.add_argument('--documentation-zip', type=Path)
    parser.add_argument('--log-dir', type=Path, required=True)
    parser.add_argument('--skip-regressions', action='store_true',
                        help='Record NOT RUN here; run the full regression matrix separately.')
    args = parser.parse_args()
    args.log_dir = args.log_dir.resolve()
    if args.documentation_zip is not None:
        args.documentation_zip = args.documentation_zip.resolve(strict=True)
    args.log_dir.mkdir(parents=True, exist_ok=True)
    report = {'stage': 'PH-LW-' + args.stage, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
              'checks': [], 'status': 'FAIL', 'installer': 'NOT RUN (PH-LW-11)',
              'automatic_executor': 'NO-GO / NOT RUN'}
    try:
        if sys.platform != 'win32' or sys.getwindowsversion().build < 22000 or platform.machine() != 'AMD64':
            raise RuntimeError('Native Windows 11 x64 required')
        if sys.version_info[:2] != (3, 14):
            raise RuntimeError('Python 3.14 x64 required for cp314 wheel inventory')
        if ctypes.windll.shell32.IsUserAnAdmin():
            raise RuntimeError('Acceptance must run as a non-admin user')
        fsname = ctypes.create_unicode_buffer(64)
        if not ctypes.windll.kernel32.GetVolumeInformationW(str(ROOT.anchor), None, 0, None, None, None, fsname, 64):
            raise ctypes.WinError()
        if fsname.value != 'NTFS':
            raise RuntimeError('Local NTFS required')
        report['filesystem'] = fsname.value
        report['dependencies'] = {name: version(name) for name in ('flask', 'waitress', 'playwright')}
        if version('flask') != '3.1.3' or version('waitress') != '3.0.2':
            raise RuntimeError('Exact Flask/Waitress pins required')
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            report['browser'] = browser.version
            browser.close()
        os.environ['PH_LW_04_BROWSER_CHANNEL'] = 'msedge'
        os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
        os.environ['PYTHONUTF8'] = '1'
        os.environ['PYTHONPATH'] = os.pathsep.join((str(ROOT / 'src'), str(ROOT)))
        sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
        modules = ['tests.test_ph_lw_04_http']
        if args.stage in ('05', '06', '07', '08', '09', '10'):
            modules += ['tests.test_ph_lw_05_import', 'tests.test_ph_lw_05_http',
                        'tests.test_ph_lw_04_05_acceptance']
        if args.stage in ('06', '07', '08', '09', '10'):
            modules += ['tests.test_ph_lw_06_exchange', 'tests.test_ph_lw_06_http']
        if args.stage in ('07', '08', '09', '10'):
            modules += ['tests.test_ph_lw_07_approvals', 'tests.test_ph_lw_07_http']
        if args.stage in ('08', '09', '10'):
            modules += ['tests.test_ph_lw_08_preparation', 'tests.test_ph_lw_08_http']
        if args.stage in ('09', '10'):
            modules += ['tests.test_ph_lw_09_tasks', 'tests.test_ph_lw_09_http', 'tests.test_ph_lw_09_manual_evidence']
        if args.stage == '10':
            modules += ['tests.test_ph_lw_10_lifecycle', 'tests.test_ph_lw_10_http']
        report['checks'].append(run_suite(modules, args.log_dir / 'stage_tests.log', reject_skips=True))
        if args.skip_regressions:
            report['regressions'] = 'NOT RUN in this invocation; separate evidence required'
        else:
            modules = ['tests.' + p.stem for p in sorted((ROOT / 'tests').glob('test_*.py'))
                       if 'tests.' + p.stem not in modules]
            report['checks'].append(run_suite(modules, args.log_dir / 'regressions.log', reject_skips=False))
        for name, command in (
            ('doctor', [sys.executable, 'project-harness.py', 'doctor']),
            ('documentation', [sys.executable, 'docs/Project_Harness_Documentation_v0.5.1/tools/validate_documentation.py',
                               'docs/Project_Harness_Documentation_v0.5.1',
                               *(['--zip', str(args.documentation_zip)] if args.documentation_zip else []),
                               '--json', str(args.log_dir / 'DOC_VALIDATION.json')])):
            with (args.log_dir / (name + '.log')).open('wb') as stream:
                result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
            report['checks'].append({'name': name, 'command': command, 'exit': result.returncode,
                                     'status': 'PASS' if result.returncode == 0 else 'FAIL'})
        report['status'] = 'PASS' if all(row['status'] == 'PASS' for row in report['checks']) else 'FAIL'
    except Exception as exc:
        report['error'] = str(exc)
    finally:
        path = args.log_dir / ('PH_LW_' + args.stage + '_WINDOWS_TEST_REPORT.json')
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

