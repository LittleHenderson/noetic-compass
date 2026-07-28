"""WORLD_REALIZATION_GRAMMAR_V1_PILOT_S2 — SILENT ENFORCEMENT.

The claim under test, per owner:
    Can the author express the World through context and causal structure
    WITHOUT NEEDING THE LABEL?
not:
    Can the author obey an avoidance instruction after being shown the
    forbidden concept?
Pilot v1 (VOID_APPARATUS_PROMPT_CONTAMINATION) demonstrated the second task
creates a priming channel capable of overwhelming the first.

Design:
  - the author sees ONLY the behavioural criterion + a realization-family
    description + craft rules. No canonical World name. No prohibition. No
    forbidden-word list. The regex operates PRIVATELY after generation.
  - all cell/world/drive/family metadata is RUNNER-OWNED, attached
    deterministically. The author never echoes experiment metadata.
  - realization families travel as opaque RF-IDs; the semantic mapping lives
    in a SEALED manifest never shown downstream.
  - MECHANICAL PROMPT AUDIT before every send: the assembled prompt must not
    contain a canonical World word. Substring check for spiritual/physical/
    emotional (compounds like 'nonphysical' and 'metaphysical' are priming
    channels — pilot v1 proved it); word-boundary check for 'mental' because
    the '-mental' suffix appears in innocent English (fundamental, elemental).
    Asymmetry disclosed here and in the lock.
  - rejected candidates are never edited, stripped, or explained to the
    author. Retries are transport-only, with no content-specific message.
  - R1B criterion-copy diagnostic: overlap between each candidate and its
    criterion + family text — reveals copying-the-grammar (the P5 class of
    defect) without banning ordinary words.

DISCLOSED CONSEQUENCE OF SILENT ENFORCEMENT: the full owner scenario spec and
the canonical Foundation definitions CANNOT be shown to the author — both are
saturated with canonical World words and would fail the audit. The author
receives the drive text (audited clean) + criterion + a condensed craft block.
This is a real reduction in author-side context and is recorded, not hidden.

Same 16 frozen cells, same 4x5 budget, same R1-R6. QUARANTINED from TKS_672_V3.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CANON = REPO / "docs/working/gate2_closure/matched_ab_20260726/tootra_28_full_definitions.json"
SEALED = HERE / "SEALED_realization_family_manifest.json"

AUTHOR_MODEL = "models/gemini-2.5-flash-lite"
N_PLANS, N_CANDIDATES = 4, 5
TRANSPORT_RETRIES = 2
PROHIBITED = re.compile(r"\b(spiritual(ly)?|mental(ly)?|emotional(ly)?|physical(ly)?)\b", re.I)

PAIRS = [("1d", "1b"), ("2a", "2b"), ("5d", "5b"), ("6a", "6c"),
         ("6b", "6d"), ("7a", "7b"), ("7c", "2c"), ("7d", "3d")]
STARVED = [p[0] for p in PAIRS]
CONTROLS = [p[1] for p in PAIRS]
CELLS = STARVED + CONTROLS

# Author-facing criteria. NO LABELS. Audited before use.
CRITERIA = {
    "a": "the decisive motive, authority, relationship, or success condition exists beyond "
         "any ordinary material, informational, or felt outcome",
    "b": "the decisive change occurs in how something is represented, understood, or "
         "organized in thought",
    "c": "the decisive change occurs in experienced value or relation — in what is felt "
         "toward someone or something",
    "d": "the decisive change occurs in bodily, spatial, object-based, consumptive, "
         "constructive, or directly operational reality",
}

TMPL = """You are writing diagnostic vignettes for a behavioural-inference benchmark.

THE ACTOR'S FUNDAMENTAL WANT: {drive}

THE DECISIVE LOCATION RULE: {criterion}
The scenario must make that location recoverable through the actor's method, the
obstacle, the diagnostic decision, and the success condition — never by naming it.

REALIZATION FAMILY {rf_id}: build the causal spine around {family_text}.

CRAFT RULES:
- Four aligned anchors: motive, method, obstacle, and success criterion must all
  point the same way.
- Include one decision or sacrifice that exposes the actor's priority, and one
  tempting close alternative the actor declines.
- At least three independent diagnostic signals; never one load-bearing keyword.
- No labels, no category names, no jargon; ordinary settings (workplace, family,
  medicine, sport, community, finance); every detail must earn its place.
