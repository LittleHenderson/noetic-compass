"""SCRAMBLE-NULL-COMPLETION-v1 + WOM-FR secondary — pre-registered at 3385aa63 BEFORE this ran.

One GPU encode (instrument-12 pipeline, verbatim), then all statistics on CPU.
Scrambling permutes the ASSIGNMENT of texts to grid cells, so the encoded
distributions are computed once and re-indexed per permutation.
"""
import os, json, re, collections
import numpy as np
os.environ.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false"})
import torch, transformers

MODEL = "/workspace/cas-hf-cache/models--EleutherAI--pythia-1b/snapshots/f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2"
N_SCRAMBLES = 200
SEEDS = list(range(1, N_SCRAMBLES + 1))          # seed 20260725 retired per prereg

tks = json.load(open("/workspace/item4/tks_defs.json", encoding="utf-8"))
cmp_ = json.load(open("/workspace/item4/cas_defs.json", encoding="utf-8"))
codes = sorted(tks)
N = len(codes)

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
    """Instrument-12 pipeline verbatim: model's own next-token distribution per cell."""
    out = np.zeros((N, m.config.vocab_size), dtype=np.float64)
    for i, c in enumerate(codes):
        acc = None
        for f in FRAMES:
            e = tok(f.format(b=defs[c]), return_tensors="pt", truncation=True, max_length=384)
            logits = m(input_ids=e.input_ids.to("cuda:0")).logits[0, -1, :]
            p = torch.softmax(logits.float(), dim=-1).cpu().numpy()
            acc = p if acc is None else acc + p
        p = acc / len(FRAMES)
        p = p + 1e-12
        out[i] = p / p.sum()
    return out                                    # (40, V) rows on the open simplex


def geodesic_rows(sq_a, sq_b):
    bc = float(np.sum(sq_a * sq_b))
    return 2.0 * np.arccos(min(1.0, max(-1.0, bc)))


ROW = {c: [j for j, cj in enumerate(codes) if cj[1:] == c[1:] and cj != c] for c in codes}
COL = {c: [j for j, cj in enumerate(codes) if cj[0] == c[0] and cj != c] for c in codes}
OTH = {c: [j for j, cj in enumerate(codes) if cj != c] for c in codes}


def recon_percell(P):
    """recon_fr per cell (verbatim math from output_simplex.py), on a (40,V) matrix."""
    M = np.sqrt(P)
    ds = np.zeros(N)
    for i, c in enumerate(codes):
        comp = M[ROW[c]].mean(0) + M[COL[c]].mean(0) - M[OTH[c]].mean(0)
        comp = np.abs(comp)
        comp = comp / (np.linalg.norm(comp) + 1e-12)
        pc = comp ** 2
        pc = pc / pc.sum()
        ds[i] = geodesic_rows(np.sqrt(pc), M[i])
    return ds


def scramble_stats(P, seeds):
    means = np.zeros(len(seeds))
    for k, s in enumerate(seeds):
        perm = np.random.default_rng(s).permutation(N)
        means[k] = recon_percell(P[perm]).mean()
    return means


# ---------- lexical channels (CPU), SAME seeds, SAME statistic ----------
STOP = set("the a an of and or to in is are be for on with that this it as by from at was were not no all any some its their".split())


def word_probs(defs):
    vocab = sorted({w for d in defs.values() for w in re.findall(r"[a-z]+", d.lower()) if w not in STOP and len(w) > 2})
    idx = {w: i for i, w in enumerate(vocab)}
    P = np.zeros((N, len(vocab)))
    for i, c in enumerate(codes):
        for w in re.findall(r"[a-z]+", defs[c].lower()):
            if w in idx:
                P[i, idx[w]] += 1.0
    P = P + 1e-9
    return P / P.sum(1, keepdims=True)


def char_probs(defs, ns=(3, 4, 5)):
    cnt = [collections.Counter() for _ in codes]
    vocab = set()
    for i, c in enumerate(codes):
        t = re.sub(r"\s+", " ", defs[c].lower())
        for n in ns:
            for j in range(len(t) - n + 1):
                g = t[j:j + n]
                cnt[i][g] += 1
                vocab.add(g)
    vocab = sorted(vocab)
    idx = {g: i for i, g in enumerate(vocab)}
    P = np.zeros((N, len(vocab)))
    for i in range(N):
        for g, v in cnt[i].items():
            P[i, idx[g]] = v
    P = P + 1e-9
    return P / P.sum(1, keepdims=True)


