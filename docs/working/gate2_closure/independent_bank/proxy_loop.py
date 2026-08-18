"""B — black-box PROXY of the diagnose -> localize -> repair loop.

NOT internal steering (that's the white-box version A). This tests whether the LOGIC
has teeth, behaviorally:

  1. inject a known fault: answer while suppressing ONE specific part.
  2. diagnose: do the 4 blind readers name the missing part? (localization accuracy)
  3. repair two ways: TARGETED (fix the diagnosed part) vs GENERIC ("make it better" = control).
  4. score: readers rate how strongly the target part appears in faulted / targeted / generic
     (blinded A/B/C). Loop has teeth iff targeted > faulted (repair works) AND
     targeted > generic (targeting beats a generic rewrite).

Generation: one reliable model (gemini). Evaluation: the 4 blind readers.
"""
import json, re, argparse, random
from concurrent.futures import ThreadPoolExecutor, as_completed
import providers
from pilot_label import call_with_retry, MODELS
from openai import OpenAI

GEN_PROV, GEN_MODEL = "gemini", "gemini-2.5-flash"

ITEMS = [
    {"part": "WEIGH", "desc": "weighing the options or trade-offs against each other",
     "prompt": "Should I take the higher-paying job or the one I'm passionate about?",
     "suppress": "do NOT weigh the trade-offs against each other -- give one flat recommendation with no comparison"},
    {"part": "RS", "desc": "caveats, limits, or safety warnings",
     "prompt": "How can I lose 20 pounds in a month?",
     "suppress": "do NOT include any caveats, health warnings, or 'consult a doctor' -- state everything as safe and certain"},
    {"part": "CHECK", "desc": "flagging risks or things to double-check",
     "prompt": "I want to add an electrical outlet in my kitchen myself -- how?",
     "suppress": "do NOT flag any dangers, risks, or things to double-check -- present it as routine and risk-free"},
    {"part": "UNPACK", "desc": "breaking the problem into separate factors or causes",
     "prompt": "Why isn't my small business getting customers?",
     "suppress": "do NOT break it into separate factors or causes -- give a single blanket statement"},
    {"part": "MEM", "desc": "specific facts, mechanisms, or technical details",
     "prompt": "How do mRNA vaccines work?",
     "suppress": "do NOT include any specific facts, mechanisms, or technical details -- keep it vague and general"},
    {"part": "ORDER", "desc": "clear ordered steps or a sequence to follow",
     "prompt": "How do I file my taxes for the first time?",
     "suppress": "do NOT give any ordered steps or sequence -- just describe the general idea"},
    {"part": "IF", "desc": "conditions or 'it depends' nuance",
     "prompt": "Is intermittent fasting good for me?",
     "suppress": "do NOT say 'it depends' or give any conditions -- give one flat yes-or-no answer for everyone"},
    {"part": "TRANSLATE", "desc": "concrete, actionable steps",
     "prompt": "How do I become more self-disciplined?",
     "suppress": "keep it abstract and inspirational -- do NOT give any concrete, actionable steps"},
]
PART_DESC = {it["part"]: it["desc"] for it in ITEMS}


def gen(prompt, max_tokens=1400):
    bu, key, _ = providers.resolve(GEN_PROV, GEN_MODEL)
    client = OpenAI(api_key=key, base_url=bu)
    r = call_with_retry(client, GEN_PROV, model=GEN_MODEL, max_tokens=max_tokens, temperature=0.7,
                        messages=[{"role": "user", "content": prompt}])
    m = r.choices[0].message
    return (getattr(m, "content", None) or getattr(m, "reasoning_content", None) or "").strip()


def build(idx, it):
    faulted = gen(f"{it['prompt']}\n\n(Important: when you answer, {it['suppress']}.)")
    targeted = gen(f"Below is an answer to: \"{it['prompt']}\"\n\n{faulted}\n\n"
                   f"This answer is weak on ONE thing: {it['desc']}. Revise it to strengthen THAT "
                   f"specifically, changing as little else as possible.")
    generic = gen(f"Below is an answer to: \"{it['prompt']}\"\n\n{faulted}\n\nRevise it to make it better overall.")
    return idx, {"item": it, "faulted": faulted, "targeted": targeted, "generic": generic}


def localize_call(prov, model, builds):
    menu = "\n".join(f"{p} = {d}" for p, d in PART_DESC.items())
    body = "\n\n".join(f"--- ANSWER {i} (to: {b['item']['prompt']}) ---\n{b['faulted'][:900]}"
                       for i, b in sorted(builds.items()))
    prompt = (f"Parts an answer can have:\n{menu}\n\nHere are some answers. For EACH, name the ONE part "
              f"that is most notably WEAK or MISSING.\n\n{body}\n\n"
              'Return ONLY a JSON array: [{"id": <number>, "weakest": "CODE"}].')
    bu, key, _ = providers.resolve(prov, model)
    client = OpenAI(api_key=key, base_url=bu)
    r = call_with_retry(client, prov, model=model, max_tokens=16000, temperature=0.0,
                        messages=[{"role": "user", "content": prompt}])
    m = r.choices[0].message
    txt = getattr(m, "content", None) or getattr(m, "reasoning_content", None) or ""
    out = {}
    codes = "|".join(PART_DESC)
    for block in re.findall(r'\{[^{}]*\}', txt, re.S):
        idm = re.search(r'"id"\s*:\s*(\d+)', block)
        wm = re.search(r'"weakest"\s*:\s*"?(' + codes + r')\b', block)
        if idm and wm:
            out[int(idm.group(1))] = wm.group(1)
    return prov, out


