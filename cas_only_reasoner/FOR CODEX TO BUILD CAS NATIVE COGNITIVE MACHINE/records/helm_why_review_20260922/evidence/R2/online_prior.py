# An INPUT-BLIND count learner given the SAME 128 examples in the SAME order as the smoke:
# before update u it has seen only examples 0..u-1; add-one smoothing over the grammar slot's legal tokens.
import json, math, collections
from pathlib import Path
src = Path(__file__).with_name("g_family_analysis.py").read_text(encoding="utf-8")
ns = {}
exec(compile(src.split("# ---------------- 5. input-free")[0], "g", "exec"), ns)
dec, seen, slot_contexts, losses_path = ns["dec"], ns["seen"], ns["slot_contexts"], ns["RUN"] / "run_001/updates.jsonl"
legal = {"expr": ["STATE", "BINARY"], "op": ["PLUS", "TIMES"], "noetic": ["N%d" % i for i in range(10)],
         "domain": ["D_NONE", "D_P", "D_C", "D_E", "D_O"], "drive": ["F_NONE"] + ["F%d" % i for i in range(1, 8)],
         "register": ["REG_ABSENT", "REG_NULL", "REG_A", "REG_f", "REG_E", "REG_T"], "END": ["EOS"]}
losses = [json.loads(l)["loss"] for l in losses_path.read_text(encoding="utf-8").splitlines() if l.strip()]
for label, key in (("slot kind only", lambda c: c[0]), ("slot kind + depth", lambda c: c)):
    table = collections.defaultdict(collections.Counter)
    ce_all = []
    for u, s in enumerate(seen):
        ce = []
        for ctx, name in slot_contexts(s):
            kind = ctx[0]
            c = table[key(ctx)]; V = legal[kind]
            p = (c.get(name, 0) + 1) / (sum(c.values()) + len(V))
            ce.append(-math.log(p))
        ce_all.append(sum(ce) / len(ce))
        for ctx, name in slot_contexts(s):
            table[key(ctx)][name] += 1
    print("online input-blind count learner [%s]: first-16 mean %.6f, last-16 mean %.6f | smoke GRU first-16 %.6f, last-16 %.6f"
          % (label, sum(ce_all[:16]) / 16, sum(ce_all[-16:]) / 16, sum(losses[:16]) / 16, sum(losses[-16:]) / 16))
    print("   updates where the GRU loss is below the input-blind learner: %d of 128" % sum(l < c for l, c in zip(losses, ce_all)))
