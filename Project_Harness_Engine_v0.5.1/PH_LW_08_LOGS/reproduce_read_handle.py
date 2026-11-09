from pathlib import Path
import tempfile,json,platform,sys
from project_harness.local_web_exchange import _save
print(json.dumps({'python':sys.version,'executable':sys.executable,'platform':platform.platform()}))
with tempfile.TemporaryDirectory() as d:
    path=Path(d)/'record.json';_save(path,{'phase':'INTENT'})
    with path.open('rb'):
        try:_save(path,{'phase':'STAGING'})
        except PermissionError as e:
            assert e.winerror==5
            print(json.dumps({'status':'PASS','reproduced':'Windows read handle denies atomic replace','winerror':e.winerror}))
        else:raise AssertionError('Expected Windows sharing violation')
