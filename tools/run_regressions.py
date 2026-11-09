"""Bounded per-module regression evidence; no skipped-test promotion to PASS."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', type=Path, default=ROOT / 'Project_Harness_Engine_v0.5.1')
    parser.add_argument('--python', type=Path, default=ROOT / '.venv/Scripts/python.exe')
    parser.add_argument('--output', type=Path, default=ROOT / '_scratch/regressions')
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('modules', nargs='*')
    args = parser.parse_args()
    engine, output = args.engine.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    names = args.modules or ['tests.' + p.stem for p in sorted((engine / 'tests').glob('test_*.py'))]
    env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1',
           'PH_LW_04_BROWSER_CHANNEL': 'msedge', 'PYTHONPATH': os.pathsep.join((str(engine / 'src'), str(engine)))}
    # Python passes argv directly, avoiding Windows PowerShell's -c quote loss.
    code = ('import sys; from pathlib import Path; '
            'from local_web.run_windows_acceptance import run_suite; '
            'r=run_suite([sys.argv[1]],Path(sys.argv[2]),reject_skips=False); '
            'raise SystemExit(0 if r["status"]=="PASS" else 1)')
    def run(name):
        log = output / (name.removeprefix('tests.') + '.log')
        command = [str(args.python.resolve()), '-c', code, name, str(log)]
        start = time.monotonic()
        row = {'module': name, 'command': command, 'started_utc': datetime.now(timezone.utc).isoformat()}
        try:
            result = subprocess.run(command, cwd=engine, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=args.timeout)
            row.update(exit=result.returncode, status='PASS' if result.returncode == 0 else 'FAIL')
            log.with_suffix('.process.log').write_bytes(result.stdout)
            result_path = log.with_suffix('.json')
            if result_path.exists():
                row.update(json.loads(result_path.read_text('utf-8')))
            if row['status'] == 'PASS' and row.get('skips'):
                row['status'] = 'PASS_WITH_SKIPS'
        except subprocess.TimeoutExpired as exc:
            row.update(exit=None, status='TIMEOUT')
            log.with_suffix('.process.log').write_bytes(exc.stdout or b'')
        row['elapsed_seconds'] = round(time.monotonic()-start, 3)
        if log.exists():
            row['log_sha256'] = hashlib.sha256(log.read_bytes()).hexdigest()
        return row
    rows = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for future in as_completed([pool.submit(run, name) for name in names]):
            row = future.result()
            rows.append(row)
            (output / 'MATRIX.json').write_text(json.dumps(sorted(rows, key=lambda r: r['module']), ensure_ascii=False, indent=2) + '\n', 'utf-8')
            print(f'{row["module"]}: {row["status"]}, ran={row.get("ran", "?")}, skips={len(row.get("skips", []))}, {row["elapsed_seconds"]}s', flush=True)
    raise SystemExit(0 if all(r['status'] in {'PASS', 'PASS_WITH_SKIPS'} for r in rows) else 1)


if __name__ == '__main__':
    main()
