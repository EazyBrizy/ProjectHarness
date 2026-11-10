"""Graceful public stop before the authorized update; never force-kill user work."""
import http.client
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'Project_Harness_Engine_v0.5.1/src'))
from project_harness.local_web_launcher import default_app_data
from project_harness.local_web_instance import connect_existing,_read_record,_process_running

base=default_app_data()
try:record=_read_record(base/'launcher-instance.json')
except FileNotFoundError:
    record=None;result={'status':'ALREADY_STOPPED','force_kill':False}
if record:
    origin=connect_existing(base).rstrip('/');port=urlsplit(origin).port
    for _ in range(60):
        conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
        try:
            conn.request('POST','/api/desktop/stop',body=b'{}',headers={'Origin':origin,'Content-Type':'application/json'})
            response=conn.getresponse();status=response.status;body=json.loads(response.read())
        finally:conn.close()
        if status==200 and body=={'status':'STOPPING'}:break
        if status!=409:raise RuntimeError('Public stop refused: '+str(status))
        time.sleep(.5)
    else:raise RuntimeError('Active work did not finish; no force stop attempted')
    for _ in range(100):
        if not _process_running(record['pid']):break
        time.sleep(.1)
    else:raise RuntimeError('Graceful stop has not finished')
    result={'status':'STOPPED','http_status':status,'active_work_waited':True,'force_kill':False,'pid':record['pid']}
(OUT/'STOP_FOR_UPDATE.json').write_text(json.dumps(result,indent=2)+'\n','utf-8')
print(json.dumps(result,indent=2))
