"""Render the actual native result, no new model request or canonical mutation."""
import json,os,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sys.path.insert(0,str(ENGINE))
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_ph_lw_03_service import byte_snapshot
from playwright.sync_api import sync_playwright,expect
BASE=ROOT/'_scratch/document_analysis_clarity_20261112/native02'
value=json.loads((BASE/'interview.json').read_text('utf-8'));pid=value['project_id']
live=LiveServer(str(BASE));before=byte_snapshot(Path(live.service._registered(pid)[0]))
try:
    with sync_playwright() as play:
        browser=play.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1600,'height':1100});errors=[];dialogs=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('dialog',lambda dialog:(dialogs.append(dialog.message),dialog.dismiss()))
        page.goto(live.origin+'/');expect(page.locator('#connection-state')).to_have_text('Сервер готов')
        page.locator('.project-button').filter(has_text=pid).click();page.locator('[data-screen="interview"]').click()
        expect(page.locator('#interview-status')).to_have_text('Анализ получен. Предложения ещё не сохранены.')
        expect(page.locator('#reply-diff')).to_contain_text('Flutter/Dart')
        expect(page.locator('#reply-diff')).to_contain_text('План из документации')
        expect(page.locator('#reply-diff')).to_contain_text('Решения текущего этапа (2)')
        expect(page.locator('#cli-model-status')).to_contain_text('gpt-6-astra')
        expect(page.locator('#cli-model-status')).to_contain_text('Средняя')
        expect(page.locator('#answers-form')).to_be_hidden()
        assert page.locator('#reply-diff h4',has_text='Какой целевой уровень').inner_text().find('PROTOTYPE')==-1
        page.screenshot(path=str(BASE/'native-result-page.png'),full_page=True)
        page.locator('#reply-diff .analysis-stage').screenshot(path=str(BASE/'current-stage.png'))
        page.locator('#reply-diff .analysis-roadmap').first.screenshot(path=str(BASE/'current-roadmap.png'))
        assert not errors and not dialogs,(errors,dialogs)
        browser.close()
    assert byte_snapshot(Path(live.service._registered(pid)[0]))==before
    (OUT/'NATIVE_UI.json').write_text(json.dumps({'status':'PASS','model_requests':0,'canonical_unchanged':True,
        'errors':errors,'dialogs':dialogs,'actual_native_result':True,'viewport':[1600,1100]},indent=2)+'\n','utf-8')
finally:live.close()
