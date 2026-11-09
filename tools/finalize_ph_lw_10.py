"""Publish immutable PH-LW-10 evidence after frozen-build acceptance."""
from collections import Counter
import ast,hashlib,json,re,zipfile
from package_acceptance import ROOT,ENGINE,files
from finalize_evidence import sanitize
S=ROOT/'_scratch/ph_lw_10';W=ROOT/'_workspace/PH_LW_10';O=ENGINE/'PH_LW_10_LOGS'
def read(p):return json.loads(p.read_text('utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(sanitize(json.dumps(v,ensure_ascii=False,indent=2))+'\n','utf-8')
def main():
    frozen=read(S/'FINAL_BUILD_FREEZE.json');source=ENGINE/'src/project_harness'
    assert frozen['source_hashes']=={p.relative_to(source).as_posix():sha(p) for p in files(source)}
    assert frozen['test_hashes']=={p.relative_to(ENGINE).as_posix():sha(p) for folder in (ENGINE/'tests',ENGINE/'local_web') for p in files(folder)}
    assert frozen['wheel_sha256']==sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl')
    initial=read(S/'INITIAL_BUILD_FREEZE.json')
    source_delta=[k for k,v in initial['source_hashes'].items() if frozen['source_hashes'][k]!=v]
    test_delta=[k for k,v in initial['test_hashes'].items() if frozen['test_hashes'][k]!=v]
    assert set(source_delta)=={'local_web_service.py','resources/local_web/assets/approvals.js','resources/local_web/metadata_v1.json'},source_delta
    assert test_delta==['tests/test_ph_lw_10_lifecycle.py'],test_delta
    pre_ui=read(S/'PRE_APPROVAL_FIX_BUILD_FREEZE.json')
    ui_delta=[k for k,v in pre_ui['source_hashes'].items() if frozen['source_hashes'][k]!=v]
    assert set(ui_delta)=={'local_web_service.py','resources/local_web/assets/approvals.js','resources/local_web/metadata_v1.json'},ui_delta
    pre_poll=read(S/'PRE_POLLING_FIX_BUILD_FREEZE.json')
    polling_delta=[k for k,v in pre_poll['source_hashes'].items() if frozen['source_hashes'][k]!=v]
    assert set(polling_delta)=={'local_web_service.py','resources/local_web/metadata_v1.json'}
    with zipfile.ZipFile(S/'before-polling-fix.whl') as z:
        old_service=z.read('project_harness/local_web_service.py').decode('utf-8')
    def methods(code):
        tree=ast.parse(code);cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='LocalWebService')
        return {x.name:ast.dump(x) for x in cls.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))}
    old_methods=methods(old_service);new_methods=methods((source/'local_web_service.py').read_text('utf-8'))
    assert old_methods.keys()==new_methods.keys()
    assert {k for k in old_methods if old_methods[k]!=new_methods[k]}=={'_registered','get_operation'}
    test_path=ENGINE/'tests/test_ph_lw_10_lifecycle.py'
    old_test=re.sub(r'class MigrationPollingTests\(unittest.TestCase\):.*?(?=class LifecycleServiceTests)', '',test_path.read_text('utf-8'),flags=re.S)
    assert hashlib.sha256(old_test.encode()).hexdigest()==pre_ui['test_hashes']['tests/test_ph_lw_10_lifecycle.py']
    assert {k for k,v in pre_ui['test_hashes'].items() if frozen['test_hashes'][k]!=v}=={'tests/test_ph_lw_10_lifecycle.py'}
    save(S/'BUILD_DELTA.json',{'initial_digest':initial['engine_build_digest'],'final_digest':frozen['engine_build_digest'],
        'changed_source_files':source_delta,'changed_test_files':test_delta,
        'reason':'Scope new controls by root kind/unique IDs; deduplicate approval reads; keep owned migration receipt polling independent of mutable migration trees. Existing tests/core algorithms unchanged.',
        'pre_ui_fix_digest':pre_ui['engine_build_digest'],'ui_fix_source_delta':ui_delta,
        'polling_fix_digest_before':pre_poll['engine_build_digest'],'polling_fix_source_delta':polling_delta,
        'service_methods_changed_at_polling_fix':['_registered','get_operation'],
        'test_addition':'MigrationPollingTests only; all pre-existing test bytes reconstructed and verified',
        'rechecked':['all PH-LW-04–10 browser/HTTP modules on source','all applicable installed browser/HTTP modules plus native picker',
          'tests.test_ph_lw_01_contract','tests.test_ph_lw_03_service','migration confirmation/replay, process crash recovery, legacy migration, new deterministic polling race'],
        'unchanged_evidence':'All core algorithms and lifecycle mutators unchanged; final source/wheel recheck covers changed receipt reading and UI paths. Unaffected cases retain complete prior evidence.'})
    native=read(S/'native-accepted/PH_LW_10_WINDOWS_TEST_REPORT.json');assert native['status']=='FAIL',native
    check=native['checks'][0];assert not check['skips'] and check['failures']==1 and check['errors']==0
    assert all(r['status']=='PASS' for r in native['checks'][1:])
    failed_case='test_edge_four_five_separate_forms_stale_tabs_reload_receipts_and_xss (tests.test_ph_lw_07_http.ApprovalBrowserTests.test_edge_four_five_separate_forms_stale_tabs_reload_receipts_and_xss)'
    native_log=(S/'native-accepted/stage_tests.log').read_text('utf-8')
    assert re.findall(r'^(?:FAIL|ERROR): (.+)$',native_log,re.M)==[failed_case]
    verified=read(S/'source-verified/tests.json');assert verified['status']=='PASS' and not verified['skips']
    ui_log=(S/'source-verified/tests.log').read_text('utf-8')
    verified_ids=set(re.findall(r'^test\S+ \((tests\.[^)]+)\) \.\.\.',ui_log,re.M))
    verified_counts=Counter('.'.join(x.split('.')[:2]) for x in verified_ids)
    assert sum(verified_counts.values())==verified['ran']
    ui_counts={m:n for m,n in verified_counts.items() if m not in {'tests.test_ph_lw_01_contract','tests.test_ph_lw_03_service','tests.test_ph_lw_10_lifecycle'}}
    ui={'ran':sum(ui_counts.values())}
    assert set(ui_counts)=={'tests.test_ph_lw_04_http','tests.test_ph_lw_05_http','tests.test_ph_lw_04_05_acceptance','tests.test_ph_lw_06_http','tests.test_ph_lw_07_http','tests.test_ph_lw_08_http','tests.test_ph_lw_09_http','tests.test_ph_lw_10_http'}
    installed_parts=[];installed_ids=[]
    for part in ('main','native'):
        expected='FAIL' if part=='main' else 'PASS'
        assert read(S/f'runs/installed-{part}.run.json')['status']==expected
        wheel_log=(S/f'runs/installed-{part}.log').read_text('utf-8')
        assert '"source_import": false' in wheel_log and '"skips": 0' in wheel_log
        assert re.findall(r'^(?:FAIL|ERROR): (.+)$',wheel_log,re.M)==([failed_case] if part=='main' else [])
        count=int(re.search(r'^Ran (\d+) tests? in ',wheel_log,re.M).group(1))
        ids=re.findall(r'^test\S+ \((tests\.[^)]+)\) \.\.\.',wheel_log,re.M)
        assert len(ids)==count
        installed_ids+=ids;installed_parts.append({'part':part,'tests':count,'status':expected,'build_digest':pre_ui['engine_build_digest'],'evidence':f'runs/installed-{part}.run.json'})
    assert len(installed_ids)==len(set(installed_ids))
    new_case='tests.test_ph_lw_10_lifecycle.MigrationPollingTests.test_owned_receipt_remains_readable_during_backup_cleanup'
    assert new_case in verified_ids
    migration_rechecks={new_case,*('tests.test_ph_lw_10_lifecycle.LifecycleServiceTests.'+x for x in (
        'test_migration_validator_confirmation_replay_history','test_migration_process_crash_explicit_web_recovery_missing_root',
        'test_legacy_v041_migration_form_keeps_completed_runs'))}
    assert {x for x in verified_ids if x.startswith('tests.test_ph_lw_10_lifecycle.')}==migration_rechecks
    assert verified_counts['tests.test_ph_lw_01_contract']==9 and verified_counts['tests.test_ph_lw_03_service']==15
    assert set(verified_counts)==set(ui_counts)|{'tests.test_ph_lw_01_contract','tests.test_ph_lw_03_service','tests.test_ph_lw_10_lifecycle'}
    installed_ui=(S/'runs/installed-verified.log').read_text('utf-8')
    assert read(S/'runs/installed-verified.run.json')['status']=='PASS'
    assert '"source_import": false' in installed_ui and '"skips": 0' in installed_ui and frozen['engine_build_digest'] in installed_ui
    installed_ui_ids=re.findall(r'^test\S+ \((tests\.[^)]+)\) \.\.\.',installed_ui,re.M)
    assert set(installed_ui_ids)<=set(installed_ids)|{new_case}
    assert len(installed_ui_ids)==int(re.search(r'^Ran (\d+) tests? in ',installed_ui,re.M).group(1))
    expected_ui_ids={x for x in installed_ids if '.'.join(x.split('.')[:2]) in set(ui_counts)-{'tests.test_ph_lw_04_http'} or x.startswith('tests.test_ph_lw_10_lifecycle.NativeSelectionTests.')}
    expected_ui_ids|={x for x in verified_ids if x.startswith('tests.test_ph_lw_10_lifecycle.')}
    assert set(installed_ui_ids)==expected_ui_ids
    installed_parts.append({'part':'verified','tests':len(installed_ui_ids),'status':'PASS','build_digest':frozen['engine_build_digest'],
        'supersedes':'All corresponding browser/HTTP, migration/recovery methods and native picker in main/native runs','evidence':'runs/installed-verified.run.json'})
    installed_ids.append(new_case);wheel_count=len(installed_ids)
    log=(S/'native-accepted/stage_tests.log').read_text('utf-8')
    counts=Counter(re.findall(r'^test\S+ \((tests\.[^.]+)\.[^)]+\) \.\.\.',log,re.M));assert sum(counts.values())==check['ran']
    new_native=set(re.findall(r'^test\S+ \((tests\.test_ph_lw_10[^)]+)\) \.\.\.',log,re.M))
    new_native.add(new_case);counts['tests.test_ph_lw_10_lifecycle']+=1
    native_current_count=sum(counts.values())
    assert {x for x in installed_ids if x.startswith('tests.test_ph_lw_10')}==new_native
    command=read(S/'runs/native-accepted.run.json')['command'];rows=read(S/'core-final/MATRIX.json')
    for row in rows:row['evidence']='core-final/'+row['log']
    revised=read(S/'core-service-recheck/MATRIX.json')
    assert {r['module'] for r in revised}=={'tests.test_ph_lw_01_contract','tests.test_ph_lw_03_service'}
    for row in revised:
        assert row['status']=='PASS' and not row['skips']
        row['evidence']='core-service-recheck/'+row['log'];row['supersedes']='core-final/'+row['log']
        rows=[row if r['module']==row['module'] else r for r in rows]
    rows += [{'module':module,'command':command,'status':'PASS','ran':count,'failures':0,'errors':0,'skips':[],
        'log':'native-accepted/stage_tests.log','evidence':'native-accepted/PH_LW_10_WINDOWS_TEST_REPORT.json'} for module,count in counts.items()]
    for row in rows:
        if row['module'] in verified_counts:
            if row['module']=='tests.test_ph_lw_10_lifecycle':
                row.update(evidence_parts=['native-accepted/stage_tests.log','source-verified/tests.log'],
                    selected_recheck_test_ids=sorted(x for x in verified_ids if x.startswith(row['module']+'.')))
            else:
                assert row['ran']==verified_counts[row['module']]
                row.update(command=read(S/'runs/source-verified.run.json')['command'],log='source-verified/tests.log',evidence='source-verified/tests.log',supersedes=row['evidence'])
    assert len(rows)==len({r['module'] for r in rows})
    assert {r['module'] for r in rows}=={'tests.'+p.stem for p in (ENGINE/'tests').glob('test_*.py')}
    prior_dir=ENGINE/'PH_LW_09_MANUAL_EVIDENCE_LOGS';old={r['module']:r for r in read(prior_dir/'REGRESSION_MATRIX_CURRENT.json')['rows']}
    comparisons=[];failed=[]
    for row in rows:
        if row['module'] not in old:assert row['status']=='PASS';continue
        prior=old[row['module']]
        differences={k:{'previous':prior[k],'current':row[k]} for k in ('status','ran','failures','errors') if prior[k]!=row[k]}
        assert not differences,(row['module'],differences)
        assert len(row['skips'])==len(prior['skips'])
        comparisons.append({'module':row['module'],'differences':differences})
        if row['status']=='FAIL':
            def ids(p):return sorted(re.findall(r'^(?:FAIL|ERROR): (.+)$',p.read_text('utf-8'),re.M))
            a=ids(prior_dir/prior['evidence']);b=ids(S/row['evidence']);assert a==b,(row['module'],a,b)
            failed.append({'module':row['module'],'same_failed_test_ids':True,'previous':a,'current':b})
    stats={'modules':len(rows),'test_methods':sum(r['ran'] for r in rows),'module_statuses':dict(Counter(r['status'] for r in rows)),
        'failure_events':sum(r['failures'] for r in rows),'error_events':sum(r['errors'] for r in rows),'skips':sum(len(r['skips']) for r in rows),
        'timeouts':sum(r['status']=='TIMEOUT' for r in rows),'mandatory_not_run':[]}
    assert stats['module_statuses'].get('FAIL')==7 and not stats['timeouts']
    assert next(r for r in rows if r['module']=='tests.test_ph_f06_maturity_lifecycle')['status']=='PASS'
    O.mkdir(exist_ok=False);index=[]
    folders={'runs','native-accepted','native-final','core-final','core-service-recheck','screenshots-final','screenshots-accepted','screenshots-wheel','screenshots-fifth','screenshots-sixth','screenshots-fourth',
        'ui-final','approval-recheck','approval-diagnostic','approval-diagnostic-repeat','approval-fixed-diagnostic','screenshots-ui-final','screenshots-wheel-ui-final',
        'source-verified','polling-diagnostic','screenshots-verified','screenshots-wheel-verified'}
    for raw in sorted(S.rglob('*')):
        if not raw.is_file() or raw.suffix not in {'.log','.json','.md','.png'}:continue
        rel=raw.relative_to(S)
        if len(rel.parts)>1 and rel.parts[0] not in folders:continue
        target=O/rel;target.parent.mkdir(parents=True,exist_ok=True)
        if raw.suffix=='.png':target.write_bytes(raw.read_bytes())
        else:target.write_text(sanitize(raw.read_text('utf-8',errors='replace')),'utf-8')
        index.append({'raw_source':raw.relative_to(ROOT).as_posix(),'file':rel.as_posix(),'raw_sha256':sha(raw),'published_sha256':sha(target)})
    save(O/'EVIDENCE_INDEX.json',index)
    save(O/'REGRESSION_MATRIX_CURRENT.json',{'status':'FAIL',**stats,'rows':sorted(rows,key=lambda r:r['module'])})
    save(O/'PREVIOUS_BASELINE_COMPARISON.json',{'status':'NO_NEW_REGRESSIONS','previous_modules':comparisons,'inherited_failures':failed})
    verdict={'status':'PASS','tests':native_current_count,'skips':[],'installed_wheel_tests':wheel_count,
        'ph_lw_10_tests':sum(n for m,n in counts.items() if m.startswith('tests.test_ph_lw_10')),
        'source':'native-accepted/PH_LW_10_WINDOWS_TEST_REPORT.json','installed_parts':installed_parts,
        'monolithic_native_status':native['status'],'native_method':'Composite: full 182-method run plus final UI/HTTP/service/migration rechecks and one added deterministic polling test; immutable core and old tests verified by hashes',
        'native_final_ui_tests':ui['ran'],'native_final_ui_status':'PASS','native_final_ui_source':'source-verified/tests.json','final_source_recheck_tests':verified['ran'],
        'installed_method':'Composite: main/native runs plus final installed browser/HTTP/migration/native-picker recheck and new deterministic polling test; original main FAIL preserved',
        'ph_f06':'13 PASS, 0 SKIP',
        'mandatory_not_run':[]}
    save(O/'NATIVE_SCOPE_VERDICT.json',verdict)
    save(O/'BUILD_PROVENANCE.json',{'build_id':'PH-LW-10-20261107','engine_build_digest':frozen['engine_build_digest'],
        'wheel_sha256':frozen['wheel_sha256'],'input':read(W/'INPUT_BASELINE.json'),'zip_created':False})
    report=f'''# PH-LW-10 — фактическая приёмка Stage lifecycle

2026-11-07. **PH-LW-10: PASS в назначенном manual scope.** Реализован полный prompt r2 на проверенной распакованной базе PH-LW-09 manual evidence. Automatic executor выключен; PH-LW-11 не выполнялся; Engine/Documentation ZIP не создавались. Требование ZIP-пары исторического prompt заменено явным указанием пользователя от 2026-11-07; исходный prompt сохранён.

## База и допустимые изменения

[Входной baseline](../_workspace/PH_LW_10/INPUT_BASELINE.json), [input hashes](../_workspace/PH_LW_10/INPUT_FILE_HASHES.json), [предыдущий CURRENT_TASK](../_workspace/PH_LW_10/CURRENT_TASK.before.md). Проверены manifests распакованных Engine/Documentation, прежний wheel и workspace checkpoint. Исторические NO-GO, input archives/specifications/r2, core schemas/registries и прежние test files сохранены.

Allowed changes: Local Web lifecycle adapters/public form helpers, service/HTTP/assets integration, новые PH-LW-10 tests/Windows runner, операторская глава и docs mirrors, metadata/generated wheel/manifests, новые reports/evidence/workspace tooling/navigation. Core governance, evidence resolver, migration algorithm, statuses и accepted scope не переписаны.

## Реализованное поведение

Stage overview разделяет canonical current-cycle target, active, claimed, observed и highest accepted; отображает exact semantic gaps и read-only acceptance/Run/evidence history. `prepare_stage_approval` создаёт unsigned form; каждый subject имеет отдельный status/rationale/validator/evidence. Actor/DEC/time появляются только после explicit action. `accept_stage` сохраняет реальные BLOCKED/FAIL; missing/unknown/forged proof не повышает maturity.

Active Stage plan проходит public preparation и strict reviewed schema. Exact context server-owned; изменённый work plan требует существующего `ACTIVE_STAGE_PLAN_REVIEW` с rationale; неизменённый не получает выдуманного Decision. `plan_active_stage` открывает только ближайшую Stage и первый READY JIT. Material scope divergence отклоняется. Level-up использует canonical target; проверены Prototype→Alpha при target RELEASE, accepted MVP→RELEASE, no-op и отказ незавершённого cycle.

Maintenance form покрывает обязательные Task/scope/verification/documentation поля и вызывает existing `start_maintenance`. Проверены обычное completion и допустимая отмена; после completed product change cancel запрещён. Stage recovery отделён от обычного Task blocker. Accepted history сохраняется по exact hashes.

Brownfield/Hybrid repository выбирается явно и читается без repository commands. New intake размещается отдельно; inventory/current revision/tree digest привязаны к запросу. Assessment показывает UNKNOWN gaps и отдельную необходимость baseline approval; README claim не принимается за proof; stale source отвергается.

Migration preview использует validator и explicit confirmation. Проверены v0.5.0 и v0.4.1, default MANUAL_HANDOFF, completed Run/history preservation, replay/NO_ACTION и настоящие process-exit interruptions после old/new rename. Recovery требует отдельный POST и existing journal; GET ничего не чинит. В legacy v0.4.1 converter отсутствие execution в lock означает существующий schema default MANUAL_HANDOFF; режим проверен через public Task view, core не изменён.

Exact-byte сохранение `PROJECT_INPUT_ACCEPTED` проверено для v0.5.0→v0.5.1. Legacy v0.4.1 converter по существующему контракту нормализует этот файл и фиксирует прежний digest в migration report; для него проверено сохранение completed Runs, а не неизменность legacy input bytes. Эти version-specific правила явно отражены в операторской документации. UI не расширяет допустимые изменения legacy input и не принимает maturity по completed history.

HTTP mutations сохраняют exact Host/Origin/port, session/CSRF, revision/fingerprint, ownership, idempotency и общий fence. Native folder picker вызывается фиксированным absolute system PowerShell path; HTTP не принимает path/command. Проверены реальное Windows dialog selection/cancel, узкий service picker contract и readonly source. Никакого shell/filesystem gateway, provider API, host Codex fallback, LAN listener, external fetch/CDN/telemetry.

После canonical commit сверка использует exact kernel transaction digest и не повторяет mutator. Reload может пересечься с предыдущим GET: UI объединяет совпадающие чтения и ограниченно повторяет только GET при `OPERATION_CONFLICT` (12 × 250 ms). POST не повторяется. Guard и test deadlines не ослаблены.

## Фактические результаты

| Проверка | Результат |
|---|---|
| Новые PH-LW-10 service/HTTP/native dialog/Edge tests | {verdict['ph_lw_10_tests']} PASS, 0 SKIP в source и installed wheel |
| Native PH-LW-04–10 current matrix | {native_current_count} unique methods PASS, 0 SKIP; полный исходный run + {verified['ran']}-test recheck (включая {ui['ran']} browser/HTTP cases) и новый polling race test; doctor/docs PASS |
| Installed wheel, отдельная venv/Unicode CWD/site-packages | {wheel_count} unique methods PASS, 0 SKIP; исходные main/native + {len(installed_ui_ids)}-test final browser/HTTP/migration/native recheck; console doctor/launcher/TCP health PASS |
| PH-F06 public lifecycle | 13 PASS, 0 SKIP |
| Полная свежая matrix | {stats['modules']} modules / {stats['test_methods']} methods; {stats['module_statuses']['PASS']} PASS / {stats['module_statuses']['PASS_WITH_SKIPS']} PASS_WITH_SKIPS / 7 FAIL |
| Failure/error/skip/module-timeout events | {stats['failure_events']} / {stats['error_events']} / {stats['skips']} / {stats['timeouts']} |

Стенд: настоящий Windows 11 x64/NTFS/non-admin, CPython 3.14.10 x64, pinned Flask 3.1.3/Waitress 3.0.2, реальный Waitress TCP и Edge. [Исходный native report](PH_LW_10_LOGS/native-accepted/PH_LW_10_WINDOWS_TEST_REPORT.json), [final source recheck](PH_LW_10_LOGS/source-verified/tests.json), [installed main](PH_LW_10_LOGS/runs/installed-main.run.json), [final installed recheck](PH_LW_10_LOGS/runs/installed-verified.run.json), [полная matrix](PH_LW_10_LOGS/REGRESSION_MATRIX_CURRENT.json), [сравнение с базой](PH_LW_10_LOGS/PREVIOUS_BASELINE_COMPARISON.json). Native picker сериализован отдельно от source dialog. Все cases выполнены; coverage и supersession проверены по точным IDs. Семь прежних FAIL имеют те же failed IDs; они не объявлены PASS. Все прежние модули повторены, незакрытых новых regression failures в current matrix нет. Mandatory NOT RUN назначенного scope отсутствует.

Ранние диагностические FAIL/ERROR сохранены отдельно: некорректные исходные defaults/fixture binding, коллизия JS identifiers, shadowing document, конкурирующие GET, повторная подготовка уже готового Gate, ожидание обязательного execution key в legacy lock. Browser migration replay воспроизвёл explicit operation-fence conflict после reload; ограниченный read-only retry устранил его без автоматического mutation. Исправления не ослабляют semantic assertions.

Первый native attempt (`native-final`) явно ABORTED до PH-LW-10 cases, когда core regression обнаружил лишние lifecycle controls в GREENFIELD workspace (32 вместо прежних 27). Production fix ограничил новые helpers совместимым kind и выдал уникальные UI IDs. Исходный PH-LW-03 test не менялся; полный 15-test recheck PASS, inventory/metadata PH-LW-01 — 9 PASS. Их rows явно supersede первоначальные core attempts; исходный FAIL сохранён.

Затем полные source/installed прогоны выявили один и тот же прежний PH-LW-07 browser case: approvals counter не менялся за исходные 5000 ms. Native `native-accepted` — 182 methods, 1 FAIL; installed `main` — 179 methods, 1 FAIL. **Эти монолитные прогоны не объявлены PASS.** Все исходные 28 PH-LW-10 cases в них прошли; 29-й polling test добавлен позднее. Диагностика воспроизвела сбой в двух из трёх runs: параллельные `loadApprovals()` получали поздний GET и повторно создавали consent fields, POST решения не отправлялся. Это direct UI regression, а не допустимый semantic failure. Исправление в `approvals.js` объединяет чтения одной формы и проверяет выбранный project; GET остаётся read-only, POST не повторяется.

После fix три последовательных исходных browser cases прошли с теми же assertions и deadlines. [Trace до fix](PH_LW_10_LOGS/approval-diagnostic-repeat/REQUEST_TIMING.json), [состояние UI](PH_LW_10_LOGS/approval-diagnostic-repeat/LAST_UI_STATE.json), [после fix](PH_LW_10_LOGS/runs/approval-fixed-diagnostic.run.json). Промежуточный full PH-LW-07 recheck также получил отдельный WinError 10055 при TCP connect; он сохранён и закрыт новым полным HTTP-module PASS. Причина системной socket error не доказана; системные настройки не менялись.

Следующий `ui-final` run сохранил два отказа: один старый test запросил отсутствующий bundled Chromium, поскольку ручная команда не передала `PH_LW_04_BROWSER_CHANNEL=msedge`; новый migration UI case остановил polling на RUNNING. Первый — ошибка команды запуска. Для второго добавлен deterministic interleaving test: реальный core удаляет backup после rename между перечислением и хешированием файлов polling. Он воспроизвёл `FileNotFoundError` в `_registered` при чтении app-owned operation receipt. После узкого fix `get_operation` проверяет digest/ownership/catalog/native ancestor path, не сканируя меняющийся migration tree; mutation/recovery проверки сохранены. [До fix](PH_LW_10_LOGS/runs/polling-race-before.run.json), [после fix](PH_LW_10_LOGS/runs/polling-race-after.run.json). Existing migration algorithm не изменён. У исходного browser timeout не сохранён server exception trace, поэтому точная причинная связь именно того occurrence с доказанной гонкой остаётся inference; воспроизводимая гонка устранена, browser case повторён успешно.

Последний source recheck использует явный Edge и охватывает все browser/HTTP modules, полный PH-LW-01/03, migration/replay/process-crash/legacy и новый polling test; соответствующие UI/migration/picker cases повторены из окончательного wheel. Все финальные rechecks PASS. [Build delta](PH_LW_10_LOGS/BUILD_DELTA.json) проверяет source hashes и AST: после полных прогонов изменились approvals.js, только методы `_registered`/`get_operation` LocalWebService и generated metadata; в tests добавлен только новый класс, старые bytes восстановлены и сверены. Core algorithms/lifecycle mutators и остальные assets идентичны. Итоговый native/installed verdict — composite по уникальным methods с явным supersession и проверенными hashes, а не новый монолитный exit 0. Общая performance/stress гарантия не заявляется.

В raw stdout также сохранены Waitress queue/connection-limit diagnostics и WinError 10038 фонового server thread при закрытии тестового сервера. Они не удалены из успешного 77-test run; unittest итог — 0 failures/errors/skips. Штатная приёмка маршрутов и guarantee отсутствия всех teardown diagnostics — разные утверждения; последнее этим этапом не заявляется.

Standalone docs validator PASS; единственный WARN — ZIP не передан по явному указанию пользователя. [Покрытие девяти пунктов prompt](PH_LW_10_LOGS/REQUIREMENT_COVERAGE.json) связано с конкретными tests. Диагностические probes не используются как frozen acceptance.

## Outputs, границы и следующий шаг

Build `PH-LW-10-20261107`; source digest `{frozen['engine_build_digest']}`; wheel SHA-256 `{frozen['wheel_sha256']}`. [Evidence index](PH_LW_10_LOGS/EVIDENCE_INDEX.json), [changed files](PH_LW_10_CHANGED_FILES.md), [финальная аттестация](../_workspace/PH_LW_10/FINAL_WORKING_TREE_VERIFICATION.json), [output SHA-256](../_workspace/PH_LW_10/SHA256.txt). Команды/CWD/platform/exit/log hashes — в run metadata; interpreter/deps — SOURCE_ENVIRONMENT/WHEEL_ENVIRONMENT. Docs mirror, build/lib и wheel сверены с текущими рабочими файлами; private auth/uploads/cache/venv не включены.

Исторические archives неизменны. ZIP внутри synthetic compiler/migration fixtures — входы/outputs тестов, не поставочные Engine/Documentation архивы. Review observations и actor — явные заявления оператора, не криптографическое удостоверение истинности или личности. Process fault injection не доказывает physical power-loss guarantees. Clean-machine installer, полный end-to-end PH-LW-12, реальный Codex, rootless Podman security и positive governed per-Run egress не входят в этот этап.

PH-LW-04–10 PASS в своих scopes. `LOCAL_WEB_MANUAL: NO-GO` до PH-LW-12; `AUTOMATIC_EXECUTOR: NO-GO`; полная v0.5.1 `NO-GO / NOT RELEASED`. Следующий этап — только по новому заданию пользователя. PH-LW-11 не начат.
'''
    (ENGINE/'PH_LW_10_TEST_REPORT.md').write_text(report,'utf-8')
    (O/'README.md').write_text('Frozen final source/core/wheel evidence and earlier diagnostics. EVIDENCE_INDEX binds raw and redacted copies. Private runtime data excluded. Historical evidence preserved.\n','utf-8')
    save(W/'RESULT_SUMMARY.json',{'stage_verdict':'PASS','native':verdict,'matrix':stats})
    print(json.dumps({'stage_verdict':'PASS','native':verdict,'matrix':stats},indent=2))
if __name__=='__main__':main()
