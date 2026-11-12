"""Two independent real document-analysis cases, no coding-agent delegation."""
import json,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sys.path.insert(0,str(ENGINE/'src'));sys.path.insert(0,str(ENGINE))
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_document_analysis_universality import UniversalityTests
from io import BytesIO
from zipfile import ZipFile
CASES=[{'name':'existing-service','documents':[
 ('z-current.md','# Согласованный этап R7: непрерывная миграция\nСервис уже работает в production. Сейчас требуется перенести API без остановки. В R7 обязательны совместимость маршрутов и платёжный callback. Начальная разработка завершена.\n'),
 ('nested/stack.md','# Принятый стек\nGo 1.23 и PostgreSQL 16 заданы проектом как условные версии тестового описания. Сервис не является мобильным приложением.\n'),
 ('a-future.md','# После R7\nЭтап R8 — обновление визуального оформления. R8 начинается после успешной миграции R7, не входит в текущую цель. Номера в имени файла не задают приоритет.\n')]},
 {'name':'nonsoftware-brief','documents':[('одна-заявка.MD','# Одностраничная заявка\nЦель — провести очную выставку двадцати архивных плакатов. Участники: куратор и экскурсовод. Это организационный, а не программный проект. Разработка приложения не предусмотрена. План работ в документации пока отсутствует, сроки и бюджет не выбраны.\n')]}]
services=[];jobs=[]
try:
    for index,case in enumerate(CASES):
        base=ROOT/'_scratch/document_analysis_universality_20261112/native'/case['name']
        assert not base.exists(),base
        base.mkdir(parents=True);live=LiveServer(str(base));services.append(live)
        pid=live.create('native-universal-create-'+str(index))
        if len(case['documents'])==1:uploads=[(case['documents'][0][0],case['documents'][0][1].encode('utf-8'))]
        else:
            stream=BytesIO()
            with ZipFile(stream,'w') as archive:
                for name,text in case['documents']:archive.writestr(name,text.encode('utf-8'))
            uploads=[('mixed-source-names.zip',stream.getvalue())]
        assert live.upload(pid,uploads)[0]==200
        connection=live.service.connect_cli()
        # Choose only values reported by this installed CLI; no model ID in fixture.
        selected=connection['models'][0]
        effort='low' if 'low' in selected['efforts'] else selected['default_effort']
        live.service.select_cli_model(model=selected['id'],reasoning_effort=effort)
        before=live.service.get_interview(pid)
        job=live.service.start_cli_analysis(pid,expected_fingerprint=before['fingerprint'],idempotency_key='native-universal-start-'+str(index))
        jobs.append((case,base,live,pid,before,job))
        print(json.dumps({'case':case['name'],'state':job['state'],'selection':job['selection']},ensure_ascii=False),flush=True)
    results=[]
    for case,base,live,pid,before,job in jobs:
        live.service._futures[job['job_id']].result(timeout=340)
        result=live.service.get_cli_analysis(pid);after=live.service.get_interview(pid)
        (base/'interview.json').write_text(json.dumps(after,ensure_ascii=False,indent=2),'utf-8')
        (base/'job.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
        assert after['draft']==before['draft']
        preview=after['imports'][-1] if after['imports'] else None
        analysis=preview.get('analysis') if preview else None
        errors=[]
        if result['state']!='SUCCEEDED':errors.append(result.get('repair_prompt') or result['message_ru'])
        if analysis:
            content=json.dumps(analysis,ensure_ascii=False).casefold()
            for foreign in ('flutter','android','sqlite','рецепт','premium'):
                if foreign in content:errors.append('Unrelated content: '+foreign)
            if case['name']=='existing-service':
                if 'прототип' in analysis['current_stage']['title'].casefold():errors.append('Existing service reset to prototype')
                if 'миграц' not in content and 'перенос' not in content:errors.append('Migration goal missing')
                if not any(s['stage']=='CURRENT' for s in analysis['roadmap']):errors.append('No current migration stage')
            else:
                if analysis['roadmap']:errors.append('Invented roadmap for explicitly missing plan')
                technology=next((d['after'] for d in preview['diff'] if d['field']=='technology.selections'),before['draft']['technology']['selections'])
                if technology:errors.append('Software stack imposed on nonsoftware brief')
        summary={'case':case['name'],'status':'FAIL' if errors else 'PASS','state':result['state'],
            'error_code':result.get('error_code'),'selection':result['selection'],'documents':len(case['documents']),
            'canonical_unchanged':True,'answers':len(analysis['answers']) if analysis else 0,
            'roadmap_stages':len(analysis['roadmap']) if analysis else 0,'errors':errors}
        results.append(summary);print(json.dumps(summary,ensure_ascii=False),flush=True)
    (OUT/'NATIVE_CASES.json').write_text(json.dumps({'status':'PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',
        'model_requests':len(jobs),'results':results},ensure_ascii=False,indent=2)+'\n','utf-8')
    assert all(r['status']=='PASS' for r in results),results
finally:
    for live in services:live.close()