def rel_margin(P, seeds):
    d_real = recon_percell(P).mean()
    null = scramble_stats(P, seeds)
    rel = (null.mean() - d_real) / null.mean()
    p_exact = (1 + int((null <= d_real).sum())) / (1 + len(null))
    return d_real, null, rel, p_exact


print("encoding TKS + compact on GPU (one pass each)...", flush=True)
P_T = output_distributions(tks)
P_C = output_distributions(cmp_)
print("encode done; all remaining statistics are CPU on the dump", flush=True)

d_t, null_t, rel_t, p_t = rel_margin(P_T, SEEDS)
d_c, null_c, rel_c, p_c = rel_margin(P_C, SEEDS)
print("MODEL TKS     d=%.6f null(mean %.6f, 2.5pct %.6f) rel=%.4f exact p=%.5f" % (
    d_t, null_t.mean(), np.percentile(null_t, 2.5), rel_t, p_t), flush=True)
print("MODEL compact d=%.6f null(mean %.6f) rel=%.4f exact p=%.5f  <- E5, reported however it lands" % (
    d_c, null_c.mean(), rel_c, p_c), flush=True)

W_T = word_probs(tks); C_T = char_probs(tks)
_, _, rel_wt, _ = rel_margin(W_T, SEEDS)
_, _, rel_ct, _ = rel_margin(C_T, SEEDS)
lex_max = max(rel_wt, rel_ct)
print("LEXICAL TKS rel: word %.4f  char %.4f  -> max %.4f" % (rel_wt, rel_ct, lex_max), flush=True)

# E3b: affine lexical->model calibration across arms (TKS, compact + their scrambles' means)
xs = np.array([rel_wt, max(  # compact lexical rels
    rel_margin(word_probs(cmp_), SEEDS)[2], rel_margin(char_probs(cmp_), SEEDS)[2])])
ys = np.array([rel_t, rel_c])
# with 2 points the fit is exact; report the residual structure honestly instead
print("E3b two-point record: lex rels %s -> model rels %s (2 points = exact fit; residual reported, not tested)" % (
    np.round(xs, 4).tolist(), np.round(ys, 4).tolist()), flush=True)

# per-cell bootstrap for E2
rng = np.random.default_rng(777)
cells_t = recon_percell(P_T)
null_cell_mean = np.array([recon_percell(P_T[np.random.default_rng(s).permutation(N)]) for s in SEEDS]).mean(0)
diffs = null_cell_mean - cells_t
boot = np.array([diffs[rng.integers(0, N, N)].mean() for _ in range(5000)])
ci = (np.percentile(boot, 2.5), np.percentile(boot, 97.5))
print("E2 per-cell bootstrap CI of (null - TKS): [%.5f, %.5f]" % ci, flush=True)

# ---------- WOM-FR secondary ----------
GAPS = np.array([1, 2, 3, 1, 2, 1], dtype=float)   # AB AC AD BC BD CD
PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
WORLDS = ["A", "B", "C", "D"]


def midrank(v):
    order = np.argsort(v, kind="mergesort")
    ranks = np.empty(len(v))
    sv = v[order]
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    return ranks


def spearman_mid(a, b):
    ra, rb = midrank(a), midrank(b)
    ra -= ra.mean(); rb -= rb.mean()
    den = np.linalg.norm(ra) * np.linalg.norm(rb)
    return float(ra @ rb / den) if den > 0 else 0.0


def wom_mean_rho(P, world_perm_per_col=None):
    sq = np.sqrt(P)
    rhos = []
    for n in range(1, 11):
        suffix = "10" if n == 10 else str(n)
        cells = [codes.index(w + suffix) for w in WORLDS]
        if world_perm_per_col is not None:
            cells = [cells[k] for k in world_perm_per_col[n - 1]]
        dists = np.array([geodesic_rows(sq[cells[a]], sq[cells[b]]) for a, b in PAIRS])
        rhos.append(spearman_mid(dists, GAPS))
    return float(np.mean(rhos))


