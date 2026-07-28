"""TRACK_B_TKS_672_CORPUS v2 — full-corpus regeneration under ONE frozen process.

NOT a backfill. All 224 families (28 x 8) are generated under this single lock.

WHY NOT BACKFILL: "backfill only the starved Foundations" makes generation cohort
correlate with Foundation — well-supplied Foundations keep v1 text, starved ones
get v2 text. Even at the same model and prompt, later batches can carry stylistic
signatures, and a classifier could learn "this sounds like the v2 batch, therefore
probably 6a." That is a lexical shortcut through PRODUCTION HISTORY rather than
through World words. One corpus, one process, one cohort.

FROZEN CANDIDATE BUDGET — exceeding it is authoring-yield FAILURE, not a reason
to keep generating:
    plans per Foundation        8
    candidate siblings per plan 5
    accepted siblings per plan  3
    transport retries           2 (fixed)
    SEMANTIC RETRIES            PROHIBITED

SELECTION RULE — the only safe form of "first three passing":
    selection uses the frozen DIRECT-LEAK REGEX and nothing else.
    A selected sibling is NEVER replaced by candidate 4 or 5 because it scored
    better on a surface gate or a judge. That would turn the spare candidates
    into evaluator-directed search. All five candidates are retained in evidence.

v1 is retained permanently as NOT_FROZEN / NOT_SCORED / AUTHORING-YIELD EVIDENCE.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
JUNE = REPO / "docs" / "working" / "mtc_f28_goemotions_20260615"
CANON = REPO / "docs/working/gate2_closure/matched_ab_20260726/tootra_28_full_definitions.json"
SPEC = REPO / "docs/working/gate2_closure/matched_ab_20260726/owner_scenario_spec.md"
sys.path.insert(0, str(JUNE))

COHORT = "v2"                    # recorded on EVERY item
AUTHOR_MODEL = "models/gemini-2.5-flash-lite"
TEMPERATURE, TOP_P = 0.95, 0.95
N_PLANS, N_CANDIDATES, N_KEEP = 8, 5, 3
TRANSPORT_RETRIES = 2
SURFACE_THRESHOLD = 0.60
LENGTH_RANGE = (80, 160)
WORLDS = {"a": "Spiritual", "b": "Mental", "c": "Emotional", "d": "Physical"}
PROHIBITED = re.compile(r"\b(spiritual(ly)?|mental(ly)?|emotional(ly)?|physical(ly)?)\b", re.I)

BOUNDARY_RUBRIC = {
    "4a": "bond located in a spiritual ontology - soul lineage, nonphysical communion, "
          "mystical order, ancestor/entity relation, dissolution of metaphysical separation",
    "4c": "outcome is an affective bond - felt intimacy, vulnerability, affection, "
          "emotional safety, acceptance, shared feeling",
    "6a": "spiritual sustenance or sacred/etheric resource",
    "6b": "mental content, doctrine, thought-form, model, intellectual property",
    "6c": "feeling or comfort mediated by an object or possession",
    "6d": "tangible possession, food, consumption, property, material resource",
}

TMPL = """{spec}

---

CANONICAL TARGET (28 Foundations 1.0 - authoritative, never substituted):
  code {code} | World {world} | Drive {drive}
  Full definition: {definition}
{boundary}
Build ONE structured plan, then write {ncand} sibling vignettes from THAT SINGLE plan.
This is plan family {plan_idx} of {nplans} for this code and must be INDEPENDENT of
the others - different actor, setting, stakes, conflict, causal structure, decision
and outcome. NOT a paraphrase of another story.

ABSOLUTE PROHIBITION - these words must NOT appear anywhere:
    spiritual  spiritually  mental  mentally
    emotional  emotionally  physical  physically
Encode the World through behaviour, relationship and consequence instead.

MANDATORY SELF-CHECK before you return: re-read each of your {ncand} scenarios and
verify none contains any prohibited word. If one does, rewrite that scenario before
returning. Items containing them are discarded.

Return ONLY JSON:
{{"plan":{{"actor":"...","setting":"...","stakes":"...","conflict":"...",
  "causal_structure":"...","decision":"...","outcome":"..."}},
  "candidates":[{{"candidate_index":1,"scenario":"..."}}]}}

