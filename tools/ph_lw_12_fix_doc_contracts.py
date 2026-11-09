"""Repeat documentation-sensitive contracts after the metadata-only change."""
import json
from ph_lw_12_fix_run import OUT,W,sha
import ph_lw_12_acceptance as runner
runner.OUT=W;runner.RUNS=OUT
ids=[row['id'] for row in json.loads((W/'DISCOVERY.json').read_text('utf-8'))['methods']
    if row['module'] in {'tests.test_ph_051_11_operator_docs','tests.test_ph_lw_01_contract'}]
assert len(ids)==14
row=runner.run_one('final04-doc-contracts',ids,python=OUT/'wheel-venv/Scripts/python.exe',wheel=True,timeout=300)
row.update(scope='INSTALLED_WHEEL; documentation-sensitive final04 recheck',
    runtime_freeze_sha256=sha(W/'RUNTIME_FREEZE.json'))
runner.save(OUT/'wheel/final04-doc-contracts.run.json',row)
raise SystemExit(row['process_status']!='PASS')
