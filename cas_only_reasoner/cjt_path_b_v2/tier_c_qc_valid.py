"""tier_c_qc_valid.py -- QC_VALID diagnostic pairs (G-C0-6).

Role per owner ruling section 1: structure-consumption / conformance family
ONLY. Excluded from primary win status, headline accuracy, and
best-family-removal. A model can learn the 3-cell mapping from data without
reading R, so the informative readout is the CONTRAST between R-variants,
not QC accuracy alone (registered interpretation law).

Construction: two-clause passages realizing an entity-bridged ordered class
pair in the solver-licensed slots, from the three ASYMMETRIC defined cells
of M: (^3,^2) mind-bridge, (^2,^8) mind-bridge, (^2,^6) idea-bridge. The
symmetric (^6,^6) cell admits no order-flipped twin and is out of QC scope.

Paired counterfactuals: the invalid twin is the SAME two clause strings in
swapped discourse order -- a string permutation, which cancels every
ORDER-INSENSITIVE surface statistic exactly. Gold is by design a function
of clause order, so ORDER-SENSITIVE shallow cues can correlate with it;
the registered surface adversary (qc_surface_ceiling) measures and
persists that ceiling as a disclosure (C0 review fix). The swapped class
order lands on an UNDEFINED cell of M.
Gold = M[cls(first clause), cls(second clause)] under the registered
discourse-order convention. Question: one frozen function-word frame with
zero operation verbs. Candidates: the registered constant pair, shuffled
per record (candidate-order law).

Entities from the train/val bundles only -- the protected bundle is NEVER
touched. Development-only, non-claim-bearing.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "cjt_gate1a_static_neural_v1"
sys.path.insert(0, str(PKG))
from exec.prng import HashPRNG  # noqa: E402

import pathb_core as pc  # noqa: E402
import tier_c_structure as ts  # noqa: E402

QC_SEED_STREAM = "TIERC_QC_VALID_20260901"
QC_QUESTION = "did the opening link carry through to the following link?"
QC_CANDS = ("carried", "stalled")
PAIRS_PER_PATTERN = 100
# (first_cls, second_cls, bridge kind) -- the VALID direction of each
# asymmetric defined cell, with the solver-licensed bridge slots.
PATTERNS = (("^3", "^2", "mind"), ("^2", "^8", "mind"), ("^2", "^6", "idea"))
QC_SPLIT_FAMS = {"train": ("A", "B"), "val": ("C",)}


def _clauses_for(rng, split, first, second):
    """The two op tuples for the VALID direction, bridged per solver slots."""
    m = rng.sample(pc.MINDS[split], 1)[0]
    ideas = rng.sample(pc.IDEAS[split], 3)
    parts = rng.sample(pc.PARTS[split], 3)
    if (first, second) == ("^3", "^2"):
        # REL: ^3(m1,x) selects m1 via x; ^2(iA,m1) consumed by m1
        return [("^3", (m, ideas[0])), ("^2", (ideas[1], m))]
    if (first, second) == ("^2", "^8"):
        # COMP: ^2(x,m1) selects m1; ^8(a,b,m1) for m1
        return [("^2", (ideas[0], m)),
                ("^8", (ideas[1], ideas[2], m))]
    # (^2, ^6) -- INT: ^2(i2,m1) yields i2; ^6(i2,parts)
    return [("^2", (ideas[0], m)),
            ("^6", (ideas[0], tuple(parts)))]


def build_qc_split(split):
    """All QC records for one split (valid item + swapped twin per pair)."""
    r_cas = ts.build_r_cas()
    records = []
    for fam in QC_SPLIT_FAMS[split]:
        for pi, (first, second, bridge) in enumerate(PATTERNS):
            assert ts.m_of(r_cas, first, second) == 1, "pattern not defined"
            assert ts.m_of(r_cas, second, first) == 0, "pattern not asymmetric"
            for i in range(PAIRS_PER_PATTERN):
                rng = HashPRNG(f"QC|{QC_SEED_STREAM}|{split}|{fam}|{pi}|{i}")
                ops = _clauses_for(rng, split, first, second)
                texts = [pc.render_clause(rng, c, a, fam) for c, a in ops]
                pair_id = f"qc{split[0]}{fam}{pi}{i:05d}"
                # PID-TAG SCRAMBLE (C0 review fix): the old 'v'/'x' suffix
                # encoded the gold label with 100% fidelity. The a/b tag
                # is now assigned to the valid/invalid twin per-pair by
                # HashPRNG, so no passage_id character correlates with gold.
                trng = HashPRNG(f"QC_TAG|{QC_SEED_STREAM}|{pair_id}")
                tags = ["a", "b"] if trng.randbelow(2) == 0 else ["b", "a"]
                for tag, order in ((tags[0], (0, 1)), (tags[1], (1, 0))):
                    o_ops = [ops[j] for j in order]
                    o_txt = [texts[j] for j in order]
                    gold = QC_CANDS[0] if ts.m_of(
                        r_cas, o_ops[0][0], o_ops[1][0]) == 1 else QC_CANDS[1]
                    cands = list(QC_CANDS)
                    crng = HashPRNG(f"QC_CAND|{QC_SEED_STREAM}|{pair_id}|"
                                    f"{tag}")
                    crng.shuffle(cands)
                    records.append({
                        "passage_id": pair_id + tag, "pair_id": pair_id,
                        "split": split, "family": fam,
                        "question_type": "QC_VALID",
                        "diagnostic_only": True,
                        "clauses": [{"text": t, "op_index": k}
                                    for k, t in enumerate(o_txt)],
                        "text": " ".join(o_txt),
                        "question": QC_QUESTION, "answer": gold,
                        "candidates": cands,
                        "ops": [[c, list(a) if c != "^6" else
                                 [a[0], list(a[1])]] for c, a in o_ops],
                        "idea_labels": [c for c, _ in o_ops],
                        "bridge_kind": bridge})
    return records


# ---- independent round-trip (verb-based class recovery + frozen-M gold) -----
_VERB_TO_CLS = {v: c for c, vs in pc.VERBS.items() for v in vs}
_VERB_RE = re.compile(
    r"\b(" + "|".join(sorted(_VERB_TO_CLS, key=len, reverse=True)) + r")\b")


def parse_clause_class(text):
    hits = {_VERB_TO_CLS[m] for m in _VERB_RE.findall(text)}
    if len(hits) != 1:
        return None
    return next(iter(hits))


def roundtrip_qc(rec, r_cas):
    """(ok, why): recover both clause classes from surface, recompute gold
    from frozen M, verify against the record."""
    cls = [parse_clause_class(c["text"]) for c in rec["clauses"]]
    if None in cls:
        return False, "clause class not uniquely recoverable"
    if cls != [c for c, _ in
               [(o[0], o[1]) for o in rec["ops"]]]:
        return False, f"surface classes {cls} != ops classes"
    want = QC_CANDS[0] if ts.m_of(r_cas, cls[0], cls[1]) == 1 else QC_CANDS[1]
    if want != rec["answer"]:
        return False, f"frozen-M gold {want} != record answer {rec['answer']}"
    if sorted(rec["candidates"]) != sorted(QC_CANDS):
        return False, "candidate set drift"
    return True, ""


def qc_gates(records, r_cas):
    """G-C0-6: round-trip 100%, pair integrity 100%, balance 50/50,
    R-only oracle 1.000. Raw counts persisted."""
    rt_fail = []
    for rec in records:
        ok, why = roundtrip_qc(rec, r_cas)
        if not ok:
            rt_fail.append({"pid": rec["passage_id"], "why": why})
    pairs = {}
    for rec in records:
        pairs.setdefault(rec["pair_id"], []).append(rec)
    pair_fail = []
    for pid, two in pairs.items():
        if len(two) != 2:
            pair_fail.append({"pair": pid, "why": "not exactly 2 items"})
            continue
        a, b = two
        ta = [c["text"] for c in a["clauses"]]
        tb = [c["text"] for c in b["clauses"]]
        if ta != list(reversed(tb)):
            pair_fail.append({"pair": pid,
                              "why": "twin is not an exact string swap"})
        if {a["answer"], b["answer"]} != set(QC_CANDS):
            pair_fail.append({"pair": pid, "why": "gold not flipped"})
    n_valid = sum(1 for r in records if r["answer"] == QC_CANDS[0])
    oracle_hits = 0
    for rec in records:
        cls = [c for c, _ in [(o[0], o[1]) for o in rec["ops"]]]
        pred = QC_CANDS[0] if ts.m_of(r_cas, cls[0], cls[1]) == 1 \
            else QC_CANDS[1]
        oracle_hits += int(pred == rec["answer"])
    # candidate-order stat (C0 review fix): gold-first fraction ~ 0.5
    gold_first = sum(1 for r in records
                     if r["candidates"][0] == r["answer"]) / len(records)
    # pid-gold decorrelation (C0 review fix): no pid suffix predicts gold
    tag_valid = {}
    for r in records:
        tag = r["passage_id"][-1]
        tag_valid.setdefault(tag, []).append(r["answer"] == QC_CANDS[0])
    tag_gold_rates = {t: sum(v) / len(v) for t, v in tag_valid.items()}
    pid_decorrelated = all(0.4 <= rate <= 0.6
                           for rate in tag_gold_rates.values())
    return {"n_records": len(records), "n_pairs": len(pairs),
            "roundtrip_failures": rt_fail,
            "roundtrip_pass_rate": (len(records) - len(rt_fail))
            / max(1, len(records)),
            "pair_integrity_failures": pair_fail,
            "balance_valid_fraction": n_valid / max(1, len(records)),
            "r_only_oracle_accuracy": oracle_hits / max(1, len(records)),
            "gold_candidate_first_fraction": gold_first,
            "pid_tag_gold_rates": tag_gold_rates,
            "pid_tag_decorrelated": pid_decorrelated,
            "pass": (not rt_fail and not pair_fail
                     and n_valid * 2 == len(records)
                     and oracle_hits == len(records)
                     and 0.4 <= gold_first <= 0.6
                     and pid_decorrelated)}


def qc_surface_ceiling(train_recs, val_recs):
    """Registered surface adversary (C0 review fix + standing char-level
    control law). The twin design cancels ORDER-INSENSITIVE surface
    statistics exactly (twins are string permutations); gold is by design
    a function of clause order, so ORDER-SENSITIVE shallow cues (e.g.
    clause length order) may correlate with it through verb/form length
    differences between classes. This measures that ceiling and persists
    it as a disclosure. Interpretation law: the C1/C2 QC readout is the
    CONTRAST between R-variants at matched surface exposure -- surface
    capacity is identical across arms, so arm differences still isolate
    structure; QC accuracy alone was never the readout."""
    import numpy as np
    from sklearn.feature_extraction.text import HashingVectorizer
    from sklearn.linear_model import LogisticRegression
    vec = HashingVectorizer(analyzer="char", ngram_range=(3, 5),
                            n_features=2 ** 14, alternate_sign=False)
    xt = vec.transform([r["text"] for r in train_recs])
    yt = np.array([1 if r["answer"] == QC_CANDS[0] else 0
                   for r in train_recs])
    clf = LogisticRegression(max_iter=1000, random_state=0)
    clf.fit(xt, yt)
    xv = vec.transform([r["text"] for r in val_recs])
    yv = np.array([1 if r["answer"] == QC_CANDS[0] else 0
                   for r in val_recs])
    char_acc = float((clf.predict(xv) == yv).mean())

    def len_rule(recs):
        hits = 0
        for r in recs:
            t = [c["text"] for c in r["clauses"]]
            pred = 1 if len(t[0]) <= len(t[1]) else 0
            hits += int(pred == (1 if r["answer"] == QC_CANDS[0] else 0))
        return max(hits, len(recs) - hits) / len(recs)
    return {"char_ngram_val_accuracy": char_acc,
            "length_order_rule_val_accuracy_best_side": len_rule(val_recs),
            "adversary": "HashingVectorizer char (3,5) 2^14 + "
                         "LogisticRegression(seed 0), train-fit val-eval",
            "reading": "disclosure only; the QC readout is the contrast "
                       "between R-variants at matched surface exposure"}
