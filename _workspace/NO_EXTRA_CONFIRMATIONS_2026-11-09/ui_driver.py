"""Only changed UI paths, against an independently installed wheel."""
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys
import unittest

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
import project_harness
package=Path(project_harness.__file__).resolve().parent
assert package.is_relative_to(Path(sys.prefix).resolve()) and not package.is_relative_to(ENGINE)
def inventory(base):return {p.relative_to(base).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert inventory(package)==inventory(ENGINE/'src/project_harness')
print(json.dumps({'package':str(package),'python':sys.version,'cwd':str(Path.cwd()),'source_import':False,
    'dependencies':{n:version(n) for n in ('Flask','Waitress','playwright')},'scope':'3 tests of changed confirmation-free UI only; no full engine suite'},ensure_ascii=False),flush=True)
sys.path.insert(0,str(ENGINE))
name=sys.argv[sys.argv.index('--case')+1] if '--case' in sys.argv else 'tests.test_single_action_ui'
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(name))
path=OUT/('UI_FOCUSED_RESULTS.json' if '--case' in sys.argv else 'UI_RESULTS.json')
assert not path.exists()
path.write_text(json.dumps({'ran':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'status':'PASS' if result.wasSuccessful() and not result.skipped else 'FAIL'},indent=2)+'\n','utf-8')
raise SystemExit(not result.wasSuccessful() or bool(result.skipped))
