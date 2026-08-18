"""L3 — Discriminant-validity test (matched-surface minimal pairs).

Each pair shares a long stem and differs only in a short tail that flips an OBVIOUS
axis (think vs feel, remember vs analyze, drawn-to vs repelled-by, act vs reflect,
present vs absent). High word-overlap => a bag-of-words (thesaurus null) is pushed to
give BOTH members the SAME label. A structure-reader should SPLIT them.

We do NOT assert a specific target cell per member (that would smuggle in a CAS
judgement). We only claim "these two read differently," which is obvious from the axis.
Metric: reader SPLIT rate (a != b) vs thesaurus SPLIT rate.

Reuses pilot_label reader infra + l1_agreement thesaurus null.
"""
import json, argparse, itertools
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import pilot_label
from pilot_label import MODELS, build_menu, label_batch
from l1_agreement import build_thesaurus, thesaurus_label

# stem shared verbatim by both members; tails flip an obvious axis
PAIRS = [
 ("After the meeting ended, Marcus stayed at his desk replaying the whole discussion, ",
  "tracing step by step whether each argument actually held together.",
  "as a heavy knot of resentment tightened in his stomach.", "think/feel"),
 ("The old letter sat on the table between them, and ",
  "reading it, she suddenly remembered the summer they first met.",
  "she carefully compared its handwriting against the forged note.", "remember/analyze"),
 ("Standing at the trailhead before the climb, Dev looked up at the peak and ",
  "felt himself pulled toward it, aching to be up there.",
  "felt his stomach turn, wanting nothing to do with it.", "drawn/averse"),
 ("When the new policy was announced in the all-hands, Priya ",
  "immediately began mapping out how each clause would interact.",
  "just felt a dull flatness, none of it landing on her at all.", "analyze/absent"),
 ("As the ambulance siren faded down the street, the sound ",
  "instantly brought back the night of his father's accident.",
  "made him tense his shoulders and grip the wheel harder.", "trigger/physical"),
 ("Halfway through writing the eulogy, she stopped and ",
  "asked herself what the words were really for, what any of it meant.",
  "reached for a tissue as her eyes blurred over.", "meaning/feel"),
 ("The chess position on the board in front of him ",
  "he broke down into threats, defenses, and a plan three moves deep.",
  "hit him with a sudden thrill he could feel in his hands.", "analyze/feel"),
 ("Every morning at the same hour for thirty years, the old monk ",
  "sat in silence, sensing a purpose larger than himself.",
  "swept the same three steps and rinsed the same clay bowl.", "purpose/physical"),
 ("When her rival's name came up in conversation, Lena ",
  "found herself leaning in, oddly fascinated by everything about her.",
  "felt her jaw clench and wanted to change the subject.", "attracted/repelled"),
 ("Reading the contract one more time before signing, Omar ",
  "spotted the clause about liability and traced exactly where it led.",
  "felt a vague unease he couldn't put into words.", "analyze/gut"),
 ("The smell of chalk in the empty classroom ",
  "carried him straight back to his first year of teaching.",
  "he noted was faint, dry, and slightly bitter on the air.", "memory/sensory"),
 ("Watching her daughter walk across the graduation stage, Maria ",
  "was flooded with a pride so sharp it caught in her throat.",
  "checked the program to see how many names were still left.", "feel/operational"),
 ("Faced with the same betrayal a third time, he ",
  "finally saw the pattern he'd been repeating for years.",
  "felt the old sick dread rise before he could think.", "insight/visceral"),
 ("Alone in the lab at 2am with the failed experiment, she ",
  "asked what it would even mean if the whole hypothesis were wrong.",
  "methodically re-ran each step to find where the error crept in.", "meaning/analyze"),
]


