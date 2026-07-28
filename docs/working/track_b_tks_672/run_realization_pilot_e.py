"""E-ARM — EXPLICIT_AVOIDANCE_INSTRUCTION diagnostic. QUARANTINED, NON-CLAIM-BEARING.

The owner-sanctioned matched comparison. Identical to S2 in every respect —
criterion, sealed families, runner-owned metadata, 16 cells, 4x5 budget — except
ONE frozen prohibition paragraph appended after the audited prompt body.

NO label is printed anywhere (that was pilot v1's fatal defect, and it stays out).
This isolates: does STATING the prohibition (without showing the label as a
target) suppress the topic-vocabulary channel S2 exposed (drive-1 'spiritual',
1b at 0.700), without recreating priming?

The audit runs on the prompt BODY only; the prohibition paragraph is exempt BY
DESIGN and that exemption is the experiment. Disclosed here and in the config.

Items from this arm may never be mixed into a claim-bearing corpus.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
from run_realization_pilot_s2 import (  # noqa: E402 — same apparatus, one delta
    AUTHOR_MODEL, CELLS, CONTROLS, CRITERIA, N_CANDIDATES, N_PLANS, PROHIBITED,
    SEALED, STARVED, TMPL, TRANSPORT_RETRIES, audit_prompt, normalize, r1b_copy, CANON,
)

PROHIB_PARAGRAPH = (
    "\n\nABSOLUTE RULE: the words spiritual, spiritually, mental, mentally, emotional, "
    "emotionally, physical, physically must not appear anywhere in any scenario. "
    "Re-read every scenario before returning and rewrite any that contains one."
)


def main() -> int:
    import google.generativeai as genai

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY required")
    genai.configure(api_key=key)
    canon = json.loads(CANON.read_text(encoding="utf-8"))
    drives = canon["drive_map"]
    sealed = json.loads(SEALED.read_text(encoding="utf-8"))["families"]
    train_by_world = {}
    for rf, m in sorted(sealed.items()):
        if not m["heldout"]:
            train_by_world.setdefault(m["world"], []).append(rf)

    cfg = {
        "design": "WORLD_REALIZATION_GRAMMAR_V1_PILOT_E",
        "arm": "EXPLICIT_AVOIDANCE_INSTRUCTION",
        "role": "SECONDARY DIAGNOSTIC — quarantined, non-claim-bearing, never mixed with S2",
        "delta_vs_s2": "ONE frozen prohibition paragraph appended after the audited body; "
                       "no label printed anywhere",
        "audit_exemption": "the prohibition paragraph is exempt from the prompt audit BY "
                           "DESIGN — that exemption IS the experiment",
        "question": "does stating the prohibition suppress the topic-vocabulary channel "
                    "(drive-1 'spiritual', 1b 0.700 under silence) without recreating priming?",
        "s2_baseline": {"overall": 0.1969, "1b": 0.700, "1d": 0.500, "7c": 0.000, "6a": 0.050},
    }
    (HERE / "pilot_e_frozen_config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True),
                                                     encoding="utf-8")
    print("E-ARM (EXPLICIT INSTRUCTION, NO LABEL)  — QUARANTINED DIAGNOSTIC\n")

    model = genai.GenerativeModel(AUTHOR_MODEL)
    path = HERE / "pilot_e_records.json"
    rec = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    done = {(r["code"], r["plan_idx"]) for r in rec}

    for code in CELLS:
        w = code[1]
        fams = train_by_world[w]
        for plan_idx in range(N_PLANS):
            if (code, plan_idx) in done:
                continue
            rf = fams[plan_idx % len(fams)]
            body = TMPL.format(drive=drives[code[0]], criterion=CRITERIA[w], rf_id=rf,
                               family_text=sealed[rf]["author_text"],
                               plan_idx=plan_idx + 1, nplans=N_PLANS, ncand=N_CANDIDATES)
            audit_prompt(body)                       # body audited; paragraph exempt by design
            prompt = body + PROHIB_PARAGRAPH
            cands, retries, last = [], 0, ""
            for attempt in range(1, TRANSPORT_RETRIES + 2):
                try:
                    resp = model.generate_content(
                        prompt, generation_config={"temperature": 0.95, "top_p": 0.95,
                                                   "max_output_tokens": 8192,
                                                   "response_mime_type": "application/json"},
                        request_options={"timeout": 240})
                    cands = [c for c in normalize(json.loads(resp.text)) if c.strip()]
                    if cands:
                        break
                    last = "no_candidates"
                except Exception as exc:  # noqa: BLE001
                    last, retries = type(exc).__name__, retries + 1
                    time.sleep(2 * attempt)
            n_leak = 0
            for i, text in enumerate(cands[:N_CANDIDATES]):
                hits = PROHIBITED.findall(text)
                n_leak += bool(hits)
                rec.append({"code": code, "plan_idx": plan_idx, "candidate_index": i + 1,
                            "arm": "starved" if code in STARVED else "control",
                            "world": w, "drive": code[0], "rf_id": rf,
                            "text": text, "leaked": bool(hits),
                            "leak_words": sorted({h[0].lower() for h in hits}) if hits else [],
                            "retry_count": retries})
            if not cands:
                rec.append({"code": code, "plan_idx": plan_idx,
                            "generation_failed": last, "retry_count": retries})
            path.write_text(json.dumps(rec, indent=1), encoding="utf-8")
            print(f"  {code} plan {plan_idx} [{rf}]: {n_leak}/{len(cands[:N_CANDIDATES])} leaked",
                  flush=True)

    from collections import defaultdict
    cand = [r for r in rec if r.get("candidate_index")]
    by = defaultdict(lambda: [0, 0])
    for r in cand:
        by[r["code"]][1] += 1
        by[r["code"]][0] += r["leaked"]
    overall = sum(r["leaked"] for r in cand) / max(1, len(cand))
    print("\nE-ARM vs S2 (silent), per cell:")
    s2 = json.load(open(HERE / "pilot_s2_r1.json"))["per_cell"]
    for c in CELLS:
        n, t = by[c]
        s2r = s2[c]["leaked"] / max(1, s2[c]["total"])
        print(f"   {c}: E {n/max(1,t):.3f}   S2 {s2r:.3f}")
    print(f"\n  E overall {overall:.4f}   S2 0.1969   v2 0.1625   v1(label) 0.4058")
    json.dump({"per_cell": {c: {"leaked": by[c][0], "total": by[c][1]} for c in CELLS},
               "overall_leak": overall,
               "comparators": {"s2_silent": 0.1969, "v2_16cell": 0.1625, "v1_label": 0.4058}},
              open(HERE / "pilot_e_r1.json", "w"), indent=2, sort_keys=True)
    print("WROTE pilot_e_r1.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
