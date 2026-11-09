import faulthandler,sys,unittest
from pathlib import Path
faulthandler.dump_traceback_later(45,repeat=True)
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'Project_Harness_Engine_v0.5.1'))
unittest.main(module=None,argv=['diagnostic','-v','tests.test_ph_lw_11_desktop.NativeLauncherTests.test_edge_manual_code_login_without_fragment_or_external_requests'])
