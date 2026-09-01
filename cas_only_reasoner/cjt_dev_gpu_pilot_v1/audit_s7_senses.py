"""audit_s7_senses.py -- CJT-DEV-P1.2 required 16-sense audit (owner ruling
S7Delta.2 point 3 / P1.2). Deterministic, WordNet-only + the frozen generator
templates. Non-claim-bearing development artifact.

For every registered surface verb: the EXACT construction clause template
(verbatim from tools/generate_construction_gold.py TEMPLATES), the frozen
context sense, its gloss, the context-correct base lemma, a lemma-membership
check (base lemma in synset lemmas), the plausible alternative senses
(including particle-verb lemmas like back_away / break_down), and an
adjudicated verdict with written rationale.

Verdict law: CORRECT (unambiguous fit), DEFENSIBLE (fits; reasonable
alternatives exist and are recorded), BEST_AVAILABLE (no closer sense exists
for this lemma), ERROR (the frozen sense has a genuinely different meaning
than the clause use -- e.g. lie.v.05 'tell an untruth').
Per the ruling: only a genuine ERROR forces a rebuilt v3 profile table;
otherwise V3 reuses the v2 profiles byte-for-byte.

Writes S7_SENSE_AUDIT.json.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (frozen sense, exact generator template, context base lemma, verdict, rationale)
ROWS = {
    "drawn": ("attract.v.01", "{m} was drawn to {i}.", "draw", "CORRECT",
              "passive 'was drawn to' = attracted toward; attract.v.01 lemmas "
              "include draw; gloss 'direct toward itself by psychological "
              "power' is the exact clause meaning"),
    "pulled": ("attract.v.01", "{i} pulled {m} toward it.", "pull", "CORRECT",
               "figurative pull-toward; attract.v.01 lemmas include pull; same "
               "attraction dynamic from the idea's side"),
    "felt": ("feel.v.01", "{m} felt an unmistakable pull toward {i}.", "feel",
             "CORRECT", "undergo an emotional sensation -- the mind "
             "experiences the pull; matches exactly"),
    "captured": ("capture.v.02", "the appeal of {i} captured {m} completely.",
                 "capture", "CORRECT",
                 "gloss IS 'attract; cause to be enamored' (captivate); the "
                 "clause subject is 'the appeal of {i}'"),
    "withdrew": ("withdraw.v.01", "{m} withdrew from {i}.", "withdraw",
                 "CORRECT", "'pull back or move away or backward' -- the "
                 "figurative move-away from the idea"),
    "repelled": ("repel.v.02", "{i} repelled {m} from the start.", "repel",
                 "CORRECT", "'be repellent to; cause aversion in' -- the idea "
                 "causes aversion in the mind; exact"),
    "recoiled": ("flinch.v.01", "{m} recoiled whenever {i} came up.", "recoil",
                 "CORRECT", "'draw back, as with fear or pain' -- exact"),
    "backed": ("back.v.02", "faced with {i}, {m} backed away.", "back",
               "DEFENSIBLE",
               "back.v.02 'travel backward' (verb.motion) is the "
               "physical-metaphor reading of the retreat. Particle "
               "alternative recorded: back_away IS a WordNet lemma, in "
               "retreat.v.04 'make a retreat from an earlier commitment or "
               "activity' (verb.communication) -- the commitment-abandonment "
               "reading. The frozen motion sense is register-consistent with "
               "the family's other frozen aversion senses (withdraw.v.01, "
               "flinch.v.01, both verb.motion); back.v.04 is "
               "transitive-causative and does not fit"),
    "broke": ("break.v.02", "{i} broke down into {p1}, {p2}, and {p3}.",
              "break", "DEFENSIBLE",
              "break.v.02 'become separated into pieces or fragments' is the "
              "decomposition-into-parts meaning. Particle alternative "
              "recorded: break_down appears in decompose.v.01 'separate "
              "(substances) into constituent elements or parts' -- "
              "near-synonymous gloss, an equally fitting anchor; also in "
              "analyze.v.02 (agentive analysis) and several "
              "failure/collapse senses that do not fit. The frozen v.02 "
              "and decompose.v.01 share the same core meaning, so this is "
              "not a sense ERROR"),
    "lay": ("lie.v.01", "inside {i} lay {p1}, {p2}, and {p3}.", "lie",
            "CORRECT",
            "'inside X lay parts' = the parts were located/situated inside; "
            "the surface 'lay' is the PAST TENSE OF LIE (be situated), not "
            "the transitive lay/put -- exactly why the context-sense policy "
            "differs from S7-H's primary-sense-of-surface-lemma policy "
            "(which anchored on put.v.01)"),
    "split": ("divide.v.01", "{i} could be split into {p1}, {p2}, and {p3}.",
              "split", "CORRECT",
              "'separate into parts or portions' -- exact; cleave.v.01 is "
              "tool-cutting, not abstract partition"),
    "made": ("constitute.v.01", "three strands made up {i}: {p1}, {p2}, and "
             "{p3}.", "make_up", "CORRECT",
             "the surface is the particle verb 'made up' = compose/constitute; "
             "constitute.v.01 lemmas include make_up; gloss 'form or compose' "
             "is exact"),
    "brought": ("bring.v.03", "{a} brought {b} to {m}'s mind.", "bring",
                "DEFENSIBLE",
                "bring.v.03 'cause to happen or to occur as a consequence' "
                "captures the trigger-effect semantics ({b} surfaces as a "
                "consequence of {a}); bring.v.01 (take somewhere) and "
                "bring.v.02 (cause to come into a state) are the recorded "
                "alternatives under the location-metaphor reading"),
    "thought": ("think.v.01", "whenever {m} thought of {a}, {b} surfaced.",
                "think", "DEFENSIBLE",
                "'thought of {a}' = regarded/considered {a} (think.v.01 'judge "
                "or regard; look upon'); remember.v.01 (recall from memory) "
                "and think.v.05 (imagine or visualize) are recorded "
                "alternatives; the template does not force recall-from-memory, "
                "so v.01's consider/regard reading stands"),
    "reminded": ("remind.v.01", "{a} reminded {m} of {b}.", "remind",
                 "CORRECT", "'put in the mind of someone' -- the exact "
                 "associative-trigger meaning"),
    "summoned": ("summon.v.02", "for {m}, {a} always summoned {b}.", "summon",
                 "BEST_AVAILABLE",
                 "the clause means {a} calls {b} forth to mind. Lemma summon "
                 "has four verb senses: v.01 official citation, v.02 'ask to "
                 "come', muster.v.01 gather, mobilize.v.01 ready-for-action. "
                 "No evoke-type synset carries the lemma summon (evoke.v "
                 "lemmas: raise/conjure/invoke/call_forth...). v.02 'ask to "
                 "come' (figuratively, asking the idea to come) is the "
                 "closest available sense for this lemma"),
}


def main():
    from nltk.corpus import wordnet as wn
    audit = {}
    all_ok = True
    for v, (sname, clause, base, verdict, why) in ROWS.items():
        s = wn.synset(sname)
        lemmas = [l.name() for l in s.lemmas()]
        member = base in lemmas
        alts = [{"synset": a.name(), "gloss": a.definition()}
                for a in wn.synsets(base, "v")]
        row = {"surface_verb": v, "construction_clause_template": clause,
               "frozen_sense": sname, "gloss": s.definition(),
               "context_base_lemma": base, "lemma_membership": member,
               "synset_lemmas": lemmas,
               "alternative_senses_of_base_lemma": alts,
               "verdict": verdict, "rationale": why}
        if not member or verdict == "ERROR":
            all_ok = False
        audit[v] = row
        print(f"{v:9} {sname:16} member={member} verdict={verdict}")
    # particle-verb existence checks recorded once (referenced in rationales)
    particle = {"back_away_verb_synsets": [a.name() for a in
                                           wn.synsets("back_away", "v")],
                "break_down_verb_synsets": [a.name() for a in
                                            wn.synsets("break_down", "v")]}
    out = {"audit_id": "S7_SENSE_AUDIT", "amendment": "CJT-DEV-P1.2",
           "non_claim_bearing": True,
           "verdict": "AUDIT_PASS_NO_SENSE_CORRECTIONS" if all_ok
           else "AUDIT_FOUND_ERROR",
           "law": ("only a genuine ERROR forces a rebuilt v3 profile table; "
                   "DEFENSIBLE/BEST_AVAILABLE stand with recorded "
                   "alternatives. Result: V3 reuses the v2 profiles "
                   "byte-for-byte."),
           "sense_policy_disclosure": (
               "S7-H uses each SURFACE lemma's PRIMARY WordNet sense "
               "(bare-form/default lexical-category control; e.g. pull.v.01 "
               "for drawn/pulled, put.v.01 for lay); S7-DELTA uses these "
               "frozen CONSTRUCTION-CONTEXT senses (e.g. attract.v.01, "
               "lie.v.01). Their contrast is NOT a pure hard-vs-soft "
               "ablation unless the sense inventories are harmonized."),
           "particle_verb_checks": particle,
           "rows": audit}
    (HERE / "S7_SENSE_AUDIT.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\nVERDICT: {out['verdict']}")
    print(f"particle checks: {particle}")
    return 0 if all_ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
