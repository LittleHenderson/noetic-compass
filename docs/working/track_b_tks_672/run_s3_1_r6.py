"""S3-1 R6 rerun — the two PENDING rows, under the MOTIVE-REPAIRED prompt.

The confirmatory R6 arms ran the pre-repair prompt; their greens do not carry.
Frozen bar, declared before running: an R6 arm passes if its primary-detector
leak rate is <= 0.05 (the same overall bar as R1). Same 16 cells, 2 plans each
(one train-family, one held-out), 5 candidates, byte-identical prompts across
arms, full logging.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
from run_realization_pilot_s2 import CANON, CELLS, CRITERIA, PROHIBITED, SEALED, STARVED, \
    audit_prompt, normalize  # noqa: E402
from run_realization_pilot_e import PROHIB_PARAGRAPH  # noqa: E402
from run_confirmatory_generation import call_anthropic, load_anthropic_key, secondary_hits  # noqa: E402
from run_s3_1_generation import MOTIVE, TMPL  # noqa: E402

ARMS = {"R6A": ("gemini", "models/gemini-2.5-flash"),
        "R6B": ("anthropic", "claude-haiku-4-5-20251001")}
N_CANDIDATES, RETRIES, BAR = 5, 2, 0.05


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    import anthropic
    import google.generativeai as genai

    genai.configure(api_key=os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"])
    aclient = anthropic.Anthropic(api_key=load_anthropic_key())
    canon = json.loads(CANON.read_text(encoding="utf-8"))
    sealed = json.loads(SEALED.read_text(encoding="utf-8"))["families"]
    train_bw, held_bw = {}, {}
    for rf, m in sorted(sealed.items()):
        (held_bw if m["heldout"] else train_bw).setdefault(m["world"], []).append(rf)

    out = {}
    for arm, (prov, model_id) in ARMS.items():
        gm = genai.GenerativeModel(model_id) if prov == "gemini" else None
        rec_path = HERE / f"s3_1_{arm}_records.json"
        rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else []
        done = {(r["code"], r["plan_idx"]) for r in rec}
        for code in CELLS:
            w, d = code[1], code[0]
            for plan_idx in range(2):
                if (code, plan_idx) in done:
                    continue
                heldout = plan_idx == 1
                pool = held_bw[w] if heldout else train_bw[w]
                rf = pool[plan_idx % len(pool)]
                want, rival = MOTIVE[d]
                body = TMPL.format(want=want, rival=rival, criterion=CRITERIA[w], rf_id=rf,
                                   family_text=sealed[rf]["author_text"],
                                   plan_idx=plan_idx + 1, nplans=2, ncand=N_CANDIDATES)
                audit_prompt(body)
                prompt = body + PROHIB_PARAGRAPH
                cands, raw, hist = [], "", []
                for attempt in range(1, RETRIES + 2):
                    try:
                        raw = (gm.generate_content(
                            prompt, generation_config={"temperature": 0.95, "top_p": 0.95,
                                                       "max_output_tokens": 8192,
                                                       "response_mime_type": "application/json"},
                            request_options={"timeout": 240}).text
                            if prov == "gemini" else call_anthropic(aclient, model_id, prompt))
                        cands = [c for c in normalize(json.loads(
                            re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.M))) if c.strip()]
                        if cands:
                            break
                        hist.append({"attempt": attempt, "error": "no_candidates"})
                    except Exception as exc:  # noqa: BLE001
                        hist.append({"attempt": attempt, "error": type(exc).__name__})
                        time.sleep(2 * attempt)
                with open(HERE / f"calls_s3_1_{arm}.jsonl", "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"arm": arm, "model": model_id, "code": code,
                                         "plan_idx": plan_idx, "rf_id": rf, "heldout": heldout,
                                         "prompt": prompt, "prompt_sha256": sha(prompt),
                                         "response_raw": raw, "response_sha256": sha(raw),
                                         "retry_history": hist,
                                         "normalized_candidates": cands[:N_CANDIDATES]},
                                        ensure_ascii=False) + "\n")
                for i, text in enumerate(cands[:N_CANDIDATES]):
                    hits = PROHIBITED.findall(text)
                    rec.append({"code": code, "plan_idx": plan_idx, "candidate_index": i + 1,
                                "world": w, "drive": d, "rf_id": rf, "heldout": heldout,
                                "text": text, "leaked_primary": bool(hits),
                                "leak_words_secondary": secondary_hits(text)})
                rec_path.write_text(json.dumps(rec, indent=1), encoding="utf-8")
                print(f"  [{arm}] {code} p{plan_idx}: "
                      f"{sum(1 for r in rec if r.get('candidate_index') and r['code'] == code and r['plan_idx'] == plan_idx and r['leaked_primary'])}"
                      f"/{len(cands[:N_CANDIDATES])} leaked", flush=True)
        rows = [r for r in rec if r.get("candidate_index")]
        p = sum(r["leaked_primary"] for r in rows) / max(1, len(rows))
        s = sum(bool(r["leak_words_secondary"]) for r in rows) / max(1, len(rows))
        out[arm] = {"model": model_id, "n": len(rows), "primary": round(p, 4),
                    "secondary": round(s, 4), "bar": BAR, "pass": bool(p <= BAR)}
        print(f"\n  {arm} {model_id}: primary={p:.4f} secondary={s:.4f} "
              f"{'PASS' if p <= BAR else 'FAIL'} (bar {BAR})")

    # ---- fill the last two rows of the mechanical table
    tbl = json.loads((HERE / "s3_1_eval_results.json").read_text(encoding="utf-8"))
    for arm in ("R6A", "R6B"):
        tbl["table"][arm] = {"pass": out[arm]["pass"],
                             "value": f"{out[arm]['primary']:.4f} (bar {BAR}) motive-repaired prompt"}
    req = ["R1", "R1B", "R2-G", "R3-J", "R4", "R5", "R6A", "R6B", "P12", "P63", "P74"]
    all_green = all(tbl["table"][k]["pass"] for k in req)
    tbl["pending"] = []
    tbl["verdict"] = "ALL_ROWS_PASS" if all_green else "NOT_AUTHORIZED"
    (HERE / "s3_1_eval_results.json").write_text(json.dumps(tbl, indent=2, sort_keys=True),
                                                 encoding="utf-8")
    json.dump(out, open(HERE / "s3_1_r6_results.json", "w"), indent=2, sort_keys=True)
    print(f"\nFINAL 13-ROW TABLE VERDICT: {tbl['verdict']}")
    print("WROTE s3_1_r6_results.json; table updated in s3_1_eval_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
