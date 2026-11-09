"""Full current Windows discovery, with explicit source-layout-only cases."""
import argparse,json,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from ph_lw_12_fix_run import ROOT,OUT,W,sha
import ph_lw_12_acceptance as runner

runner.OUT=W;runner.RUNS=OUT
wheel=OUT/'wheel-venv/Scripts/python.exe'
source_only={'tests.test_ph_f01_gate_semantics_regression','tests.test_ph_f01_planner_regression',
             'tests.test_ph_f03_active_stage_planning','tests.test_ph_f04_runtime_reachability'}
parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('nonbrowser','browser'));args=parser.parse_args()
deadline=time.monotonic()+3000
while not (OUT/'final03-installed-deep-full.run.json').exists():
    if time.monotonic()>deadline:raise RuntimeError('Frozen suites still active; native launcher suite must not overlap')
    time.sleep(1)
groups={}
for row in json.loads((W/'DISCOVERY.json').read_text('utf-8'))['methods']:
    if row['platform_status']!='SCHEDULED_WINDOWS':continue
    browser=any(x in row['id'] for x in ('Browser','Edge','NativeLauncherTests'))
    if browser!=(args.mode=='browser'):continue
    if row['module']=='tests.test_ph_f06_maturity_lifecycle':continue # own full original setup/run, observed cache
    groups.setdefault(row['module'],[]).append(row['id'])
def check(item):
    module,ids=item;source=module in source_only
    name=module.removeprefix('tests.')+'-'+args.mode
    result=runner.run_one(name,ids,python=None if source else wheel,wheel=not source,timeout=2400 if '10_lifecycle' in module else 1800)
    result.update(scope='SOURCE_LAYOUT_ONLY' if source else 'INSTALLED_WHEEL',
        runtime_freeze_sha256=sha(W/'RUNTIME_FREEZE.json'))
    destination=OUT/('source' if source else 'wheel')/(name+'.run.json')
    runner.save(destination,result)
    print(module,result['status'],result.get('ran'),result['elapsed_seconds'],flush=True)
    return result
items=sorted(groups.items(),key=lambda item:(item[0]!='tests.test_ph_lw_10_lifecycle',item[0]))
rows=[]
with ThreadPoolExecutor(max_workers=1 if args.mode=='browser' else 2) as pool:
    for future in as_completed([pool.submit(check,item) for item in items]):
        rows.append(future.result());runner.save(W/(args.mode.upper()+'_MATRIX.json'),rows)
raise SystemExit(not all(row.get('process_status')=='PASS' for row in rows))
