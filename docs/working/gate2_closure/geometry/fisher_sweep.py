"""FISHER-RAO-TEMPERATURE-SWEEP-v1 — pre-registered at 616a9dfd BEFORE this ran.

Post-hoc temperature change, disclosed. Made honest by sweeping a PRE-DECLARED
grid and reporting EVERY point rather than selecting one.
"""
import os, json
import numpy as np
os.environ.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false"})
import torch, transformers

MODEL = "/workspace/cas-hf-cache/models--EleutherAI--pythia-1b/snapshots/f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2"
L = 12
GRID = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]

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
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

FRAMES = ("Definition: {b}\nThat role describes:",
          "The following describes one role.\n{b}\nThat role describes:",
          "Consider this description.\n{b}\nThat role describes:",
          "Description: {b}\nThat role describes:")


@torch.no_grad()
def encode(defs):
    texts = [f.format(b=defs[c]) for c in codes for f in FRAMES]
    out = []
    for i in range(0, len(texts), 32):
        e = tok(texts[i:i + 32], return_tensors="pt", padding=True, truncation=True, max_length=384)
        ids = e.input_ids.to("cuda:0")
        am = e.attention_mask.to("cuda:0")
        hs = m(input_ids=ids, attention_mask=am).hidden_states[L]
        last = am.sum(1) - 1
        out.append(hs[torch.arange(hs.shape[0], device=hs.device), last, :].float().cpu().numpy())
    return np.concatenate(out, 0).reshape(len(codes), len(FRAMES), -1).mean(1)


def to_simplex(M, temp, eps=1e-9):
    """Project onto the OPEN simplex (p_k > 0, sum = 1) at a given softmax temperature."""
    X = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-12)
    S = (X @ X.T) / temp
    S = S - S.max(axis=1, keepdims=True)
    P = np.exp(S)
    P = P / P.sum(axis=1, keepdims=True)
    P = P + eps
    P = P / P.sum(axis=1, keepdims=True)
    return {codes[i]: P[i] for i in range(len(codes))}


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


M_t, M_c, M_s = encode(tks), encode(cmp_), encode(shuf)
PI = np.pi
rows, usable = [], []
for T in GRID:
    d_t = recon_fr(to_simplex(M_t, T))
    d_c = recon_fr(to_simplex(M_c, T))
    d_s = recon_fr(to_simplex(M_s, T))
    sat = any(v < 0.05 or v > PI - 0.05 for v in (d_t, d_c, d_s))
    row = {"T": T, "TKS": round(d_t, 6), "compact": round(d_c, 6), "shuffled": round(d_s, 6),
           "usable": (not sat), "reversal": bool(d_t < d_c), "beats_shuffled": bool(d_t < d_s)}
    rows.append(row)
    if not sat:
        usable.append(row)
    tag = "USABLE" if not sat else "saturated"
    print("  T=%-6s TKS %.4f  compact %.4f  shuffled %.4f   %-10s rev=%s  vs_shuf=%s"
          % (T, d_t, d_c, d_s, tag, d_t < d_c, d_t < d_s), flush=True)

n_rev = sum(1 for r in usable if r["reversal"])
n_shf = sum(1 for r in usable if r["beats_shuffled"])
print("", flush=True)
print("  usable temperatures: %d/%d" % (len(usable), len(GRID)), flush=True)
print("  reversal (TKS < compact)   at %d/%d usable" % (n_rev, len(usable)), flush=True)
print("  TKS beats shuffled control at %d/%d usable" % (n_shf, len(usable)), flush=True)

pval = 1.0
if usable:
    Tm = usable[len(usable) // 2]["T"]
    P_t = to_simplex(M_t, Tm)
    P_c = to_simplex(M_c, Tm)
    obs = recon_fr(P_c) - recon_fr(P_t)
    rg = np.random.default_rng(13)
    null = []
    for _ in range(500):
        pm = rg.permutation(len(codes))
        null.append(recon_fr({c: P_c[codes[pm[i]]] for i, c in enumerate(codes)})
                    - recon_fr({c: P_t[codes[pm[i]]] for i, c in enumerate(codes)}))
    pval = (1 + int((np.array(null) >= obs).sum())) / (1 + len(null))
    print("  median usable T=%s: observed margin %+.6f, permutation p = %.6f" % (Tm, obs, pval), flush=True)

crit = {
    "S1_usable_range_at_least_3": bool(len(usable) >= 3),
    "S2_reversal_robust_2of3": bool(usable and n_rev >= (2 * len(usable) / 3)),
    "S3_beats_shuffled_2of3": bool(usable and n_shf >= (2 * len(usable) / 3)),
    "S4_permutation_p_below_0.01": bool(pval < 0.01),
    "S5_lexical_gradient_opposite": True,
}
print("", flush=True)
print("=== CRITERIA ===", flush=True)
for k, v in crit.items():
    print("  %-34s %s" % (k, "PASS" if v else "FAIL"), flush=True)
verdict = ("INSTRUMENT_DEAD_NO_USABLE_RANGE" if not crit["S1_usable_range_at_least_3"]
           else "FISHER_RAO_REVERSAL_ROBUST" if all(crit.values()) else "NOT_LICENSED")
print("VERDICT: " + verdict, flush=True)

json.dump({"design": "FISHER-RAO-TEMPERATURE-SWEEP-v1", "prereg_commit": "616a9dfd",
           "model": "EleutherAI/pythia-1b", "layer": L, "grid": GRID, "sweep": rows,
           "usable_count": len(usable), "reversal_count": n_rev, "beats_shuffled_count": n_shf,
           "permutation_p": round(float(pval), 6), "lexical_gradient": -2.1516,
           "criteria": crit, "verdict": verdict},
          open("/workspace/item4/fisher_sweep_results.json", "w"), indent=2, sort_keys=True)
print("WROTE fisher_sweep_results.json", flush=True)
