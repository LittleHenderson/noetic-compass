"""L1 — Convergent-validity test for the CAS output-lens.

Question: do 4 independent blind readers converge on the SAME CAS reading MORE than
a surface word-counter (thesaurus null) does? If reader-vs-reader agreement only
matches reader-vs-thesaurus agreement, the lens is thesaurus-equivalent.

Corpus: balanced subsample of the 640 pilot scenarios (surface-separable -> the
thesaurus is a STRONG adversary here, which makes this a hard test). Each item also
carries an author label (the intended cell) used as a secondary reference.

Reuses pilot_label.build_menu / label_batch / MODELS (the 4 blind readers).
"""
import os, re, json, argparse, random
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import pilot_label
from pilot_label import MODELS, build_menu, label_batch

STOP = set("the a an of and or to in is are be for on with that this it as by from at was were "
           "not no all any some its their he she they i you we his her them who whom which what "
           "when where how why but if then than so just very more most can could would should".split())

def toks(t):
    return [w for w in re.findall(r"[a-z]+", str(t).lower()) if w not in STOP and len(w) > 2]

def build_thesaurus(cell_file):
    d = json.load(open(cell_file, encoding="utf-8"))
    cells = d["cells"]
    vocab = {}
    for code, c in cells.items():
        words = toks(c["label_plain"]) + toks(c["description_plain"])
        for ex in c.get("examples_positive", []):
            words += toks(ex)
        vocab[code] = Counter(words)
    return vocab

def thesaurus_label(text, vocab):
    tw = set(toks(text))
    best, best_score = None, -1
    for code, cv in vocab.items():
        score = sum(cv[w] for w in tw)               # overlap weighted by cell-vocab frequency
        if score > best_score:
            best, best_score = code, score
    return best

