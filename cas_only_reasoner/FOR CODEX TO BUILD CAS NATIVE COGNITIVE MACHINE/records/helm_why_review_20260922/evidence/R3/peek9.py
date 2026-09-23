import json
ROOT = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
T = ROOT+'/records/typed_pointer_001/'
for name in ['admission_helm1_certified','admission_001']:
    g = json.load(open(T+name+'/gate_reading.json','rb'))
    print('=====', name)
    for s,e in g['seeds'].items():
        row = []
        for k in ['reach','analogy','correspondence','parts','context','definition','edge_account','role_set']:
            t = e['G_LEARN_kind_'+k]
            row.append('%s %d/%d p=%s %s' % (k[:5], t['wrong_to_right'], t['right_to_wrong'], t['p_one_sided'], 'P' if t['passed'] else 'F'))
        for tier in ['G_LEARN_DIRECT_READ','G_LEARN_TEXT']:
            t = e[tier]; row.append('%s %d/%d p=%s %s' % (tier[8:], t['wrong_to_right'], t['right_to_wrong'], t['p_one_sided'], 'P' if t['passed'] else 'F'))
        print(s, ' | '.join(row))
    print('tiers', g['tiers'])
    print('gained_questions per seed (kind, records, admissible):')
    for s,e in g['seeds'].items():
        print('  ', s, [(x['kind'], x['query_id'].split('-')[-1][:8], x['records'], x['admissible_answers']) for x in e['gained_questions']], 'gained_single_record', e['gained_single_record'])
