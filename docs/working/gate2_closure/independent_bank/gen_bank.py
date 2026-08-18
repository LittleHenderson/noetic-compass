#!/usr/bin/env python3
"""Track A generation: call the (blindness-passed) Gemini author with the frozen
elicit prompt, parse {code,scenario} items from each response (tolerant of truncation),
accumulate + dedupe across calls, report per-cell coverage. Same prompt each call;
temperature varies output. Does NOT repair — just accumulates unique items."""
import os, re, json, argparse, sys
from openai import OpenAI

AP = argparse.ArgumentParser()
AP.add_argument("--prompt", default="elicit_prompt_v2.txt")
AP.add_argument("--provider", default="gemini",
                help="deepseek|qwen|glm|gemini|openai (reads key from keys file)")
AP.add_argument("--model", default=None, help="override model id (else provider default)")
AP.add_argument("--keys-file", default=None)
AP.add_argument("--calls", type=int, default=2)
AP.add_argument("--temperature", type=float, default=0.9)
AP.add_argument("--max-tokens", type=int, default=8000)
AP.add_argument("--out-raw", default="generated_bank_raw.json")
AP.add_argument("--out-jsonl", default="generated_bank.jsonl")
A = AP.parse_args()

prompt = open(A.prompt, encoding="utf-8").read()
import providers
base_url, key, MODEL = providers.resolve(A.provider, A.model, A.keys_file)
client = OpenAI(api_key=key, base_url=base_url)

CODE = re.compile(r"^[ABCD](?:10|[1-9])$")
# tolerant object extractor: pull every {...} with code+scenario, even from a truncated array
OBJ = re.compile(r'\{[^{}]*?"code"\s*:\s*"([ABCD](?:10|[1-9]))"[^{}]*?"scenario"\s*:\s*"((?:[^"\\]|\\.)*)"[^{}]*?\}', re.S)
OBJ2 = re.compile(r'\{[^{}]*?"scenario"\s*:\s*"((?:[^"\\]|\\.)*)"[^{}]*?"code"\s*:\s*"([ABCD](?:10|[1-9]))"[^{}]*?\}', re.S)

def parse_items(text):
    out = []
    for m in OBJ.finditer(text):
        out.append({"code": m.group(1), "scenario": json.loads('"' + m.group(2) + '"')})
    for m in OBJ2.finditer(text):
        out.append({"code": m.group(2), "scenario": json.loads('"' + m.group(1) + '"')})
    return out

seen = set(); items = []
for i in range(A.calls):
    try:
        r = client.chat.completions.create(
            model=MODEL, temperature=A.temperature, max_tokens=A.max_tokens,
            messages=[{"role": "user", "content": prompt}])
        txt = r.choices[0].message.content or ""
    except Exception as e:
        print(f"call {i}: ERROR {str(e)[:120]}", flush=True); continue
    got = parse_items(txt)
    new = 0
    for it in got:
        sc = it["scenario"].strip()
        k = sc.lower()
        if CODE.match(it["code"]) and len(sc) > 20 and k not in seen:
            seen.add(k); items.append({"code": it["code"], "scenario": sc}); new += 1
    print(f"call {i}: parsed {len(got)} -> {new} new (total {len(items)}); resp_chars={len(txt)}", flush=True)

from collections import Counter
per_cell = Counter(it["code"] for it in items)
cells_covered = len(per_cell); min_per = min(per_cell.values()) if per_cell else 0
print(f"\nTOTAL unique items: {len(items)} across {cells_covered}/40 cells; min/cell={min_per}")
print("per-cell counts:", dict(sorted(per_cell.items())))
json.dump(items, open(A.out_raw, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
with open(A.out_jsonl, "w", encoding="utf-8") as f:
    for it in items:
        f.write(json.dumps({"code": it["code"], "scenario": it["scenario"], "label": it["code"]}) + "\n")
print(f"wrote {A.out_raw} + {A.out_jsonl}")
if items:
    print("\nSAMPLES:")
    for c in ["A1", "B5", "C3", "D7"]:
        s = next((it for it in items if it["code"] == c), None)
        if s: print(f"  [{c}] {s['scenario'][:150]}")
