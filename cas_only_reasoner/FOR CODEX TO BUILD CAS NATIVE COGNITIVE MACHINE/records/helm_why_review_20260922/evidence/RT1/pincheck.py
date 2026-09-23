import sys, json
from pathlib import Path
ROOT = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
LAB = ROOT / "research/helm_cas_expression_lab"
sys.path.insert(0, str(LAB))
from q4_checkpoint import runtime_source_pins
man = json.loads((ROOT / "records/q4_authorized_20260922/run_001/checkpoint/manifest.json").read_text(encoding="utf-8"))
pins = runtime_source_pins()
print("source pins equal:", pins == man["identity"]["source_pins"])
for k in sorted(pins):
    if pins[k] != man["identity"]["source_pins"].get(k):
        print(" DIFF", k)
