#!/usr/bin/env python
"""Matched-taxonomy comparator on the dual_labeled 40E GPT-NeoX-20B activations.

Specificity question (honest framing):
  On the SAME hidden states, is the CAS 40-Element partition more linearly
  recoverable than a *matched alternative* 40-way taxonomy, a *found* lexical
  taxonomy, and a *scrambled* null?

Label sets probed on identical activations + identical fixed 800/200 split:
  - cas_element            : the real CAS target (labels_element, 40 classes)
  - matched_control_tf     : control_semantic topic_40 x frame_40 (<=40 classes)
  - lexical_kmeans40       : TF-IDF -> KMeans(40) on the prompt text (found taxonomy)
  - scrambled_cas          : permuted CAS labels (pure null floor, ~chance)

For each label set:
  - hidden probe: per-layer StandardScaler + LogisticRegression(C=0.1,
    class_weight='balanced', solver='lbfgs'); each set gets its OWN best layer.
  - text baseline: CountVectorizer(1-2gram) + LogisticRegression on prompts.
  - lift = hidden_best_acc - text_acc.

CAVEAT (must accompany any result): this tests specificity on the dual_labeled
pilot fixture, NOT on the lost v1 fixture that produced the 95.625% headline.
The dual_labeled CAS text baseline is non-trivial (~32%), so part of the CAS
signal is text-visible here. Read CAS-vs-control deltas, not absolute CAS acc.
"""
import argparse, json, time, warnings
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import accuracy_score, f1_score
warnings.filterwarnings("ignore")


def load(npz_path, fixture_path):
    npz = np.load(npz_path, allow_pickle=True)
    feats = npz["features"]            # (N, L, H)
    layers = npz["layers"]            # (L,)
    sids = [str(x) for x in npz["scenario_ids"]]
    prompts = [str(x) for x in npz["prompts"]]
    cas = [str(x) for x in npz["labels_element"]]

    fx = json.load(open(fixture_path, encoding="utf-8"))
    recs = fx["records"] if isinstance(fx, dict) and "records" in fx else fx
    by_id = {}
    for r in recs:
        rid = str(r.get("id") or r.get("sample_id"))
        by_id[rid] = r
    splits, control, control_c = [], [], []
    for sid in sids:
        r = by_id[sid]
        splits.append(r.get("split"))
        cs = r.get("control_semantic") or {}
        control.append(f"{cs.get('topic_40','?')}|{cs.get('frame_40','?')}")        # Control B (NC40)
        control_c.append(f"{cs.get('topic_7','?')}|{cs.get('function_4','?')}")      # Control C (NC28)
    return (feats, layers, np.array(sids), prompts, np.array(cas),
            np.array(splits), np.array(control), np.array(control_c))


def encode(y):
    classes = sorted(set(y))
    idx = {c: i for i, c in enumerate(classes)}
    return np.array([idx[v] for v in y]), classes


def hidden_sweep(feats, layers, y, tr, te, tag):
    yenc, classes = encode(y)
    best = {"acc": -1.0}
    for li in range(feats.shape[1]):
        Xtr = feats[tr, li, :]
        Xte = feats[te, li, :]
        sc = StandardScaler().fit(Xtr)
        Xtr, Xte = sc.transform(Xtr), sc.transform(Xte)
        clf = LogisticRegression(C=0.1, class_weight="balanced",
                                 solver="lbfgs", max_iter=2000, multi_class="multinomial")
        clf.fit(Xtr, yenc[tr])
        pred = clf.predict(Xte)
        acc = accuracy_score(yenc[te], pred)
        if acc > best["acc"]:
            best = {"acc": acc,
                    "macro_f1": f1_score(yenc[te], pred, average="macro"),
                    "layer": int(layers[li]), "layer_idx": li}
    best["n_classes"] = len(classes)
    best["chance"] = 1.0 / len(classes)
    print(f"  [{tag}] hidden best: layer={best['layer']} "
          f"acc={best['acc']:.4f} macroF1={best['macro_f1']:.4f} "
          f"({best['n_classes']} cls, chance={best['chance']:.4f})")
    return best


