"""Run unchanged installed-EXE assertions with full long-path fixture snapshots."""
import hashlib
import argparse
import json
import inspect
import textwrap
from pathlib import Path
import winreg
import sys
import acceptance

def setting():
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Control\FileSystem') as key:
        return winreg.QueryValueEx(key,'LongPathsEnabled')[0]

def snapshot(root):
    # Test-only IO adaptation. Do not drop any deep files from the assertion.
    io=Path('\\\\?\\'+str(root.absolute()))
    return {p.relative_to(io).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in io.rglob('*') if p.is_file()}

if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--app-data-root',type=Path)
    fixture_args,remaining=parser.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    app_fixture=fixture_args.app_data_root.resolve() if fixture_args.app_data_root else None
    if app_fixture and app_fixture.exists():raise RuntimeError('Use a new app-data fixture root')
    acceptance.APP_DATA_FIXTURE=app_fixture
    before=setting()
    # This regression concerns long project/profile paths. Keep independent
    # app-data in the short fixture output; do not add an unrelated long
    # intake storage requirement to the inherited publication scenario.
    source=textwrap.dedent(inspect.getsource(acceptance.FrozenServer.__init__))
    old="local=self.base/'LocalAppData';local.mkdir(exist_ok=True)"
    assert source.count(old)==1
    source=source.replace(old,"local=APP_DATA_FIXTURE or OPTIONS.output/'LocalAppData';local.mkdir(exist_ok=True)")
    exec(compile(source,'<long profile; separate fixture app-data>','exec'),vars(acceptance))
    acceptance.FrozenServer.__init__=vars(acceptance)['__init__']
    acceptance.byte_snapshot=snapshot
    acceptance.harness_app_snapshot=lambda _root:{name:snapshot((app_fixture or acceptance.OPTIONS.output/'LocalAppData')/name)
        for name in ('ProjectHarness','ProjectHarness-workspaces')}
    import tests.test_ph_lw_08_http as previous
    previous.byte_snapshot=snapshot
    code=acceptance.main()
    options=acceptance.OPTIONS
    report_path=options.output/'RESULT.json';report=json.loads(report_path.read_text('utf-8'))
    root=(options.runtime_root or options.output)/'Профиль с пробелами'/'HarnessProjects'
    retained=snapshot(root)
    maximum=max((len(str(root/name)) for name in retained),default=0)
    after=setting()
    report['long_path']={'maximum_retained_project_file_path_length':maximum,
        'retained_file_count':len(retained),'long_paths_enabled_before':before,
        'long_paths_enabled_after':after,'system_settings_changed':False,
        'app_data_fixture':str(app_fixture or options.output/'LocalAppData'),
        'startup_adapter':'Long USERPROFILE/project root; separate short app-data fixture; same real installed EXE',
        'snapshot_adapter':'Same assertions; independent extended IO reads every deep fixture file'}
    if maximum<=260 or before!=0 or after!=before:
        report['status']='FAIL';code=1
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps(report['long_path'],indent=2));raise SystemExit(code)
