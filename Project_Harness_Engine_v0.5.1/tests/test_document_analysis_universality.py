"""Cross-domain document transport, normalization and schema-driven UI only."""
from copy import deepcopy
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from project_harness.local_web_analysis import normalize_analysis,text_key
from project_harness.local_web_drafts import DRAFT_FIELDS
from project_harness.local_web_exchange_contract import digest
from project_harness.project_input import load_project_input_schema
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_manual_analysis_archive import contents,ManualArchiveBrowserTests


CORPUS=[
 {'name':'Compiler library','documents':[('not-a-concept.MD','# ABI compatibility\nExisting C++ and C# bindings use different APIs. RELEASE is a literal build target. Preserve case: MB is not Mb.\n')],
  'summary':'Действующая библиотека с отдельными C++ и C# интерфейсами.', 'stage':'Миграция ABI'},
 {'name':'Data laboratory','documents':[('研究/計画.md','# Данные\nПакет исследует качество открытых наборов данных. Язык реализации ещё не выбран.\n'),
    ('notes/measurement.md','# Методика\nСравнить полноту и воспроизводимость. Следующий этап — воспроизводимый эксперимент.\n')],
  'summary':'Исследование качества наборов данных без выбранного стека.','stage':'Воспроизводимый эксперимент'},
 {'name':'Public web service','documents':[('z-last.md','# Миграция\nСервис уже работает в production. Текущая цель — перенос API без остановки. Прототип не является текущей работой.\n'),
    ('nested/без-префикса.md','# Принятый стек\nGo и PostgreSQL выбраны в этом проекте. Платёжный callback нужен именно на текущем этапе.\n'),
    ('a-first.md','# Следующий цикл\nИзменение дизайна отложено. Порядок имён файлов не задаёт приоритет требований.\n')],
  'summary':'Миграция действующего сервиса Go/PostgreSQL.','stage':'Перенос API'},
 {'name':'Offline exhibition','documents':[(f'任意/часть-{i}.md',f'# Экспозиция {i}\nКаталог музейных экспонатов: зал {i}, подписи, доступность. Это организационный проект; программный стек не задан.\n') for i in range(6)],
  'summary':'Организационный проект музейной экспозиции.','stage':'Этап не определён'},
]


def synthetic_analysis(ref,summary='Краткое исходное описание проекта.',stage='Этап не определён'):
    return {'summary':summary,'current_stage':{'title':stage,'goal':'Уточнить недостающие сведения, если они нужны для продолжения.',
        'basis':'Рекомендация по предоставленному описанию, без назначения Stage.','source_refs':[ref]},
        'answers':[{'title':'Сведения из источника','answer':summary,'status':'DOCUMENTED','source_refs':[ref]}],
        'roadmap':[],'notes':['Подробный план в исходном документе отсутствует.']}


class UniversalityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='document-universality-');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.live=LiveServer(self.temp.name);self.addCleanup(self.live.close)
        self.pid=self.live.create('universal-create-00001');self.path='/api/projects/'+self.pid

    def upload_corpus(self,case,pid=None):
        pid=pid or self.pid
        if len(case['documents'])==1:
            documents=[(Path(case['documents'][0][0]).name,case['documents'][0][1].encode('utf-8-sig'))]
        else:
            stream=BytesIO()
            with ZipFile(stream,'w') as archive:
                for name,text in reversed(case['documents']):archive.writestr(name,text.encode('utf-8'))
            documents=[('произвольный-архив.zip',stream.getvalue())]
        self.assertEqual(self.live.upload(pid,documents)[0],200)

    def pack(self,pid=None):
        pid=pid or self.pid;view=self.live.service.get_interview(pid)
        export=self.live.service.create_analysis_export(pid,expected_fingerprint=view['fingerprint'],idempotency_key='universal-export-key-0001')
        archive=contents(self.live.service.read_gpt_export_archive(pid,export['exchange_id']))
        payload=json.loads(archive['pack.md'].split('## Exact payload\n\n',1)[1].split('## Return skeleton\n\n',1)[0])
        reply=json.loads(archive['pack.md'].split('## Return skeleton\n\n',1)[1])
        reply['analysis']=synthetic_analysis(view['documents'][0]['document_ref'])
        return view,payload,reply

    def commit(self,reply):
        from tests.test_document_decision_options import fixture_choices
        fixture_choices(reply)
        view=self.live.service.get_interview(self.pid)
        result=self.live.service.preview_gpt_reply(self.pid,text=json.dumps(reply,ensure_ascii=False),expected_fingerprint=view['fingerprint'])
        self.assertEqual(result['status'],'PREVIEW',result);preview=result['preview']
        self.live.service.commit_gpt_reply(self.pid,preview['import_id'],preview_digest=preview['preview_digest'],expected_fingerprint=view['fingerprint'])

    def test_arbitrary_names_counts_domains_exact_text_and_project_isolation(self):
        for i,case in enumerate(CORPUS):
            with self.subTest(case=case['name']):
                pid=self.pid if i==0 else self.live.create('universal-create-corpus-'+str(i))
                self.upload_corpus(case,pid);view,payload,reply=self.pack(pid)
                self.assertEqual(len(payload['documents']),len(case['documents']))
                self.assertEqual({d['text'] for d in payload['documents']},{text for _,text in case['documents']})
                self.assertEqual(payload['project_ref'],pid)
                self.assertEqual(reply['export_sha256'],digest(payload))
                self.assertEqual(payload['project_input_draft']['technology']['selections'],[])
                self.assertIsNone(payload['project_input_draft']['implementation']['target_level'])
                self.assertEqual(view['editor_schema'],load_project_input_schema())
                for document in payload['documents']:
                    self.assertTrue(any(document['source_relative_path'].endswith(Path(name).name) for name,_ in case['documents']))
                reply['analysis']=synthetic_analysis(view['documents'][0]['document_ref'],case['summary'],case['stage'])
                result=self.live.service.preview_gpt_reply(pid,text=json.dumps(reply,ensure_ascii=False),expected_fingerprint=view['fingerprint'])
                self.assertEqual(result['status'],'PREVIEW',result)
                self.assertEqual(result['preview']['analysis']['current_stage']['title'],case['stage'])
                self.assertEqual(result['preview']['analysis']['roadmap'],[])
                self.assertEqual(self.live.service.get_interview(pid)['draft'],view['draft'])
        first=self.live.service.get_interview(self.pid)
        self.assertEqual(len(first['documents']),1)
        self.assertEqual(first['imports'][-1]['analysis']['summary'],CORPUS[0]['summary'])

    def test_distinct_code_units_unicode_and_repeated_topic_are_not_lost(self):
        self.upload_corpus(CORPUS[0]);view,_,reply=self.pack()
        phrases=['Использовать C++?','Использовать C#?','Использовать C?',
                 'Лимит 1 MB?','Лимит 1 Mb?','Что обозначает x²?','Что обозначает x2?','どの形式を使用しますか？']
        questions=[{'id':'TOPIC_'+str(i),'field':'project.constraints.mandatory','question':text,
                    'why':'Требуется отдельное решение.','stage':'CURRENT','blocking':True,'source_refs':[]} for i,text in enumerate(phrases)]
        reply['questions']=questions+[dict(questions[0],id='SAME_TEXT',question='  Использовать   C++?  '),
            dict(questions[1],question='Выбираем C# для интерфейса?')]
        analysis,unknowns=normalize_analysis(reply,view['draft'],{d['document_ref'] for d in view['documents']},DRAFT_FIELDS)
        self.assertEqual(len(analysis['questions']),len(phrases));self.assertEqual(len(unknowns),len(phrases))
        self.assertEqual({u['question'] for u in unknowns},set(phrases))
        self.assertNotEqual(text_key('MB?'),text_key('Mb?'))


