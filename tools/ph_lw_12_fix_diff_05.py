"""Exact textual patch against the verified input source, without runtime edits."""
import difflib,hashlib,json,shutil
from package_acceptance import ROOT,ENGINE,files
W=ROOT/'_workspace/PH_LW_12_FIX';source=ENGINE/'src/project_harness';before=W/'input-source'
freeze=json.loads((W/'RUNTIME_FREEZE.json').read_text('utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert freeze['source_hashes']=={p.relative_to(source).as_posix():sha(p) for p in files(source)}
target=W/'CODE_DIFF_CANDIDATE_04.patch';assert not target.exists();shutil.copy2(W/'CODE_DIFF.patch',target)
chunks=[];changed=[]
for path in files(source):
    relative=path.relative_to(source);old=before/relative
    if old.exists() and old.read_bytes()==path.read_bytes():continue
    name='project_harness/'+relative.as_posix();changed.append(name)
    chunks.extend(difflib.unified_diff(old.read_text('utf-8').splitlines(True) if old.exists() else [],
        path.read_text('utf-8').splitlines(True),fromfile='before/'+name,tofile='after/'+name))
(W/'CODE_DIFF.patch').write_text(''.join(chunks),'utf-8')
(W/'CODE_CHANGE_SCOPE.json').write_text(json.dumps({'files':changed,
    'scope':'Native IO in reproduced deep manual path; serialized client JSON/multipart; fresh card view; read-only operation/preparation snapshots avoid mutable canonical enumeration. Full mutation/root/ownership/integrity checks retained; no schema/registry/state semantics changes.'},indent=2)+'\n','utf-8')
print(json.dumps({'changed_source_files':len(changed),'freeze_unchanged':True}))
