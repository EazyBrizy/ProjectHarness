"""Check and test the exact final ZIP bytes, without modifying the packaged trees."""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / '_deliverables/PH_LW_04_05_WINDOWS_RETEST_2026-11-07'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--hash-name', default='PH_LW_04_05_WINDOWS_ACCEPTANCE_SHA256.txt')
    parser.add_argument('--manual-migration', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    destination = ROOT / '_scratch' / ('final-extracted-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    destination.mkdir()
    reports = output / 'FINAL_VERIFICATION'
    reports.mkdir(exist_ok=True)
    artifacts = []
    hashes = (output / args.hash_name).read_text('utf-8').splitlines()
    for line in hashes:
        expected, name = line.split('  ', 1)
        path = output / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        with zipfile.ZipFile(path) as zf:
            assert zf.testzip() is None
            for info in zf.infolist():
                parts = PurePosixPath(info.filename).parts
                assert not info.filename.startswith('/') and '..' not in parts and '\\' not in info.filename
                assert not set(parts).intersection({'_scratch', '_tools', '.venv', '__pycache__', 'windows_ci_logs'})
                assert not info.filename.endswith('.pyc')
                assert (info.external_attr >> 16) & 0o170000 != 0o120000
                target = destination.joinpath(*parts)
                assert target.resolve().is_relative_to(destination.resolve())
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(info))
                original = ROOT.joinpath(*parts)
                assert original.read_bytes() == target.read_bytes(), info.filename
            artifacts.append({'file': name, 'sha256': expected, 'files': len(zf.namelist()), 'crc_exact_tree': 'PASS'})
    manifests = []
    for manifest in destination.rglob('MANIFEST.sha256'):
        rows = {}
        for line in manifest.read_text('utf-8').splitlines():
            digest, relative = line.split('  ', 1)
            target = manifest.parent / relative
            assert target.resolve().is_relative_to(manifest.parent.resolve())
            assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, relative
            rows[relative] = digest
        actual = {p.relative_to(manifest.parent).as_posix() for p in manifest.parent.rglob('*')
                  if p.is_file() and p != manifest}
        assert set(rows) == actual
        manifests.append({'file': manifest.relative_to(destination).as_posix(), 'verified': len(rows)})
    engine = destination / 'Project_Harness_Engine_v0.5.1'
    command = ['powershell.exe', '-NoProfile', '-File', str(engine / 'local_web/ci_ph_lw_05_windows.ps1'),
               '-PythonExecutable', sys.executable, '-DocumentationZip',
               str(output / 'Project_Harness_Documentation_v0.5.1_PH_LW_05.zip'),
               '-LogDirectory', str(reports / 'extracted_ci05'), '-SkipRegressions']
    with (reports / 'extracted_ci05.log').open('wb') as stream:
        result = subprocess.run(command, cwd=engine, stdout=stream, stderr=subprocess.STDOUT, timeout=600,
                                env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1',
                                     'PYTHONPATH': os.pathsep.join((str(engine / 'src'), str(engine)))})
    report = {'status': 'PASS' if result.returncode == 0 else 'FAIL', 'archives': artifacts,
              'manifests': manifests, 'extracted_ci_command': command, 'exit': result.returncode,
              'extraction': str(destination), 'scope': 'exact final ZIP pair; 44 stage tests plus doctor/docs; full regressions reported separately'}
    if args.manual_migration:
        manual_command = [sys.executable, '-m', 'unittest', '-v',
                          'tests.test_windows_manual_migration',
                          'tests.test_ph_051_10_migration_recovery.V051MigrationTests']
        with (reports / 'extracted_manual.log').open('wb') as stream:
            manual = subprocess.run(manual_command, cwd=engine, stdout=stream, stderr=subprocess.STDOUT,
                                    timeout=600, env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1',
                                                     'PYTHONPATH': os.pathsep.join((str(engine / 'src'), str(engine)))})
        report['manual_migration'] = {'command': manual_command, 'exit': manual.returncode}
        if manual.returncode != 0:
            report['status'] = 'FAIL'
    (reports / 'FINAL_ARCHIVE_VERIFICATION.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
