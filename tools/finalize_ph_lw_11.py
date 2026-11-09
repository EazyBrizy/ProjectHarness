"""Publish PH-LW-11 evidence; unavailable mandatory acceptance stays NO-GO."""
from collections import Counter
import hashlib,json,re,shutil,sys,unittest
from pathlib import Path
from package_acceptance import ROOT,ENGINE,files
from finalize_evidence import sanitize
S=ROOT/'_scratch/ph_lw_11';W=ROOT/'_workspace/PH_LW_11';O=ENGINE/'PH_LW_11_LOGS'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(sanitize(json.dumps(v,ensure_ascii=False,indent=2))+'\n','utf-8')
def test_ids(p):return re.findall(r'^test\S+ \((tests\.[^)]+)\)',p.read_text('utf-8-sig'),re.M)
def failed_ids(p):return sorted(re.findall(r'^(?:FAIL|ERROR): (.+)$',p.read_text('utf-8-sig'),re.M))

def observed(p):
    """Completed unittest method outcomes; interrupted methods never become PASS."""
    content=p.read_text('utf-8-sig')
    starts=list(re.finditer(r'^test\S+ \((tests\.[^)]+)\)(?: \.\.\.)?[ \t]*',content,re.M));out={}
    for i,start in enumerate(starts):
        part=content[start.end():starts[i+1].start() if i+1<len(starts) else len(content)]
        part=re.split(r'^={20,}|^-{20,}',part,maxsplit=1,flags=re.M)[0]
        if re.search(r'(?:^|\.\.\. )ERROR\s*$',part,re.M):status='ERROR'
        elif re.search(r'(?:^|\.\.\. )FAIL\s*$',part,re.M):status='FAIL'
        elif re.search(r'(?:^|\.\.\. )skipped ',part,re.M):status='SKIP'
        elif re.search(r'(?:^|\.\.\. )ok\s*$',part,re.M):status='PASS'
        else:continue
        out[start.group(1)]={'status':status,'evidence':p.relative_to(S).as_posix()}
        if status=='SKIP':
            out[start.group(1)]['reason']=re.search(r'(?:^|\.\.\. )skipped (.+)$',part,re.M).group(1)
    return out

def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from flatten(item)
        else:yield item.id()

