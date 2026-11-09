"""Run the preserved installed-wheel suites plus new long app-data ZIP cases."""
import argparse,json,os,subprocess,sys
from package_acceptance import ROOT
parser=argparse.ArgumentParser();parser.add_argument('suite',choices=['nonbrowser','browser']);args=parser.parse_args()
old_name='installed-'+args.suite;name='installed-final-'+args.suite;out=ROOT/'_scratch/ph_lw_11_zip_path'
old=json.loads((ROOT/'_scratch/ph_lw_11_long_path/runs'/f'{old_name}.run.json').read_text('utf-8'))
command=[x.replace('ph_lw_11_long_path','ph_lw_11_zip_path').replace('/wheel-venv/','/wheel-final-venv/') for x in old['command']]
# The earlier project-path test is retained; add this task's seven ZIP cases.
command=[x.replace('tests.test_ph_lw_11_zip_path','tests.test_ph_lw_11_long_path') if x.startswith('tests.') else x for x in command]
if args.suite=='nonbrowser':command+=['--case','tests.test_ph_lw_11_zip_path']
runner=[sys.executable,str(ROOT/'tools/run_logged.py'),'--log',str(out/'runs'/f'{name}.log'),'--cwd',str(out/'Независимая финальная папка wheel'),'--timeout',str(old['timeout_seconds']),'--',*command]
raise SystemExit(subprocess.run(runner,cwd=ROOT,env={**os.environ,'PYTHONUTF8':'1','PYTHONPATH':'','PH_LW_04_BROWSER_CHANNEL':'msedge'}).returncode)
