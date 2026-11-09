"""Compare immutable pre-fix ASTs after removing explicit IO spelling adapters."""
import ast,hashlib,json
from package_acceptance import ROOT,ENGINE
OLD=ROOT/'_scratch/ph_lw_11_long_path/build/frozen/Harness/_internal/project_harness'
FILES=('local_web_exchange.py','local_web_imports.py','local_web_source_refresh.py','local_web_sources_service.py','inventory.py','safety.py','serialization.py')
class LogicalIO(ast.NodeTransformer):
 def visit_ImportFrom(self,node):
  if node.module=='platform_fs':
   node.names=[x for x in node.names if x.name not in {'_native_io_path','native_walk','native_glob'}]
   if not node.names:return None
  return node
 def visit_Call(self,node):
  node=self.generic_visit(node)
  if isinstance(node.func,ast.Name):
   if node.func.id=='_native_io_path':return node.args[0]
   if node.func.id=='native_glob':
    recursive=any(k.arg=='recursive' and isinstance(k.value,ast.Constant) and k.value.value is True for k in node.keywords)
    return ast.Call(func=ast.Attribute(value=node.args[0],attr='rglob' if recursive else 'glob',ctx=ast.Load()),args=node.args[1:],keywords=[])
   if node.func.id=='native_walk':node.func=ast.Attribute(value=ast.Name(id='os',ctx=ast.Load()),attr='walk',ctx=ast.Load())
  return node
 def visit_Assign(self,node):
  node=self.generic_visit(node)
  if len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
   if node.targets[0].id=='open_path':
    assert isinstance(node.value,ast.IfExp)
    assert ast.dump(node.value.body)==ast.dump(node.value.orelse)
    return None
   if isinstance(node.value,ast.Name) and node.targets[0].id==node.value.id:return None
  return node
 def visit_Name(self,node):
  if node.id=='open_path' and isinstance(node.ctx,ast.Load):return ast.Name(id='path',ctx=node.ctx)
  return node

def normalized(text):
 tree=ast.parse(text)
 # Exclude import grouping, but verify the same non-adapter imports separately.
 imports=[]
 for node in tree.body:
  if isinstance(node,ast.ImportFrom):imports.extend((node.module,a.name,a.asname) for a in node.names if a.name not in {'_native_io_path','native_walk','native_glob'})
 tree=LogicalIO().visit(tree)
 tree.body=[n for n in tree.body if not isinstance(n,ast.ImportFrom)]
 return sorted(imports,key=str),ast.dump(tree,include_attributes=False)
def main():
 before=json.loads((ROOT/'_workspace/PH_LW_11_ZIP_PATH/INPUT_FILE_HASHES.json').read_text('utf-8'));rows=[]
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 for name in FILES:
  old=OLD/name;new=ENGINE/'src/project_harness'/name
  assert sha(old)==before[ENGINE.name+'/src/project_harness/'+name]
  equal=normalized(old.read_text('utf-8'))==normalized(new.read_text('utf-8'))
  rows.append({'file':name,'before_sha256':sha(old),'after_sha256':sha(new),'same_business_ast_without_io_adapters':equal})
 assert all(r['same_business_ast_without_io_adapters'] for r in rows),rows
 (ROOT/'_scratch/ph_lw_11_zip_path/LOGIC_DELTA.json').write_text(json.dumps({'status':'PASS','scope':'Structural proof supplements runtime tests; private IO wrappers/walks/write rebindings removed. copy_verified_document short/long open spelling normalized to the same logical source path. No ZIP contract or transaction branches removed.','files':rows},indent=2)+'\n','utf-8')
 print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
