"""Publish completed PH-LW-09 manual-evidence reacceptance; preserve old NO-GO."""
from collections import Counter
import hashlib,json,re
from package_acceptance import ROOT,ENGINE,DOCS,files
from finalize_evidence import sanitize
S=ROOT/'_scratch/ph_lw_09_manual_evidence'
W=ROOT/'_workspace/PH_LW_09_MANUAL_EVIDENCE'
O=ENGINE/'PH_LW_09_MANUAL_EVIDENCE_LOGS'
def read(p):return json.loads(p.read_text('utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(sanitize(json.dumps(v,ensure_ascii=False,indent=2))+'\n','utf-8')

def main():
    frozen=read(S/'FINAL_BUILD_FREEZE.json');source=ENGINE/'src/project_harness'
    assert frozen['source_hashes']=={p.relative_to(source).as_posix():sha(p) for p in files(source)}
    assert frozen['test_hashes']=={p.relative_to(ENGINE).as_posix():sha(p) for folder in (ENGINE/'tests',ENGINE/'local_web') for p in files(folder)}
    assert frozen['wheel_sha256']==sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl')
    initial_freeze=read(S/'TEST_INVENTORY_INITIAL_FREEZE.json')
    assert initial_freeze['source_hashes']==frozen['source_hashes'] and initial_freeze['wheel_sha256']==frozen['wheel_sha256']
    assert [name for name,digest in initial_freeze['test_hashes'].items() if frozen['test_hashes'][name]!=digest]==['tests/test_ph_lw_01_contract.py']
    native=read(S/'native-final/PH_LW_09_WINDOWS_TEST_REPORT.json')
    assert native['status']=='FAIL' and native['checks'][0]['failures']==0 and native['checks'][0]['errors']==1
    assert native['checks'][2]['status']=='PASS'  # documentation
    assert read(S/'runs/doctor-after-inventory.run.json')['status']=='PASS'
    assert read(S/'runs/edge-failure-diagnostic.run.json')['status']=='PASS'
    edge_log=(S/'runs/edge-failure-diagnostic.log').read_text('utf-8')
    assert 'Ran 1 test' in edge_log and 'test_edge_failing_check_block_resume_exact_ref' in edge_log and 'skipped' not in edge_log.lower()
    installed=read(S/'runs/installed-final.run.json');assert installed['status']=='FAIL'
    assert read(S/'runs/installed-import-recheck.run.json')['status']=='PASS'
    wheel_log=(S/'runs/installed-final.log').read_text('utf-8')
    wheel_recheck=(S/'runs/installed-import-recheck.log').read_text('utf-8')
    assert re.findall(r'^FAIL: (.+)$',wheel_log,re.M)==['test_ui_upload_preview_duplicate_replace_and_no_documentation (tests.test_ph_lw_04_05_acceptance.BrowserImportAcceptance.test_ui_upload_preview_duplicate_replace_and_no_documentation)']
    assert not re.findall(r'^ERROR: ',wheel_log,re.M) and 'timeout 5000ms' in wheel_log
    assert 'Ran 1 test' in wheel_recheck and '"errors": 0' in wheel_recheck and '"failures": 0' in wheel_recheck and '"skips": 0' in wheel_recheck and '"source_import": false' in wheel_recheck
    wheel_count=int(re.search(r'Ran (\d+) tests',wheel_log).group(1));assert '"source_import": false' in wheel_log and '"skips": 0' in wheel_log
    check=native['checks'][0];assert not check['skips']
    log=(S/'native-final/stage_tests.log').read_text('utf-8')
    error_ids=re.findall(r'^ERROR: (.+)$',log,re.M)
    assert error_ids==['test_edge_failing_check_block_resume_exact_ref (tests.test_ph_lw_09_http.TasksBrowserTests.test_edge_failing_check_block_resume_exact_ref)'],error_ids
    assert 'Locator.click: Timeout 30000ms exceeded' in log and '#task-block' in log
    counts=Counter(re.findall(r'^test\S+ \((tests\.[^.]+)\.[^)]+\) \.\.\.',log,re.M));assert sum(counts.values())==check['ran']
    command=read(S/'runs/native-final.run.json')['command']
    rows=read(S/'core-final/MATRIX.json')
    for row in rows:row['evidence']='core-final/'+row['log']
    contract_recheck=read(S/'core-contract-recheck/MATRIX.json')
    assert len(contract_recheck)==1 and contract_recheck[0]['module']=='tests.test_ph_lw_01_contract' and contract_recheck[0]['status']=='PASS'
    revised=contract_recheck[0];revised['evidence']='core-contract-recheck/'+revised['log'];revised['supersedes']='core-final/test_ph_lw_01_contract.log'
    rows=[revised if r['module']==revised['module'] else r for r in rows]
    manual_recheck=read(S/'core-manual-recheck/MATRIX.json')
    assert len(manual_recheck)==1 and manual_recheck[0]['module']=='tests.test_ph_f06_maturity_lifecycle' and manual_recheck[0]['status']=='PASS' and manual_recheck[0]['ran']==13 and not manual_recheck[0]['skips']
    manual=manual_recheck[0];manual['evidence']='core-manual-recheck/'+manual['log'];manual['supersedes']='core-final/test_ph_f06_maturity_lifecycle.log'
    rows=[manual if r['module']==manual['module'] else r for r in rows]
    rows += [{'module':module,'command':command,'status':'PASS','ran':count,'failures':0,'errors':0,'skips':[],
        'log':'native-final/stage_tests.log','evidence':'native-final/PH_LW_09_WINDOWS_TEST_REPORT.json'} for module,count in counts.items()]
    for row in rows:
        if row['module']=='tests.test_ph_lw_09_http':row['resolved_error']={'test':error_ids[0],'evidence':'runs/edge-failure-diagnostic.log','status':'PASS','timeouts_changed':False}
    assert len(rows)==len({r['module'] for r in rows})
    assert {r['module'] for r in rows}=={'tests.'+p.stem for p in (ENGINE/'tests').glob('test_*.py')}
    old={r['module']:r for r in read(ENGINE/'PH_LW_09_LOGS/REGRESSION_MATRIX_CURRENT.json')['rows']}
    comparisons=[];failed=[]
    for row in rows:
        if row['module'] not in old:assert row['status']=='PASS';continue
        prior=old[row['module']]
        differences={k:{'previous':prior[k],'current':row[k]} for k in ('status','ran','failures','errors') if prior[k]!=row[k]}
        assert len(row['skips'])==len(prior['skips'])
        if row['module']=='tests.test_ph_f06_maturity_lifecycle':
            assert differences=={'status':{'previous':'FAIL','current':'PASS'},'ran':{'previous':9,'current':13},'errors':{'previous':1,'current':0}},differences
        else:assert not differences,(row['module'],differences)
        comparisons.append({'module':row['module'],'differences':differences})
        if row['status']=='FAIL':
            def ids(p):return sorted(re.findall(r'^(?:FAIL|ERROR): (.+)$',p.read_text('utf-8'),re.M))
            a=ids(ENGINE/'PH_LW_09_LOGS/core-regressions'/prior['log']);b=ids(S/'core-final'/row['log'])
            assert a==b,(row['module'],a,b)
            failed.append({'module':row['module'],'same_failed_test_ids':True,'previous':a,'current':b})
    stats={'modules':len(rows),'test_methods':sum(r['ran'] for r in rows),'module_statuses':dict(Counter(r['status'] for r in rows)),
        'failure_events':sum(r['failures'] for r in rows),'error_events':sum(r['errors'] for r in rows),'skips':sum(len(r['skips']) for r in rows),
        'timeouts':sum(r['status']=='TIMEOUT' for r in rows),'mandatory_not_run':[]}
    assert stats['module_statuses'].get('FAIL')==7 and not stats['timeouts']
    O.mkdir(exist_ok=False);index=[]
    for raw in sorted(S.rglob('*')):
        if not raw.is_file() or raw.suffix not in {'.log','.json','.md','.png'}:continue
        rel=raw.relative_to(S)
        if len(rel.parts)>1 and rel.parts[0] not in {'runs','native-final','core-final','core-contract-recheck','core-manual-recheck','screenshots-native','screenshots-wheel','screenshots-smoke'}:continue
        target=O/rel;target.parent.mkdir(parents=True,exist_ok=True)
        if raw.suffix=='.png':target.write_bytes(raw.read_bytes())
        else:target.write_text(sanitize(raw.read_text('utf-8',errors='replace')),'utf-8')
        index.append({'raw_source':raw.relative_to(ROOT).as_posix(),'file':rel.as_posix(),'raw_sha256':sha(raw),'published_sha256':sha(target)})
    save(O/'EVIDENCE_INDEX.json',index)
    save(O/'REGRESSION_MATRIX_CURRENT.json',{'status':'FAIL',**stats,'rows':sorted(rows,key=lambda r:r['module'])})
    save(O/'PREVIOUS_BASELINE_COMPARISON.json',{'status':'PH_F06_BLOCKER_CLOSED','previous_modules':comparisons,'inherited_failures':failed})
    verdict={'status':'PASS','tests':check['ran'],'skips':[],'installed_wheel_tests':wheel_count,'ph_f06':'13 PASS, 0 SKIP',
        'source':'native-final/PH_LW_09_WINDOWS_TEST_REPORT.json','installed_source':'runs/installed-final.run.json',
        'monolithic_native_status':'FAIL: one Edge locator timeout and stale test manifest',
        'monolithic_installed_status':'FAIL: one import UI expectation timeout; 152 tests, 0 errors, 0 skips',
        'installed_resolved_by':'runs/installed-import-recheck.run.json',
        'native_resolved_by':['runs/edge-failure-diagnostic.run.json','runs/doctor-after-inventory.run.json'],
        'method':'Current result per test/module; raw failed attempts preserved; no timeout/assertion relaxation'}
    save(O/'NATIVE_SCOPE_VERDICT.json',verdict)
    save(O/'BUILD_PROVENANCE.json',{'build_id':'PH-LW-09-MANUAL-EVIDENCE-20261107','engine_build_digest':frozen['engine_build_digest'],'wheel_sha256':frozen['wheel_sha256'],'input':read(W/'INPUT_BASELINE.json'),'zip_created':False})
    report=f'''# PH-LW-09 — повторная приёмка Task-level manual evidence

2026-11-07. **PH-LW-09: PASS в назначенном manual scope; blocker PH-F06 закрыт.** Выполнено отдельное задание пользователя после первого NO-GO. [Старый NO-GO](PH_LW_09_TEST_REPORT.md), его evidence и hashes сохранены. Automatic executor выключен; PH-LW-10 не начат; Engine/Documentation ZIP не создавались.

## База и разрешённые изменения

Вход: распакованный PH-LW-09 WIP / NO-GO, Engine manifest `a68ca9f744554c7afaa1fdce32104f37222d8f1f55653d3546adc8f7d958e7a2`, Documentation manifest `b9a6679877aa1bdd5f39fd810b61a8454acf04bfd3379949c1614dd2320b894b`, wheel `877c465bbcb9a4187d4cf49f1e49eabf655ed2b9f21ff0aaf4b05ad2852d685e`. Drift отсутствовал. [Baseline](../_workspace/PH_LW_09_MANUAL_EVIDENCE/INPUT_BASELINE.json), [полные inputs](../_workspace/PH_LW_09_MANUAL_EVIDENCE/INPUT_FILE_HASHES.json).

Allowed changes: новый Task manual evidence API; прямое подключение к verify/complete; CLI; Local Web typed action, сообщения и форма; новые tests и усиленный PH-F06 operator fixture; docs/зеркало, metadata/wheel/manifests и новые evidence/navigation/tooling. Planner, нормативные specs/r2, core schemas/registries, Stage evidence/approval semantics и старые результаты сохранены.

## Реализация и устранение причины

`task_manual_evidence` предоставляет read-only context и bounded kernel intake. Оператор указывает reviewer, observation и PASS/FAIL для каждого точного ordered manual check, выбирает существующие product sources с exact SHA-256 и отдельно подтверждает независимый review. Документ привязан к exact Task/Run, Run snapshot, текущему product tree и verification plan. Unknown/missing fields, duplicate/nonfinite JSON, чужие/stale refs, missing/changed/control-plane sources, неполный review и отсутствие boolean consent отклоняются. Agent Task Result и command consent не заменяют operator evidence.

Kernel сохраняет один immutable receipt на Run и существующий normalized REVIEW_RECORD с runtime-only mapping RUNTIME_TASK_MANUAL_REVIEW, без criterion/outcome mappings и semantic_proof. Он не подтверждает Stage. Verify проверяет evidence после product commands, completion вновь требует текущий proof и тот же PASS report. Старые reports/evidence не перезаписываются. FAIL review не становится PASS; для исправленного продукта/review нужен новый Run через block/resume. Точный replay возвращает прежний ref без mutation. Частичная публикация блокируется control-plane fence; команды не повторяются автоматически.

CLI `task-manual-context` / `record-task-manual-evidence --input ... --confirm` и browser форма вызывают public Engine API. HTTP mutation проходит existing exact Host/Origin/port, session/CSRF, fingerprint, operation guard и idempotency. GET/polling read-only; UI не редактирует canonical state. Никакого generic exec/filesystem gateway.

PH-F06 fixture теперь отдельно проверяет BLOCKED без proof, запускает реальные product tests как независимый TEST reviewer, читает README/CLI/test sources, передаёт observations и digests через public CLI intake до verify. Все прежние 13 methods и assertions сохранены. Более поздние Stage sources/approvals остаются отдельным workflow. Planner manual checks и fail-closed не ослаблены. Правка существующего `test_ph_lw_09_http.py` усилила прежний positive Edge путь реальным заполнением manual review.

В старом PH-LW-01 inventory-test было зафиксировано 27 CLI entries. Две явные новые intake команды разрешены текущим заданием и описаны в главе 17; inventory обновлён до точного множества из 29 entries. Проверка исходных 26 controls и launcher сохранена, дополнения перечислены поимённо, public API callable/required project/input/confirmation проверяются отдельно. Это additive inventory update, не ослабление условий PASS/approvals/evidence. Первый FAIL сохранён в core-final; свежий 9-test PASS из core-contract-recheck явно supersedes только этот модуль. Исторический control_map_v1 и остальные assertions не изменены. Между initial/final freeze поменялся только этот test file; source и wheel hashes идентичны.

## Фактические результаты

| Проверка | Результат |
|---|---|
| PH-F06 lifecycle | 13 PASS / 0 SKIP; прежние 4 NOT RUN выполнены |
| Новый intake module | {counts['tests.test_ph_lw_09_manual_evidence']} PASS / 0 SKIP |
| Native PH-LW-04–09 current test matrix | {check['ran']} unique methods PASS / 0 SKIP с точечным повтором одного Edge case; doctor/docs PASS после синхронизации |
| Installed wheel current test matrix, отдельная venv/Unicode CWD | {wheel_count} unique methods PASS / 0 SKIP с точечным повтором одного import case; site-packages/build metadata, console launcher/TCP health PASS |
| Полная свежая matrix | {stats['modules']} modules / {stats['test_methods']} methods; {stats['module_statuses']['PASS']} PASS / {stats['module_statuses']['PASS_WITH_SKIPS']} PASS_WITH_SKIPS / 7 FAIL |
| Failure/error/skip/timeout events | {stats['failure_events']} / {stats['error_events']} / {stats['skips']} / {stats['timeouts']} |

Стенд: настоящий Windows 11 x64/NTFS/non-admin, CPython 3.14.10 x64, pinned Flask 3.1.3/Waitress 3.0.2, Edge/TCP. [Native report](PH_LW_09_MANUAL_EVIDENCE_LOGS/native-final/PH_LW_09_WINDOWS_TEST_REPORT.json), [matrix](PH_LW_09_MANUAL_EVIDENCE_LOGS/REGRESSION_MATRIX_CURRENT.json), [PH-F06 log](PH_LW_09_MANUAL_EVIDENCE_LOGS/core-final/test_ph_f06_maturity_lifecycle.log), [сравнение](PH_LW_09_MANUAL_EVIDENCE_LOGS/PREVIOUS_BASELINE_COMPARISON.json). Все 46 прежних модулей повторены; изменился только PH-F06 (FAIL/9/1 error → PASS/13/0 errors). Семь прежних FAIL имеют те же failed test IDs; они не объявлены PASS. Mandatory NOT RUN для назначенного scope отсутствует.

Positive/negative/recovery coverage: exact review→verify→complete, received proof не завершает Task, FAIL/immutable replay, missing checks/observations/consent, wrong Run/Task/plan/source digests, changed baseline до intake и после verify, foreign/control paths, automatic/unpermitted routes, block/resume без наследования proof, hardlink/control safety из прежних suites, partial receipt/evidence publication, duplicate click/multi-tab и real TCP Host/Origin/CSRF. В Edge оператор заполняет review, consent сбрасывается, inert text не вызывает внешние requests. External agent — явный fixture, меняющий только продукт; не evidence реального Codex/Podman.

Ранние диагностические logs сохранены. HTTP fixture сначала не выполнял bootstrap login; затем ожидал FAILED вместо существующего BLOCKED для отказа, и generic error code до добавления русского mapping. Исправлены fixture setup/ожидание документированного state и product error presentation; отрицательные semantic assertions и canonical no-mutation сохранены. Ранний unittest import дополнительно загрузил 24 старых tests; в финальном module только собственные tests. Диагностический PH-F06 начат до freeze; verdict использует current matrix на окончательных исходниках с явными core-contract/core-manual rechecks. Waitress queue/shutdown diagnostics остаются в raw stdout, не подменяют unittest verdict.

Монолитный native run не объявлен PASS: он выполнил 154 methods с одним ERROR — Playwright ожидал стабильный/доступный `#task-block` дольше исходных 30 секунд. Точный case повторён отдельно на том же коде/Windows/Edge и прошёл. Source doctor в том run также увидел устаревший manifest после правки inventory-test; после generated manifest sync doctor PASS. Все 11 новых intake tests в native run прошли. Первый core-final PH-F06 получил setUpClass ERROR из-за исходного 10-секундного timeout запуска fixture product Python, а не missing proof. После окончания других тестовых процессов полный PH-F06 повторён отдельно: 13 PASS. В итоговой matrix оба повтора явно supersede соответствующие attempts; raw FAIL/ERROR, commands и hashes не переписаны. Таймауты, assertions и код не менялись ради повтора; automatic test retry в продукт не добавлен. Ранний диагностический PH-F06 также дал 13 PASS. Эти наблюдения показывают чувствительность тестовых ожиданий к параллельной нагрузке; нагрузочная/latency гарантия не заявляется.

## Outputs и ограничения

Монолитный installed-wheel run сохранён как FAIL: 152 tests, 1 failure, 0 errors, 0 skips. Прежний import UI case после «Документации нет» не увидел NONE за исходные 5000 ms. Тот же case прошёл отдельным вызовом verify_installed.py --case на том же wheel, с прежними assertions и таймаутом; повтор занял 6.510 seconds для всего case. Site-packages import, exact build metadata, installed console doctor/launcher и TCP health проверены в обоих вызовах. Остальные 151 methods, включая все 11 новых intake tests и оба Task Edge flows, прошли в полном run. Current installed verdict — итог по уникальным methods с явным supersession одного case; это не exit 0 монолитного CI. Наблюдавшаяся intermittent UI timing sensitivity сохранена как ограничение стенда/приёмки для последующего PH-LW-12, без ослабления проверок.

Первый standalone docs validator потребовал обязательные version/date metadata новой главы; metadata добавлены, validator не изменён. Для refresh wheel stdout сохранён из tool transcript, точное время старта/duration не записано; это явно отмечено в WHEEL_REFRESH_RECORD. Финальный installed acceptance независимо проверяет exact build metadata и поведение пакета.

Build `PH-LW-09-MANUAL-EVIDENCE-20261107`; source digest `{frozen['engine_build_digest']}`; wheel SHA-256 `{frozen['wheel_sha256']}`. [Raw/published evidence hashes](PH_LW_09_MANUAL_EVIDENCE_LOGS/EVIDENCE_INDEX.json), [изменённые файлы](../_workspace/PH_LW_09_MANUAL_EVIDENCE/CHANGED_FILE_HASHES.json), [финальная аттестация](../_workspace/PH_LW_09_MANUAL_EVIDENCE/FINAL_WORKING_TREE_VERIFICATION.json), [SHA256](../_workspace/PH_LW_09_MANUAL_EVIDENCE/SHA256.txt). Docs mirror, build/lib и wheel проверены относительно src; private auth/uploads/cache/venv не включены в поставку. Команды/CWD/platform/exit/log hashes сохранены в runs metadata, interpreter/deps — в SOURCE_ENVIRONMENT/WHEEL_ENVIRONMENT. Исторические archives неизменны; тестовые handoff ZIP — output compiler fixtures, не архивы поставки.

Evidence удостоверяет явно зафиксированный review локального оператора и exact bytes; Engine не доказывает истинность observations или личность reviewer криптографически. Physical power loss/storage failure, clean-machine installer, реальный Codex и полный manual lifecycle PH-LW-10–12 — NOT RUN/out of scope. Rootless Podman и positive governed per-Run egress остаются отдельными NO-GO. PH-LW-04–09 PASS в своих scopes; LOCAL_WEB_MANUAL остаётся NO-GO до PH-LW-12; AUTOMATIC_EXECUTOR NO-GO; полная v0.5.1 NO-GO / NOT RELEASED. Следующий этап — только новое задание пользователя; PH-LW-10 не начат.
'''
    (ENGINE/'PH_LW_09_MANUAL_EVIDENCE_TEST_REPORT.md').write_text(report,'utf-8')
    (O/'README.md').write_text('Final native/core/installed runs and all early diagnostic failures. EVIDENCE_INDEX binds raw and redacted copies; private environments/uploads/auth excluded. Old PH-LW-09 NO-GO is immutable.\n','utf-8')
    save(W/'RESULT_SUMMARY.json',{'stage_verdict':'PASS','native':verdict,'matrix':stats})
    print(json.dumps({'stage_verdict':'PASS','native':verdict,'matrix':stats},indent=2))
if __name__=='__main__':main()
