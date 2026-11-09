"""Run the unchanged full no-doc browser scenario with genuinely deep app data.

This source diagnostic is distinct from the later actual installed EXE run.
"""
import argparse,importlib.util,json,socket,sys,threading,unittest
import functools,traceback
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sys.path[:0]=[str(ENGINE/'src'),str(ENGINE),str(ENGINE/'local_web/windows')]
from project_harness.local_web_service import LocalWebService
from project_harness.platform_fs import _native_io_path,native_glob
from project_harness.local_web_http import LocalWebAuth
from project_harness.local_web_launcher import create_loopback_server,open_bound_loopback_socket
from tests.test_ph_lw_04_05_acceptance import LiveServer

parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=False)
spec=importlib.util.spec_from_file_location('lw12_final_driver',ENGINE/'local_web/windows/final_acceptance.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.OPTIONS=SimpleNamespace(output=args.output)
# The shared driver owns the external-agent IO adaptation and full snapshot.
import project_harness.manual_tasks as manual
import project_harness.task_manual_evidence as manual_evidence
import project_harness.local_web_preparation as preparation
from project_harness.errors import HarnessError
for owner,names in [(manual,('verify_manual_task','complete_manual_task')),(manual_evidence,('record_manual_evidence',)),
                    (preparation,('get_preparation',)),(LocalWebService,('_registered','get_operation'))]:
    for name in names:
        original=getattr(owner,name)
        def observe(fn):
            @functools.wraps(fn)
            def traced(*args,**kwargs):
                try:return fn(*args,**kwargs)
                except HarnessError:raise
                except Exception:
                    traceback.print_exc();raise
            return traced
        setattr(owner,name,observe(original))

class NativeDeepServer(LiveServer):
    def __init__(self,directory):
        base=Path(directory)
        self.app_data=base/('Глубокий-'+('x'*120))/('данные-'+('y'*25))/'ProjectHarness'
        assert len(str(self.app_data))>213
        count=230-len(str(base/'profile-'/'HarnessProjects'))
        projects=base/('profile-'+('p'*count))/'HarnessProjects'
        assert count>0 and len(str(projects))==230
        self.service=LocalWebService(self.app_data,projects_directory=projects)
        self.auth=LocalWebAuth();self.socket=open_bound_loopback_socket();self.port=self.socket.getsockname()[1]
        self.origin=f'http://127.0.0.1:{self.port}'
        self.server=create_loopback_server(self.service,self.auth,self.socket)
        self.thread=threading.Thread(target=self.server.run,daemon=True);self.thread.start()
        self.cookie=self.csrf=None
        print(json.dumps({'native_deep_app_data_length':len(str(self.app_data))}),flush=True)

module.FrozenFixtureServer=NativeDeepServer
suite=unittest.defaultTestLoader.loadTestsFromName('InstalledFullFlowTests.test_no_documents_gpt_approvals_publish_manual_evidence_verify_complete',module)
result=unittest.TextTestRunner(verbosity=2).run(suite)
(args.output/'RESULT.json').write_text(json.dumps({'status':'PASS' if result.wasSuccessful() else 'FAIL','ran':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'kind':'Native source Edge/TCP; actual frozen delivery tested separately'},indent=2)+'\n','utf-8')
raise SystemExit(not result.wasSuccessful())
