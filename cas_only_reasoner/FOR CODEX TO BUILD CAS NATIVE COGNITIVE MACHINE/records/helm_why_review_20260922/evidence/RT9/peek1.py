"""RT9 peek: structure of p10 prediction/scoring files (keys only, one reach row). stdlib only, read-only."""
import json
from pathlib import Path
ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
T = ROOT / 'records/typed_pointer_001/receipt_20260917/checkpoints'
for name in ['course_p10_predictions.json', 'course_p10_scoring.json', 'development_p10_predictions.json', 'development_p10_scoring.json']:
    d = json.loads((T / name).read_bytes())
    print('==', name, 'top keys:', list(d.keys()))
    for k, v in d.items():
        if isinstance(v, list):
            print('  list', k, 'len', len(v))
            if v and isinstance(v[0], dict):
                print('   row keys:', list(v[0].keys()))
        elif isinstance(v, dict):
            print('  dict', k, 'keys', list(v.keys())[:20])
        else:
            print('  ', k, repr(v)[:200])