rho_t = wom_mean_rho(P_T)
rng2 = np.random.default_rng(4242)
null_rho = np.array([wom_mean_rho(P_T, [rng2.permutation(4) for _ in range(10)]) for _ in range(10000)])
p_rho = (1 + int((null_rho >= rho_t).sum())) / (1 + len(null_rho))
rho_c = wom_mean_rho(P_C)
print("WOM-FR: TKS mean rho %.4f (bar >= +0.32), perm p %.5f (bar < 0.005); compact rho %.4f (excluded, W3)" % (
    rho_t, p_rho, rho_c), flush=True)

# ---------- criteria ----------
PI = np.pi
sat = any(v < 0.05 or v > PI - 0.05 for v in (d_t, d_c, null_t.mean(), null_c.mean()))
E = {
    "E1_below_2.5pct_null": bool(d_t < np.percentile(null_t, 2.5) and p_t <= 0.025),
    "E2_sanity_ci_excludes_0": bool(ci[0] > 0),
    "E3_margin_beyond_lexical_0.10": bool((rel_t - lex_max) >= 0.10),
    "E4_no_saturation": bool(not sat),
}
W = {
    "W1_ordinal_rho_and_p": bool(rho_t >= 0.32 and p_rho < 0.005),
}
print("\n=== PRIMARY ===", flush=True)
for k, v in E.items():
    print("  %-34s %s" % (k, "PASS" if v else "FAIL"), flush=True)
print("=== SECONDARY ===", flush=True)
for k, v in W.items():
    print("  %-34s %s" % (k, "PASS" if v else "FAIL"), flush=True)
primary = ("VOID_SATURATED" if not E["E4_no_saturation"]
           else "PRIMARY_LICENSED" if (E["E1_below_2.5pct_null"] and E["E3_margin_beyond_lexical_0.10"]) else "PRIMARY_NOT_LICENSED")
secondary = "SECONDARY_LICENSED" if W["W1_ordinal_rho_and_p"] else "SECONDARY_NOT_LICENSED"
print("VERDICT: %s | %s" % (primary, secondary), flush=True)

np.savez("/workspace/item4/scramble_null_dump.npz",
         P_T_sqrt_head=np.sqrt(P_T[:, :4096]).astype(np.float32),
         cells_t=cells_t, null_t=null_t, null_c=null_c,
         null_cell_mean=null_cell_mean, null_rho=null_rho.astype(np.float32),
         d_t=d_t, d_c=d_c, rel_t=rel_t, rel_c=rel_c,
         rel_word=rel_wt, rel_char=rel_ct, rho_t=rho_t, rho_c=rho_c, p_rho=p_rho, p_t=p_t)
json.dump({"design": "SCRAMBLE-NULL-COMPLETION-v1", "prereg_commit": "3385aa63",
           "model": "EleutherAI/pythia-1b", "seeds": "1..200 (20260725 retired)",
           "primary": {"d_tks": round(d_t, 6), "null_mean": round(float(null_t.mean()), 6),
                        "null_2p5": round(float(np.percentile(null_t, 2.5)), 6),
                        "rel_margin": round(rel_t, 6), "exact_p": round(p_t, 6),
                        "lexical_rel_word": round(rel_wt, 6), "lexical_rel_char": round(rel_ct, 6),
                        "E3_margin_minus_lexical": round(rel_t - lex_max, 6),
                        "E2_bootstrap_ci": [round(ci[0], 6), round(ci[1], 6)],
                        "compact_rel_E5": round(rel_c, 6), "compact_exact_p": round(p_c, 6)},
           "secondary_womfr": {"tks_mean_rho": round(rho_t, 6), "perm_p": round(p_rho, 6),
                                "compact_rho_excluded_W3": round(rho_c, 6)},
           "criteria_primary": E, "criteria_secondary": W,
           "verdict": primary + " | " + secondary},
          open("/workspace/item4/scramble_null_results.json", "w"), indent=2, sort_keys=True)
print("WROTE scramble_null_results.json + dump", flush=True)
