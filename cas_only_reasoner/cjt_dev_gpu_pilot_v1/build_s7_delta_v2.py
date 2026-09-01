"""build_s7_delta_v2.py -- CJT-DEV-P1-S7Delta.1: the soft WordNet semantic
composition simplex control, REBUILT under the owner's adopt-with-modifications
ruling. Non-claim-bearing development artifact.

What changed vs v1 (`build_s7_delta.py`, commit 354f315c -- preserved):
  1. EXCLUSION LAW (ruling point 7): the TF-IDF vocabulary, the 4-factor NMF,
     and the balancing transform are all fit on the WordNet verb-sense
     BACKGROUND with the 16 target senses EXCLUDED; the targets are projected
     afterward. The target vocabulary can no longer shape its own control.
  2. FACTOR-STABILITY GATE: the primary deterministic fit (nndsvda) is compared
     against 5 predetermined random-init fits; components aligned by optimal
     permutation (Hungarian on cosine similarity of H); gate on the median
     across fits of the mean per-target-row Jensen-Shannon divergence.
  3. PERMUTATION-INVARIANT, NULL-CALIBRATED ANTI-COPY GATES (points 10):
       A_hard* = max over all 24 column permutations of argmax agreement /16
       A_soft* = max over all 24 column permutations of mean CAS-aligned mass
     PRIMARY null: the exact conditional shuffle null -- keep the observed 16
     soft rows EXACTLY (perfectly entropy- and marginal-matched by identity)
     and randomize only which balanced CAS labeling they pair with (frozen
     seed, 200,000 draws). Gate: observed <= the null's 95th percentile.
     SECONDARY structural bounds (reported): A_hard* <= 9/16 (the exact
     balanced-hard-null ~95th percentile, P(A*<=9/16)=0.94555) and the
     provisional absolute cap A_soft* <= 0.55 (belt-and-suspenders only).
  4. ANTI-UNIFORM (INFORMATIVENESS) GATES, thresholds frozen from the FULL
     WordNet background distribution (not invented after neural results):
       U1 mean target total-variation distance from uniform >= background P25
       U2 mean target normalized entropy <= background P90 (not fog)
       U3 matrix rank == 4 and effective rank (participation ratio) >= 2.0
       U4 every component's share of total target mass >= 5%
  5. RAW + TRANSFORMED PRESERVED: both the raw projected loadings and the
     balanced simplex profiles are recorded, with the per-row L1 change the
     balancing introduced.
  6. SPLIT TYPE TAGS: profile_semantics=SEMANTIC_COMPOSITION (what the numbers
     mean) and authority=RESOURCE_DERIVED_CONTROL (why the profile is admitted).

Frozen definitions (ruling point 12): natural log everywhere; normalized
entropy = H(p)/ln 4; Jensen-Shannon divergence with natural log (max ln 2);
epsilon = 1e-6; permutation procedure = exhaustive over all 24 permutations.

Independence law unchanged: WordNet 3.0 ONLY -- no CAS labels, no CAS class
order, no Qwen anything, no pilot losses or validation results enter the
construction. CAS is read ONLY afterward, to compute the frozen diagnostics.

Fail-closed: any gate failure => S7_DELTA_V2_CONSTRUCTION_FAILED, exit 4, and
the five-arm GPU pilot must NOT launch with this control.

Run:  NLTK_DATA=<dir with corpora/wordnet.zip> python build_s7_delta_v2.py
Writes S7_DELTA_WN1_V2.json + S7_DELTA_V2_BUILD_RECEIPT.json. Does not touch
the preserved v1 artifacts or the hard-partition negative result.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import re
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.optimize import linear_sum_assignment
from sklearn.decomposition import NMF

HERE = Path(__file__).resolve().parent
EPS = 1e-6
N_FACTORS = 4
NMF_INIT = "nndsvda"
NMF_MAX_ITER = 2000
NMF_RANDOM_STATE = 0
STABILITY_SEEDS = (1, 2, 3, 4, 5)          # predetermined random-init fits
STABILITY_MEDIAN_MEAN_JS_MAX = 0.10        # nats; JS max is ln2 ~= 0.693
SHUFFLE_NULL_SEED = 20260831
SHUFFLE_NULL_DRAWS = 200_000
HARD_STRUCTURAL_MAX = 9                    # A_hard* <= 9/16 (exact null P=0.94555)
SOFT_ABS_CAP = 0.55                        # provisional belt-and-suspenders only
BG_TV_PCTL, BG_ENT_PCTL = 25, 90           # anti-uniform background percentiles
EFF_RANK_MIN = 2.0
MIN_COMPONENT_SHARE = 0.05
FEATURE_WEIGHTING = "tfidf_sublinear_l2 (fit on background only)"
BALANCING = "global_factor_scale_equalization (learned on background only)"

CAS_ORDER = ("^2", "^3", "^6", "^8")
VERBS = ["drawn", "pulled", "felt", "captured",
         "withdrew", "repelled", "recoiled", "backed",
         "broke", "lay", "split", "made",
         "brought", "thought", "reminded", "summoned"]
CAS = {v: (i // 4) for i, v in enumerate(VERBS)}

# FROZEN sense-in-context assignment -- identical to v1 (chosen by clause
# MEANING from the construction templates; CAS never consulted).
SENSE = {
    "drawn": "attract.v.01", "pulled": "attract.v.01", "felt": "feel.v.01",
    "captured": "capture.v.02", "withdrew": "withdraw.v.01",
    "repelled": "repel.v.02", "recoiled": "flinch.v.01", "backed": "back.v.02",
    "broke": "break.v.02", "lay": "lie.v.01", "split": "divide.v.01",
    "made": "constitute.v.01", "brought": "bring.v.03", "thought": "think.v.01",
    "reminded": "remind.v.01", "summoned": "summon.v.02",
}

_STOP = set("""a an the of to and or in on at for with by from into as is are was were
be been being that this these those it its their his her they them he she you your our
not no nor so than then thus such via per not one two three""".split())
_WORD = re.compile(r"[a-z][a-z_-]+")


def synset_features(s):
    toks = ["LEX::" + s.lexname()]
    for lm in s.lemmas():
        toks.append("MEM::" + lm.name().lower())
    text = " ".join([s.definition()] + list(s.examples())).lower()
    for w in _WORD.findall(text):
        if w not in _STOP and len(w) > 2:
            toks.append("GLO::" + w)
    seen = set()
    for path in s.hypernym_paths():
        for h in path:
            if h.name() in seen:
                continue
            seen.add(h.name())
            for lm in h.lemmas():
                toks.append("HYP::" + lm.name().lower())
    try:
        for fid in s.frame_ids():
            toks.append("FRM::%02d" % fid)
    except Exception:
        pass
    return toks


def entropy_norm(p):
    p = np.clip(np.asarray(p, float), 1e-12, 1.0)
    return float(-(p * np.log(p)).sum() / math.log(len(p)))


def js_divergence(p, q):
    p = np.clip(np.asarray(p, float), 1e-12, 1)
    q = np.clip(np.asarray(q, float), 1e-12, 1)
    m = 0.5 * (p + q)
    kl = lambda a, b: float((a * np.log(a / b)).sum())
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def to_simplex(rows):
    sm = np.asarray(rows, float) + EPS
    return sm / sm.sum(axis=1, keepdims=True)


def best_perm_stats(bal, cas_idx):
    """(A_hard*, A_soft*, best perms) over ALL 24 column permutations."""
    hard = bal.argmax(axis=1)
    best_h, best_s = -1, -1.0
    ph = ps = None
    for pi in itertools.permutations(range(4)):
        h = sum(1 for i, c in enumerate(cas_idx) if hard[i] == pi[c])
        s = float(np.mean([bal[i, pi[c]] for i, c in enumerate(cas_idx)]))
        if h > best_h:
            best_h, ph = h, pi
        if s > best_s:
            best_s, ps = s, pi
    return best_h, best_s, ph, ps


def main():
    from nltk.corpus import wordnet as wn
    import sklearn

    target_syn = {v: wn.synset(SENSE[v]) for v in VERBS}
    excluded = sorted({s.name() for s in target_syn.values()})   # 15 unique

    # ---- background = ALL verb synsets EXCEPT the target senses ----
    all_syn = list(wn.all_synsets("v"))
    bg_syn = [s for s in all_syn if s.name() not in set(excluded)]
    tg_syn = [target_syn[v] for v in VERBS]                      # 16 rows (dup ok)

    # df-pruned vocabulary from BACKGROUND ONLY
    from collections import Counter
    df = Counter()
    bg_tokens = []
    for s in bg_syn:
        toks = set(synset_features(s))
        bg_tokens.append(toks)
        for t in toks:
            df[t] += 1
    n_bg = len(bg_syn)
    vocab = {t: i for i, t in enumerate(sorted(
        t for t, c in df.items() if 5 <= c <= 0.40 * n_bg))}

    def rows_for(token_sets):
        rows, cols, data = [], [], []
        for r, toks in enumerate(token_sets):
            for t in toks:
                j = vocab.get(t)
                if j is not None:
                    rows.append(r); cols.append(j); data.append(1.0)
        return sp.csr_matrix((data, (rows, cols)),
                             shape=(len(token_sets), len(vocab)))

    X_bg_counts = rows_for(bg_tokens)
    X_tg_counts = rows_for([set(synset_features(s)) for s in tg_syn])

    from sklearn.feature_extraction.text import TfidfTransformer
    tfidf = TfidfTransformer(sublinear_tf=True, norm="l2").fit(X_bg_counts)
    X_bg = tfidf.transform(X_bg_counts)
    X_tg = tfidf.transform(X_tg_counts)

    # ---- primary deterministic factorization on BACKGROUND ONLY ----
    primary = NMF(n_components=N_FACTORS, init=NMF_INIT,
                  random_state=NMF_RANDOM_STATE, max_iter=NMF_MAX_ITER)
    W_bg = primary.fit_transform(X_bg)                 # (n_bg, 4)
    W_tg_raw = primary.transform(X_tg)                 # (16, 4) projection

    # balancing transform learned on BACKGROUND ONLY
    col_bg = W_bg.sum(axis=0)
    factor_scale = col_bg.mean() / np.clip(col_bg, 1e-12, None)
    W_tg_eq = W_tg_raw * factor_scale[None, :]
    W_bg_eq = W_bg * factor_scale[None, :]

    bal = to_simplex(W_tg_eq)                          # (16,4) rows sum to 1
    raw_simplex = to_simplex(W_tg_raw)                 # pre-balancing, preserved
    bg_bal = to_simplex(W_bg_eq)                       # background through the
                                                       # SAME pipeline (percentiles)
    balance_row_L1 = np.abs(bal - raw_simplex).sum(axis=1)

    # ---- FACTOR-STABILITY GATE ----
    stab = []
    for seed in STABILITY_SEEDS:
        alt = NMF(n_components=N_FACTORS, init="random", random_state=seed,
                  max_iter=NMF_MAX_ITER)
        Wb = alt.fit_transform(X_bg)
        # align alt components to primary via Hungarian on cosine(H rows)
        Hp = primary.components_ / np.clip(
            np.linalg.norm(primary.components_, axis=1, keepdims=True), 1e-12, None)
        Ha = alt.components_ / np.clip(
            np.linalg.norm(alt.components_, axis=1, keepdims=True), 1e-12, None)
        cos = Hp @ Ha.T
        ri, ci = linear_sum_assignment(-cos)
        Wt = alt.transform(X_tg)[:, ci]                # aligned target loadings
        colb = Wb.sum(axis=0)[ci]
        scale = colb.mean() / np.clip(colb, 1e-12, None)
        bal_alt = to_simplex(Wt * scale[None, :])
        mean_js = float(np.mean([js_divergence(bal[i], bal_alt[i])
                                 for i in range(16)]))
        stab.append({"seed": seed, "component_alignment": [int(x) for x in ci],
                     "mean_row_js_vs_primary_nats": round(mean_js, 6)})
    js_list = [s["mean_row_js_vs_primary_nats"] for s in stab]
    median_js = float(np.median(js_list))
    stable = median_js <= STABILITY_MEDIAN_MEAN_JS_MAX

    # ---- anti-copy: permutation-invariant + exact conditional shuffle null ----
    cas_idx = [CAS[v] for v in VERBS]
    A_hard, A_soft, perm_h, perm_s = best_perm_stats(bal, cas_idx)

    rng = np.random.default_rng(SHUFFLE_NULL_SEED)
    labels = np.array(cas_idx)
    null_h = np.empty(SHUFFLE_NULL_DRAWS, dtype=np.int16)
    null_s = np.empty(SHUFFLE_NULL_DRAWS, dtype=np.float64)
    hard = bal.argmax(axis=1)
    perms = list(itertools.permutations(range(4)))
    for d in range(SHUFFLE_NULL_DRAWS):
        lab = rng.permutation(labels)                  # balanced 4-4-4-4 kept
        bh, bs = -1, -1.0
        for pi in perms:
            mapped = np.array([pi[c] for c in lab])
            h = int((hard == mapped).sum())
            s = float(bal[np.arange(16), mapped].mean())
            if h > bh:
                bh = h
            if s > bs:
                bs = s
        null_h[d] = bh
        null_s[d] = bs
    h_p95 = float(np.percentile(null_h, 95))
    s_p95 = float(np.percentile(null_s, 95))
    h_pval = float((null_h >= A_hard).mean())
    s_pval = float((null_s >= A_soft).mean())
    anticopy_hard = A_hard <= h_p95                    # PRIMARY (null-calibrated)
    anticopy_soft = A_soft <= s_p95                    # PRIMARY (null-calibrated)
    hard_structural = A_hard <= HARD_STRUCTURAL_MAX    # secondary, reported
    soft_abs = A_soft <= SOFT_ABS_CAP                  # secondary, reported

    # ---- anti-uniform (informativeness), background-frozen thresholds ----
    u = np.full(4, 0.25)
    tv = lambda M: 0.5 * np.abs(M - u[None, :]).sum(axis=1)
    tg_tv = tv(bal); bg_tv = tv(bg_bal)
    tg_ent = np.array([entropy_norm(r) for r in bal])
    bg_ent = np.array([entropy_norm(r) for r in bg_bal])
    tv_thresh = float(np.percentile(bg_tv, BG_TV_PCTL))
    ent_thresh = float(np.percentile(bg_ent, BG_ENT_PCTL))
    U1 = float(tg_tv.mean()) >= tv_thresh
    U2 = float(tg_ent.mean()) <= ent_thresh
    sv = np.linalg.svd(bal, compute_uv=False)
    p_sv = (sv ** 2) / (sv ** 2).sum()
    eff_rank = float(1.0 / (p_sv ** 2).sum())          # participation ratio
    rank = int(np.linalg.matrix_rank(bal, tol=1e-6))
    U3 = (rank == 4) and (eff_rank >= EFF_RANK_MIN)
    comp_share = bal.sum(axis=0) / bal.sum()
    U4 = bool((comp_share >= MIN_COMPONENT_SHARE).all())

    # ---- base integrity gates (unchanged from v1) ----
    C = np.zeros((16, 4))
    for i, v in enumerate(VERBS):
        C[i, CAS[v]] = 1.0
    finite = bool(np.isfinite(bal).all())
    nonneg = bool((bal >= -1e-9).all())
    rows_sum1 = bool(np.allclose(bal.sum(axis=1), 1.0, atol=1e-6))
    equals_S3 = bool(np.allclose(bal, C, atol=1e-6))
    perm_equals_S3 = any(np.allclose(bal[:, list(pi)], C, atol=1e-6)
                         for pi in itertools.permutations(range(4)))

    gates = {
        "rows_finite": finite, "rows_nonnegative": nonneg,
        "rows_sum_to_one": rows_sum1, "equals_S3": equals_S3,
        "permutation_equals_S3": perm_equals_S3,
        "four_dim_interface": bal.shape[1] == 4,
        "no_cas_or_qwen_input": True,
        "exclusion_law_targets_excluded_from_fit": True,
        "stability_median_mean_row_js_nats": round(median_js, 6),
        "stability_pass": stable,
        "anticopy_A_hard_star_of_16": int(A_hard),
        "anticopy_A_hard_null_p95": h_p95,
        "anticopy_A_hard_null_pvalue": round(h_pval, 6),
        "anticopy_hard_pass_primary": anticopy_hard,
        "anticopy_hard_structural_le_9_of_16": hard_structural,
        "anticopy_A_soft_star": round(A_soft, 6),
        "anticopy_A_soft_null_p95": round(s_p95, 6),
        "anticopy_A_soft_null_pvalue": round(s_pval, 6),
        "anticopy_soft_pass_primary": anticopy_soft,
        "anticopy_soft_abs_cap_0p55": soft_abs,
        "antiuniform_U1_mean_tv_ge_bgP25": U1,
        "antiuniform_U2_mean_entropy_le_bgP90": U2,
        "antiuniform_U3_rank4_and_effrank_ge_2": U3,
        "antiuniform_U4_min_component_share_ge_5pct": U4,
    }
    integrity_pass = all([
        finite, nonneg, rows_sum1, not equals_S3, not perm_equals_S3,
        stable, anticopy_hard, anticopy_soft, U1, U2, U3, U4])

    senses = {v: target_syn[v] for v in VERBS}
    profiles = {v: [round(float(x), 8) for x in bal[i]]
                for i, v in enumerate(VERBS)}
    per_verb = {}
    for i, v in enumerate(VERBS):
        p = bal[i]; order = np.argsort(p)[::-1]
        per_verb[v] = {
            "cas_class": CAS_ORDER[CAS[v]], "sense": senses[v].name(),
            "profile": profiles[v],
            "raw_profile_pre_balancing": [round(float(x), 8) for x in raw_simplex[i]],
            "balancing_row_L1_change": round(float(balance_row_L1[i]), 6),
            "dominant_component": int(order[0]),
            "dominance_max": round(float(p[order[0]]), 6),
            "dominance_margin_top1_top2": round(float(p[order[0]] - p[order[1]]), 6),
            "normalized_entropy": round(entropy_norm(p), 6)}

    # frozen post-hoc reporting (never a gate)
    T = C.T @ bal
    joint = T / T.sum()
    pr_ = joint.sum(axis=1, keepdims=True); pc_ = joint.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        mi = float(np.nansum(joint * np.log(joint / (pr_ * pc_ + 1e-12) + 1e-12)))
    class_mean = {c: bal[[i for i, v in enumerate(VERBS) if CAS[v] == c]].mean(axis=0)
                  for c in range(4)}
    js_pairs = [js_divergence(class_mean[a], class_mean[b])
                for a in range(4) for b in range(a + 1, 4)]

    wn_zip = _pin_wordnet()
    table_obj = {
        "table_id": "S7_DELTA_WN1_V2",
        "control_name": "Soft WordNet Semantic-Composition Simplex Control (Delta.1)",
        "non_claim_bearing": True,
        "profile_semantics": "SEMANTIC_COMPOSITION",
        "authority": "RESOURCE_DERIVED_CONTROL",
        "cas_class_order": CAS_ORDER,
        "verb_to_profile": profiles,
        "verb_to_sense": {v: senses[v].name() for v in VERBS},
        "provenance": {
            "wordnet_version": wn.get_version(), **wn_zip,
            "sklearn_version": sklearn.__version__,
            "numpy_version": np.__version__,
            "n_factors": N_FACTORS, "nmf_init": NMF_INIT,
            "nmf_max_iter": NMF_MAX_ITER, "nmf_random_state": NMF_RANDOM_STATE,
            "feature_weighting": FEATURE_WEIGHTING, "balancing": BALANCING,
            "epsilon": EPS, "log_base": "natural (entropy normalized by ln 4)",
            "background_verb_synsets_fit": n_bg,
            "target_senses_excluded_from_fit": excluded,
            "n_features": len(vocab),
            "stability_seeds": list(STABILITY_SEEDS),
            "shuffle_null": {"seed": SHUFFLE_NULL_SEED,
                             "draws": SHUFFLE_NULL_DRAWS}}}
    table_text = json.dumps(table_obj, indent=2, sort_keys=True) + "\n"
    table_sha = hashlib.sha256(table_text.encode("utf-8")).hexdigest()

    receipt = {
        "receipt_id": "S7_DELTA_V2_BUILD_RECEIPT",
        "pilot": "CJT-DEV-P1", "amendment": "CJT-DEV-P1-S7Delta.1",
        "non_claim_bearing": True,
        "verdict": ("S7_DELTA_V2_CONSTRUCTED" if integrity_pass
                    else "S7_DELTA_V2_CONSTRUCTION_FAILED"),
        "s7_delta_v2_table_sha256": table_sha,
        "preserves": {
            "hard_partition_verdict": "S7_PILOT_CONSTRUCTION_FAILED (19d9e843)",
            "v1_soft_control": "S7_DELTA_WN1.json (354f315c) -- superseded for "
                               "the five-arm pilot, kept in history"},
        "integrity_gates": gates,
        "integrity_pass": integrity_pass,
        "stability_fits": stab,
        "per_verb_profile": per_verb,
        "component_target_mass_share": [round(float(x), 6) for x in comp_share],
        "antiuniform_background_thresholds": {
            "bg_tv_P25": round(tv_thresh, 6), "target_mean_tv": round(float(tg_tv.mean()), 6),
            "bg_entropy_P90": round(ent_thresh, 6),
            "target_mean_entropy": round(float(tg_ent.mean()), 6),
            "effective_rank": round(eff_rank, 4), "matrix_rank": rank},
        "soft_cas_alignment_reporting": {
            "note": "REPORTED after freezing; NOT a gate and NOT optimized.",
            "soft_contingency_CAS_rows_x_factor_cols":
                [[round(float(x), 4) for x in r] for r in T],
            "soft_mutual_information_nats": round(mi, 6),
            "mean_pairwise_JS_of_class_means": round(float(np.mean(js_pairs)), 6),
            "best_perm_for_A_hard": list(perm_h), "best_perm_for_A_soft": list(perm_s),
            "mean_normalized_entropy": round(float(tg_ent.mean()), 6),
            "mean_dominance_max": round(float(np.mean([per_verb[v]["dominance_max"]
                                                       for v in VERBS])), 6)},
        "provenance": table_obj["provenance"]}

    (HERE / "S7_DELTA_WN1_V2.json").write_text(table_text, encoding="utf-8")
    (HERE / "S7_DELTA_V2_BUILD_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    print(f"VERDICT: {receipt['verdict']}")
    print(f"  stability median mean-row JS = {median_js:.4f} nats "
          f"(gate <= {STABILITY_MEDIAN_MEAN_JS_MAX}) -> {stable}")
    print(f"  A_hard* = {A_hard}/16  null p95 = {h_p95}  p = {h_pval:.4f} "
          f"-> {anticopy_hard} (structural <=9: {hard_structural})")
    print(f"  A_soft* = {A_soft:.4f}  null p95 = {s_p95:.4f}  p = {s_pval:.4f} "
          f"-> {anticopy_soft} (abs cap 0.55: {soft_abs})")
    print(f"  U1 tv {tg_tv.mean():.4f} >= bgP25 {tv_thresh:.4f} -> {U1}")
    print(f"  U2 ent {tg_ent.mean():.4f} <= bgP90 {ent_thresh:.4f} -> {U2}")
    print(f"  U3 rank={rank} effrank={eff_rank:.3f} -> {U3}   U4 shares "
          f"{[round(float(x),3) for x in comp_share]} -> {U4}")
    print(f"  soft MI = {mi:.4f} nats | mean balancing row-L1 change "
          f"{float(balance_row_L1.mean()):.4f}")
    print(f"  table sha256 {table_sha[:16]}...")
    for v in VERBS:
        pv = per_verb[v]
        print(f"    {v:9} {pv['cas_class']} {pv['sense']:16} "
              f"p={['%.2f' % x for x in pv['profile']]} H={pv['normalized_entropy']:.2f}")
    return 0 if integrity_pass else 4


def _pin_wordnet():
    import glob
    data = os.environ.get("NLTK_DATA", "")
    z = None
    for base in list(filter(None, data.split(os.pathsep))) + [""]:
        cand = Path(base) / "corpora" / "wordnet.zip" if base else None
        if cand and cand.is_file():
            z = cand; break
    if z is None and data:
        hits = glob.glob(str(Path(data) / "**" / "wordnet.zip"), recursive=True)
        z = Path(hits[0]) if hits else None
    if z is None or not z.is_file():
        return {"wordnet_zip_sha256": "UNAVAILABLE", "wordnet_zip_bytes": 0}
    b = z.read_bytes()
    return {"wordnet_zip_sha256": hashlib.sha256(b).hexdigest(),
            "wordnet_zip_bytes": len(b),
            "wordnet_license": "WordNet Release 3.0 License (Princeton University)"}


if __name__ == "__main__":
    raise SystemExit(main())
