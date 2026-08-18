"""Track A pilot — STAGE 3: independent labelling (R6).

Each authored situation is independently labelled by TWO blind models that did NOT
write it. Labellers see ONLY the scenario + a colloquial 40-category menu (no TKS
terms, no author label, no other labeller's label). Keep the item iff the two
labellers AGREE; discard on disagreement (never adjudicate). Agreed code becomes
the item's final label.

Independence rotation (author -> its 2 labellers):
    gemini   -> deepseek, qwen
    deepseek -> qwen, glm
    qwen     -> glm, gemini
    glm      -> gemini, deepseek

Outputs:
    pilot_bank.jsonl          survivors only: {english, element_label, label}  (NO rater field -> G4 clean)
    pilot_labelling_report.json  raw agreement, discard rate, per-cell survivors, per-item labels (R6 evidence)
"""
import os, re, json, argparse, random, sys, time, threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import providers
from openai import OpenAI

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_SEM = {"gemini": threading.Semaphore(4), "deepseek": threading.Semaphore(2),
        "qwen": threading.Semaphore(2), "glm": threading.Semaphore(1)}


def call_with_retry(client, provider, **kw):
    delay = 5.0
    for attempt in range(6):
        with _SEM.get(provider, threading.Semaphore(2)):
            try:
                return client.chat.completions.create(**kw)
            except Exception as e:
                msg = str(e)
                transient = "429" in msg or "rate" in msg.lower() or "500" in msg or "502" in msg or "503" in msg
                if not (transient and attempt < 5):
                    raise
        time.sleep(delay); delay = min(delay * 2, 60)

MODELS = {"gemini": "gemini-2.5-flash", "deepseek": "deepseek-v4-pro",
          "qwen": "qwen3.8-max", "glm": "glm-4.6"}
ORDER = ["gemini", "deepseek", "qwen", "glm"]
LABELLERS_FOR = {
    "gemini":   ["deepseek", "qwen"],
    "deepseek": ["qwen", "glm"],
    "qwen":     ["glm", "gemini"],
    "glm":      ["gemini", "deepseek"],
}

ARR = re.compile(r'\{[^{}]*?"id"\s*:\s*(\d+)[^{}]*?"code"\s*:\s*"([ABCD](?:10|[1-9]))"[^{}]*?\}', re.S)
ARR2 = re.compile(r'\{[^{}]*?"code"\s*:\s*"([ABCD](?:10|[1-9]))"[^{}]*?"id"\s*:\s*(\d+)[^{}]*?\}', re.S)


def build_menu(cell_file):
    d = json.load(open(cell_file, encoding="utf-8"))
    cells, worlds = d["cells"], d["worlds"]
    L = ["The 40 categories (pick the ONE that best fits each scenario):", ""]
    for w in ["A", "B", "C", "D"]:
        L.append(f"-- {worlds[w]['name_plain']} --")
        for n in range(1, 11):
            code = f"{w}{n}"
            c = cells[code]
            desc = re.sub(r"\s+", " ", c["description_plain"]).strip()
            L.append(f"{code}: {c['label_plain']} — {desc[:130]}")
        L.append("")
    return "\n".join(L)


