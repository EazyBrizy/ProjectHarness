"""Fresh full Windows matrix for final05 immutable runtime."""
import argparse,json,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from ph_lw_12_fix_run import OUT,W,sha
import ph_lw_12_acceptance as runner
runner.OUT=W;runner.RUNS=OUT
p=argparse.ArgumentParser();p.add_argument('mode',choices=('nonbrowser','browser'));a=p.parse_args()
deadline=time.monotonic()+3600
marker=W/'FINAL05_TEST_FREEZE_READY.json' if a.mode=='nonbrowser' else OUT/'final05-installed-deep-full.run.json'
while not marker.exists():
    if time.monotonic()>deadline:raise RuntimeError('Final05 not ready')
    time.sleep(1)
groups={};source_only={'tests.test_ph_f01_gate_semantics_regression','tests.test_ph_f01_planner_regression',
    'tests.test_ph_f03_active_stage_planning','tests.test_ph_f04_runtime_reachability'}
for row in json.loads((W/'DISCOVERY.json').read_text('utf-8'))['methods']:
    if row['platform_status']!='SCHEDULED_WINDOWS' or row['module']=='tests.test_ph_f06_maturity_lifecycle':continue
    browser=any(x in row['id'] for x in ('Browser','Edge','NativeLauncherTests'))
    if browser==(a.mode=='browser'):groups.setdefault(row['module'],[]).append(row['id'])
def check(item):
    module,ids=item;source=module in source_only;name='suite05-'+module.removeprefix('tests.')+'-'+a.mode
    row=runner.run_one(name,ids,python=None if source else OUT/'wheel-venv/Scripts/python.exe',wheel=not source,
        timeout=2400 if '10_lifecycle' in module else 1800)
    row.update(scope='SOURCE_LAYOUT_ONLY' if source else 'INSTALLED_WHEEL',runtime_freeze_sha256=sha(W/'RUNTIME_FREEZE.json'))
    runner.save(OUT/('source' if source else 'wheel')/(name+'.run.json'),row)
    print(module,row['status'],row.get('ran'),flush=True);return row
rows=[];items=sorted(groups.items(),key=lambda item:(item[0]!='tests.test_ph_lw_10_lifecycle',item[0]))
with ThreadPoolExecutor(max_workers=1 if a.mode=='browser' else 2) as pool:
    for future in as_completed([pool.submit(check,item) for item in items]):
        rows.append(future.result());runner.save(W/(a.mode.upper()+'_MATRIX_05.json'),rows)
raise SystemExit(not all(row['process_status']=='PASS' for row in rows))
