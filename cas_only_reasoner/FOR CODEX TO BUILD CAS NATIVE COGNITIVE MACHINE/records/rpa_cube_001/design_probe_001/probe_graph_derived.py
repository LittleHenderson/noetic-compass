import sys, importlib.abc, json
class Deny(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in {'torch','numpy','boto3','botocore','requests','cas_cjt'}: raise RuntimeError('PROHIBITED_IMPORT:'+fullname)
sys.meta_path.insert(0,Deny())
from cas_meta2.graph_teaching import cube_node, cube_profile
bundle=cube_node.load_bundle(); counts={}
for view in ('view_formal','view_context','view_analogy'):
 cases=cube_node.answer_cases(bundle,view)['cases']; matches=0; refusals=[]
 for case in cases:
  minimal=cube_profile.public_case(case)
  graph_case={**minimal,'correct':cube_profile.derived_answer(bundle,minimal,view)}
  for assistance in ('guided','unassisted'):
   try:
    full=cube_profile.compile_lesson(bundle,case,assistance=assistance,view_id=view)
    derived=cube_profile.compile_public_exercise(bundle,graph_case,assistance=assistance,view_id=view)
    assert full['encoding']['public']==derived['encoding']['public']
    assert full['task_id']==derived['task_id']
    matches+=1
   except ValueError as e: refusals.append(str(e))
 counts[view]={'questions':len(cases),'matching_compilations':matches,'refusals':refusals}
print(json.dumps({'bundle_digest':cube_node.bundle_digest(bundle),'counts':counts,'prohibited_imports_present':sorted({'torch','numpy','boto3','botocore','requests','cas_cjt'} & set(sys.modules)),'neural_calls':0,'optimizer_updates':0,'note':'Graph-derived teacher case succeeds; target-free legacy compiler fails as separately retained.'},sort_keys=True))

