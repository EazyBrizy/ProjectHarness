"""Separate observed reruns; no acceptance verdict or POST replay."""
import argparse
from ph_lw_12_fix_run import run,ROOT,OUT,ENGINE
p=argparse.ArgumentParser();p.add_argument('mode',choices=('source','frozen'));a=p.parse_args()
if a.mode=='source':
    row=run('deep-reload-source-trace-01',[ROOT/'.venv/Scripts/python.exe','-B',ROOT/'tools/ph_lw_12_fix_native_flow.py',
        '--output',OUT/'deep-reload-source-trace-01'],timeout=600)
else:
    row=run('final04-deep-reload-trace',[OUT/'wheel-venv/Scripts/python.exe','-B',ENGINE/'local_web/windows/final_acceptance.py',
        '--installer',ENGINE/'windows/Harness-Setup-win-x64.exe','--output',OUT/'final04-deep-reload-trace','--deep-full-flow',
        '--case','__main__.InstalledFullFlowTests.test_no_documents_gpt_approvals_publish_manual_evidence_verify_complete'],
        extra={'PH_LW_12_INSTALLED_DRIVER':'1'},timeout=600)
raise SystemExit(row['status']!='PASS')