def label_batch(provider, model, menu, batch):
    """batch = list of (id, scenario). Returns dict id->code."""
    bu, key, _ = providers.resolve(provider, model)
    client = OpenAI(api_key=key, base_url=bu)
    lines = [f'{i}: {s}' for i, s in batch]
    prompt = (menu + "\n\nScenarios to categorize:\n" + "\n".join(lines) +
              '\n\nFor EACH scenario, choose the single best-fitting category code. '
              'Return ONLY a JSON array: [{"id": <number>, "code": "<code>"}]. '
              "Every scenario id must appear exactly once.")
    r = call_with_retry(client, provider, model=model, max_tokens=8000, temperature=0.0,
                        messages=[{"role": "user", "content": prompt}])
    txt = getattr(r.choices[0].message, "content", None) or ""
    out = {}
    for m in ARR.finditer(txt):
        out[int(m.group(1))] = m.group(2)
    for m in ARR2.finditer(txt):
        out.setdefault(int(m.group(2)), m.group(1))
    return provider, out, r.choices[0].finish_reason, len(txt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default="pilot_dedup.jsonl")
    ap.add_argument("--cell-file", default="cell_descriptions_colloquial.json")
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out-bank", default="pilot_bank.jsonl")
    ap.add_argument("--out-report", default="pilot_labelling_report.json")
    A = ap.parse_args()

    items = []
    with open(A.bank, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if line:
                r = json.loads(line); r["_id"] = i; items.append(r)
    print(f"labelling {len(items)} items; 2 independent labellers each", flush=True)

    menu = build_menu(A.cell_file)
    # build per-labeller worklists: labeller_provider -> [(id, scenario)]
    work = defaultdict(list)
    for it in items:
        for lab in LABELLERS_FOR[it["author_id"]]:
            work[lab].append((it["_id"], it["english"]))

    rng = random.Random(1234)
    labels = defaultdict(dict)   # id -> {labeller: code}
    jobs = []
    for lab, lst in work.items():
        rng.shuffle(lst)
        for k in range(0, len(lst), A.batch_size):
            jobs.append((lab, MODELS[lab], menu, lst[k:k + A.batch_size]))
    print(f"{len(jobs)} labelling calls (batch={A.batch_size}) across {len(work)} labellers", flush=True)

    done = 0
    with ThreadPoolExecutor(max_workers=A.workers) as ex:
        futs = {ex.submit(label_batch, lab, model, menu, batch): lab
                for (lab, model, menu, batch) in jobs}
        for fut in as_completed(futs):
            lab = futs[fut]
            try:
                provider, out, finish, nchars = fut.result()
            except Exception as e:
                print(f"  [{lab}] batch ERROR {str(e)[:110]}", flush=True); continue
            for _id, code in out.items():
                labels[_id][provider] = code
            done += 1
            if done % 10 == 0 or finish != "stop":
                print(f"  {done}/{len(jobs)} calls (last {lab}: {len(out)} labels, finish={finish})", flush=True)

    # apply R6: keep iff the 2 independent labellers agree
    survivors, per_item, agree, disagree, incomplete = [], [], 0, 0, 0
    for it in items:
        labs = LABELLERS_FOR[it["author_id"]]
        got = labels.get(it["_id"], {})
        c1, c2 = got.get(labs[0]), got.get(labs[1])
        rec = {"id": it["_id"], "author": it["author_id"], "author_label": it["element_label"],
               "labeller1": labs[0], "code1": c1, "labeller2": labs[1], "code2": c2}
        if c1 is None or c2 is None:
            incomplete += 1; rec["result"] = "incomplete"
        elif c1 == c2:
            agree += 1; rec["result"] = "agree"; rec["final"] = c1
            survivors.append({"english": it["english"], "element_label": c1, "label": c1})
        else:
            disagree += 1; rec["result"] = "disagree"
        per_item.append(rec)

    n = len(items)
    decided = agree + disagree
    raw_agreement = agree / max(1, decided)
    per_cell = Counter(s["element_label"] for s in survivors)
    # also: how often labellers matched the ORIGINAL author label
    author_match = sum(1 for r in per_item if r.get("final") and r["final"] == r["author_label"])

    with open(A.out_bank, "w", encoding="utf-8") as f:
        for s in survivors:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    report = {
        "n_authored": n, "n_decided": decided, "n_incomplete_labelling": incomplete,
        "agree": agree, "disagree": disagree,
        "raw_agreement": round(raw_agreement, 4),
        "discard_rate_disagree": round(disagree / max(1, decided), 4),
        "survivors": len(survivors),
        "survivor_cells": len(per_cell),
        "survivor_min_per_cell": min(per_cell.values()) if per_cell else 0,
        "survivor_max_per_cell": max(per_cell.values()) if per_cell else 0,
        "labeller_matched_author_label": author_match,
        "per_item": per_item,
    }
    json.dump(report, open(A.out_report, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\n=== R6 LABELLING ===")
    print(f"  authored={n}  decided={decided}  incomplete={incomplete}")
    print(f"  agree={agree}  disagree={disagree}  raw_agreement={raw_agreement:.3f}")
    print(f"  survivors={len(survivors)}  cells={len(per_cell)}/40  "
          f"min/cell={report['survivor_min_per_cell']}  max/cell={report['survivor_max_per_cell']}")
    print(f"  (labeller pair also matched author's own label on {author_match} survivors)")
    print(f"  wrote {A.out_bank} + {A.out_report}")


if __name__ == "__main__":
    main()