Exactly {ncand} candidates, each {lo}-{hi} words of naturalistic prose. No foundation
code, no Tootra terminology, no copied definition wording."""


def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def sha_str(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()


def leak_reason(text, code):
    hits = PROHIBITED.findall(text)
    if hits:
        return f"direct_world_label:{sorted({h[0].lower() for h in hits})}"
    n = len(text.split())
    if not (LENGTH_RANGE[0] - 20 <= n <= LENGTH_RANGE[1] + 40):
        return f"length_{n}"
    if re.search(rf"\b{re.escape(code)}\b", text, re.I):
        return "code_leak"
    if re.search(r"\bTootra\b|\bFoundation\b", text):
        return "terminology_leak"
    return None


def main() -> int:
    import google.generativeai as genai
    import surface_gate_f28_goemotions as june_gate

    if june_gate.THRESHOLD != SURFACE_THRESHOLD:
        raise SystemExit(f"June gate drift: {june_gate.THRESHOLD} != {SURFACE_THRESHOLD}")
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY required")
    genai.configure(api_key=key)

    canon = json.loads(CANON.read_text(encoding="utf-8"))
    defs, drives = canon["definitions"], canon["drive_map"]
    spec = SPEC.read_text(encoding="utf-8")

    cfg = {
        "track": "TRACK_B_TKS_672_CORPUS", "version": "v2", "cohort": COHORT,
        "supersedes": "v1 (513 accepted, 126/224 complete families) — retained as "
                      "NOT_FROZEN / NOT_SCORED / AUTHORING-YIELD EVIDENCE",
        "regeneration_scope": "FULL CORPUS under one process — NOT a backfill",
        "cohort_rationale": "backfill would make generation batch correlate with Foundation, "
                            "creating a lexical shortcut through production history",
        "author_model": AUTHOR_MODEL, "temperature": TEMPERATURE, "top_p": TOP_P,
        "author_prompt_hash": sha_str(TMPL + spec),
        "spec_sha256": sha_file(SPEC), "canon_sha256": sha_file(CANON),
        "june_gate_sha256": sha_file(JUNE / "surface_gate_f28_goemotions.py"),
        "surface_threshold": SURFACE_THRESHOLD,
        "candidate_budget": {"plans_per_foundation": N_PLANS,
                             "candidates_per_plan": N_CANDIDATES,
                             "accepted_per_plan": N_KEEP,
                             "transport_retries": TRANSPORT_RETRIES,
                             "semantic_retries": "PROHIBITED"},
        "budget_overrun_policy": "if any Foundation ends below 8 complete families, v2 FAILS "
                                 "authoring yield; extending requires a NEW successor lock",
        "selection_rule": "first 3 candidates passing the frozen DIRECT-LEAK REGEX, in frozen "
                          "generation order. A selected sibling is NEVER replaced by candidate "
                          "4 or 5 for a better surface score or judge prediction.",
        "all_candidates_retained": True,
        "prohibited_expressions": PROHIBITED.pattern,
        "june_gate_granularity": "the June surface gate is a corpus-level cross-validated "
                                 "measure, so it runs once over the completed selected corpus "
                                 "BEFORE freezing and BEFORE any readout — gating admission of "
                                 "the corpus, never a post-hoc audit of a scored result",
    }
    (HERE / "frozen_config_v2.json").write_text(json.dumps(cfg, indent=2, sort_keys=True),
                                                encoding="utf-8")
    print("v2 FROZEN CONFIG — full-corpus regeneration, cohort", COHORT)
    print(f"  budget {N_PLANS} plans x {N_CANDIDATES} candidates -> keep {N_KEEP}")
    print(f"  june gate {cfg['june_gate_sha256'][:16]} threshold {june_gate.THRESHOLD}\n")

    model = genai.GenerativeModel(AUTHOR_MODEL)
    path = HERE / "corpus_records_v2.json"
    records = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    done = {(r["foundation_code"], r["plan_family_id"]) for r in records}

    for code in sorted(defs):
        for plan_idx in range(N_PLANS):
            if (code, plan_idx) in done:
                continue
            boundary = (f"\nBOUNDARY RUBRIC (operational aid; does NOT rewrite canon):\n"
                        f"  {BOUNDARY_RUBRIC[code]}\n") if code in BOUNDARY_RUBRIC else ""
            prompt = TMPL.format(spec=spec, code=code, world=WORLDS[code[1]],
                                 drive=drives[code[0]], definition=defs[code],
                                 boundary=boundary, ncand=N_CANDIDATES, plan_idx=plan_idx,
                                 nplans=N_PLANS, lo=LENGTH_RANGE[0], hi=LENGTH_RANGE[1])
            got, retries, last = None, 0, ""
            for attempt in range(1, TRANSPORT_RETRIES + 2):
                try:
                    resp = model.generate_content(
                        prompt, generation_config={"temperature": TEMPERATURE, "top_p": TOP_P,
                                                   "max_output_tokens": 8192,
                                                   "response_mime_type": "application/json"},
                        request_options={"timeout": 240})
                    got = json.loads(resp.text)
                    break
                except Exception as exc:  # noqa: BLE001 — TRANSPORT ONLY
                    last, retries = type(exc).__name__, retries + 1
                    time.sleep(2 * attempt)

            cands = (got or {}).get("candidates", [])[:N_CANDIDATES]
            selected, family = 0, []
            for i, c in enumerate(cands):
                text = str(c.get("scenario", "")).strip()
                reason = leak_reason(text, code)
                keep = (reason is None) and selected < N_KEEP
                if keep:
                    selected += 1
                family.append({
                    "foundation_code": code, "plan_family_id": plan_idx,
                    "candidate_index": i + 1, "cohort": COHORT,
                    "text": text, "n_words": len(text.split()),
                    "regex_reason": reason,
                    "selected": keep,
                    "sibling_role": f"s{selected}" if keep else None,
                    "selection_rule": "first-3-regex-passing, frozen order",
                    "retry_count": retries,
                    "author_model": AUTHOR_MODEL,
                    "author_prompt_hash": cfg["author_prompt_hash"],
                    "author_seed": 20260727 + plan_idx,
                })
            if not cands:
                family.append({"foundation_code": code, "plan_family_id": plan_idx,
                               "cohort": COHORT, "selected": False,
                               "regex_reason": f"generation_failed:{last}",
                               "retry_count": retries})
            # FAMILY-LEVEL disposition: a family is complete only with N_KEEP siblings
            for r in family:
                r["family_complete"] = bool(selected == N_KEEP)
            records.extend(family)
            path.write_text(json.dumps(records, indent=1), encoding="utf-8")
            print(f"  {code} plan {plan_idx}: {selected}/{N_KEEP} selected "
                  f"from {len(cands)} candidates", flush=True)

    # ---- yield, always reported, all candidates counted
    from collections import Counter, defaultdict
    cand = [r for r in records if r.get("candidate_index")]
    sel = [r for r in cand if r.get("selected")]
    fam = defaultdict(int)
    for r in sel:
        fam[(r["foundation_code"], r["plan_family_id"])] += 1
    complete = Counter(c for (c, _), n in fam.items() if n == N_KEEP)
    per_found = [complete.get(c, 0) for c in sorted(defs)]
    starved = {c: complete.get(c, 0) for c in sorted(defs) if complete.get(c, 0) < N_PLANS}
    causes = Counter((r.get("regex_reason") or "pass").split(":")[0] for r in cand)

    yield_report = {
        "cohort": COHORT,
        "candidates_generated": len(cand), "selected": len(sel),
        "complete_families": sum(1 for n in fam.values() if n == N_KEEP),
        "complete_families_target": 28 * N_PLANS,
        "complete_families_per_foundation": {"min": min(per_found), "max": max(per_found)},
        "starved_foundations_below_8": starved,
        "candidate_dispositions": dict(causes),
        "world_leak_candidate_rate": round(
            sum(1 for r in cand if str(r.get("regex_reason", "")).startswith("direct_world"))
            / max(1, len(cand)), 4),
        "budget_verdict": "PASS" if not starved else "FAIL_AUTHORING_YIELD",
        "budget_overrun_policy": cfg["budget_overrun_policy"],
    }
    (HERE / "authoring_yield_v2.json").write_text(json.dumps(yield_report, indent=2,
                                                             sort_keys=True), encoding="utf-8")
    print("\nv2 AUTHORING YIELD")
    for k, v in yield_report.items():
        print(f"   {k}: {v}")
    if starved:
        print("\nBUDGET VERDICT: FAIL_AUTHORING_YIELD — extending requires a NEW successor lock.")
    else:
        print("\nNEXT: June surface gates over the selected corpus, then the independent "
              "recoverability test, then freeze. NO readout before the frozen manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
