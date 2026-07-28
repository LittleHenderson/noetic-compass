"""CONFIRMATORY-PILOT-R1-R6 — generation stage, three author arms, FULL LOGGING.

Replayability repair: every call stores exact rendered prompt, prompt SHA-256,
raw response, response SHA-256, model, params, cell, RF-ID, parser hash, and
retry history — to calls_<arm>.jsonl BEFORE any scoring.

Arms (same prompt bytes; only the model differs):
  A0   gemini-2.5-flash-lite   16 x 4 x 5 = 320   plans 0-2 TRAIN, plan 3 HELD-OUT
  R6A  gemini-2.5-flash        16 x 2 x 5 = 160   one train + one held-out plan
  R6B  claude-haiku-4-5        16 x 2 x 5 = 160   TRUE cross-family author

Dual detectors: primary frozen regex (selection uses ONLY this, comparability);
secondary morphology-aware (NFKC, casefold, +ity forms) reported alongside.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import time
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
from run_realization_pilot_s2 import (  # noqa: E402 — byte-identical policy
    CANON, CELLS, CRITERIA, PROHIBITED, SEALED, STARVED, TMPL, audit_prompt, normalize,
    r1b_copy,
)
from run_realization_pilot_e import PROHIB_PARAGRAPH  # noqa: E402

SECONDARY = re.compile(
    r"\b(spiritual(ly)?|spirituality|physical(ly)?|physicality|"
    r"mental(ly)?|mentality|emotional(ly)?)\b")
N_CANDIDATES, TRANSPORT_RETRIES = 5, 2
PARSER_HASH = hashlib.sha256(inspect.getsource(normalize).encode()).hexdigest()[:16]

ARMS = {
    "A0": {"provider": "gemini", "model": "models/gemini-2.5-flash-lite", "n_plans": 4},
    "R6A": {"provider": "gemini", "model": "models/gemini-2.5-flash", "n_plans": 2},
    "R6B": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001", "n_plans": 2},
}


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def secondary_hits(text: str):
    t = unicodedata.normalize("NFKC", text).casefold()
    return sorted({m.group(0) for m in SECONDARY.finditer(t)})


def load_anthropic_key() -> str:
    envp = HERE.parents[2] / "noetic-compass-scaffold/noetic-compass/.env"
    m = re.search(r"NC_ANTHROPIC_API_KEY\s*=\s*(\S+)",
                  envp.read_text(encoding="utf-8", errors="replace"))
    if not m:
        raise SystemExit("NC_ANTHROPIC_API_KEY not found")
    return m.group(1).strip().strip('"')


def call_gemini(model_obj, prompt: str):
    resp = model_obj.generate_content(
        prompt, generation_config={"temperature": 0.95, "top_p": 0.95,
                                   "max_output_tokens": 8192,
                                   "response_mime_type": "application/json"},
        request_options={"timeout": 240})
    return resp.text


def call_anthropic(client, model: str, prompt: str):
    msg = client.messages.create(
        model=model, max_tokens=8192, temperature=0.95,
        messages=[{"role": "user", "content": prompt + "\n\nReturn ONLY the JSON object, no other text."}])
    return msg.content[0].text


def main() -> int:
    import google.generativeai as genai
    import anthropic

    gkey = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not gkey:
        raise SystemExit("GEMINI_API_KEY required")
    genai.configure(api_key=gkey)
    aclient = anthropic.Anthropic(api_key=load_anthropic_key())

    canon = json.loads(CANON.read_text(encoding="utf-8"))
    drives = canon["drive_map"]
    sealed = json.loads(SEALED.read_text(encoding="utf-8"))["families"]
    train_by_world, held_by_world = {}, {}
    for rf, m in sorted(sealed.items()):
        (held_by_world if m["heldout"] else train_by_world).setdefault(m["world"], []).append(rf)

    print("CONFIRMATORY-PILOT-R1-R6 — generation, full logging")
    print(f"  parser hash {PARSER_HASH}   arms: " +
          ", ".join(f"{a}={c['model']}" for a, c in ARMS.items()) + "\n")

    gemini_models = {}
    for arm, cfgA in ARMS.items():
        calls_path = HERE / f"calls_{arm}.jsonl"
        rec_path = HERE / f"confirm_{arm}_records.json"
        rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else []
        done = {(r["code"], r["plan_idx"]) for r in rec}
        n_plans = cfgA["n_plans"]
        for code in CELLS:
            w = code[1]
            for plan_idx in range(n_plans):
                if (code, plan_idx) in done:
                    continue
                # A0: plans 0-2 train, 3 held-out. R6 arms: plan 0 train, plan 1 held-out.
                heldout = (plan_idx == n_plans - 1)
                pool = held_by_world[w] if heldout else train_by_world[w]
                rf = pool[plan_idx % len(pool)]
                body = TMPL.format(drive=drives[code[0]], criterion=CRITERIA[w], rf_id=rf,
                                   family_text=sealed[rf]["author_text"],
                                   plan_idx=plan_idx + 1, nplans=n_plans, ncand=N_CANDIDATES)
                audit_prompt(body)
                prompt = body + PROHIB_PARAGRAPH
                cands, retry_hist, raw = [], [], ""
                for attempt in range(1, TRANSPORT_RETRIES + 2):
                    try:
                        if cfgA["provider"] == "gemini":
                            mo = gemini_models.setdefault(
                                cfgA["model"], __import__("google.generativeai", fromlist=["x"]
                                                          ).GenerativeModel(cfgA["model"]))
                            raw = call_gemini(mo, prompt)
                        else:
                            raw = call_anthropic(aclient, cfgA["model"], prompt)
                        got = json.loads(re.sub(r"^```(json)?|```$", "",
                                                raw.strip(), flags=re.M))
                        cands = [c for c in normalize(got) if c.strip()]
                        if cands:
                            break
                        retry_hist.append({"attempt": attempt, "error": "no_candidates"})
                    except Exception as exc:  # noqa: BLE001 — transport only
                        retry_hist.append({"attempt": attempt, "error": type(exc).__name__})
                        time.sleep(2 * attempt)
                # FULL LOGGING, before scoring
                with open(calls_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({
                        "arm": arm, "model": cfgA["model"], "code": code,
                        "plan_idx": plan_idx, "rf_id": rf, "heldout": heldout,
                        "request_params": {"temperature": 0.95, "top_p": 0.95,
                                           "max_tokens": 8192},
                        "prompt": prompt, "prompt_sha256": sha(prompt),
                        "response_raw": raw, "response_sha256": sha(raw),
                        "parser_hash": PARSER_HASH, "retry_history": retry_hist,
                        "normalized_candidates": cands[:N_CANDIDATES],
                    }, ensure_ascii=False) + "\n")
                n_sel = 0
                for i, text in enumerate(cands[:N_CANDIDATES]):
                    p_hits = PROHIBITED.findall(text)
                    keep = (not p_hits) and n_sel < 3
                    if keep:
                        n_sel += 1
                    rec.append({
                        "code": code, "plan_idx": plan_idx, "candidate_index": i + 1,
                        "arm_group": "starved" if code in STARVED else "control",
                        "world": w, "drive": code[0], "rf_id": rf, "heldout": heldout,
                        "text": text,
                        "leaked_primary": bool(p_hits),
                        "leak_words_primary": sorted({h[0].lower() for h in p_hits}),
                        "leak_words_secondary": secondary_hits(text),
                        "selected": keep,
                        "r1b": round(r1b_copy(text, CRITERIA[w] + " " +
                                              sealed[rf]["author_text"]), 4),
                    })
                if not cands:
                    rec.append({"code": code, "plan_idx": plan_idx,
                                "generation_failed": True, "retry_history": retry_hist})
                rec_path.write_text(json.dumps(rec, indent=1), encoding="utf-8")
                n_leak = sum(1 for r in rec if r.get("candidate_index")
                             and r["code"] == code and r["plan_idx"] == plan_idx
                             and r["leaked_primary"])
                print(f"  [{arm}] {code} p{plan_idx} {'H' if heldout else 'T'} [{rf}]: "
                      f"{n_leak}/{len(cands[:N_CANDIDATES])} leaked", flush=True)

    # ---- summary across arms
    print("\nARM SUMMARIES (primary | secondary detector):")
    out = {}
    for arm in ARMS:
        rp = HERE / f"confirm_{arm}_records.json"
        rows = [r for r in json.loads(rp.read_text(encoding="utf-8"))
                if r.get("candidate_index")]
        p = sum(r["leaked_primary"] for r in rows) / max(1, len(rows))
        s = sum(bool(r["leak_words_secondary"]) for r in rows) / max(1, len(rows))
        out[arm] = {"n": len(rows), "primary": round(p, 4), "secondary": round(s, 4),
                    "model": ARMS[arm]["model"]}
        print(f"  {arm:4s} {ARMS[arm]['model']:34s} n={len(rows):4d}  "
              f"primary={p:.4f}  secondary={s:.4f}")
    json.dump(out, open(HERE / "confirm_generation_summary.json", "w"), indent=2,
              sort_keys=True)
    print("\nNEXT: R2 June gate, R3/R4 blind judging, R5 lexical baselines — separate "
          "script, run only after this generation freezes.")
    print("WROTE confirm_generation_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
