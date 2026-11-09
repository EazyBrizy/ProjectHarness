"""Native public-operation vs read-only journal polling race diagnostic."""
import json,sys,threading,time,traceback
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sys.path.insert(0,str(ENGINE/'src'))
from project_harness.local_web_service import LocalWebService,OperationRequest
from project_harness.errors import HarnessError
out=ROOT/'_scratch/ph_lw_12_fix/poll-race-before';out.mkdir(exist_ok=False)
done=threading.Event();ids=[];worker_errors=[];calls=0;failure=None;delays=[]
with LocalWebService(out/'app-data') as service:
    pid=service.create_provisional_intake(project_name='Polling race',idempotency_key='poll-race-before-intake-0001',no_documentation=True)['project_id']
    root,_=service._registered(pid)
    def mutate():
        try:
            for index in range(100):
                if done.is_set():break
                op=service.submit(OperationRequest(pid,'check-intake',{},'poll-race-'+str(index).zfill(12),service.get_status(pid)['fingerprint']))
                ids.append(op['operation_id'])
                while service._load_op(op['operation_id'])['state'] in {'QUEUED','RUNNING'}:time.sleep(.001)
        except Exception:worker_errors.append(traceback.format_exc())
        finally:done.set()
    original=Path.is_file;main=threading.current_thread()
    def delayed(path):
        result=original(path)
        if result and threading.current_thread() is main and path.name.startswith('.') and str(root) in str(path):
            delays.append(path.name);time.sleep(.02)
        return result
    thread=threading.Thread(target=mutate);thread.start()
    with patch.object(Path,'is_file',delayed):
        while not done.is_set() and calls<10000:
            if not ids:time.sleep(.001);continue
            calls+=1
            try:service.get_operation(pid,ids[-1])
            except HarnessError:pass
            except Exception:
                failure=traceback.format_exc();done.set();break
    thread.join(120);assert not thread.is_alive()
result={'status':'REPRODUCED' if failure else 'NOT REPRODUCED','poll_calls':calls,'actual_public_operations':len(ids),
    'fault':'Only delay main read after successful is_file of an actual serializer temp file; no fabricated exceptions or canonical edits.',
    'delayed_temporary_names':delays,'traceback':failure,'worker_errors':worker_errors}
(out/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