class UniversalityBrowserTests(UniversalityTests):
    open_page=ManualArchiveBrowserTests.open_page

    def test_generic_structured_answers_from_schema_and_literal_identifiers(self):
        self.upload_corpus(CORPUS[0]);view,_,reply=self.pack()
        fields=[('project.users','Кто использует библиотеку C++ и C#?'),
            ('architecture.components','Какие компоненты входят в библиотеку?'),
            ('project.success_criteria','Как проверить совместимость?'),
            ('technology.selections','Что означает API RELEASE в выбранных технологиях?')]
        reply['questions']=[{'id':'EDIT_'+str(i),'field':field,'question':question,'why':'Уточнить исходное описание.',
            'stage':'CURRENT','blocking':True,'source_refs':[]} for i,(field,question) in enumerate(fields)]
        self.commit(reply);self.open_page();p=self.page;e=self.expect
        values=[{'Название':'Разработчик','Задача пользователя':'Использовать оба интерфейса'},
            {'Название':'ABI adapter','За что отвечает':'Совместимость C++ и C#'},
            {'Критерий':'Интерфейсы совместимы','Как проверить':'Сравнить результаты вызовов'},
            {'Назначение':'Нативный интерфейс','Технология':'C++','Версия или диапазон версий':'C++20','Обоснование':'Указано в документации'}]
        for (_,question),data in zip(fields,values):
            row=p.locator('#question-fields .question').filter(has=p.get_by_role('heading',name=question,exact=True))
            row.locator('.custom-decision > summary').click()
            row.locator('.custom-decision details > summary').click()
            row.get_by_role('button',name='Добавить запись',exact=True).click()
            for label,value in data.items():row.get_by_label(label,exact=True).fill(value)
            row.get_by_role('button',name='Сохранить свой ответ',exact=True).click();e(p.locator('#notice')).to_contain_text('Вопрос решён')
            e(row).to_have_count(0)
        draft=self.live.service.get_interview(self.pid)['draft']
        self.assertEqual(draft['project']['users'][0]['need'],'Использовать оба интерфейса')
        self.assertEqual(draft['architecture']['components'][0]['responsibility'],'Совместимость C++ и C#')
        self.assertEqual(draft['project']['success_criteria'][0]['verification'],'Сравнить результаты вызовов')
        self.assertEqual(draft['technology']['selections'][0]['technology'],'C++')
        self.assertEqual(draft['technology']['selections'][0]['version_constraint'],'C++20')
        self.assertEqual(draft['architecture']['interfaces'],[],'Unedited lists remain unchanged')
        folder=os.environ.get('UNIVERSALITY_EVIDENCE')
        if folder:
            target=Path(folder);target.mkdir(parents=True,exist_ok=True);p.screenshot(path=str(target/'generic-answers.png'),full_page=True)

    def test_missing_plan_empty_lists_schema_enums_and_inert_source_text(self):
        self.upload_corpus(CORPUS[-1]);view,_,reply=self.pack()
        reply['analysis']['summary']='Организация экспозиции. <img src=x onerror="window.unexpected=true">'
        reply['analysis']['answers']=[];self.commit(reply);self.open_page();p=self.page;e=self.expect
        e(p.locator('#saved-analysis')).to_contain_text('План работ в документации не описан')
        self.assertEqual(p.locator('#saved-analysis img').count(),0)
        self.assertIsNone(p.evaluate('window.unexpected'))
        self.assertEqual(p.locator('#saved-analysis .analysis-roadmap').count(),0)
        select=p.locator('#answer-implementation-target_level')
        self.assertEqual(select.locator('option').evaluate_all('(items)=>items.map(i=>i.value).filter(Boolean)'),
            [v for v in load_project_input_schema()['$defs']['implementation']['properties']['target_level']['enum'] if v is not None])
