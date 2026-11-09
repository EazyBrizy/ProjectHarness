import json,os,subprocess,sys,time,types
from pathlib import Path
root=Path(__file__).resolve().parents[2];engine=root/'Project_Harness_Engine_v0.5.1';sys.path[:0]=[str(engine/'src'),str(engine)]
from project_harness.local_web_instance import connect_existing
from tests.test_ph_lw_04_05_acceptance import LiveServer
out=root/'_scratch/ph_lw_11/installed-interactive';runtime=root/'_scratch/Л11interactive'
app=runtime/'LocalAppData/ProjectHarness';url=connect_existing(app)
live=LiveServer.__new__(LiveServer);live.origin=url.split('/#')[0];live.port=int(live.origin.rsplit(':',1)[1]);live.cookie=live.csrf=None
live.auth=types.SimpleNamespace(issue_bootstrap=lambda:connect_existing(app).split('=')[1]);live.login()
projects=live.request('GET','/api/projects');assert projects[0]==200 and not projects[2]['projects']
assert live.request('POST','/api/desktop/stop',value={})[0]==200
for _ in range(100):
    if not (app/'launcher-private.json').exists():break
    time.sleep(.1)
assert not (app/'launcher-private.json').exists()
uninstall=next((out/'Программа/uninstall').glob('unins*.exe'))
command=[str(uninstall),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/LOG='+str(out/'uninstall.log')]
removed=subprocess.run(command,timeout=120);assert removed.returncode==0
report={'status':'PARTIAL / VISUAL_CHECK_NOT_COMPLETED',
 'interactive_install':'PASS: nonsilent setup log records completion and Run entry',
 'postinstall_launcher':'PASS: authenticated live server and empty project catalog observed; no extra launch used',
 'wizard_visual':'NOT RUN: Computer Use stopped because browser URL could not be determined confidently; installer UI clicks were not recorded by this agent',
 'automatic_intake_created':False,'clean_stop':'PASS','uninstall_exit':removed.returncode,'uninstall_command':command}
(out/'RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
