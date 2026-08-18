"""Track A pilot — STAGE 1: authoring.

Each of the 4 blind authors (Gemini, DeepSeek-V4-Pro, Qwen3.8-max, GLM-4.6) writes
plain-English SITUATIONS for the 40 concepts, generated PER-WORLD (4 smaller calls
per author) to fix the truncation that lost worlds B/C/D in the all-40-in-one prompt.

Documented pre-registration deviation: per-world chunking. Same colloquial content
(cell_descriptions_colloquial.json) and same output contract as the frozen template;
only the call is split by world. Does NOT touch the frozen elicit_prompt_template.txt.

Output: pilot_raw.jsonl with rows {english, element_label, label, author_id, model, world}.
Fields match acceptance_gate.py (english / element_label). NO rater field yet (added at
labelling stage as a separate report, so G4 admissibility stays clean).
"""
import os, re, json, argparse, sys, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import providers
from openai import OpenAI

try:  # Windows console is cp1252; API error messages can contain non-latin chars
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# per-provider concurrency caps (GLM/Zhipu rate-limits hard) + retry-on-429
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
                if transient and attempt < 5:
                    pass
                else:
                    raise
        time.sleep(delay); delay = min(delay * 2, 60)

# provider -> exact model id that PASSED the blindness probe
AUTHORS = [
    ("gemini",   "gemini-2.5-flash"),
    ("deepseek", "deepseek-v4-pro"),
    ("qwen",     "qwen3.8-max"),
    ("glm",      "glm-4.6"),
]
WORLDS = ["A", "B", "C", "D"]

OBJ = re.compile(r'\{[^{}]*?"code"\s*:\s*"([ABCD](?:10|[1-9]))"[^{}]*?"scenario"\s*:\s*"((?:[^"\\]|\\.)*)"[^{}]*?\}', re.S)
OBJ2 = re.compile(r'\{[^{}]*?"scenario"\s*:\s*"((?:[^"\\]|\\.)*)"[^{}]*?"code"\s*:\s*"([ABCD](?:10|[1-9]))"[^{}]*?\}', re.S)


def build_world_prompt(data, world, items_per_cell):
    cells, worlds = data["cells"], data["worlds"]
    w = worlds[world]
    L = []
    L.append(f"# Evaluation-dataset authoring — Set {world}")
    L.append("")
    L.append("You are helping create an evaluation dataset for a research project. Below are 10 short")
    L.append('descriptions of "human situations" — each describes a particular kind of experience,')
    L.append("reaction, or state a person can be in. For each, write short natural-language scenarios")
    L.append("that exemplify it.")
    L.append("")
    L.append("Constraints:")
    L.append("- Each item is a brief, concrete scenario (2-4 sentences) about a person.")
    L.append("- Vary the people, settings, and circumstances across items.")
    L.append("- Do NOT use abstract philosophical or technical language. Stay concrete.")
    L.append("- Each item must clearly exemplify ONE category below.")
    L.append(f'- Label each item with the exact code shown (e.g. "{world}1", "{world}5").')
    L.append("")
    L.append(f"## Categories — {w['name_plain']}")
    L.append(w["description_plain"])
    L.append("")
    for n in range(1, 11):
        code = f"{world}{n}"
        c = cells[code]
        L.append(f"**{code} — {c['label_plain']}**")
        L.append(c["description_plain"])
        L.append("Write about situations like these:")
        for ex in c["examples_positive"]:
            L.append(f"- {ex}")
        L.append("Avoid situations like these:")
        for ex in c["examples_negative"]:
            L.append(f"- {ex}")
        L.append("")
    L.append("## Output format")
    L.append('Return ONLY a JSON array. Each element: {"code": "%s1", "scenario": "..."}.' % world)
    L.append(f"Generate {items_per_cell} items per category ({items_per_cell*10} items total for this set).")
    L.append("Vary people, settings, and situations. Never reuse wording across categories.")
    return "\n".join(L)


def parse_items(text):
    out = []
    for m in OBJ.finditer(text):
        try: out.append((m.group(1), json.loads('"' + m.group(2) + '"')))
        except Exception: pass
    for m in OBJ2.finditer(text):
        try: out.append((m.group(2), json.loads('"' + m.group(1) + '"')))
        except Exception: pass
    return out


def gen_one(provider, model, world, prompt, max_tokens, temperature):
    bu, key, _ = providers.resolve(provider, model)
    client = OpenAI(api_key=key, base_url=bu)
    r = call_with_retry(client, provider, model=model, max_tokens=max_tokens,
                        temperature=temperature,
                        messages=[{"role": "user", "content": prompt}])
    msg = r.choices[0].message
    txt = getattr(msg, "content", None) or ""
    return provider, model, world, txt, r.choices[0].finish_reason


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell-file", default="cell_descriptions_colloquial.json")
    ap.add_argument("--items-per-cell", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="pilot_raw.jsonl")
    A = ap.parse_args()

    data = json.load(open(A.cell_file, encoding="utf-8"))
    jobs = []
    for provider, model in AUTHORS:
        for world in WORLDS:
            prompt = build_world_prompt(data, world, A.items_per_cell)
            jobs.append((provider, model, world, prompt))
    print(f"authoring: {len(AUTHORS)} authors x {len(WORLDS)} worlds = {len(jobs)} calls "
          f"@ {A.items_per_cell}/cell, max_tokens={A.max_tokens}", flush=True)

    rows, seen = [], set()
    fout = open(A.out, "w", encoding="utf-8")   # write incrementally: partial progress survives a crash
    with ThreadPoolExecutor(max_workers=A.workers) as ex:
        futs = {ex.submit(gen_one, p, m, w, pr, A.max_tokens, A.temperature): (p, m, w)
                for (p, m, w, pr) in jobs}
        for fut in as_completed(futs):
            p, m, w = futs[fut]
            try:
                provider, model, world, txt, finish = fut.result()
            except Exception as e:
                print(f"  [{p}/{w}] ERROR {str(e)[:160]}", flush=True); continue
            got = parse_items(txt)
            new = 0
            for code, scen in got:
                scen = scen.strip()
                if code[0] != world:      # keep only this world's codes
                    continue
                k = scen.lower()
                if len(scen) > 20 and k not in seen:
                    seen.add(k)
                    row = {"english": scen, "element_label": code, "label": code,
                           "author_id": provider, "model": model, "world": world}
                    rows.append(row)
                    fout.write(json.dumps(row, ensure_ascii=False) + "\n"); fout.flush()
                    new += 1
            print(f"  [{p}/{w}] parsed {len(got)} -> {new} new (finish={finish}, resp_chars={len(txt)})", flush=True)
    fout.close()

    from collections import Counter
    per_cell = Counter(r["element_label"] for r in rows)
    per_author = Counter(r["author_id"] for r in rows)
    covered = sorted(per_cell)
    print(f"\nTOTAL unique authored items: {len(rows)}")
    print(f"cells covered: {len(per_cell)}/40   min/cell={min(per_cell.values()) if per_cell else 0}   "
          f"max/cell={max(per_cell.values()) if per_cell else 0}")
    print("per-author:", dict(per_author))
    missing = [f"{w}{n}" for w in WORLDS for n in range(1, 11) if f"{w}{n}" not in per_cell]
    if missing: print("MISSING cells:", missing)
    below5 = sorted(c for c, n in per_cell.items() if n < 5)
    if below5: print(f"cells <5 items ({len(below5)}):", below5)
    print(f"wrote {A.out}")


if __name__ == "__main__":
    main()
