"""wordnet_profile_builder.py -- CJT-DEV-P1.2 STRUCTURALLY CAS-FREE builder of
the soft WordNet lexical-factor simplex control S7_DELTA_WN1_V3.

STRUCTURAL INDEPENDENCE LAW (owner ruling S7Delta.2 point 2): this program
CANNOT import or read any CAS mapping. It holds only the 16 surface verbs and
their frozen construction-context senses, in ALPHABETICAL order; its four
output columns are the anonymous NMF factors WN-F0..WN-F3, in no CAS-related
order; the output table carries NO cas_class_order field. Every CAS-relative
diagnostic lives in the separate comparator (compare_s7_to_cas.py), which runs
only after this table is sealed. "We did not use CAS" is now a software
boundary, not a hardcoded receipt sentence.

Pipeline (identical constants to the v2 builder -- the deterministic
recomputation must REPRODUCE the frozen v2 profiles; any drift fails closed):
  WordNet 3.0 pin FAIL-CLOSED (exact registered SHA-256, ruling repair 1)
  -> background = all verb synsets EXCLUDING the 16 target senses
  -> df-pruned vocabulary + TF-IDF fit on background only
  -> 4-factor NMF (nndsvda, random_state 0) fit on background only
  -> targets projected; balancing scale learned on background only
  -> epsilon-smoothed row normalization to the simplex
Gates owned here (WordNet-only): factor stability (5 predetermined
random-init fits, Hungarian-aligned, median mean-row JS <= 0.10) and the four
background-frozen anti-uniform gates. Also records the FACTOR REPORT (ruling
point 5): per component the top weighted features, top background synsets,
lexname and frame distributions, and mass -- components stay anonymous
WN-F0..WN-F3. Centered affine rank recorded (simplex variation lives in an
affine space of dimension <= 3).

Writes S7_DELTA_WN1_V3.json + S7_DELTA_FACTOR_REPORT.json +
S7_DELTA_V3_BUILDER_RECEIPT.json.
"""
from __future__ import annotations

import hashlib
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
STABILITY_SEEDS = (1, 2, 3, 4, 5)
STABILITY_MEDIAN_MEAN_JS_MAX = 0.10
BG_TV_PCTL, BG_ENT_PCTL = 25, 90
EFF_RANK_MIN = 2.0
MIN_COMPONENT_SHARE = 0.05
REGISTERED_WORDNET_SHA256 = \
    "cbda5ea6eef7f36a97a43d4a75f85e07fccbb4f23657d27b4ccbc93e2646ab59"

# ALPHABETICAL -- no grouping of any kind is encoded here
SENSE = {
    "backed": "back.v.02", "broke": "break.v.02", "brought": "bring.v.03",
    "captured": "capture.v.02", "drawn": "attract.v.01", "felt": "feel.v.01",
    "lay": "lie.v.01", "made": "constitute.v.01", "pulled": "attract.v.01",
    "recoiled": "flinch.v.01", "reminded": "remind.v.01",
    "repelled": "repel.v.02", "split": "divide.v.01",
    "summoned": "summon.v.02", "thought": "think.v.01",
    "withdrew": "withdraw.v.01",
}
VERBS = sorted(SENSE)

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


def pin_wordnet_failclosed():
    """Repair 1: the exact registered WordNet 3.0 archive must be present and
    hash-identical, else the build refuses."""
    import glob
    data = os.environ.get("NLTK_DATA", "")
    z = None
    for base in filter(None, data.split(os.pathsep)):
        cand = Path(base) / "corpora" / "wordnet.zip"
        if cand.is_file():
            z = cand
            break
    if z is None and data:
        hits = glob.glob(str(Path(data) / "**" / "wordnet.zip"), recursive=True)
        z = Path(hits[0]) if hits else None
    if z is None or not z.is_file():
        raise SystemExit("WORDNET_PIN_FAILURE: wordnet.zip not found; the "
                         "frozen source cannot be bound -- refusing to build")
    b = z.read_bytes()
    sha = hashlib.sha256(b).hexdigest()
    if sha != REGISTERED_WORDNET_SHA256:
        raise SystemExit(f"WORDNET_PIN_FAILURE: archive sha {sha} != "
                         f"registered {REGISTERED_WORDNET_SHA256}")
    return {"wordnet_zip_sha256": sha, "wordnet_zip_bytes": len(b),
            "wordnet_license":
                "WordNet Release 3.0 License (Princeton University)"}


