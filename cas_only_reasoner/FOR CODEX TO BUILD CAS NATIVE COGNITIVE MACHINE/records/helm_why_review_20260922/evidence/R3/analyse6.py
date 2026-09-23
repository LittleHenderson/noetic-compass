import json
from pathlib import Path
ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
T = ROOT/'records/typed_pointer_001'
line = (T/'receipt_20260919/collected/results/artifacts/pass_10_updates.jsonl').read_bytes().splitlines()[0]
print(line[:1500])
for v, pat in [('1.0','receipt_helm1_certified_%s'),('2.0','receipt_%s')]:
    for s in ['20260917','20260918','20260919']:
        art = T/(pat % s)/'collected/results/artifacts'
        wr = json.loads((art/'worker_report.json').read_bytes())
        ps = wr['pass_summaries']
        clipped = 0; n = 0; maxpre = 0.0; last_pass_clipped = 0
        for p in range(1, 11):
            for ln in (art/('pass_%02d_updates.jsonl' % p)).read_bytes().splitlines():
                u = json.loads(ln); n += 1
                c = u.get('clipped'); pre = u.get('pre_clip_norm') or u.get('gradient_norm_pre_clip')
                if c: clipped += 1; last_pass_clipped += (p == 10)
                if isinstance(pre,(int,float)) and pre > maxpre: maxpre = pre
        print('Helm', v, s, 'updates', n, 'clipped', clipped, 'clipped in pass10', last_pass_clipped, 'max pre-clip norm', maxpre, '| pass10 mean loss', ps[-1]['mean_raw_batch_loss'], 'pass10 mean grad sq norm', ps[-1]['mean_gradient_squared_norm'], '| pass1 mean loss', ps[0]['mean_raw_batch_loss'])
