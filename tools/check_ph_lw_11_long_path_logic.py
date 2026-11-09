"""Show that business validators/mutators differ only at explicit IO call sites."""
import ast,hashlib,json
from pathlib import Path
from package_acceptance import ROOT,ENGINE
OLD=ROOT/'_scratch/ph_lw_11/build-docs-final/frozen/Harness/_internal/project_harness'
NAMES={'_native_io_path','native_walk','native_glob'}
class LogicalIO(ast.NodeTransformer):
 def visit_ImportFrom(self,node):
  if node.module=='platform_fs':
   node.names=[x for x in node.names if x.name not in NAMES]
   if not node.names:return None
  return node
 def visit_Call(self,node):
  node=self.generic_visit(node)
  if isinstance(node.func,ast.Name):
   if node.func.id=='_native_io_path':return node.args[0]
   if node.func.id=='native_walk':node.func=ast.Attribute(value=ast.Name(id='os',ctx=ast.Load()),attr='walk',ctx=ast.Load())
   elif node.func.id=='native_glob':
    recursive=any(k.arg=='recursive' and isinstance(k.value,ast.Constant) and k.value.value is True for k in node.keywords)
    return ast.Call(func=ast.Attribute(value=node.args[0],attr='rglob' if recursive else 'glob',ctx=ast.Load()),args=node.args[1:],keywords=[])
  return node
def main():
 before=json.loads((ROOT/'_workspace/PH_LW_11_LONG_PATH/INPUT_FILE_HASHES.json').read_text('utf-8'))
 rows=[]
 for name in ('compiler.py','hashing.py','serialization.py','workspace.py','validation.py','stages.py','materialization.py'):
  old=OLD/name;new=ENGINE/'src/project_harness'/name
  sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  assert sha(old)==before[ENGINE.name+'/src/project_harness/'+name]
  a=ast.parse(old.read_text('utf-8'));b=LogicalIO().visit(ast.parse(new.read_text('utf-8')))
  equal=ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
  rows.append({'file':name,'before_sha256':sha(old),'after_sha256':sha(new),'same_logic_after_explicit_io_adaptation_removed':equal})
 assert all(x['same_logic_after_explicit_io_adaptation_removed'] for x in rows),rows
 out=ROOT/'_scratch/ph_lw_11_long_path/LOGIC_DELTA.json'
 out.write_text(json.dumps({'status':'PASS','scope':'Structural evidence in addition to runtime tests; IO implementations and guards are tested separately','files':rows},indent=2)+'\n','utf-8')
 print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
