"""THE CURRICULUM: three more constructions taught by the live 3B
through the same schema-constrained pipeline - questions, commands,
coordination. One sealed episode each; the examiner (the ten-stage
ladder + OUR protected held-out) never changes.

GPU-only per the standing owner order.
"""

import glob
import json
import os
import re
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(LANE, "CCB_L1_v0.1"))
sys.path.insert(0, os.path.join(LANE, "CAS_CORTEX_v0.1"))

from apprentice.board import ApprenticeshipBoard  # noqa: E402
from constrained_teacher import (TEACHING_LEX,  # noqa: E402
                                 extract_json_value, valid_ambiguity,
                                 valid_morphology, valid_pairs)
from lang.apprentice import Apprentice  # noqa: E402
from lang.constructions import (ConstructionParser, GrammarStore,  # noqa: E402
                                MorphTable, validate_construction)
from lang.lexicon import Lexicon  # noqa: E402

TEACHER_MODEL = os.environ.get("CAS_TEACHER_MODEL",
                               "Qwen/Qwen2.5-3B-Instruct")
SEED_GRAMMAR = os.path.join(LANE, "CCB_L1_v0.1", "fixtures",
                            "seed_grammar.json")
SEED_MORPH = os.path.join(LANE, "CCB_L1_v0.1", "fixtures",
                          "seed_morphology.json")

CURRICULUM_LEX = dict(TEACHING_LEX)
CURRICULUM_LEX.update({
    "gray": {"pos": "adj", "sense": "gray"},
    "brown": {"pos": "adj", "sense": "brown"},
    "quiet": {"pos": "adj", "sense": "quiet"},
})

SEED_LEXICON = os.path.join(LANE, "CCB_L1_v0.1", "fixtures",
                            "seed_lexicon.json")

# The student's vocabulary is the RUNTIME's accumulated lexicon: every
# word an earlier lesson promoted (LEX persistence) must be present,
# or prior-grammar regression guards that use those words falsely
# fail (found live: lesson L009 tripped the ditransitive guard
# because 'bone' was missing from the static teaching set).
try:
    with open(SEED_LEXICON, encoding="utf-8") as _fh:
        CURRICULUM_LEX.update(json.load(_fh)["lexicon"])
except (FileNotFoundError, KeyError):
    pass

ROLES = ("agent", "patient", "agent2", "patient2",
         "agent3", "patient3", "possessor", "recipient",
         "experiencer", "instrument", "source", "destination",
         "location")
ADJ_SLOTS = ("agent_mod", "patient_mod", "mod", "prop",
             "comp")
VERB_NAMES = ("pred", "pred2", "pred3")
VERB_FORMS = ("base", "past", "participle", "present_3sg")


