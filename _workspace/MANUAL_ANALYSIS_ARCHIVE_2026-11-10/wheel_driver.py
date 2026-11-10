"""Only five new manual ZIP checks from an independent installed wheel."""
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import sys
import unittest

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
import project_harness
package=Path(project_harness.__file__).resolve().parent
assert package.is_relative_to(Path(sys.prefix).resolve()) and not package.is_relative_to(ENGINE)
def inventory(base):return {p.relative_to(base).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert inventory(package)==inventory(ENGINE/'src/project_harness')
environment={'package':str(package),'python':sys.version,'executable':sys.executable,'cwd':str(Path.cwd()),
    'platform':platform.platform(),'source_import':False,
    'dependencies':{n:version(n) for n in ('Flask','Waitress','playwright')},
    'scope':'Only 3 ZIP HTTP/content methods and 2 automatic-download Edge methods; no full engine suite',
    'reason_for_wheel_run':'New archive route and binary download assets must be present at the distribution boundary',
    'provider':'No CLI/provider invoked; synthetic documents and one declared model JSON reply for preview compatibility'}
(OUT/'WHEEL_ENVIRONMENT.json').write_text(json.dumps(environment,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(environment,ensure_ascii=False),flush=True)
sys.path.insert(0,str(ENGINE))
os.environ['MANUAL_ARCHIVE_EVIDENCE']=str(OUT/'output/playwright')
case=sys.argv[sys.argv.index('--case')+1] if '--case' in sys.argv else None
suite=unittest.defaultTestLoader.loadTestsFromNames([case] if case else ['tests.test_manual_analysis_archive'])
assert suite.countTestCases()==(1 if case else 5),suite.countTestCases()
result=unittest.TextTestRunner(verbosity=2).run(suite)
path=OUT/('WHEEL_FOCUSED_RESULTS.json' if case else 'WHEEL_RESULTS.json');assert not path.exists()
path.write_text(json.dumps({'ran':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
    'skips':len(result.skipped),'status':'PASS' if result.wasSuccessful() and not result.skipped else 'FAIL'},indent=2)+'\n','utf-8')
raise SystemExit(not result.wasSuccessful() or bool(result.skipped))