def label_all(texts, batch_size=12, workers=8):
    """texts: dict id->text. Return {provider: {id: code}}."""
    import random
    menu = build_menu("cell_descriptions_colloquial.json")
    ids = list(texts)
    random.Random(42).shuffle(ids)   # split a/b of each pair across batches so the model can't game the contrast
    jobs = []
    for prov, model in MODELS.items():
        batch = [(i, texts[i]) for i in ids]
        for k in range(0, len(batch), batch_size):
            jobs.append((prov, model, menu, batch[k:k+batch_size]))
    out = defaultdict(dict)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(label_batch, p, m, mn, b): p for (p, m, mn, b) in jobs}
        for fut in as_completed(futs):
            try:
                prov, res, finish, nch = fut.result()
            except Exception as e:
                print(f"  batch ERROR {str(e)[:110]}", flush=True); continue
            out[prov].update(res)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="l3_minimal_pairs_report.json")
    A = ap.parse_args()

    texts = {}
    for pi, (stem, ta, tb, axis) in enumerate(PAIRS):
        texts[2 * pi] = stem + ta        # integer ids: label_batch parses \d+ ids only
        texts[2 * pi + 1] = stem + tb
    print(f"L3: {len(PAIRS)} matched-surface pairs, {len(texts)} texts, {len(MODELS)} readers", flush=True)

    reader = label_all(texts)
    vocab = build_thesaurus("cell_descriptions_colloquial.json")
    thes = {i: thesaurus_label(texts[i], vocab) for i in texts}

    readers = list(MODELS.keys())
    per_pair = []
    reader_splits = defaultdict(int); reader_total = defaultdict(int)
    thes_split = 0
    reader_split_any = 0
    for pi, (stem, ta, tb, axis) in enumerate(PAIRS):
        a, b = 2 * pi, 2 * pi + 1
        rec = {"pair": pi, "axis": axis, "thesaurus_a": thes[a], "thesaurus_b": thes[b],
               "thesaurus_split": thes[a] != thes[b], "readers": {}}
        splitters = 0
        for r in readers:
            ca, cb = reader[r].get(a), reader[r].get(b)
            rec["readers"][r] = [ca, cb]
            if ca is not None and cb is not None:
                reader_total[r] += 1
                if ca != cb:
                    reader_splits[r] += 1; splitters += 1
        rec["reader_split_count"] = splitters
        if thes[a] != thes[b]:
            thes_split += 1
        if splitters >= 3:   # majority of 4 readers split
            reader_split_any += 1
        per_pair.append(rec)

    reader_split_rate = {r: round(reader_splits[r]/reader_total[r], 3) if reader_total[r] else None for r in readers}
    mean_reader_split = round(sum(reader_splits[r] for r in readers)/max(1, sum(reader_total[r] for r in readers)), 3)
    thes_split_rate = round(thes_split/len(PAIRS), 3)
    majority_split_rate = round(reader_split_any/len(PAIRS), 3)

    rep = {
        "n_pairs": len(PAIRS),
        "mean_reader_split_rate": mean_reader_split,
        "per_reader_split_rate": reader_split_rate,
        "majority_readers_split_rate": majority_split_rate,
        "thesaurus_split_rate": thes_split_rate,
        "DECISIVE_readers_split_where_thesaurus_ties": bool(mean_reader_split - thes_split_rate > 0.3),
        "per_pair": per_pair,
    }
    json.dump(rep, open(A.out, "w", encoding="utf-8"), indent=2)
    print("\n=== L3 RESULT (matched-surface minimal pairs) ===")
    print(f"  mean reader split rate (a != b): {mean_reader_split:.3f}")
    print(f"  majority (>=3/4) readers split : {majority_split_rate:.3f}")
    print(f"  thesaurus split rate           : {thes_split_rate:.3f}   (low = thesaurus fooled, as designed)")
    print(f"  per-reader split: {reader_split_rate}")
    print(f"  DECISIVE (readers split where thesaurus ties, gap>0.3): {rep['DECISIVE_readers_split_where_thesaurus_ties']}")
    print(f"  wrote {A.out}")


if __name__ == "__main__":
    main()
