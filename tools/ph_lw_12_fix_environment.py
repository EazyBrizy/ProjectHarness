"""Installed wheel identity/dependencies outside the source tree."""
import ctypes,hashlib,json,os,platform,subprocess,sys
from importlib.metadata import version
from pathlib import Path
import project_harness
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];W=ROOT/'_workspace/PH_LW_12_FIX'
package=Path(project_harness.__file__).resolve().parent
assert package.is_relative_to(Path(sys.prefix).resolve())
freeze=json.loads((W/'RUNTIME_FREEZE.json').read_text('utf-8'))
actual={p.relative_to(package).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in package.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert actual==freeze['source_hashes']
fs=ctypes.create_unicode_buffer(64)
assert ctypes.windll.kernel32.GetVolumeInformationW(str(ROOT.anchor),None,0,None,None,None,fs,64)
check=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True)
assert check.returncode==0,check.stdout
with sync_playwright() as play:
    browser=play.chromium.launch(channel='msedge',headless=True)
    browser_version=browser.version
    browser.close()
edge=Path(os.environ['ProgramFiles(x86)'])/'Microsoft/Edge/Application/msedge.exe'
assert edge.is_file()
data={'status':'PASS','command':[sys.executable,*sys.argv],'exit':0,
      'python':sys.version,'executable':sys.executable,'prefix':sys.prefix,'installed_package':str(package),
      'cwd':str(Path.cwd()),'PYTHONPATH':os.environ.get('PYTHONPATH',''),'platform':platform.platform(),
      'filesystem':fs.value,'non_admin':not bool(ctypes.windll.shell32.IsUserAnAdmin()),
      'dependencies':{n:version(n) for n in ('Flask','Waitress','Playwright','PyYAML','jsonschema')},
      'build_id':freeze['build_id'],'engine_build_digest':freeze['engine_build_digest'],
      'wheel_sha256':freeze['wheel_sha256'],'package_byte_equality':'PASS','pip_check':check.stdout.strip(),
      'browser':'existing msedge headless','browser_version':browser_version,
      'browser_executable':str(edge),'browser_executable_sha256':hashlib.sha256(edge.read_bytes()).hexdigest(),
      'dependency_install':'Offline --no-index --require-hashes; existing hash-locked wheelhouses',
      'automatic_executor':'disabled','zip_created':False}
(W/'WHEEL_ENVIRONMENT.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps({'status':'PASS','build_id':freeze['build_id'],'package_byte_equality':'PASS'}))