def valid_pattern(value):
    if not isinstance(value, list) or not value:
        return "must be a non-empty FLAT JSON list of strings"
    has_np = has_verb = False
    for element in value:
        if not isinstance(element, str):
            return f"element {element!r} is not a string"
        if element.startswith("NP:") or element.startswith("NPPL:") \
                or element.startswith("PRON:") \
                or element.startswith("NPOSS:"):
            parts = element.split(":")
            if len(parts) != 2 or parts[1] not in ROLES:
                return (f"NP slot {element!r} must name a role from "
                        f"{ROLES}")
            has_np = True
        elif element.startswith("QUANT:"):
            if element != "QUANT:quantifier":
                return "the QUANT slot is written QUANT:quantifier"
        elif element.startswith("NUM:"):
            if element.split(":")[1] not in ("x", "y", "b", "c"):
                return ("NUM slots are written NUM:x / NUM:y / "
                        "NUM:b / NUM:c")
        elif element.startswith("OPW:"):
            if element != "OPW:op":
                return "the OPW slot is written OPW:op"
        elif element.startswith("ADV:"):
            if element != "ADV:time":
                return "the ADV slot is written ADV:time"
        elif element.startswith("VERB:"):
            parts = element.split(":")
            if len(parts) != 3 or parts[1] not in VERB_NAMES \
                    or parts[2] not in VERB_FORMS:
                return (f"VERB slot {element!r} must be "
                        f"VERB:pred:form (or VERB:pred2:form) with "
                        f"form in {VERB_FORMS}")
            has_verb = True
        elif element.startswith("ADJ:"):
            parts = element.split(":")
            if len(parts) != 2 or parts[1] not in ADJ_SLOTS:
                return (f"ADJ slot {element!r} must be ADJ:name with "
                        f"name in {ADJ_SLOTS}")
        elif "." in element or "?" in element:
            return (f"element {element!r} contains punctuation - "
                    f"patterns hold only slots and bare lowercase "
                    f"words")
        elif element in ("chase", "chases", "chased"):
            return (f"you wrote the verb {element!r} as a literal "
                    f"word - write it as a VERB SLOT instead, for "
                    f"example 'VERB:pred:base' (so it matches ANY "
                    f"verb in that form)")
        elif element in ("x", "y", "a", "b", "c", "d", "noun")                 and not any(e.startswith(("NUM:", "OPW:"))
                            for e in value):
            # in a MATH pattern the literal 'x' is the unknown, not a
            # placeholder (bridge finding: the validator rejected the
            # teacher's correct equation pattern)
            return (f"{element!r} is a placeholder - use an NP slot "
                    f"like 'NP:agent' or 'NP:patient' instead")
        elif not element.islower():
            return f"literal {element!r} must be lowercase"
    # copular constructions ('is the gray cat quiet?') carry the
    # copula as a literal and legitimately have no VERB slot; MATH
    # patterns (NUM/OPW slots) have neither nouns nor verbs
    is_math = any(e.startswith(("NUM:", "OPW:")) for e in value)
    has_copula = any(e in ("is", "was", "are", "were") for e in value)
    if not has_verb and not has_copula and not is_math:
        return ("missing the VERB slot: write the verb position as "
                "VERB:pred:form (e.g. 'VERB:pred:base'), never the "
                "literal verb word")
    if not has_np and not is_math:
        return ("missing NP slots: write noun positions as NP:agent / "
                "NP:patient, never literal nouns")
    return None


def structural_check(sentences, pattern, morphology, must_match):
    parser = _parser(morphology)
    rule = {"construction_id": "field_check",
            "surface_pattern": pattern,
            "semantics": {"frame": "event", "tense": "present",
                          "polarity": "positive"}}
    verb_forms = [e.split(":")[2] for e in pattern
                  if e.startswith("VERB:")]
    for sentence in sentences:
        matched = parser.match(rule, sentence) is not None
        if must_match and not matched:
            # name the FORM conflict when that is the actual cause
            if "chases" in sentence and "present_3sg" not in verb_forms:
                return (f"FORM MISMATCH: your pattern's VERB form is "
                        f"{verb_forms} (matches 'chase') but "
                        f"{sentence!r} uses 'chases' (present_3sg). "
                        f"Either answer with sentences using the "
                        f"form your pattern declares, or note the "
                        f"pattern needs VERB:...:present_3sg")
            if "chase " in sentence and "base" not in verb_forms:
                return (f"FORM MISMATCH: {sentence!r} uses base "
                        f"'chase' but your pattern's VERB form is "
                        f"{verb_forms}")
            # name the exact unknown words - vague feedback wastes
            # teacher retries (round-2 finding: 'quick' used 4x)
            from lang.grammar import tokenize
            known = set(CURRICULUM_LEX)
            # function words and the pattern's own literals are not
            # 'unknown' - flagging 'to' when the real defect is a
            # shape mismatch sent the teacher chasing the wrong fix
            function_words = {"the", "a", "to", "by", "did", "does",
                              "was", "were", "is", "are", "not",
                              "and", "or"}
            literals = {e for e in pattern if ":" not in e}
            unknown = [t for t in tokenize(sentence)
                       if t not in known and t not in (".", "?", ",")
                       and t not in function_words
                       and t not in literals
                       and _parser(morphology).morph.analyze(t) is None]
            if unknown:
                adjectives = sorted(w for w, e in CURRICULUM_LEX.items()
                                    if e["pos"] == "adj")
                nouns = sorted(w for w, e in CURRICULUM_LEX.items()
                               if e["pos"] == "noun")
                return (f"unknown word(s) {unknown} in {sentence!r} - "
                        f"known adjectives: {adjectives}; known "
                        f"nouns: {nouns}. Use ONLY these")
            return (f"{sentence!r} does not match YOUR pattern "
                    f"{pattern}; the sentence must have EXACTLY that "
                    f"token shape (same literals in the same places - "
                    f"a question pattern needs a question sentence). "
                    f"Simplest correct answer: reuse a sentence from "
                    f"your positive_examples")
        if not must_match and matched:
            return (f"{sentence!r} is grammatical under your pattern "
                    f"- a counterexample must be BROKEN so it does "
                    f"NOT match")
    return None


