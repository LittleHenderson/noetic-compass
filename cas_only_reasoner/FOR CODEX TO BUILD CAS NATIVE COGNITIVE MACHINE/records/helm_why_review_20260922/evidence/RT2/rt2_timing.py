import sys, torch
if not torch.cuda.is_available(): print('GPU_REQUIRED'); sys.exit(2)
"""RT2 pre-run timing: FORWARD ONLY on the saved checkpoint (no backward, no optimizer). Writes nothing.
Purpose: size the evaluation cost so the one bounded re-run fits the 5-minute command limit. DIAGNOSTIC_NOT_CLAIM_BEARING."""
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import json, time
from pathlib import Path
ROOT = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
LAB = ROOT / "research/helm_cas_expression_lab"
RUN = ROOT / "records/q4_authorized_20260922/run_001"
sys.path.insert(0, str(LAB))
from learner_q4_decoder import free_decode, ast_to_tokens
from learner_q4_representation import from_visible_record
from q3_load import load_visible
from q4_checkpoint import load_checkpoint
torch.use_deterministic_algorithms(True)
torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
m = json.loads((RUN / "checkpoint/manifest.json").read_text(encoding="utf-8"))
model = load_checkpoint(RUN / "checkpoint", expected_identity=m["identity"], expected_weights_sha256=m["weights_sha256"], width=64, device="cuda:0")
dev = [from_visible_record(r) for r in load_visible(LAB / "data/q3_v0_7", "G", "dev")]
tr = [from_visible_record(r) for r in load_visible(LAB / "data/q3_v0_7", "G", "train")[:256]]
t = time.perf_counter(); vecs = [model.encode(x) for x in dev]; torch.cuda.synchronize(); print("encode 256 dev: %.3f s" % (time.perf_counter() - t))
t = time.perf_counter(); outs = [free_decode(v, model.next_logits) for v in vecs[:64]]; print("free_decode 64 dev: %.3f s, steps %s" % (time.perf_counter() - t, sorted({o.steps for o in outs})))
# next_logits cost vs prefix length
for L in (1, 20, 40, 100, 300):
    pref = tuple([2] * 0 + [1, 5, 16, 20, 28] * (L // 5 + 1))[:L]
    t = time.perf_counter()
    for _ in range(50):
        model.next_logits(vecs[0], pref)
    print("next_logits prefix %d: %.3f ms/call" % (L, (time.perf_counter() - t) / 50 * 1000))
tgt = ast_to_tokens({"node": "StateLiteral", "operator": "^1", "domain": "C", "drive": None})
t = time.perf_counter()
with torch.no_grad():
    for x in tr:
        model.teacher_forced_logits(x, tuple([1, 5, 16, 20, 28] * 8)[:40])
torch.cuda.synchronize(); print("TF forward 256 rows (40-token prefix): %.3f s" % (time.perf_counter() - t))
print("peak bytes", torch.cuda.max_memory_allocated(0))
