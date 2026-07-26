"""FISHER-RAO-SIMPLEX-v2 — pre-registered BEFORE this ran.

v1 (7e806675) voided: softmax with temp=1.0 collapsed to uniform distributions
because cosine similarities between definition embeddings are all near 0.97.
Result: geodesic distances 0.003–0.017 where max is π≈3.14. F5 fired.

v2 fix: adaptive temperature τ = std(off-diagonal cosine similarities),
floored at 0.005. This is a deterministic function of the cosine matrix,
not a tuned parameter. The lexical baseline uses the SAME rule for parity.

Pre-registered rule: τ = max(0.005, std(all pairwise cosine similarities
excluding the diagonal)). Applied identically to all arms and all layers.
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

def adaptive_temperature(M):
    """τ = max(0.005, std of off-diagonal cosine similarities).
    
    Deterministic function of the embedding matrix. Not tuned.
    Off-diagonal exclusion prevents self-similarity (always 1.0) from
    inflating the standard deviation.
    """
    X = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-12)
    C = X @ X.T
    n = C.shape[0]
    mask = ~np.eye(n, dtype=bool)
    off_diag = C[mask]
    tau = max(0.005, float(np.std(off_diag)))
    return tau

def to_simplex(M, eps=1e-6, temp=None):
    """Project onto the OPEN simplex.
    
    If temp is None, uses adaptive_temperature(M).
    """
    if temp is None:
        temp = adaptive_temperature(M)
    X = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-12)
    S = X @ X.T / temp
    S = S - S.max(axis=1, keepdims=True)
    P = np.exp(S); P = P / P.sum(axis=1, keepdims=True)
    P = P + eps; P = P / P.sum(axis=1, keepdims=True)
    return {codes[i]: P[i] for i in range(len(codes))}, temp

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

# ═══════════════════════════════════════════════════════════════════════════
# MODEL
# ═══════════════════════════════════════════════════════════════════════════

print("Encoding definitions...", flush=True)
E_t, E_c, E_s = encode(tks), encode(cmp_), encode(shuf)

print(f"\nAdaptive temperatures:", flush=True)
P_t, tau_t = to_simplex(E_t)
P_c, tau_c = to_simplex(E_c)
P_s, tau_s = to_simplex(E_s)
print(f"  TKS       τ = {tau_t:.6f}", flush=True)
print(f"  compact   τ = {tau_c:.6f}", flush=True)
print(f"  shuffled  τ = {tau_s:.6f}", flush=True)

res = {}
for name, P in [("TKS", P_t), ("compact", P_c), ("shuffled_TKS", P_s)]:
    res[name] = recon_fr(P)
    print(f"  {name:14s} geodesic {res[name]:.6f}", flush=True)

# ═══════════════════════════════════════════════════════════════════════════
# LEXICAL BASELINE (same adaptive rule for parity)
# ═══════════════════════════════════════════════════════════════════════════

import re, collections
STOP = set("the a an of and or to in is are be for on with that this it as by "
           "from at was were not no all any some its their".split())
all_texts = [tks[c] for c in codes] + [cmp_[c] for c in codes]
all_words = set()
for t in all_texts:
    all_words.update(w.lower() for w in re.findall(r"[a-z]+", str(t).lower())
                     if w.lower() not in STOP and len(w) > 2)
vocab = sorted(all_words)
w2i = {w: i for i, w in enumerate(vocab)}

def bow(text):
    v = np.zeros(len(vocab))
    for w in re.findall(r"[a-z]+", str(text).lower()):
        if w.lower() not in STOP and len(w) > 2 and w.lower() in w2i:
            v[w2i[w.lower()]] += 1
    n = np.linalg.norm(v)
    return v / n if n > 0 else v

E_lex_t = np.array([bow(tks[c]) for c in codes])
E_lex_c = np.array([bow(cmp_[c]) for c in codes])
P_lex_t, tau_lex_t = to_simplex(E_lex_t)
P_lex_c, tau_lex_c = to_simplex(E_lex_c)
lex_t = recon_fr(P_lex_t)
lex_c = recon_fr(P_lex_c)
print(f"\nLEXICAL (adaptive τ):", flush=True)
print(f"  TKS       τ = {tau_lex_t:.6f}  geodesic {lex_t:.6f}", flush=True)
print(f"  compact   τ = {tau_lex_c:.6f}  geodesic {lex_c:.6f}", flush=True)
print(f"  margin (compact - TKS) = {lex_c - lex_t:+.6f}", flush=True)

# ═══════════════════════════════════════════════════════════════════════════
# CRITERIA
# ═══════════════════════════════════════════════════════════════════════════

margin_shuf = res["shuffled_TKS"] - res["TKS"]       # positive = TKS better
margin_cmp  = res["compact"] - res["TKS"]             # positive = REVERSAL
lex_margin  = lex_c - lex_t                            # positive = compact leads

print(f"\n  TKS vs shuffled : {margin_shuf:+.6f}  (positive = TKS better)", flush=True)
print(f"  TKS vs compact  : {margin_cmp:+.6f}  (positive = REVERSAL)", flush=True)
print(f"  lexical margin  : {lex_margin:+.6f}  (positive = compact leads lexically)", flush=True)

# Permutation test on TKS vs compact
rg = np.random.default_rng(13); null = []
for _ in range(500):
    p = rg.permutation(len(codes))
    Pt = {c: P_t[codes[p[i]]] for i, c in enumerate(codes)}
    Pc = {c: P_c[codes[p[i]]] for i, c in enumerate(codes)}
    null.append(recon_fr(Pc) - recon_fr(Pt))
null = np.array(null)
pval = (1 + int((null >= margin_cmp).sum())) / (1 + len(null))
print(f"  permutation p = {pval:.6f} (floor {1/501:.6f})", flush=True)

# Saturation guard: both ends
vals = list(res.values())
# Too low: geodesic < 0.01 (near-zero = distributions identical = projection failed)
# Too high: geodesic > π - 0.01 (near-max = distributions orthogonal)
# Identical arms: any two arms within 1e-6
sat_low  = any(v < 0.01 for v in vals)
sat_high = any(v > np.pi - 0.01 for v in vals)
sat_same = any(abs(vals[i] - vals[j]) < 1e-6 for i in range(3) for j in range(i+1, 3))
sat = sat_low or sat_high or sat_same

# Check whether the adaptive temperature actually fixed the dynamic range
has_range = (max(vals) - min(vals)) > 0.05  # at least 0.05 spread

crit = {
    "F1_TKS_beats_shuffled_by_0.05": bool(margin_shuf >= 0.05),
    "F2_reversal_TKS_better_than_compact": bool(margin_cmp > 0),
    "F3_permutation_p_below_0.01": bool(pval < 0.01),
    "F4_lexical_opposite": bool(lex_margin > 0),
    "F5_no_saturation": bool(not sat),
    "F6_dynamic_range": bool(has_range),
}
print("\n=== CRITERIA ===", flush=True)
for k, v in crit.items():
    print(f"  {k:40s} {'PASS' if v else 'FAIL'}", flush=True)

if not crit["F5_no_saturation"] or not crit["F6_dynamic_range"]:
    verdict = "VOID_SATURATED"
elif crit["F1_TKS_beats_shuffled_by_0.05"] and crit["F2_reversal_TKS_better_than_compact"] and crit["F3_permutation_p_below_0.01"]:
    verdict = "FISHER_RAO_REVERSAL_CONFIRMED"
else:
    verdict = "NOT_LICENSED"

print(f"\nVERDICT: {verdict}", flush=True)
print(f"  dynamic range: {max(vals)-min(vals):.4f}  (need > 0.05)", flush=True)
print(f"  low sat: {sat_low}  high sat: {sat_high}  identical: {sat_same}", flush=True)

json.dump({"design":"FISHER-RAO-SIMPLEX-v2","prereg_commit":"ADAPTIVE_TAU",
           "model":"EleutherAI/pythia-1b","layer":L,
           "temperatures":{"tks":round(tau_t,6),"compact":round(tau_c,6),
                           "shuffled":round(tau_s,6),
                           "lexical_tks":round(tau_lex_t,6),
                           "lexical_compact":round(tau_lex_c,6)},
           "geodesic":{k:round(v,6) for k,v in res.items()},
           "lexical_geodesic":{"tks":round(lex_t,6),"compact":round(lex_c,6)},
           "tks_vs_shuffled":round(margin_shuf,6),
           "tks_vs_compact":round(margin_cmp,6),
           "lexical_margin":round(lex_margin,6),
           "permutation_p":round(pval,6),
           "dynamic_range":round(max(vals)-min(vals),6),
           "criteria":crit,"verdict":verdict},
          open("/workspace/item4/fisher_v2_results.json","w"), indent=2, sort_keys=True)
print("WROTE fisher_v2_results.json", flush=True)
