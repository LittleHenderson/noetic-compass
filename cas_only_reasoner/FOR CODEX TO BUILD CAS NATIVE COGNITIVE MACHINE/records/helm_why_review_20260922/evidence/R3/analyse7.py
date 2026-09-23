import json
from pathlib import Path
ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
T = ROOT/'records/typed_pointer_001'
u = json.loads((T/'receipt_20260919/collected/results/artifacts/pass_10_updates.jsonl').read_bytes().splitlines()[0])
def walk(d, pre=''):
    for k,v in d.items():
        if isinstance(v, dict): walk(v, pre+k+'.')
        elif isinstance(v, list): print(pre+k, 'list', len(v))
        else: print(pre+k, '=', str(v)[:100])
walk(u)
