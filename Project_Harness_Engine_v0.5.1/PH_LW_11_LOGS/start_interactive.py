import hashlib,json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'_scratch/ph_lw_11/installed-interactive';out.mkdir(exist_ok=False)
runtime=root/'_scratch/Л11interactive';runtime.mkdir(exist_ok=False)
profile=runtime/'Профиль';profile.mkdir();local=runtime/'LocalAppData';local.mkdir()
exe=root/'_scratch/ph_lw_11/build-ui-final/Harness-Setup-win-x64.exe'
command=[str(exe),'/DIR='+str(out/'Программа'),'/LOG='+str(out/'install.log'),'/NORESTART']
env={**os.environ,'USERPROFILE':str(profile),'LOCALAPPDATA':str(local),'PATH':str(Path(os.environ['SystemRoot'])/'System32'),'PYTHONPATH':'','PROJECT_HARNESS_HOME':''}
child=subprocess.Popen(command,cwd=runtime,env=env)
info={'command':command,'pid':child.pid,'installer_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'runtime_root':str(runtime),'status':'RUNNING_INTERACTIVE'}
(out/'LAUNCH.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(info,ensure_ascii=False,indent=2))
