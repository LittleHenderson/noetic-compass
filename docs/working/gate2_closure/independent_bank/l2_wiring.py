"""Stage 2 (WIRING) — change WHAT we measure.

Not "which parts are present" (Jaccard on a set), but:
  (1) the MAIN part (one dominant) -> directly comparable to the 0.53 single-cell number,
  (2) the WIRING -- the ordered signal path through the parts -> agreement on the
      directed edges (how parts connect), which is where real circuit structure lives.

12 parts (the ones that actually got used in the 20-part run). 4 blind readers each give
an ordered signal path + the single main part per real output. We measure main-part
agreement (raw + Fleiss kappa) and edge-set Jaccard vs a shuffled null.
"""
import json, re, argparse, itertools, random
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import providers
from pilot_label import call_with_retry, MODELS
from l1_agreement import fleiss_kappa
from openai import OpenAI

COMPONENTS = [
    ("SENSE",     "Taking it in",      "registering the situation or question before responding."),
    ("MEM",       "Drawing on memory", "pulling in stored knowledge, facts, or experience."),
    ("UNPACK",    "Breaking it down",  "taking the problem apart into pieces to examine."),
    ("AMP",       "The engine",        "the main reasoning that turns the question into an answer."),
    ("WEIGH",     "Weighing options",  "holding choices side by side to compare them."),
    ("IF",        "The switch",        "conditionals -- 'if X then Y', 'it depends'."),
    ("RS",        "The brakes",        "holding back, caveats, limits, or declining."),
    ("DR",        "The push",          "the goal or motivation driving the answer."),
    ("TRANSLATE", "Making it usable",  "turning an abstract idea into concrete steps."),
    ("ORDER",     "First things first","sequencing or prioritizing steps."),
    ("GND",       "The baseline",      "the reference it judges against -- 'compared to what?'."),
    ("CHECK",     "The danger point",  "the spot where a quiet mistake could slip through."),
]
CODES = [c for c, _, _ in COMPONENTS]
CODE_RE = re.compile(r'\b(' + '|'.join(sorted(CODES, key=len, reverse=True)) + r')\b')


def build_menu():
    L = ["Below are twelve kinds of PARTS an answer can move through.", "", "The parts:"]
    for code, name, desc in COMPONENTS:
        L.append(f"{code} = {name}: {desc}")
    return "\n".join(L)


def read_batch(provider, model, menu, batch):
    bu, key, _ = providers.resolve(provider, model)
    client = OpenAI(api_key=key, base_url=bu)
    lines = [f'--- ANSWER {i} ---\n{s}' for i, s in batch]
    prompt = (menu + "\n\nAnswers to read:\n" + "\n\n".join(lines) +
              "\n\nFor EACH answer, trace its MAIN SIGNAL PATH: the ordered sequence of parts the "
              "answer moves through, from what it takes in to what it produces (3 to 6 parts). "
              "Also name the ONE part that does the most work (the main part). "
              'Return ONLY a JSON array: [{"id": <number>, "path": ["CODE", ...], "main": "CODE"}]. '
              "Use only the codes above.")
    r = call_with_retry(client, provider, model=model, max_tokens=16000, temperature=0.0,
                        messages=[{"role": "user", "content": prompt}])
    msg = r.choices[0].message
    txt = getattr(msg, "content", None) or ""
    if not txt:
        txt = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or ""
    out = {}
    for block in re.findall(r'\{[^{}]*\}', txt, re.S):
        idm = re.search(r'"id"\s*:\s*(\d+)', block)
        if not idm:
            continue
        oid = int(idm.group(1))
        pm = re.search(r'"path"\s*:\s*\[([^\]]*)\]', block, re.S)
        path = CODE_RE.findall(pm.group(1)) if pm else []
        mm = re.search(r'"main"\s*:\s*"?(' + '|'.join(CODES) + r')\b', block)
        main = mm.group(1) if mm else (path[0] if path else None)
        out[oid] = {"path": path, "main": main}
    return provider, out


def edges(path):
    return set(zip(path, path[1:]))   # directed consecutive pairs


