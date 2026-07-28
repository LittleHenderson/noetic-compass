"""S3-1 — motive-repaired generation. Prereg: PREREG_S3_LOCK.md. Triggered by S3-0 report.

CHANGED vs the confirmatory pilot: ONLY the motive block (five elements, with the
REJECTED CLOSE RIVAL as the load-bearing element). Unchanged: World grammar,
universal target-blind instruction, regex + morphology audit, realization
families and splits, logging standard, quarantine.

Frozen close-rival map. The owner specified rivals for drives 1, 6, 7 (the three
observed collapses). Rivals for 2, 3, 4, 5 are defined HERE, before any data,
from the involution/adjacency structure and the observed confusion matrix
(6->2, 7->5 were the next largest collapses):
    1 <-> 2      6 <-> 3      7 <-> 4      5 -> 6
All rival texts pass the prompt audit (no canonical World words, checked
mechanically like everything else).
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
from run_realization_pilot_s2 import (  # noqa: E402 — World instrument UNTOUCHED
    CANON, CELLS, CRITERIA, PROHIBITED, SEALED, STARVED, audit_prompt, normalize, r1b_copy,
)
from run_realization_pilot_e import PROHIB_PARAGRAPH  # noqa: E402
from run_confirmatory_generation import secondary_hits  # noqa: E402

AUTHOR_MODEL = "models/gemini-2.5-flash-lite"
N_PLANS, N_CANDIDATES, TRANSPORT_RETRIES = 4, 5, 2
PARSER_HASH = hashlib.sha256(inspect.getsource(normalize).encode()).hexdigest()[:16]

# FROZEN motive repair: terminal want + the close rival that must NOT satisfy.
MOTIVE = {
    "1": ("direct communion, nearness, participation, surrender — BEING-WITH the divine",
          "a complete explanation, doctrine, or intellectual answer. If the actor gains perfect "
          "understanding but no direct relation, the effort still fails"),
    "2": ("genuine comprehension — truly understanding why and how",
          "practical success, comfort, or acquisition achieved without understanding. If things "
          "go well but the actor still cannot explain why, the effort still fails"),
    "3": ("renewed vigor, health, and aliveness in themselves",
          "obtaining possessions or resources. If the actor acquires everything sought but their "
          "vitality is not restored, the effort still fails"),
    "4": ("genuine mutual companionship, belonging with another",
          "achievement, admiration, or pleasure without a mutual bond. If the actor is admired "
          "or gratified but remains unaccompanied, the effort still fails"),
    "5": ("their will effectively directing events and others",
          "merely possessing resources or being liked. If the actor is wealthy and popular but "
          "cannot make outcomes bend to their intention, the effort still fails"),
    "6": ("acquiring, consuming, possessing, preserving, or gaining access to a concrete resource",
          "improved energy, comfort, or bodily condition. If the actor feels better but never "
          "obtains or uses the resource itself, the effort still fails"),
    "7": ("consummation, fertility, conception, lineage continuation — an unmistakably "
          "generative union",
          "affection, loyalty, or intimacy alone. If the relationship becomes deeply loving but "
          "never reaches the generative outcome, the effort still fails"),
}

TMPL = """You are writing diagnostic vignettes for a behavioural-inference benchmark.

THE ACTOR'S TERMINAL WANT: {want}

THE CLOSE RIVAL THAT MUST NOT SATISFY: {rival}.
The scenario must OFFER the rival outcome and show the actor treating it as
insufficient — through a decision, not through narration about feelings.

THE DECISIVE LOCATION RULE: {criterion}
The scenario must make that location recoverable through the actor's method, the
obstacle, the diagnostic decision, and the success condition — never by naming it.

REALIZATION FAMILY {rf_id}: build the causal spine around {family_text}.

MOTIVE BLOCK — all five must be present and legible in the story:
1. the final condition the actor truly wants;
2. the close-rival outcome that would NOT satisfy them (offered, then declined
   or found hollow);
3. the obstacle preventing the true outcome;
4. one diagnostic choice that reveals the motive;
5. the exact result that counts as success.

CRAFT RULES:
- Four aligned anchors: motive, method, obstacle, success criterion.
- At least three independent diagnostic signals; never one load-bearing keyword.
- No labels, no category names, no jargon; ordinary settings; every detail earns
  its place; 80-160 words per scenario, naturalistic prose.
- The rival rejection must appear as a concrete decision or an explicit success
  test, never as definition-shaped exposition.

This is plan {plan_idx} of {nplans} — use a different actor, setting, stakes,
conflict and outcome than a typical treatment.

