"""Only the new CLI/pack connection boundaries; no full engine regression."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from project_harness.local_web_cli import CliError, invoke
from project_harness.serialization import load_data
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_ph_lw_03_service import byte_snapshot


class FixtureCli:
    """Declared synthetic CLI response, not a real provider/model conversation."""
    def __init__(self):
        self.calls=[];self.mode='ok';self.started=threading.Event();self.release=threading.Event()

    def __call__(self,argv,*,cwd,stdin=b'',timeout=15,cancel=None):
        self.calls.append(list(argv))
        if '--version' in argv:return 0,b'codex-cli 0.154.0\n',b''
        if '--help' in argv:return 0,b'--ignore-user-config --ephemeral --output-schema --output-last-message',b''
        if 'status' in argv:return (1,b'',b'Not logged in') if self.mode=='logged-out' else (0,b'',b'Logged in using ChatGPT')
        if 'models' in argv:
            return 0,json.dumps({'models':[{'slug':'fixture-model','display_name':'Модель проверки','visibility':'list',
                'default_reasoning_level':'medium','supported_reasoning_levels':[{'effort':'low'},{'effort':'medium'},{'effort':'high'}]}]}).encode(),b''
        self.started.set()
        if self.mode=='slow':
            for _ in range(200):
                if cancel.wait(.05):raise CliError('CLI_CANCELLED','Анализ остановлен.')
                if self.release.is_set():break
        if self.mode=='error':return 1,b'',b'private diagnostics must not reach HTTP'
        answer=Path(argv[argv.index('--output-last-message')+1])
        if self.mode=='invalid':
            answer.write_text('{"reply_json":"not-json"}','utf-8');return 0,b'',b''
        text=stdin.decode('utf-8')
        skeleton=json.loads(text.split('## Return skeleton\n\n',1)[1])
        payload=json.loads(text.split('## Exact payload\n\n',1)[1].split('## Return skeleton\n\n',1)[0])
        skeleton['project_input_draft']['project']['primary_outcome']='Результат из подключённого CLI'
        skeleton['claims']=[{'field':'project.primary_outcome','source_refs':[payload['documents'][0]['document_ref']]}]
        if 'analysis' in skeleton:
            skeleton['analysis'].update(summary='Результат анализа тестового документа.',current_stage={
                'title':'Первый прототип','goal':'Проверить основной сценарий.','basis':'Описание в документе.','source_refs':[payload['documents'][0]['document_ref']]})
        answer.write_text(json.dumps({'reply_json':json.dumps(skeleton,ensure_ascii=False)},ensure_ascii=False),'utf-8')
        return 0,b'',b''


class CliAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cli-analysis-');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.live=LiveServer(self.temp.name);self.addCleanup(self.live.close)
        self.pid=self.live.create('cli-document-test-create-001')
        self.assertEqual(self.live.upload(self.pid,[('Требования.md','# Приложение для учёта книг'.encode())])[0],200)
        self.executable=self.base/'codex.exe';self.executable.write_bytes(b'MZ declared fixture, never executed')
        self.fake=FixtureCli()
        for name,value in [('project_harness.local_web_cli.find_cli',lambda:self.executable),
                           ('project_harness.local_web_cli.invoke',self.fake),
                           ('project_harness.local_web_cli_analysis.invoke',self.fake)]:
            mock=patch(name,value);mock.start();self.addCleanup(mock.stop)
        self.path=f'/api/projects/{self.pid}'

    def fp(self):return self.live.request('GET',self.path+'/interview')[2]['fingerprint']
    def connect(self):
        code,_,value=self.live.request('POST','/api/cli/connect',value={});self.assertEqual(code,200,value)
        return value
    def start(self,key='cli-analysis-test-start-001',fp=None):
        return self.live.request('POST',self.path+'/cli/analysis',value={'expected_fingerprint':fp or self.fp(),'idempotency_key':key})
    def wait(self,job):
        self.live.service._futures[job].result(timeout=10)
        return self.live.request('GET',self.path+'/cli/analysis')[2]

    def test_gets_read_only_connect_fixed_commands_and_unknown_origin_rejected(self):
        before=byte_snapshot(self.base)
        self.assertFalse(self.live.request('GET','/api/cli')[2]['connected'])
        self.assertEqual(self.live.request('GET',self.path+'/cli/analysis')[2]['state'],'IDLE')
        self.assertEqual(byte_snapshot(self.base),before);self.assertEqual(self.fake.calls,[])
        self.assertEqual(self.live.request('POST','/api/cli/connect',value={'executable':'cmd.exe'})[0],400)
        self.assertEqual(self.live.request('POST','/api/cli/connect',value={},headers={'Origin':'http://foreign.invalid'})[0],403)
        self.assertEqual(self.fake.calls,[])
        self.assertTrue(self.connect()['connected']);self.assertEqual(len(self.fake.calls),4)
        self.assertNotIn('executable',self.live.request('GET','/api/cli')[2])
        calls=len(self.fake.calls);self.live.request('GET','/api/cli');self.assertEqual(len(self.fake.calls),calls)

    def test_connection_auth_missing_changed_binary_and_stale_inputs_block_before_analysis(self):
        self.fake.mode='logged-out'
        self.assertEqual(self.live.request('POST','/api/cli/connect',value={})[2]['error']['code'],'CLI_LOGIN_REQUIRED')
        self.fake.mode='ok';self.connect();self.executable.write_bytes(b'changed')
        self.assertEqual(self.start()[2]['error']['code'],'CLI_EXECUTABLE_CHANGED')
        self.connect();self.assertEqual(self.start(fp='sha256:'+'0'*64)[0],409)
        self.assertFalse(self.fake.started.is_set())
        with patch('project_harness.local_web_cli.find_cli',side_effect=CliError('CLI_NOT_FOUND','Не найден',503)):
            self.assertEqual(self.live.request('POST','/api/cli/connect',value={})[0],503)

    def test_manual_pack_one_click_no_classification_and_no_cli_launch(self):
        value={'expected_fingerprint':self.fp(),'idempotency_key':'manual-analysis-pack-001'}
        code,_,export=self.live.request('POST',self.path+'/analysis/package',value=value)
        self.assertEqual(code,201,export);self.assertEqual(self.fake.calls,[])
        again=self.live.request('POST',self.path+'/analysis/package',value=value)[2]
        self.assertEqual(again['exchange_id'],export['exchange_id'])
        pack=self.live.request('GET',self.path+'/gpt/exports/'+export['exchange_id']+'/pack.md')[2]
        self.assertIn(b'UNCLASSIFIED',pack);self.assertNotIn(b'"classification": "PUBLIC"',pack)
        root,_=self.live.service._registered(self.pid)
        record=root.parent/'exchange/exports'/export['exchange_id']/'record.json'
        receipt=load_data(record)['policy_receipt']
        self.assertEqual(receipt['classification_method'],'NOT_CLASSIFIED_BY_OPERATOR')
        self.assertEqual(self.live.request('POST',self.path+'/analysis/package',value={**value,'command':'anything'})[0],400)

    def test_result_uses_strict_preview_replay_does_not_rerun_and_draft_not_committed(self):
        self.connect();before=self.live.service.get_interview(self.pid)['draft']
        code,_,job=self.start();self.assertEqual(code,202,job)
        result=self.wait(job['job_id']);self.assertEqual(result['state'],'SUCCEEDED',result)
        after=self.live.service.get_interview(self.pid)
        self.assertEqual(after['draft'],before)
        self.assertEqual(after['imports'][-1]['state'],'PREVIEW')
        calls=len(self.fake.calls);same=self.start()[2]
        self.assertEqual(same['job_id'],job['job_id']);self.assertEqual(len(self.fake.calls),calls)
        self.assertEqual(self.live.request('POST',self.path+'/cli/analysis',value={'expected_fingerprint':self.fp(),'idempotency_key':'cli-analysis-test-start-001','argv':['bad']})[0],400)
        argv=self.fake.calls[-1]
        self.assertIn('read-only',argv);self.assertIn('shell_tool',argv);self.assertIn('--ignore-user-config',argv)

    def test_cancel_busy_stale_result_and_invalid_reply_never_apply_draft(self):
        self.connect();self.fake.mode='slow'
        _,_,job=self.start();self.assertTrue(self.fake.started.wait(3))
        self.assertEqual(self.start(key='second-analysis-busy-001')[2]['error']['code'],'CLI_BUSY')
        self.assertEqual(self.live.request('POST',self.path+'/cli/analysis/'+job['job_id']+'/cancel',value={})[0],200)
        self.assertEqual(self.wait(job['job_id'])['state'],'CANCELLED')
        self.fake.mode='invalid'
        _,_,job=self.start(key='invalid-reply-job-001');result=self.wait(job['job_id'])
        self.assertEqual(result['state'],'FAILED');self.assertEqual(self.live.service.get_interview(self.pid)['imports'],[])
        self.fake.mode='slow';self.fake.started.clear();self.fake.release.clear()
        _,_,job=self.start(key='stale-reply-job-001');self.assertTrue(self.fake.started.wait(3))
        self.assertEqual(self.live.upload(self.pid,[('Дополнение.md',b'# changed')])[0],200)
        self.fake.mode='ok'
        self.fake.release.set()
        stale=self.wait(job['job_id'])
        self.assertEqual(stale['state'],'FAILED');self.assertEqual(stale['error_code'],'STALE_EXCHANGE')
        self.assertEqual(self.live.service.get_interview(self.pid)['imports'],[])

    def test_restart_projection_is_read_only_and_never_restarts_cli(self):
        from project_harness.local_web_cli_analysis import _load,_save
        from project_harness.local_web_service import LocalWebService
        self.connect();_,_,job=self.start();self.wait(job['job_id'])
        directory=self.live.service.app_data/'cli-analysis'/self.pid
        path=directory/(job['job_id']+'.json');record=_load(path)
        record['state']='RUNNING';record['owner_pid']=-1;_save(path,record)
        calls=len(self.fake.calls);before=byte_snapshot(self.base)
        with LocalWebService(self.live.service.app_data) as restarted:
            self.assertTrue(restarted.get_cli_connection()['connected'])
            self.assertEqual(restarted.get_cli_analysis(self.pid)['state'],'INTERRUPTED')
        self.assertEqual(self.fake.calls.__len__(),calls)
        self.assertEqual(byte_snapshot(self.base),before)

    def test_direct_analysis_pack_keeps_secret_and_restricted_project_rejection(self):
        from project_harness.local_web_drafts import draft_input_digest,update_provisional_draft
        root,_=self.live.service._registered(self.pid)
        update_provisional_draft(root,{'project.data.sensitivity':'CONFIDENTIAL'},expected_input_digest=draft_input_digest(root))
        value={'expected_fingerprint':self.fp(),'idempotency_key':'restricted-analysis-pack-001'}
        code,_,result=self.live.request('POST',self.path+'/analysis/package',value=value)
        self.assertEqual(code,400,result);self.assertEqual(result['error']['code'],'EXPORT_POLICY_BLOCKED')
        update_provisional_draft(root,{'project.data.sensitivity':'UNKNOWN'},expected_input_digest=draft_input_digest(root))
        self.assertEqual(self.live.upload(self.pid,[('Секрет.md',b'-----BEGIN PRIVATE KEY-----\nsynthetic sentinel\n-----END PRIVATE KEY-----')])[0],200)
        code,_,result=self.live.request('POST',self.path+'/analysis/package',value={
            'expected_fingerprint':self.fp(),'idempotency_key':'secret-analysis-pack-001'})
        self.assertEqual(code,400,result)
        self.assertEqual(self.fake.calls,[])
        self.assertNotIn('synthetic sentinel',json.dumps(result))


class NativeTransportTests(unittest.TestCase):
    def test_owned_process_utf8_timeout_cancel_and_bounded_output(self):
        if os.name!='nt':self.skipTest('Native Windows transport')
        with tempfile.TemporaryDirectory(prefix='cli-transport-') as folder:
            cwd=Path(folder)
            code,out,_=invoke([sys.executable,'-c','import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())'],cwd=cwd,stdin='Текст'.encode(),timeout=5)
            self.assertEqual((code,out),(0,'Текст'.encode()))
            with self.assertRaises(CliError) as error:
                invoke([sys.executable,'-c','import time;time.sleep(30)'],cwd=cwd,timeout=.2)
            self.assertEqual(error.exception.cli_code,'CLI_TIMEOUT')
            event=threading.Event();timer=threading.Timer(.2,event.set);timer.start()
            with self.assertRaises(CliError) as error:
                invoke([sys.executable,'-c','import time;time.sleep(30)'],cwd=cwd,cancel=event,timeout=5)
            self.assertEqual(error.exception.cli_code,'CLI_CANCELLED');timer.join()
            with patch('project_harness.local_web_cli.OUTPUT_LIMIT',1024):
                with self.assertRaises(CliError) as error:
                    invoke([sys.executable,'-c','import sys;sys.stdout.write("x"*4096)'],cwd=cwd,timeout=5)
                self.assertEqual(error.exception.cli_code,'CLI_OUTPUT_TOO_LARGE')


if __name__=='__main__':unittest.main(verbosity=2)
