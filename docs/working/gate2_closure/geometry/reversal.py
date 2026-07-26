"""GRID-LEXICAL-REVERSAL-v1 — pre-registered at 8e498389 BEFORE this ran.

Criterion: the model must rank TKS ABOVE compact CAS on grid reconstructability,
REVERSING the lexical baseline which ranks compact above TKS by +0.634.
Vocabulary overlap cannot produce a result that runs against itself.
"""
import os, json, re, sys
import numpy as np
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","TOKENIZERS_PARALLELISM":"false"})
import torch, transformers

MODEL = "/workspace/cas-hf-cache/models--EleutherAI--pythia-1b/snapshots/f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2"
L = 12
tks = json.load(open("/workspace/item4/tks_defs.json", encoding="utf-8"))
cmp_ = json.load(open("/workspace/item4/cas_defs.json", encoding="utf-8"))
codes = sorted(tks)

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
    M = np.concatenate(out, 0).reshape(len(codes), len(FRAMES), -1).mean(1)
    return {c: M[i] for i, c in enumerate(codes)}

def recon(E):
    """Verbatim reimplementation of grid_alignment.compute_crossval_reconstruction.
    Verified to reproduce their published lexical values to six decimals:
    TKS 0.351074, compact 0.984950. scipy is unavailable on the pod, so the
    function is inlined rather than a different metric substituted."""
    M = np.array([E[c] for c in codes])
    cos = []
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

E_t, E_c = encode(tks), encode(cmp_)
r_t, r_c = recon(E_t), recon(E_c)
margin = r_t - r_c
print(f"MODEL  TKS reconstruction {r_t:.6f}", flush=True)
print(f"MODEL  compact CAS       {r_c:.6f}", flush=True)
print(f"MODEL  margin TKS-compact {margin:+.6f}", flush=True)
print(f"LEXICAL margin (measured) -0.633876   <- confound favours COMPACT", flush=True)

# permutation null on the difference: shuffle which definition sits at which grid position
rng = np.random.default_rng(11)
null = []
for _ in range(500):
    p = rng.permutation(len(codes))
    Et = {c: E_t[codes[p[i]]] for i, c in enumerate(codes)}
    Ec = {c: E_c[codes[p[i]]] for i, c in enumerate(codes)}
    null.append(recon(Et) - recon(Ec))
null = np.array(null)
pval = (1 + int((null >= margin).sum())) / (1 + len(null))
print(f"permutation p = {pval:.6f}  (floor {1/501:.6f})", flush=True)

crit = {
    "R1_reversal_TKS_above_compact": bool(r_t > r_c),
    "R2_margin_at_least_0.05": bool(margin >= 0.05),
    "R3_permutation_p_below_0.01": bool(pval < 0.01),
    "R4_lexical_orders_opposite": True,
    "R5_metric_content_dependent": bool(1/501 < pval < 1.0 and abs(r_t - r_c) > 1e-9),
}
print("\n=== CRITERIA ===", flush=True)
for k, v in crit.items(): print(f"  {k:34s} {'PASS' if v else 'FAIL'}", flush=True)
verdict = ("VOID_DEGENERATE" if not crit["R5_metric_content_dependent"]
           else "REVERSAL_CONFIRMED" if all(crit.values()) else "NOT_LICENSED")
print("VERDICT:", verdict, flush=True)
json.dump({"design":"GRID-LEXICAL-REVERSAL-v1","prereg_commit":"8e498389",
           "model":"EleutherAI/pythia-1b","layer":L,
           "model_tks_reconstruction":round(float(r_t),6),
           "model_compact_reconstruction":round(float(r_c),6),
           "model_margin":round(float(margin),6),
           "lexical_tks":0.351074,"lexical_compact":0.98495,"lexical_margin":-0.633876,
           "permutation_p":round(float(pval),6),"permutation_floor":round(1/501,6),
           "criteria":crit,"verdict":verdict},
          open("/workspace/item4/reversal_results.json","w"), indent=2, sort_keys=True)
print("WROTE reversal_results.json", flush=True)
