"""Bounded Windows test diagnostics; stack locations only, no local values."""
import faulthandler,sys,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'Project_Harness_Engine_v0.5.1/src'),str(root/'Project_Harness_Engine_v0.5.1')]
faulthandler.enable();faulthandler.dump_traceback_later(45,repeat=True)
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:]))
faulthandler.cancel_dump_traceback_later()
raise SystemExit(not result.wasSuccessful())