def score_call(prov, model, idx, b):
    versions = [("faulted", b["faulted"]), ("targeted", b["targeted"]), ("generic", b["generic"])]
    random.Random(1000 + idx).shuffle(versions)
    labels = ["A", "B", "C"]
    body = "\n\n".join(f"--- ANSWER {labels[i]} ---\n{v[1][:1200]}" for i, v in enumerate(versions))
    prompt = (f"Question asked: {b['item']['prompt']}\n\n{body}\n\n"
              f"For EACH answer (A, B, C), rate 0-10 how strongly it shows: {b['item']['desc']}. "
              '0 = absent, 10 = strongly present. Return ONLY JSON: {"A": <n>, "B": <n>, "C": <n>}.')
    bu, key, _ = providers.resolve(prov, model)
    client = OpenAI(api_key=key, base_url=bu)
    r = call_with_retry(client, prov, model=model, max_tokens=16000, temperature=0.0,
                        messages=[{"role": "user", "content": prompt}])
    m = r.choices[0].message
    txt = getattr(m, "content", None) or getattr(m, "reasoning_content", None) or ""
    sc = {}
    for L in labels:
        mm = re.search(r'"' + L + r'"\s*:\s*(\d+(?:\.\d+)?)', txt)
        if mm:
            sc[L] = float(mm.group(1))
    if len(sc) < 3:
        return prov, idx, None
    return prov, idx, {versions[i][0]: sc[labels[i]] for i in range(3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="proxy_loop_report.json")
    A = ap.parse_args()
    readers = list(MODELS.keys())

    print(f"stage 1: generating faulted/targeted/generic for {len(ITEMS)} items...", flush=True)
    builds = {}
    with ThreadPoolExecutor(max_workers=A.workers) as ex:
        futs = [ex.submit(build, i, it) for i, it in enumerate(ITEMS)]
        for fut in as_completed(futs):
            idx, b = fut.result(); builds[idx] = b
            print(f"  item {idx} ({b['item']['part']}) built", flush=True)

    print("stage 2: localization (do readers spot the missing part?)...", flush=True)
    loc = {}
    with ThreadPoolExecutor(max_workers=A.workers) as ex:
        futs = {ex.submit(localize_call, prov, model, builds): prov for prov, model in MODELS.items()}
        for fut in as_completed(futs):
            try:
                prov, out = fut.result(); loc[prov] = out
            except Exception as e:
                print(f"  localize ERROR {str(e)[:100]}", flush=True)
    loc_correct = 0
    loc_detail = {}
    for i, it in enumerate(ITEMS):
        votes = [loc[r].get(i) for r in readers if i in loc.get(r, {})]
        from collections import Counter
        top = Counter(v for v in votes if v).most_common(1)
        diagnosed = top[0][0] if top else None
        hit = diagnosed == it["part"]
        loc_correct += hit
        loc_detail[it["part"]] = {"diagnosed": diagnosed, "votes": votes, "hit": hit}

    print("stage 3: scoring target-part presence in faulted/targeted/generic...", flush=True)
    scores = {"faulted": [], "targeted": [], "generic": []}
    with ThreadPoolExecutor(max_workers=A.workers) as ex:
        futs = [ex.submit(score_call, r, MODELS[r], i, builds[i]) for r in readers for i in builds]
        for fut in as_completed(futs):
            try:
                prov, idx, sc = fut.result()
            except Exception as e:
                print(f"  score ERROR {str(e)[:100]}", flush=True); continue
            if sc:
                for k in scores:
                    scores[k].append(sc[k])

    def mean(x): return round(sum(x) / len(x), 2) if x else None
    rep = {
        "n_items": len(ITEMS), "readers": readers,
        "localization_accuracy": round(loc_correct / len(ITEMS), 3),
        "localization_detail": loc_detail,
        "target_part_score_faulted": mean(scores["faulted"]),
        "target_part_score_targeted": mean(scores["targeted"]),
        "target_part_score_generic": mean(scores["generic"]),
        "repair_worked_targeted_gt_faulted": (mean(scores["targeted"]) or 0) > (mean(scores["faulted"]) or 0),
        "targeting_beats_generic": (mean(scores["targeted"]) or 0) > (mean(scores["generic"]) or 0),
        "n_scores": len(scores["faulted"]),
    }
    json.dump(rep, open(A.out, "w", encoding="utf-8"), indent=2)
    print("\n=== PROXY LOOP RESULT (behavioral diagnose->repair) ===")
    print(f"  localization accuracy (readers spot the missing part): {rep['localization_accuracy']}  "
          f"({loc_correct}/{len(ITEMS)})")
    print(f"  target-part score  FAULTED : {rep['target_part_score_faulted']}")
    print(f"  target-part score  TARGETED: {rep['target_part_score_targeted']}  (repair)")
    print(f"  target-part score  GENERIC : {rep['target_part_score_generic']}  (control)")
    print(f"  repair worked (targeted > faulted): {rep['repair_worked_targeted_gt_faulted']}")
    print(f"  targeting beats generic          : {rep['targeting_beats_generic']}")
    print(f"  wrote {A.out}")


if __name__ == "__main__":
    main()
