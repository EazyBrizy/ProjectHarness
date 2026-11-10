"""One-time graceful transition from the previous running login-based build.

Uses only its previously accepted launcher API and public stop route. Never
exports credentials and never force-kills a user process or active operation.
"""
import http.client
import importlib.util
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit,parse_qs

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Project_Harness_Engine_v0.5.1/src'))
base=Path(os.environ['LOCALAPPDATA'])/'ProjectHarness'
result={'status':'NOT_NEEDED','force_kill':False}
if (base/'launcher-private.json').exists():
    old=OUT/'before/src/project_harness/local_web_instance.py'
    spec=importlib.util.spec_from_file_location('project_harness._previous_launcher',old)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    url=module.connect_existing(base);parts=urlsplit(url)
    assert parts.hostname=='127.0.0.1' and parts.scheme=='http'
    origin=f'http://127.0.0.1:{parts.port}'
    conn=http.client.HTTPConnection('127.0.0.1',parts.port,timeout=15)
    try:
        headers={'Origin':origin,'Content-Type':'application/json'}
        conn.request('POST','/api/session/bootstrap',body=json.dumps({'token':parse_qs(parts.fragment)['bootstrap'][0]}),headers=headers)
        response=conn.getresponse();raw=response.read();assert response.status==200
        headers.update({'Cookie':response.getheader('Set-Cookie').split(';',1)[0],'X-CSRF-Token':json.loads(raw)['csrf']})
        conn.request('POST','/api/desktop/stop',body='{}',headers=headers)
        response=conn.getresponse();body=json.loads(response.read())
        result={'status':'STOPPING' if response.status==200 else 'BUSY_OR_REFUSED','http_status':response.status,
                'force_kill':False,'operation_state':body.get('status')}
    finally:
        conn.close()
(OUT/'PREVIOUS_SERVER_STOP.json').write_text(json.dumps(result,indent=2)+'\n','utf-8')
print(json.dumps(result))
