"""SCHEMA-CONSTRAINED TEACHING: the 3B authors a lesson field by
field. Each field is a SMALL question with its own validator and up
to three attempts with typed feedback - the packet SYNTAX cannot end
up malformed, while the lesson CONTENT (pattern, semantics, examples,
contrasts) remains the teacher's own work.

The examiner is unchanged: the assembled packet still faces the full
ten-stage acceptance ladder with OUR protected held-out channel, then
delayed retention. If promoted DURABLY, the construction is saved
into the RUNTIME grammar store (seed_grammar.json) - and the machine
visibly knows something it did not know before. Before/after router
transcripts are captured as the proof.
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
from lang.apprentice import Apprentice  # noqa: E402
from lang.constructions import (GrammarStore, MorphTable,  # noqa: E402
                                validate_construction)
from lang.lexicon import Lexicon  # noqa: E402

TEACHER_MODEL = os.environ.get("CAS_TEACHER_MODEL",
                               "Qwen/Qwen2.5-3B-Instruct")
_SLUG = TEACHER_MODEL.split("/")[-1].lower().replace(".", "_")

SEED_GRAMMAR = os.path.join(LANE, "CCB_L1_v0.1", "fixtures",
                            "seed_grammar.json")
SEED_MORPH = os.path.join(LANE, "CCB_L1_v0.1", "fixtures",
                          "seed_morphology.json")

# teaching lexicon = runtime nouns + the extra teaching nouns
TEACHING_LEX = {
    "the": {"pos": "article", "sense": "the"},
    "cat": {"pos": "noun", "sense": "cat"},
    "dog": {"pos": "noun", "sense": "dog"},
    "bird": {"pos": "noun", "sense": "bird"},
    "fox": {"pos": "noun", "sense": "fox"},
    "hen": {"pos": "noun", "sense": "hen"},
}

HELD_OUT = [
    {"sentence": "the fox does not chase the hen.",
     "expected_core": {"frame": "event", "predicate": "chase",
                       "agent": "fox", "patient": "hen",
                       "tense": "present", "polarity": "negative"}},
    {"sentence": "the bird does not chase the cat.",
     "expected_core": {"frame": "event", "predicate": "chase",
                       "agent": "bird", "patient": "cat",
                       "tense": "present", "polarity": "negative"}},
    {"sentence": "the does not chase fox hen.", "expect": "no_parse"},
]

RETENTION = [
    {"sentence": "the hen does not chase the dog.",
     "expected_core": {"frame": "event", "predicate": "chase",
                       "agent": "hen", "patient": "dog",
                       "tense": "present", "polarity": "negative"}},
]

CONTEXT = (
    "You are a grammar teacher for a symbolic language machine. "
    "Constructions use pattern slots: NP slots are written "
    "NP:agent or NP:patient (the semantic ROLE is the slot name); "
    "'VERB:name:form' (THREE parts: the word VERB, a slot name like "
    "pred, and a form - base, past, or participle); lowercase words "
    "are literal tokens. Semantics reference slots as '@name'. "
    "The target construction: negated present transitive - "
    "'the X does not VERB the Y' meaning an event with the verb as "
    "predicate, X as agent, Y as patient, tense present, polarity "
    "negative. Nouns available: cat, dog, bird, fox, hen. Verb: "
    "chase (base form 'chase')."
)


# ----------------------------------------------------------------------
# per-field validators: typed defects, never silent acceptance
def valid_pattern(value):
    if not isinstance(value, list) or not value:
        return "must be a non-empty JSON list"
    has_np = has_verb = False
    for element in value:
        if not isinstance(element, str):
            return f"element {element!r} is not a string"
        if element.startswith("NP:"):
            parts = element.split(":")
            roles = ("agent", "patient", "recipient", "experiencer",
                     "instrument", "source", "destination", "location")
            if len(parts) != 2 or parts[1] not in roles:
                return (f"NP slot {element!r} must name a semantic "
                        f"ROLE from {roles}")
            has_np = True
        elif element.startswith("VERB:"):
            parts = element.split(":")
            if len(parts) != 3 or parts[1] != "pred" \
                    or parts[2] not in ("base", "past", "participle"):
                return (f"VERB slot {element!r} must be exactly "
                        f"VERB:pred:form with form in base/past/"
                        f"participle")
            has_verb = True
        elif not element.islower():
            return f"literal {element!r} must be lowercase"
    if not has_np or not has_verb:
        return "pattern needs at least one NP slot and one VERB slot"
    return None


def valid_semantics(value, pattern):
    if not isinstance(value, dict):
        return "must be a JSON object"
    slots = set()
    for element in pattern:
        if element.startswith("NP:"):
            slots.add(element.split(":")[1])
        elif element.startswith("VERB:"):
            slots.add(element.split(":")[1])
    for key in ("frame", "tense", "polarity"):
        if key not in value:
            return f"missing required key {key!r}"
    for key, ref in value.items():
        if isinstance(ref, str) and ref.startswith("@"):
            if ref[1:] not in slots:
                return (f"{ref!r} references no declared slot; declared "
                        f"slots are {sorted(slots)}")
    return None


def valid_examples(value, pattern=None, morphology=None):
    if not isinstance(value, list) or len(value) < 2:
        return "must be a JSON list of at least 2 items"
    for item in value:
        if not isinstance(item, dict) or "sentence" not in item \
                or "expected_core" not in item:
            return "each item needs 'sentence' and 'expected_core'"
        core = item["expected_core"]
        if not isinstance(core, dict) or "predicate" not in core:
            return "expected_core must be an object with 'predicate'"
        if core.get("frame") not in ("event", "state"):
            return "expected_core.frame must be 'event' or 'state'"
    # STRUCTURAL pre-check: each sentence must actually match the
    # teacher's own pattern (typed feedback beats a late COMPILED
    # rejection; the ladder still owns the real examination)
    if pattern:
        from lang.constructions import ConstructionParser, MorphTable
        morph = MorphTable()
        for entry in morphology or []:
            morph.teach(entry["surface"], entry["lemma"],
                        entry["form"], provenance="field_check")
        parser = ConstructionParser(Lexicon(TEACHING_LEX), morph)
        rule = {"construction_id": "field_check",
                "surface_pattern": pattern,
                "semantics": {"frame": "event", "tense": "present",
                              "polarity": "negative"}}
        for item in value:
            if parser.match(rule, item["sentence"]) is None:
                return (f"sentence {item['sentence']!r} does not "
                        f"match YOUR pattern {pattern}; remember "
                        f"NP slots already consume 'the NOUN', and "
                        f"only lexicon nouns (cat, dog, bird, fox, "
                        f"hen) can fill them")
    return None


def valid_pairs(value, _pattern=None):
    if not isinstance(value, list) or len(value) < 2:
        return "must be a JSON list of at least 2 items"
    for item in value:
        if not isinstance(item, dict) or not all(
                k in item for k in ("sentence_a", "sentence_b",
                                    "relation")):
            return "each item needs sentence_a, sentence_b, relation"
        if item["relation"] not in ("same_meaning",
                                    "different_meaning"):
            return "relation must be same_meaning or different_meaning"
    return None


def valid_counters(value, pattern=None, morphology=None):
    if not isinstance(value, list) or len(value) < 2:
        return "must be a JSON list of at least 2 items"
    for item in value:
        if not isinstance(item, dict) or "sentence" not in item:
            return "each item needs 'sentence'"
    # STRUCTURAL pre-check: a counterexample must NOT match the
    # teacher's own pattern (mirror of the positives pre-check)
    if pattern:
        from lang.constructions import ConstructionParser, MorphTable
        morph = MorphTable()
        for entry in morphology or []:
            morph.teach(entry["surface"], entry["lemma"],
                        entry["form"], provenance="field_check")
        parser = ConstructionParser(Lexicon(TEACHING_LEX), morph)
        rule = {"construction_id": "field_check",
                "surface_pattern": pattern,
                "semantics": {"frame": "event", "tense": "present",
                              "polarity": "negative"}}
        for item in value:
            if parser.match(rule, item["sentence"]) is not None:
                return (f"{item['sentence']!r} is a GRAMMATICAL "
                        f"sentence your pattern matches - a "
                        f"counterexample must be BROKEN (scrambled "
                        f"or missing words) so it does NOT match")
    return None


def valid_ambiguity(value, _pattern=None):
    if not isinstance(value, list) or len(value) < 1:
        return "must be a JSON list of at least 1 item"
    for item in value:
        if not isinstance(item, dict) or "sentence" not in item \
                or item.get("expect") not in ("parsed",
                                              "ambiguous_or_unknown"):
            return ("each item needs 'sentence' and 'expect' in "
                    "parsed/ambiguous_or_unknown")
    return None


def valid_morphology(value, _pattern=None):
    if not isinstance(value, list) or not value:
        return "must be a non-empty JSON list"
    for item in value:
        if not isinstance(item, dict) or not all(
                k in item for k in ("surface", "lemma", "form")):
            return "each item needs surface, lemma, form"
    return None


FIELDS = [
    ("surface_pattern",
     "Example surface_pattern for a DIFFERENT construction (passive "
     "past, 'the Y was VERBed by the X'): "
     '["NP:patient", "was", "VERB:pred:participle", "by", "NP:agent"]'
     " Now give ONLY the surface_pattern JSON list (a FLAT list of "
     "strings) for the negated present construction "
     "'the X does not VERB the Y'.",
     valid_pattern),
    ("semantics",
     "Example semantics for the passive-past construction: "
     '{"frame": "event", "predicate": "@pred", "agent": "@agent", '
     '"patient": "@patient", "tense": "past", "polarity": "positive"}'
     " Now give ONLY the semantics JSON object for YOUR negated "
     "present construction, using @references to YOUR pattern's slot "
     "names.",
     valid_semantics),
    ("morphology",
     "Example morphology entry: "
     '[{"surface": "chased", "lemma": "chase", "form": "participle"}]'
     " Now give ONLY the morphology JSON list for the verb form "
     "YOUR pattern needs (the base form).",
     valid_morphology),
    ("positive_examples",
     "Give ONLY the positive_examples JSON list: 2 items, each "
     "{\"sentence\": ..., \"expected_core\": {\"frame\": \"event\", "
     "\"predicate\": ..., \"agent\": ..., \"patient\": ..., "
     "\"tense\": \"present\", \"polarity\": \"negative\"}}. Each "
     "sentence must be a NEGATED sentence that YOUR pattern matches "
     "(shaped 'the X does not chase the Y.'), using ONLY the nouns "
     "cat, dog, bird, fox, hen. Sentences end with '.'.",
     valid_examples),
    ("minimal_pairs",
     "Give ONLY the minimal_pairs JSON list: 2 items "
     "{sentence_a, sentence_b, relation}. Pair 1: the negated "
     "sentence vs its positive counterpart (different_meaning). "
     "Pair 2: the negated sentence vs its role-reversed negation "
     "(different_meaning).",
     valid_pairs),
    ("counterexamples",
     "Give ONLY the counterexamples JSON list: 2 items {sentence}. "
     "A counterexample is a BROKEN, ungrammatical string the "
     "construction must NOT match - scrambled word order or missing "
     "words (for instance shaped like 'not chase the cat does the "
     "dog.'). Do NOT give any grammatical sentence.",
     valid_counters),
    ("ambiguity_cases",
     "Give ONLY the ambiguity_cases JSON list: 1 item {sentence, "
     "expect: 'parsed'} using a clearly well-formed negated sentence.",
     valid_ambiguity),
]


def extract_json_value(text):
    for pattern in (r"\[.*\]", r"\{.*\}"):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
    return None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    if not torch.cuda.is_available():
        raise SystemExit("REFUSING to run on CPU (standing owner "
                         "order). Use the CUDA venv or RunPod/AWS.")

    base = os.path.expanduser(
        "~/.cache/huggingface/hub/models--"
        + TEACHER_MODEL.replace("/", "--") + "/snapshots")
    snapshot = sorted(glob.glob(os.path.join(base, "*")))[-1]
    print(f"teacher {TEACHER_MODEL} on {torch.cuda.get_device_name(0)}")
    tokenizer = AutoTokenizer.from_pretrained(snapshot)
    model = AutoModelForCausalLM.from_pretrained(
        snapshot, dtype=torch.float16, device_map="cuda")
    model.eval()

    def ask(question):
        messages = [{"role": "system", "content": CONTEXT},
                    {"role": "user", "content": question}]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to("cuda")
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=400,
                                 do_sample=False,
                                 pad_token_id=tokenizer.eos_token_id)
        return tokenizer.decode(out[0][inputs["input_ids"].shape[1]:],
                                skip_special_tokens=True).strip()

    # ---------------- field-wise elicitation with typed retries
    lesson = {"lesson_id": "LIVE_L002_negation_constrained",
              "lesson_type": "grammar_construction",
              "teacher_model": TEACHER_MODEL,
              "teacher_revision": os.path.basename(snapshot),
              "teacher_confidence": None,
              "provenance": "schema_constrained_field_elicitation"}
    elicitation_log = []
    pattern_so_far = None
    for field, question, validator in FIELDS:
        accepted = None
        for attempt in range(1, 4):
            prompt = question if attempt == 1 else (
                question + f"\nYour previous answer was invalid: "
                           f"{defect}. Answer again, ONLY the JSON.")
            reply = ask(prompt)
            value = extract_json_value(reply)
            if value is None:
                defect = "not parseable as JSON"
            elif field == "surface_pattern":
                defect = validator(value)
            elif field in ("positive_examples", "counterexamples"):
                defect = validator(value, pattern_so_far,
                                   lesson.get("morphology"))
            else:
                defect = validator(value, pattern_so_far)
            elicitation_log.append({"field": field, "attempt": attempt,
                                    "defect": defect,
                                    "raw": reply[:400]})
            print(f"  {field} attempt {attempt}: "
                  f"{'OK' if defect is None else defect}")
            if defect is None:
                accepted = value
                break
        if accepted is None and field == "semantics":
            # This field is FULLY DETERMINED by the declared slots +
            # the task (one valid answer exists). Token-constrained
            # decoding would emit it by masking; we derive it
            # mechanically and DISCLOSE the scaffold in provenance.
            # The teacher's contributions remain the pattern and all
            # example content; the ladder still examines everything.
            accepted = {"frame": "event", "predicate": "@pred",
                        "agent": "@agent", "patient": "@patient",
                        "tense": "present", "polarity": "negative"}
            lesson["semantics_provenance"] = \
                "derived_from_teacher_pattern_by_schema_scaffold"
            elicitation_log.append(
                {"field": field, "attempt": "scaffold",
                 "defect": None,
                 "raw": "derived mechanically from declared slots"})
            print("  semantics: derived by schema scaffold "
                  "(teacher garbled @-syntax 3x; disclosed)")
        if accepted is None:
            _seal_failure(lesson, elicitation_log, field)
            return
        lesson[field] = accepted
        if field == "surface_pattern":
            pattern_so_far = accepted

    lesson["construction"] = {
        "construction_id": "negated_present_transitive",
        "surface_pattern": lesson.pop("surface_pattern"),
        "semantics": lesson.pop("semantics"),
        "surface_meta": {"polarity_marker": "does_not"},
    }
    schema_defects = validate_construction(lesson["construction"])
    print(f"assembled construction schema defects: {schema_defects}")

    # ---------------- BEFORE transcript (the runtime as it is now)
    from cortex.router import HybridRouter
    probe = "the cat does not chase the dog."
    before_router = HybridRouter(mode="NATIVE_ONLY")
    before = before_router.turn(probe)
    print(f"BEFORE: {probe!r} -> {before['answer']['status']} "
          f"(route {before['route']})")

    # ---------------- the unchanged examiner: the full ladder
    store = GrammarStore.load(SEED_GRAMMAR)
    morph = MorphTable()
    for surface, entry in json.load(open(SEED_MORPH,
                                         encoding="utf-8")).items():
        morph.teach(surface, entry["lemma"], entry["form"],
                    provenance=entry["provenance"])
    student = Apprentice(Lexicon(TEACHING_LEX), morph, store)
    board = ApprenticeshipBoard()

    def ladder(meta):
        result = student.learn(lesson, held_out_cases=HELD_OUT)
        return {"verdict": result["verdict"],
                "evidence": result["stages"],
                "episode_digest": result["episode_digest"]}

    episode = board.teach(
        {"lesson_id": lesson["lesson_id"],
         "domain": "language_grammar", "target": "grammar_store",
         "teacher_model": TEACHER_MODEL,
         "teacher_revision": os.path.basename(snapshot),
         "teacher_role": "lecturer",
         "examiner_identity": "ccb_l1_acceptance_ladder",
         "provenance": "schema_constrained_field_elicitation"},
        ladder)
    verdict = episode["outcome"]["verdict"]
    print(f"LADDER VERDICT: {verdict}")

    after = None
    retention = None
    if verdict == "PROMOTED_PROVISIONALLY":
        retention = student.confirm_retention(
            "negated_present_transitive", RETENTION)
        print(f"RETENTION: {retention['verdict']}")
        if retention["verdict"] == "PROMOTED_DURABLY":
            # the machine KEEPS what it learned: save the runtime store
            store.save(SEED_GRAMMAR)
            morph_payload = json.load(open(SEED_MORPH,
                                           encoding="utf-8"))
            for entry in lesson.get("morphology", []):
                morph_payload[entry["surface"]] = {
                    "lemma": entry["lemma"], "form": entry["form"],
                    "provenance": f"lesson:{lesson['lesson_id']}"}
            json.dump(morph_payload, open(SEED_MORPH, "w",
                                          encoding="utf-8"), indent=1)
            # ---------------- AFTER transcript (fresh runtime)
            after_router = HybridRouter(mode="NATIVE_ONLY")
            after = after_router.turn(probe)
            print(f"AFTER:  {probe!r} -> {after['answer']['status']} "
                  f"(route {after['route']})")
            if after["answer"].get("core"):
                print(f"        core: {after['answer']['core']}")

    artifact = {
        "event": "SCHEMA_CONSTRAINED_LIVE_TEACHING",
        "teacher": TEACHER_MODEL,
        "teacher_snapshot": os.path.basename(snapshot),
        "elicitation_log": elicitation_log,
        "assembled_lesson": lesson,
        "ladder_episode": episode,
        "retention": retention,
        "before_transcript": before,
        "after_transcript": after,
    }
    out_path = os.path.join(HERE, "output",
                            f"constrained_teaching_{_SLUG}.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=1, sort_keys=True, default=str)
    print(f"sealed: {out_path}")


def _seal_failure(lesson, log, field):
    artifact = {"event": "SCHEMA_CONSTRAINED_LIVE_TEACHING",
                "teacher": TEACHER_MODEL,
                "verdict": f"ELICITATION_FAILED_{field}",
                "elicitation_log": log}
    out_path = os.path.join(HERE, "output",
                            f"constrained_teaching_{_SLUG}.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=1, sort_keys=True)
    print(f"ELICITATION FAILED at {field}; sealed: {out_path}")


if __name__ == "__main__":
    main()
