"""RT9 peek 2: dev panel packet structure in protocol_material.json; list artifact file names (no private/sealed opened)."""
import json
from pathlib import Path
ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
A = ROOT / 'records/typed_pointer_001/receipt_20260917/collected/results/artifacts'
print(sorted(f.name for f in A.iterdir()))
pm = json.loads((A / 'protocol_material.json').read_bytes())
print('pm keys', list(pm.keys()))
dev = pm['development']
print('dev keys', list(dev.keys()))
p = dev['packets'][0]
def show(x, pre='', depth=0):
    if depth > 3: return
    if isinstance(x, dict):
        for k, v in x.items():
            if isinstance(v, (dict, list)):
                print(pre + k, type(v).__name__, len(v))
                show(v, pre + '  ', depth + 1)
            else:
                print(pre + k, repr(v)[:120])
    elif isinstance(x, list) and x:
        show(x[0], pre + '[0] ', depth + 1)
show(p)