Return ONLY JSON: {{"candidates": ["scenario one", "scenario two", "scenario three",
"scenario four", "scenario five"]}}
Exactly {ncand} candidate scenarios, each a plain string."""


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    import google.generativeai as genai

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY required")
    genai.configure(api_key=key)
    canon = json.loads(CANON.read_text(encoding="utf-8"))
    sealed = json.loads(SEALED.read_text(encoding="utf-8"))["families"]
    train_by_world, held_by_world = {}, {}
    for rf, m in sorted(sealed.items()):
        (held_by_world if m["heldout"] else train_by_world).setdefault(m["world"], []).append(rf)

    # audit every new author-facing string up front, fail closed
    for want, rival in MOTIVE.values():
        audit_prompt(want)
        audit_prompt(rival)

    cfg = {
        "phase": "S3-1", "prereg": "PREREG_S3_LOCK.md",
        "changed": "ONLY the motive block (five elements, rejected close rival)",
        "unchanged": ["World grammar", "universal instruction", "regex+morphology audit",
                      "realization families and splits", "logging", "quarantine"],
        "frozen_rival_map": {d: {"want": w, "rival": r} for d, (w, r) in MOTIVE.items()},
        "rival_map_provenance": "owner-specified for 1/6/7; 2/3/4/5 defined pre-data from "
                                "involution adjacency and the observed confusion matrix",
        "baselines_to_beat": {"train_joint_full_canon": 0.6181, "P12": 0.6833,
                              "P63": 0.7333, "P74": 0.5833},
        "author_model": AUTHOR_MODEL, "prompt_hash": sha(TMPL), "parser_hash": PARSER_HASH,
    }
    (HERE / "s3_1_frozen_config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True),
                                                  encoding="utf-8")
    print("S3-1 motive-repaired generation (QUARANTINED)")
    print(f"  baselines to beat: {cfg['baselines_to_beat']}\n")

    model = genai.GenerativeModel(AUTHOR_MODEL)
    rec_path = HERE / "s3_1_records.json"
    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else []
    done = {(r["code"], r["plan_idx"]) for r in rec}

    for code in CELLS:
        w, d = code[1], code[0]
        for plan_idx in range(N_PLANS):
            if (code, plan_idx) in done:
                continue
            heldout = plan_idx == N_PLANS - 1
            pool = held_by_world[w] if heldout else train_by_world[w]
            rf = pool[plan_idx % len(pool)]
            want, rival = MOTIVE[d]
            body = TMPL.format(want=want, rival=rival, criterion=CRITERIA[w], rf_id=rf,
                               family_text=sealed[rf]["author_text"],
                               plan_idx=plan_idx + 1, nplans=N_PLANS, ncand=N_CANDIDATES)
            audit_prompt(body)
            prompt = body + PROHIB_PARAGRAPH
            cands, retry_hist, raw = [], [], ""
            for attempt in range(1, TRANSPORT_RETRIES + 2):
                try:
                    resp = model.generate_content(
                        prompt, generation_config={"temperature": 0.95, "top_p": 0.95,
                                                   "max_output_tokens": 8192,
                                                   "response_mime_type": "application/json"},
                        request_options={"timeout": 240})
                    raw = resp.text
                    cands = [c for c in normalize(json.loads(raw)) if c.strip()]
                    if cands:
                        break
                    retry_hist.append({"attempt": attempt, "error": "no_candidates"})
                except Exception as exc:  # noqa: BLE001
                    retry_hist.append({"attempt": attempt, "error": type(exc).__name__})
                    time.sleep(2 * attempt)
            with open(HERE / "calls_s3_1.jsonl", "a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "phase": "S3-1", "model": AUTHOR_MODEL, "code": code,
                    "plan_idx": plan_idx, "rf_id": rf, "heldout": heldout,
                    "prompt": prompt, "prompt_sha256": sha(prompt),
                    "response_raw": raw, "response_sha256": sha(raw),
                    "parser_hash": PARSER_HASH, "retry_history": retry_hist,
                    "normalized_candidates": cands[:N_CANDIDATES]}, ensure_ascii=False) + "\n")
            n_sel = 0
            for i, text in enumerate(cands[:N_CANDIDATES]):
                hits = PROHIBITED.findall(text)
                keep = (not hits) and n_sel < 3
                if keep:
                    n_sel += 1
                rec.append({"code": code, "plan_idx": plan_idx, "candidate_index": i + 1,
                            "arm_group": "starved" if code in STARVED else "control",
                            "world": w, "drive": d, "rf_id": rf, "heldout": heldout,
                            "text": text, "leaked_primary": bool(hits),
                            "leak_words_primary": sorted({h[0].lower() for h in hits}),
                            "leak_words_secondary": secondary_hits(text),
                            "selected": keep,
                            "r1b": round(r1b_copy(text, CRITERIA[w] + " " + want + " " + rival +
                                                  " " + sealed[rf]["author_text"]), 4)})
            if not cands:
                rec.append({"code": code, "plan_idx": plan_idx, "generation_failed": True,
                            "retry_history": retry_hist})
            rec_path.write_text(json.dumps(rec, indent=1), encoding="utf-8")
            print(f"  {code} p{plan_idx} {'H' if heldout else 'T'} [{rf}]: "
                  f"{sum(1 for r in rec if r.get('candidate_index') and r['code'] == code and r['plan_idx'] == plan_idx and r['leaked_primary'])}"
                  f"/{len(cands[:N_CANDIDATES])} leaked", flush=True)

    rows = [r for r in rec if r.get("candidate_index")]
    p = sum(r["leaked_primary"] for r in rows) / max(1, len(rows))
    s = sum(bool(r["leak_words_secondary"]) for r in rows) / max(1, len(rows))
    r1b = sum(r["r1b"] for r in rows) / max(1, len(rows))
    from collections import defaultdict
    fam = defaultdict(int)
    for r in rows:
        if r["selected"]:
            fam[(r["code"], r["plan_idx"])] += 1
    print(f"\nS3-1 generation: {len(rows)} candidates  primary {p:.4f}  secondary {s:.4f}  "
          f"R1B {r1b:.4f}  complete families {sum(1 for v in fam.values() if v == 3)}/64")
    print("NEXT: full-canon judging + grouped gate + P12/P63/P74 via the S3-0 eval apparatus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
