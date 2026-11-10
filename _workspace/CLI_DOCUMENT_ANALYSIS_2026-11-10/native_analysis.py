"""One actual native Codex analysis, synthetic documents only; no user uploads."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path[:0]=[str(ROOT/'Project_Harness_Engine_v0.5.1/src'),str(ROOT/'Project_Harness_Engine_v0.5.1')]
from tests.test_ph_lw_04_05_acceptance import LiveServer
from project_harness import local_web_cli_analysis as analysis

suffix=('-'+sys.argv[sys.argv.index('--attempt')+1]) if '--attempt' in sys.argv else ('-02' if '--retry' in sys.argv else '')
base=ROOT/('_scratch/cli_document_analysis_20261110/native'+suffix)
base.mkdir(parents=True,exist_ok=False)
live=LiveServer(base)
original=analysis.invoke
def traced(argv,**kwargs):
    result=original(argv,**kwargs)
    events=[];items=[]
    for line in result[1].splitlines():
        try:
            event=json.loads(line);events.append(event.get('type'))
            if isinstance(event.get('item'),dict):items.append(event['item'].get('type'))
        except ValueError:pass
    stderr=result[2].decode('utf-8','replace')[-10000:]
    stderr=re.sub(r'(?:sk-[A-Za-z0-9_-]{10,}|eyJ[A-Za-z0-9_.-]{30,}|Bearer\s+\S+)', '[REDACTED]',stderr)
    (OUT/('NATIVE_CLI_TRANSPORT'+suffix+'.json')).write_text(json.dumps({'exit':result[0],'event_types':events,'item_types':items,
        'stderr_sanitized_tail':stderr,'command_tools_disabled':'shell_tool' in argv,'apps_disabled':'apps' in argv,
        'sandbox':'read-only','no_user_uploads':True},ensure_ascii=False,indent=2)+'\n','utf-8')
    return result
analysis.invoke=traced
report={'scope':'One actual Codex native document-analysis positive with synthetic source only','browser':'separate targeted UI fixture run','user_uploads_used':False}
try:
    code,_,connected=live.request('POST','/api/cli/connect',value={})
    assert code==200,(code,connected)
    report['connection']=connected
    pid=live.create('native-cli-doc-create-001')
    source='''# Прототип личной библиотеки
Нужно веб-приложение для одного человека, который ведёт домашнюю коллекцию книг.
Основной проверяемый результат: добавить книгу с названием и автором, затем найти её по названию.
Первый этап: локальный прототип для Windows. Данные хранятся локально; интернет для работы с книгами не требуется.
В первый этап входят добавление, поиск и список книг. Оплата, реклама и совместная работа не входят.
Документ описывает учебный синтетический проект, созданный только для проверки интеграции CLI.
'''
    assert live.upload(pid,[('Требования.md',source.encode())])[0]==200
    root,_=live.service._registered(pid)
    initial=hashlib.sha256((root/'PROJECT_INPUT.yaml').read_bytes()).hexdigest()
    view=live.request('GET',f'/api/projects/{pid}/interview')[2]
    code,_,job=live.request('POST',f'/api/projects/{pid}/cli/analysis',value={
        'expected_fingerprint':view['fingerprint'],'idempotency_key':'native-cli-analysis-start-001'})
    assert code==202,(code,job)
    deadline=time.monotonic()+360;previous=None
    while time.monotonic()<deadline:
        code,_,job=live.request('GET',f'/api/projects/{pid}/cli/analysis')
        assert code==200,(code,job)
        if job['state']!=previous:print(job['state']+': '+job['message_ru'],flush=True);previous=job['state']
        if job['state'] not in analysis.ACTIVE:break
        time.sleep(1)
    else:raise AssertionError('Analysis did not reach a terminal state')
    report['job']=job
    final=live.request('GET',f'/api/projects/{pid}/interview')[2]
    report['canonical_draft_unchanged']=hashlib.sha256((root/'PROJECT_INPUT.yaml').read_bytes()).hexdigest()==initial
    report['preview_count']=len([r for r in final['imports'] if r['state']=='PREVIEW'])
    transport=json.loads((OUT/('NATIVE_CLI_TRANSPORT'+suffix+'.json')).read_text('utf-8'))
    report['command_execution_events']=transport['item_types'].count('command_execution')
    report['unrelated_mcp_startup']='rmcp_client' in transport['stderr_sanitized_tail']
    report['status']='PASS' if job['state']=='SUCCEEDED' and report['canonical_draft_unchanged'] and report['preview_count']==1 and report['command_execution_events']==0 and not report['unrelated_mcp_startup'] else 'FAIL'
finally:
    if 'job' in locals() and job.get('state') in analysis.ACTIVE:
        live.request('POST',f'/api/projects/{pid}/cli/analysis/'+job['job_id']+'/cancel',value={})
    live.close();analysis.invoke=original
    (OUT/('NATIVE_ANALYSIS_RESULT'+suffix+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(report.get('status')!='PASS')