def fleiss_kappa(rows):
    """rows: list of label-lists, one per item, each length = n_raters (constant)."""
    cats = sorted({c for r in rows for c in r})
    idx = {c: i for i, c in enumerate(cats)}
    N = len(rows); n = len(rows[0]); k = len(cats)
    M = [[0]*k for _ in range(N)]
    for i, r in enumerate(rows):
        for c in r:
            M[i][idx[c]] += 1
    Pi = [(sum(x*x for x in M[i]) - n) / (n*(n-1)) for i in range(N)]
    Pbar = sum(Pi)/N
    pj = [sum(M[i][j] for i in range(N))/(N*n) for j in range(k)]
    Pe = sum(p*p for p in pj)
    return (Pbar - Pe)/(1 - Pe) if (1-Pe) > 1e-9 else 0.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="pilot_raw.jsonl")
    ap.add_argument("--cell-file", default="cell_descriptions_colloquial.json")
    ap.add_argument("--per-cell", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=12)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="l1_agreement_report.json")
    A = ap.parse_args()

    all_rows = [json.loads(l) for l in open(A.corpus, encoding="utf-8")]
    by_cell = defaultdict(list)
    for r in all_rows:
        by_cell[r["element_label"]].append(r)
    rng = random.Random(7)
    items = []
    for cell in sorted(by_cell):
        pool = by_cell[cell][:]; rng.shuffle(pool)
        items += pool[:A.per_cell]
    for i, it in enumerate(items):
        it["_id"] = i
    print(f"L1 corpus: {len(items)} items ({A.per_cell}/cell x {len(by_cell)} cells)", flush=True)

    menu = build_menu(A.cell_file)
    vocab = build_thesaurus(A.cell_file)

    # every reader labels every item
    jobs = []
    for prov, model in MODELS.items():
        batch = [(it["_id"], it["english"]) for it in items]
        for k in range(0, len(batch), A.batch_size):
            jobs.append((prov, model, menu, batch[k:k+A.batch_size]))
    print(f"{len(jobs)} labelling calls ({len(MODELS)} readers x items/batch)", flush=True)

    reader_labels = defaultdict(dict)   # prov -> {id: code}
    done = 0
    with ThreadPoolExecutor(max_workers=A.workers) as ex:
        futs = {ex.submit(label_batch, p, m, mn, b): p for (p, m, mn, b) in jobs}
        for fut in as_completed(futs):
            p = futs[fut]
            try:
                prov, out, finish, nch = fut.result()
            except Exception as e:
                print(f"  [{p}] batch ERROR {str(e)[:110]}", flush=True); continue
            reader_labels[prov].update(out)
            done += 1
            if done % 8 == 0:
                print(f"  {done}/{len(jobs)} calls done", flush=True)

    readers = list(MODELS.keys())
    thes = {it["_id"]: thesaurus_label(it["english"], vocab) for it in items}
    author = {it["_id"]: it["element_label"] for it in items}

    # complete cases: items all readers labelled
    complete = [it["_id"] for it in items if all(it["_id"] in reader_labels[r] for r in readers)]
    rows = [[reader_labels[r][i] for r in readers] for i in complete]

    # metrics
    import itertools
    pair_ag = []
    for i in complete:
        codes = [reader_labels[r][i] for r in readers]
        agr = [a == b for a, b in itertools.combinations(codes, 2)]
        pair_ag.append(sum(agr)/len(agr))
    reader_reader = sum(pair_ag)/len(pair_ag) if pair_ag else 0.0
    kappa = fleiss_kappa(rows) if rows else 0.0

    rt = []  # reader vs thesaurus (mean over readers)
    for r in readers:
        m = [reader_labels[r][i] == thes[i] for i in complete]
        rt.append(sum(m)/len(m) if m else 0.0)
    reader_thes = sum(rt)/len(rt)

    ra = []  # reader vs author label (accuracy)
    for r in readers:
        m = [reader_labels[r][i] == author[i] for i in complete]
        ra.append(sum(m)/len(m) if m else 0.0)
    reader_author = sum(ra)/len(ra)
    thes_author = sum(thes[i] == author[i] for i in complete)/len(complete)

    # surface-misleading subset: thesaurus disagrees with author label
    mis = [i for i in complete if thes[i] != author[i]]
    if mis:
        mis_pair = []
        for i in mis:
            codes = [reader_labels[r][i] for r in readers]
            agr = [a == b for a, b in itertools.combinations(codes, 2)]
            mis_pair.append(sum(agr)/len(agr))
        mis_reader_reader = sum(mis_pair)/len(mis_pair)
        mis_reader_author = sum(sum(reader_labels[r][i] == author[i] for r in readers)/len(readers) for i in mis)/len(mis)
    else:
        mis_reader_reader = mis_reader_author = None

    rep = {
        "corpus": A.corpus, "n_items": len(items), "n_complete": len(complete), "readers": readers,
        "reader_reader_agreement": round(reader_reader, 4),
        "fleiss_kappa_readers": round(kappa, 4),
        "reader_thesaurus_agreement": round(reader_thes, 4),
        "reader_author_accuracy": round(reader_author, 4),
        "thesaurus_author_accuracy": round(thes_author, 4),
        "per_reader_vs_author": {r: round(ra[k], 4) for k, r in enumerate(readers)},
        "surface_misleading_n": len(mis),
        "surface_misleading_reader_reader_agreement": (round(mis_reader_reader, 4) if mis_reader_reader is not None else None),
        "surface_misleading_reader_author_recovery": (round(mis_reader_author, 4) if mis_reader_author is not None else None),
        "DECISIVE_readers_converge_beyond_thesaurus": bool(reader_reader > reader_thes + 0.05),
    }
    json.dump(rep, open(A.out, "w", encoding="utf-8"), indent=2)
    print("\n=== L1 RESULT ===")
    print(f"  reader<->reader agreement : {reader_reader:.3f}   (Fleiss kappa {kappa:.3f})")
    print(f"  reader<->thesaurus agree  : {reader_thes:.3f}")
    print(f"  reader accuracy vs author : {reader_author:.3f}")
    print(f"  thesaurus accuracy vs auth: {thes_author:.3f}")
    print(f"  surface-misleading items  : {len(mis)}  -> reader<->reader {mis_reader_reader}  reader->author {mis_reader_author}")
    print(f"  DECISIVE (readers converge beyond thesaurus, >+0.05): {rep['DECISIVE_readers_converge_beyond_thesaurus']}")
    print(f"  wrote {A.out}")


if __name__ == "__main__":
    main()
