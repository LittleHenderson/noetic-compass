#!/usr/bin/env python3
"""Gate 2 item 4 / build item B5 - PROPOSE the TKS<->CAS crosswalk.

This script emits a PROPOSAL, not a ratification. Every row carries its own
evidence with file:line. Rows that are not evidenced are marked CONTESTED and
are NOT filled in by position (registry future_agent_rule 2 forbids that).

Nothing is committed to git. No experiment is run.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS")
OUT = REPO / "docs" / "working" / "gate2_closure" / "item4_arms" / "proposed_tks_cas_crosswalk.json"
CREATED_AT = "2026-07-25T00:00:00Z"

CANON40 = Path(r"C:/Users/wakil/Downloads/Everthing-Tootra-TKS/canon/normalized/canon_elements_40.json")
OWNER = REPO / "docs" / "working" / "tks_owner_locked_definitions_20260603.json"
SCEN20B = Path(r"D:/tksCAS-archive/gpt_neox_20b_stage9_original_40e_closure_20260527/stage9_original_40e_scenarios_20260527.json")
BANK_BLOB = "165df0f6ff08c80fe1c42cd4412478527aabc934"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha_blob(rev: str) -> str:
    return hashlib.sha256(subprocess.run(["git", "show", rev], cwd=str(REPO),
                                         capture_output=True, check=True).stdout).hexdigest()


# --------------------------------------------------------------------------
# canonical CAS Noetic names, verbatim from Clarification 1 (name field only)
# --------------------------------------------------------------------------
CAS_NOETIC_NAME = {
    "^0": "Idea", "^1": "Mind", "^2": "Positive", "^3": "Negative", "^4": "Vibration",
    "^5": "Female", "^6": "Male", "^7": "Rhythm", "^8": "Above/Cause", "^9": "Below/Effect",
}
TKS_POS_TO_CAS_NOETIC = {1: "^1", 2: "^2", 3: "^3", 4: "^4", 5: "^5",
                         6: "^6", 7: "^7", 8: "^8", 9: "^9", 10: "^0"}
WORLD_LETTER_TO_NAME = {"A": "Spiritual", "B": "Mental", "C": "Emotional", "D": "Physical"}

# Assistant judgement of whether the owner's own element TITLE at each position
# carries the CAS Noetic name. Owner titles measured this session.
OWNER_TITLE_NOETIC_WORD = {1: "Mind", 2: "Positive", 3: "Negative", 4: "Vibration", 5: "Female",
                           6: "Male", 7: "Rhythm", 8: "Above", 9: "Below", 10: "Idea"}

# Per-row meaning check between the zero-based canon names and the CAS Noetic
# they would land on under the proposed index crosswalk. ASSISTANT JUDGEMENT.
INDEX_ROW_VERDICT = {
    # (canon symbol): (verdict, note)
    "A0": ("WEAK", "Canon 'Divine Blueprint / Life purpose, soul mission' is the weakest of the four "
                   "zero-position rows. The other three (B0 'a specific idea/concept', C0 'the idea of an "
                   "emotion', D0 'Concept of a physical thing') say 'idea/concept' outright; A0 does not. "
                   "It reads as ^0 Idea only by analogy to a blueprint being the idea of a life."),
    "D8": ("DIVERGENT", "Canon D8 'Physical Elevation / Status upgrade, material improvement' reads ^8 "
                        "SPATIALLY (higher up). The CAS definition of ^8 is CAUSAL ('An Idea that triggers a "
                        "different Idea'). A8/B8/C8 all read causally ('Divine Cause', 'Thought Trigger', "
                        "'Emotional Trigger'); only the D world switches to the spatial reading."),
    "D9": ("DIVERGENT", "Canon D9 'Physical Foundation / Foundation, base, basics' reads ^9 SPATIALLY "
                        "(lower down). The CAS definition of ^9 is CAUSAL ('The Idea brought to Mind by an "
                        "Above/Cause trigger'). A9/B9/C9 read causally ('Spiritual Effect', 'Cognitive "
                        "Response', 'Emotional Response'); only the D world switches."),
    "D5": ("WEAK", "Canon D5 'Physical Woman / Woman, female person' is a person-referent, not the CAS "
                   "^5 structural definition ('A Mind impregnated with an Idea'). Same for D6 'Physical Man'. "
                   "The owner titles at D5/D6 are 'Physical Female'/'Physical Male', so the NAME matches; the "
                   "canon DEFINITION does not carry the CAS structural content."),
    "D6": ("WEAK", "See D5. Canon 'Physical Man / Man, male person' is a person-referent, not ^6's "
                   "compositional definition."),
}


def build_noetic_rows(owner_titles: dict[str, str]) -> list[dict]:
    rows = []
    for pos in range(1, 11):
        cas = TKS_POS_TO_CAS_NOETIC[pos]
        word = OWNER_TITLE_NOETIC_WORD[pos]
        owner_examples = {f"{w}{pos}": owner_titles[f"{w}{pos}"] for w in "ABCD"}
        exact = CAS_NOETIC_NAME[cas] == word
        rows.append({
            "tks_noetic_position": pos,
            "proposed_cas_noetic": cas,
            "cas_noetic_name_clarification_1": CAS_NOETIC_NAME[cas],
            "verdict": "EVIDENCED",
            "name_match_kind": "EXACT" if exact else "PREFIX",
            "name_match_note": (
                "Owner title word and Clarification 1 name are byte-identical."
                if exact else
                f"Owner title word is '{word}'; Clarification 1 name is "
                f"'{CAS_NOETIC_NAME[cas]}'. The owner uses the short form; the canonical name adds the "
                f"causal suffix. Treated as the same Noetic. THIS IS AN ASSISTANT JUDGEMENT and is one of "
                f"the two rows where the owner's word is not byte-identical to the canonical name."
            ),
            "evidence": [
                {
                    "tier": "2 - exact field authority (OWNER SOURCE)",
                    "artifact": "docs/working/tks_owner_locked_definitions_20260603.json",
                    "sha256": "d3dac0ef5c94ccd768da0f18987846d8d0c0fa0b366e13dccc49c82252d2fc12",
                    "locator": f"tks_40_elements[*] where code in {sorted(owner_examples)}",
                    "what_it_says": owner_examples,
                    "why_it_is_evidence": (
                        f"The owner's own element titles put the word '{word}' at TKS position {pos} in all "
                        f"four worlds. Four independent owner-authored corroborations for this single row."
                    ),
                },
                {
                    "tier": "5 - repository-normative CAS authority",
                    "artifact": "docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md",
                    "sha256": "cda85c03273c47f7df9ac53258920b95ba7b3b2007b0e760856a67497f661880",
                    "locator": "Clarification 1, the 10 Noetic definition lines",
                    "what_it_says": f"{cas} (CO-{cas[1]}): {CAS_NOETIC_NAME[cas]}",
                    "why_it_is_evidence": "Supplies the CAS-side name this row lands on.",
                },
                {
                    "tier": "6 - CAS operational implementation",
                    "artifact": "noetic-compass-scaffold/noetic-compass/cas-native/belief/tks40_specificity.py",
                    "sha256": "16c2777c83f4e954487bf1dca831cc173e91b2a39966c41f231951696926a7a1",
                    "locator": f"LEGACY_ELEMENT_TO_NOETIC, line {39 + pos}",
                    "what_it_says": f"{pos}: {int(cas[1])},  # {word}",
                    "why_it_is_evidence": "Live code asserting exactly this row, with the same name in its comment.",
                },
                {
                    "tier": "8 - generated fixture (corroboration only)",
                    "artifact": "noetic-compass-scaffold/noetic-compass/research/cas_probe/stage9_elements_pilot_20260517.jsonl",
                    "git_blob_id": BANK_BLOB,
                    "branch": "experiment/cas-probe-pythia",
                    "locator": "fields element_noetic_tks / element_cas_noetic / element_noetic_name",
                    "what_it_says": f"element_noetic_tks={pos} -> element_cas_noetic='{cas}', element_noetic_name='{word}'",
                    "why_it_is_evidence": (
                        "The holdout bank the experiment scores on asserts this row on every one of its 8,320 "
                        "rows. Tier 8 cannot supply authority, only corroboration."
                    ),
                },
                {
                    "tier": "8 - generated fixture (corroboration only)",
                    "artifact": "D:/tksCAS-archive/gpt_neox_20b_stage9_original_40e_closure_20260527/stage9_original_40e_scenarios_20260527.json",
                    "locator": "metadata.legacy_element_noetic -> expected_cas_axes.noetic",
                    "what_it_says": f"legacy_element_noetic={pos} -> noetic='{cas}' (208 rows per world-position, 8,320 total)",
                    "why_it_is_evidence": (
                        "This is the label set behind the project's strongest live claim (95.625% GPT-NeoX-20B "
                        "layer-2 readout). Enumerated exhaustively this session."
                    ),
                },
                {
                    "tier": "6 - CAS operational implementation",
                    "artifact": "noetic-compass-scaffold/noetic-compass/research/cas_probe/build_stage9_elements_fixture.py",
                    "branch": "experiment/cas-probe-pythia",
                    "sha256": "16ef2fd005449cc0d4384f4bf53f39057fe19a37dc3c5aa3670ef57d95422f06",
                    "locator": "line 55",
                    "what_it_says": '_TKS_TO_CAS_NOETIC = {10: "^0", **{i: f"^{i}" for i in range(1, 10)}}',
                    "why_it_is_evidence": "The generator of the crosswalk assertion in the bank. Inline, unversioned, unhashed.",
                },
            ],
            "counter_evidence": [] if pos != 10 else [
                {
                    "what": "This is the ONLY non-identity row in the Noetic axis.",
                    "detail": (
                        "Positions 1..9 map to the same digit. Position 10 maps to ^0. Everything that could "
                        "go wrong in this axis is concentrated here, so it is worth stating what supports it "
                        "independently of the digit pattern: the owner's own titles A10/B10/C10/D10 are "
                        "'Spiritual Idea' / 'Mental Idea' / 'Emotional Idea' / 'Physical Idea', and "
                        "Clarification 1 names ^0 'Idea'. The zero-based TKS canon independently puts Idea at "
                        "position 0 (B0 'a specific idea/concept', C0 'the idea of an emotion', D0 'Concept of "
                        "a physical thing'). Three sources, two of them non-positional."
                    ),
                },
            ],
        })
    return rows


def build_world_rows() -> dict:
    """The World axis. This is where the crosswalk is NOT bijective, because two
    mutually-exclusive mappings are both live in the repo."""
    wd = {"A": "P", "B": "C", "C": "E", "D": "O"}
    wr = {"A": "T", "B": "A", "C": "f", "D": "E"}
    dom_name = {"P": "Principled", "C": "Cognitive", "E": "Evaluative", "O": "Operational"}
    reg_name = {"T": "Transcendent", "A": "Analytical", "f": "Affective", "E": "Embodied"}

    rows = []
    for w in "ABCD":
        rows.append({
            "tks_world_letter": w,
            "tks_world_name": WORLD_LETTER_TO_NAME[w],
            "tks_world_name_evidence": {
                "tier": "2 - exact field authority (OWNER SOURCE)",
                "artifact": "docs/working/tks_owner_locked_definitions_20260603.json",
                "locator": f"tks_28_foundations[*].title where code ends in '{w.lower()}'",
                "what_it_says": (
                    f"e.g. code '1{w.lower()}' title '{WORLD_LETTER_TO_NAME[w]} desire to be and be with God'; "
                    f"code '3{w.lower()}' title '{WORLD_LETTER_TO_NAME[w]} life, vitality, and health'. The same "
                    f"world word appears at all seven Foundation positions for this letter."
                ),
                "verdict": "EVIDENCED - the letter-to-world-NAME mapping is owner-sourced and is not in dispute.",
            },
            "hypothesis_H_WD_v1_world_to_cas_domain": {
                "proposed": wd[w],
                "proposed_name": dom_name[wd[w]],
                "verdict": "CONTESTED",
                "evidence_for": [
                    {
                        "tier": "6 - CAS operational implementation",
                        "artifact": "noetic-compass-scaffold/noetic-compass/cas-native/belief/tks40_specificity.py",
                        "sha256": "16c2777c83f4e954487bf1dca831cc173e91b2a39966c41f231951696926a7a1",
                        "locator": f"LEGACY_DOMAIN_TO_CAS, line {18 + 'ABCD'.index(w) + 1}",
                        "what_it_says": f'"{w}": "{wd[w]}",  # {WORLD_LETTER_TO_NAME[w]} -> ...',
                        "note": "Module docstring line 3-5 states the framing outright: 'The original TKS format "
                                "used four planes (A/B/C/D) ... CAS v7.x now represents the same 40-state surface "
                                "as ^noetic^domain over P/C/E/O domains'.",
                    },
                    {
                        "tier": "6 - CAS operational implementation (registry source active_python_notation_compiler)",
                        "artifact": "noetic-compass-scaffold/noetic-compass/api/notation/compiler.py",
                        "sha256": "8169188ad73df8fc3ca709731b3fb4ea07b2513d38d69cf66d22d64cfe88ff4c",
                        "locator": "lines 1214-1215",
                        "what_it_says": 'META_SET_ALIASES = {"Worlds": "Domains", ...}',
                        "note": (
                            "The executable compiler aliases the meta-set name 'Worlds' to 'Domains'. This is an "
                            "axis-level identity assertion, not a per-letter one - it does not say WHICH world "
                            "maps to which domain - but it is the strongest structural statement in the repo that "
                            "the World axis IS the Domain axis. sha256 matches the registry's recorded hash "
                            "(registry sources[] id active_python_notation_compiler)."
                        ),
                    },
                    {
                        "tier": "8 - generated fixture (corroboration only)",
                        "artifact": "D:/tksCAS-archive/gpt_neox_20b_stage9_original_40e_closure_20260527/stage9_original_40e_scenarios_20260527.json",
                        "sha256": "b2ad0481daaa1e5597a445a7ad8a9f2a4d108ead213818edd2ffb665af55b537",
                        "locator": "metadata.legacy_domain / legacy_domain_name -> expected_cas_axes.domain",
                        "what_it_says": f"legacy_domain='{w}', legacy_domain_name='{WORLD_LETTER_TO_NAME[w]}' -> domain='{wd[w]}' (2,080 rows for this world; 8,320 total)",
                        "note": (
                            "Enumerated exhaustively this session: exactly four (legacy_domain, legacy_domain_name, "
                            "domain) triples exist across all 8,320 scenarios. This is the label set behind the "
                            "95.625% GPT-NeoX-20B claim, so H-WD is ALREADY LOAD-BEARING in shipped labels - with "
                            "no crosswalk id, version, or hash recorded anywhere in the export."
                        ),
                    },
                ],
                "evidence_against": [
                    {
                        "artifact": "docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md",
                        "locator": "line 346 (Clarification 8)",
                        "what_it_says": (
                            "TKS encoded both cross-products with the same 4-Worlds axis. Reframed in secular "
                            "universal terms as 4 Registers (T, A, f, E), this axis applies consistently across "
                            "all CAS primitives - both Noetic-level (10 x 4 = 40 Cognitive-State-by-Register "
                            "combinations) and Drive-level (7 x 4 = 28 Drive-by-Register combinations)."
                        ),
                        "why_it_bites": (
                            "The highest-precedence artifact in this dispute says the 40-Element cross-product's "
                            "second factor is REGISTER, not Domain. If that is right, H-WD is wrong."
                        ),
                    },
                ],
            },
            "hypothesis_H_WR_v1_world_to_cas_register": {
                "proposed": wr[w],
                "proposed_name": reg_name[wr[w]],
                "verdict": "CONTESTED",
                "evidence_for": [
                    {
                        "tier": "5 - repository-normative CAS authority (registry source cas_foundational_clarifications)",
                        "artifact": "docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md",
                        "sha256": "cda85c03273c47f7df9ac53258920b95ba7b3b2007b0e760856a67497f661880",
                        "locator": "lines 343-348 (Clarification 8 section 8)",
                        "what_it_says": (
                            "'10 Noetics x 4 Worlds = 40 Elements' ... 'Reframed in secular universal terms as 4 "
                            "Registers (T, A, f, E), this axis applies consistently across all CAS primitives' ... "
                            "'CAS v7.4 lost the Worlds axis in translation from TKS. CAS v7.5 restores it on "
                            "secular universal basis as the Phenomenological Register.'"
                        ),
                        "note": (
                            "This is the HIGHEST-PRECEDENCE artifact asserting either hypothesis. But its registry "
                            "precedence line is scoped: 'Operational CAS authority for Noetic NAMES AND "
                            "DEFINITIONS' (registry line 47). It is not declared authority for the World axis. So "
                            "even the strongest evidence here is out of its own stated scope."
                        ),
                    },
                    {
                        "tier": "6 - CAS operational implementation",
                        "artifact": "noetic-compass-scaffold/noetic-compass/cas-native/belief/tks28_foundations.py",
                        "sha256": "7e57d80741e2f5ac3d6e5cfa0b3aa6e7fe9e3abeaf29ffe23419aca5aff83c55",
                        "locator": f"LEGACY_WORLD_TO_REGISTER, line {18 + 'ABCD'.index(w) + 1}",
                        "what_it_says": f'"{w.lower()}": "{wr[w]}",  # {WORLD_LETTER_TO_NAME[w]} -> {reg_name[wr[w]]}',
                        "note": (
                            "SIBLING FILE to tks40_specificity.py in the same package. One maps the four world "
                            "letters to Domains, the other maps the same four world letters to Registers. This is "
                            "registry known_conflict tks_world_to_cas_domain_and_register_collision, live, in two "
                            "adjacent files."
                        ),
                    },
                    {
                        "tier": "7 - pedagogical summary",
                        "artifact": "docs/reference/tks_28_foundations_translation_key.md",
                        "sha256": "5d3e87025cbba5a4ac7887063cf26603a2b16af10a7e8fffd0a597bfbb3444b7",
                        "locator": "lines 43-52 ('Register-to-World correspondence' table)",
                        "what_it_says": (
                            "|T Transcendent = 1st World (highest/most abstract); |A Analytical = 2nd World; "
                            "|f Affective = 3rd World; |E Embodied = 4th World (lowest/most concrete)."
                        ),
                        "note": (
                            "IMPORTANT: this table maps by WORLD ORDINAL POSITION, not by world letter or world "
                            "name. It never says 'Spiritual'. It reaches A->T only if the owner's letter order "
                            "A,B,C,D is also the abstraction order, which it separately asserts at line 52: 'This "
                            "World-order convention (high-abstraction at 1st, embodied at 4th) matches the Domain "
                            "descent ordering in CAS (P > C > E > O).' That sentence is the ONLY place in the repo "
                            "that links BOTH hypotheses to the same ordering - and it explicitly says the two axes "
                            "'do not collapse'."
                        ),
                    },
                    {
                        "tier": "6 - CAS operational implementation",
                        "artifact": "docs/working/mtc_f28_goemotions_20260615/*.py",
                        "locator": (
                            "build_confirmatory_authoring_plan_tks_original.py:31; "
                            "build_confirmatory_authoring_plan_tks_original_delink.py:25; "
                            "gate2_confirmatory_tks_original_blind.py:32"
                        ),
                        "what_it_says": f'WORLD_TO_REGISTER[...]  -> {WORLD_LETTER_TO_NAME[w]} = {reg_name[wr[w]]}',
                        "note": "Three separate scripts hardcode it with no version and no hash.",
                    },
                    {
                        "tier": "8 - generated fixture (corroboration only)",
                        "artifact": "noetic-compass-scaffold/noetic-compass/research/cas_probe/stage9_elements_pilot_20260517.jsonl",
                        "git_blob_id": BANK_BLOB,
                        "branch": "experiment/cas-probe-pythia",
                        "locator": "fields element_domain / element_domain_name / element_register / element_register_name",
                        "what_it_says": f"element_domain='{w}', element_domain_name='{WORLD_LETTER_TO_NAME[w]}', element_register='{wr[w]}', element_register_name='{reg_name[wr[w]]}'",
                        "note": (
                            "MEASURED THIS SESSION, and this correction matters: the Gate 2 item 4 holdout bank "
                            "carries NO CAS-DOMAIN FIELD AT ALL. Its field named 'element_domain' holds the TKS "
                            "WORLD LETTER (A/B/C/D), not a CAS domain letter (P/C/E/O). The only CAS second-factor "
                            "the bank asserts is Register. Generated by build_stage9_elements_fixture.py line 30 "
                            "(_DOMAIN_TO_REGISTER) on branch experiment/cas-probe-pythia."
                        ),
                    },
                ],
                "evidence_against": [
                    {
                        "artifact": "D:/tksCAS-archive/.../stage9_original_40e_scenarios_20260527.json",
                        "what_it_says": "8,320 rows binding legacy_domain -> expected_cas_axes.domain in P/C/E/O.",
                        "why_it_bites": "The shipped label set behind the strongest live claim used the DOMAIN reading, not the Register reading.",
                    },
                ],
            },
            "why_this_row_is_CONTESTED": (
                "Both hypotheses are asserted in live repo artifacts, and CAS_FOUNDATIONAL_CLARIFICATIONS.md "
                "lines 308-310 makes them mutually exclusive as identities: 'The Domain axis ... specifies the "
                "ontological-substrate level ... The Register axis ... specifies the operational character. These "
                "are independent. A Principled-domain operation can occur in any of the four registers ... all "
                "four being ^2^P operations.' If Domain does not determine Register, then a single World letter "
                "cannot be identical to both. At most one of H-WD and H-WR is an identity; the other is at best a "
                "correlation. Nothing on disk decides which. No owner-authored artifact states either one."
            ),
        })

    return {
        "axis_status": "CONTESTED - ALL FOUR ROWS",
        "what_is_evidenced": (
            "The world LETTER -> world NAME mapping (A/a=Spiritual, B/b=Mental, C/c=Emotional, D/d=Physical) is "
            "owner-sourced and is not in dispute."
        ),
        "what_is_contested": (
            "What the world maps ONTO in CAS. Two mutually exclusive hypotheses, both live, neither owner-ratified."
        ),
        "rows": rows,
        "registry_required_resolution_verbatim": (
            "Preserve native TKS World as its own field, define separate versioned World-to-Domain and "
            "World-to-Register hypotheses, and test each crosswalk as a distinct multi-head probe rather than "
            "declaring an identity."
        ),
        "assistant_reading_of_that_resolution": (
            "The registry's own required_resolution does NOT ask the owner to pick a winner. It asks for BOTH "
            "mappings to be preserved as separately-versioned, separately-tested hypotheses with the native World "
            "kept as its own field. This proposal is written to that shape: H_WD_v1 and H_WR_v1 are named and "
            "versioned separately, and neither is declared an identity. What the owner must still decide for "
            "Gate 2 item 4 is narrower: WHICH hypothesis binds Arm D's compile rule for THIS run."
        ),
    }


def build_index_rows(owner_titles, canon) -> dict:
    rows = []
    for w in "ABCD":
        for pos in range(1, 11):
            one = f"{w}{pos}"
            zero_digit = 0 if pos == 10 else pos
            zero = f"{w}{zero_digit}"
            c = canon[zero]
            verdict, note = INDEX_ROW_VERDICT.get(zero, ("CONSISTENT", ""))
            rows.append({
                "one_based_symbol_A1_D10": one,
                "owner_title": owner_titles[one],
                "zero_based_symbol_A0_D9": zero,
                "canon_name": c["name"],
                "canon_definition": c["definition"],
                "canon_world_field": c["world"],
                "world_letter_identical": c["world"] == w,
                "proposed_cas_noetic": TKS_POS_TO_CAS_NOETIC[pos],
                "meaning_check_verdict": verdict,
                "meaning_check_note": note or (
                    f"Canon '{c['name']}' and owner '{owner_titles[one]}' pick out the same "
                    f"{CAS_NOETIC_NAME[TKS_POS_TO_CAS_NOETIC[pos]]} role in the {WORLD_LETTER_TO_NAME[w]} world."
                ),
                "meaning_check_provenance": "ASSISTANT_JUDGEMENT - read from both files this session, not asserted by any artifact.",
            })
    n_con = sum(1 for r in rows if r["meaning_check_verdict"] == "CONSISTENT")
    n_weak = sum(1 for r in rows if r["meaning_check_verdict"] == "WEAK")
    n_div = sum(1 for r in rows if r["meaning_check_verdict"] == "DIVERGENT")
    return {
        "axis_status": f"EVIDENCED AS A CODE BIJECTION; MEANING-CONSISTENT ON {n_con} OF {len(rows)} ROWS "
                       f"({n_weak} WEAK, {n_div} DIVERGENT)",
        "what_this_axis_is": (
            "This is registry known_conflict #1, element_indexing_A1_D10_vs_A0_D9 (P0_SEMANTIC_IDENTITY), whose "
            "required_resolution is: 'Publish and test a bijective code-and-meaning crosswalk; store both "
            "source_symbol and normalized_index in every artifact.' It is a TKS<->TKS index crosswalk, not a "
            "TKS<->CAS one, but the registry names it as the blocker on binding 6 and the pre-registration names "
            "it as the reason Arm C is unavailable (GATE2_ITEM4_PREREGISTRATION.md:155)."
        ),
        "THE_KEY_FINDING": (
            "The remap is NOT a shift by one and is NOT a rotation. Measured this session by reading both files: "
            "the zero-based canon puts IDEA at position 0 (B0 'Thought Form / A specific idea/concept', C0 "
            "'Emotional Concept / The idea of an emotion', D0 'Physical Template / Concept of a physical thing') "
            "and the owner's one-based scheme puts IDEA at position 10 ('Mental Idea', 'Emotional Idea', "
            "'Physical Idea'). Every other position holds the SAME DIGIT in both schemes. So the crosswalk is "
            "IDENTITY on digits 1..9 and 10 <-> 0, with the world letter unchanged. That is exactly the same "
            "shape as the TKS-position -> CAS-Noetic map. The registry calls it 'a cyclic index remapping'; the "
            "measured structure is narrower and better-behaved than that phrase suggests, because 39 of the 40 "
            "codes are literally the same string."
        ),
        "why_that_matters_for_future_agent_rule_2": (
            "future_agent_rule 2 forbids remapping A1-D10 to A0-D9 BY POSITION without a tested crosswalk. The "
            "map proposed here is not derived from position: it is derived from the NAMES on both sides, read "
            "from both files. A pure by-position remap (A1->A0, A2->A1, ... A10->A9) would put Mind at Idea's "
            "slot and is REFUTED by the name evidence. Stating that explicitly is the point of this section: the "
            "naive positional remap the rule warns against is not merely unratified, it is measurably wrong."
        ),
        "counts": {"CONSISTENT": n_con, "WEAK": n_weak, "DIVERGENT": n_div, "total": len(rows)},
        "rows_needing_owner_attention": [
            r["zero_based_symbol_A0_D9"] for r in rows if r["meaning_check_verdict"] != "CONSISTENT"
        ],
        "caveat_that_is_not_smoothed_over": (
            "Code-bijectivity is trivial once the map is stated. MEANING-bijectivity is not established. The "
            "canon definitions are min 13 / mean 21.1 / max 36 chars of concrete gloss ('Woman, female person') "
            "against the owner's 71-686 char structural prose. Establishing that A5 in one scheme MEANS what A5 "
            "in the other means is a judgement I made by reading, not a test anyone ran. The registry asks for a "
            "'tested' crosswalk. Nothing here is tested. This is a proposal for the owner to ratify, and "
            "ratifying it does not make it tested."
        ),
        "does_this_unblock_arm_C": (
            "NO - and it must not be read that way. Even with this index crosswalk ratified, Arm C stays "
            "'unavailable' on the 40-Element axis for an INDEPENDENT reason the pre-registration already froze at "
            "section 2.3: canon_elements_40.json's definition field is min 13 / mean 21.1 / max 36 chars against "
            "Arm A's mean 196.2, a ~9x length mismatch that violates spec 8.2's 'prompt style and length "
            "distribution' hold-constant. The pre-registration is LOCKED and says Arm C is unavailable. Nothing "
            "in this proposal changes that, and the run stays five-armed."
        ),
        "rows": rows,
    }


def main() -> None:
    owner = json.loads(OWNER.read_text(encoding="utf-8"))
    owner_titles = {e["code"]: e["title"] for e in owner["tks_40_elements"]}
    canon = {r["symbol"]: r for r in json.loads(CANON40.read_text(encoding="utf-8"))}

    payload = {
        "schema_version": "gate2_item4_tks_cas_crosswalk_proposal_v1",
        "artifact_id": "TKS_CAS_CROSSWALK_PROPOSAL_v1",
        "status": "PROPOSAL_UNRATIFIED",
        "build_item": "B5",
        "design_id": "TKS-DEFCTX-40E-PRIMARY-v1",
        "created_at": CREATED_AT,
        "created_by": "assistant (Claude, Gate 2 item 4 build subagent)",
        "provenance": "ASSISTANT_COMPILED",
        "git_committed": False,
        "experiment_run": False,

        "READ_THIS_FIRST": {
            "what_this_is": (
                "A PROPOSAL, so that the owner ratifies or corrects rather than designs from scratch. Every row "
                "below carries the repo evidence that supports it, with file and line. Rows with no evidence, or "
                "with conflicting evidence, are marked CONTESTED and are LEFT EMPTY. They are not filled in by "
                "position."
            ),
            "what_this_is_NOT": [
                "Not a ratification. required_run_bindings[6] tks_to_cas_crosswalk_sha256 stays EMPTY until the "
                "owner signs something.",
                "Not a tested crosswalk. The registry's required_resolution says 'publish and TEST a bijective "
                "code-and-meaning crosswalk'. Nothing here is tested. Ratifying this proposal publishes it; it "
                "does not test it.",
                "Not bijective on all three axes. The Noetic axis is proposed complete (10/10 evidenced). The "
                "symbol-index axis is proposed complete as a code map (40/40 rows) but meaning-clean on only "
                "35/40 (3 WEAK, 2 DIVERGENT). The WORLD axis is 4 of 4 rows CONTESTED and is the reason this "
                "artifact cannot be hashed into binding 6 as it stands.",
                "Not a licence to capture. GATE2_ITEM4_PREREGISTRATION.md:32 requires B5 committed and hashed "
                "BEFORE capture, and 9.2 condition 3 requires the ratification to be DATED before the capture "
                "timestamp.",
            ],
            "honest_headline": (
                "Two of the three axes are evidenced well enough to ratify on sight. The third - what TKS World "
                "A/B/C/D maps onto in CAS - has two mutually exclusive answers, both live in the repo, and the "
                "owner has to make that call. Those are the four rows that need a decision."
            ),
        },

        "controlling_text": {
            "registry": {
                "path": "docs/working/TKS_CAS_SEMANTIC_SOURCE_REGISTRY_CANDIDATE_20260720.json",
                "sha256": "9469a10ae330749c61d157518b849a3737b0f5bd268e44c7bd6334625a38c483",
                "status": "OWNER_SIGNED_SEMANTIC_AUTHORITY_REGISTRY",
                "required_run_bindings_index_6": "tks_to_cas_crosswalk_sha256 (registry line 245) - currently EMPTY",
                "known_conflict_1_verbatim": {
                    "id": "element_indexing_A1_D10_vs_A0_D9",
                    "severity": "P0_SEMANTIC_IDENTITY",
                    "registry_lines": "156-162",
                    "finding": (
                        "TKS v7.4 and owner-locked original fixtures use A1-D10, while normalized "
                        "canon_elements_40.json uses A0-D9. This is a cyclic index remapping, not a harmless "
                        "display change."
                    ),
                    "required_resolution": (
                        "Publish and test a bijective code-and-meaning crosswalk; store both source_symbol and "
                        "normalized_index in every artifact."
                    ),
                },
                "known_conflict_world_axis_verbatim": {
                    "id": "tks_world_to_cas_domain_and_register_collision",
                    "severity": "P0_SEMANTIC_AXIS",
                    "registry_lines": "186-191",
                    "finding": (
                        "Existing artifacts map the four native TKS Worlds both to CAS Domains P/C/E/O and to CAS "
                        "Registers T/A/f/E, although Domain and Register are separate CAS axes. A single World "
                        "label therefore cannot be silently treated as both."
                    ),
                    "required_resolution": (
                        "Preserve native TKS World as its own field, define separate versioned World-to-Domain and "
                        "World-to-Register hypotheses, and test each crosswalk as a distinct multi-head probe "
                        "rather than declaring an identity."
                    ),
                },
                "future_agent_rule_2_verbatim": (
                    "Do not remap A1-D10 to A0-D9 by position without a tested crosswalk."
                ),
                "compliance_statement": (
                    "No row in this proposal was derived by position. The Noetic axis rows are derived from NAME "
                    "identity in an owner source. The symbol-index rows are derived from NAME semantics read from "
                    "both files. The World rows are not derived at all - they are presented as two competing "
                    "hypotheses with their evidence, and left for the owner."
                ),
            },
            "pre_registration": {
                "path": "docs/working/gate2_closure/GATE2_ITEM4_PREREGISTRATION.md",
                "status": "LOCKED - this proposal conforms to it and does not modify it",
                "B5_row_verbatim": (
                    "Owner ratification of the TKS<->CAS crosswalk used by Arm D (Domain A/B/C/D <-> CAS Domain, "
                    "TKS Noetic 1..10 <-> CAS ^1..^9,^0) - required for required_run_bindings[6] "
                    "tks_to_cas_crosswalk_sha256, currently empty"
                ),
                "line_32_verbatim": (
                    "B5 must be committed and hashed BEFORE capture, not after. If the crosswalk is ratified only "
                    "after the numbers exist, the owner - who holds the prior under test - controls whether an Arm "
                    "A loss to Arm D 'counts'. That is unfalsifiability by procedure and this document forbids it."
                ),
                "note_on_the_B5_wording": (
                    "The B5 row names 'Domain A/B/C/D <-> CAS Domain'. Measured this session, that phrasing "
                    "prejudges the contested axis: it assumes the World maps to CAS Domain. The pre-registration "
                    "itself contradicts that at section 2.4, which flags "
                    "tks_world_to_cas_domain_and_register_collision as unresolved, and the Gate 2 item 4 holdout "
                    "bank asserts Register and carries no CAS-domain field at all. This proposal therefore treats "
                    "the second factor as OPEN rather than as Domain-by-assumption. That is a widening of B5's "
                    "question, not a change to any frozen threshold, criterion, control, or unit of analysis - "
                    "nothing in sections 5-9 is touched."
                ),
            },
        },

        "source_refs": [
            {"id": "owner_raw_40_28_workspace", "path": str(OWNER).replace("\\", "/"),
             "sha256": sha(OWNER), "precedence_tier": "2 - exact field authority (OWNER SOURCE)",
             "role": "Element titles and Foundation titles. The ONLY owner-authored evidence in this artifact."},
            {"id": "cas_foundational_clarifications", "path": "C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md",
             "sha256": sha(REPO / "docs" / "CAS_FOUNDATIONAL_CLARIFICATIONS.md"),
             "precedence_tier": "5 - repository-normative CAS authority",
             "role": "Clarification 1 (10 Noetic names/definitions); Clarification 8 lines 308-310 (Domain and Register are independent) and 343-348 (Worlds reframed as Registers)."},
            {"id": "normalized_elements_40", "path": str(CANON40).replace("\\", "/"), "sha256": sha(CANON40),
             "precedence_tier": "registry sources[] - 'Derived representation requiring an explicit A1-D10 crosswalk before use with original-TKS artifacts'",
             "role": "The A0-D9 side of known_conflict #1."},
            {"id": "tks40_specificity", "path": "C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/belief/tks40_specificity.py",
             "sha256": sha(REPO / "noetic-compass-scaffold/noetic-compass/cas-native/belief/tks40_specificity.py"),
             "precedence_tier": "6 - CAS operational implementation",
             "role": "LEGACY_DOMAIN_TO_CAS (World->Domain) at :18-23 and LEGACY_ELEMENT_TO_NOETIC at :39-50. Carries the legacy_domain / legacy_element_code field names."},
            {"id": "tks28_foundations", "path": "C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/belief/tks28_foundations.py",
             "sha256": sha(REPO / "noetic-compass-scaffold/noetic-compass/cas-native/belief/tks28_foundations.py"),
             "precedence_tier": "6 - CAS operational implementation",
             "role": "LEGACY_WORLD_TO_REGISTER (World->Register) at :18-23. Sibling of the file above; the collision is between these two."},
            {"id": "active_python_notation_compiler", "path": "C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/notation/compiler.py",
             "sha256": sha(REPO / "noetic-compass-scaffold/noetic-compass/api/notation/compiler.py"),
             "precedence_tier": "6 - CAS operational implementation (registry source)",
             "role": "META_SET_ALIASES {'Worlds': 'Domains'} at :1214-1215. sha256 matches the registry's recorded hash."},
            {"id": "tks_28_foundations_translation_key", "path": "C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/reference/tks_28_foundations_translation_key.md",
             "sha256": sha(REPO / "docs/reference/tks_28_foundations_translation_key.md"),
             "precedence_tier": "7 - pedagogical summary",
             "role": "Register-to-World table at :43-52, by world ORDINAL not by letter. Also :29-41 position-matches TKS Foundation position to CAS Drive F1-F7."},
            {"id": "stage9_elements_pilot_bank", "path": "noetic-compass-scaffold/noetic-compass/research/cas_probe/stage9_elements_pilot_20260517.jsonl",
             "git_blob_id": BANK_BLOB, "branch": "experiment/cas-probe-pythia",
             "sha256": "2f8637eedff0fb4d9e6191bd5c051ddc21cea699e33621896469a2e522306889",
             "precedence_tier": "8 - generated fixture (corroboration only)",
             "role": "The Gate 2 item 4 holdout bank. Asserts World->Register and TKS-position->CAS-Noetic on all 8,320 rows. Asserts NO CAS Domain."},
            {"id": "stage9_original_40e_scenarios_20260527", "path": str(SCEN20B).replace("\\", "/"),
             "sha256": sha(SCEN20B), "precedence_tier": "8 - generated fixture (corroboration only)",
             "role": "The 20B label set. Asserts World->CAS Domain on all 8,320 rows. This is the opposite reading from the bank above."},
            {"id": "build_stage9_elements_fixture", "path": "noetic-compass-scaffold/noetic-compass/research/cas_probe/build_stage9_elements_fixture.py",
             "branch": "experiment/cas-probe-pythia", "sha256": sha_blob("experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/build_stage9_elements_fixture.py"),
             "precedence_tier": "6 - CAS operational implementation",
             "role": ":29 _DOMAINS=('A','B','C','D'); :30 _DOMAIN_TO_REGISTER; :55 _TKS_TO_CAS_NOETIC. The generator of the bank's assertions."},
        ],

        "correction_to_the_task_brief": {
            "claim_checked": (
                "The build brief said the stage9 40E fixture metadata 'carries legacy_domain / "
                "legacy_element_code / element_domain / element_noetic_tks fields'."
            ),
            "measured": (
                "Those fields are split across TWO DIFFERENT artifacts, and conflating them would have produced a "
                "wrong crosswalk. The Gate 2 item 4 holdout bank (git blob 165df0f6, branch "
                "experiment/cas-probe-pythia) has exactly 28 keys and NONE of them is legacy_domain or "
                "legacy_element_code; it carries element_domain / element_domain_name / element_register / "
                "element_register_name / element_noetic_tks / element_cas_noetic / element_noetic_name, and its "
                "'element_domain' field holds the TKS WORLD LETTER, not a CAS domain. The legacy_domain / "
                "legacy_element_code fields live in a DIFFERENT artifact - the 20260527 scenarios export in "
                "D:/tksCAS-archive - and in noetic-compass-scaffold/noetic-compass/cas-native/belief/"
                "tks40_specificity.py:71-72. Those two artifacts assert OPPOSITE second factors. Treating them as "
                "one de-facto crosswalk is exactly the error this artifact exists to prevent."
            ),
            "consequence_for_this_proposal": (
                "The 'existing de-facto crosswalk' is not one crosswalk. It is two, they disagree on the World "
                "axis, and they agree on the Noetic axis. That split is precisely the EVIDENCED / CONTESTED "
                "boundary drawn below."
            ),
        },

        "axis_1_tks_noetic_position_to_cas_noetic": {
            "axis_status": "EVIDENCED - 10 OF 10 ROWS",
            "proposed_map": {str(k): v for k, v in TKS_POS_TO_CAS_NOETIC.items()},
            "shape": "identity on digits 1..9; position 10 -> ^0",
            "strength_summary": (
                "This is the strong half. It is evidenced by an OWNER source (the owner's own element titles put "
                "the CAS Noetic name at each TKS position, in all four worlds - 40 corroborations for 10 rows), "
                "by repository-normative CAS authority (Clarification 1 names), by two live code modules, and by "
                "two independently-built 8,320-row fixtures that agree with each other on this axis even though "
                "they disagree on the World axis. Eight of ten owner title words are byte-identical to the "
                "Clarification 1 names; the two that are not ('Above' vs 'Above/Cause', 'Below' vs "
                "'Below/Effect') are prefixes of them."
            ),
            "the_one_assistant_judgement_in_this_axis": (
                "That the owner's 'Above'/'Below' mean the canonical 'Above/Cause'/'Below/Effect' rather than a "
                "spatial above/below. Supporting: the owner's A8/A9 sit in the same positions the canon names "
                "'Divine Cause'/'Spiritual Effect' and the bank names 'Above/Cause'/'Below/Effect'. Against: the "
                "zero-based canon reads exactly these two positions SPATIALLY in the Physical world (D8 'Physical "
                "Elevation', D9 'Physical Foundation'). Flagged here rather than buried; see axis 3 rows D8/D9."
            ),
            "rows": build_noetic_rows(owner_titles),
        },

        "axis_2_tks_world_to_cas_second_factor": build_world_rows(),

        "axis_3_symbol_index_A1_D10_to_A0_D9": build_index_rows(owner_titles, canon),

        "contested_summary": {
            "count": 4,
            "rows": [
                "TKS World A (Spiritual) -> CAS ??? : P (Principled) under H_WD_v1, or |T (Transcendent) under H_WR_v1",
                "TKS World B (Mental)    -> CAS ??? : C (Cognitive)  under H_WD_v1, or |A (Analytical)   under H_WR_v1",
                "TKS World C (Emotional) -> CAS ??? : E (Evaluative) under H_WD_v1, or |f (Affective)    under H_WR_v1",
                "TKS World D (Physical)  -> CAS ??? : O (Operational) under H_WD_v1, or |E (Embodied)    under H_WR_v1",
            ],
            "why_no_assistant_recommendation_on_the_axis_choice": (
                "I will state what the evidence weighs at, and then stop. Weighing on precedence alone, H_WR "
                "(World->Register) is ahead: its top source (CAS_FOUNDATIONAL_CLARIFICATIONS.md:346) sits at "
                "repository-normative tier 5, and the Gate 2 item 4 holdout bank - the one this experiment "
                "actually scores on - asserts Register and carries no CAS-domain field at all. Weighing on "
                "consequences, H_WD is ahead: it is already load-bearing in the 8,320-row label set behind the "
                "95.625% GPT-NeoX-20B claim, so ratifying H_WR as an exclusive identity would put that label set "
                "on a different footing. Those two considerations point opposite ways, no owner-authored artifact "
                "decides between them, and the owner holds the prior under test in this experiment. An assistant "
                "recommendation here would be an assistant deciding the semantics of the owner's own ontology on "
                "a coin-flip, which is the failure mode the registry's future_agent_rules exist to stop."
            ),
            "narrower_decision_that_actually_unblocks_the_run": (
                "Gate 2 item 4 does not need the World axis SETTLED. It needs Arm D's second factor NAMED and "
                "HASHED before capture. The already-built Arm D payload "
                "(docs/working/gate2_closure/item4_arms/arm_D_compact_cas.json) emits both variants - D_REG_V1 "
                "(second factor = Register) and D_DOM_LITERAL_V1 (second factor = Domain) - so the owner can bind "
                "one for this run WITHOUT declaring an identity, and the registry's 'two separate versioned "
                "hypotheses' resolution stays intact for later. That is the minimum decision."
            ),
        },

        "owner_ratification": {
            "instructions": (
                "Answer Q1-Q5 yes or no. A 'no' on any question is as useful as a 'yes' - it tells the build what "
                "to change. Do NOT answer these after any activation has been captured: pre-registration line 32 "
                "and section 9.2 condition 3 require the ratification to be dated BEFORE the capture timestamp, "
                "because the owner holds the prior under test."
            ),
            "questions": [
                {
                    "id": "Q1",
                    "blocking": True,
                    "question": (
                        "Ratify the Noetic axis: TKS Noetic position 1->^1, 2->^2, 3->^3, 4->^4, 5->^5, 6->^6, "
                        "7->^7, 8->^8, 9->^9, and 10->^0 (Idea)?"
                    ),
                    "answer_format": "YES / NO / NO-WITH-CORRECTION (state the corrected row)",
                    "evidence_strength": "STRONGEST. Owner-sourced (your own element titles), plus 4 independent corroborations.",
                    "what_a_NO_costs": "Arm D cannot be compiled at all; the 40-Element axis loses its Noetic labels; the bank's element_cas_noetic field is wrong on 8,320 rows.",
                },
                {
                    "id": "Q2",
                    "blocking": True,
                    "question": (
                        "Which axis is the SECOND FACTOR of the 40 Elements - the CAS Domain (P/C/E/O), or the CAS "
                        "Register (T/A/f/E)? Pick ONE for this run. This does not have to settle the ontology; it "
                        "has to name what Arm D compiles against."
                    ),
                    "answer_format": "DOMAIN / REGISTER / BOTH-AS-SEPARATE-HYPOTHESES-AND-ARM-D-USES-<one>",
                    "evidence_strength": "CONTESTED. Both readings are live in the repo and CAS_FOUNDATIONAL_CLARIFICATIONS.md:308-310 makes them mutually exclusive as identities.",
                    "what_a_wrong_answer_costs": "Nothing statistically - Arm D is comparator-only and E2 is stamped CONDITIONAL either way - but the run would be measuring a compiled arm the owner does not recognise as CAS.",
                },
                {
                    "id": "Q3",
                    "blocking": True,
                    "depends_on": "Q2",
                    "question": (
                        "IF DOMAIN: ratify A/Spiritual->P, B/Mental->C, C/Emotional->E, D/Physical->O? "
                        "IF REGISTER: ratify A/Spiritual->|T, B/Mental->|A, C/Emotional->|f, D/Physical->|E?"
                    ),
                    "answer_format": "YES / NO / NO-WITH-CORRECTION (state the corrected rows)",
                    "evidence_strength": (
                        "The ORDERING within each hypothesis is better evidenced than the hypothesis itself. Both "
                        "candidate orderings run high-abstraction to concrete in the letter order A,B,C,D, and "
                        "docs/reference/tks_28_foundations_translation_key.md:52 says so explicitly. So if you "
                        "answer Q2, the four rows in Q3 follow with much less doubt than Q2 itself carries."
                    ),
                },
                {
                    "id": "Q4",
                    "blocking": False,
                    "affects": "Arm C (currently 'unavailable') and registry known_conflict #1",
                    "question": (
                        "Ratify the symbol-index crosswalk A1..D10 <-> A0..D9 as: same world letter, digits 1..9 "
                        "unchanged, and 10 <-> 0 (Idea)? Note the four rows I flagged as not clean: A0 (canon "
                        "'Divine Blueprint' is a weak match for ^0 Idea), D5 and D6 (canon reads them as literal "
                        "persons, 'Woman'/'Man'), and D8/D9 (canon reads Above/Below SPATIALLY as "
                        "'Elevation'/'Foundation' while CAS reads them CAUSALLY as Cause/Effect - the A, B and C "
                        "worlds all read causally, only D switches)."
                    ),
                    "answer_format": "YES / YES-EXCEPT-<codes> / NO",
                    "note": (
                        "Answering this does NOT unblock Arm C. Arm C stays 'unavailable' for an independent, "
                        "already-frozen reason: canon definitions average 21.1 chars against Arm A's 196.2, a ~9x "
                        "length mismatch that violates spec 8.2. The run stays five-armed either way."
                    ),
                },
                {
                    "id": "Q5",
                    "blocking": True,
                    "affects": "which Arm D payload is captured",
                    "question": (
                        "Bind Arm D to variant D_REG_V1 (Noetic definition + verbatim Register definition, 100% "
                        "byte-verbatim from CAS_FOUNDATIONAL_CLARIFICATIONS.md) or D_DOM_LITERAL_V1 (Noetic "
                        "definition + an assistant-assembled one-sentence Domain gloss)? Both are already built "
                        "in arm_D_compact_cas.json. The assistant's recorded recommendation there is D_REG_V1, "
                        "because D_DOM_LITERAL_V1's four domain sentences differ from one another by exactly one "
                        "word, which makes it close to a 10-class arm wearing 40 labels."
                    ),
                    "answer_format": "D_REG_V1 / D_DOM_LITERAL_V1",
                    "why_it_must_be_answered_before_capture": (
                        "Pre-registration section 2.4 and the payload's own variant_binding block: promoting a "
                        "variant after any number exists is post-hoc selection, which section 9.3 forbids."
                    ),
                },
            ],
            "after_answering": [
                "1. Record the answers in a signed receipt alongside OWNER_SEMANTIC_AUTHORITY_REGISTRY_SIGNED_20260724.json.",
                "2. Emit the ratified crosswalk as its own JSON with only the ratified rows, compute its sha256 over LF bytes, and write that hash into required_run_bindings[6] tks_to_cas_crosswalk_sha256.",
                "3. Append it to GATE2_ITEM4_PREREGISTRATION.md as a hashed amendment, DATED, before any forward pass.",
                "4. If Q2 selected an axis, re-run compile_arm_D_compact_cas.py bound to that variant and rehash the Arm D payload.",
            ],
        },

        "what_this_artifact_does_not_settle": [
            "It does not test anything. The registry asks for a TESTED crosswalk (known_conflict #1 required_resolution). Ratification publishes; it does not test.",
            "It does not resolve known_conflict tks_world_to_cas_domain_and_register_collision. Q2/Q3 bind a working choice for one run; the registry's own resolution asks for both hypotheses preserved and each tested as a distinct multi-head probe, which is a separate piece of work.",
            "It does not touch the 28-Foundation / 7-Drive position mapping (registry known_conflict tks_foundation_vs_cas_drive_position_mapping, P1_SEMANTIC_AXIS). docs/reference/tks_28_foundations_translation_key.md:29-41 position-matches TKS Foundation n to CAS Drive Fn, and its own line 68 records the 28 entries as scaffolded placeholders with TKS-source fields PENDING. That axis is out of scope here because the pre-registration section 4.4 dropped the 28-Foundation axis as claim-bearing.",
            "It does not lift any claim status. Nothing here licenses an empirical claim, and the pre-registration's section 12 list is unchanged.",
            "It does not make Arm D claim-bearing. Arm D stays comparator-only at precedence tier 7, and every A-vs-D number stays stamped CONDITIONAL_ON_UNRATIFIED_CROSSWALK until a signed artifact is hashed into binding 6.",
        ],

        "one_notational_defect_found_in_passing": {
            "where": "D:/tksCAS-archive/.../stage9_original_40e_scenarios_20260527.json, expected_cas_axes.element",
            "what": "The 8,320-row export spells the element as '^1|P', '^2|C', etc.",
            "why_it_is_a_defect": (
                "The '|' is the CAS Register operator (Clarification 8 notation: ^n|R). Here it carries a DOMAIN "
                "letter. The correct CAS spelling for a Noetic-in-a-Domain is '^1^P'. This is the "
                "World/Domain/Register collision leaking into notation. Recorded, not fixed - fixing a shipped "
                "8,320-row label set is not a Gate 2 item 4 action."
            ),
        },
    }

    body = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    blob = body.encode("utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(blob)
    digest = hashlib.sha256(blob).hexdigest()
    print("wrote", OUT)
    print("sha256 (on-disk LF bytes):", digest)
    assert hashlib.sha256(OUT.read_bytes()).hexdigest() == digest
    idx = payload["axis_3_symbol_index_A1_D10_to_A0_D9"]["counts"]
    print("index-axis meaning counts:", idx)


if __name__ == "__main__":
    main()
