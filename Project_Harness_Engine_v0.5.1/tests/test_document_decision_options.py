"""Only decision-options contract, user selection, recovery and browser paths."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from project_harness.local_web_exchange_contract import validate_envelope,digest,ExchangeError
from project_harness.local_web_analysis import normalize_analysis
from project_harness.local_web_drafts import update_provisional_draft,draft_input_digest,DRAFT_FIELDS
from tests.test_ph_lw_03_service import byte_snapshot
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_document_analysis_universality import synthetic_analysis
from tests.test_manual_analysis_archive import ManualArchiveBrowserTests


def choice(ident,title,answer,changes=(),resolves=True):
    return {'id':ident,'title':title,'description':answer,'tradeoffs':['Проверьте соответствие условиям проекта.'],
        'answer':answer,'resolves_question':resolves,'changes':list(changes)}


def fixture_choices(reply):
    """Compatibility fixtures describe two real approaches, never model evidence."""
    if reply.get('envelope_version',0)<4:return reply
    for q in reply['questions']:
        q.setdefault('existing_unknown_index',None)
        q.setdefault('choices',[choice('MEASURE','Сначала проверить','Провести ограниченную проверку и затем выбрать решение.',resolves=False),
            choice('CLARIFY','Уточнить требования','Уточнить требования у ответственного за проект.',resolves=False)])
        q.setdefault('recommended_choice_id',q['choices'][0]['id'])
        q.setdefault('recommendation_reason','Проверка ограничивает риск и не выдумывает отсутствующие факты.')
    return reply


class DecisionOptionsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='document-decisions-');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.live=LiveServer(self.temp.name);self.addCleanup(self.live.close)
        self.pid=self.live.create('decision-options-create-0001');self.path='/api/projects/'+self.pid
        self.assertEqual(self.live.upload(self.pid,[('brief.md','# Библиотека обработки данных. Существующий интерфейс сохраняется.'.encode())])[0],200)

    def view(self):return self.live.service.get_interview(self.pid)
    def reply(self):
        view=self.view();export=self.live.service.create_analysis_export(self.pid,expected_fingerprint=view['fingerprint'],idempotency_key='decision-options-export-0001')
        self.export=export
        pack=self.live.service.read_gpt_export(self.pid,export['exchange_id'],'pack.md').decode('utf-8')
        reply=json.loads(pack.split('## Return skeleton\n\n',1)[1]);ref=view['documents'][0]['document_ref']
        reply['analysis']=synthetic_analysis(ref,'Библиотека с существующим API.','Уточнение границ поставки')
        reply['project_input_draft']['architecture']['interfaces']=['Существующий API']
        reply['claims']=[{'field':'architecture.interfaces','source_refs':[ref]}]
        def q(ident,field,text,choices,stage='CURRENT',blocking=True):
            return {'id':ident,'field':field,'question':text,'why':'Нужно выбрать подход к этому аспекту.',
                'stage':stage,'blocking':blocking,'source_refs':[ref],'existing_unknown_index':None,
                'choices':choices,'recommended_choice_id':choices[0]['id'],'recommendation_reason':'Первый вариант ограничивает объём текущей работы.'}
        reply['questions']=[
            q('TARGET','implementation.target_level','До какого уровня подготовить проект?',[
                choice('PROTOTYPE','Проверить основной сценарий','Сначала проверить основной сценарий в прототипе.',[{'field':'implementation.target_level','operation':'SET','value':'PROTOTYPE'}]),
                choice('ALPHA','Подготовить внутреннюю версию','Подготовить альфа-версию для внутренней работы.',[{'field':'implementation.target_level','operation':'SET','value':'ALPHA'}])]),
            q('BUDGET','project.constraints.mandatory','Как определить доступный бюджет?',[
                choice('ASK_OWNER','Уточнить у ответственного','Получить бюджет у ответственного; сумма пока неизвестна.',resolves=False),
                choice('MEASURE','Оценить после проверки','Оценить затраты после небольшой проверки.',resolves=False)]),
            q('CPP','architecture.interfaces','Как поддержать C++ интерфейс позже?',[
                choice('CPP_ADAPTER','Добавить адаптер C++','Предусмотреть отдельный C++ адаптер.',[{'field':'architecture.interfaces','operation':'APPEND','value':['Адаптер C++']}]),
                choice('CPP_WAIT','Уточнить спрос','Сначала проверить спрос на адаптер.',resolves=False)],'FUTURE',False),
            q('CSHARP','architecture.interfaces','Как поддержать C# интерфейс позже?',[
                choice('CSHARP_ADAPTER','Добавить адаптер C#','Предусмотреть отдельный C# адаптер.',[{'field':'architecture.interfaces','operation':'APPEND','value':['Адаптер C#']}]),
                choice('CSHARP_WAIT','Сначала исследовать','Проверить востребованность интерфейса.',resolves=False)],'FUTURE',False),
            q('OUTCOME','project.primary_outcome','Какой результат должен получить пользователь?',[
                choice('READ','Читать данные','Пользователь читает один набор данных.',[{'field':'project.primary_outcome','operation':'SET','value':'Чтение одного набора данных'}]),
                choice('COMPARE','Сравнивать данные','Пользователь сравнивает два набора данных.',[{'field':'project.primary_outcome','operation':'SET','value':'Сравнение двух наборов данных'}])])]
        return reply
    def preview(self,reply):
        return self.live.service.preview_gpt_reply(self.pid,text=json.dumps(reply,ensure_ascii=False),expected_fingerprint=self.view()['fingerprint'])
    def accept_analysis(self):
        result=self.preview(self.reply());self.assertEqual(result['status'],'PREVIEW',result);preview=result['preview']
        self.live.service.commit_gpt_reply(self.pid,preview['import_id'],preview_digest=preview['preview_digest'],expected_fingerprint=self.view()['fingerprint'])
        return preview
    def request(self,qid,cid,key=None,**custom):
        view=self.view()
        return {'analysis_import_id':view['analysis_import_id'],'question_id':qid,'choice_id':cid,
            'answer_text':'','custom_value':None,'has_custom_value':False,'expected_fingerprint':view['fingerprint'],
            'idempotency_key':key or 'answer-'+qid+'-unique-0001',**custom}
    def answer(self,qid,cid,**custom):
        body=self.request(qid,cid,**custom)
        code,_,value=self.live.request('POST',self.path+'/interview/answers',value=body)
        self.assertEqual(code,200,value);return value

    def test_strict_options_recommendation_values_and_legacy_envelopes(self):
        original=self.reply();validate_envelope(original)
        for version in (2,3):
            legacy=deepcopy(original);legacy['envelope_version']=version
            if version==2:legacy.pop('analysis');legacy['questions']=[];legacy['uncertainties']=[]
            else:
                for q in legacy['questions']:
                    for key in ['choices','recommended_choice_id','recommendation_reason','existing_unknown_index']:q.pop(key)
            validate_envelope(legacy)
        cases=[]
        bad=deepcopy(original);bad['questions'][0]['choices']=[];cases.append((bad,'EXCHANGE_SCHEMA_INVALID'))
        bad=deepcopy(original);bad['questions'][0]['recommended_choice_id']='NOT_PRESENT';cases.append((bad,'CHOICE_RECOMMENDATION_INVALID'))
        bad=deepcopy(original);bad['questions'][0]['choices'][0]['changes'][0]['value']='INVALID_LEVEL';cases.append((bad,'CHOICE_VALUE_INVALID'))
        bad=deepcopy(original);bad['questions'][0]['choices'][0]['changes'][0]['field']='execution.mode';cases.append((bad,'CHOICE_FIELD_INVALID'))
        bad=deepcopy(original);bad['questions'][0]['choices'][0]['changes']=[{'field':'planning.work_packages','operation':'SET','value':[]}];cases.append((bad,'CHOICE_FIELD_INVALID'))
        bad=deepcopy(original);bad['questions'][0]['choices'][0]['changes']=[];cases.append((bad,'CHOICE_VALUE_INVALID'))
        bad=deepcopy(original);bad['project_input_draft']['implementation']['target_level']='PROTOTYPE';cases.append((bad,'TARGET_DECISION_REQUIRED'))
        for value,code in cases:
            before=byte_snapshot(self.base);result=self.preview(value)
            self.assertEqual(result['status'],'REJECTED',result);self.assertEqual(result['error']['code'],code,result)
            self.assertEqual(byte_snapshot(self.base),before)

    def test_existing_questions_receive_options_without_duplicates_or_unblocking(self):
        root,_=self.live.service._registered(self.pid)
        update_provisional_draft(root,{'project.unknowns':[{'question':'Уточнить ограничения','blocking':True}]},expected_input_digest=draft_input_digest(root))
        reply=self.reply();reply['questions'][0]['existing_unknown_index']=0
        reply['questions'][0]['question']='Новая формулировка того же решения?'
        result=self.preview(reply);self.assertEqual(result['status'],'PREVIEW',result)
        self.assertEqual(result['preview']['analysis']['questions'][0]['question'],'Уточнить ограничения')
        unknowns=next(d['after'] for d in result['preview']['diff'] if d['field']=='project.unknowns')
        self.assertEqual(sum(u['question']=='Уточнить ограничения' for u in unknowns),1)
        reply['questions'][0]['blocking']=False
        self.assertEqual(self.preview(reply)['error']['code'],'QUESTION_SCOPE_CONFLICT')

    def test_selection_keep_open_append_custom_and_next_packet_context(self):
        self.accept_analysis();self.assertIsNone(self.view()['draft']['implementation']['target_level'])
        with patch('project_harness.local_web_cli.invoke',side_effect=AssertionError('No model call on selection')):
            self.answer('TARGET','PROTOTYPE')
            self.answer('BUDGET','ASK_OWNER')
            self.answer('CPP','CPP_ADAPTER');self.answer('CSHARP','CSHARP_ADAPTER')
            self.answer('OUTCOME',None,answer_text='Пользователь проверяет целостность набора данных.')
        view=self.view();self.assertEqual(view['draft']['implementation']['target_level'],'PROTOTYPE')
        self.assertEqual(view['draft']['architecture']['interfaces'],['Существующий API','Адаптер C++','Адаптер C#'])
        self.assertEqual(view['draft']['project']['primary_outcome'],'Пользователь проверяет целостность набора данных.')
        self.assertEqual(len(view['analysis']['questions']),1)
        self.assertTrue(view['draft']['project']['unknowns'][0]['blocking'])
        self.assertIn('сумма пока неизвестна',view['draft']['project']['unknowns'][0]['decision_plan'])
        self.assertEqual(len(view['user_answers']),5)
        self.assertTrue(all(not a['superseded_fields'] for a in view['user_answers']))
        self.assertFalse(any(a['approved'] for a in view['draft']['approvals'].values()))
        root,_=self.live.service._registered(self.pid)
        update_provisional_draft(root,{'implementation.target_level':'ALPHA'},expected_input_digest=draft_input_digest(root))
        view=self.view()
        self.assertEqual(next(a for a in view['user_answers'] if a['question_id']=='TARGET')['superseded_fields'],['implementation.target_level'])
        export=self.live.service.create_analysis_export(self.pid,expected_fingerprint=view['fingerprint'],idempotency_key='answered-export-context-001')
        pack=self.live.service.read_gpt_export(self.pid,export['exchange_id'],'pack.md').decode()
        payload=json.loads(pack.split('## Exact payload\n\n',1)[1].split('## Return skeleton\n\n',1)[0])
        self.assertEqual(len(payload['user_answers']),5);self.assertEqual(len(payload['open_items']),1)

    def test_replay_origin_tamper_stale_set_and_changed_sources(self):
        self.accept_analysis();body=self.request('CPP','CPP_ADAPTER')
        self.assertEqual(self.live.request('POST',self.path+'/interview/answers',value=body,headers={'Origin':'https://foreign.invalid'})[0],403)
        self.assertEqual(self.live.request('POST',self.path+'/interview/answers',value={**body,'changes':[]})[0],400)
        first=self.live.request('POST',self.path+'/interview/answers',value=body)[2];before=byte_snapshot(self.base)
        second=self.live.request('POST',self.path+'/interview/answers',value=body)[2]
        self.assertEqual(first['import_id'],second['import_id']);self.assertEqual(byte_snapshot(self.base),before)
        conflict=self.live.request('POST',self.path+'/interview/answers',value={**body,'choice_id':'CPP_WAIT'})
        self.assertEqual(conflict[2]['error']['code'],'ANSWER_REPLAY_CONFLICT')
        root,_=self.live.service._registered(self.pid)
        update_provisional_draft(root,{'implementation.target_level':'ALPHA'},expected_input_digest=draft_input_digest(root))
        stale=self.live.request('POST',self.path+'/interview/answers',value=self.request('TARGET','PROTOTYPE'))
        self.assertEqual(stale[2]['error']['code'],'CHOICE_STALE')
        self.assertEqual(self.view()['draft']['implementation']['target_level'],'ALPHA')
        self.answer('TARGET',None,answer_text='Для этого цикла выбираю бета-версию.',has_custom_value=True,custom_value='BETA')
        self.assertEqual(self.view()['draft']['implementation']['target_level'],'BETA')
        self.assertEqual(self.live.upload(self.pid,[('new.md',b'# Changed source inventory')])[0],200)
        changed=self.live.request('POST',self.path+'/interview/answers',value=self.request('BUDGET','ASK_OWNER'))
        self.assertEqual(changed[2]['error']['code'],'STALE_EXCHANGE')

    def test_existing_commit_recovery_keeps_user_intent_before_and_after_atomic_write(self):
        import project_harness.local_web_exchange as exchange
        self.accept_analysis();real=exchange.update_provisional_draft
        for qid,cid,after in [('TARGET','PROTOTYPE',True),('CPP','CPP_ADAPTER',False)]:
            body=self.request(qid,cid)
            def interrupted(*args,**kwargs):
                if after:real(*args,**kwargs)
                raise RuntimeError('declared interruption')
            with patch.object(exchange,'update_provisional_draft',side_effect=interrupted):
                with self.assertRaises(RuntimeError):self.live.service.answer_interview_question(self.pid,**body)
            result=self.live.service.recover_gpt_reply(self.pid)
            self.assertEqual(result['status'],'COMMITTED_RECOVERED' if after else 'NOT_COMMITTED')
            if not after:self.live.service.answer_interview_question(self.pid,**body)
            self.assertTrue(any(a['question_id']==qid for a in self.view()['user_answers']))


class DecisionOptionsBrowserTests(DecisionOptionsTests):
    open_page=ManualArchiveBrowserTests.open_page
    def view(self):
        # Browser reads share its serialized transport; a direct service GET
        # would race the page's own pending reads against the operation guard.
        if hasattr(self,'page'):
            return self.page.evaluate('() => api(interviewPath("/interview"))')
        return super().view()
    def test_recommended_options_preview_single_click_custom_and_future(self):
        result=self.preview(self.reply());self.assertEqual(result['status'],'PREVIEW',result)
        self.open_page();p=self.page;e=self.expect
        e(p.locator('#reply-diff')).to_contain_text('Рекомендуется')
        self.assertEqual(p.locator('#reply-diff button',has_text='Выбрать этот вариант').count(),0)
        self.assertIsNone(self.view()['draft']['implementation']['target_level'])
        p.locator('#commit-reply').click();e(p.locator('#interview-status')).to_contain_text('сохранён')
        row=p.locator('#question-fields .question').filter(has=p.get_by_role('heading',name='До какого уровня подготовить проект?',exact=True))
        self.assertEqual(row.locator('.decision-option').count(),2)
        folder=os.environ.get('DECISION_OPTIONS_EVIDENCE')
        if folder:
            target=Path(folder);target.mkdir(parents=True,exist_ok=True);row.screenshot(path=str(target/'ready-options.png'))
        self.assertIsNone(self.view()['draft']['implementation']['target_level'])
        row.locator('.decision-recommended').get_by_role('button',name='Выбрать этот вариант',exact=True).click()
        e(p.locator('#notice')).to_contain_text('Вопрос решён')
        self.assertEqual(self.view()['draft']['implementation']['target_level'],'PROTOTYPE')
        row=p.locator('#question-fields .question').filter(has=p.get_by_role('heading',name='Как определить доступный бюджет?',exact=True))
        row.locator('.decision-recommended').get_by_role('button',name='Выбрать этот вариант',exact=True).click()
        e(p.locator('#notice')).to_contain_text('остаётся открытым');e(row).to_be_visible()
        e(row).to_contain_text('Сохранён подход')
        row=p.locator('#question-fields .question').filter(has=p.get_by_role('heading',name='Какой результат должен получить пользователь?',exact=True))
        row.locator('.custom-decision > summary').click();row.get_by_label('Ваш ответ',exact=True).fill('Проверить согласованность данных.')
        row.get_by_role('button',name='Сохранить свой ответ',exact=True).click();e(p.locator('#notice')).to_contain_text('Вопрос решён')
        self.assertEqual(self.view()['draft']['project']['primary_outcome'],'Проверить согласованность данных.')
        p.locator('#question-fields details > summary').filter(has_text='Вопросы будущих этапов').click()
        row=p.locator('#question-fields .question').filter(has=p.get_by_role('heading',name='Как поддержать C++ интерфейс позже?',exact=True))
        row.locator('.decision-recommended').get_by_role('button',name='Выбрать этот вариант',exact=True).click()
        e(p.locator('#notice')).to_contain_text('Вопрос решён')
        self.assertIn('Адаптер C++',self.view()['draft']['architecture']['interfaces'])
        p.reload();e(p.locator('#question-fields')).to_contain_text('Выбранные ответы и подходы (4)')
        folder=os.environ.get('DECISION_OPTIONS_EVIDENCE')
        if folder:
            target=Path(folder);target.mkdir(parents=True,exist_ok=True);p.screenshot(path=str(target/'decision-options.png'),full_page=True)
