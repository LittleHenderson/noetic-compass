import sys, torch
if not torch.cuda.is_available(): print('GPU_REQUIRED'); sys.exit(2)
"""RT1 EXTRA 2 (not used for any outcome rule): does the decoder act on an input fact the vector clearly carries?
The vector carries 'right child of the root is binary' (nearest-centroid 128/128 on unseen128, rt1_extra_out.txt).
Fixed prefix = the constant tree up to the root's right-child slot:
  BINARY PLUS STATE N7 D_E F_NONE REG_ABSENT  -> next slot is the root's right child (STATE or BINARY).
For each of the 2048 train rows, own TRUE vector, record logit[BINARY]-logit[STATE] at that prefix. Compare groups.
Same for the root-op slot (prefix BINARY): logit[TIMES]-logit[PLUS], grouped by true root op.
Forward-only. DIAGNOSTIC_NOT_CLAIM_BEARING. Writes only to SCRATCH/RT1 (stdout captured by the caller)."""
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import json
from pathlib import Path

ROOT = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
LAB = ROOT / "research/helm_cas_expression_lab"
SCRATCH = Path("C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad/helm_review")
RUN = ROOT / "records/q4_authorized_20260922/run_001"
DATA = LAB / "data/q3_v0_7"
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(SCRATCH / "R5"))
from common import parse
from learner_q4_decoder import TOKEN_IDS as T
from learner_q4_representation import from_visible_record
from q3_load import load_visible
from q4_checkpoint import load_checkpoint

torch.use_deterministic_algorithms(True)
torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
manifest = json.loads((RUN / "checkpoint/manifest.json").read_text(encoding="utf-8"))
model = load_checkpoint(RUN / "checkpoint", expected_identity=manifest["identity"],
                        expected_weights_sha256="d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477",
                        width=64, device="cuda:0")
rows = load_visible(DATA, "G", "train")[:2048]
asts = [parse(r["observation"]) for r in rows]
vecs = [model.encode(from_visible_record(r)) for r in rows]
PR = tuple(T[n] for n in ("BINARY", "PLUS", "STATE", "N7", "D_E", "F_NONE", "REG_ABSENT"))
PO = (T["BINARY"],)


def stats(xs):
    m = sum(xs) / len(xs)
    return m, min(xs), max(xs), len(xs)


gr = {True: [], False: []}
go = {"PLUS": [], "TIMES": []}
for v, a in zip(vecs, asts):
    L = model.next_logits(v, PR)
    gr[a["right"]["node"] == "BinaryExpr"].append(L[T["BINARY"]] - L[T["STATE"]])
    L = model.next_logits(v, PO)
    go[a["op"]].append(L[T["TIMES"]] - L[T["PLUS"]])
for k in (True, False):
    print("right child binary=%s: gap BINARY-STATE at the right-child slot mean %+.6f min %+.6f max %+.6f n %d" % ((k,) + stats(gr[k])))
print("difference of group means (binary minus leaf): %+.6f" % (stats(gr[True])[0] - stats(gr[False])[0]))
for k in ("PLUS", "TIMES"):
    print("root op=%s: gap TIMES-PLUS at the root-op slot mean %+.6f min %+.6f max %+.6f n %d" % ((k,) + stats(go[k])))
print("difference of group means (TIMES minus PLUS): %+.6f" % (stats(go["TIMES"])[0] - stats(go["PLUS"])[0]))
print("rows whose greedy right-child choice would be BINARY (gap > 0): %d/2048" % sum(g > 0 for g in gr[True] + gr[False]))
print("rows whose greedy root-op choice would be TIMES (gap > 0): %d/2048" % sum(g > 0 for g in go["PLUS"] + go["TIMES"]))
