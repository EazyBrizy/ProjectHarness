"""Native installed EXE tests; isolated fixture roots, never a clean-VM claim.

Developer Playwright/Python drive the tests. The installed process receives a
Windows-only PATH, empty PYTHONPATH and independent Unicode CWD/profile paths.
"""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import time
import types
import unittest

ENGINE=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ENGINE/'src'),str(ENGINE)]
from project_harness.local_web_instance import connect_existing
from project_harness.windows_package import verify_bundle
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_ph_lw_03_service import byte_snapshot

OPTIONS = None

def harness_app_snapshot(runtime_root):
    # Default browser owns its separate profile/cache and can hold lockfiles.
    # Uninstall retention contract concerns precisely Harness-owned app data.
    return {name:byte_snapshot(runtime_root/'LocalAppData'/name)
            for name in ('ProjectHarness','ProjectHarness-workspaces')}


class FrozenServer(LiveServer):
    def __init__(self, _directory=None):
        self.base=OPTIONS.runtime_root or OPTIONS.output
        self.base.mkdir(parents=True,exist_ok=True)
        profile=self.base/'Профиль с пробелами';profile.mkdir(exist_ok=True)
        local=self.base/'LocalAppData';local.mkdir(exist_ok=True)
        self.app_data=local/'ProjectHarness'
        self.service=types.SimpleNamespace(projects_directory=profile/'HarnessProjects')
        self.env={**os.environ,'LOCALAPPDATA':str(local),'USERPROFILE':str(profile),
                  'PATH':str(Path(os.environ['SystemRoot'])/'System32'),'PYTHONPATH':'',
                  'PROJECT_HARNESS_HOME':'','PYTHONDONTWRITEBYTECODE':'1'}
        self.cwd=self.base/'Другая рабочая папка';self.cwd.mkdir(exist_ok=True)
        self.executable=OPTIONS.install_dir/'versions'/OPTIONS.build_id/'Harness.exe'
        self.process=subprocess.Popen([str(self.executable),'--no-browser'],cwd=self.cwd,env=self.env,
                                      stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(120):
            if self.process.poll() is not None:raise RuntimeError('Frozen process exited: '+str(self.process.returncode))
            try:
                url=connect_existing(self.app_data);break
            except (OSError,ValueError,Exception):time.sleep(.1)
        else:raise RuntimeError('Frozen process did not become ready')
        self.origin=url.split('/#')[0];self.port=int(self.origin.rsplit(':',1)[1]);self.cookie=self.csrf=None
        self.auth=types.SimpleNamespace(issue_bootstrap=lambda:connect_existing(self.app_data).split('=')[1])
        print('Frozen server ready; PID',self.process.pid,'PATH has no developer tools',flush=True)

    def close(self):
        if self.process.poll() is None:
            self.login()
            code,_,_=self.request('POST','/api/desktop/stop',value={})
            if code != 200:raise AssertionError('Clean stop refused: '+str(code))
            self.process.wait(timeout=30)
            if self.process.returncode!=0:raise AssertionError('Frozen clean stop failed')
        if (self.app_data/'launcher-private.json').exists():raise AssertionError('Instance record not removed')


class InstalledLifecycleTests(unittest.TestCase):
    def test_crash_recovery_retains_project_and_replaces_stale_record(self):
        live=FrozenServer();before=byte_snapshot(live.service.projects_directory)
        record=(live.app_data/'launcher-private.json').read_bytes()
        live.process.kill();live.process.wait(timeout=15) # this test's own idle child only
        self.assertEqual(record,(live.app_data/'launcher-private.json').read_bytes())
        live=FrozenServer()
        try:
            self.assertNotEqual(record,(live.app_data/'launcher-private.json').read_bytes())
            self.assertEqual(before,byte_snapshot(live.service.projects_directory))
        finally:live.close()

    def test_restart_resume_second_launch_collision_and_clean_stop(self):
        from playwright.sync_api import sync_playwright,expect
        live=FrozenServer()
        try:
            live.login();projects=live.request('GET','/api/projects')[2]['projects'];self.assertTrue(projects)
            before=byte_snapshot(live.service.projects_directory)
            selected=next(p['project_id'] for p in projects if p['kind']=='project')
            resume=live.request('GET','/api/ui/resume')[2]
            self.assertEqual(live.request('POST','/api/ui/resume',value={'project_id':selected,'screen':'tasks','expected_revision':resume['revision']})[0],200)
            pid=live.process.pid
            setup=subprocess.run([str(OPTIONS.installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',
                '/DIR='+str(OPTIONS.install_dir),'/LOG='+str(OPTIONS.output/'setup-while-running.log')],timeout=30)
            self.assertNotEqual(setup.returncode,0);self.assertIsNone(live.process.poll())
            # Real second Harness.exe opens default browser and exits, keeping
            # the first process and exact catalog. No fixture/private API edits.
            second=subprocess.run([str(live.executable)],cwd=live.cwd,env=live.env,timeout=30)
            self.assertEqual(second.returncode,0);self.assertIsNone(live.process.poll())
            self.assertEqual(pid,live.process.pid);self.assertEqual(projects,live.request('GET','/api/projects')[2]['projects'])
            old_port=live.port;live.close()
            collision=socket.socket();collision.bind(('127.0.0.1',old_port));collision.listen()
            try:
                live=FrozenServer();self.assertNotEqual(live.port,old_port)
                with sync_playwright() as p:
                    browser=p.chromium.launch(channel='msedge',headless=True)
                    try:
                        page=browser.new_page();page.goto(live.origin+'/#bootstrap='+live.auth.issue_bootstrap())
                        expect(page.locator('#session-state')).to_have_text('Сессия активна')
                        expect(page.locator('#screen-title')).to_have_text('Задачи и Run')
                        expect(page.locator('#task-prompt')).not_to_have_value('',timeout=30000)
                        page.screenshot(path=str(OPTIONS.output/'restart-resume.png'))
                        page.on('dialog',lambda d:d.accept());page.locator('#stop-harness').click()
                        expect(page.locator('#notice')).to_contain_text('Harness завершает работу')
                        live.process.wait(timeout=30);self.assertEqual(live.process.returncode,0)
                    finally:browser.close()
                self.assertEqual(before,byte_snapshot(live.service.projects_directory))
                self.assertTrue(collision.fileno()>=0)
            finally:collision.close()
        finally:live.close()

    def test_package_doctor_and_not_an_interpreter(self):
        exe=OPTIONS.install_dir/'versions'/OPTIONS.build_id/'Harness.exe'
        for args,code in [(['--check-package'],0),(['--doctor'],0),(['-c','raise SystemExit(0)'],1)]:
            result=subprocess.run([str(exe),*args],cwd=OPTIONS.output,timeout=30)
            self.assertEqual(result.returncode,code,args)


def main():
    global OPTIONS
    parser=argparse.ArgumentParser();parser.add_argument('--installer',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--runtime-root',type=Path,help='Independent fixture app/profile root; keep each run new')
    OPTIONS=parser.parse_args();OPTIONS.installer=OPTIONS.installer.resolve();OPTIONS.output=OPTIONS.output.resolve()
    if OPTIONS.runtime_root:
        OPTIONS.runtime_root=OPTIONS.runtime_root.resolve()
        if OPTIONS.runtime_root.exists():raise RuntimeError('Use a new runtime root')
    OPTIONS.output.mkdir(parents=True,exist_ok=False)
    if sys.platform!='win32' or sys.getwindowsversion().build<22000 or ctypes.windll.shell32.IsUserAnAdmin():
        raise RuntimeError('Native non-admin Windows 11 required')
    OPTIONS.install_dir=OPTIONS.output/'Установленная программа'
    report={'platform':platform.platform(),'python':sys.version,'non_admin':True,
            'installer_sha256':hashlib.sha256(OPTIONS.installer.read_bytes()).hexdigest(),
            'clean_machine':'NOT RUN; developer host with sanitized installed-process PATH',
            'physical_offline':'NOT RUN; no adapter/security setting changes',
            'unicode_username':'NOT RUN; actual username unchanged; Unicode paths tested',
            'real_disk_full':'NOT RUN; ENOSPC injection tested separately', 'commands':[]}
    fsname=ctypes.create_unicode_buffer(64)
    if not ctypes.windll.kernel32.GetVolumeInformationW(str(OPTIONS.output.anchor),None,0,None,None,None,fsname,64):raise ctypes.WinError()
    report['filesystem']=fsname.value
    if fsname.value!='NTFS':raise RuntimeError('NTFS required')
    foreign=OPTIONS.output/'Чужой продукт';foreign.mkdir();(foreign/'sentinel').write_bytes(b'preserve')
    rejected=subprocess.run([str(OPTIONS.installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',
        '/DIR='+str(foreign),'/LOG='+str(OPTIONS.output/'foreign-target.log')],timeout=120)
    if rejected.returncode==0 or list(foreign.iterdir())!=[foreign/'sentinel'] or (foreign/'sentinel').read_bytes()!=b'preserve':
        raise AssertionError('Foreign product protection failed')
    report['foreign_target_rejection']={'exit':rejected.returncode,'sentinel_preserved':True}
    command=[str(OPTIONS.installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',
             '/DIR='+str(OPTIONS.install_dir),'/LOG='+str(OPTIONS.output/'install.log')]
    result=subprocess.run(command,timeout=120);report['commands'].append({'command':command,'exit':result.returncode})
    if result.returncode:raise RuntimeError('Installer failed: '+str(result.returncode))
    OPTIONS.build_id=json.loads((OPTIONS.install_dir/'current.json').read_text())['build_id']
    verify_bundle(OPTIONS.install_dir/'versions'/OPTIONS.build_id)
    # Same public browser scenario as PH-LW-08, against installed EXE. The only
    # adapter differences are startup and the frozen default project directory.
    import inspect
    import tests.test_ph_lw_08_http as previous
    source=inspect.getsource(previous.PreparationBrowserTests)
    source=source[source.index('class PreparationBrowserTests'):]
    source=source.replace('class PreparationBrowserTests','class FrozenPreparationBrowserTests')
    source=source.replace("            live.service.projects_directory=Path(directory)/'Готовые проекты'\n",'')
    scope=dict(vars(previous));scope['LiveServer']=FrozenServer
    exec(compile(source,'<inherited PH-LW-08 browser scenario against installed EXE>','exec'),scope)
    os.environ['PH_LW_08_SCREENSHOT_DIR']=str(OPTIONS.output/'screenshots')
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(scope['FrozenPreparationBrowserTests']),
                            unittest.defaultTestLoader.loadTestsFromTestCase(InstalledLifecycleTests)])
    with (OPTIONS.output/'browser.log').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    report['tests']={'ran':result.testsRun,'errors':len(result.errors),'failures':len(result.failures),'skips':len(result.skipped)}
    # Retention tested by actual Inno uninstall; only fixture installations.
    runtime_root=OPTIONS.runtime_root or OPTIONS.output
    retained=byte_snapshot(runtime_root/'Профиль с пробелами')
    app_retained=harness_app_snapshot(runtime_root)
    uninstall=next((OPTIONS.install_dir/'uninstall').glob('unins*.exe'))
    command=[str(uninstall),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/LOG='+str(OPTIONS.output/'uninstall.log')]
    removed=subprocess.run(command,timeout=120);report['commands'].append({'command':command,'exit':removed.returncode})
    report['uninstall_preserved_projects']=retained==byte_snapshot(runtime_root/'Профиль с пробелами')
    report['uninstall_preserved_app_data']=app_retained==harness_app_snapshot(runtime_root)
    report['executable_removed']=not (OPTIONS.install_dir/'versions'/OPTIONS.build_id/'Harness.exe').exists()
    report['status']='PASS' if result.wasSuccessful() and not result.skipped and removed.returncode==0 and all(
        report[k] for k in ['uninstall_preserved_projects','uninstall_preserved_app_data','executable_removed']) else 'FAIL'
    (OPTIONS.output/'RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