- 80 to 160 words per scenario, naturalistic prose.

This is plan {plan_idx} of {nplans} for this assignment — use a different actor,
setting, stakes, conflict and outcome than a typical treatment would.

Return ONLY JSON: {{"candidates": ["scenario one", "scenario two", "scenario three",
"scenario four", "scenario five"]}}
Exactly {ncand} candidate scenarios, each a plain string."""


def audit_prompt(p: str) -> None:
    """MECHANICAL, runs before every send. Fails closed."""
    low = p.lower()
    bad = []
    if PROHIBITED.search(p):
        bad.append("word-boundary canonical World word")
    for s in ("spiritual", "physical", "emotional"):     # substring: compounds prime
        if s in low:
            bad.append(f"substring:{s}")
    if re.search(r"\bmental(ly)?\b", low):               # boundary-only: '-mental' suffixes
        bad.append("mental")
    if bad:
        raise SystemExit(f"PROMPT AUDIT FAILED — {bad}. Nothing was sent.")


def normalize(obj):
    if isinstance(obj, list):
        return [x if isinstance(x, str) else str(x.get("scenario", "")) for x in obj]
    if isinstance(obj, dict):
        for k in ("candidates", "scenarios", "items"):
            if isinstance(obj.get(k), list):
                return normalize(obj[k])
    return []


def r1b_copy(text: str, source: str) -> float:
    """Recall of distinctive source words (len>=5) in the candidate. Diagnostic only."""
    stop = {"their", "about", "would", "could", "there", "which", "something", "someone",
            "toward", "through", "change", "occurs", "decisive"}
    src = {w for w in re.findall(r"[a-z]+", source.lower()) if len(w) >= 5} - stop
    if not src:
        return 0.0
    got = set(re.findall(r"[a-z]+", text.lower()))
    return len(src & got) / len(src)


def main() -> int:
    import google.generativeai as genai

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY required")
    genai.configure(api_key=key)
    canon = json.loads(CANON.read_text(encoding="utf-8"))
    drives = canon["drive_map"]
    sealed = json.loads(SEALED.read_text(encoding="utf-8"))["families"]

    # runner-owned deterministic family assignment: TRAIN families only, rotated
    train_by_world = {}
    for rf, m in sorted(sealed.items()):
        if not m["heldout"]:
            train_by_world.setdefault(m["world"], []).append(rf)

    # audit every author-facing string once up front, fail closed
    for w, crit in CRITERIA.items():
        audit_prompt(crit)
    for rf, m in sealed.items():
        audit_prompt(m["author_text"])
    for d in drives.values():
        audit_prompt(d)

    cfg = {
        "design": "WORLD_REALIZATION_GRAMMAR_V1_PILOT_S2",
        "enforcement": "SILENT — author never sees a World name, a prohibition, or a word list; "
                       "regex operates privately after generation",
        "claim_under_test": "expression through context and causal structure, not instructed avoidance",
        "instructed_avoidance_arm": "DEFERRED — separate quarantined diagnostic, never mixed "
                                    "into a claim-bearing corpus",
        "metadata_ownership": "runner-owned; author returns only candidate strings",
        "family_ids": "opaque RF-IDs; mapping sealed in SEALED_realization_family_manifest.json",
        "prompt_audit": "substring for spiritual/physical/emotional (compounds prime), "
                        "word-boundary for mental ('-mental' suffix is innocent English) — "
                        "asymmetry disclosed",
        "disclosed_context_reduction": "owner spec and canonical definitions are saturated with "
                                       "World words and CANNOT be shown under silent enforcement; "
                                       "author receives drive text + criterion + condensed craft "
                                       "block only",
        "frozen_pairs": PAIRS, "n_plans": N_PLANS, "n_candidates": N_CANDIDATES,
        "v2_baseline_leak": {"5d": 0.350, "7c": 0.375, "6a": 0.300, "7a": 0.300, "1d": 0.275,
                             "overall": 0.142},
        "pilot_v1": "VOID_APPARATUS_PROMPT_CONTAMINATION — its 0.4058 is apparatus evidence only",
        "prompt_hash": hashlib.sha256(TMPL.encode()).hexdigest()[:32],
        "quarantine": "no item may enter TKS_672_V3",
    }
    (HERE / "pilot_s2_frozen_config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True),
                                                      encoding="utf-8")
    print("WORLD_REALIZATION_GRAMMAR_V1_PILOT_S2  (SILENT ENFORCEMENT, QUARANTINED)")
    print(f"  16 cells / {N_PLANS} plans / {N_CANDIDATES} candidates = "
          f"{len(CELLS)*N_PLANS*N_CANDIDATES}\n")

    model = genai.GenerativeModel(AUTHOR_MODEL)
    path = HERE / "pilot_s2_records.json"
    rec = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    done = {(r["code"], r["plan_idx"]) for r in rec}

    for code in CELLS:
        w = code[1]
        fams = train_by_world[w]
        for plan_idx in range(N_PLANS):
            if (code, plan_idx) in done:
                continue
            rf = fams[plan_idx % len(fams)]              # deterministic, runner-owned
            fam_text = sealed[rf]["author_text"]
            prompt = TMPL.format(drive=drives[code[0]], criterion=CRITERIA[w],
                                 rf_id=rf, family_text=fam_text,
                                 plan_idx=plan_idx + 1, nplans=N_PLANS, ncand=N_CANDIDATES)
            audit_prompt(prompt)                          # mechanical, every send
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
                except Exception as exc:  # noqa: BLE001 — transport only, no content message
                    last, retries = type(exc).__name__, retries + 1
                    time.sleep(2 * attempt)
            n_leak = 0
            for i, text in enumerate(cands[:N_CANDIDATES]):
                hits = PROHIBITED.findall(text)
                n_leak += bool(hits)
                rec.append({
                    "code": code, "plan_idx": plan_idx, "candidate_index": i + 1,
                    "arm": "starved" if code in STARVED else "control",
                    "world": w, "drive": code[0],
                    "rf_id": rf,                                   # opaque; runner-attached
                    "text": text, "n_words": len(text.split()),
                    "leaked": bool(hits),
                    "leak_words": sorted({h[0].lower() for h in hits}) if hits else [],
                    "r1b_criterion_copy": round(r1b_copy(text, CRITERIA[w] + " " + fam_text), 4),
                    "retry_count": retries,
                })
            if not cands:
                rec.append({"code": code, "plan_idx": plan_idx,
                            "arm": "starved" if code in STARVED else "control",
                            "generation_failed": last, "retry_count": retries})
            path.write_text(json.dumps(rec, indent=1), encoding="utf-8")
            print(f"  {code} plan {plan_idx} [{rf}]: {n_leak}/{len(cands[:N_CANDIDATES])} leaked",
                  flush=True)

    # ---- R1 + R1B readout (this script decides R1 only)
    from collections import defaultdict
    cand = [r for r in rec if r.get("candidate_index")]
    by = defaultdict(lambda: [0, 0])
    for r in cand:
        by[r["code"]][1] += 1
        by[r["code"]][0] += r["leaked"]
    v2 = cfg["v2_baseline_leak"]
    print("\nR1 — leak vs v2 baseline (starved):")
    for c in STARVED:
        n, t = by[c]
        cur = n / t if t else float("nan")
        base = v2.get(c)
        print(f"   {c}: pilot {cur:.3f}" + (f"   v2 {base:.3f}  {cur-base:+.3f}" if base else ""))
    print("controls:")
    for c in CONTROLS:
        n, t = by[c]
        print(f"   {c}: {n/t if t else float('nan'):.3f}")
    overall = sum(r["leaked"] for r in cand) / max(1, len(cand))
    copy_mean = sum(r["r1b_criterion_copy"] for r in cand) / max(1, len(cand))
    print(f"\n  overall leak {overall:.4f}   v2 {v2['overall']:.4f}   {overall-v2['overall']:+.4f}")
    print(f"  R1B criterion-copy mean recall {copy_mean:.4f}  (diagnostic — reveals copying, "
          f"bans nothing)")
    print("\nThis script decides R1 only. R2-R6 need the June gate, blind judges, held-out "
          "transfer, lexical baselines, and a second author.")
    json.dump({"per_cell": {c: {"leaked": by[c][0], "total": by[c][1]} for c in CELLS},
               "overall_leak": overall, "v2_overall": v2["overall"],
               "r1b_copy_mean": copy_mean, "decides": "R1 (R1B diagnostic)"},
              open(HERE / "pilot_s2_r1.json", "w"), indent=2, sort_keys=True)
    print("WROTE pilot_s2_r1.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
