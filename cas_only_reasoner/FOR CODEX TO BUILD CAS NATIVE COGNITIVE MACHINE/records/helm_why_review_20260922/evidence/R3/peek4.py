import json
ROOT = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
A = ROOT+'/records/typed_pointer_001/receipt_20260917/collected/results/artifacts/'
pm = json.load(open(A+'protocol_material.json','rb'))
print('pm keys', list(pm.keys()))
for k,v in pm.items():
    print(' ', k, type(v).__name__, (len(v) if hasattr(v,'__len__') else v), str(v)[:200])
p = json.load(open(A+'course_p10_predictions.json','rb'))
for pr in p['predictions']:
    if pr['answer']['kind']=='reach':
        print(json.dumps(pr)[:3000]); break
g = json.load(open(ROOT+'/records/typed_pointer_001/admission_001/gate_reading.json','rb'))
pop = g['population']
print('pop question_ids', len(pop['question_ids']))
print('eligible_questions', type(pop['eligible_questions']).__name__, len(pop['eligible_questions']), str(pop['eligible_questions'])[:300])
print('shortcut', pop['shortcut_question_ids'])
print('zero_learning_floor', json.dumps(pop['zero_learning_floor'])[:2000])
print('removed_by_rule', json.dumps(pop['removed_by_rule'])[:1500])
print('by_world', pop['by_world'])
print('seed gained', json.dumps(g['seeds']['20260919']['gained_questions'])[:3000])
