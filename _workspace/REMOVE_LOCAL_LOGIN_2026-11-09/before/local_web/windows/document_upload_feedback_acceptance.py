"""Real installed EXE recheck of the document UI, using isolated fixtures."""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import acceptance
from project_harness.windows_package import verify_bundle
import tests.test_document_upload_feedback as feedback

class IsolatedFrozenServer(acceptance.FrozenServer):
    def __init__(self,directory):
        acceptance.OPTIONS.runtime_root=Path(directory)
        super().__init__()

def main():
    p=argparse.ArgumentParser();p.add_argument('--installer',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);options=p.parse_args()
    if sys.platform!='win32' or sys.getwindowsversion().build<22000 or ctypes.windll.shell32.IsUserAnAdmin():
        raise RuntimeError('Native non-admin Windows 11 required')
    options.output=options.output.resolve();options.output.mkdir(parents=True,exist_ok=False)
    options.installer=options.installer.resolve();options.install_dir=options.output/'Установленная программа'
    acceptance.OPTIONS=options
    report={'installer_sha256':hashlib.sha256(options.installer.read_bytes()).hexdigest(),'non_admin':True,
            'browser':'headless Edge, real TCP, actual installed EXE with sanitized PATH',
            'validation_timing_test':'NOT RUN against EXE; timing latch test belongs to source/wheel only'}
    shortcut_paths=[Path(os.environ['USERPROFILE'])/'Desktop/Project Harness.lnk',
        Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/Project Harness.lnk']
    saved_shortcuts={path:path.read_bytes() if path.exists() else None for path in shortcut_paths}
    try:
        command=[str(options.installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',
                 '/DIR='+str(options.install_dir),'/LOG='+str(options.output/'install.log')]
        installed=subprocess.run(command,timeout=180);report['install']={'command':command,'exit':installed.returncode}
        if installed.returncode:
            raise RuntimeError('Fixture install failed')
        options.build_id=json.loads((options.install_dir/'current.json').read_text('utf-8'))['build_id']
        verify_bundle(options.install_dir/'versions'/options.build_id)
        feedback.LiveServer=IsolatedFrozenServer
        os.environ['DOCUMENT_UPLOAD_SCREENSHOTS']=str(options.output/'screenshots')
        names=[name for name in unittest.defaultTestLoader.getTestCaseNames(feedback.DocumentUploadFeedbackTests)
               if name!='test_transfer_finished_is_still_validation_not_success']
        suite=unittest.TestSuite(feedback.DocumentUploadFeedbackTests(name) for name in names)
        with (options.output/'browser.log').open('w',encoding='utf-8') as stream:
            result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        report['tests']={'ran':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped)}
        report['build_id']=options.build_id
        uninstall=next((options.install_dir/'uninstall').glob('unins*.exe'))
        removed=subprocess.run([str(uninstall),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',
            '/LOG='+str(options.output/'uninstall.log')],timeout=120)
        report['uninstall_exit']=removed.returncode
        report['status']='PASS' if result.wasSuccessful() and not result.skipped and removed.returncode==0 else 'FAIL'
    finally:
        for path,data in saved_shortcuts.items():
            if data is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(data)
        report['operator_shortcuts_preserved']=True
        (options.output/'RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report.get('status')!='PASS'

if __name__=='__main__':
    raise SystemExit(main())