def text_baseline(prompts, y, tr, te, tag):
    yenc, classes = encode(y)
    P = np.array(prompts, dtype=object)
    vec = CountVectorizer(ngram_range=(1, 2), max_features=2 ** 14)
    Xtr = vec.fit_transform(P[tr]); Xte = vec.transform(P[te])
    clf = LogisticRegression(C=1.0, class_weight="balanced",
                             solver="lbfgs", max_iter=2000, multi_class="multinomial")
    clf.fit(Xtr, yenc[tr])
    pred = clf.predict(Xte)
    acc = accuracy_score(yenc[te], pred)
    f1 = f1_score(yenc[te], pred, average="macro")
    print(f"  [{tag}] text baseline: acc={acc:.4f} macroF1={f1:.4f}")
    return {"acc": acc, "macro_f1": f1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    ap.add_argument("--fixture", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--control-c-view", default=None,
                    help="optional control_c_nc28_balanced_view_*.json; adds a rows-matched "
                         "Control C (NC28) arm on its balanced sample_id subset")
    ap.add_argument("--seed", type=int, default=20260530)
    args = ap.parse_args()

    t0 = time.time()
    feats, layers, sids, prompts, cas, splits, control, control_c = load(args.npz, args.fixture)
    N = feats.shape[0]
    print(f"Loaded features {feats.shape}, {N} items, {feats.shape[1]} layers")

    tr = np.where(splits == "train")[0]
    te = np.where(splits == "test")[0]
    print(f"Fixed split: {len(tr)} train / {len(te)} test")

    rng = np.random.RandomState(args.seed)
    scrambled = cas.copy()
    perm = rng.permutation(len(scrambled))
    scrambled = scrambled[perm]

    # lexical found taxonomy: TF-IDF -> KMeans(40), fit on train prompts only
    P = np.array(prompts, dtype=object)
    tfidf = TfidfVectorizer(ngram_range=(1, 2), max_features=2 ** 14)
    Xtr_tf = tfidf.fit_transform(P[tr])
    km = KMeans(n_clusters=40, random_state=args.seed, n_init=10).fit(Xtr_tf)
    lex = np.empty(N, dtype=int)
    lex[tr] = km.labels_
    lex[te] = km.predict(tfidf.transform(P[te]))
    lex = lex.astype(str)

    label_sets = {
        "cas_element": cas,
        "matched_control_tf": control,
        "lexical_kmeans40": lex,
        "scrambled_cas": scrambled,
    }

    results = {}
    for tag, y in label_sets.items():
        print(f"\n=== {tag} ===")
        h = hidden_sweep(feats, layers, y, tr, te, tag)
        if tag in ("cas_element", "matched_control_tf"):
            t = text_baseline(prompts, y, tr, te, tag)
        else:
            t = {"acc": None, "macro_f1": None}
        lift = (h["acc"] - t["acc"]) if t["acc"] is not None else None
        results[tag] = {"hidden": h, "text": t, "hidden_minus_text": lift}
        if lift is not None:
            print(f"  [{tag}] lift hidden-text = {lift:+.4f}")

    # Rows-matched Control C (NC28) arm on the balanced view ------------------
    results_view = None
    if args.control_c_view:
        view = json.load(open(args.control_c_view, encoding="utf-8"))
        vids = set()
        for split_ids in view["view_sample_ids"].values():
            vids.update(split_ids)
        sid_in_view = np.array([s in vids for s in sids])
        tr_c = tr[sid_in_view[tr]]
        te_c = te[sid_in_view[te]]
        print(f"\n=== rows-matched view (Control C) : {len(tr_c)} train / {len(te_c)} test "
              f"(NC28 balanced subset) ===")
        view_sets = {
            "cas_element": cas,
            "matched_control_nc40": control,
            "matched_control_nc28": control_c,
        }
        results_view = {}
        for tag, y in view_sets.items():
            h = hidden_sweep(feats, layers, y, tr_c, te_c, f"view:{tag}")
            t = text_baseline(prompts, y, tr_c, te_c, f"view:{tag}")
            lift = h["acc"] - t["acc"]
            results_view[tag] = {"hidden": h, "text": t, "hidden_minus_text": lift}
            print(f"  [view:{tag}] lift hidden-text = {lift:+.4f}")

    summary = {
        "npz": args.npz, "fixture": args.fixture, "seed": args.seed,
        "n_items": int(N), "n_layers": int(feats.shape[1]),
        "split": {"train": int(len(tr)), "test": int(len(te))},
        "probe": "StandardScaler + LogisticRegression(C=0.1, balanced, lbfgs)",
        "results": results,
        "control_c_view": args.control_c_view,
        "results_view_nc28_matched": results_view,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    json.dump(summary, open(args.out, "w"), indent=2)
    print(f"\nWrote {args.out} in {summary['elapsed_sec']}s")

    print("\n================ SPECIFICITY READOUT ================")
    ce = results["cas_element"]["hidden"]["acc"]
    mc = results["matched_control_tf"]["hidden"]["acc"]
    lx = results["lexical_kmeans40"]["hidden"]["acc"]
    sc = results["scrambled_cas"]["hidden"]["acc"]
    print(f"CAS element        hidden best acc = {ce:.4f}")
    print(f"Matched control    hidden best acc = {mc:.4f}  (CAS - control = {ce-mc:+.4f})")
    print(f"Lexical kmeans40   hidden best acc = {lx:.4f}  (CAS - lexical = {ce-lx:+.4f})")
    print(f"Scrambled (null)   hidden best acc = {sc:.4f}  (floor; expect ~chance)")


if __name__ == "__main__":
    main()
