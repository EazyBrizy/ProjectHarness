"""Installed-byte checks with exact, validated public initial-state fixtures."""
import hashlib,json,sys
from pathlib import Path
import project_harness
assert Path(project_harness.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
ROOT=Path(__file__).resolve().parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sys.path.insert(0,str(ENGINE))
base=ROOT/'_scratch/ph_lw_12/advanced-fixtures'
att=json.loads((ROOT/'_workspace/PH_LW_12/ADVANCED_FIXTURES.json').read_text('utf-8'))
for name in ('gate','accepted'):
    actual={p.relative_to(base/name).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (base/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert actual==att['states'][name]['hashes']
import tests.test_ph_lw_10_lifecycle as lifecycle
import tests.test_ph_lw_10_http as transport
lifecycle.public_fixtures=transport.public_fixtures=lambda:(base/'gate',base/'accepted')
from verify_installed import main
raise SystemExit(main())
