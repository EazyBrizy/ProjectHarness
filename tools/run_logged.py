"""Run a bounded command with separate UTF-8 log and machine-readable evidence."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', required=True, type=Path)
    parser.add_argument('--cwd', type=Path, default=Path.cwd())
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    args.log.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    info = {'command': command, 'cwd': str(args.cwd.resolve()),
            'started_utc': datetime.now(timezone.utc).isoformat(),
            'platform': platform.platform(), 'timeout_seconds': args.timeout}
    with args.log.open('wb') as output:
        child = subprocess.Popen(command, cwd=args.cwd, stdout=output, stderr=subprocess.STDOUT,
                                 env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
        try:
            code = child.wait(timeout=args.timeout)
            info.update(exit_code=code, status='PASS' if code == 0 else 'FAIL')
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            else:
                child.terminate()
            child.wait(timeout=15)
            info.update(exit_code=None, status='TIMEOUT')
    info.update(elapsed_seconds=round(time.monotonic()-start, 3),
                log_sha256=hashlib.sha256(args.log.read_bytes()).hexdigest())
    args.log.with_suffix('.run.json').write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print(args.log.read_text('utf-8', errors='replace')[-8000:])
    raise SystemExit(0 if info['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
