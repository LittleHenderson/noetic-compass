import json
from pathlib import Path
ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
T = ROOT/'records/typed_pointer_001'
for v, pat in [('1.0','receipt_helm1_certified_%s'),('2.0','receipt_%s')]:
    for s in ['20260917','20260918','20260919']:
        art = T/(pat % s)/'collected/results/artifacts'
        clipped = 0; n = 0; maxpre = 0.0; clip10 = 0; lr=set(); sched=set(); pre10=[]
        for p in range(1, 11):
            for ln in (art/('pass_%02d_updates.jsonl' % p)).read_bytes().splitlines():
                u = json.loads(ln); n += 1
                if u.get('gradient_was_clipped'): clipped += 1; clip10 += (p==10)
                pre = u.get('gradient_norm_before_clip')
                if isinstance(pre, (int,float)):
                    maxpre = max(maxpre, pre)
                    if p == 10: pre10.append(pre)
                lr.add(u.get('learning_rate_this_step')); sched.add(u.get('learning_rate_schedule'))
        print('Helm', v, s, 'updates', n, 'clipped', clipped, 'clipped_in_pass10', clip10, 'max_pre_clip', maxpre, 'pass10 pre-clip mean', (sum(pre10)/len(pre10) if pre10 else None), 'lr', lr, 'sched', sched)
