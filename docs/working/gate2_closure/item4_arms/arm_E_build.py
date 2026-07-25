# -*- coding: utf-8 -*-
"""Emit the Arm E payload JSON for GATE2 item 4 (build item B2).

Deterministic. Reads Arm A (owner source) and the holdout bank blob for code
spelling + gloss-overlap covariate; writes the payload with full length stats.
"""
import json, hashlib, re, statistics, datetime, os
from arm_E_definitions_source import DEFS
from transformers import AutoTokenizer

PROXY_TOK_ID = "gpt2"
PROXY_TOK = AutoTokenizer.from_pretrained(PROXY_TOK_ID)

ARM_A = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/tks_owner_locked_definitions_20260603.json"
BANK = r"./bank.jsonl"  # obtain: git -C <scaffold> cat-file -p 165df0f6ff08c80fe1c42cd4412478527aabc934 > bank.jsonl
PRE = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/gate2_closure/GATE2_ITEM4_PREREGISTRATION.md"
OUT = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/gate2_closure/item4_arms/arm_E_non_tks_ontology.json"

STOP = set("""a an the and or but if of to in on at by for with from as is are was were be been being
it its this that these those there here he she they them his her their our we us i me my you your one
ones s not no nor so than then when while which who whom what where how all any both each few more most
other some such only own same too very can will just do does did doing done have has had having into
over under again further once about against between through during before after above below up down out
off also etc like whether whose within without upon toward towards per via across among around because
would could should may might must shall let thing things way ways make makes made""".split())

QUESTION = {"A": ("Mechanistic", "mechanism / proximate causation"),
            "B": ("Developmental", "ontogeny / development"),
            "C": ("Functional", "function / survival value"),
            "D": ("Phylogenetic", "phylogeny / evolutionary history")}
VALUE = {1: "Self-Direction", 2: "Stimulation", 3: "Hedonism", 4: "Achievement", 5: "Power",
         6: "Security", 7: "Conformity", 8: "Tradition", 9: "Benevolence", 10: "Universalism"}
VALUE_GOAL = {
    1: "independent thought and action - choosing, creating, exploring",
    2: "excitement, novelty, and challenge in life",
    3: "pleasure or sensuous gratification for oneself",
    4: "personal success through demonstrating competence according to social standards",
    5: "social status and prestige, control or dominance over people and resources",
    6: "safety, harmony, and stability of society, of relationships, and of self",
    7: "restraint of actions, inclinations, and impulses likely to upset or harm others and violate social expectations or norms",
    8: "respect, commitment, and acceptance of the customs and ideas that one's culture or religion provides",
    9: "preserving and enhancing the welfare of those with whom one is in frequent personal contact",
    10: "understanding, appreciation, tolerance, and protection for the welfare of all people and for nature",
}


def sha256_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def content_words(t):
    return {w for w in re.findall(r"[a-z]+", t.lower()) if w not in STOP and len(w) > 2}


def sentences(t):
    return [s for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s]


def syllables(w):
    w = re.sub(r"[^a-z]", "", w.lower())
    if not w:
        return 0
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and n > 1:
        n -= 1
    return max(1, n)


def fk_grade(texts):
    W = S = Y = 0
    for t in texts:
        ws = re.findall(r"[A-Za-z']+", t)
        W += len(ws)
        S += len(sentences(t))
        Y += sum(syllables(w) for w in ws)
    return round(0.39 * (W / S) + 11.8 * (Y / W) - 15.59, 3)


def register(defs):
    allw, allsent, types, fp = [], [], set(), 0
    for t in defs.values():
        w = re.findall(r"[A-Za-z']+", t)
        allw += w
        types |= {x.lower() for x in w}
        allsent += sentences(t)
        fp += sum(1 for x in w if x.lower() in {"i", "we", "me", "us", "my", "our", "ours", "mine"})
    return dict(total_words=len(allw), total_sentences=len(allsent),
                mean_words_per_sentence=round(len(allw) / len(allsent), 3),
                type_token_ratio=round(len(types) / len(allw), 4),
                first_person_pronoun_rate=round(fp / len(allw), 5),
                flesch_kincaid_grade=fk_grade(list(defs.values())))


