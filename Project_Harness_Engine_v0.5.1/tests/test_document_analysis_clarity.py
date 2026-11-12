"""Targeted v3 semantic projection, strict import and model-selection regressions."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from project_harness.local_web_analysis import normalize_analysis
from project_harness.local_web_exchange_contract import ExchangeError
from project_harness.local_web_drafts import DRAFT_FIELDS
from tests.test_cli_document_analysis import CliAnalysisTests
from tests.test_manual_analysis_archive import ManualArchiveTests,ManualArchiveBrowserTests


def analysis(ref):
    return {'summary':'Мобильная библиотека: читатель добавляет книги и видит список без интернета.',
        'current_stage':{'title':'Прототип основного сценария','goal':'Добавить книгу и найти её в локальном списке.',
            'basis':'Документация начинает с локального учёта; продажи отнесены к будущему.','source_refs':[ref]},
        'answers':[{'title':'Платформа и стек','answer':'Android, Flutter/Dart и SQLite предложены документом. Версии ещё не выбраны.',
            'status':'PROPOSED','source_refs':[ref]}],
        'roadmap':[{'title':'Локальный список книг','stage':'CURRENT','goal':'Проверить сценарий без сети.',
            'steps':['Создать форму книги с названием и автором.','Сохранить книгу локально.','Показать поиск по названию.'],
            'done_when':['После перезапуска сохранённая книга находится поиском.'],'source_refs':[ref]},
            {'title':'Платная синхронизация','stage':'FUTURE','goal':'Добавить подписку после проверки прототипа.',
            'steps':['Выбрать платёжный сервис и цену.'],'done_when':['Оплата проверена на тестовом аккаунте.'],'source_refs':[ref]}],
        'notes':['Документ содержит предложения, а не утверждённый релизный план.']}


class AnalysisContractTests(ManualArchiveTests):
    # Inherit setup/helpers, not unrelated old tests.
    test_single_archive_content_exact_binding_read_only_and_replay=None
    test_real_multipart_recombined_without_truncation_and_tamper_rejected=None
    test_stale_and_foreign_origin_rejected_without_download_or_mutation=None

    def reply(self):
        export=self.create();root,_=self.live.service._registered(self.pid)
        from project_harness.local_web_exchange import _load
        record=_load(root.parent/'exchange/exports'/export['exchange_id']/'record.json')
        value=deepcopy(record['return_skeleton']);ref=self.live.service.get_interview(self.pid)['documents'][0]['document_ref']
        value['analysis']=analysis(ref)
        value['questions']=[{'id':'ANDROID_MIN','field':'project.platforms','question':'Какая минимальная версия Android нужна для прототипа?',
            'why':'Влияет на выбор устройства для проверки.','stage':'CURRENT','blocking':True,'source_refs':[ref]},
            {'id':'PAYMENT_PRICE','field':'project.integrations','question':'Какую цену подписки проверить после прототипа?',
            'why':'Нужна при разработке оплаты.','stage':'FUTURE','blocking':False,'source_refs':[ref]}]
        value['project_input_draft']['project']['primary_outcome']='Читатель сохраняет книгу и находит её без интернета.'
        value['project_input_draft']['project']['users']=[{'name':'Читатель','need':'Найти сохранённую книгу'}]
        value['claims']=[{'field':f,'source_refs':[ref]} for f in ['project.primary_outcome','project.users']]
        from tests.test_document_decision_options import fixture_choices
        return fixture_choices(value)

    def preview(self,value):
        return self.live.service.preview_gpt_reply(self.pid,text=json.dumps(value,ensure_ascii=False),expected_fingerprint=self.live.service.get_interview(self.pid)['fingerprint'])

    def test_single_channel_dedupe_current_future_commit_and_reload_sources(self):
        value=self.reply();value['questions'].append({**value['questions'][0],'question':'Какую минимальную Android версию поддержать в прототипе?'})
        before=self.live.service.get_interview(self.pid)['draft']
        result=self.preview(value);self.assertEqual(result['status'],'PREVIEW',result)
        preview=result['preview'];self.assertEqual(len(preview['analysis']['questions']),2)
        unknowns=next(row['after'] for row in preview['diff'] if row['field']=='project.unknowns')
        self.assertEqual([q['blocking'] for q in unknowns],[True,False])
        self.assertEqual(self.live.service.get_interview(self.pid)['draft'],before)
        self.assertEqual(preview['analysis']['roadmap'][1]['stage'],'FUTURE')
        self.assertEqual(preview['claims'][0]['source_refs'],value['claims'][0]['source_refs'])
        self.assertEqual(sum(q['field']=='project.platforms' for q in preview['questions']),0)
        self.live.service.commit_gpt_reply(self.pid,preview['import_id'],preview_digest=preview['preview_digest'],expected_fingerprint=preview['binding']['fingerprint'])
        saved=self.live.service.get_interview(self.pid)
        self.assertEqual(saved['analysis']['summary'],value['analysis']['summary'])
        self.assertEqual(len(saved['draft']['project']['unknowns']),2)
        self.assertFalse(any(a['approved'] for a in saved['draft']['approvals'].values()))
        self.assertEqual(saved['draft']['planning']['work_packages'],before['planning']['work_packages'])
        self.assertEqual(saved['draft']['project']['users'][0]['need'],'Найти сохранённую книгу')

    def test_conflicting_scope_notes_refs_bindings_and_approvals_rejected(self):
        original=self.reply()
        cases=[]
        value=deepcopy(original);value['questions'][1]['blocking']=True;cases.append((value,'QUESTION_SCOPE_INVALID'))
        value=deepcopy(original);value['questions'].append({**value['questions'][0],'stage':'FUTURE','blocking':False});cases.append((value,'QUESTION_SCOPE_CONFLICT'))
        value=deepcopy(original);value['questions'][0]['question']='Тесты не выполнялись.';cases.append((value,'QUESTION_REQUIRED'))
        value=deepcopy(original);value['analysis']['answers'][0]['source_refs']=['UNKNOWN-SOURCE'];cases.append((value,'SOURCE_REF_UNKNOWN'))
        value=deepcopy(original);value['project_input_draft']['project']['unknowns']=['Новый дублирующий вопрос?'];value['claims'].append({'field':'project.unknowns','source_refs':[]});cases.append((value,'SINGLE_QUESTION_CHANNEL'))
        value=deepcopy(original);value['export_sha256']='sha256:'+'0'*64;cases.append((value,'BINDING_MISMATCH'))
        value=deepcopy(original);value['project_input_draft']['approvals']['project_definition']['approved']=True;cases.append((value,'APPROVAL_FORGERY'))
        for value,expected in cases:
            result=self.preview(value);self.assertEqual(result['status'],'REJECTED',result);self.assertEqual(result['error']['code'],expected,result)
        self.assertEqual(self.live.service.get_interview(self.pid)['imports'],[])

    def test_existing_user_uncertainty_preserved_and_future_does_not_block(self):
        value=self.reply();value['questions']=value['questions'][1:]
        result=self.preview(value);self.assertEqual(result['status'],'PREVIEW',result)
        self.assertNotIn('project.unknowns',result['preview']['readiness']['missing_fields'])
        original=value['project_input_draft'];original['project']['unknowns']=[{'question':'Как сохранить существующие данные?','blocking':True}]
        if value['envelope_version']>=4:
            value['questions'].append({**deepcopy(value['questions'][0]),'id':'EXISTING_GAP','field':'project.unknowns',
                'question':original['project']['unknowns'][0]['question'],'blocking':True,'stage':'CURRENT','existing_unknown_index':0})
        normalized,unknowns=normalize_analysis(value,deepcopy(original),set(value['claims'][0]['source_refs']),DRAFT_FIELDS)
        self.assertEqual(unknowns[0],original['project']['unknowns'][0]);self.assertEqual(len(unknowns),2)

    def test_export_supplies_exact_consumable_profile_refs(self):
        value=self.reply()
        data=self.live.service.read_gpt_export(self.pid,value['exchange_id'],'pack.md').decode('utf-8')
        payload=json.loads(data.split('## Exact payload\n\n',1)[1].split('## Return skeleton\n\n',1)[0])
        from project_harness.registry import known_profiles,load_registries
        self.assertEqual(set(payload['profile_catalog']['allowed_refs']),known_profiles(load_registries()))
        value['project_input_draft']['profile']['ref']='PRF-MOBILE-APPLICATION@1'
        self.assertIn(value['project_input_draft']['profile']['ref'],payload['profile_catalog']['allowed_refs'])
        value['claims'].append({'field':'profile.ref','source_refs':value['claims'][0]['source_refs']})
        result=self.preview(value);self.assertEqual(result['status'],'PREVIEW',result)


class ModelSelectionTests(CliAnalysisTests):
    # Only new behavior; base class is separately selected by the driver.
    def test_explicit_model_effort_snapshot_invalid_inputs_and_readonly_get(self):
        self.connect();code,_,value=self.live.request('POST','/api/cli/model',value={'model':'fixture-model','reasoning_effort':'high'})
        self.assertEqual(code,200,value)
        self.assertEqual(value['selection'],{'model':'fixture-model','reasoning_effort':'high'})
        for model,effort in [('cmd.exe','high'),('fixture-model','bogus'),(['fixture-model'],'high')]:
            self.assertEqual(self.live.request('POST','/api/cli/model',value={'model':model,'reasoning_effort':effort})[0],400)
        self.assertEqual(self.live.request('POST','/api/cli/model',value={'model':'fixture-model','reasoning_effort':'high'},headers={'Origin':'http://foreign.invalid'})[0],403)
        calls=len(self.fake.calls);self.live.request('GET','/api/cli');self.assertEqual(len(self.fake.calls),calls)
        _,_,job=self.start();result=self.wait(job['job_id']);self.assertEqual(result['state'],'SUCCEEDED',result)
        self.assertEqual(result['selection']['reasoning_effort'],'high')
        argv=self.fake.calls[-1];self.assertEqual(argv[argv.index('--model')+1],'fixture-model')
        self.assertIn('model_reasoning_effort="high"',argv)
        self.live.request('POST','/api/cli/model',value={'model':'fixture-model','reasoning_effort':'low'})
        self.assertEqual(self.live.request('GET',self.path+'/cli/analysis')[2]['selection']['reasoning_effort'],'high')
        self.assertEqual(self.start()[2]['job_id'],job['job_id'])
        self.live.service.cli_connection.models_path.write_text('{broken','utf-8')
        self.assertEqual(self.live.request('GET','/api/cli')[2]['error']['code'],'CLI_MODELS_INVALID')
        self.assertTrue(self.connect()['models'])


class AnalysisBrowserTests(AnalysisContractTests):
    open_page=ManualArchiveBrowserTests.open_page

    def test_preview_answers_plan_sources_consistent_status_then_typed_saved_answers(self):
        value=self.reply();preview=self.preview(value)['preview'];self.open_page();p=self.page;e=self.expect
        e(p.locator('#interview-status')).to_have_text('Анализ получен. Предложения ещё не сохранены.')
        e(p.locator('#interview-next')).to_contain_text('Сохранить предложения')
        e(p.locator('#answers-form')).to_be_hidden()
        e(p.locator('#reply-diff')).to_contain_text('Flutter/Dart и SQLite')
        e(p.locator('#reply-diff')).to_contain_text('Создать форму книги с названием и автором.')
        e(p.locator('#reply-diff')).to_contain_text('Основание:')
        self.assertEqual(p.locator('#reply-diff h4').filter(has_text=value['questions'][0]['question']).count(),1)
        e(p.locator('#reply-diff details').filter(has=p.locator('summary',has_text='Будущие этапы')).first).not_to_have_attribute('open','')
        p.locator('#commit-reply').click();e(p.locator('#interview-status')).to_have_text('Результат анализа сохранён в черновике.')
        e(p.locator('#saved-analysis')).to_contain_text('Flutter/Dart и SQLite')
        e(p.locator('#question-fields')).to_contain_text(value['questions'][0]['question'])
        p.locator('#known-answers').locator('..').locator('summary').click()
        row=p.locator('#known-answers .known-answer').filter(has=p.get_by_text('Пользователи и их задачи',exact=True))
        row.get_by_role('button',name='Изменить ответ').click()
        controls=row.locator('textarea');self.assertEqual(controls.count(),2)
        controls.first.fill('Владелец библиотеки');p.locator('#save-answers').click()
        e(p.locator('#notice')).to_contain_text('проверены и сохранены')
        saved=self.live.service.get_interview(self.pid)['draft']['project']['users'][0]
        self.assertEqual(saved,{'name':'Владелец библиотеки','need':'Найти сохранённую книгу'})
        folder=os.environ.get('ANALYSIS_CLARITY_EVIDENCE')
        if folder:
            target=Path(folder);target.mkdir(parents=True,exist_ok=True);p.screenshot(path=str(target/'saved-analysis.png'),full_page=True)

    def test_model_selection_in_browser_autosaves_and_survives_reload(self):
        from tests.test_cli_document_analysis import FixtureCli
        fake=FixtureCli();exe=self.base/'codex.exe';exe.write_bytes(b'MZ fixture')
        with patch('project_harness.local_web_cli.find_cli',lambda:exe),patch('project_harness.local_web_cli.invoke',fake):
            self.open_page();p=self.page;e=self.expect;p.locator('#cli-connect').click()
            e(p.locator('#cli-model')).to_have_value('fixture-model');p.locator('#cli-effort').select_option('high')
            e(p.locator('#cli-model-status')).to_contain_text('Высокая');e(p.locator('#cli-effort')).to_be_enabled()
            p.reload();e(p.locator('#cli-effort')).to_have_value('high')
            e(p.locator('#cli-connect-label')).to_have_text('Подключено');e(p.locator('#cli-connection-help')).to_be_hidden()

    def test_current_technology_question_has_typed_answer_and_resolution(self):
        value=self.reply();value['questions'][0].update(field='technology.selections',id='TECH_VERSION',
            question='Какую версию Flutter использовать для прототипа?')
        result=self.preview(value)['preview']
        self.live.service.commit_gpt_reply(self.pid,result['import_id'],preview_digest=result['preview_digest'],expected_fingerprint=result['binding']['fingerprint'])
        self.open_page();p=self.page;e=self.expect
        row=p.locator('#question-fields .question').filter(has=p.locator('h3',has_text='Какую версию Flutter использовать для прототипа?'))
        row.locator('.custom-decision > summary').click()
        row.locator('.custom-decision details > summary').click()
        row.get_by_role('button',name='Добавить запись',exact=True).click()
        controls=row.locator('.answer-field textarea');self.assertEqual(controls.count(),4)
        for label,text in {'Назначение':'Мобильный интерфейс','Технология':'Flutter',
            'Версия или диапазон версий':'3.0 (синтетическая версия проверки)','Обоснование':'Согласованный ответ теста'}.items():
            row.get_by_label(label,exact=True).fill(text)
        row.get_by_role('button',name='Сохранить свой ответ',exact=True).click()
        e(p.locator('#notice')).to_contain_text('Вопрос решён')
        e(row).to_have_count(0)
        saved=self.live.service.get_interview(self.pid)
        self.assertEqual(saved['draft']['technology']['selections'][0]['technology'],'Flutter')
        self.assertFalse(any(q['id']=='TECH_VERSION' for q in saved['analysis']['questions']))