def main():
    frozen=read(S/'FINAL_BUILD_FREEZE.json');src=ENGINE/'src/project_harness'
    assert frozen['source_hashes']=={p.relative_to(src).as_posix():sha(p) for p in files(src)}
    assert frozen['test_hashes']=={p.relative_to(ENGINE).as_posix():sha(p) for d in (ENGINE/'tests',ENGINE/'local_web') for p in files(d)}
    assert frozen['wheel_sha256']==sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl')
    assert frozen['installer_sha256']==sha(S/'build-docs-final/Harness-Setup-win-x64.exe')
    old=read(S/'PRE_UPLOAD_FIX_BUILD_FREEZE.json')
    pre_tab=read(S/'PRE_TAB_RESUME_FREEZE.json')
    delta=[k for k in old['source_hashes'] if old['source_hashes'][k]!=pre_tab['source_hashes'][k]]
    assert set(delta)=={'resources/local_web/assets/app.js','resources/local_web/metadata_v1.json'},delta
    save(S/'UPLOAD_FIX_DELTA.json',{'before_digest':old['engine_build_digest'],'after_digest':pre_tab['engine_build_digest'],
        'changed_source_files':delta,'reproduction':'runs/upload-race-repro.log','fixed':'runs/upload-race-fixed.log',
        'previous_tests_unchanged':True,'fix':'Publish upload success after awaited refresh and release of requestBusy; no assertion/deadline changes'})
    delta=[k for k in pre_tab['source_hashes'] if pre_tab['source_hashes'][k]!=frozen['source_hashes'][k]]
    assert set(delta)=={'resources/local_web/assets/app.js','resources/local_web/metadata_v1.json'},delta
    save(S/'TAB_RESUME_DELTA.json',{'before_digest':pre_tab['engine_build_digest'],'after_digest':frozen['engine_build_digest'],
        'changed_source_files':delta,'reproduction':'runs/tab-resume-before.log','fixed':'runs/desktop-source-tab-final.log',
        'previous_tests_unchanged':True,'new_desktop_methods':18,
        'fix':'Launcher/manual-code restores global screen; fresh cookie tab starts at project selector; reload uses tab screen. Only app.js and generated metadata changed after previous regression runs.'})
    runner_before=read(S/'PRE_INSTALLER_TEST_WINDOW_FREEZE.json')
    pre_docs=read(S/'PRE_DOCS_FREEZE.json')
    runner_delta=[k for k in runner_before['test_hashes'] if runner_before['test_hashes'][k]!=frozen['test_hashes'][k]]
    assert runner_delta==['local_web/windows/installer_fault_acceptance.py'],runner_delta
    assert all(runner_before[k]==pre_docs[k] for k in ('source_hashes','wheel_sha256','installer_sha256','package_manifest_sha256'))
    save(S/'INSTALLER_TEST_RUNNER_DELTA.json',{'files':runner_delta,'before_sha256':runner_before['test_hashes'][runner_delta[0]],
        'after_sha256':frozen['test_hashes'][runner_delta[0]],'artifact_inputs_unchanged':True,
        'change':'Bound observation by 120 seconds wall clock rather than 1200 x 10ms; same observed-real-copy/kill/no-commit/retry assertions. Initial 12-second attempt expired before helper copy began.'})
    assert all(pre_docs[k]==frozen[k] for k in ('source_hashes','test_hashes','wheel_sha256'))
    a=read(S/'build-tab-final/frozen/Harness/PACKAGE_FILES.json')['files']
    b=read(S/'build-docs-final/frozen/Harness/PACKAGE_FILES.json')['files']
    changed=sorted(k for k in set(a)|set(b) if a.get(k)!=b.get(k))
    generated={'Harness.exe','_internal/base_library.zip'}
    assert all(k.startswith('_internal/documentation/') or k in generated for k in changed),changed
    save(S/'DOCS_ONLY_DELTA.json',{'before_installer_sha256':pre_docs['installer_sha256'],
        'after_installer_sha256':frozen['installer_sha256'],'source_and_wheel_unchanged':True,
        'frozen_runtime_bytes_identical':False,'changed_frozen_files':changed,
        'generated_container_differences':[k for k in changed if k in generated],
        'fix':'Documentation metadata header and README status wording; validator unchanged, 0 errors. Final installer rebuilt and native acceptance repeated.'})
    # Method-level composite retains aborted runs, TIMEOUT and absent cases.
    raw_rows=read(S/'regressions/MATRIX.json')
    sys.path[:0]=[str(ENGINE/'src'),str(ENGINE)]
    modules=['tests.'+p.stem for p in sorted((ENGINE/'tests').glob('test_*.py'))]
    expected={m:set(flatten(unittest.defaultTestLoader.loadTestsFromName(m))) for m in modules}
    outcomes={}
    for raw in raw_rows:
        path=S/'regressions'/(raw['module'].removeprefix('tests.')+'.log')
        complete=observed(path);outcomes.update(complete)
        for pending in set(test_ids(path))-set(complete):
            outcomes[pending]={'status':'TIMEOUT' if raw['status']=='TIMEOUT' else 'ABORTED','evidence':path.relative_to(S).as_posix()}
    native_partial=observed(S/'native-ui-final/previous/stage_tests.log');outcomes.update(native_partial)
    for pending in set(test_ids(S/'native-ui-final/previous/stage_tests.log'))-set(native_partial):
        outcomes.setdefault(pending,{'status':'ABORTED','evidence':'native-ui-final/previous/stage_tests.log'})
    for name in ('desktop-source-isolated','upload-race-fixed','lifecycle-frozen-recheck','desktop-source-settled'):
        outcomes.update(observed(S/'runs'/f'{name}.log'))
    wheel_log=S/'runs/installed-nonbrowser-final.log';wheel_outcomes=observed(wheel_log);wheel_ids=list(wheel_outcomes)
    assert read(S/'runs/installed-nonbrowser-final.run.json')['status']=='PASS'
    assert '"source_import": false' in wheel_log.read_text('utf-8') and all(x['status']=='PASS' for x in wheel_outcomes.values())
    outcomes.update(wheel_outcomes)
    for name in ('installed-settled-final','installed-tab-final'):
        settled_log=S/'runs'/f'{name}.log'
        if (S/'runs'/f'{name}.run.json').exists():
            settled=observed(settled_log)
            assert '"source_import": false' in settled_log.read_text('utf-8')
            outcomes.update(settled)
            wheel_ids=sorted(set(wheel_ids)|set(settled))
    outcomes.update(observed(S/'runs/desktop-source-tab-final.log'))
    rows={}
    for module,ids in expected.items():
        methods=[{'id':i,**outcomes.get(i,{'status':'NOT RUN','evidence':None})} for i in sorted(ids)]
        count=Counter(x['status'] for x in methods)
        state=('FAIL' if count['FAIL'] or count['ERROR'] else 'TIMEOUT' if count['TIMEOUT'] else 'PARTIAL' if count['ABORTED'] else
            'PARTIAL' if count['NOT RUN'] and len(count)>1 else 'NOT RUN' if count['NOT RUN'] else
            'PASS_WITH_SKIPS' if count['SKIP'] else 'PASS')
        rows[module]={'module':module,'status':state,'expected':len(ids),'ran':sum(x['status'] not in {'NOT RUN'} for x in methods),
            'failures':count['FAIL'],'errors':count['ERROR'],'skips':[x['id'] for x in methods if x['status']=='SKIP'],
            'method_statuses':dict(count),'methods':methods}
    counts=Counter(x['status'] for r in rows.values() for x in r['methods'])
    stats={'modules':len(rows),'test_methods':sum(r['expected'] for r in rows.values()),'method_statuses':dict(counts),
        'module_statuses':dict(Counter(r['status'] for r in rows.values())),
        'failure_events':sum(r.get('failures',0) for r in raw_rows),'error_events':sum(r.get('errors',0) for r in raw_rows),
        'raw_core_event_counts_note':'Original complete core results, including subtests; rechecks listed per method separately',
        'skips':counts['SKIP'],'timeouts':counts['TIMEOUT'],'not_run_methods':counts['NOT RUN']}
    if '--preview' in sys.argv:
        print(json.dumps({'stats':stats,'missing':[x['id'] for r in rows.values() for x in r['methods'] if x['status'] in {'NOT RUN','TIMEOUT','ABORTED'}]},ensure_ascii=False,indent=2))
        return
    assert all(outcomes[i]['status']=='PASS' for i in wheel_ids),'Installed wheel methods require successful final rechecks'
    prior_dir=ENGINE/'PH_LW_10_LOGS';prior={r['module']:r for r in read(prior_dir/'REGRESSION_MATRIX_CURRENT.json')['rows']}
    comparisons=[]
    for module,row in rows.items():
        if module not in prior:continue
        oldrow=prior[module]
        difference={} if row['status']==oldrow['status'] else {'status':{'previous':oldrow['status'],'current':row['status']}}
        old_skips=sorted(x['test'] if isinstance(x,dict) else x for x in oldrow['skips'])
        item={'module':module,'differences':difference,'skip_count_equal':len(oldrow['skips'])==len(row['skips']),
            'same_skipped_ids':old_skips==sorted(row['skips'])}
        if oldrow['status']=='FAIL':
            a=failed_ids(prior_dir/oldrow['evidence']);b=failed_ids(S/'regressions'/(module.removeprefix('tests.')+'.log'))
            item.update(same_failed_ids=a==b,previous=a,current=b)
        comparisons.append(item)
    same=all(not x['differences'] and x['same_skipped_ids'] and x.get('same_failed_ids',True) for x in comparisons)
    assert same,'Baseline comparison requires review before publication'
    installed=read(S/'installed-docs-final/RESULT.json');assert installed['status']=='PASS'
    faults=read(S/'installer-fault-docs-final/RESULT.json');assert faults['status']=='PASS'
    final_wheel=read(S/'runs/installed-tab-final.run.json');assert final_wheel['status']=='PASS'
    final_wheel_methods=observed(S/'runs/installed-tab-final.log')
    assert read(S/'runs/desktop-source-tab-final.run.json')['status']=='PASS'
    not_run=['Clean Windows machine without developer runtimes installed',
        'Actual Windows account with Unicode username','Physical offline preparation',
        'Real volume/quota disk-full (only injected ENOSPC available)']
    assert counts['NOT RUN']==0 and counts['TIMEOUT']==0 and counts['ABORTED']==0
    verdict={'status':'NO-GO','implementation':'BUILT; composite regression matrix complete with inherited FAIL/SKIP; mandatory acceptance gaps remain',
        'native_test_methods':sum(x['status']=='PASS' for x in native_partial.values()),'native_aggregate':'ABORTED, not PASS',
        'new_desktop_tests':18,'desktop_source':'18 PASS','desktop_upload_race':'PASS before/after fix evidence',
        'desktop_manual_login':'PASS source and installed wheel after transient Edge teardown issue; original TIMEOUT retained',
        'installed_wheel_test_methods':len(wheel_ids),'installed_exe':installed['tests'],
        'installed_wheel_final_recheck_methods':len(final_wheel_methods),
        'installed_wheel_scope':'Composite across recorded builds; final app.js/metadata delta rechecked in final wheel desktop, PH01, PH04 browser and PH07 browser tests',
        'installer_recovery':faults,'mandatory_not_run':not_run,
        'manual_blockers':['Long profile path with LongPathsEnabled=0: preparation staging copy PREPARATION_IO_BLOCKED; reproduced through public source API'],
        'local_web_manual':'NO-GO; PH-LW-12 not started','automatic_executor':'NO-GO; not enabled',
        'v0.5.1':'NO-GO / NOT RELEASED','zip_created':False}
    bindings=[]
    for path in sorted((S/'runs').glob('*.run.json')):
        record=read(path);command=record['command'];interpreter=command[0]
        env=('build-docs-final/BUILD_RESULT.json' if 'build-env' in interpreter else
             'WHEEL_ENVIRONMENT.json' if 'wheel-venv' in interpreter else 'SOURCE_ENVIRONMENT.json')
        bindings.append({'run':path.relative_to(S).as_posix(),'command_interpreter':interpreter,
            'environment':env,'platform':record['platform'],'status':record['status'],
            'note':'Dependency/runtime environment binding; exact build digest is in each run or freeze/delta evidence. Historical failed attempts retain their original result.'})
    for record in raw_rows:
        bindings.append({'run':'regressions/'+record['module'].removeprefix('tests.')+'.log',
            'command_interpreter':record['command'][0],'environment':'SOURCE_ENVIRONMENT.json',
            'platform':read(S/'SOURCE_ENVIRONMENT.json')['platform'],'status':record['status']})
    save(S/'RUN_ENVIRONMENT_BINDINGS.json',bindings)
    refresh='--refresh-docs' in sys.argv
    if refresh:
        assert read(W/'FINAL_WORKING_TREE_VERIFICATION.json')['status']!='PASS'
        assert (W/'verification-attempt-1/PH_LW_11_TEST_REPORT.md').exists()
    O.mkdir(exist_ok=refresh);index=[]
    # Explicit allowlist: never publish projects, uploads, auth, browser profiles,
    # venvs, tools or staging contents. Failed diagnostic runs remain visible.
    pairs=[]
    for p in S.iterdir():
        if p.is_file() and p.suffix=='.json':pairs.append(p)
        if p.is_file() and p.name in {'diagnose_browser_close.py','diagnose_manual_login.py','diagnose_manual_login_lines.py','recheck_lifecycle.py','start_interactive.py','finish_interactive.py'}:pairs.append(p)
    for folder in ('runs','regressions','native-ui-final'):
        pairs += [p for p in (S/folder).rglob('*') if p.is_file() and p.suffix in {'.json','.log','.png'}]
    for folder in S.iterdir():
        if not folder.is_dir():continue
        if folder.name.startswith(('installed-','installer-fault-')):
            pairs += [p for p in folder.iterdir() if p.is_file() and p.suffix in {'.json','.log','.png'}]
            pairs += [p for p in (folder/'screenshots').glob('*.png')]
        if folder.name.startswith('build-') and folder.name!='build-env':
            pairs += [p for p in folder.glob('BUILD_RESULT.json')]
        if folder.name.startswith(('long-preparation','long-path-final')):
            pairs += [p for p in folder.iterdir() if p.is_file() and p.name in {'ERROR.txt','RESULT.json'}]
    for raw in sorted(set(pairs)):
        rel=raw.relative_to(S);target=O/rel;target.parent.mkdir(parents=True,exist_ok=True)
        if raw.suffix=='.png':target.write_bytes(raw.read_bytes())
        else:target.write_text(sanitize(raw.read_text('utf-8-sig',errors='replace')),'utf-8')
        index.append({'raw_source':raw.relative_to(ROOT).as_posix(),'file':rel.as_posix(),'raw_sha256':sha(raw),'published_sha256':sha(target)})
    save(O/'EVIDENCE_INDEX.json',index)
    save(O/'REGRESSION_MATRIX_CURRENT.json',{'status':'FAIL',**stats,'rows':sorted(rows.values(),key=lambda r:r['module'])})
    save(O/'PREVIOUS_BASELINE_COMPARISON.json',{'status':'NO_NEW_REGRESSIONS' if same else 'DIFFERENCES_REQUIRE_REVIEW','rows':comparisons})
    save(O/'NATIVE_SCOPE_VERDICT.json',verdict)
    save(O/'BUILD_PROVENANCE.json',{'build_id':'PH-LW-11-20261108',**{k:frozen[k] for k in ('engine_build_digest','wheel_sha256','installer_sha256','package_manifest_sha256')},
        'input':read(W/'INPUT_BASELINE.json'),'zip_created':False,'signing':'UNSIGNED'})
    print(json.dumps({'verdict':verdict,'regressions':stats,'baseline_comparison':same,'evidence_files':len(index)},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
