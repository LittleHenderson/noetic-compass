"""Condition-3 Surface Gate (local CPU, $0).

Two opposite things must be true at once, and this script checks both:

  A) The CAS label (40-element domain x noetic) must stay NEAR CHANCE from prompt
     text alone. The noetic-dynamic + register-manner phrasing is train/test
     disjoint, so a bag-of-words classifier trained on train cannot transfer the
     CAS-label surface to test. Target: <= Condition-2's ~6.9%, ideally lower.

  B) The ORTHOGONAL scaffold (topic_40 / frame_40) SHOULD be highly recoverable
     from the same text. That is the point: it is a real, coherent, surface-present
     non-CAS taxonomy -- the Control B opponent. High topic/frame text accuracy is
     EVIDENCE the ordinary content is genuinely there (Fixture-Eligibility), while
     the orthogonal assignment keeps it useless for the CAS label (so A holds).

Text lane matches run_matched_taxonomy_control.py / the Condition-2 gate:
  CountVectorizer(1-2gram, max_features=2**14) + LogisticRegression(C=1.0,
  class_weight='balanced', lbfgs), train -> test.
"""
import argparse, json
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

_HERE = Path(__file__).resolve().parent
_FIX = _HERE / "mtc_condition3_topical_scenarios_20260531.jsonl"


def _label(r, axis):
    cs = r["control_semantic"]
    return {
        "cas_full": r["element_label"],
        "cas_domain": r["element_domain"],
        "cas_noetic": str(r["element_noetic_tks"]),
        "topic_40": cs["topic_40"],
        "frame_40": cs["frame_40"],
        "nc40_cell": f"{cs['topic_40']}|{cs['frame_40']}",
    }[axis]


def run(rows, axis, text_key="english"):
    tr = [r for r in rows if r["split"] == "train"]
    te = [r for r in rows if r["split"] == "test"]
    classes = sorted({_label(r, axis) for r in rows})
    idx = {c: i for i, c in enumerate(classes)}
    ytr = np.array([idx[_label(r, axis)] for r in tr])
    yte = np.array([idx[_label(r, axis)] for r in te])
    vec = CountVectorizer(ngram_range=(1, 2), max_features=2 ** 14)
    Xtr = vec.fit_transform([r[text_key] for r in tr])
    Xte = vec.transform([r[text_key] for r in te])
    clf = LogisticRegression(C=1.0, class_weight="balanced", solver="lbfgs", max_iter=2000)
    clf.fit(Xtr, ytr)
    pred = clf.predict(Xte)
    return accuracy_score(yte, pred), f1_score(yte, pred, average="macro"), len(classes)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", default=str(_FIX))
    args = ap.parse_args(argv)
    rows = [json.loads(l) for l in open(args.fixture, encoding="utf-8")]
    print(f"fixture: {Path(args.fixture).name}")
    print(f"rows={len(rows)} splits={dict(sorted(Counter(r['split'] for r in rows).items()))}")
    print()
    print(f"{'axis':12s} {'n_cls':>5s} {'chance':>8s} {'text_acc':>9s} {'macroF1':>8s}  role")
    plan = [
        ("cas_full", "CAS LABEL -> must be NEAR CHANCE"),
        ("cas_domain", "CAS domain -> near chance"),
        ("cas_noetic", "CAS noetic -> near chance"),
        ("topic_40", "OPPONENT -> should be HIGH (real content)"),
        ("frame_40", "OPPONENT -> should be HIGH (real content)"),
        ("nc40_cell", "OPPONENT joint -> should be HIGH"),
    ]
    res = {}
    for axis, role in plan:
        acc, f1, nc = run(rows, axis)
        chance = 1.0 / nc
        res[axis] = {"acc": round(acc, 4), "macro_f1": round(f1, 4), "n_cls": nc,
                     "chance": round(chance, 4), "acc_over_chance": round(acc / chance, 2)}
        print(f"{axis:12s} {nc:5d} {chance:8.4f} {acc:9.4f} {f1:8.4f}  {role}")
    print()
    cas = res["cas_full"]
    verdict = "PASS" if cas["acc"] <= 0.069 else ("NEAR-PASS" if cas["acc"] <= 0.10 else "FAIL")
    print(f"CAS-label text leakage = {cas['acc']:.4f} ({cas['acc_over_chance']}x chance). "
          f"Condition-2 ref = 0.069. Surface Gate: {verdict}")
    print(f"Opponent present: topic_40 text acc={res['topic_40']['acc']:.4f} "
          f"({res['topic_40']['acc_over_chance']}x chance), "
          f"frame_40={res['frame_40']['acc']:.4f} ({res['frame_40']['acc_over_chance']}x).")
    out = _HERE / "surface_gate_condition3_result.json"
    out.write_text(json.dumps({"fixture": Path(args.fixture).name, "results": res,
                               "cas_label_verdict": verdict}, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"wrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