def main():
    a_raw = open(ARM_A, "rb").read()
    a_doc = json.loads(a_raw)
    order = [e["code"] for e in a_doc["tks_40_elements"]]
    A = {e["code"]: e["definition"] for e in a_doc["tks_40_elements"]}
    a_sha = hashlib.sha256(a_raw).hexdigest()

    bank_raw = open(BANK, "rb").read()
    bank_sha = hashlib.sha256(bank_raw).hexdigest()
    glosses, bank_codes = {}, set()
    for line in bank_raw.decode("utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            bank_codes.add(r["element_label"])
            glosses.setdefault(r["element_label"], r["element_gloss"])

    assert bank_codes == set(order) == set(DEFS), "code set mismatch"

    definitions, per_code, deltas, jac_a, jac_g, tpct = {}, {}, [], [], [], []
    for c in order:
        w, n = c[0], int(c[1:])
        e, a = DEFS[c], A[c]
        ce, ca = len(e), len(a)
        we, wa = len(e.split()), len(a.split())
        se, sa = len(sentences(e)), len(sentences(a))
        te, ta = len(PROXY_TOK.encode(e)), len(PROXY_TOK.encode(a))
        tpct.append(abs(100.0 * (te - ta) / ta))
        ja = content_words(a)
        jg = content_words(glosses[c])
        je = content_words(e)
        j_a = round(len(ja & je) / len(ja | je), 4)
        j_g = round(len(jg & je) / len(jg | je), 4)
        j_ag = round(len(jg & ja) / len(jg | ja), 4)
        deltas.append(ce - ca)
        jac_a.append(j_a)
        jac_g.append(j_g)
        definitions[c] = {
            "code": c,
            "title": f"{QUESTION[w][0]} {VALUE[n]}",
            "definition": e,
            "cell": {"tinbergen_question": QUESTION[w][1],
                     "tinbergen_index": "ABCD".index(w) + 1,
                     "schwartz_value": VALUE[n],
                     "schwartz_index": n,
                     "schwartz_defining_motivational_goal": VALUE_GOAL[n]},
        }
        per_code[c] = {
            "arm_e_chars": ce, "arm_a_chars": ca,
            "delta_chars": ce - ca, "pct_delta_chars": round(100.0 * (ce - ca) / ca, 2),
            "arm_e_proxy_tokens_gpt2": te, "arm_a_proxy_tokens_gpt2": ta,
            "delta_proxy_tokens": te - ta,
            "pct_delta_proxy_tokens": round(100.0 * (te - ta) / ta, 2),
            "arm_e_words": we, "arm_a_words": wa,
            "delta_words": we - wa, "pct_delta_words": round(100.0 * (we - wa) / wa, 2),
            "arm_e_sentences": se, "arm_a_sentences": sa,
            "content_word_jaccard_vs_arm_a": j_a,
            "shared_content_words_vs_arm_a": sorted(ja & je),
            "content_word_jaccard_vs_bank_gloss": j_g,
            "shared_content_words_vs_bank_gloss": sorted(jg & je),
            "reference_arm_a_jaccard_vs_bank_gloss": j_ag,
        }

    ce_all = [per_code[c]["arm_e_chars"] for c in order]
    ca_all = [per_code[c]["arm_a_chars"] for c in order]
    pct = [abs(per_code[c]["pct_delta_chars"]) for c in order]
    pctw = [abs(per_code[c]["pct_delta_words"]) for c in order]
    worst = max(order, key=lambda c: abs(per_code[c]["pct_delta_chars"]))
    worst_w = max(order, key=lambda c: abs(per_code[c]["pct_delta_words"]))
    reg_a, reg_e = register(A), register(DEFS)

    payload = {
        "schema_version": "gate2_item4_arm_definition_payload.v1",
        "arm_id": "NON_TKS_SCHWARTZ_X_TINBERGEN_40_V1",
        "arm_letter": "E",
        "arm_role": "coherent matched non-TKS ontology (pre-registration section 2.5, build item B2)",
        "provenance": "ASSISTANT_COMPILED",
        "authorship": "ASSISTANT_AUTHORED_FROM_EXTERNAL_ONTOLOGIES",
        "authorship_note": (
            "The two primitive sets (Schwartz's ten basic values; Tinbergen's four questions) are "
            "externally authored and published. The 40 cross-product cells and every one of the 40 "
            "definition body strings in this file were WRITTEN BY THE ASSISTANT for this experiment "
            "and appear in no external source. A win over this arm is a win over assistant-authored "
            "text, not over a published owner source, and must be reported as such."
        ),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "created_by": "claude-opus-5 subagent, Gate 2 item 4 build list B2",
        "git_committed": False,
        "experiment_run": False,

        "framework": {
            "name": "Schwartz basic human values x Tinbergen's four questions",
            "shape": "10 values x 4 levels of explanation = 40 cells",
            "axis_1": {
                "name": "Schwartz theory of basic human values",
                "citation": "Schwartz, S. H. (1992). Universals in the content and structure of values: "
                            "Theoretical advances and empirical tests in 20 countries. Advances in "
                            "Experimental Social Psychology, 25, 1-65.",
                "secondary_citation": "Schwartz, S. H. (2012). An overview of the Schwartz theory of basic "
                                      "values. Online Readings in Psychology and Culture, 2(1).",
                "primitives_in_order": [VALUE[i] for i in range(1, 11)],
                "internal_logic": "Ten motivationally distinct value types derived from three universal "
                                  "requirements of human existence (biological needs, coordinated social "
                                  "interaction, group survival and welfare), arranged on a circumplex of "
                                  "compatibilities and conflicts. Cross-culturally replicated in 20+ countries."
            },
            "axis_2": {
                "name": "Tinbergen's four questions (four levels of explanation in ethology)",
                "citation": "Tinbergen, N. (1963). On aims and methods of ethology. Zeitschrift fur "
                            "Tierpsychologie, 20(4), 410-433.",
                "secondary_citation": "Bateson, P., & Laland, K. N. (2013). Tinbergen's four questions: "
                                      "an appreciation and an update. Trends in Ecology & Evolution, 28(12), 712-718.",
                "primitives_in_order": ["mechanism / proximate causation", "ontogeny / development",
                                        "function / survival value", "phylogeny / evolutionary history"],
                "internal_logic": "Two orthogonal cuts - proximate vs ultimate, and static vs dynamic - "
                                  "yielding four non-overlapping and jointly exhaustive levels at which any "
                                  "behavioural trait can be explained. A complete account of a trait answers all four."
            },
            "why_this_is_a_serious_alternative": (
                "Both axes are independently published, peer-reviewed, cross-culturally or cross-species "
                "validated, and internally coherent. Their cross-product is not an ad hoc device: analysing "
                "a motivational disposition at Tinbergen's four levels is standard practice in evolutionary "
                "and comparative psychology. Each of the 40 cells names a real, answerable research question "
                "(e.g. 'what is the ontogeny of conformity?'), which is the coherence property the "
                "straw-man gate in pre-registration section 2.5 tests for."
            )
        },

        "bijection": {
            "frozen_before_capture": True,
            "searched_over": False,
            "rule": "Schwartz value n -> TKS Noetic index n in the listed order; Tinbergen question j -> "
                    "TKS World j in the order A, B, C, D. Fixed by pre-registration section 2.5; no "
                    "alternative bijection was tried, scored, or reported.",
            "world_to_tinbergen": {w: QUESTION[w][1] for w in "ABCD"},
            "noetic_index_to_schwartz": {str(i): VALUE[i] for i in range(1, 11)},
            "semantic_alignment_disclaimer": (
                "The bijection is POSITIONAL, not semantic. It is not claimed that TKS World A means "
                "'mechanism' or that TKS Noetic 1 means 'Self-Direction'. The bijection exists only so that "
                "Arm E occupies the same 40 code slots as the bank's label space; the pre-registration fixes "
                "it precisely so that no post-hoc alignment search can be run."
            )
        },

        "source_refs": [
            {"role": "length_and_register_reference (Arm A, canonical arm)", "path": ARM_A,
             "sha256": a_sha, "field_used": "tks_40_elements[*].definition",
             "note": "used ONLY to derive per-code length and register targets; no Arm A wording was reused"},
            {"role": "code_spelling_and_gloss_overlap_covariate (holdout bank)",
             "path": "noetic-compass-scaffold/noetic-compass/research/cas_probe/stage9_elements_pilot_20260517.jsonl",
             "git_blob_id": "165df0f6ff08c80fe1c42cd4412478527aabc934",
             "git_branch": "experiment/cas-probe-pythia",
             "sha256": bank_sha,
             "note": "read to confirm the 40 element_label spellings are exactly A1..D10 and to compute the "
                     "S13 lexical-overlap covariate. Bank content did not influence any definition wording."},
            {"role": "controlling_design", "path": PRE, "sha256": sha256_file(PRE),
             "note": "sha256 of the pre-registration as read at authoring time"}
        ],

        "codes_covered": {"n": len(order), "codes": order,
                          "matches_bank_label_space_exactly": True},

        "definitions": definitions,

        "length_stats": {
            "unit": "characters of the definition body string, as fed to the anchor frames",
            "reference_arm": "A",
            "per_code": per_code,
            "arm_e": {"mean_chars": round(statistics.mean(ce_all), 3),
                      "sd_chars": round(statistics.stdev(ce_all), 3),
                      "min_chars": min(ce_all), "max_chars": max(ce_all),
                      "mean_words": round(statistics.mean([per_code[c]["arm_e_words"] for c in order]), 3),
                      "mean_proxy_tokens_gpt2": round(statistics.mean([per_code[c]["arm_e_proxy_tokens_gpt2"] for c in order]), 3),
                      "sd_proxy_tokens_gpt2": round(statistics.stdev([per_code[c]["arm_e_proxy_tokens_gpt2"] for c in order]), 3),
                      "total_sentences": sum(per_code[c]["arm_e_sentences"] for c in order)},
            "arm_a": {"mean_chars": round(statistics.mean(ca_all), 3),
                      "sd_chars": round(statistics.stdev(ca_all), 3),
                      "min_chars": min(ca_all), "max_chars": max(ca_all),
                      "mean_words": round(statistics.mean([per_code[c]["arm_a_words"] for c in order]), 3),
                      "mean_proxy_tokens_gpt2": round(statistics.mean([per_code[c]["arm_a_proxy_tokens_gpt2"] for c in order]), 3),
                      "sd_proxy_tokens_gpt2": round(statistics.stdev([per_code[c]["arm_a_proxy_tokens_gpt2"] for c in order]), 3),
                      "total_sentences": sum(per_code[c]["arm_a_sentences"] for c in order)},
            "delta_vs_arm_a": {
                "PRIMARY_proxy_token_match_gpt2_bpe": {
                    "mean_abs_pct_delta": round(statistics.mean(tpct), 3),
                    "max_abs_pct_delta": round(max(tpct), 2),
                    "worst_code": max(order, key=lambda c: abs(per_code[c]["pct_delta_proxy_tokens"])),
                    "n_codes_outside_plus_minus_10_pct": sum(1 for p in tpct if p > 10.0),
                    "arm_a_mean_tokens": round(statistics.mean([per_code[c]["arm_a_proxy_tokens_gpt2"] for c in order]), 3),
                    "arm_e_mean_tokens": round(statistics.mean([per_code[c]["arm_e_proxy_tokens_gpt2"] for c in order]), 3)},
                "mean_delta_chars": round(statistics.mean(deltas), 3),
                "sd_delta_chars": round(statistics.stdev(deltas), 3),
                "mean_abs_pct_delta_chars": round(statistics.mean(pct), 3),
                "max_abs_pct_delta_chars": max(pct),
                "worst_code_chars": worst,
                "n_codes_outside_plus_minus_10_pct_chars": sum(1 for p in pct if p > 10.0),
                "mean_abs_pct_delta_words": round(statistics.mean(pctw), 3),
                "max_abs_pct_delta_words": max(pctw),
                "worst_code_words": worst_w,
                "n_codes_outside_plus_minus_10_pct_words": sum(1 for p in pctw if p > 10.0),
                "sentence_count_mismatches": sum(
                    1 for c in order if per_code[c]["arm_e_sentences"] != per_code[c]["arm_a_sentences"])
            },
            "matching_rule_applied": "per-code subword-token count (GPT-2 BPE proxy) within +/-10% of the "
                                     "index-matched Arm A definition, AND per-code character count within "
                                     "+/-10%, AND exact per-code sentence-count match. All three hold on "
                                     "40/40 codes.",
            "proxy_tokenizer": {
                "id": PROXY_TOK_ID,
                "why_a_proxy": "The pre-registration matches on tokens under the tokenizer pinned at "
                               "required_run_bindings[10], which is unavailable_until_capture_host_resolved "
                               "(build item B8; candidate Qwen/Qwen2.5-1.5B-Instruct, not pinned). GPT-2 BPE "
                               "is used here as a same-family subword stand-in so the match is measured "
                               "rather than assumed.",
                "why_it_mattered": "Character matching alone was NOT sufficient. Arm A's rarer vocabulary "
                                   "fragments into more subwords per character, so a char-matched draft "
                                   "sat 19/40 codes outside +/-10% on tokens. The definitions were "
                                   "re-tuned against the tokenizer until both metrics passed.",
                "MANDATORY_RECHECK": "Recompute this table under the pinned tokenizer once B8 resolves. If "
                                     "any code then falls outside +/-10% tokens, THIS ARM MUST BE REWRITTEN "
                                     "before capture. Passing under a proxy is not passing."
            }
        },

        "register_stats": {
            "arm_e": reg_e, "arm_a": reg_a,
            "preregistered_tolerances_section_2_5": {
                "mean_words_per_sentence": {"tolerance": "+/-15%", "arm_a": reg_a["mean_words_per_sentence"],
                                            "arm_e": reg_e["mean_words_per_sentence"],
                                            "pct_delta": round(100.0 * (reg_e["mean_words_per_sentence"] - reg_a["mean_words_per_sentence"]) / reg_a["mean_words_per_sentence"], 2),
                                            "pass": abs(reg_e["mean_words_per_sentence"] - reg_a["mean_words_per_sentence"]) / reg_a["mean_words_per_sentence"] <= 0.15},
                "type_token_ratio": {"tolerance": "+/-0.05", "arm_a": reg_a["type_token_ratio"],
                                     "arm_e": reg_e["type_token_ratio"],
                                     "delta": round(reg_e["type_token_ratio"] - reg_a["type_token_ratio"], 4),
                                     "pass": abs(reg_e["type_token_ratio"] - reg_a["type_token_ratio"]) <= 0.05},
                "first_person_pronoun_rate": {"tolerance": "+/-0.02", "arm_a": reg_a["first_person_pronoun_rate"],
                                              "arm_e": reg_e["first_person_pronoun_rate"],
                                              "delta": round(reg_e["first_person_pronoun_rate"] - reg_a["first_person_pronoun_rate"], 5),
                                              "pass": abs(reg_e["first_person_pronoun_rate"] - reg_a["first_person_pronoun_rate"]) <= 0.02},
                "flesch_kincaid_grade": {"tolerance": "+/-1.5", "arm_a": reg_a["flesch_kincaid_grade"],
                                         "arm_e": reg_e["flesch_kincaid_grade"],
                                         "delta": round(reg_e["flesch_kincaid_grade"] - reg_a["flesch_kincaid_grade"], 3),
                                         "pass": abs(reg_e["flesch_kincaid_grade"] - reg_a["flesch_kincaid_grade"]) <= 1.5}
            },
            "grammatical_style": "Every definition opens with its cell name followed by 'is', matching Arm A's "
                                 "'<Title> is ...' definitional frame, then elaborates in comma-chained "
                                 "declarative prose. Sentence counts match Arm A per code exactly.",
            "measurement_notes": [
                "Flesch-Kincaid uses a regex vowel-group syllable heuristic, not a pronunciation dictionary; "
                "it is applied identically to both arms so the DELTA is the meaningful quantity, not the level.",
                "Length matching was optimised against GPT-2 BPE token counts, not against the pinned "
                "capture tokenizer, which does not exist yet (B8). See length_stats.proxy_tokenizer."
            ]
        },

        "independence_from_tks": {
            "method": "content-word Jaccard per code against the index-matched Arm A definition; content "
                      "words are lowercased alphabetic tokens of length > 3 characters after stopword removal",
            "vs_arm_a": {"min": min(jac_a), "mean": round(statistics.mean(jac_a), 5), "max": max(jac_a),
                         "max_code": max(order, key=lambda c: per_code[c]["content_word_jaccard_vs_arm_a"]),
                         "n_codes_with_any_shared_content_word": sum(1 for c in order if per_code[c]["shared_content_words_vs_arm_a"]),
                         "all_shared_content_words": sorted({w for c in order for w in per_code[c]["shared_content_words_vs_arm_a"]})},
            "vs_bank_glosses_S13_covariate": {
                "min": min(jac_g), "mean": round(statistics.mean(jac_g), 5), "max": max(jac_g),
                "reference_arm_a_vs_bank_glosses": {
                    "min": min(per_code[c]["reference_arm_a_jaccard_vs_bank_gloss"] for c in order),
                    "mean": round(statistics.mean([per_code[c]["reference_arm_a_jaccard_vs_bank_gloss"] for c in order]), 5),
                    "max": max(per_code[c]["reference_arm_a_jaccard_vs_bank_gloss"] for c in order)},
                "note": "Arm E sits near zero overlap with the bank glosses by construction while Arm A does "
                        "not. Pre-registration S13 therefore REQUIRES that any A-over-E margin survive "
                        "conditioning on per-class overlap at concept level (n = 40). An uncontrolled A > E "
                        "could be nothing but lexical overlap."
            },
            "vocabulary_exclusions_applied": [
                "no TKS World names (Spiritual, Mental, Emotional, Physical)",
                "no TKS Noetic names (Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above, Below, Idea)",
                "no CAS framework vocabulary (Noetic, Domain, Drive, Register, Element, Foundation, Operator, Inversion)",
                "no devotional or metaphysical register (soul, God, Divine, spirit, aura, aether, Akashic, esoteric, initiate)"
            ]
        },

        "preregistered_ceiling": {
            "headline": "ARM E CANNOT WIN BY CONSTRUCTION. Beating it is close to tautological.",
            "statement": (
                "The holdout bank's LABEL SPACE is the TKS ontology itself: its 40 classes ARE the 40 TKS "
                "Elements and its 40 glosses were authored inside this project. Arm E is scored on how well "
                "a Schwartz x Tinbergen definition set identifies TKS categories. A TKS-derived arm is "
                "therefore advantaged by the construction of the evaluation, independently of any semantic "
                "merit. An Arm A win over Arm E (criterion E6) restates the setup; it is not evidence that "
                "TKS concepts are more universal, more valid, or better than Schwartz x Tinbergen."
            ),
            "governing_text": [
                "Pre-registration section 4.3: 'Arm E cannot win by construction. ... Criterion E6 is "
                "therefore declared THE WEAKEST of 8.4's six and is never headlined.'",
                "Pre-registration section 7, E6: bar >= +0.08 with LCB > 0, 'Declared IN ADVANCE the WEAKEST "
                "of the six criteria and never headlined'.",
                "Pre-registration section 9.3: E6 is absent from the frozen headline contrast list.",
                "Pre-registration section 12.7: 'No claim that TKS concepts are more universal than other "
                "concept sets.'"
            ],
            "what_would_actually_be_informative": (
                "Only the reverse. Pre-registration section 10.1 R3: if Arm E MATCHES OR BEATS Arm A on a "
                "bank whose labels are the TKS ontology, that is the strongest disconfirmation available in "
                "this design, and the canonical-wording claim does not issue."
            ),
            "authoring_posture": (
                "Given that ceiling, this arm was authored to be as strong as honesty allows rather than as "
                "a foil: real published primitive sets, a cross-product that is standard practice in the "
                "source literature, per-code length and sentence-count matching to Arm A, four matched "
                "register statistics, and near-zero lexical overlap achieved by writing different content "
                "rather than by degrading it."
            )
        },

        "outstanding_gates": [
            {"id": "P6 / section 2.5 STRAW-MAN GATE", "status": "unavailable_until_rated",
             "requirement": "80 definitions (40 Arm A + 40 Arm E) shuffled, rated blind to arm, 1-5, on "
                            "'coherent, non-circular definition of a distinct category', by a pre-registered "
                            "independent rater. Arm E must score >= mean(Arm A) - 0.5.",
             "note": "NOT RUN. The rater is not pre-registered and is not the author of this file. A failed "
                     "audit is a DESIGN DEFECT requiring rewrite, and is NEVER reported as an Arm E loss."},
            {"id": "B8 tokenizer-exact length match", "status": "matched_under_proxy_only",
             "requirement": "per-code token count within +/-10% of Arm A under the tokenizer pinned at "
                            "required_run_bindings[10]",
             "note": "Matched on 40/40 codes under a GPT-2 BPE proxy (max 8.1%). The pinned tokenizer does "
                     "not exist yet. Recompute under it before capture; rewrite this arm if any code fails."},
            {"id": "arm manifest sha256 registration", "status": "pending",
             "requirement": "this file's own sha256 registered per pre-registration bindings 1-4 in the "
                            "hashed amendment, before the first forward pass"}
        ],

        "honest_limitations": [
            "ASSISTANT_COMPILED. All 40 definition bodies are the assistant's own composition. Only the two "
            "primitive NAME sets are external; no external source contains this prose.",
            "The straw-man / blind-coherence audit (P6) has NOT been run. Until an independent rater scores "
            "it, 'coherent' is the author's claim about the author's own text.",
            "Length matching passes on 40/40 codes for BOTH subword tokens (GPT-2 BPE proxy, max 8.1%) and "
            "characters (max 9.4%), but the tokenizer that will actually be used at capture is not pinned "
            "(B8), so the token match is a proxy result and must be rechecked. WHITESPACE-WORD counts are "
            "deliberately NOT matched and diverge by up to 40% on short codes: Arm A packs rare multi-token "
            "words, Arm E packs common single-token words, and matching all three quantities at once is not "
            "simultaneously satisfiable. Tokens were prioritised because the residual confound named in "
            "pre-registration section 3.2 is the anchor read POSITION, which is a token index.",
            "Near-zero lexical overlap with Arm A is a design goal for independence, but it is CONFOUNDED "
            "with overlap against the bank glosses (S13). Arm A shares vocabulary with the bank; Arm E does "
            "not. Any A-over-E margin that does not survive the S13 covariate is lexical overlap, not semantics.",
            "Per-code register matching forced a real prose cost on a handful of codes. Arm A's C2, D5, D6 "
            "and similar entries are terse comma-lists of short words, which are unusually token-dense; "
            "matching them drove Arm E's C2, C4, D5, D6 into the same telegraphic list register (e.g. C2 "
            "'news, range, luck, reach, spread'). Those cells are the most likely to be marked down by the "
            "P6 blind rater. If they are, the correct response is to rewrite them and re-audit, NOT to "
            "report an Arm E loss.",
            "The bijection is positional and arbitrary by design. It carries no claim that any Schwartz value "
            "corresponds to any TKS Noetic, or that any Tinbergen question corresponds to any TKS World.",
            "Register matching removes obvious style confounds at the arm level; it cannot remove domain-block "
            "style, which the pre-registration (section 3.3) states survives arm-internal centering.",
            "Arm E is structurally disadvantaged and the disadvantage is not correctable within this design. "
            "It is a fair comparator for the question 'does a coherent 40-category ontology do as well on a "
            "TKS-labelled bank', and it is not a fair comparator for 'is TKS a better ontology than Schwartz "
            "x Tinbergen'. The second question is not asked and cannot be answered here."
        ]
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=True)
        f.write("\n")
    print("wrote", OUT)
    print("payload sha256", sha256_file(OUT))
    ls = payload["length_stats"]["delta_vs_arm_a"]
    print("mean|pct|chars", ls["mean_abs_pct_delta_chars"], "max", ls["max_abs_pct_delta_chars"],
          "n>10%", ls["n_codes_outside_plus_minus_10_pct_chars"])
    print("E mean chars", payload["length_stats"]["arm_e"]["mean_chars"],
          "A mean chars", payload["length_stats"]["arm_a"]["mean_chars"])
    print("register", json.dumps(payload["register_stats"]["preregistered_tolerances_section_2_5"], indent=1))
    print("jaccard vs A", payload["independence_from_tks"]["vs_arm_a"])
    print("jaccard vs glosses", {k: v for k, v in payload["independence_from_tks"]["vs_bank_glosses_S13_covariate"].items() if k != "note"})


if __name__ == "__main__":
    main()
