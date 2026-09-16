import sys, importlib.abc, json, hashlib
class Deny(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in {'torch','numpy','boto3','botocore','requests','cas_cjt'}: raise RuntimeError('PROHIBITED_IMPORT:'+fullname)
sys.meta_path.insert(0,Deny())
from cas_meta2.graph_teaching import cube_node, cube_profile
bundle=cube_node.load_bundle()
counts={}
for view in ('view_formal','view_context','view_analogy'):
 cases=cube_node.answer_cases(bundle,view)['cases']; delivered=0; private_independent=0
 for case in cases:
  for assistance in ('guided','unassisted'):
   full=cube_profile.compile_lesson(bundle,case,assistance=assistance,view_id=view)
   public=cube_profile.compile_public_exercise(bundle,cube_profile.public_case(case),assistance=assistance,view_id=view)
   assert full['encoding']['public']==public['encoding']['public']
   assert full['task_id']==public['task_id']
   delivered+=1;private_independent+=1
 counts[view]={'questions':len(cases),'compilations':delivered,'target_free_public_matches':private_independent}
print(json.dumps({'bundle_digest':cube_node.bundle_digest(bundle),'counts':counts,'prohibited_imports_present':sorted({'torch','numpy','boto3','botocore','requests','cas_cjt'} & set(sys.modules)),'neural_calls':0,'optimizer_updates':0,'note':'Compiler check only; no RPA cube adapter implemented.'},sort_keys=True))