def _parser(morphology):
    morph = MorphTable()
    # start from the machine's PERSISTED morphology - the field check
    # must know every verb form earlier lessons promoted (found live:
    # 'give' flagged unknown while the runtime knew it perfectly)
    try:
        for surface, entry in json.load(
                open(SEED_MORPH, encoding="utf-8")).items():
            morph.teach(surface, entry["lemma"], entry["form"],
                        provenance=entry["provenance"])
    except FileNotFoundError:
        pass
    for entry in morphology or []:
        try:
            morph.teach(entry["surface"], entry["lemma"],
                        entry["form"], provenance="field_check")
        except Exception:
            # a lesson entry conflicting with prior knowledge is NOT
            # silently accepted - the ladder refuses it typed; the
            # field check just declines to crash on it
            pass
    return ConstructionParser(Lexicon(CURRICULUM_LEX), morph)


# ----------------------------------------------------------------------
def _core_event(pred, agent, patient, tense="present",
                polarity="positive"):
    return {"frame": "event", "predicate": pred, "agent": agent,
            "patient": patient, "tense": tense, "polarity": polarity}


TARGETS = [
    {
        "construction_id": "interrogative_present_transitive",
        "lesson_id": "LIVE_L003_question",
        "description": "the yes/no QUESTION construction "
                       "'does the X VERB the Y?' - meaning an event "
                       "with the verb as predicate, X as agent, Y as "
                       "patient, tense present, polarity positive; "
                       "it is a QUESTION about that event",
        "shape_hint": "does the X chase the Y?",
        "surface_meta": {"mood": "interrogative"},
        "scaffold_semantics": _core_event("@pred", "@agent",
                                          "@patient"),
        "example_sentence_hint": "shaped 'does the X chase the Y?' "
                                 "ending with '?'",
        "expected_core_hint": json.dumps(_core_event(
            "chase", "<X>", "<Y>")),
        "held_out": [
            {"sentence": "does the fox chase the hen?",
             "expected_core": _core_event("chase", "fox", "hen")},
            {"sentence": "does the bird chase the cat?",
             "expected_core": _core_event("chase", "bird", "cat")},
            {"sentence": "does chase the fox the?", "expect": "no_parse"},
        ],
        "retention": [
            {"sentence": "does the hen chase the dog?",
             "expected_core": _core_event("chase", "hen", "dog")},
        ],
        "probe": "does the cat chase the dog?",
    },
    {
        "construction_id": "imperative_transitive",
        "lesson_id": "LIVE_L004_command",
        "description": "the COMMAND construction 'VERB the Y.' (for "
                       "instance 'chase the dog.') - meaning an event "
                       "where the verb is the predicate, the agent is "
                       "the literal string 'addressee' (the one being "
                       "commanded), Y is the patient, tense present, "
                       "polarity positive",
        "shape_hint": "chase the Y.",
        "surface_meta": {"mood": "imperative"},
        "scaffold_semantics": {"frame": "event", "predicate": "@pred",
                               "agent": "addressee",
                               "patient": "@patient",
                               "tense": "present",
                               "polarity": "positive"},
        "example_sentence_hint": "shaped 'chase the Y.' ending "
                                 "with '.'",
        "expected_core_hint": json.dumps({
            "frame": "event", "predicate": "chase",
            "agent": "addressee", "patient": "<Y>",
            "tense": "present", "polarity": "positive"}),
        "held_out": [
            {"sentence": "chase the hen.",
             "expected_core": {"frame": "event", "predicate": "chase",
                               "agent": "addressee", "patient": "hen",
                               "tense": "present",
                               "polarity": "positive"}},
            {"sentence": "the chase hen.", "expect": "no_parse"},
        ],
        "retention": [
            {"sentence": "chase the bird.",
             "expected_core": {"frame": "event", "predicate": "chase",
                               "agent": "addressee",
                               "patient": "bird",
                               "tense": "present",
                               "polarity": "positive"}},
        ],
        "probe": "chase the dog.",
    },
    {
        "construction_id": "coordination_present_transitive",
        "lesson_id": "LIVE_L005_coordination",
        "description": "the COORDINATION construction 'the A chases "
                       "the B and the C chases the D.' - TWO events "
                       "joined by 'and'; the first uses slots agent/"
                       "patient with verb slot pred, the second uses "
                       "slots agent2/patient2 with verb slot pred2 "
                       "(both verbs in present_3sg form like "
                       "'chases'); the meaning keeps BOTH events",
        "shape_hint": "the A chases the B and the C chases the D.",
        "surface_meta": {"mood": "declarative"},
        "scaffold_semantics": {
            "frame": "coordination",
            "conjuncts": [_core_event("@pred", "@agent", "@patient"),
                          _core_event("@pred2", "@agent2",
                                      "@patient2")]},
        "example_sentence_hint": "shaped 'the A chases the B and the "
                                 "C chases the D.' with four nouns "
                                 "from the lexicon",
        "expected_core_hint": json.dumps({
            "frame": "coordination",
            "conjuncts": [_core_event("chase", "<A>", "<B>"),
                          _core_event("chase", "<C>", "<D>")]}),
        "held_out": [
            {"sentence": "the fox chases the hen and the dog chases "
                         "the cat.",
             "expected_core": {"frame": "coordination", "conjuncts": [
                 _core_event("chase", "fox", "hen"),
                 _core_event("chase", "dog", "cat")]}},
            {"sentence": "the and chases fox hen the.",
             "expect": "no_parse"},
        ],
        "retention": [
            {"sentence": "the bird chases the fox and the cat chases "
                         "the hen.",
             "expected_core": {"frame": "coordination", "conjuncts": [
                 _core_event("chase", "bird", "fox"),
                 _core_event("chase", "cat", "hen")]}},
        ],
        "probe": "the cat chases the dog and the dog chases the cat.",
    },
    {
        "construction_id": "ditransitive_present",
        "lesson_id": "LIVE_L006_recipient",
        "description": "the DITRANSITIVE construction 'the X gives the Y to the Z.' - an event where the verb is the predicate, X the agent, Y the patient (thing transferred), Z the RECIPIENT (slot NP:recipient); tense present, polarity positive. Verb: give (present_3sg 'gives'). Extra noun: bone",
        "shape_hint": "the X gives the bone to the Z.",
        "surface_meta": {
            "mood": "declarative"
        },
        "scaffold_semantics": {
            "frame": "event",
            "predicate": "@pred",
            "agent": "@agent",
            "patient": "@patient",
            "recipient": "@recipient",
            "tense": "present",
            "polarity": "positive"
        },
        "example_sentence_hint": "shaped 'the X gives the bone to the Z.'",
        "expected_core_hint": "{\"frame\": \"event\", \"predicate\": \"give\", \"agent\": \"<X>\", \"patient\": \"bone\", \"tense\": \"present\", \"polarity\": \"positive\", \"recipient\": \"<Z>\"}",
        "lexicon_additions": {
            "bone": {
                "pos": "noun",
                "sense": "bone"
            }
        },
        "held_out": [
            {
                "sentence": "the fox gives the bone to the hen.",
                "expected_core": {
                    "frame": "event",
                    "predicate": "give",
                    "agent": "fox",
                    "patient": "bone",
                    "tense": "present",
                    "polarity": "positive",
                    "recipient": "hen"
                }
            },
            {
                "sentence": "the dog gives the bone to the cat.",
                "expected_core": {
                    "frame": "event",
                    "predicate": "give",
                    "agent": "dog",
                    "patient": "bone",
                    "tense": "present",
                    "polarity": "positive",
                    "recipient": "cat"
                }
            },
            {
                "sentence": "the gives bone to dog the.",
                "expect": "no_parse"
            }
        ],
        "retention": [
            {
                "sentence": "the hen gives the bone to the bird.",
                "expected_core": {
                    "frame": "event",
                    "predicate": "give",
                    "agent": "hen",
                    "patient": "bone",
                    "tense": "present",
                    "polarity": "positive",
                    "recipient": "bird"
                }
            }
        ],
        "probe": "the cat gives the bone to the dog."
    },
    {
        "construction_id": "attributive_adjective_transitive",
        "lesson_id": "LIVE_L007_adjectives",
        "description": "the ATTRIBUTIVE ADJECTIVE construction 'the ADJ X chases the ADJ Y.' - each noun carries an adjective. Use ADJ slots: ADJ:agent_mod before NP:agent, ADJ:patient_mod before NP:patient (an ADJ slot matches adjectives gray, brown, quiet). IMPORTANT: write the literal 'the' before each ADJ slot, then the bare NP after it: the, ADJ:agent_mod, NP:agent. Meaning: the chase event PLUS agent_mod and patient_mod properties; tense present, polarity positive; verb form present_3sg ('chases')",
        "shape_hint": "the gray cat chases the brown dog.",
        "surface_meta": {
            "mood": "declarative"
        },
        "scaffold_semantics": {
            "frame": "event",
            "predicate": "@pred",
            "agent": "@agent",
            "patient": "@patient",
            "agent_mod": "@agent_mod",
            "patient_mod": "@patient_mod",
            "tense": "present",
            "polarity": "positive"
        },
        "example_sentence_hint": "shaped 'the gray cat chases the brown dog.' (adjectives: gray, brown, quiet)",
        "expected_core_hint": "{\"frame\": \"event\", \"predicate\": \"chase\", \"agent\": \"<X>\", \"patient\": \"<Y>\", \"tense\": \"present\", \"polarity\": \"positive\", \"agent_mod\": \"<ADJ1>\", \"patient_mod\": \"<ADJ2>\"}",
        "held_out": [
            {
                "sentence": "the brown fox chases the quiet hen.",
                "expected_core": {
                    "frame": "event",
                    "predicate": "chase",
                    "agent": "fox",
                    "patient": "hen",
                    "tense": "present",
                    "polarity": "positive",
                    "agent_mod": "brown",
                    "patient_mod": "quiet"
                }
            },
            {
                "sentence": "the quiet dog chases the gray cat.",
                "expected_core": {
                    "frame": "event",
                    "predicate": "chase",
                    "agent": "dog",
                    "patient": "cat",
                    "tense": "present",
                    "polarity": "positive",
                    "agent_mod": "quiet",
                    "patient_mod": "gray"
                }
            },
            {
                "sentence": "the gray chases cat the dog brown.",
                "expect": "no_parse"
            }
        ],
        "retention": [
            {
                "sentence": "the gray bird chases the brown hen.",
                "expected_core": {
                    "frame": "event",
                    "predicate": "chase",
                    "agent": "bird",
                    "patient": "hen",
                    "tense": "present",
                    "polarity": "positive",
                    "agent_mod": "gray",
                    "patient_mod": "brown"
                }
            }
        ],
        "probe": "the gray cat chases the brown dog."
    },
    {
        "construction_id": "interrogative_past_transitive",
        "lesson_id": "LIVE_L008_past_question",
        "description": "the PAST-TENSE yes/no QUESTION construction 'did the X VERB the Y?' - a question about an event with the verb as predicate (BASE form after 'did'), X as agent, Y as patient, tense PAST, polarity positive",
        "shape_hint": "did the X chase the Y?",
        "surface_meta": {
            "mood": "interrogative"
        },
        "scaffold_semantics": {
            "frame": "event",
            "predicate": "@pred",
            "agent": "@agent",
            "patient": "@patient",
            "tense": "past",
            "polarity": "positive"
        },
        "example_sentence_hint": "shaped 'did the X chase the Y?' ending with '?'",
        "expected_core_hint": "{\"frame\": \"event\", \"predicate\": \"chase\", \"agent\": \"<X>\", \"patient\": \"<Y>\", \"tense\": \"past\", \"polarity\": \"positive\"}",
        "held_out": [
            {
                "sentence": "did the fox chase the hen?",
                "expected_core": {
                    "frame": "event",
                    "predicate": "chase",
                    "agent": "fox",
                    "patient": "hen",
                    "tense": "past",
                    "polarity": "positive"
                }
            },
            {
                "sentence": "did the bird chase the cat?",
                "expected_core": {
                    "frame": "event",
                    "predicate": "chase",
                    "agent": "bird",
                    "patient": "cat",
                    "tense": "past",
                    "polarity": "positive"
                }
            },
            {
                "sentence": "did chase the fox the?",
                "expect": "no_parse"
            }
        ],
        "retention": [
            {
                "sentence": "did the hen chase the dog?",
                "expected_core": {
                    "frame": "event",
                    "predicate": "chase",
                    "agent": "hen",
                    "patient": "dog",
                    "tense": "past",
                    "polarity": "positive"
                }
            }
        ],
        "probe": "did the cat chase the dog?"
    },
]


