"""Reproduce a real vanished-temp-file race using scheduling barriers only."""
import json,sys,threading,time,traceback
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sys.path.insert(0,str(ENGINE/'src'))
from project_harness.local_web_service import LocalWebService,OperationRequest
from project_harness.errors import HarnessError
import project_harness.serialization as serialization
out=ROOT/'_scratch/ph_lw_12_fix/poll-barrier-before';out.mkdir(exist_ok=False)
ready=threading.Event();release=threading.Event();main=threading.current_thread();failure=None
original_replace=serialization.os.replace;original_file=Path.is_file;observed=[]
with LocalWebService(out/'app-data') as service:
    pid=service.create_provisional_intake(project_name='Snapshot race',idempotency_key='poll-barrier-intake-0001',no_documentation=True)['project_id']
    root,_=service._registered(pid);fingerprint=service.get_status(pid)['fingerprint']
    def replacement(src,dest):
        if threading.current_thread() is not main and Path(dest).name=='READINESS.json' and str(root) in str(dest):
            ready.set();assert release.wait(10),'Reader did not reach serializer temp file'
        return original_replace(src,dest)
    def is_file(path):
        result=original_file(path)
        if threading.current_thread() is main and result and path.name.startswith('.READINESS.json.') and str(root) in str(path):
            observed.append(str(path));release.set()
            deadline=time.monotonic()+5
            while path.exists() and time.monotonic()<deadline:time.sleep(.001)
            assert not path.exists(),'Actual writer did not replace its temp file'
        return result
    with patch.object(serialization.os,'replace',replacement),patch.object(Path,'is_file',is_file):
        op=service.submit(OperationRequest(pid,'check-intake',{},'poll-barrier-operation-0001',fingerprint))
        assert ready.wait(15),'Public check-intake did not reach serializer replacement'
        try:service.get_operation(pid,op['operation_id'])
        except Exception:failure=traceback.format_exc()
        finally:release.set()
        deadline=time.monotonic()+15
        while service._load_op(op['operation_id'])['state'] in {'QUEUED','RUNNING'} and time.monotonic()<deadline:time.sleep(.01)
        final=service._load_op(op['operation_id'])['state']
result={'status':'REPRODUCED' if failure else 'NOT REPRODUCED','traceback':failure,'observed_temporary_files':observed,
    'worker_final_state':final,'fault':'Only pause actual public check-intake serializer before os.replace, then let it complete between reader is_file and stat. No fabricated exceptions or private canonical writes.'}
(out/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
assert failure and 'FileNotFoundError' in failure and final=='SUCCEEDED'
