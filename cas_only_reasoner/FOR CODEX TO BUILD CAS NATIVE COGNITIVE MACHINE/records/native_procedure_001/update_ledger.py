"""Append the bounded native result without changing original requirement scope."""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
addition = """
## 2026-09-16 bounded native acquisition, exact resume and recovery

The earlier procedure-integration gap is now implemented for one opt-in exact
rational capability in runtime 0.2.0. A real missing-procedure caller suspends;
finite selection and independently checked installation occur as native
coordinator transitions; the same caller resumes with remaining debited budget.
Its candidate produces x=7 for 3*x+5=26 before ordinary checked commitment.
A separate process semantically replays the journal and reuses installed bytes
for -4*x+7=13, yielding -3/2 with new-call selection/qualification disabled.
Native rollback to first-install absence causes the next call to refuse while
all old artifacts and evidence remain. Failed checks consume their allocations;
forged, stale, misbound and rehashed false histories fail replay.

Complete homebase verification passed 467 tests plus 448 subtests; all14 retained
legacy fixtures reproduce. Exact evidence is records/native_procedure_001/
STATUS.md and acceptance_002/receipt.json in vision-next. Its source profile is
c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607.
The default0.1 manifest and accepted fixture behavior remain unchanged.

This advances bounded portions of V05/V06/V08/V10/V15 and systems7/8/9/18/20/31.
It does not complete those requirements: selection is twelve authored forms,
qualification uses public engineering panels, recovery trusts the host/genesis/
external digest, and the demonstrated rollback removes a first installation.
Exhausted unresolved acquisition frames cannot bootstrap a new budget.
General learning, neural assembly, learned retrieval, broader mathematical
strategy acquisition, adaptive flow, complete ontology and the full V01-V18,
31-system and integrated20-step destination remain open.

No new paid neural work was needed for this implementation. Existing budget
reservations and negative experiments remain unchanged. The user's newly supplied
CAS-RPA documents are being reviewed for a separate typed evidence/possibility
view; their proposed geometry and namespace annotations grant no kernel authority.
"""
rows = []
for base in (HOME, ROOT):
    path = base / "docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md"
    before = path.read_bytes()
    assert sha256(before).hexdigest() == "e41f3d038632da408adc7c3e3391dd990c01b0c451f9a4ce943bf5034fa8aa6c"
    path.write_bytes(before + addition.encode())
    rows.append({"path": str(path), "before_sha256": sha256(before).hexdigest(),
        "after_sha256": sha256(path.read_bytes()).hexdigest(),
        "original_bytes_preserved": path.read_bytes().startswith(before), "full_goal_complete": False})
out = Path(__file__).with_name("ledger_update.json")
with out.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(rows, stream, indent=2)
    stream.write("\n")
print(json.dumps(rows))

