"""Publish factual Windows rerun evidence without changing earlier reports."""
import hashlib,json,re
from collections import Counter
from pathlib import Path
from package_acceptance import ROOT,ENGINE,DOCS
from ph_lw_12_report import outcomes,sanitize

S=ROOT/'_scratch/ph_lw_12_fix';W=ROOT/'_workspace/PH_LW_12_FIX';O=ENGINE/'PH_LW_12_FIX_LOGS'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text('utf-8-sig'))

def clean(text):
    text=sanitize(text)
    return re.sub(r'''(?i)((?:['"]?(?:x-csrf-token|csrf)['"]?)\s*[:=]\s*['"]?)[A-Za-z0-9_-]{20,}''',r'\1<REDACTED>',text)

def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(clean(json.dumps(value,ensure_ascii=False,indent=2))+'\n','utf-8')

def main():
    discovery=read(W/'DISCOVERY.json');freeze=read(W/'RUNTIME_FREEZE.json');freeze_sha=sha(W/'RUNTIME_FREEZE.json')
    assert freeze['build_id']=='PH-LW-12-FIX5-20261108'
    assert read(W/'DOC_VALIDATION_BEFORE_BUILD_05.json')['status']=='PASS'
    native={r['id'] for r in discovery['methods'] if r['platform_status']=='SCHEDULED_WINDOWS'}
    methods={r['id']:{'status':'NOT RUN','reason':r['reason']} for r in discovery['methods']}
    for folder in ('wheel','source'):
        for p in (S/folder).glob('*.run.json'):
            row=read(p)
            if row.get('process_status')=='PASS' and row.get('runtime_freeze_sha256')==freeze_sha:
                methods.update(outcomes(p.with_suffix('').with_suffix('.log')))
    maturity=S/'maturity-final05.run.json'
    assert maturity.exists() and read(maturity)['status']=='PASS','Maturity final run incomplete'
    assert read(maturity)['runtime_freeze_sha256']==freeze_sha
    methods.update(outcomes(S/'maturity-final05.log'))
    methods={key:value for key,value in methods.items() if key in {r['id'] for r in discovery['methods']}}
    missing=sorted(key for key in native if methods[key]['status'] not in {'PASS','SKIP'})
    counts=dict(Counter(methods[key]['status'] for key in native))
    skips={key:methods[key] for key in native if methods[key]['status']=='SKIP'}
    allowed_skips={'tests.test_contract_hardening.ContractHardeningControlPlaneTests.test_agent_result_symlink_is_rejected',
        'tests.test_ph_lw_02_windows_core.WindowsCoreBoundaryTests.test_05_colliding_tree_rejected_without_rewriting_case'}
    runs={}
    for name in ('final05-installed-supported','final05-installed-deep','final05-installer-recovery',
                 'final05-installed-extended','final05-installed-deep-full','maturity-final05'):
        p=S/(name+'.run.json');assert p.exists(),name
        row=read(p);assert row['runtime_freeze_sha256']==freeze_sha,name
        runs[name]={'status':row['status'],'exit':row['exit'],'log_sha256':row['log_sha256'],
            'runtime_freeze_sha256':row['runtime_freeze_sha256']}
    http_files=[p for folder in ('final05-installed-extended','final05-installed-deep-full')
        for p in (S/folder).glob('task-responses-*.json')]
    assert len(http_files)==3
    http_rows=[row for p in http_files for row in read(p)]
    unexpected=[row for row in http_rows if row['status']>=500]
    save(O/'POSITIVE_FLOW_HTTP_STATUS.json',{'status':'FAIL' if unexpected else 'PASS',
        'scope':'POST operation/result responses and all >=400 /api/projects errors observed in positive no-doc/maintenance flows; not a universal network trace.',
        'statuses':dict(Counter(row['status'] for row in http_rows)),'unexpected_5xx':unexpected,
        'installer_sha256':freeze['installer_sha256'],
        'inputs':[{'file':p.relative_to(S).as_posix(),'raw_sha256':sha(p)} for p in http_files]})
    gate=not missing and not unexpected and set(skips)<=allowed_skips and all(row['status']=='PASS' for row in runs.values())
    verdict={'PH-LW-04':'GO in tested Windows scope','PH-LW-05':'GO in tested Windows scope',
        'PH-LW-12':'GO with retained accepted limitations' if gate else 'NO-GO',
        'LOCAL_WEB_MANUAL':'GO' if gate else 'NO-GO','AUTOMATIC_EXECUTOR':'previous NO-GO; disabled',
        'v0.5.1':'NO-GO / NOT RELEASED','platform':'Windows 11 x64 / NTFS / non-admin only',
        'accepted_not_run':['clean Windows without developer runtimes','physical offline','real disk-full','actual Unicode username'],
        'windows_methods':len(native),'windows_counts':counts,'windows_unclosed_methods':missing,'platform_skips':skips,
        'posix_methods_outside_windows_scope':len(discovery['methods'])-len(native),'final_runs':runs,
        'prior_candidate_results_credited':False,
        'positive_flow_observed_unexpected_5xx':len(unexpected),
        'blockers':{key:('CLOSED' if gate else 'NOT CLOSED BY THIS REPORT') for key in
            ('LW12-DEEP-APPDATA-INTAKE','LW12-MAINTENANCE-RESULT-CONFLICT','LW12-PROJECT-LIST-PROJECTION')},
        'zip_created':False,'automatic_executor_enabled':False,'system_settings_changed':False,'visible_browser_windows_opened':False}
    save(O/'VERDICTS.json',verdict);save(O/'METHOD_RESULTS.json',methods)
    for name in ('INPUT_BASELINE.json','INPUT_FILE_HASHES.json','DISCOVERY.json','RUNTIME_FREEZE.json','INTEGRITY.json',
                 'WHEEL_ENVIRONMENT.json','MATURITY_SETUP_CACHE.json','VISUAL_QA.json','ATTEMPT_DECISIONS.json',
                 'RUNTIME_FREEZE_CANDIDATE_03.json','RUNTIME_FREEZE_CANDIDATE_04.json','FINALIZATION_ATTEMPT_03.json',
                 'DOC_VALIDATION_METADATA_FAIL.json','DOC_VALIDATION_FIXED_BEFORE_BUILD.json','BUILD04_WRAPPER_DIAGNOSTIC.json',
                 'DOC_VALIDATION_BEFORE_BUILD_05.json','POLL_STRESS_STOPPED.json'):
        if (W/name).exists():save(O/name,read(W/name))
    if (W/'CODE_DIFF.patch').exists():(O/'CODE_DIFF.patch').write_text((W/'CODE_DIFF.patch').read_text('utf-8'),'utf-8')
    selected=[p for p in S.iterdir() if p.is_file() and p.suffix in {'.log','.json'}]
    for folder in ('wheel','source'):
        selected += [p for p in (S/folder).rglob('*') if p.is_file() and p.suffix in {'.log','.json','.png'}]
    for folder in [p for p in S.iterdir() if p.is_dir() and (p.name.startswith(('installed-','final-installed-','final03-','final04-','final05-','installer-recovery','deep-native-full-','deep-reload-','poll-barrier-')))]:
        selected += [p for p in folder.iterdir() if p.is_file() and p.suffix in {'.log','.json','.txt','.png'}]
        selected += list((folder/'screenshots').rglob('*.png'))
        selected += [p for d in folder.glob('operations-*') for p in d.glob('*.json')]
    index=[]
    for p in sorted(set(selected)):
        rel=p.relative_to(S);target=O/rel;target.parent.mkdir(parents=True,exist_ok=True)
        if p.suffix=='.png':target.write_bytes(p.read_bytes())
        else:target.write_text(clean(p.read_text('utf-8-sig',errors='replace')),'utf-8')
        index.append({'raw':p.relative_to(ROOT).as_posix(),'published':rel.as_posix(),'raw_sha256':sha(p),'published_sha256':sha(target)})
    save(O/'EVIDENCE_INDEX.json',index)
    bad=[]
    pattern=re.compile(r'harness_local_session=(?!<REDACTED>)[A-Za-z0-9_-]{20,}|#bootstrap=(?!<REDACTED>)[A-Za-z0-9_-]{24,}')
    for p in O.rglob('*'):
        if p.suffix in {'.log','.json','.txt'} and pattern.search(p.read_text('utf-8',errors='replace')):bad.append(p.relative_to(O).as_posix())
    save(O/'PUBLISHED_LOG_SCAN.json',{'status':'FAIL' if bad else 'PASS','matches':bad,
        'scope':'Published textual evidence: bootstrap/session/CSRF redaction and explicit patterns; not universal DLP.'})
    assert not bad,bad
    acceptance=[]
    for line in (ROOT/'Harness_Local_Web_Prompts_RU_r2/ACCEPTANCE_MATRIX.md').read_text('utf-8').splitlines():
        match=re.match(r'\| (LW-E\d+) \| ([^|]+)',line)
        if match:acceptance.append({'id':match[1],'check':match[2].strip(),
            'status':'NOT RUN — accepted limitation' if match[1]=='LW-E01' else 'PASS in stated Windows scope' if gate else 'INCOMPLETE',
            'evidence':'METHOD_RESULTS.json; VERDICTS.json final_runs; actual EXE results',
            'qualification':'Actual Unicode username NOT RUN accepted; deep Unicode paths PASS' if match[1]=='LW-E02' else
                'Real disk-full NOT RUN accepted; actual interruption/read-only/injected failures separate' if match[1]=='LW-E31' else
                'Fresh visible default-browser second launch not repeated by user instruction; --no-browser exact refusal and retained PH-LW-11 normal-launch evidence separate' if match[1]=='LW-E32' else
                'Engine/Documentation ZIP not requested; working trees/wheel/frozen/installer verified' if match[1]=='LW-E36' else None})
    save(O/'ACCEPTANCE_MATRIX.json',acceptance)
    control=read(ENGINE/'PH_LW_12_LOGS/CONTROL_MATRIX.json')
    for row in control['controls']:row['evidence']='Final current method matrix; actual 22-method EXE browser suite; baseline control map unchanged'
    save(O/'CONTROL_MATRIX.json',control)
    save(O/'SECURITY_MATRIX.json',{'status':'PASS' if gate else 'INCOMPLETE','rows':[
        {'control':name,'status':'PASS' if gate else 'INCOMPLETE','evidence':ref} for name,ref in [
            ('Host/Origin/port/session/CSRF/replay','Current PH-LW-04/05 TCP and actual EXE negative cases'),
            ('XSS/text-only/CSP/no external requests','Current Edge source/GPT/results and actual EXE flows'),
            ('ZIP limits/CRC/encryption/traversal/reparse','Current import/core NTFS boundary and real EXE hostile ZIP cases'),
            ('Revision/replay/concurrency/recovery','Current shared fence/CLI/process/transaction/installer tests'),
            ('Immutable evidence/history/consent/manual boundary','Current Task/Stage/Brownfield/migration/maturity suites'),
            ('Distribution/log contents','INTEGRITY.json; PUBLISHED_LOG_SCAN.json; VISUAL_QA.json')]],
        'platform_skips':skips,'scan_limits':'Bounded patterns and synthetic UI review; no universal DLP claim',
        'automatic_executor':'NO-GO; disabled'})
    state=verdict['LOCAL_WEB_MANUAL'];deep=read(S/'final05-installed-deep/RESULT.json')
    environment=read(W/'WHEEL_ENVIRONMENT.json')
    report=f'''# PH-LW-12 — исправление трёх blockers и повторная приёмка

2026-11-08. **LOCAL_WEB_MANUAL: {state}.**  
**AUTOMATIC_EXECUTOR: прежний NO-GO; выключен.**  
Полная v0.5.1: **NO-GO / NOT RELEASED**. Только Windows. Engine/Documentation ZIP не создавались.

Это новый checkpoint на [проверенной предыдущей базе](PH_LW_12_FIX_LOGS/INPUT_BASELINE.json). [Исходный NO-GO](PH_LW_12_TEST_REPORT.md) и его evidence сохранены. [Verdicts](PH_LW_12_FIX_LOGS/VERDICTS.json), [изменения](PH_LW_12_FIX_CHANGED_FILES.md), [точный diff](PH_LW_12_FIX_LOGS/CODE_DIFF.patch).

## Три исправления

1. **LW12-DEEP-APPDATA-INTAKE — {verdict['blockers']['LW12-DEEP-APPDATA-INTAKE']}.** Native IO охватывает создание/replay/cleanup intake, источники, catalog/draft/fingerprint, approvals, compilation/ZIP validation, no-replace publication и затронутые manual Task/evidence/journal reads. Ordinary paths/refs сохраняются; UNC/device/reparse запреты не ослаблены. Исходная ошибка cleanup не маскируется; committed session не удаляется. Control-plane scan не объявляет существующие глубокие файлы удалёнными, а настоящий tamper/deletion остаётся FAIL.
2. **LW12-MAINTENANCE-RESULT-CONFLICT — {verdict['blockers']['LW12-MAINTENANCE-RESULT-CONFLICT']}.** JSON и multipart одной вкладки проходят общую очередь с прежними reads и navigation resume. Внешний конфликт остаётся 409; POST не повторяется; исходные binding/consent не заменяются новыми автоматически. Actual maintenance result/evidence/verify/complete проверены реальными формами.
3. **LW12-PROJECT-LIST-PROJECTION — {verdict['blockers']['LW12-PROJECT-LIST-PROJECTION']}.** Карточка обновляется из того же fresh public Engine view, что основной panel. После MVP→RELEASE проверяются core ACTIVE, lifecycle STAGE_PLANNING_REQUIRED и актуальная карточка; accepted history сохраняется.

Operation/preparation polling читает собственный атомарный companion snapshot без рекурсивного обхода меняющегося canonical дерева. Сохраняются catalog/project ownership, root/ancestor reparse checks, record integrity и прежняя migration policy. До появления snapshot preparation GET получает прежний shared guard; mutation admission и явное recovery сохраняют полную проверку дерева. GET не пишет журнал и не повторяет операции.

State machines, schemas/registries, порядок уровней, exact refs/digests, approvals, semantic evidence и manual/automatic policy не менялись. UI/HTTP не редактируют canonical YAML. Изменения соседнего core ограничены доказанными native IO regressions и read-only companion snapshot boundary.

## Фактические tests

Discovery: **{discovery['current_methods']} methods / {discovery['current_modules']} modules**. Windows scope — **{len(native)}**, итог `{counts}`. **{len(discovery['methods'])-len(native)} POSIX-only** methods NOT RUN вне разрешённой Windows платформы; Linux/WSL/Docker jobs не выполнялись. Source-layout-only PH-F01/F03/F04 — 27 methods на source; прочая текущая matrix — installed wheel из независимой Unicode CWD с пустым PYTHONPATH. Все case IDs, commands/exits/counts/elapsed/причины — в [method matrix](PH_LW_12_FIX_LOGS/METHOD_RESULTS.json), `.run.json` и [evidence index](PH_LW_12_FIX_LOGS/EVIDENCE_INDEX.json).

| Exact final run | Status |
|---|---|
'''+''.join(f'| {name} | {row["status"]} |\n' for name,row in runs.items())+f'''

Actual EXE extended — 22 methods; отдельный глубокий no-doc→GPT→4 approvals→publish→result→manual evidence→verify→complete проверен дополнительно. Deep MD/ZIP EXE — retained project/app-data paths **{deep['long_path']['maximum_retained_project_file_path_length']}/{deep['long_path']['maximum_retained_app_data_file_path_length']}** символов; LongPathsEnabled 0→0. [Deep EXE](PH_LW_12_FIX_LOGS/final05-installed-deep/RESULT.json), [deep full manual](PH_LW_12_FIX_LOGS/final05-installed-deep-full/RESULT.json), [22-method browser/security](PH_LW_12_FIX_LOGS/final05-installed-extended/RESULT.json), [actual installer recovery](PH_LW_12_FIX_LOGS/final05-installer-recovery/RESULT.json).

Native source diagnostic также прошёл полный manual путь при app-data 242 / project root 251 и public compile/initial validation при output parent 294. Это отдельный source evidence, не замена actual frozen run. External fixture agent пишет только product plane; его IO и полный non-empty control snapshot адаптированы к длинным путям. Initial advanced fixtures происходят из public kernel flow; browser segment применяет реальные reviewed forms, без изготовленных private approvals. GPT fixture проверяет протокол, не интеллект модели.

Два прежних capability SKIP сохранены с точными причинами: native file symlink требует отсутствующей privilege; casefold aliases требуют case-sensitive directory. Новых SKIP не допускается. Actual NTFS junction/hardlink и ZIP link/collision tests выполняются отдельно. Четыре принятых NOT RUN — clean Windows, physical offline, actual Unicode username, real disk-full — не открывались заново и не переименованы PASS. Headless Edge не объявляется новой проверкой visible default-browser second launch.

## Сохранённые диагностические попытки

Кандидаты 01/02 и прерванные legacy setups сохранены с исходными FAIL/exit/logs; их результаты не засчитаны финальной matrix. После исправления archive IO последующие проверки выявили plain-path control scan, archive comparison и rename; эти read/write sites исправлены до final freeze. Финальный набор включает 12 targeted regressions: 8 native IO/snapshot и 4 real Edge.

После успешных runtime tests кандидата 03 финальный docs validator обнаружил отсутствующее обязательное поле базовой даты в новой главе 23. FAIL сохранён в [metadata diagnostic](PH_LW_12_FIX_LOGS/DOC_VALIDATION_METADATA_FAIL.json); предварительный GO report не был завершённой аттестацией и сохранён отдельно. В кандидате 04 дата исправлена; docs validator и 14 documentation-sensitive contracts прошли. Full aggregate Local Web addenda не включает и корректно не изменился; ошибка строгого inventory assertion build-helper описана отдельно, build-04 сам PASS.

У кандидата 04 последний deep full E2E дал FAIL: publication journal в core SUCCEEDED, но UI после reload остановился на INTERNAL_ERROR. Isolated rerun и source trace прошли без изменений; это не было принято как устранение дефекта. [Scheduling-barrier reproduction](PH_LW_12_FIX_LOGS/poll-barrier-before/RESULT.json) детерминированно выявила реальный FileNotFoundError: GET рекурсивно сканировал временный файл публичной check-intake, который её настоящий atomic writer уже переименовал. Python stack первого frozen 500 не записан; связь с найденной гонкой — вывод по общему read path, а не восстановленный stack trace. Исключение в reproduction не изготовлено mock; менялся только порядок исполнения. Два новых теста на прежних bytes дали 2 ERROR, на исправленном коде — 2 PASS с теми же assertions. Обычный stress helper остановлен после собственного некорректного budget cleanup и не засчитан; запись сохранена. В [наблюдаемых positive-flow HTTP responses](PH_LW_12_FIX_LOGS/POSITIVE_FLOW_HTTP_STATUS.json) final05 неожиданных 5xx нет; границы наблюдения указаны явно.

Кандидат **05** меняет snapshot boundary и содержит эти regressions. Его source/wheel/frozen/installer зафиксированы заново; вся Windows matrix, fresh maturity и пять actual EXE/recovery наборов выполнены заново по **одному final05 freeze**. Никакие результаты прежних candidates и их прежние equivalence proofs в итоговые counts не перенесены. Глава 23 описывает дополнительную гонку; validator прошёл до build и финальной аттестацией.

Один прежний PH-LW-12 fault-test синхронизирован с новым serialized transport: искусственно задержанный GET освобождается до ожидания запроса, который правильно ждёт в очереди. Assertions exact fingerprint и canonical/UI state сохранены; исходные bytes — `_workspace/PH_LW_12_FIX/input-tests/`. Остальные legacy test assertions не менялись. Frozen HTTP driver сохраняет exact 431 assertion при Windows reset после уже полученного HTTP 431 status; body loss успешных responses остаётся ошибкой. Это не PASS при reset до HTTP status.

## Точные bytes и ограничения

Build `{freeze['build_id']}`; source digest `{freeze['engine_build_digest']}`.  
Wheel SHA-256 `{freeze['wheel_sha256']}`.  
UNSIGNED installer SHA-256 `{freeze['installer_sha256']}`.

[Freeze](PH_LW_12_FIX_LOGS/RUNTIME_FREEZE.json), [installed environment](PH_LW_12_FIX_LOGS/WHEEL_ENVIRONMENT.json), [integrity](PH_LW_12_FIX_LOGS/INTEGRITY.json), [final attestation](../_workspace/PH_LW_12_FIX/FINAL_WORKING_TREE_VERIFICATION.json), [before/after hashes](../_workspace/PH_LW_12_FIX/CHANGED_FILE_HASHES.json). После freeze runtime/docs bytes не менялись; добавлены только tests/evidence/reports/navigation/manifests. Build metadata conservatively preserves pre-acceptance NO-GO release flags; текущий exact-hash manual verdict дан этим внешним отчётом, full v0.5.1 не переобъявлен RELEASE.

Windows 11 x64/NTFS/non-admin, CPython 3.14.10 x64, Flask 3.1.3, Waitress 3.0.2, pinned Playwright/real Edge {environment['browser_version']}/TCP. Hash browser executable сохранён в environment evidence. Frozen child имеет System32-only PATH. Payload PE AMD64 0x8664; Inno bootstrap x86 0x14c с x64compatible target. Ни системные защитные настройки, ни LongPathsEnabled не менялись. Исторические archives не пересобраны.

[Acceptance](PH_LW_12_FIX_LOGS/ACCEPTANCE_MATRIX.json), [controls](PH_LW_12_FIX_LOGS/CONTROL_MATRIX.json), [security](PH_LW_12_FIX_LOGS/SECURITY_MATRIX.json), [published log scan](PH_LW_12_FIX_LOGS/PUBLISHED_LOG_SCAN.json), [операторская глава 23](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/23_PH_LW_12_Blocker_Fixes.md). Scan имеет заявленные text-pattern границы; это не универсальная DLP. Raw auth/uploads/projects, `_scratch`, `_tools`, `.venv`, caches в distribution не включены.

Следующий разрешённый шаг: использовать/проверять принятый manual companion в указанном Windows scope. К automatic executor, Podman/egress или следующему этапу автоматически не переходить. ZIP только по отдельному запросу.
'''
    (ENGINE/'PH_LW_12_FIX_TEST_REPORT.md').write_text(report,'utf-8')
    (ENGINE/'PH_LW_12_FIX_CHANGED_FILES.md').write_text('''# PH-LW-12 — исправления blockers

Изменения: native Windows IO boundary в доказанном intake/publication/manual пути; request ordering для JSON/multipart; project-card projection из public view; regressions и actual EXE driver; новая операторская глава 23, generated docs mirrors/index/manifests и новый wheel/frozen/installer. Test-only изменения сохраняют semantic assertions и явно отделены от runtime.

Нормативные specs/r2, schemas/registries, старые reports/evidence/archives сохраняются. Automatic executor выключен; Engine/Documentation ZIP не создавались. [Точный code diff](PH_LW_12_FIX_LOGS/CODE_DIFF.patch), [полные before/after hashes](../_workspace/PH_LW_12_FIX/CHANGED_FILE_HASHES.json), [фактический отчёт](PH_LW_12_FIX_TEST_REPORT.md).
''','utf-8')
    print(json.dumps({'verdict':state,'windows':counts,'missing':missing,'evidence_files':len(index)}))

if __name__=='__main__':main()
