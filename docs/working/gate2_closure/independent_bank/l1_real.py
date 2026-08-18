"""L1-REAL — ecological-validity lens test on REAL model outputs.

Same convergent/discriminant test as l1_agreement, but the corpus is real model
answers (real_outputs.jsonl), NOT authored exemplars. No answer key. Each output is
truncated to a substantive opening; 4 blind readers assign the dominant CAS cell;
we measure inter-reader agreement vs a thesaurus null, plus how SPREAD the
disagreements are (1 = all 4 agree ... 4 = all differ).
"""
import json, argparse, itertools
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import pilot_label
from pilot_label import MODELS, build_menu, label_batch
from l1_agreement import build_thesaurus, thesaurus_label, fleiss_kappa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="real_outputs.jsonl")
    ap.add_argument("--cell-file", default="cell_descriptions_colloquial.json")
    ap.add_argument("--truncate", type=int, default=1000)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="l1_real_report.json")
    A = ap.parse_args()

    rows = [json.loads(l) for l in open(A.corpus, encoding="utf-8")]
    items = [{"_id": r["id"], "text": r["output"][:A.truncate]} for r in rows]
    print(f"reading {len(items)} REAL outputs (truncated {A.truncate} chars), {len(MODELS)} readers", flush=True)

    menu = build_menu(A.cell_file)
    vocab = build_thesaurus(A.cell_file)
    jobs = []
    for prov, model in MODELS.items():
        batch = [(it["_id"], it["text"]) for it in items]
        for k in range(0, len(batch), A.batch_size):
            jobs.append((prov, model, menu, batch[k:k + A.batch_size]))

    reader_labels = defaultdict(dict)
    done = 0
    with ThreadPoolExecutor(max_workers=A.workers) as ex:
        futs = {ex.submit(label_batch, p, m, mn, b): p for (p, m, mn, b) in jobs}
        for fut in as_completed(futs):
            try:
                prov, out, finish, nch = fut.result()
            except Exception as e:
                print(f"  batch ERROR {str(e)[:110]}", flush=True); continue
            reader_labels[prov].update(out)
            done += 1
            if done % 5 == 0:
                print(f"  {done}/{len(jobs)} calls done", flush=True)

    readers = list(MODELS.keys())
    thes = {it["_id"]: thesaurus_label(it["text"], vocab) for it in items}
    complete = [it["_id"] for it in items if all(it["_id"] in reader_labels[r] for r in readers)]
    rows_lbl = [[reader_labels[r][i] for r in readers] for i in complete]

    combos = list(itertools.combinations(range(len(readers)), 2))
    pair_ag = []
    for i in complete:
        codes = [reader_labels[r][i] for r in readers]
        pair_ag.append(sum(codes[a] == codes[b] for a, b in combos) / len(combos))
    reader_reader = sum(pair_ag) / len(pair_ag) if pair_ag else 0.0
    kappa = fleiss_kappa(rows_lbl) if rows_lbl else 0.0
    rt = [sum(reader_labels[r][i] == thes[i] for i in complete) / max(1, len(complete)) for r in readers]
    reader_thes = sum(rt) / len(rt)

    # spread: distinct cells among the 4 readers per item (1 = unanimous, 4 = all differ)
    spread = Counter(len(set(reader_labels[r][i] for r in readers)) for i in complete)
    # majority: fraction of items where >=3 of 4 readers share a cell
    def maj(i):
        c = Counter(reader_labels[r][i] for r in readers)
        return max(c.values()) >= 3
    majority_frac = sum(maj(i) for i in complete) / max(1, len(complete))

    rep = {
        "corpus": A.corpus, "n_items": len(items), "n_complete": len(complete), "readers": readers,
        "reader_reader_agreement": round(reader_reader, 4),
        "fleiss_kappa": round(kappa, 4),
        "reader_thesaurus_agreement": round(reader_thes, 4),
        "majority_3of4_share_cell": round(majority_frac, 4),
        "label_spread_per_item": {str(k): v for k, v in sorted(spread.items())},
        "DECISIVE_beyond_thesaurus": bool(reader_reader > reader_thes + 0.05),
    }
    json.dump(rep, open(A.out, "w", encoding="utf-8"), indent=2)
    print("\n=== L1-REAL RESULT (ecological validity — real outputs, no answer key) ===")
    print(f"  n_complete: {len(complete)}/{len(items)}")
    print(f"  reader<->reader agreement : {reader_reader:.3f}  (Fleiss kappa {kappa:.3f})")
    print(f"  reader<->thesaurus        : {reader_thes:.3f}")
    print(f"  >=3 of 4 readers share cell: {majority_frac:.3f}")
    print(f"  label spread (1=unanimous..4=all differ): {dict(sorted(spread.items()))}")
    print(f"  DECISIVE beyond thesaurus : {rep['DECISIVE_beyond_thesaurus']}")
    print(f"  wrote {A.out}")


if __name__ == "__main__":
    main()
