"""Observe unchanged public test setup and preserve its accepted MVP fixture."""
import hashlib,json,shutil,sys
from pathlib import Path
import project_harness
assert Path(project_harness.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Project_Harness_Engine_v0.5.1'))
from tests.test_ph_f06_maturity_lifecycle import PHF06MaturityLifecycleTests
from project_harness.validation import validate_project_directory
from project_harness.stages import stage_status
original=PHF06MaturityLifecycleTests.setUpClass.__func__
def observed(cls):
    original(cls) # All original public CLI construction and assertions.
    assert stage_status(cls.mvp)['highest_accepted_level']=='MVP'
    assert validate_project_directory(cls.mvp)['status']=='PASS'
    target=ROOT/'_scratch/ph_lw_12_fix/advanced-fixtures-final05/mvp';assert not target.exists()
    shutil.copytree(cls.mvp,target)
    hashes=lambda base:{p.relative_to(base).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert hashes(cls.mvp)==hashes(target)
    (ROOT/'_workspace/PH_LW_12_FIX/MATURITY_SETUP_CACHE.json').write_text(json.dumps({
        'status':'PASS','observer_only':True,'generator':'unchanged PHF06MaturityLifecycleTests.setUpClass',
        'package':project_harness.__file__,'actual_boundaries':cls.boundaries,'hashes':hashes(target)},ensure_ascii=False,indent=2)+'\n','utf-8')
PHF06MaturityLifecycleTests.setUpClass=classmethod(observed)
from verify_installed import main
raise SystemExit(main())
