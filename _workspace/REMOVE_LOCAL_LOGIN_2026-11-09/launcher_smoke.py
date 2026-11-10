"""Actual source pythonw launch, address discovery, repeat start and direct stop."""
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
fixture=ROOT/'_scratch/remove_local_login_20261109/source-launcher'
fixture.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(ROOT/'Project_Harness_Engine_v0.5.1/src'))
from project_harness.local_web_instance import connect_existing
python=ROOT/'.venv/Scripts/python.exe';pythonw=ROOT/'.venv/Scripts/pythonw.exe'
helper=ROOT/'tools/launch_harness_dev.py'
env={**os.environ,'PYTHONPATH':'','PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'}
app=fixture/'app';app.mkdir();(app/'launcher-private.json').write_text('{"retired":"synthetic fixture"}','utf-8')
report={};child=None;origin=None

def request(method,path,payload=None):
    headers={'Origin':origin}
    if payload is not None:headers['Content-Type']='application/json'
    conn=http.client.HTTPConnection('127.0.0.1',urlsplit(origin).port,timeout=10)
    try:
        conn.request(method,path,body=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        response=conn.getresponse();raw=response.read()
        assert 'Set-Cookie' not in dict(response.getheaders())
        return response.status,json.loads(raw) if raw.startswith(b'{') else raw
    finally:conn.close()

def start():
    global child,origin
    child=subprocess.Popen([str(pythonw),'-B',str(helper),'--no-browser','--app-data',str(app)],cwd=fixture,env=env)
    for _ in range(200):
        assert child.poll() is None,'Source launcher exited'
        try:
            origin=connect_existing(app).rstrip('/');break
        except (OSError,ValueError):time.sleep(.1)
    else:raise AssertionError('Source launcher not ready')

try:
    checked=subprocess.run([str(pythonw),'-B',str(helper),'--check'],cwd=fixture,env=env,timeout=30)
    assert checked.returncode==0
    start()
    assert not (app/'launcher-private.json').exists()
    assert request('GET','/api/projects')[0]==200
    assert request('GET','/api/session')[0]==404
    status,page=request('GET','/');assert status==200 and b'session-gate' not in page
    assert request('POST','/api/intakes',{'project_name':'Source restart fixture','no_documentation':True,
        'idempotency_key':'source-direct-create-001'})[0]==201
    projects=request('GET','/api/projects')[1]
    # Capture the normal browser-open request in the second process so no visible window opens.
    code='import webbrowser,runpy,sys; webbrowser.open=lambda url,**kw: (print(url),True)[1]; sys.argv='+repr([str(helper),'--app-data',str(app)])+'; runpy.run_path('+repr(str(helper))+',run_name="__main__")'
    second=subprocess.run([str(python),'-B','-c',code],cwd=fixture,env=env,capture_output=True,text=True,timeout=30)
    assert second.returncode==0,(second.returncode,second.stderr)
    assert second.stdout.strip()==origin+'/' and child.poll() is None
    assert '#' not in second.stdout and '?' not in second.stdout
    assert request('POST','/api/desktop/stop',{})[0]==200 and child.wait(timeout=30)==0
    start()
    assert request('GET','/api/projects')[1]==projects
    assert request('POST','/api/desktop/stop',{})[0]==200 and child.wait(timeout=30)==0
    assert not (app/'launcher-instance.json').exists()
    report={'status':'PASS','pythonw_source_launcher':'PASS','direct_http_without_credentials':'PASS',
        'legacy_record_retired':'PASS','second_launch_plain_url_same_process':'PASS','restart_retains_project':'PASS',
        'direct_clean_stop':'PASS','browser_open_intercepted':True,'visible_browser':'NOT RUN',
        'operator_data_accessed':False,'automatic_executor_enabled':False}
finally:
    if child and child.poll() is None:
        try:
            request('POST','/api/desktop/stop',{});child.wait(timeout=30)
        except Exception:child.terminate();child.wait(timeout=15) # only our own isolated fixture
(OUT/'LAUNCHER_SMOKE.json').write_text(json.dumps(report,indent=2)+'\n','utf-8')
print(json.dumps(report,indent=2))
