"""Publish reviewable Windows evidence and independent PH-LW-12 verdicts."""
from collections import Counter
import hashlib,json,re,sys
from pathlib import Path
from package_acceptance import ROOT,ENGINE,DOCS,files
from finalize_evidence import sanitize as base_sanitize

S=ROOT/'_scratch/ph_lw_12';W=ROOT/'_workspace/PH_LW_12';O=ENGINE/'PH_LW_12_LOGS'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sanitize(value):
    value=base_sanitize(value)
    value=re.sub(r'(harness_local_session=)[A-Za-z0-9_-]+',r'\1<REDACTED>',value)
    value=re.sub(r'(?i)((?:x-csrf-token|"csrf")\s*[:=]\s*"?)[A-Za-z0-9_-]{20,}',r'\1<REDACTED>',value)
    return value
def save(p,value):
    p.parent.mkdir(exist_ok=True,parents=True)
    p.write_text(sanitize(json.dumps(value,ensure_ascii=False,indent=2))+'\n','utf-8')
def outcomes(path):
    result={};text=path.read_text('utf-8',errors='replace')
    # unittest emits a test docstring on a second line before the dots.
    starts=list(re.finditer(r'(?m)^test[^\n]*?\(([^)]+)\)(?: \.\.\. |\n[^\n]* \.\.\. )',text))
    for i,start in enumerate(starts):
        segment=text[start.end():starts[i+1].start() if i+1<len(starts) else len(text)]
        found=re.search(r'(?m)^(ok|FAIL|ERROR|skipped [^\n]*)\s*$',segment)
        if not found:continue
        ident,status=start[1],found[1]
        result[ident]={'status':'PASS' if status=='ok' else 'SKIP' if status.startswith('skipped') else status,
                       'reason':status if status.startswith('skipped') else None,'raw_log':path.relative_to(ROOT).as_posix()}
    return result
def completed(path):
    if not path.exists():return False
    r=read(path);return r.get('status')=='PASS' and r.get('process_status','PASS')=='PASS'