def jac(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="real_outputs.jsonl")
    ap.add_argument("--truncate", type=int, default=1000)
    ap.add_argument("--batch-size", type=int, default=6)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="l2_wiring_report.json")
    A = ap.parse_args()

    rows = [json.loads(l) for l in open(A.corpus, encoding="utf-8")]
    items = [{"_id": r["id"], "text": r["output"][:A.truncate]} for r in rows]
    print(f"reading {len(items)} real outputs as WIRING ({len(CODES)} parts), {len(MODELS)} readers", flush=True)
    menu = build_menu()

    jobs = []
    for prov, model in MODELS.items():
        batch = [(it["_id"], it["text"]) for it in items]
        for k in range(0, len(batch), A.batch_size):
            jobs.append((prov, model, menu, batch[k:k + A.batch_size]))
    data = defaultdict(dict)
    done = 0
    with ThreadPoolExecutor(max_workers=A.workers) as ex:
        futs = {ex.submit(read_batch, p, m, mn, b): p for (p, m, mn, b) in jobs}
        for fut in as_completed(futs):
            try:
                prov, out = fut.result()
            except Exception as e:
                print(f"  batch ERROR {str(e)[:110]}", flush=True); continue
            data[prov].update(out)
            done += 1
            if done % 5 == 0:
                print(f"  {done}/{len(jobs)} calls done", flush=True)

    readers = list(MODELS.keys())
    complete = [it["_id"] for it in items
                if all(it["_id"] in data[r] and data[r][it["_id"]]["main"] for r in readers)]
    combos = list(itertools.combinations(range(len(readers)), 2))

    # (1) MAIN-part agreement
    main_pair = []
    for oid in complete:
        m = [data[r][oid]["main"] for r in readers]
        main_pair.append(sum(m[i] == m[k] for i, k in combos) / len(combos))
    main_agree = sum(main_pair) / len(main_pair) if main_pair else 0.0
    kappa = fleiss_kappa([[data[r][oid]["main"] for r in readers] for oid in complete]) if complete else 0.0

    # (2) WIRING (edge-set) agreement vs shuffled null
    per_out = [sum(jac(edges(data[readers[i]][oid]["path"]), edges(data[readers[k]][oid]["path"]))
                   for i, k in combos) / len(combos) for oid in complete]
    wiring_jac = sum(per_out) / len(per_out) if per_out else 0.0
    rng = random.Random(0)
    null_trials = []
    for _ in range(30):
        shuf = {}
        for r in readers:
            es = [edges(data[r][oid]["path"]) for oid in complete]
            rng.shuffle(es)
            shuf[r] = dict(zip(complete, es))
        tj = [sum(jac(shuf[readers[i]][oid], shuf[readers[k]][oid]) for i, k in combos) / len(combos)
              for oid in complete]
        null_trials.append(sum(tj) / len(tj) if tj else 0.0)
    wiring_null = sum(null_trials) / len(null_trials)

    main_usage = Counter(data[r][oid]["main"] for r in readers for oid in complete)
    rep = {
        "corpus": A.corpus, "n_parts": len(CODES), "n_items": len(items), "n_complete": len(complete),
        "main_part_agreement": round(main_agree, 4), "main_fleiss_kappa": round(kappa, 4),
        "wiring_edge_jaccard": round(wiring_jac, 4), "wiring_null_jaccard": round(wiring_null, 4),
        "wiring_lift": round(wiring_jac - wiring_null, 4),
        "main_usage": dict(main_usage.most_common()),
    }
    json.dump(rep, open(A.out, "w", encoding="utf-8"), indent=2)
    print("\n=== STAGE 2 WIRING — change what we measure ===")
    print(f"  n_complete: {len(complete)}/{len(items)}")
    print(f"  MAIN-part agreement : {main_agree:.3f}  (Fleiss kappa {kappa:.3f})   [single-cell was 0.53 / k 0.45]")
    print(f"  WIRING edge Jaccard : {wiring_jac:.3f}  vs null {wiring_null:.3f}  -> lift {wiring_jac - wiring_null:+.3f}")
    print(f"  main-part usage: {rep['main_usage']}")
    print(f"  wrote {A.out}")


if __name__ == "__main__":
    main()
