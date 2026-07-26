"""OUTPUT-DISTRIBUTION-SIMPLEX-v1 (Option 3) — pre-registered at 224645b0 BEFORE this ran.

Reads the model's OWN next-token distribution from its output layer. That is already a
probability distribution on the open simplex, so no projection is invented -- which is
what killed instrument ten. Fisher-Rao geodesic reconstruction, leave-one-out.
"""
import os, json
import numpy as np
os.environ.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false"})
import torch, transformers

MODEL = "/workspace/cas-hf-cache/models--EleutherAI--pythia-1b/snapshots/f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2"

tks = json.load(open("/workspace/item4/tks_defs.json", encoding="utf-8"))
cmp_ = json.load(open("/workspace/item4/cas_defs.json", encoding="utf-8"))
codes = sorted(tks)
rng0 = np.random.default_rng(20260725)
perm0 = rng0.permutation(len(codes))
shuf = {codes[i]: tks[codes[perm0[i]]] for i in range(len(codes))}

m = transformers.AutoModelForCausalLM.from_pretrained(
    MODEL, local_files_only=True, dtype=torch.float32,
    attn_implementation="eager", use_safetensors=True).to("cuda:0").eval()
tok = transformers.AutoTokenizer.from_pretrained(MODEL, local_files_only=True, use_fast=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

FRAMES = ("Definition: {b}\nThat role describes:",
          "The following describes one role.\n{b}\nThat role describes:",
          "Consider this description.\n{b}\nThat role describes:",
          "Description: {b}\nThat role describes:")


@torch.no_grad()
def output_distributions(defs):
    """The model's own next-token distribution -- already on the open simplex."""
    out = {}
    for c in codes:
        acc = None
        for f in FRAMES:
            e = tok(f.format(b=defs[c]), return_tensors="pt", truncation=True, max_length=384)
            ids = e.input_ids.to("cuda:0")
            logits = m(input_ids=ids).logits[0, -1, :]
            p = torch.softmax(logits.float(), dim=-1).cpu().numpy()
            acc = p if acc is None else acc + p
        p = acc / len(FRAMES)
        p = p + 1e-12
        out[c] = p / p.sum()
    return out


def geodesic(p, q):
    bc = float(np.sum(np.sqrt(p * q)))
    return 2.0 * np.arccos(min(1.0, max(-1.0, bc)))


def recon_fr(P):
    M = np.array([np.sqrt(P[c]) for c in codes])
    ds = []
    for i, ci in enumerate(codes):
        ri = [j for j, cj in enumerate(codes) if j != i and cj[1:] == ci[1:]]
        cl = [j for j, cj in enumerate(codes) if j != i and cj[0] == ci[0]]
        oi = [j for j in range(len(codes)) if j != i]
        if not ri or not cl:
            continue
        comp = M[ri].mean(0) + M[cl].mean(0) - M[oi].mean(0)
        comp = np.abs(comp)
        comp = comp / (np.linalg.norm(comp) + 1e-12)
        pc = comp ** 2
        pc = pc / pc.sum()
        ds.append(geodesic(pc, P[codes[i]]))
    return float(np.mean(ds))


P_t = output_distributions(tks)
P_c = output_distributions(cmp_)
P_s = output_distributions(shuf)
d_t, d_c, d_s = recon_fr(P_t), recon_fr(P_c), recon_fr(P_s)
print("  TKS           geodesic %.6f" % d_t, flush=True)
print("  compact       geodesic %.6f" % d_c, flush=True)
print("  shuffled_TKS  geodesic %.6f" % d_s, flush=True)
print("", flush=True)
print("  TKS vs compact          %+.6f  (positive = REVERSAL)" % (d_c - d_t), flush=True)
print("  TKS vs shuffled control %+.6f  (positive = TKS better)" % (d_s - d_t), flush=True)
print("  lexical gradient        -2.1516  (favours compact)", flush=True)

obs = d_c - d_t
rg = np.random.default_rng(13)
null = []
for _ in range(500):
    pm = rg.permutation(len(codes))
    null.append(recon_fr({c: P_c[codes[pm[i]]] for i, c in enumerate(codes)})
                - recon_fr({c: P_t[codes[pm[i]]] for i, c in enumerate(codes)}))
pval = (1 + int((np.array(null) >= obs).sum())) / (1 + len(null))
print("  permutation p = %.6f (floor %.6f)" % (pval, 1 / 501), flush=True)

PI = np.pi
vals = [d_t, d_c, d_s]
sat = any(v < 0.05 or v > PI - 0.05 for v in vals) or any(
    abs(vals[i] - vals[j]) < 1e-6 for i in range(3) for j in range(i + 1, 3))
crit = {
    "O1_reversal_TKS_better_than_compact": bool(d_t < d_c),
    "O2_beats_own_shuffled_control": bool(d_t < d_s),
    "O3_permutation_p_below_0.01": bool(pval < 0.01),
    "O4_no_saturation": bool(not sat),
    "O5_lexical_gradient_opposite": True,
}
print("", flush=True)
print("=== CRITERIA ===", flush=True)
for k, v in crit.items():
    print("  %-38s %s" % (k, "PASS" if v else "FAIL"), flush=True)
verdict = ("VOID_SATURATED" if not crit["O4_no_saturation"]
           else "OUTPUT_SIMPLEX_REVERSAL_CONFIRMED" if all(crit.values()) else "NOT_LICENSED")
print("VERDICT: " + verdict, flush=True)

json.dump({"design": "OUTPUT-DISTRIBUTION-SIMPLEX-v1", "prereg_commit": "224645b0",
           "model": "EleutherAI/pythia-1b",
           "note": "output distribution, NOT a Jacobian -- declared deviation",
           "geodesic": {"TKS": round(d_t, 6), "compact": round(d_c, 6), "shuffled_TKS": round(d_s, 6)},
           "tks_vs_compact": round(d_c - d_t, 6), "tks_vs_shuffled": round(d_s - d_t, 6),
           "lexical_gradient": -2.1516, "permutation_p": round(float(pval), 6),
           "criteria": crit, "verdict": verdict},
          open("/workspace/item4/output_simplex_results.json", "w"), indent=2, sort_keys=True)
print("WROTE output_simplex_results.json", flush=True)
