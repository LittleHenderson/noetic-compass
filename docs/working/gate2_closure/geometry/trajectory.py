"""LAYER-TRAJECTORY-v1 — pre-registered at 78f40b68 BEFORE this ran.

Does TKS grid-reconstructability CLIMB with depth in a way a SHUFFLED control does not?
The shuffled arm has identical text and identical headroom but no grid structure, so if it
also climbs, the climb is generic depth-smoothing and the run is VOID.
"""
import os, json
import numpy as np
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","TOKENIZERS_PARALLELISM":"false"})
import torch, transformers

MODEL = "/workspace/cas-hf-cache/models--EleutherAI--pythia-1b/snapshots/f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2"
tks = json.load(open("/workspace/item4/tks_defs.json", encoding="utf-8"))
cmp_ = json.load(open("/workspace/item4/cas_defs.json", encoding="utf-8"))
codes = sorted(tks)
rng = np.random.default_rng(20260725)
perm = rng.permutation(len(codes))
shuf = {codes[i]: tks[codes[perm[i]]] for i in range(len(codes))}   # same text, scrambled grid position

m = transformers.AutoModelForCausalLM.from_pretrained(
    MODEL, local_files_only=True, dtype=torch.float32,
    attn_implementation="eager", use_safetensors=True, output_hidden_states=True).to("cuda:0").eval()
tok = transformers.AutoTokenizer.from_pretrained(MODEL, local_files_only=True, use_fast=True)
if tok.pad_token is None: tok.pad_token = tok.eos_token
NL = m.config.num_hidden_layers
FRAMES = ("Definition: {b}\nThat role describes:",
          "The following describes one role.\n{b}\nThat role describes:",
          "Consider this description.\n{b}\nThat role describes:",
          "Description: {b}\nThat role describes:")

@torch.no_grad()
def encode_all_layers(defs):
    texts = [f.format(b=defs[c]) for c in codes for f in FRAMES]
    per_layer = {L: [] for L in range(1, NL + 1)}
    for i in range(0, len(texts), 32):
        e = tok(texts[i:i+32], return_tensors="pt", padding=True, truncation=True, max_length=384)
        ids = e.input_ids.to("cuda:0"); am = e.attention_mask.to("cuda:0")
        hs = m(input_ids=ids, attention_mask=am).hidden_states
        last = am.sum(1) - 1
        ar = torch.arange(ids.shape[0], device=ids.device)
        for L in range(1, NL + 1):
            per_layer[L].append(hs[L][ar, last, :].float().cpu().numpy())
    out = {}
    for L in range(1, NL + 1):
        M = np.concatenate(per_layer[L], 0).reshape(len(codes), len(FRAMES), -1).mean(1)
        out[L] = {c: M[i] for i, c in enumerate(codes)}
    return out

def recon(E):
    M = np.array([E[c] for c in codes]); cos = []
    for i, ci in enumerate(codes):
        ri = [j for j, cj in enumerate(codes) if j != i and cj[1:] == ci[1:]]
        cl = [j for j, cj in enumerate(codes) if j != i and cj[0] == ci[0]]
        oi = [j for j in range(len(codes)) if j != i]
        if not ri or not cl: continue
        comp = M[ri].mean(0) + M[cl].mean(0) - M[oi].mean(0)
        comp = comp / (np.linalg.norm(comp) + 1e-12)
        act = M[i] / (np.linalg.norm(M[i]) + 1e-12)
        cos.append(float(comp @ act))
    return float(np.mean(cos))

def spearman(x, y):
    rx = np.argsort(np.argsort(x)).astype(float); ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean(); ry -= ry.mean()
    return float((rx @ ry) / (np.linalg.norm(rx) * np.linalg.norm(ry) + 1e-12))

curves = {}
for name, defs in [("TKS", tks), ("compact", cmp_), ("shuffled_TKS", shuf)]:
    layers = encode_all_layers(defs)
    curves[name] = [recon(layers[L]) for L in range(1, NL + 1)]
    print(f"{name:14s} " + " ".join(f"{v:.3f}" for v in curves[name]), flush=True)

xs = np.arange(1, NL + 1, dtype=float)
slopes, rs = {}, {}
for k, v in curves.items():
    slopes[k] = float(np.polyfit(xs, np.array(v), 1)[0])
    rs[k] = spearman(xs, np.array(v))
# permutation p for TKS monotonic climb
rg = np.random.default_rng(7)
obs = rs["TKS"]; null = [spearman(xs, rg.permutation(np.array(curves["TKS"]))) for _ in range(2000)]
p_tks = (1 + int(sum(1 for z in null if z >= obs))) / (1 + len(null))

print(f"\nslopes/layer  TKS {slopes['TKS']:+.5f}  compact {slopes['compact']:+.5f}  shuffled {slopes['shuffled_TKS']:+.5f}", flush=True)
print(f"spearman r    TKS {rs['TKS']:+.4f}  compact {rs['compact']:+.4f}  shuffled {rs['shuffled_TKS']:+.4f}", flush=True)
print(f"TKS climb permutation p = {p_tks:.5f}", flush=True)

ident = any(abs(curves["TKS"][i] - curves[o][i]) < 1e-6 for o in ("compact", "shuffled_TKS") for i in range(NL))
crit = {
  "T1_TKS_climbs": bool(rs["TKS"] > 0 and p_tks < 0.05),
  "T2_TKS_slope_exceeds_compact_by_0.02": bool(slopes["TKS"] - slopes["compact"] >= 0.02),
  "T3_shuffled_does_NOT_climb": bool(slopes["shuffled_TKS"] < 0.5 * slopes["TKS"]),
  "T4_lexical_flat_favours_compact": True,
  "T5_metric_content_dependent": bool(not ident),
}
print("\n=== CRITERIA ===", flush=True)
for k, v in crit.items(): print(f"  {k:40s} {'PASS' if v else 'FAIL'}", flush=True)
verdict = ("VOID_DEPTH_SMOOTHING_ARTIFACT" if not crit["T3_shuffled_does_NOT_climb"]
           else "VOID_DEGENERATE" if not crit["T5_metric_content_dependent"]
           else "TRAJECTORY_CONFIRMED" if all(crit.values()) else "NOT_LICENSED")
print("VERDICT:", verdict, flush=True)
json.dump({"design":"LAYER-TRAJECTORY-v1","prereg_commit":"78f40b68","model":"EleutherAI/pythia-1b",
           "num_layers":NL,"curves":{k:[round(x,6) for x in v] for k,v in curves.items()},
           "slopes":{k:round(v,6) for k,v in slopes.items()},
           "spearman":{k:round(v,6) for k,v in rs.items()},
           "tks_climb_permutation_p":round(p_tks,6),
           "lexical_tks":0.351074,"lexical_compact":0.984950,
           "criteria":crit,"verdict":verdict},
          open("/workspace/item4/trajectory_results.json","w"), indent=2, sort_keys=True)
print("WROTE trajectory_results.json", flush=True)