def main():
    wn_pin = pin_wordnet_failclosed()
    from nltk.corpus import wordnet as wn
    import sklearn

    target_syn = {v: wn.synset(SENSE[v]) for v in VERBS}
    excluded = sorted({s.name() for s in target_syn.values()})

    all_syn = list(wn.all_synsets("v"))
    bg_syn = [s for s in all_syn if s.name() not in set(excluded)]
    tg_syn = [target_syn[v] for v in VERBS]

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
    inv_vocab = {i: t for t, i in vocab.items()}

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

    primary = NMF(n_components=N_FACTORS, init=NMF_INIT,
                  random_state=NMF_RANDOM_STATE, max_iter=NMF_MAX_ITER)
    W_bg = primary.fit_transform(X_bg)
    W_tg_raw = primary.transform(X_tg)
    col_bg = W_bg.sum(axis=0)
    factor_scale = col_bg.mean() / np.clip(col_bg, 1e-12, None)
    bal = to_simplex(W_tg_raw * factor_scale[None, :])
    raw_simplex = to_simplex(W_tg_raw)
    bg_bal = to_simplex(W_bg * factor_scale[None, :])
    balance_row_L1 = np.abs(bal - raw_simplex).sum(axis=1)

    # ---- stability gate (WordNet-only) ----
    stab = []
    for seed in STABILITY_SEEDS:
        alt = NMF(n_components=N_FACTORS, init="random", random_state=seed,
                  max_iter=NMF_MAX_ITER)
        Wb = alt.fit_transform(X_bg)
        Hp = primary.components_ / np.clip(np.linalg.norm(
            primary.components_, axis=1, keepdims=True), 1e-12, None)
        Ha = alt.components_ / np.clip(np.linalg.norm(
            alt.components_, axis=1, keepdims=True), 1e-12, None)
        ri, ci = linear_sum_assignment(-(Hp @ Ha.T))
        Wt = alt.transform(X_tg)[:, ci]
        colb = Wb.sum(axis=0)[ci]
        bal_alt = to_simplex(Wt * (colb.mean() / np.clip(colb, 1e-12, None)))
        mean_js = float(np.mean([js_divergence(bal[i], bal_alt[i])
                                 for i in range(16)]))
        stab.append({"seed": seed, "mean_row_js_vs_primary_nats":
                     round(mean_js, 6)})
    js_list = [s["mean_row_js_vs_primary_nats"] for s in stab]
    median_js = float(np.median(js_list))
    stable = median_js <= STABILITY_MEDIAN_MEAN_JS_MAX

    # ---- anti-uniform gates (background-frozen, WordNet-only) ----
    u = np.full(4, 0.25)
    tv = lambda M: 0.5 * np.abs(M - u[None, :]).sum(axis=1)
    tg_tv, bg_tv = tv(bal), tv(bg_bal)
    tg_ent = np.array([entropy_norm(r) for r in bal])
    bg_ent = np.array([entropy_norm(r) for r in bg_bal])
    tv_thresh = float(np.percentile(bg_tv, BG_TV_PCTL))
    ent_thresh = float(np.percentile(bg_ent, BG_ENT_PCTL))
    U1 = float(tg_tv.mean()) >= tv_thresh
    U2 = float(tg_ent.mean()) <= ent_thresh
    sv = np.linalg.svd(bal, compute_uv=False)
    p_sv = (sv ** 2) / (sv ** 2).sum()
    eff_rank = float(1.0 / (p_sv ** 2).sum())
    rank = int(np.linalg.matrix_rank(bal, tol=1e-6))
    centered = bal - bal.mean(axis=0, keepdims=True)
    centered_rank = int(np.linalg.matrix_rank(centered, tol=1e-6))
    U3 = (rank == 4) and (eff_rank >= EFF_RANK_MIN)
    comp_share = bal.sum(axis=0) / bal.sum()
    U4 = bool((comp_share >= MIN_COMPONENT_SHARE).all())

    # ---- byte-frozen reuse law: recomputation must equal the v2 profiles ----
    # (read via the FACTOR data only -- the v2 file is WordNet-derived; we
    # compare numbers, not CAS fields)
    v2 = json.loads((HERE / "S7_DELTA_WN1_V2.json").read_text("utf-8"))
    v2p = v2["verb_to_profile"]
    drift = max(abs(float(bal[i][k]) - float(v2p[v][k]))
                for i, v in enumerate(VERBS) for k in range(4))
    if drift > 5e-8:
        raise SystemExit(f"REPRODUCTION_DRIFT: recomputed profiles differ from "
                         f"the frozen v2 profiles by up to {drift}")
    profiles = {v: v2p[v] for v in VERBS}              # byte-for-byte reuse

    # ---- factor report (ruling point 5) ----
    H = primary.components_
    factor_report = {}
    for k in range(4):
        top_feat = np.argsort(H[k])[::-1][:30]
        loadings = W_bg[:, k]
        top_syn = np.argsort(loadings)[::-1][:30]
        lex = Counter(); frm = Counter()
        dom = W_bg.argmax(axis=1) == k
        for i in np.nonzero(dom)[0]:
            lex[bg_syn[i].lexname()] += 1
            try:
                for fid in bg_syn[i].frame_ids():
                    frm["%02d" % fid] += 1
            except Exception:
                pass
        factor_report[f"WN-F{k}"] = {
            "top_weighted_features": [
                {"feature": inv_vocab[j], "weight": round(float(H[k][j]), 6)}
                for j in top_feat],
            "top_background_synsets": [
                {"synset": bg_syn[i].name(),
                 "loading": round(float(loadings[i]), 6)}
                for i in top_syn],
            "lexname_distribution_of_dominant_synsets":
                dict(lex.most_common(15)),
            "frame_distribution_of_dominant_synsets":
                dict(frm.most_common(15)),
            "background_component_mass": round(float(col_bg[k]), 4),
            "dominant_background_synset_count": int(dom.sum())}

    gates = {"wordnet_pin_matched": True,
             "reproduces_frozen_v2_profiles": True,
             "max_reproduction_drift": float(drift),
             "rows_finite": bool(np.isfinite(bal).all()),
             "rows_nonnegative": bool((bal >= -1e-9).all()),
             "rows_sum_to_one": bool(np.allclose(bal.sum(axis=1), 1.0,
                                                 atol=1e-6)),
             "stability_median_mean_row_js_nats": round(median_js, 6),
             "stability_pass": stable,
             "antiuniform_U1_mean_tv_ge_bgP25": U1,
             "antiuniform_U2_mean_entropy_le_bgP90": U2,
             "antiuniform_U3_rank4_and_effrank_ge_2": U3,
             "antiuniform_U4_min_component_share_ge_5pct": U4,
             "matrix_rank": rank, "centered_affine_rank": centered_rank,
             "effective_rank_participation": round(eff_rank, 4)}
    builder_pass = all([gates["rows_finite"], gates["rows_nonnegative"],
                        gates["rows_sum_to_one"], stable, U1, U2, U3, U4])

    per_verb = {}
    for i, v in enumerate(VERBS):
        p = np.array(profiles[v]); order = np.argsort(p)[::-1]
        per_verb[v] = {
            "sense": SENSE[v], "profile": profiles[v],
            "raw_profile_pre_balancing":
                [round(float(x), 8) for x in raw_simplex[i]],
            "balancing_row_L1_change": round(float(balance_row_L1[i]), 6),
            "dominant_component": f"WN-F{int(order[0])}",
            "dominance_max": round(float(p[order[0]]), 6),
            "dominance_margin_top1_top2":
                round(float(p[order[0]] - p[order[1]]), 6),
            "normalized_entropy": round(entropy_norm(p), 6)}

    table_obj = {
        "table_id": "S7_DELTA_WN1_V3",
        "control_name":
            "Soft WordNet Lexical-Factor Simplex Control (Delta.2)",
        "non_claim_bearing": True,
        "profile_semantics": "WORDNET_LEXICAL_FACTOR_COMPOSITION",
        "authority": "RESOURCE_DERIVED_CONTROL",
        "column_law": ("the four columns are the ANONYMOUS WordNet NMF "
                       "factors WN-F0..WN-F3, in no CAS-related order; this "
                       "builder cannot represent the CAS grouping"),
        "sense_policy": ("frozen construction-context senses (audited: "
                         "S7_SENSE_AUDIT.json). S7-H instead uses each "
                         "surface lemma's PRIMARY sense -- their contrast is "
                         "NOT a pure hard-vs-soft ablation"),
        "verb_to_profile": profiles,
        "verb_to_sense": SENSE,
        "provenance": {
            "reused_byte_for_byte_from": "S7_DELTA_WN1_V2.json (7b6f2560)",
            "wordnet_version": wn.get_version(), **wn_pin,
            "sklearn_version": sklearn.__version__,
            "numpy_version": np.__version__,
            "n_factors": N_FACTORS, "nmf_init": NMF_INIT,
            "nmf_max_iter": NMF_MAX_ITER,
            "nmf_random_state": NMF_RANDOM_STATE,
            "background_verb_synsets_fit": n_bg,
            "target_senses_excluded_from_fit": excluded,
            "n_features": len(vocab),
            "stability_seeds": list(STABILITY_SEEDS)}}
    table_text = json.dumps(table_obj, indent=2, sort_keys=True) + "\n"
    table_sha = hashlib.sha256(table_text.encode("utf-8")).hexdigest()

    receipt = {
        "receipt_id": "S7_DELTA_V3_BUILDER_RECEIPT",
        "amendment": "CJT-DEV-P1.2 / S7Delta.2",
        "non_claim_bearing": True,
        "verdict": ("S7_DELTA_V3_BUILT" if builder_pass
                    else "S7_DELTA_V3_BUILDER_FAILED"),
        "structural_independence":
            "this builder holds no CAS mapping; CAS-relative diagnostics "
            "live ONLY in compare_s7_to_cas.py, run after sealing",
        "s7_delta_v3_table_sha256": table_sha,
        "builder_gates": gates,
        "builder_pass": builder_pass,
        "stability_fits": stab,
        "component_target_mass_share":
            [round(float(x), 6) for x in comp_share],
        "antiuniform_background_thresholds": {
            "bg_tv_P25": round(tv_thresh, 6),
            "target_mean_tv": round(float(tg_tv.mean()), 6),
            "bg_entropy_P90": round(ent_thresh, 6),
            "target_mean_entropy": round(float(tg_ent.mean()), 6)},
        "per_verb": per_verb}

    (HERE / "S7_DELTA_WN1_V3.json").write_text(table_text, encoding="utf-8")
    (HERE / "S7_DELTA_FACTOR_REPORT.json").write_text(
        json.dumps({"report_id": "S7_DELTA_FACTOR_REPORT",
                    "non_claim_bearing": True,
                    "naming_law": ("components stay anonymous WN-F0..WN-F3 "
                                   "unless later evidence supports a "
                                   "human-readable semantic name"),
                    "factors": factor_report}, indent=2) + "\n",
        encoding="utf-8")
    (HERE / "S7_DELTA_V3_BUILDER_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    print(f"VERDICT: {receipt['verdict']}")
    print(f"  reproduction drift vs v2: {drift:.2e} (byte-for-byte reuse)")
    print(f"  stability median JS {median_js:.6f} (fits: {js_list}) -> {stable}")
    print(f"  anti-uniform U1={U1} U2={U2} U3={U3} U4={U4}")
    print(f"  rank={rank} centered_affine_rank={centered_rank} "
          f"effrank={eff_rank:.3f}")
    print(f"  table sha256 {table_sha[:16]}...")
    return 0 if builder_pass else 4


if __name__ == "__main__":
    from collections import Counter  # noqa: E402  (used in factor report)
    raise SystemExit(main())
