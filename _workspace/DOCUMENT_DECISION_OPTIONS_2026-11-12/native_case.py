"""One real v4 analysis and explicit recommended choice in a synthetic workspace."""
import json,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sys.path.insert(0,str(ENGINE/'src'));sys.path.insert(0,str(ENGINE))
from tests.test_ph_lw_04_05_acceptance import LiveServer
from project_harness.local_web_drafts import update_provisional_draft,draft_input_digest
BASE=ROOT/'_scratch/document_decision_options_20261112/native';assert not BASE.exists();BASE.mkdir(parents=True)
live=LiveServer(str(BASE))
try:
    pid=live.create('native-decision-options-create-001')
    document='''# Сравнение двух JSON файлов
Цель прототипа — один локальный пользователь сравнивает два UTF-8 JSON файла
и видит пути отличающихся значений. Это CLI-инструмент на Python 3.14 со
стандартной библиотекой, без сервера, сети и аккаунтов. Платформы Windows/Linux.
Данные тестовые, общедоступные, временно хранятся локально; рост нагрузки не нужен.
Сравнение примитивов и полей объектов определено. Как учитывать порядок элементов
массивов, пока не решено: важен выбор понятного правила без скрытой потери различий.
Проверка: одинаковые данные не имеют отличий, разные примитивы показывают путь.
Формальный план файлов/задач и команды сборки ещё не описаны.
'''
    assert live.upload(pid,[('одно-описание.md',document.encode('utf-8'))])[0]==200
    root,_=live.service._registered(pid)
    update_provisional_draft(root,{'implementation.target_level':'PROTOTYPE',
        'project.unknowns':[{'question':'Как учитывать порядок элементов массивов при сравнении?','blocking':True}]},
        expected_input_digest=draft_input_digest(root))
    connection=live.service.connect_cli();model=connection['models'][0]
    effort='low' if 'low' in model['efforts'] else model['default_effort']
    live.service.select_cli_model(model=model['id'],reasoning_effort=effort)
    before=live.service.get_interview(pid)
    job=live.service.start_cli_analysis(pid,expected_fingerprint=before['fingerprint'],idempotency_key='native-decision-options-start-001')
    print(json.dumps({'state':job['state'],'selection':job['selection']},ensure_ascii=False),flush=True)
    live.service._futures[job['job_id']].result(timeout=340)
    result=live.service.get_cli_analysis(pid);view=live.service.get_interview(pid)
    (BASE/'job.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    (BASE/'interview-before-choice.json').write_text(json.dumps(view,ensure_ascii=False,indent=2),'utf-8')
    summary={'status':'FAIL','state':result['state'],'selection':result['selection'],'model_requests':1,
        'canonical_unchanged_by_model':view['draft']==before['draft'],'error_code':result.get('error_code')}
    if result['state']=='SUCCEEDED':
        preview=view['imports'][-1];questions=preview['analysis']['questions']
        assert questions and all(2<=len(q['choices'])<=3 for q in questions)
        assert any(q['existing_unknown_index']==0 for q in questions)
        live.service.commit_gpt_reply(pid,preview['import_id'],preview_digest=preview['preview_digest'],expected_fingerprint=view['fingerprint'])
        saved=live.service.get_interview(pid);question=next(q for q in saved['analysis']['questions'] if q['existing_unknown_index']==0)
        selected=live.service.answer_interview_question(pid,analysis_import_id=saved['analysis_import_id'],question_id=question['id'],
            choice_id=question['recommended_choice_id'],answer_text='',custom_value=None,has_custom_value=False,
            expected_fingerprint=saved['fingerprint'],idempotency_key='native-explicit-recommended-choice-001')
        after=live.service.get_interview(pid)
        (BASE/'interview-after-choice.json').write_text(json.dumps(after,ensure_ascii=False,indent=2),'utf-8')
        assert len(after['user_answers'])==1 and selected['state']=='COMMITTED'
        assert not any(a['approved'] for a in after['draft']['approvals'].values())
        summary.update(status='PASS',questions=len(questions),choices=sum(len(q['choices']) for q in questions),
            selected_question=question['question'],selected_title=selected['user_answer']['title'],
            resolves_question=selected['user_answer']['resolves_question'],user_answer_saved=True,
            no_approvals=True,task_execution=False)
    (OUT/'NATIVE_CASE.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    assert summary['status']=='PASS',result
finally:live.close()
