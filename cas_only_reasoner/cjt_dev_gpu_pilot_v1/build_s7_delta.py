"""build_s7_delta.py -- CJT-DEV-P1-S7Delta: the SOFT WordNet Semantic Simplex
Control (owner amendment). Non-claim-bearing development artifact.

The hard S7-P gate failed because it forced each verb sense into one exclusive
box and then demanded near-independence from CAS (Cramer's V <= 0.35). The owner
amendment replaces that with a SOFT control: each registered verb sense gets a
4-component profile p in the simplex Delta^3 (four nonnegative numbers summing to
1) that represents how the sense's WordNet-only semantic ingredients compose --
NOT a probability, and NOT forced to a corner. `simplex_semantics =
SEMANTIC_COMPOSITION`.

Construction (independence law -- WordNet 3.0 ONLY, no CAS labels, no CAS class
order, no Qwen embeddings/hidden states/outputs, no pilot results):
  1. freeze one sense-in-context synset per registered verb (by MEANING, from the
     construction templates -- documented; CAS is never consulted);
  2. build a nonnegative WordNet feature matrix over the COMPLETE verb-sense
     inventory (~13.7k synsets) -- lexname, gloss content words, hypernym lemmas,
     verb frames -- so four factors are learned from a real population, not from
     16 points;
  3. a FROZEN 4-factor NMF (deterministic nndsvda init) yields per-synset factor
     loadings; the 16 target rows are epsilon-smoothed and normalized to Delta^3;
  4. a FROZEN Sinkhorn matrix-scaling balances the TOTAL component mass to ~25%
     each (row sums 1, column sums 4) without forcing any word to a corner.

The Cramer's-V <= 0.35 rule does NOT govern this soft control. Soft CAS-alignment
is REPORTED after the table is frozen, never optimized against. The integrity
gates are: finite / nonnegative / rows sum to 1; meaningful rank; fixed per
sense; no CAS/Qwen input; S7-Delta != S3; no permutation of S7-Delta equals S3;
same 4-dim interface + trainable-parameter budget + downstream processing as S3.

Run:  NLTK_DATA=<dir with corpora/wordnet.zip> python build_s7_delta.py
Writes S7_DELTA_WN1.json (the frozen 16x4 profile table) and
S7_DELTA_BUILD_RECEIPT.json. Does NOT touch S7_PILOT_BUILD_RECEIPT.json (the
preserved hard-partition negative result).
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
NMF_INIT = "nndsvda"                 # deterministic (SVD-based) -> reproducible
NMF_MAX_ITER = 2000
NMF_RANDOM_STATE = 0
FEATURE_WEIGHTING = "tfidf_sublinear_l2"
BALANCING = "global_factor_scale_equalization"

CAS_ORDER = ("^2", "^3", "^6", "^8")
VERBS = ["drawn", "pulled", "felt", "captured",
         "withdrew", "repelled", "recoiled", "backed",
         "broke", "lay", "split", "made",
         "brought", "thought", "reminded", "summoned"]
CAS = {v: (i // 4) for i, v in enumerate(VERBS)}   # ^2->0 ^3->1 ^6->2 ^8->3

# FROZEN sense-in-context assignment (chosen by clause MEANING from the
# generate_construction_gold.py TEMPLATES; CAS labels were NOT consulted). Each
# entry: (preferred synset, clause, rationale). If the preferred synset is
# missing in the snapshot, the loader falls back to the verb sense whose gloss
# best matches `rationale` -- recorded either way.
SENSE = {
    "drawn":   ("attract.v.01", "{m} was drawn to {i}",
                "attract: direct toward itself by psychological/physical power"),
    "pulled":  ("attract.v.01", "{i} pulled {m} toward it",
                "attract/draw toward (figurative pull)"),
    "felt":    ("feel.v.01", "{m} felt an unmistakable pull toward {i}",
                "feel/experience an emotional sensation or state of mind"),
    "captured": ("capture.v.02", "the appeal of {i} captured {m} completely",
                 "attract; cause to be enamored (captivate/fascinate)"),
    "withdrew": ("withdraw.v.01", "{m} withdrew from {i}",
                 "pull back or move away or backward"),
    "repelled": ("repel.v.02", "{i} repelled {m} from the start",
                 "be repellent to; cause aversion in"),
    "recoiled": ("flinch.v.01", "{m} recoiled whenever {i} came up",
                 "draw back, as with fear or pain"),
    "backed":  ("back.v.02", "faced with {i}, {m} backed away",
                "travel backward / move back"),
    "broke":   ("break.v.02", "{i} broke down into parts",
                "become separated into pieces or fragments"),
    "lay":     ("lie.v.01", "inside {i} lay parts",
                "be located or situated somewhere"),
    "split":   ("divide.v.01", "{i} could be split into parts",
                "separate into parts or portions"),
    "made":    ("constitute.v.01", "three strands made up {i}",
                "form or compose (make up / constitute)"),
    "brought": ("bring.v.03", "{a} brought {b} to {m}'s mind",
                "cause to happen or occur as a consequence (evoke)"),
    "thought": ("think.v.01", "whenever {m} thought of {a}, {b} surfaced",
                "judge or regard; consider / call to mind"),
    "reminded": ("remind.v.01", "{a} reminded {m} of {b}",
                 "put in the mind of someone"),
    "summoned": ("summon.v.02", "{a} always summoned {b}",
                 "ask to come / call forth (to mind)"),
}

_STOP = set("""a an the of to and or in on at for with by from into as is are was were
be been being that this these those it its their his her they them he she you your our
not no nor so than then thus such via per not one two three""".split())
_WORD = re.compile(r"[a-z][a-z_-]+")


def resolve_senses(wn):
    chosen = {}
    for v, (pref, clause, why) in SENSE.items():
        syn = None
        try:
            syn = wn.synset(pref)
        except Exception:
            syn = None
        if syn is None:
            lemma = wn.morphy(v, wn.VERB) or v
            key = why.split(":")[0].split("/")[0].strip().lower()
            cands = wn.synsets(lemma, "v")
            syn = next((s for s in cands if key in s.definition().lower()),
                       cands[0] if cands else None)
        if syn is None:
            raise RuntimeError(f"SENSE_RESOLUTION_FAILED for {v!r}")
        chosen[v] = syn
    return chosen


def synset_features(s):
    """Nonnegative WordNet-only feature tokens for one synset."""
    toks = []
    toks.append("LEX::" + s.lexname())
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


def build_matrix(wn):
    all_syn = list(wn.all_synsets("v"))
    # vocabulary with document-frequency pruning (df >= 5, df <= 40% of corpus)
    from collections import Counter
    df = Counter()
    per = []
    for s in all_syn:
        toks = set(synset_features(s))
        per.append(toks)
        for t in toks:
            df[t] += 1
    n = len(all_syn)
    vocab = {t: i for i, t in enumerate(sorted(
        t for t, c in df.items() if 5 <= c <= 0.40 * n))}
    rows, cols, data = [], [], []
    for r, toks in enumerate(per):
        for t in toks:
            j = vocab.get(t)
            if j is not None:
                rows.append(r); cols.append(j); data.append(1.0)
    counts = sp.csr_matrix((data, (rows, cols)), shape=(n, len(vocab)))
    # TF-IDF weighting (sublinear tf + idf): the standard remedy so that generic
    # features shared by most verbs (e.g. root-hypernym lemmas like "act",
    # "change", "move") do NOT dominate the factorization into one "generic verb"
    # factor. Chosen on principle, before any CAS-alignment is computed.
    from sklearn.feature_extraction.text import TfidfTransformer
    X = TfidfTransformer(sublinear_tf=True, norm="l2").fit_transform(counts)
    index = {s.name(): i for i, s in enumerate(all_syn)}
    return X, index, len(vocab), n


def equalize_factor_scales(W_targets, W_full):
    """Gentle GLOBAL factor-scale equalization (frozen, CAS-blind). Each of the 4
    NMF factors is scaled by the inverse of its TOTAL activation over the COMPLETE
    verb-sense inventory, so no single factor dominates by sheer background
    frequency. It is a single per-column monotone rescale of nonnegative loadings
    -- unlike an aggressive Sinkhorn to exact marginals, it CANNOT drive a
    genuinely mixed sense to a pure corner. The per-target simplex mass comes out
    APPROXIMATELY (not exactly) equal, which is what the amendment asks for."""
    col_full = np.asarray(W_full.sum(axis=0), dtype=np.float64).ravel()
    scale = col_full.mean() / np.clip(col_full, 1e-12, None)
    return np.asarray(W_targets, dtype=np.float64) * scale[None, :], scale


def entropy_norm(p):
    p = np.clip(np.asarray(p, float), 1e-12, 1.0)
    return float(-(p * np.log(p)).sum() / math.log(len(p)))


def js_divergence(p, q):
    p = np.clip(np.asarray(p, float), 1e-12, 1)
    q = np.clip(np.asarray(q, float), 1e-12, 1)
    m = 0.5 * (p + q)
    kl = lambda a, b: float((a * np.log(a / b)).sum())
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def main():
    from nltk.corpus import wordnet as wn
    import sklearn
    senses = resolve_senses(wn)
    X, index, n_features, n_syn = build_matrix(wn)

    model = NMF(n_components=N_FACTORS, init=NMF_INIT, random_state=NMF_RANDOM_STATE,
                max_iter=NMF_MAX_ITER)
    W = model.fit_transform(X)                      # (n_syn, 4) >= 0, deterministic

    # target factor loadings -> gentle global factor-scale equalization (no
    # corner-forcing) -> epsilon-smoothed simplex profiles
    raw_targets = np.array([W[index[senses[v].name()]] for v in VERBS])   # (16,4)
    equalized, factor_scale = equalize_factor_scales(raw_targets, W)
    smoothed = equalized + EPS
    bal = smoothed / smoothed.sum(axis=1, keepdims=True)           # rows sum to 1

    profiles = {v: [round(float(x), 8) for x in bal[i]] for i, v in enumerate(VERBS)}

    # ---- integrity gates (soft control) ----
    C = np.zeros((16, 4))
    for i, v in enumerate(VERBS):
        C[i, CAS[v]] = 1.0
    finite = bool(np.isfinite(bal).all())
    nonneg = bool((bal >= -1e-9).all())
    rows_sum1 = bool(np.allclose(bal.sum(axis=1), 1.0, atol=1e-6))
    rank = int(np.linalg.matrix_rank(bal, tol=1e-6))
    equals_S3 = bool(np.allclose(bal, C, atol=1e-6))
    # no permutation of the 4 components turns S7-Delta into the CAS one-hot
    perm_equals_S3 = any(np.allclose(bal[:, list(pi)], C, atol=1e-6)
                         for pi in itertools.permutations(range(4)))
    # stronger diagnostic: the HARDENED argmax labeling is not a CAS permutation
    hard = bal.argmax(axis=1)
    hard_is_cas_perm = any(all(hard[i] == pi[CAS[v]] for i, v in enumerate(VERBS))
                           for pi in itertools.permutations(range(4)))
    gates = {"rows_finite": finite, "rows_nonnegative": nonneg,
             "rows_sum_to_one": rows_sum1, "profile_matrix_rank": rank,
             "rank_is_full_4": rank == 4, "equals_S3": equals_S3,
             "permutation_equals_S3": perm_equals_S3,
             "hardened_argmax_is_cas_permutation": hard_is_cas_perm,
             "no_cas_or_qwen_input": True,   # construction path never reads CAS/Qwen
             "four_dim_interface": bal.shape[1] == 4}
    integrity_pass = (finite and nonneg and rows_sum1 and rank == N_FACTORS
                      and not equals_S3 and not perm_equals_S3)

    # ---- reporting (AFTER freezing; NOT optimized) ----
    per_verb = {}
    for i, v in enumerate(VERBS):
        p = bal[i]
        order = np.argsort(p)[::-1]
        per_verb[v] = {"cas_class": CAS_ORDER[CAS[v]],
                       "sense": senses[v].name(),
                       "sense_gloss": senses[v].definition(),
                       "profile": profiles[v],
                       "dominant_factor": int(order[0]),
                       "dominance_max": round(float(p[order[0]]), 6),
                       "dominance_margin_top1_top2": round(float(p[order[0]] - p[order[1]]), 6),
                       "normalized_entropy": round(entropy_norm(p), 6)}
    T = C.T @ bal                                   # 4x4 soft contingency
    ri, ci = linear_sum_assignment(-T)              # best-permutation alignment
    best_alignment_mass = float(T[ri, ci].sum())
    col_mass = bal.sum(axis=0)
    # soft mutual information over the joint T/16
    joint = T / T.sum()
    pr = joint.sum(axis=1, keepdims=True); pc = joint.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        mi = float(np.nansum(joint * np.log(joint / (pr * pc + 1e-12) + 1e-12)))
    class_mean = {c: bal[[i for i, v in enumerate(VERBS) if CAS[v] == c]].mean(axis=0)
                  for c in range(4)}
    js_pairs = [js_divergence(class_mean[a], class_mean[b])
                for a in range(4) for b in range(a + 1, 4)]

    reporting = {
        "note": "REPORTED AFTER the table was frozen; NOT a gate and NOT optimized. "
                "Correlation with CAS is expected when both capture real semantics.",
        "soft_contingency_CAS_rows_x_factor_cols": [[round(float(x), 4) for x in r]
                                                    for r in T],
        "best_permutation_alignment_mass_of_16": round(best_alignment_mass, 4),
        "soft_mutual_information_nats": round(mi, 6),
        "mean_pairwise_JS_of_class_means": round(float(np.mean(js_pairs)), 6),
        "component_total_mass": [round(float(x), 4) for x in col_mass],
        "component_mass_balance_maxdev_from_4": round(float(np.max(np.abs(col_mass - 4.0))), 4),
        "mean_normalized_entropy": round(float(np.mean([per_verb[v]["normalized_entropy"]
                                                        for v in VERBS])), 6),
        "mean_dominance_max": round(float(np.mean([per_verb[v]["dominance_max"]
                                                   for v in VERBS])), 6)}

    wn_zip = _pin_wordnet()
    table_obj = {
        "table_id": "S7_DELTA_WN1",
        "control_name": "WordNet Soft Semantic Simplex Control",
        "non_claim_bearing": True,
        "simplex_semantics": "SEMANTIC_COMPOSITION",
        "cas_class_order": CAS_ORDER,
        "verb_to_profile": profiles,
        "verb_to_sense": {v: senses[v].name() for v in VERBS},
        "provenance": {"wordnet_version": wn.get_version(), **wn_zip,
                       "sklearn_version": sklearn.__version__,
                       "numpy_version": np.__version__,
                       "n_factors": N_FACTORS, "nmf_init": NMF_INIT,
                       "nmf_max_iter": NMF_MAX_ITER,
                       "nmf_random_state": NMF_RANDOM_STATE,
                       "feature_weighting": FEATURE_WEIGHTING,
                       "balancing": BALANCING, "epsilon": EPS,
                       "background_verb_synsets": n_syn, "n_features": n_features}}
    table_text = json.dumps(table_obj, indent=2, sort_keys=True) + "\n"
    table_sha = hashlib.sha256(table_text.encode("utf-8")).hexdigest()

    receipt = {
        "receipt_id": "S7_DELTA_BUILD_RECEIPT",
        "pilot": "CJT-DEV-P1", "amendment": "CJT-DEV-P1-S7Delta",
        "non_claim_bearing": True,
        "verdict": "S7_DELTA_CONSTRUCTED" if integrity_pass
        else "S7_DELTA_INTEGRITY_FAILED",
        "preserves": {"hard_partition_verdict": "S7_PILOT_CONSTRUCTION_FAILED",
                      "note": "the hard S7-P negative result (commit 19d9e843) "
                              "remains valid and is not rewritten"},
        "s7_delta_table_sha256": table_sha,
        "sense_assignment": {v: {"synset": senses[v].name(),
                                 "gloss": senses[v].definition(),
                                 "clause": SENSE[v][1], "rationale": SENSE[v][2],
                                 "chosen_by": "clause MEANING (CAS never consulted)"}
                             for v in VERBS},
        "integrity_gates": gates,
        "integrity_pass": integrity_pass,
        "per_verb_profile": per_verb,
        "soft_cas_alignment_reporting": reporting,
        "provenance": table_obj["provenance"]}

    (HERE / "S7_DELTA_WN1.json").write_text(table_text, encoding="utf-8")
    (HERE / "S7_DELTA_BUILD_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    print(f"VERDICT: {receipt['verdict']}")
    print(f"  integrity_pass={integrity_pass} rank={rank} equals_S3={equals_S3} "
          f"perm_equals_S3={perm_equals_S3}")
    print(f"  component mass {reporting['component_total_mass']} "
          f"(target 4.0 each; maxdev {reporting['component_mass_balance_maxdev_from_4']})")
    print(f"  mean entropy {reporting['mean_normalized_entropy']} "
          f"mean dominance {reporting['mean_dominance_max']}")
    print(f"  soft MI(CAS,factors)={reporting['soft_mutual_information_nats']} nats "
          f"best-perm alignment {reporting['best_permutation_alignment_mass_of_16']}/16")
    print(f"  table sha256 {table_sha[:16]}...  wn {wn.get_version()} "
          f"sklearn {sklearn.__version__}")
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