def make_fields(target):
    def valid_examples(value, pattern, morphology):
        if not isinstance(value, list) or len(value) < 2:
            return "must be a JSON list of at least 2 items"
        for item in value:
            if not isinstance(item, dict) or "sentence" not in item \
                    or "expected_core" not in item:
                return "each item needs 'sentence' and 'expected_core'"
            if not isinstance(item["expected_core"], dict) \
                    or "frame" not in item["expected_core"]:
                return "expected_core must be an object with 'frame'"
        return structural_check([i["sentence"] for i in value],
                                pattern, morphology, must_match=True)

    def valid_counters(value, pattern, morphology):
        if not isinstance(value, list) or len(value) < 2:
            return "must be a JSON list of at least 2 items"
        for item in value:
            if not isinstance(item, dict) or "sentence" not in item:
                return "each item needs 'sentence'"
        return structural_check([i["sentence"] for i in value],
                                pattern, morphology, must_match=False)

    return [
        ("surface_pattern",
         "Two example surface_patterns from OTHER constructions this "
         "machine already learned: passive past = "
         '["NP:patient", "was", "VERB:pred:participle", "by", '
         '"NP:agent"] ; negated present = '
         '["NP:agent", "does", "not", "VERB:pred:base", '
         '"NP:patient"] . '
         "Note the verb is ALWAYS a VERB:pred:form slot, never the "
         "word chase itself. "
         f"Now give ONLY the surface_pattern JSON flat list for: "
         f"{target['description']} (shape: '{target['shape_hint']}').",
         lambda v, p=None, m=None: valid_pattern(v)),
        ("morphology",
         "Example morphology entry: "
         '[{"surface": "chased", "lemma": "chase", "form": '
         '"participle"}] '
         "Now give ONLY the morphology JSON list for the verb "
         "form(s) YOUR pattern needs (forms: base, past, participle, "
         "present_3sg; 'chases' is present_3sg of 'chase').",
         lambda v, p=None, m=None: valid_morphology(v)),
        ("positive_examples",
         "Give ONLY the positive_examples JSON list: 2 items, each "
         "{\"sentence\": ..., \"expected_core\": ...}. Each sentence "
         f"must match YOUR pattern ({target['example_sentence_hint']})"
         ", using ONLY nouns cat, dog, bird, fox, hen. expected_core "
         f"shaped like: {target['expected_core_hint']}.",
         valid_examples),
        ("minimal_pairs",
         "Give ONLY the minimal_pairs JSON list: 2 items "
         "{sentence_a, sentence_b, relation}, both relations "
         "'different_meaning' (for instance role-swapped versions).",
         lambda v, p=None, m=None: valid_pairs(v)),
        ("counterexamples",
         "Give ONLY the counterexamples JSON list: 2 items "
         "{sentence}. A counterexample is a BROKEN, scrambled string "
         "the construction must NOT match. Do NOT give any "
         "grammatical sentence.",
         valid_counters),
        ("ambiguity_cases",
         "Give ONLY the ambiguity_cases JSON list: 1 item {sentence, "
         "expect: 'parsed'}. The sentence MUST be one of YOUR OWN "
         "construction's sentences - simplest correct answer: reuse "
         "the first sentence from your positive_examples.",
         lambda v, p=None, m=None: (
             valid_ambiguity(v)
             or structural_check([i["sentence"] for i in v
                                  if i.get("expect") == "parsed"],
                                 p, m, must_match=True))),
    ]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    backend = os.environ.get("CAS_TEACHER_BACKEND", "local_gpu")

    if backend == "bedrock":
        # AWS door (standing owner order: 20B-class teachers on AWS).
        # Cloud GPU inference via the Bedrock converse API - no local
        # compute at all. Retries use temperature (the API has no
        # seed); every attempt is still logged and the ladder that
        # judges the result stays fully deterministic.
        import boto3
        region = os.environ.get("AWS_REGION", "us-west-2")
        runtime = boto3.Session().client("bedrock-runtime",
                                         region_name=region)
        snapshot = f"bedrock:{region}"
        print(f"teacher {TEACHER_MODEL} via AWS Bedrock ({region})")

        def ask(context, question, seed=None):
            response = runtime.converse(
                modelId=TEACHER_MODEL,
                system=[{"text": context}],
                messages=[{"role": "user",
                           "content": [{"text": question}]}],
                inferenceConfig={
                    "maxTokens": 900,
                    "temperature": 0.0 if seed is None else 0.7})
            text = response["output"]["message"]["content"][-1]["text"]
            # strip any reasoning block defensively
            text = re.sub(r"<think>.*?</think>", "", text,
                          flags=re.DOTALL)
            return text.strip()
    else:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        if not torch.cuda.is_available():
            raise SystemExit("REFUSING to run on CPU (standing owner "
                             "order). Use the CUDA venv or "
                             "RunPod/AWS.")

        base = os.path.expanduser(
            "~/.cache/huggingface/hub/models--"
            + TEACHER_MODEL.replace("/", "--") + "/snapshots")
        snapshot = sorted(glob.glob(os.path.join(base, "*")))[-1]
        print(f"teacher {TEACHER_MODEL} on "
              f"{torch.cuda.get_device_name(0)}")
        tokenizer = AutoTokenizer.from_pretrained(snapshot)
        model = AutoModelForCausalLM.from_pretrained(
            snapshot, dtype=torch.float16, device_map="cuda")
        model.eval()

        def ask(context, question, seed=None):
            messages = [{"role": "system", "content": context},
                        {"role": "user", "content": question}]
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(text, return_tensors="pt").to("cuda")
            kwargs = {"max_new_tokens": 450,
                      "pad_token_id": tokenizer.eos_token_id}
            if seed is None:
                kwargs["do_sample"] = False
            else:
                torch.manual_seed(seed)
                kwargs.update({"do_sample": True, "temperature": 0.7,
                               "top_p": 0.9})
            with torch.no_grad():
                out = model.generate(**inputs, **kwargs)
            return tokenizer.decode(
                out[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True).strip()

    from cortex.router import HybridRouter
    targets_file = os.environ.get("CAS_TARGETS_FILE")
    if targets_file:
        TARGETS.extend(json.load(open(targets_file,
                                      encoding="utf-8")))
    only = os.environ.get("CAS_TARGETS")
    targets = [t for t in TARGETS
               if only is None
               or t["construction_id"] in only.split(",")]
    results = []
    for target in targets:
        print(f"\n=== TEACHING {target['construction_id']} ===")
        # LEX subboard: lesson-scoped vocabulary enters the teaching
        # lexicon now; it persists to the runtime lexicon only on
        # durable promotion
        for word, entry in target.get("lexicon_additions", {}).items():
            CURRICULUM_LEX[word] = entry
        context = (
            "You are a grammar teacher for a symbolic language "
            "machine. Pattern slots: NP:agent / NP:patient (and "
            "NP:agent2 / NP:patient2 for a second clause) match "
            "'the NOUN'; VERB:pred:form (and VERB:pred2:form) match "
            "a verb in that form (base, past, participle, "
            "present_3sg); lowercase words are literal tokens. "
            f"Target: {target['description']} Nouns: cat, dog, bird, "
            "fox, hen. Verb: chase.")

        lesson = {"lesson_id": target["lesson_id"],
                  "lesson_type": "grammar_construction",
                  "teacher_model": TEACHER_MODEL,
                  "teacher_revision": os.path.basename(snapshot) if backend != "bedrock" else snapshot,
                  "teacher_confidence": None,
                  "provenance":
                      "schema_constrained_field_elicitation"}
        log = []
        pattern = None
        failed_field = None
        for field, question, validator in make_fields(target):
            accepted = None
            defect = None
            for attempt in range(1, 5):
                prompt = question
                if attempt > 1:
                    prompt += (f" Your previous answer was invalid: "
                               f"{defect}. Answer again, ONLY the "
                               f"JSON.")
                reply = ask(context, prompt,
                            seed=None if attempt == 1 else attempt)
                value = extract_json_value(reply)
                defect = ("not parseable as JSON" if value is None
                          else validator(value, pattern,
                                         lesson.get("morphology")))
                log.append({"field": field, "attempt": attempt,
                            "defect": defect, "raw": reply[:300]})
                print(f"  {field} attempt {attempt}: "
                      f"{'OK' if defect is None else defect}")
                if defect is None:
                    accepted = value
                    break
            if accepted is None:
                failed_field = field
                break
            lesson[field] = accepted
            if field == "surface_pattern":
                pattern = accepted

        if failed_field:
            results.append({"target": target["construction_id"],
                            "verdict":
                                f"ELICITATION_FAILED_{failed_field}",
                            "log": log})
            continue

        # semantics: fully determined by slots + task -> scaffold,
        # disclosed (same law as the negation round)
        lesson["semantics_provenance"] = \
            "derived_from_teacher_pattern_by_schema_scaffold"
        lesson["construction"] = {
            "construction_id": target["construction_id"],
            "surface_pattern": lesson.pop("surface_pattern"),
            "semantics": target["scaffold_semantics"],
            "surface_meta": target["surface_meta"],
        }
        defects = validate_construction(lesson["construction"])
        print(f"  assembled schema defects: {defects}")

        before = HybridRouter(mode="NATIVE_ONLY").turn(target["probe"])
        print(f"  BEFORE: {target['probe']!r} -> "
              f"{before['answer']['status']}")

        store = GrammarStore.load(SEED_GRAMMAR)
        morph = MorphTable()
        for surface, entry in json.load(
                open(SEED_MORPH, encoding="utf-8")).items():
            morph.teach(surface, entry["lemma"], entry["form"],
                        provenance=entry["provenance"])
        student = Apprentice(Lexicon(CURRICULUM_LEX), morph, store)
        board = ApprenticeshipBoard()

        def ladder(meta, _student=student, _lesson=lesson,
                   _held=target["held_out"]):
            outcome = _student.learn(_lesson, held_out_cases=_held)
            return {"verdict": outcome["verdict"],
                    "evidence": outcome["stages"],
                    "episode_digest": outcome["episode_digest"]}

        episode = board.teach(
            {"lesson_id": lesson["lesson_id"],
             "domain": "language_grammar", "target": "grammar_store",
             "teacher_model": TEACHER_MODEL,
             "teacher_revision": os.path.basename(snapshot) if backend != "bedrock" else snapshot,
             "teacher_role": "lecturer",
             "examiner_identity": "ccb_l1_acceptance_ladder",
             "provenance": "schema_constrained_field_elicitation"},
            ladder)
        verdict = episode["outcome"]["verdict"]
        print(f"  LADDER: {verdict}")

        after = None
        retention = None
        if verdict == "PROMOTED_PROVISIONALLY":
            retention = student.confirm_retention(
                target["construction_id"], target["retention"])
            print(f"  RETENTION: {retention['verdict']}")
            if retention["verdict"] == "PROMOTED_DURABLY":
                store.save(SEED_GRAMMAR)
                # save the student's MERGED morph table - NEVER the
                # raw lesson entries (save-path clobber bug: raw
                # 'chased: participle' overwrote the merged
                # past_or_participle on disk and the runtime FORGOT
                # active-past)
                merged = {surface: {"lemma": e["lemma"],
                                    "form": e["form"],
                                    "provenance": e["provenance"]}
                          for surface, e in
                          sorted(student.morph.to_json().items())}
                json.dump(merged,
                          open(SEED_MORPH, "w", encoding="utf-8"),
                          indent=1)
                if target.get("lexicon_additions"):
                    seed_payload = json.load(open(SEED_LEXICON,
                                                  encoding="utf-8"))
                    for word, entry in target[
                            "lexicon_additions"].items():
                        seed_payload["lexicon"].setdefault(word, entry)
                    json.dump(seed_payload,
                              open(SEED_LEXICON, "w",
                                   encoding="utf-8"), indent=1)
                after = HybridRouter(mode="NATIVE_ONLY").turn(
                    target["probe"])
                print(f"  AFTER:  {target['probe']!r} -> "
                      f"{after['answer']['status']}")

        results.append({"target": target["construction_id"],
                        "verdict": verdict,
                        "retention": retention,
                        "lesson": lesson, "episode": episode,
                        "before": before, "after": after,
                        "log": log})

    slug = TEACHER_MODEL.replace("/", "_").replace(":", "_")
    # PER-RUN filenames - a fixed name OVERWROTE the previous run's
    # sealed episodes (found live after the 20-lesson queue: only the
    # LAST single-target run's episode file survived)
    run_tag = "+".join(r["target"] for r in results)[:80]         or time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(HERE, "output",
                            f"curriculum_{slug}_{run_tag}.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"event": "CURRICULUM_ROUND_1",
                   "teacher": TEACHER_MODEL,
                   "results": results}, fh, indent=1, sort_keys=True,
                  default=str)
    print(f"\nsealed: {out_path}")
    for row in results:
        print(f"  {row['target']}: {row['verdict']}"
              + (f" -> {row['retention']['verdict']}"
                 if row.get("retention") else ""))


if __name__ == "__main__":
    main()
