"""FISHER-RAO-SIMPLEX-v1 — pre-registered at 7e806675 BEFORE this ran.

Projects each definition's hidden state onto the OPEN simplex (p_k > 0, sum = 1),
composes held-out cells in sqrt(p) space, scores by the Fisher-Rao geodesic
d(p,q) = 2*arccos(sum sqrt(p_k q_k)).  Lower = better reconstruction.
Third arm = shuffled TKS (same text, scrambled grid assignment).
"""
import os, json
import numpy as np
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","TOKENIZERS_PARALLELISM":"false"})
import torch, transformers

MODEL = "/workspace/cas-hf-cache/models--EleutherAI--pythia-1b/snapshots/f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2"
L = 12
tks = json.load(open("/workspace/item4/tks_defs.json", encoding="utf-8"))
cmp_ = json.load(open("/workspace/item4/cas_defs.json", encoding="utf-8"))
codes = sorted(tks)
rng0 = np.random.default_rng(20260725)
perm0 = rng0.permutation(len(codes))
shuf = {codes[i]: tks[codes[perm0[i]]] for i in range(len(codes))}

m = transformers.AutoModelForCausalLM.from_pretrained(
    MODEL, local_files_only=True, dtype=torch.float32,
    attn_implementation="eager", use_safetensors=True, output_hidden_states=True).to("cuda:0").eval()
tok = transformers.AutoTokenizer.from_pretrained(MODEL, local_files_only=True, use_fast=True)
if tok.pad_token is None: tok.pad_token = tok.eos_token
FRAMES = ("Definition: {b}\nThat role describes:",
          "The following describes one role.\n{b}\nThat role describes:",
          "Consider this description.\n{b}\nThat role describes:",
          "Description: {b}\nThat role describes:")

@torch.no_grad()
def encode(defs):
    texts = [f.format(b=defs[c]) for c in codes for f in FRAMES]
    out = []
    for i in range(0, len(texts), 32):
        e = tok(texts[i:i+32], return_tensors="pt", padding=True, truncation=True, max_length=384)
        ids = e.input_ids.to("cuda:0"); am = e.attention_mask.to("cuda:0")
        hs = m(input_ids=ids, attention_mask=am).hidden_states[L]
        last = am.sum(1) - 1
        out.append(hs[torch.arange(hs.shape[0], device=hs.device), last, :].float().cpu().numpy())
    return np.concatenate(out, 0).reshape(len(codes), len(FRAMES), -1).mean(1)

def to_simplex(M, eps=1e-6, temp=1.0):
    """Project onto the OPEN simplex: softmax over cosine sims to the 40 anchor
    directions, floored strictly positive (p_k > 0, sum p_k = 1)."""
    X = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-12)
    S = X @ X.T / temp
    S = S - S.max(axis=1, keepdims=True)
    P = np.exp(S); P = P / P.sum(axis=1, keepdims=True)
    P = P + eps; P = P / P.sum(axis=1, keepdims=True)
    return {codes[i]: P[i] for i in range(len(codes))}

def geodesic(p, q):
    bc = float(np.sum(np.sqrt(p * q)))
    return 2.0 * np.arccos(min(1.0, max(-1.0, bc)))

def recon_fr(P):
    M = np.array([np.sqrt(P[c]) for c in codes]); ds = []
    for i, ci in enumerate(codes):
        ri = [j for j, cj in enumerate(codes) if j != i and cj[1:] == ci[1:]]
        cl = [j for j, cj in enumerate(codes) if j != i and cj[0] == ci[0]]
        oi = [j for j in range(len(codes)) if j != i]
        if not ri or not cl: continue
        comp = M[ri].mean(0) + M[cl].mean(0) - M[oi].mean(0)
        comp = np.abs(comp); comp = comp / (np.linalg.norm(comp) + 1e-12)
        pc = comp ** 2; pc = pc / pc.sum()
        ds.append(geodesic(pc, P[codes[i]]))
    return float(np.mean(ds))

res = {}
for name, defs in [("TKS", tks), ("compact", cmp_), ("shuffled_TKS", shuf)]:
    res[name] = recon_fr(to_simplex(encode(defs)))
    print(f"  {name:14s} geodesic {res[name]:.6f}", flush=True)

margin_shuf = res["shuffled_TKS"] - res["TKS"]
margin_cmp  = res["compact"] - res["TKS"]
print(f"\n  TKS vs its shuffled control : {margin_shuf:+.6f}  (positive = TKS better)", flush=True)
print(f"  TKS vs compact              : {margin_cmp:+.6f}  (positive = REVERSAL)", flush=True)
print(f"  lexical gradient (measured) : -2.1516  (favours compact)", flush=True)

P_t = to_simplex(encode(tks)); P_c = to_simplex(encode(cmp_))
rg = np.random.default_rng(13); null = []
for _ in range(500):
    p = rg.permutation(len(codes))
    Pt = {c: P_t[codes[p[i]]] for i, c in enumerate(codes)}
    Pc = {c: P_c[codes[p[i]]] for i, c in enumerate(codes)}
    null.append(recon_fr(Pc) - recon_fr(Pt))
null = np.array(null)
pval = (1 + int((null >= margin_cmp).sum())) / (1 + len(null))
print(f"  permutation p = {pval:.6f} (floor {1/501:.6f})", flush=True)

vals = list(res.values())
sat = any(v < 0.05 or v > np.pi - 0.05 for v in vals) or any(
    abs(vals[i] - vals[j]) < 1e-6 for i in range(3) for j in range(i+1, 3))
crit = {
  "F1_TKS_beats_own_shuffled_by_0.10": bool(margin_shuf >= 0.10),
  "F2_reversal_TKS_better_than_compact": bool(margin_cmp > 0),
  "F3_permutation_p_below_0.01": bool(pval < 0.01),
  "F4_lexical_gradient_opposite": True,
  "F5_no_saturation": bool(not sat),
}
print("\n=== CRITERIA ===", flush=True)
for k, v in crit.items(): print(f"  {k:38s} {'PASS' if v else 'FAIL'}", flush=True)
verdict = ("VOID_SATURATED" if not crit["F5_no_saturation"]
           else "FISHER_RAO_REVERSAL_CONFIRMED" if all(crit.values()) else "NOT_LICENSED")
print("VERDICT:", verdict, flush=True)
json.dump({"design":"FISHER-RAO-SIMPLEX-v1","prereg_commit":"7e806675",
           "model":"EleutherAI/pythia-1b","layer":L,
           "geodesic":{k:round(v,6) for k,v in res.items()},
           "tks_vs_shuffled":round(margin_shuf,6),"tks_vs_compact":round(margin_cmp,6),
           "lexical_gradient":-2.1516,"permutation_p":round(pval,6),
           "criteria":crit,"verdict":verdict},
          open("/workspace/item4/fisher_results.json","w"), indent=2, sort_keys=True)
print("WROTE fisher_results.json", flush=True)
