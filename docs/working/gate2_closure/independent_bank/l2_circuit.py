"""Stage 2 — read real outputs as CIRCUITS (component sets), not single cells.

Hypothesis from the ecological result: real answers are multi-structure, so a single
dominant cell forces disagreement. Reading an answer as a SET of parts (a circuit)
should recover agreement, because it matches what a real answer is.

Each of 10 core parts is described in plain English (no TKS/CAS jargon). The 4 blind
readers mark which parts are present in each real output. We measure inter-reader
agreement on the part-SET (mean pairwise Jaccard overlap) vs a shuffled null that keeps
each reader's marking rate but breaks per-output correlation. reader >> null = the
circuit reading is non-arbitrary.
"""
import json, re, argparse, itertools, random
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import providers
from pilot_label import call_with_retry, MODELS
from openai import OpenAI

# 10 core parts (plain English) mapped to the PCBA Field Manual components
COMPONENTS = [
    ("DR",     "The push",        "the motivation or goal driving the answer — what it's trying to do."),
    ("RS",     "The brakes",      "where it holds back, limits, adds caveats, or declines."),
    ("MEM",    "Drawing on memory","where it pulls in stored knowledge, facts, or past experience."),
    ("DIR",    "One-way street",  "where it insists on a direction and won't reverse it."),
    ("IF",     "The switch",      "where it makes something conditional — 'if X then Y', 'it depends'."),
    ("AMP",    "The engine",      "the main reasoning step that turns the question into an answer (cause -> effect)."),
    ("LOOP",   "The feedback",    "where it loops back, self-corrects, or weighs how its answer affects what comes next."),
    ("CHECK",  "The danger point","the spot where a quiet mistake could slip through — the thing worth double-checking."),
    ("WEIGH",  "The scale",       "where it weighs options against each other and picks."),
    ("FILTER", "The sieve",       "where it filters out noise, or flags a sudden change or shift."),
]
CODES = [c for c, _, _ in COMPONENTS]
CODE_RE = re.compile(r'\b(' + '|'.join(CODES) + r')\b')


def build_menu():
    L = ["Below are ten kinds of PARTS an answer can contain. Read each answer and mark",
         "which parts are clearly doing work in it (usually 2 to 5).", "", "The parts:"]
    for code, name, desc in COMPONENTS:
        L.append(f"{code} = {name}: {desc}")
    return "\n".join(L)


def mark_batch(provider, model, menu, batch):
    bu, key, _ = providers.resolve(provider, model)
    client = OpenAI(api_key=key, base_url=bu)
    lines = [f'--- ANSWER {i} ---\n{s}' for i, s in batch]
    prompt = (menu + "\n\nAnswers to read:\n" + "\n\n".join(lines) +
              '\n\nFor EACH answer, mark the parts clearly present. '
              'Return ONLY a JSON array: [{"id": <number>, "parts": ["CODE", ...]}]. '
              "Every answer id must appear once; use only the codes above.")
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
        out[int(idm.group(1))] = set(CODE_RE.findall(block)) - {"id"}
    return provider, out


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
    ap.add_argument("--out", default="l2_circuit_report.json")
    A = ap.parse_args()

    rows = [json.loads(l) for l in open(A.corpus, encoding="utf-8")]
    items = [{"_id": r["id"], "text": r["output"][:A.truncate]} for r in rows]
    print(f"reading {len(items)} real outputs as CIRCUITS, {len(MODELS)} readers", flush=True)
    menu = build_menu()

    jobs = []
    for prov, model in MODELS.items():
        batch = [(it["_id"], it["text"]) for it in items]
        for k in range(0, len(batch), A.batch_size):
            jobs.append((prov, model, menu, batch[k:k + A.batch_size]))
    marks = defaultdict(dict)
    done = 0
    with ThreadPoolExecutor(max_workers=A.workers) as ex:
        futs = {ex.submit(mark_batch, p, m, mn, b): p for (p, m, mn, b) in jobs}
        for fut in as_completed(futs):
            try:
                prov, out = fut.result()
            except Exception as e:
                print(f"  batch ERROR {str(e)[:110]}", flush=True); continue
            marks[prov].update(out)
            done += 1
            if done % 5 == 0:
                print(f"  {done}/{len(jobs)} calls done", flush=True)

    readers = list(MODELS.keys())
    complete = [it["_id"] for it in items if all(it["_id"] in marks[r] for r in readers)]
    combos = list(itertools.combinations(range(len(readers)), 2))

    per_out = []
    for oid in complete:
        s = [marks[r][oid] for r in readers]
        per_out.append(sum(jac(s[i], s[k]) for i, k in combos) / len(combos))
    reader_jac = sum(per_out) / len(per_out) if per_out else 0.0

    # shuffled null: permute each reader's sets across outputs (keeps marking rate, breaks correlation)
    rng = random.Random(0)
    null_trials = []
    for _ in range(30):
        shuf = {}
        for r in readers:
            sets = [marks[r][oid] for oid in complete]
            rng.shuffle(sets)
            shuf[r] = dict(zip(complete, sets))
        tj = [sum(jac(shuf[readers[i]][oid], shuf[readers[k]][oid]) for i, k in combos) / len(combos)
              for oid in complete]
        null_trials.append(sum(tj) / len(tj) if tj else 0.0)
    null_jac = sum(null_trials) / len(null_trials)

    sizes = [len(marks[r][oid]) for r in readers for oid in complete]
    mean_parts = sum(sizes) / len(sizes) if sizes else 0
    usage = Counter(c for r in readers for oid in complete for c in marks[r][oid])

    rep = {
        "corpus": A.corpus, "n_items": len(items), "n_complete": len(complete), "readers": readers,
        "reader_jaccard": round(reader_jac, 4),
        "null_jaccard": round(null_jac, 4),
        "lift_over_null": round(reader_jac - null_jac, 4),
        "mean_parts_per_answer": round(mean_parts, 2),
        "part_usage": {c: usage.get(c, 0) for c in CODES},
        "DECISIVE_beyond_null": bool(reader_jac - null_jac > 0.10),
    }
    json.dump(rep, open(A.out, "w", encoding="utf-8"), indent=2)
    print("\n=== STAGE 2 — CIRCUIT READING (real outputs) ===")
    print(f"  n_complete: {len(complete)}/{len(items)}")
    print(f"  reader<->reader part-set agreement (Jaccard): {reader_jac:.3f}")
    print(f"  shuffled-null Jaccard                       : {null_jac:.3f}")
    print(f"  lift over null                              : {reader_jac - null_jac:+.3f}")
    print(f"  mean parts marked per answer                : {mean_parts:.2f}")
    print(f"  part usage: {rep['part_usage']}")
    print(f"  DECISIVE beyond null (lift>0.10): {rep['DECISIVE_beyond_null']}")
    print(f"  wrote {A.out}")


if __name__ == "__main__":
    main()
