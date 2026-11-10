"""Targeted manual ZIP content/binding/GET/download checks, no model calls."""
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from project_harness.local_web_exchange_contract import digest
from tests.test_ph_lw_03_service import byte_snapshot
from tests.test_ph_lw_04_05_acceptance import LiveServer


def contents(data):
    with ZipFile(BytesIO(data)) as archive:
        assert archive.testzip() is None
        assert archive.namelist() == ['ИНСТРУКЦИЯ.md', 'pack.md']
        assert all(not info.is_dir() and info.external_attr >> 16 == 0o100600 for info in archive.infolist())
        return {name: archive.read(name).decode('utf-8') for name in archive.namelist()}


class ManualArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='manual-analysis-zip-');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.live=LiveServer(self.temp.name);self.addCleanup(self.live.close)
        self.pid=self.live.create('manual-archive-create-001');self.path='/api/projects/'+self.pid
        self.assertEqual(self.live.upload(self.pid,[('Требования.md','# Учёт домашней библиотеки'.encode())])[0],200)

    def create(self,key='manual-archive-export-001'):
        view=self.live.request('GET',self.path+'/interview')[2]
        self.request={'expected_fingerprint':view['fingerprint'],'idempotency_key':key}
        code,_,value=self.live.request('POST',self.path+'/analysis/package',value=self.request)
        self.assertEqual(code,201,value)
        return value

    def url(self,export):return self.path+'/gpt/exports/'+export['exchange_id']+'/archive.zip'

    def test_single_archive_content_exact_binding_read_only_and_replay(self):
        export=self.create();before=byte_snapshot(self.base)
        code,headers,data=self.live.request('GET',self.url(export))
        self.assertEqual(code,200);self.assertEqual(headers['Content-Type'],'application/zip')
        self.assertIn('harness-analysis.zip',headers['Content-Disposition'])
        self.assertIn('no-store',headers['Cache-Control'])
        result=contents(data);self.assertIn('Прочитай pack.md целиком',result['ИНСТРУКЦИЯ.md'])
        old=self.live.request('GET',self.path+'/gpt/exports/'+export['exchange_id']+'/pack.md')[2]
        self.assertEqual(result['pack.md'],old.decode('utf-8')[len(export['prompt']+'\n\n'):])
        payload=json.loads(result['pack.md'].split('## Exact payload\n\n',1)[1].split('## Return skeleton\n\n',1)[0])
        skeleton=json.loads(result['pack.md'].split('## Return skeleton\n\n',1)[1])
        self.assertEqual(digest(payload),export['export_sha256'])
        self.assertEqual(skeleton['exchange_id'],export['exchange_id'])
        self.assertEqual(skeleton['export_sha256'],export['export_sha256'])
        self.assertEqual(byte_snapshot(self.base),before,'ZIP GET changed stored state')
        self.assertEqual(self.live.request('GET',self.url(export))[2],data)
        again=self.live.request('POST',self.path+'/analysis/package',value=self.request)[2]
        self.assertEqual(again['exchange_id'],export['exchange_id'])
        self.assertEqual(self.live.request('GET',self.url(again))[2],data)

    def test_real_multipart_recombined_without_truncation_and_tamper_rejected(self):
        large='\n'.join(f'Требование {i}: хранить название и автора книги; поиск по названию.' for i in range(6000))
        self.assertEqual(self.live.upload(self.pid,[('Большой документ.md',large.encode())])[0],200)
        export=self.create();self.assertEqual(export['files'][0]['name'],'index.md')
        pieces=[self.live.request('GET',self.path+'/gpt/exports/'+export['exchange_id']+'/'+f['name'])[2]
                for f in export['files'][1:]]
        expected=b''.join(part.split(b'\n\n',1)[1] for part in pieces).decode('utf-8')
        result=contents(self.live.request('GET',self.url(export))[2])
        self.assertEqual(result['pack.md'],expected)
        payload=json.loads(result['pack.md'].split('## Exact payload\n\n',1)[1].split('## Return skeleton\n\n',1)[0])
        self.assertEqual(digest(payload),export['export_sha256'])
        self.assertIn(large,[d['text'] for d in payload['documents']])
        root,_=self.live.service._registered(self.pid)
        part=root.parent/'exchange/exports'/export['exchange_id']/export['files'][1]['name']
        part.write_bytes(b'changed')
        before=byte_snapshot(self.base);code,headers,result=self.live.request('GET',self.url(export))
        self.assertEqual(code,400,result);self.assertNotEqual(headers['Content-Type'],'application/zip')
        self.assertEqual(result['status'],'FAILED');self.assertEqual(byte_snapshot(self.base),before)

    def test_stale_and_foreign_origin_rejected_without_download_or_mutation(self):
        export=self.create();before=byte_snapshot(self.base)
        self.assertEqual(self.live.request('GET',self.url(export),headers={'Origin':'https://foreign.invalid'})[0],403)
        self.assertEqual(byte_snapshot(self.base),before)
        self.assertEqual(self.live.upload(self.pid,[('Дополнение.md',b'# New source revision')])[0],200)
        before=byte_snapshot(self.base);code,_,result=self.live.request('GET',self.url(export))
        self.assertEqual(code,409,result);self.assertEqual(result['error']['code'],'STALE_EXCHANGE')
        self.assertEqual(byte_snapshot(self.base),before)