def main():
    discovery=read(W/'DISCOVERY.json');current={r['id']:{'status':r['platform_status'] if r['platform_status']=='NOT RUN' else 'NOT RUN',
        'reason':r['reason'] or 'No completed final applicable run yet'} for r in discovery['methods']}
    # Exact Python/runtime modules are unchanged across the recorded UI-only
    # refresh delta. Completed backend runs retain their byte bindings.
    for p in sorted((S/'wheel').glob('*.run.json')):
        if completed(p):current.update(outcomes(p.with_suffix('').with_suffix('.log')))
    for p in sorted((S/'source-layout-rechecks').glob('test_*.json')):
        if p.name.endswith('.run.json') or p.name.endswith('.process.json'):continue
        if read(p).get('status')=='PASS' and p.with_suffix('.log').exists():current.update(outcomes(p.with_suffix('.log')))
    final_names=['maturity-final','exchange-http-final','lifecycle-http-final','lifecycle-service-final',
                 'wheel-browser-final','source-final-regressions']
    for name in final_names:
        if completed(S/(name+'.run.json')):current.update(outcomes(S/(name+'.log')))
    delivery={}
    for name in ['installed-extended-final','installed-extended-focus3','installed-no-doc-final','installed-maintenance-final']:
        if (S/(name+'.run.json')).exists():delivery.update(outcomes(S/name/'browser.log'))
    delivery_counts=dict(Counter(row['status'] for row in delivery.values()))
    expected={r['id'] for r in discovery['methods']};current={k:v for k,v in current.items() if k in expected}
    native={r['id'] for r in discovery['methods'] if r['platform_status']=='SCHEDULED_WINDOWS'}
    missing=sorted(k for k in native if current[k]['status'] not in {'PASS','SKIP'})
    counts=dict(Counter(current[k]['status'] for k in native))
    skips=[{'test':k,**current[k]} for k in sorted(native) if current[k]['status']=='SKIP']
    verdict={'PH-LW-12':'NO-GO','LOCAL_WEB_MANUAL':'NO-GO','AUTOMATIC_EXECUTOR':'NO-GO; disabled; previous verdict',
        'v0.5.1':'NO-GO / NOT RELEASED','platform':'Windows-only per explicit user decision',
        'accepted_not_run':['clean Windows without developer runtimes','physical offline','real disk-full','actual Unicode username'],
        'new_unaccepted_blockers':[{'id':'LW12-DEEP-APPDATA-INTAKE','status':'OPEN',
            'summary':'Deep app-data root: public intake creation fails at intake.py:157 with WinError 206; cleanup at local_web_sources_service.py:113 masks it with WinError 145. No catalog registration; partial app-owned session remains.',
            'evidence':'ADDITIONAL_PATH_STRESS.json; installed-basic-final/RESULT.json'},
            {'id':'LW12-MAINTENANCE-RESULT-CONFLICT','status':'OPEN',
             'summary':'Actual installed EXE maintenance result-upload returns HTTP 409 OPERATION_CONFLICT after navigation/refresh; result stays NOT_RECEIVED. Own UI read overlap is suspected; exact lock holder was not traced.',
             'evidence':'installed-maintenance-final/task-responses-maintenance.json; browser.log; ui-test_maintenance_task_completion_through_browser.json'},
            {'id':'LW12-PROJECT-LIST-PROJECTION','status':'OPEN / OBSERVED UI INCONSISTENCY',
             'summary':'After successful MVP to RELEASE, main lifecycle shows STAGE_PLANNING_REQUIRED while project-list card still shows TARGET_LEVEL_REACHED. Screenshot observation; likely stale state.projects cache, not a newly asserted test.',
             'evidence':'UI_PROJECTION_OBSERVATION.json; installed-extended-focus3/screenshots/10/mvp-to-release.png'}],
        'windows_discovery_methods':len(native),'windows_method_counts':counts,'windows_unclosed_methods':missing,
        'non_windows_methods_not_run':len(expected-native),'skips':skips,'zip_created':False,
        'system_settings_changed':False,'new_visible_browser_windows':False,
        'installed_extended_current_methods':delivery,'installed_extended_current_counts':delivery_counts}
    http04=[k for k in native if k.startswith(('tests.test_ph_lw_04_http.','tests.test_ph_lw_04_05_acceptance.'))]
    verdict['PH-LW-04']='GO in tested Windows scope' if http04 and all(current[k]['status']=='PASS' for k in http04) else 'NO-GO / incomplete current Windows coverage'
    verdict['PH-LW-05']='NO-GO for deep app-data intake; baseline source-import coverage recorded separately'
    if missing:verdict['new_unaccepted_blockers'].append({'id':'LW12-WINDOWS-MATRIX','status':'OPEN','methods':missing})
    critical_runs={name:(read(S/(name+'.run.json'))['status'] if (S/(name+'.run.json')).exists() else 'NOT RUN')
        for name in ['installed-basic-supported','installer-recovery-final','installed-extended-final',
                     'installed-extended-focus3','installed-no-doc-final','installed-maintenance-final',*final_names]}
    verdict['final_run_statuses']=critical_runs
    if any(status!='PASS' for status in critical_runs.values()):
        verdict['new_unaccepted_blockers'].append({'id':'LW12-DELIVERY-RUNS','status':'OPEN',
            'runs':{name:status for name,status in critical_runs.items() if status!='PASS'}})
    save(O/'VERDICTS.json',verdict);save(O/'METHOD_RESULTS.json',{'scope':'Windows-only current discovery; completed applicable runs with explicit supersession','methods':current})
    save(O/'BUILD_PROVENANCE.json',read(W/'RUNTIME_FREEZE.json'))
    save(O/'PLATFORM_SCOPE.json',{'platform':'Windows only','user_instruction':'мы не используем линукс нигде',
        'prior_linux_attempt':'Stopped at user instruction; runner removed; no Linux result credited; raw private diagnostic omitted from distribution',
        'future_linux_jobs_authorized':False})
    selected=[]
    selected += [p for p in S.iterdir() if p.is_file() and p.suffix in {'.log','.json'} and 'linux' not in p.name.lower()]
    for folder in ['source','wheel','wheel-preliminary','wheel-before-controls','source-layout-rechecks','final-screenshots']:
        selected += [p for p in (S/folder).rglob('*') if p.is_file() and p.suffix in {'.log','.json','.png'}]
    for folder in ['installed-extended','installed-final-focus','installed-final-focus2','installed-basic-final',
                   'installed-basic-supported','installer-recovery-final','installed-extended-final','installed-extended-focus3',
                   'installed-no-doc-final','installed-maintenance-final']:
        base=S/folder
        selected += [p for p in base.glob('*') if p.is_file() and p.suffix in {'.log','.json','.png','.txt'}]
        selected += [p for p in (base/'screenshots').rglob('*.png')]
        selected += [p for d in base.glob('operations-*') for p in d.glob('*.json')]
    index=[]
    for p in sorted(set(selected)):
        rel=p.relative_to(S);target=O/rel;target.parent.mkdir(parents=True,exist_ok=True)
        if p.suffix=='.png':target.write_bytes(p.read_bytes())
        else:target.write_text(sanitize(p.read_text('utf-8-sig',errors='replace')),'utf-8')
        index.append({'raw_source':p.relative_to(ROOT).as_posix(),'file':rel.as_posix(),'raw_sha256':sha(p),'published_sha256':sha(target)})
    for name in ['INPUT_BASELINE.json','INPUT_FILE_HASHES.json','DISCOVERY.json','RUNTIME_FREEZE.json','PRE_REFRESH_RUNTIME_FREEZE.json',
                 'REFRESH_DELTA.json','INTEGRITY.json','ADVANCED_FIXTURES.json','MATURITY_SETUP_CACHE.json','ADDITIONAL_PATH_STRESS.json',
                 'PATH_IO_EXPERIMENT_REVERTED.json','ADDITIONAL_PATH_IO_AFTER.json','ADDITIONAL_PATH_IO_AFTER2.json',
                 'TEST_RUNNER_FREEZE.json','FINAL_ACCEPTANCE_RUNNER_VERSION.json','MAINTENANCE_RUNNER_VERSION.json',
                 'VISUAL_QA.json','UI_PROJECTION_OBSERVATION.json','RUNNER_VERSIONS.json']:
        p=W/name
        if p.exists():save(O/name,read(p))
    save(O/'EVIDENCE_INDEX.json',index)
    for p in W.glob('RUNNER_*.py'):
        target=O/'runner-sources'/(p.stem+'.txt');target.parent.mkdir(exist_ok=True)
        target.write_text(sanitize(p.read_text('utf-8')),'utf-8')
    tokens=[]
    pattern=re.compile(r'harness_local_session=(?!<REDACTED>)[A-Za-z0-9_-]{20,}|#bootstrap=(?!<REDACTED>)[A-Za-z0-9_-]{24,}')
    for p in O.rglob('*'):
        if p.is_file() and p.suffix in {'.log','.json','.txt'} and pattern.search(p.read_text('utf-8',errors='replace')):
            tokens.append(p.relative_to(O).as_posix())
    save(O/'PUBLISHED_LOG_SCAN.json',{'status':'FAIL' if tokens else 'PASS','live_token_pattern_matches':tokens,
        'scope':'Published PH-LW-12 textual evidence only; exact bootstrap/session patterns plus redaction. Binary/screenshot semantic DLP is not claimed.'})
    assert not tokens,tokens
    controls=read(ENGINE/'src/project_harness/resources/local_web/control_map_v1.json')['commands']
    disabled={'doctor','validate-handoff','executor-doctor','execute-current','demo'}
    mapping={'start-intake':'#create-intake / #create-no-docs','check-intake':'#save-answers / #check-answers',
        'prepare':'#prepare-project','validate-project':'#action-list','status':'#project-details','next':'#task-next',
        'verify':'#task-verify','complete':'#task-complete','block':'#task-block','resume':'#task-resume',
        'stage-status':'#navigation gates / stage-status button','migrate-project':'prepare-migration form'}
    control_rows=[]
    for r in controls:
        control_rows.append({'id':r['id'],'cli':r['cli'],'status':'TRUTHFUL_DISABLED' if r['cli'] in disabled else 'AVAILABLE_WITH_CORE_PRECONDITIONS',
            'ui':mapping.get(r['cli'],'#lifecycle-actions / schema-driven reviewed form'),
            'reason':'Automatic executor remains disabled' if r['cli'] in {'executor-doctor','execute-current'} else
                     'Current UI explicitly states operation is not implemented' if r['cli'] in disabled else None,
            'evidence':'source-final-regressions.log; wheel-browser-final.log; installed-extended-final/browser.log; current native method matrix'})
    save(O/'CONTROL_MATRIX.json',{'controls':control_rows,'operation_log_export':'Explicit disabled button and truthful reason; per-operation result panels exist'})
    def prefix_status(*prefixes):
        values=[current[k]['status'] for k in native if k.startswith(prefixes)]
        if values and all(v in {'PASS','SKIP'} for v in values):return 'PASS_WITH_EXPLICIT_SKIPS' if 'SKIP' in values else 'PASS'
        return 'FAIL' if any(v in {'FAIL','ERROR'} for v in values) else 'NOT RUN / incomplete'
    basic_status=critical_runs['installed-basic-supported']
    extended_status=critical_runs['installed-extended-final']
    status_map={'LW-E01':'NOT RUN — ACCEPTED LIMITATION','LW-E02':'FAIL — NEW DEEP APP-DATA BOUNDARY',
        'LW-E03':basic_status,'LW-E04':basic_status,'LW-E05':extended_status,
        'LW-E06':prefix_status('tests.test_ph_lw_06'),'LW-E07':basic_status,'LW-E08':prefix_status('tests.test_ph_lw_06','tests.test_ph_lw_07'),
        'LW-E09':extended_status,'LW-E10':prefix_status('tests.test_ph_lw_07'),
        'LW-E11':basic_status,'LW-E12':prefix_status('tests.test_ph_lw_08_preparation'),
        'LW-E13':prefix_status('tests.test_ph_lw_09','tests.test_ph_lw_10_lifecycle'),
        'LW-E14':extended_status,'LW-E15':prefix_status('tests.test_ph_lw_09'),
        'LW-E16':prefix_status('tests.test_ph_lw_09'),'LW-E17':extended_status,'LW-E18':extended_status,'LW-E19':extended_status,'LW-E20':extended_status,
        'LW-E21':extended_status,'LW-E22':extended_status,
        'LW-E23':prefix_status('tests.test_ph_lw_04_http','tests.test_ph_lw_04_05_acceptance'),
        'LW-E24':extended_status,'LW-E25':extended_status,'LW-E26':extended_status,
        'LW-E27':prefix_status('tests.test_ph_lw_05','tests.test_ph_lw_08','tests.test_ph_lw_09'),
        'LW-E28':prefix_status('tests.test_ph_lw_03','tests.test_ph_lw_07','tests.test_ph_lw_11_desktop','tests.test_ph_lw_12'),
        'LW-E29':prefix_status('tests.test_ph_lw_02','tests.test_ph_lw_03'),
        'LW-E30':prefix_status('tests.test_ph_lw_03','tests.test_ph_lw_08_preparation','tests.test_stage_transaction_recovery'),
        'LW-E31':critical_runs['installer-recovery-final'],'LW-E32':basic_status,
        'LW-E33':critical_runs['wheel-browser-final'],'LW-E34':'PASS — bounded scans; not universal DLP',
        'LW-E35':basic_status,'LW-E36':'PASS integrity; regression results separate'}
    def delivered(suffix):
        values=[v['status'] for k,v in delivery.items() if k.endswith(suffix)]
        return 'PASS' if values and all(x=='PASS' for x in values) else 'FAIL' if values else 'NOT RUN'
    status_map.update({
        'LW-E05':critical_runs['installed-no-doc-final'],
        'LW-E09':delivered('test_edge_four_five_separate_forms_stale_tabs_reload_receipts_and_xss'),
        'LW-E14':critical_runs['installed-no-doc-final'],
        'LW-E17':prefix_status('tests.test_ph_lw_09','tests.test_ph_lw_10_lifecycle'),
        'LW-E18':delivered('test_edge_prototype_accept_alpha_form_plan_first_ready_reload'),
        'LW-E19':'FAIL UI projection; core/form/history transition PASS',
        'LW-E20':critical_runs['installed-maintenance-final'],
        'LW-E21':delivered('test_edge_brownfield_assessment_unknown_and_stale_readonly'),
        'LW-E22':delivered('test_edge_supported_migration_confirmation_and_restart_replay'),
        'LW-E24':prefix_status('tests.test_ph_lw_04_http','tests.test_ph_lw_06_http','tests.test_ph_lw_07_http','tests.test_ph_lw_09_http'),
        'LW-E25':delivered('test_installed_tcp_security_and_ownership'),
        'LW-E26':delivered('test_production_wsgi_declared_and_chunked_body_header_and_idle_limits'),
        'LW-E28':'FAIL observed project-list projection; reload/replay/concurrency methods PASS',
        'LW-E33':'PASS controls/disabled reasons; workflow failures remain E19/E20'})
    acceptance=[]
    for line in (ROOT/'Harness_Local_Web_Prompts_RU_r2/ACCEPTANCE_MATRIX.md').read_text('utf-8').splitlines():
        m=re.match(r'\| (LW-E\d+) \| ([^|]+)',line)
        if m:acceptance.append({'id':m[1],'check':m[2].strip(),'status':status_map[m[1]],
            'evidence':'METHOD_RESULTS.json; final_run_statuses in VERDICTS.json; CONTROL_MATRIX.json',
            'qualification':'NOT RUN accepted limitation' if m[1]=='LW-E01' else
                'Baseline long paths PASS; additional deeper app-data stress FAIL remains OPEN' if m[1]=='LW-E02' else
                'Real disk-full NOT RUN accepted; actual interruption/read-only/injection remain separate evidence' if m[1]=='LW-E31' else
                'Fresh visible-browser second launch NOT RUN per user instruction; exact --no-browser refusal and historical normal launch kept' if m[1]=='LW-E32' else None})
    save(O/'ACCEPTANCE_MATRIX.json',{'rows':acceptance,'mandatory_missing_tests':missing,'decision':verdict['LOCAL_WEB_MANUAL']})
    security=[('session/bootstrap/Host/Origin/CSRF','Native TCP; installed TCP; replay/expiry; no test-client substitution'),
              ('XSS sources/GPT/results','Headless real Edge; text-only rendering; same-origin request assertions'),
              ('ZIP/limits/traversal/ownership','Native import tests, real TCP body limits and installed negative archive fixtures'),
              ('Windows reparse and locking','Actual junction/hardlink/share-denial tests; two native capability SKIP remain explicit'),
              ('replay/concurrency/recovery','Shared fence/process/CLI tests; injected kernel faults; installed idle crash; real installer interruption'),
              ('logs/exports/distribution','Bounded runtime pattern scan and published-evidence token scan; no universal DLP')]
    security_statuses=[prefix_status('tests.test_ph_lw_04_http','tests.test_ph_lw_04_05_acceptance'),
        status_map['LW-E24'],status_map['LW-E25'],prefix_status('tests.test_ph_lw_02','tests.test_ph_lw_05_import','tests.test_ph_lw_11_desktop'),
        prefix_status('tests.test_ph_lw_03','tests.test_ph_lw_08','tests.test_stage_transaction_recovery'),'PASS bounded scan']
    save(O/'SECURITY_MATRIX.json',{'rows':[{'control':a,'evidence_scope':b,'status':security_statuses[i]} for i,(a,b) in enumerate(security)],
        'known_open_issue':'LW12-DEEP-APPDATA-INTAKE','automatic_executor':'NO-GO; no activation'})
    freeze=read(W/'RUNTIME_FREEZE.json');basic=read(S/'installed-basic-supported/RESULT.json') if (S/'installed-basic-supported/RESULT.json').exists() else {}
    report=f'''# PH-LW-12 — финальная Windows/browser/security приёмка

2026-11-08. **PH-LW-12: NO-GO.**

`LOCAL_WEB_MANUAL: NO-GO`  
`AUTOMATIC_EXECUTOR: прежний NO-GO; выключен`

Полная v0.5.1 остаётся **NO-GO / NOT RELEASED**. Engine/Documentation ZIP не создавались. Поставляются распакованные рабочие файлы, wheel и UNSIGNED installer. Это самостоятельный checkpoint; старые reports/NO-GO и prompts r2 сохранены.

Отдельные текущие verdicts: PH-LW-04 — `{verdict['PH-LW-04']}`; PH-LW-05 — `{verdict['PH-LW-05']}`. Прежние отчёты не переписаны.

## База и область

Выполнен [полный PH-LW-12 r2](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_12.md) на проверенной PH-LW-11 базе, принятой пользователем с четырьмя ограничениями. [Input baseline](PH_LW_12_LOGS/INPUT_BASELINE.json), [input hashes](PH_LW_12_LOGS/INPUT_FILE_HASHES.json). Drift на входе отсутствовал. Новое явное уточнение пользователя ограничило платформу Windows: POSIX-only legacy cases не запускать и не назначать prerequisite. Первоначальный Linux test attempt остановлен; новый runner удалён из Engine; его результаты в приёмку не включаются.

Allowed changes: acceptance tests/runners, прямые UI regressions, current README/operator docs, mirrors, generated wheel/frozen/installer/manifests и новые evidence/reports. Python-алгоритмы core, schemas/registries, old test bytes и исторические отчёты не менялись; в service изменена только устаревшая формулировка disabled reason. [Изменения](PH_LW_12_CHANGED_FILES.md), [before/after](../_workspace/PH_LW_12/CHANGED_FILE_HASHES.json).

## Исправления

Пользовательский JSON POST теперь ждёт собственную очередь navigation resume: отдельный Edge regression воспроизвёл overtaking до fix и прошёл после. POST автоматически не повторяется, guards не ослаблены. Доступные stage-status/manual-evidence открывают существующие формы; удалены устаревшие обещания следующего этапа/ожидания PH-LW-09. Общий log export явно disabled с причиной.

После commit и явного refresh UI запрашивает новую проекцию, дождавшись старого in-flight чтения. Регрессия воспроизведена неизменными прежними assets из сохранённого frozen build: UI READY_FOR_CODEX при canonical TASK_BLOCKED; новый source test PASS. Python bytes и контракты при этом неизменны: [delta](PH_LW_12_LOGS/REFRESH_DELTA.json). Source/installed/frozen rechecks указаны отдельно; ранние FAIL/TIMEOUT не переписаны.

## Фактическая проверка

Текущий discovery: **{discovery['current_methods']} methods / {discovery['current_modules']} modules**; Windows scope — {len(native)} methods; Windows current outcomes: `{counts}`. Не-Windows {len(expected-native)} methods — NOT RUN вне уточнённой платформы. [Полная method matrix](PH_LW_12_LOGS/METHOD_RESULTS.json), [verdicts и незакрытые cases](PH_LW_12_LOGS/VERDICTS.json).

| Run | Результат |
|---|---|
'''+''.join(f'| {name} | {status} |\n' for name,status in critical_runs.items())+f'''

Actual installed EXE baseline MD/ZIP→GPT fixture→отдельные approvals→publish/JIT, restart/resume/crash/port/no-browser second launch, doctor/interpreter refusal и uninstall: `{basic.get('status','NOT RUN')}`, tests `{basic.get('tests',{})}`. Подтверждённые retained paths: `{basic.get('long_path',{}).get('maximum_retained_project_file_path_length','?')}` / `{basic.get('long_path',{}).get('maximum_retained_app_data_file_path_length','?')}` символов. LongPathsEnabled 0→0. [EXE result](PH_LW_12_LOGS/installed-basic-supported/RESULT.json), [actual installer recovery](PH_LW_12_LOGS/installer-recovery-final/RESULT.json).

Расширенный EXE набор: исходный полный run — 18 methods, 3 FAIL / 1 ERROR. Текущее объединение по test IDs после отдельных rechecks: **`{delivery_counts}`**; это составное evidence, не новый monolithic PASS. No-doc весь путь result → manual evidence → независимый PASS → отдельное complete прошёл: [result](PH_LW_12_LOGS/installed-no-doc-final/RESULT.json). MVP → RELEASE с проверкой accepted history и production HTTP limits прошли в [focused run](PH_LW_12_LOGS/installed-extended-focus3/browser.log). Maintenance result-upload остаётся FAIL: [HTTP response](PH_LW_12_LOGS/installed-maintenance-final/task-responses-maintenance.json), [UI state](PH_LW_12_LOGS/installed-maintenance-final/ui-test_maintenance_task_completion_through_browser.json).

Исправления только нового driver: ошибочная повторная прогонка READY-task recipe из уже VERIFYING Gate заменена byte-validated accepted MVP cache; expect timeout 5 s, оставшийся несмотря на page timeout 30 s, исправлен на общий browser expect 30 s; внешний fixture agent формирует result до начала UI reads. Старые assertions не менялись. Предыдущие ошибки и исходные logs сохранены. [Runner versions](PH_LW_12_LOGS/FINAL_ACCEPTANCE_RUNNER_VERSION.json), [maintenance driver](PH_LW_12_LOGS/MAINTENANCE_RUNNER_VERSION.json).

Source-only fixture layout PH-F01/F03/F04: 27 PASS на native Windows source; попытка запустить их неизменёнными через wheel получила missing test-fixture paths, а не runtime failure. Тесты не переписаны. Параллельный native run также сохранил WinError 10055, timeout вложенной product fixture и два outer TIMEOUT; completed sequential rechecks имеют явный supersession по test IDs. Ни один незавершённый run не переименован PASS. [Source-layout rechecks](PH_LW_12_LOGS/source-layout-rechecks/MATRIX.json).

Advanced fixture cache — отдельно проверенные initial states публичного kernel flow, не browser E2E с нуля. Все засчитываемые browser transitions/approvals/result/verification/completion используют реальные формы. Product writes — явно внешний fixture agent; прямых YAML edits control plane в browser segment нет. GPT fixture проверяет протокол, а не интеллект модели. SDK в product-command fixtures — явно test-driver Python; no-doc full flow использует manual evidence без продуктового SDK. Четыре/пять approvals, Stage/MVP→RELEASE, maintenance, Brownfield и migration имеют собственные строки logs.

Среда: настоящий Windows 11 x64/NTFS/non-admin, CPython 3.14.10 x64, Flask 3.1.3, Waitress 3.0.2, pinned Playwright/реальный headless Edge/TCP. Wheel из независимой Unicode CWD/site-packages без source PYTHONPATH. Frozen process получает System32-only PATH. Это не clean-machine и не physical-offline evidence. Полные argv/cwd/interpreter/build bindings и exit — в `.run.json` и [evidence index](PH_LW_12_LOGS/EVIDENCE_INDEX.json).

## Открытые blockers и наблюдения

**LW12-DEEP-APPDATA-INTAKE: OPEN.** Дополнительный более глубокий app-data root приводит к WinError 206 при `intake.py:157` (`workspace.mkdir`); `local_web_sources_service.py:113` cleanup затем маскирует его WinError 145. Public intake не регистрируется; остаётся partial app-owned session. [Native reproduction](PH_LW_12_LOGS/ADDITIONAL_PATH_STRESS.json), [первый EXE stress FAIL](PH_LW_12_LOGS/installed-basic-final/RESULT.json). Это не прежний ZIP-import bug и не automatic-only blocker. Геометрия путей ранее принятой PH-LW-11 базы повторена отдельно и прошла; более глубокий FAIL сохранён и не объявлен принятым ограничением. Полный manual GO не выдаётся.

Узкие source experiments с mkdir/cleanup выявили дальнейшие plain-path resolve/existence failures и не дали полного IO fix. Они полностью отменены, точные production bytes восстановлены: [revert attestation](PH_LW_12_LOGS/PATH_IO_EXPERIMENT_REVERTED.json). Непроверенная часть исправления не включена в wheel/installer.

**LW12-MAINTENANCE-RESULT-CONFLICT: OPEN.** На actual installed EXE после создания maintenance Task и navigation/refresh загрузка result получает 409 `OPERATION_CONFLICT`; result остаётся NOT_RECEIVED, verification недоступна. Повтор с устранённым конфликтом fixture-helper тоже FAIL. Own UI read overlap — гипотеза по sequence и коду, точный holder guard не трассирован. Нельзя засчитать maintenance verify/complete по успешному start/cancel или по source API tests. [Final failing run](PH_LW_12_LOGS/installed-maintenance-final/RESULT.json).

**LW12-PROJECT-LIST-PROJECTION: OPEN, observed UI inconsistency.** На настоящем [скриншоте после MVP→RELEASE](PH_LW_12_LOGS/installed-extended-focus3/screenshots/10/mvp-to-release.png) lifecycle показывает STAGE_PLANNING_REQUIRED и active RELEASE, а карточка списка — прежний TARGET_LEVEL_REACHED. Вероятная причина — `state.projects` обновляется только list GET; это вывод из кода, не отдельно прошедший regression test. [Observation](PH_LW_12_LOGS/UI_PROJECTION_OBSERVATION.json). Отдельно исправленный stale lifecycle GET не закрывает это наблюдение.

Также незакрыты все NOT RUN/FAIL/TIMEOUT, явно перечисленные в current Windows matrix. Новые обязательные пробелы не списываются на старый automatic verdict. Четыре ранее принятых NOT RUN — clean Windows, physical offline, real disk-full и actual Unicode username — не блокируют повторно. Fresh normal second launch, открывающий default browser, не выполнялся по запрету новых видимых окон; точный отказ второго --no-browser и прежнее normal-launch evidence разделены.

## Поставка и целостность

Build `{freeze['build_id']}`, source digest `{freeze['engine_build_digest']}`.  
Wheel SHA-256 `{freeze['wheel_sha256']}`.  
Installer SHA-256 `{freeze['installer_sha256']}`.

[Integrity](PH_LW_12_LOGS/INTEGRITY.json): wheel CRC/RECORD/source bytes, frozen inventory, standalone/embedded/frozen docs, resource mirrors и отсутствие private runtime files. Payload Harness.exe — AMD64 PE `0x8664`; Inno Setup bootstrap — x86 PE `0x14c`, x64compatible target. Installer UNSIGNED. Exact schemas/registries сохраняются. После финального runtime freeze допустимы только tests/evidence/reports/навигация и manifests; любые прежние пересборки имеют отдельные hashes. [Freeze](PH_LW_12_LOGS/RUNTIME_FREEZE.json), [final working-tree attestation](../_workspace/PH_LW_12/FINAL_WORKING_TREE_VERIFICATION.json).

Scan имеет заявленные границы: controlled runtime source/resources/docs и публикуемые text logs; это не универсальная DLP или анализ секретов внутри всех бинарников. Raw uploads/auth/operator roots, `_scratch`, `_tools`, `.venv` и caches в distribution не копируются. [Published-log scan](PH_LW_12_LOGS/PUBLISHED_LOG_SCAN.json). Скриншоты — настоящие synthetic UI; приватных пользовательских документов/credentials в них нет.

[Acceptance matrix](PH_LW_12_LOGS/ACCEPTANCE_MATRIX.json), [Control matrix](PH_LW_12_LOGS/CONTROL_MATRIX.json), [Security matrix](PH_LW_12_LOGS/SECURITY_MATRIX.json), [операторская глава 22](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/22_PH_LW_12_Operator_Acceptance.md). Исторические Engine/Documentation ZIP неизменны и не называются обновлёнными.

Следующий шаг в пределах PH-LW-12 manual scope — устранение deep app-data intake/cleanup, result-upload конфликтов и устаревшей карточки, затем повтор затронутых Windows gates на новом freeze. К automatic executor/Podman/egress не переходить; Linux jobs не запускать; ZIP без отдельного запроса не создавать.
'''
    (ENGINE/'PH_LW_12_TEST_REPORT.md').write_text(report,'utf-8')
    (ENGINE/'PH_LW_12_CHANGED_FILES.md').write_text('''# PH-LW-12 — изменения

Allowed scope: acceptance tests/runners, прямые UI regression fixes, current operator docs/README, generated resources/build/wheel/frozen/installer/manifests, новые logs/matrices/reports и workspace navigation.

- `src/project_harness/resources/local_web/assets/app.js`, `lifecycle.js`, `tasks.js`, `interview.js`: resume ordering, свежие post-commit/read projections, навигация существующих форм.
- `assets/index.html`, `local_web_service.py`: truthful labels/disabled reasons, удаление исторических UI обещаний; в Python service только текст причины.
- `metadata_v1.json`, README и generated build/lib/egg-info/wheel/frozen/installer: новая сборка с точным digest.
- Новый `tests/test_ph_lw_12_acceptance.py`, `local_web/windows/final_acceptance.py` и `tools/ph_lw_12_*.py`: тесты, bounded runners, observers и публикация evidence. Старые test files/assertions не менялись.
- Новая глава `22_PH_LW_12_Operator_Acceptance.md`, docs aggregates/index/manifests и byte-identical embedded/frozen docs; текущая навигация workspace.
- Новые `PH_LW_12_LOGS`, report/matrices/changed-files и final attestation.

Нормативные specs/r2, `_inputs`, исторические reports/archives, core algorithms/schemas/registries сохранены. Automatic executor выключен. Engine/Documentation ZIP не собирались. Полный before/after hash inventory — [CHANGED_FILE_HASHES.json](../_workspace/PH_LW_12/CHANGED_FILE_HASHES.json); [test report](PH_LW_12_TEST_REPORT.md).
''','utf-8')
    print(json.dumps({'verdict':'NO-GO','windows':counts,'missing_windows_methods':len(missing),'evidence_files':len(index)},ensure_ascii=False))

if __name__=='__main__':main()
