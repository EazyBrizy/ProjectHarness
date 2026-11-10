"""Local source launcher: reuse the workspace venv, no install or rebuild.

This is a development entry point, not an accepted frozen release. It calls
the same public loopback launcher and preserves the per-user instance lock.
"""
from __future__ import annotations
import argparse
import ctypes
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'Project_Harness_Engine_v0.5.1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Read-only environment and package check; no listener/browser')
    parser.add_argument('--no-browser', action='store_true', help='Headless diagnostics; no visible browser')
    parser.add_argument('--app-data', type=Path, help='Trusted local diagnostic app-data directory')
    args = parser.parse_args()
    if os.name != 'nt' or sys.version_info[:2] != (3, 14):
        raise RuntimeError('Requires the existing native Windows Python 3.14 workspace venv')
    if Path(sys.prefix).resolve() != (ROOT/'.venv').resolve():
        raise RuntimeError('Run with this workspace .venv/Scripts/python.exe or pythonw.exe')
    source = ENGINE/'src'
    if not (source/'project_harness/local_web_launcher.py').is_file():
        raise RuntimeError('Workspace source directory not found')
    # Source selection is explicit; a host resource override must not silently
    # substitute another distribution. This changes only our child process.
    os.environ.pop('PROJECT_HARNESS_HOME', None)
    sys.path.insert(0, str(source))
    import project_harness
    from project_harness.local_web_launcher import run_local_web
    from project_harness.validation import doctor
    package = Path(project_harness.__file__).resolve().parent
    if package != source/'project_harness':
        raise RuntimeError('Unexpected project_harness import location')
    dependencies = {name:version(name) for name in ('Flask','Waitress')}
    if dependencies != {'Flask':'3.1.3','Waitress':'3.0.2'}:
        raise RuntimeError('Pinned web dependencies differ; no automatic installation is performed')
    if args.check:
        result=doctor()
        payload={'status':result['status'],'mode':'SOURCE_DEVELOPMENT','python':sys.version,
            'interpreter':sys.executable,'source_package':str(package),'dependencies':dependencies,
            'listener_started':False,'browser_opened':False,'release_acceptance':'NOT CLAIMED'}
        if sys.stdout:
            print(json.dumps(payload,ensure_ascii=False,indent=2))
        return 0 if result['status']=='PASS' else 1
    return run_local_web(app_data=args.app_data, open_browser=not args.no_browser)


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception:
        # pythonw has no console. Never disclose raw exception details or
        # launcher credentials in a dialog/log.
        message=('Не удалось запустить Harness из исходников. Возможно, уже работает другой экземпляр '
                 'или недоступна среда разработки. Завершите работающий Harness его штатной кнопкой. '
                 'Для диагностики выполните .venv\\Scripts\\python.exe -B tools\\launch_harness_dev.py --check '
                 'из папки ProjectHarness.')
        if sys.stderr:
            print(message,file=sys.stderr)
        elif '--no-browser' not in sys.argv and '--check' not in sys.argv:
            ctypes.windll.user32.MessageBoxW(None,message,'Project Harness — разработка',0x10)
        raise SystemExit(1)