class ManualArchiveBrowserTests(unittest.TestCase):
    setUp=ManualArchiveTests.setUp
    def open_page(self):
        from playwright.sync_api import sync_playwright,expect
        self.expect=expect;self.play=sync_playwright().start();self.addCleanup(self.play.stop)
        self.browser=self.play.chromium.launch(channel='msedge',headless=True);self.addCleanup(self.browser.close)
        self.page=self.browser.new_page(viewport={'width':1600,'height':1100})
        self.errors=[];self.dialogs=[];self.downloads=[];self.posts=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        self.page.on('dialog',lambda dialog:(self.dialogs.append(dialog.message),dialog.dismiss()))
        self.page.on('download',lambda download:self.downloads.append(download))
        self.page.on('request',lambda request:self.posts.append(request) if request.method=='POST' and request.url.endswith('/analysis/package') else None)
        self.page.goto(self.live.origin+'/');expect(self.page.locator('#connection-state')).to_have_text('Сервер готов')
        self.page.locator('.project-button').filter(has_text=self.pid).click()
        self.page.locator('[data-screen="interview"]').click()
        expect(self.page.locator('#review-export')).to_be_visible()
        self.addCleanup(lambda:self.assertEqual(self.errors,[]));self.addCleanup(lambda:self.assertEqual(self.dialogs,[]))

    def test_one_click_zip_download_without_history_and_reply_still_previews(self):
        self.open_page();p=self.page;e=self.expect
        self.assertEqual(p.locator('#export-history').count(),0)
        self.assertEqual(p.get_by_role('button',name='Копировать инструкцию',exact=True).count(),0)
        with p.expect_download() as downloaded:p.locator('#review-export').click()
        download=downloaded.value;self.assertEqual(download.suggested_filename,'harness-analysis.zip')
        result=contents(Path(download.path()).read_bytes())
        e(p.locator('#notice')).to_contain_text('скачивание началось')
        e(p.locator('#review-export')).to_be_enabled()
        self.assertEqual(len(self.posts),1);self.assertEqual(len(self.downloads),1)
        skeleton=json.loads(result['pack.md'].split('## Return skeleton\n\n',1)[1])
        payload=json.loads(result['pack.md'].split('## Exact payload\n\n',1)[1].split('## Return skeleton\n\n',1)[0])
        skeleton['project_input_draft']['project']['primary_outcome']='Цель из ответа на ZIP'
        skeleton['claims']=[{'field':'project.primary_outcome','source_refs':[payload['documents'][0]['document_ref']]}]
        p.locator('#gpt-reply').fill(json.dumps(skeleton,ensure_ascii=False));p.locator('#preview-reply').click()
        e(p.locator('#preview-summary')).to_contain_text('Изменений:')
        self.assertNotEqual(self.live.service.get_interview(self.pid)['draft']['project']['primary_outcome'],'Цель из ответа на ZIP')
        folder=os.environ.get('MANUAL_ARCHIVE_EVIDENCE')
        if folder:
            target=Path(folder);target.mkdir(parents=True,exist_ok=True)
            download.save_as(str(target/'harness-analysis.zip'))
            for name,text in result.items():(target/name).write_text(text,'utf-8')
            p.locator('#analysis-options').screenshot(path=str(target/'one-click-manual-card.png'))

    def test_download_error_and_wrong_mime_are_inline_without_extra_download(self):
        self.open_page();p=self.page;e=self.expect
        for status,content_type,body,message in [
            (409,'application/json',json.dumps({'error':{'code':'STALE_EXCHANGE','message_ru':'Документы изменились. Сформируйте пакет заново.'}},ensure_ascii=False),'Документы изменились'),
            (200,'text/plain','not a zip','Сервер не вернул ZIP-архив')]:
            p.route('**/archive.zip',lambda route,request,s=status,c=content_type,b=body:route.fulfill(status=s,content_type=c,body=b))
            p.locator('#review-export').click();e(p.locator('#notice')).to_contain_text(message)
            e(p.locator('#review-export')).to_be_enabled();self.assertEqual(self.downloads,[])
            p.unroute('**/archive.zip')
        self.assertEqual(len(self.posts),2,'No automatic mutation replay')
