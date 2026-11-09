"""Before/after tests use the same new assertions and real Windows IO."""
import argparse,sys
from ph_lw_12_fix_run import ROOT,OUT,ENGINE,run
p=argparse.ArgumentParser();p.add_argument('mode',choices=('before','after'));a=p.parse_args()
ids=['tests.test_ph_lw_12_blockers.DeepAppDataTests.test_operation_snapshot_survives_worker_temp_file_rename',
     'tests.test_ph_lw_12_blockers.DeepAppDataTests.test_preparation_poll_during_write_is_conflict_not_internal_error']
reference=OUT/'input-frozen-candidate-03/_internal' if a.mode=='before' else ENGINE/'src'
code="import sys,unittest;sys.path[:0]=sys.argv[1:3];import project_harness;print(project_harness.__file__,flush=True);r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(sys.argv[3:]));raise SystemExit(not r.wasSuccessful())"
row=run('poll-snapshot-'+a.mode+'-05',[ROOT/'.venv/Scripts/python.exe','-B','-c',code,reference,ENGINE,*ids],timeout=120)
raise SystemExit((row['status']!='FAIL') if a.mode=='before' else (row['status']!='PASS'))
