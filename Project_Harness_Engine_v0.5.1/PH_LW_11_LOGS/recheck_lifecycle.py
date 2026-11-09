import faulthandler,json,sys,traceback,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[2];engine=root/'Project_Harness_Engine_v0.5.1';sys.path[:0]=[str(engine/'src'),str(engine)]
faulthandler.dump_traceback_later(300,repeat=True)
class ImmediateResult(unittest.TextTestResult):
 def addError(self,test,err):
  super().addError(test,err);traceback.print_exception(*err,file=self.stream);self.stream.flush()
 def addFailure(self,test,err):
  super().addFailure(test,err);traceback.print_exception(*err,file=self.stream);self.stream.flush()
suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_ph_lw_10_lifecycle.LifecycleServiceTests.test_accepted_mvp_level_up_release_through_adapter')
result=unittest.TextTestRunner(verbosity=2,resultclass=ImmediateResult).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
