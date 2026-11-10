"""Exercise the source launcher against isolated app-data and real loopback."""
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit, parse_qs

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
attempt='-02' if '--retry' in sys.argv else ''
fixture=ROOT/('_scratch/dev_launcher_20261109'+attempt)
fixture.mkdir(exist_ok=False)
sys.path.insert(0,str(ROOT/'Project_Harness_Engine_v0.5.1/src'))
from project_harness.local_web_instance import connect_existing

python=ROOT/'.venv/Scripts/python.exe'
helper=ROOT/'tools/launch_harness_dev.py'
env={**os.environ,'PYTHONPATH':'','PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'}
cookie=csrf=origin=None
child=None
report={}
def request(method,path,payload=None,authenticated=False):
    headers={'Origin':origin}
    if authenticated:
        headers.update({'Cookie':cookie,'X-CSRF-Token':csrf})
    if payload is not None:
        headers['Content-Type']='application/json'
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
    try:
        conn.request(method,path,body=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        response=conn.getresponse()
        return response.status,dict(response.getheaders()),response.read()
    finally:
        conn.close()

with (OUT/('server'+attempt+'.log')).open('wb') as log:
    try:
        child=subprocess.Popen([str(python),'-B',str(helper),'--no-browser','--app-data',str(fixture/'app')],
            cwd=fixture,env=env,stdout=log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            assert child.poll() is None,'Source launcher exited'
            try:
                url=connect_existing(fixture/'app');break
            except Exception:
                time.sleep(.1)
        else:
            raise AssertionError('Source launcher not ready')
        parsed=urlsplit(url);port=parsed.port;origin=f'http://127.0.0.1:{port}'
        status,_,raw=request('GET','/health')
        assert status==200 and json.loads(raw)=={'status':'ok'}
        report['real_waitress_tcp_health']='PASS'
        status,_,raw=request('GET','/api/session')
        assert status==200 and json.loads(raw)['authenticated'] is False
        report['unauthenticated_session_gated']='PASS'
        status,_,raw=request('GET','/')
        assert status==200 and b'upload-step-title' in raw
        report['current_source_ui']='PASS'
        second=subprocess.run([str(python),'-B',str(helper),'--no-browser','--app-data',str(fixture/'other-app')],
            cwd=fixture,env=env,capture_output=True,timeout=30)
        assert second.returncode==1 and not (fixture/'other-app').exists() and child.poll() is None
        report['second_instance_rejected_before_start']='PASS'
        status,headers,raw=request('POST','/api/session/bootstrap',{'token':parse_qs(parsed.fragment)['bootstrap'][0]})
        assert status==200
        cookie=headers['Set-Cookie'].split(';',1)[0];csrf=json.loads(raw)['csrf']
        status,_,_=request('POST','/api/desktop/stop',{},authenticated=True)
        assert status==200 and child.wait(timeout=30)==0
        report['authenticated_clean_stop']='PASS'
        checked=subprocess.run([str(ROOT/'.venv/Scripts/pythonw.exe'),'-B',str(helper),'--check'],cwd=fixture,env=env,timeout=30)
        assert checked.returncode==0
        report['windowless_shortcut_interpreter']='PASS'
        report['status']='PASS'
    finally:
        if child and child.poll() is None:
            child.terminate();child.wait(timeout=15)  # this script's own fixture child only
report.update(browser_opened=False,operator_data_accessed=False,automatic_executor_enabled=False)
(OUT/'SMOKE_RESULT.json').write_text(json.dumps(report,indent=2)+'\n','utf-8')
print(json.dumps(report,indent=2))
