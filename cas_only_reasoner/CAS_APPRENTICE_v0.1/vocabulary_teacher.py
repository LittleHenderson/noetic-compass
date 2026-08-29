"""VOCABULARY LESSONS (goal lessons 18-19): pure LEX+MORPH teaching -
no new construction. The teacher proposes word entries; the examiner
is GENERALIZATION THROUGH EXISTING CONSTRUCTIONS: unseen sentences
using the new words must parse to the exact cores OUR protected
channel expects, every prior regression guard must still hold, and
the merge law protects prior knowledge. One sealed episode per
lesson, rejections included.

Mini-ladder: PROPOSED -> SCHEMA_VALID -> MERGE_SAFE ->
HELD_OUT_GENERALIZATION_PASS -> PRIOR_KNOWLEDGE_REGRESSION_PASS ->
PROMOTED_PROVISIONALLY -> DELAYED_RETENTION -> PROMOTED_DURABLY

Teacher inference is cloud GPU (AWS Bedrock) per the standing
never-CPU order.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(LANE, "CCB_L1_v0.1"))
sys.path.insert(0, os.path.join(LANE, "CAS_CORTEX_v0.1"))

from apprentice.board import ApprenticeshipBoard  # noqa: E402
from constrained_teacher import (extract_json_value,  # noqa: E402
                                 valid_morphology)
from curriculum_teacher import CURRICULUM_LEX  # noqa: E402
from lang.constructions import (ConstructionParser, GrammarStore,  # noqa: E402
                                MorphTable)
from lang.lexicon import Lexicon  # noqa: E402

TEACHER_MODEL = os.environ.get("CAS_TEACHER_MODEL",
                               "qwen.qwen3-32b-v1:0")
SEED_GRAMMAR = os.path.join(LANE, "CCB_L1_v0.1", "fixtures",
                            "seed_grammar.json")
SEED_MORPH = os.path.join(LANE, "CCB_L1_v0.1", "fixtures",
                          "seed_morphology.json")
SEED_LEXICON = os.path.join(LANE, "CCB_L1_v0.1", "fixtures",
                            "seed_lexicon.json")


def _ev(pred, agent, patient, tense="present", polarity="positive",
        **extra):
    base = {"frame": "event", "predicate": pred, "agent": agent,
            "patient": patient, "tense": tense, "polarity": polarity}
    base.update(extra)
    return base


def _valid_carry_morphology(value):
    defect = valid_morphology(value)
    if defect:
        return defect
    by_form = {}
    for entry in value:
        if entry["lemma"] != "carry":
            return (f"every entry's lemma must be 'carry' - got "
                    f"{entry['lemma']!r}")
        by_form.setdefault(entry["form"], set()).add(entry["surface"])
    if "carry" not in by_form.get("base", set()):
        return "missing: 'carry' as form 'base'"
    if "carries" not in by_form.get("present_3sg", set()):
        return "missing: 'carries' as form 'present_3sg'"
    past_ok = "carried" in (by_form.get("past", set())
                            | by_form.get("participle", set())
                            | by_form.get("past_or_participle", set()))
    if not past_ok:
        return ("missing: 'carried' as form 'past' and as form "
                "'participle' (two entries, or one "
                "'past_or_participle')")
    return None


def _valid_adjectives(value):
    if not isinstance(value, dict):
        return "must be a JSON OBJECT mapping word -> entry"
    if sorted(value.keys()) != ["large", "small"]:
        return ("the object must have exactly the keys 'small' and "
                "'large'")
    for word, entry in value.items():
        if entry != {"pos": "adj", "sense": word}:
            return (f"entry for {word!r} must be exactly "
                    f'{{"pos": "adj", "sense": "{word}"}}')
    return None


VOCAB_TARGETS = [
    {
        "lesson_id": "LIVE_L026_new_verb",
        "kind": "morphology",
        "field": "morphology",
        "question": (
            "The machine already knows the verbs chase and give in "
            "the forms base, past, participle, present_3sg. Teach it "
            "the NEW verb 'carry'. Example morphology entry format: "
            '[{"surface": "chased", "lemma": "chase", "form": '
            '"past"}] . '
            "Give ONLY the morphology JSON list covering ALL forms "
            "of 'carry': base 'carry', present_3sg 'carries', past "
            "'carried', participle 'carried' (lemma is always "
            "'carry')."),
        "validator": _valid_carry_morphology,
        "lexicon_additions": {},
        "held_out": [
            {"sentence": "the cat carries the bone to the dog.",
             "expected_core": _ev("carry", "cat", "bone",
                                  recipient="dog")},
            {"sentence": "the cats carry the dog.",
             "expected_core": _ev("carry", "cat", "dog",
                                  agent_number="plural")},
            {"sentence": "did the fox carry the hen?",
             "expected_core": _ev("carry", "fox", "hen",
                                  tense="past")},
            {"sentence": "the dog was carried by the cat.",
             "expected_core": _ev("carry", "cat", "dog",
                                  tense="past")},
            {"sentence": "the cat carrys the dog.",
             "expect": "no_parse"},
        ],
        "retention": [
            {"sentence": "the hen carries the bone to the bird.",
             "expected_core": _ev("carry", "hen", "bone",
                                  recipient="bird")},
        ],
        "probe": "the cat carries the bone to the dog.",
    },
    {
        "lesson_id": "LIVE_L027_new_adjectives",
        "kind": "lexicon",
        "field": "lexicon_entries",
        "question": (
            "The machine already knows the adjectives gray, brown, "
            "quiet. Teach it the NEW adjectives 'small' and 'large'. "
            "Give ONLY a JSON object mapping each word to its entry, "
            'exactly: {"small": {"pos": "adj", "sense": "small"}, '
            '"large": {"pos": "adj", "sense": "large"}}'),
        "validator": _valid_adjectives,
        "held_out": [
            {"sentence": "the small cat chases the large dog.",
             "expected_core": _ev("chase", "cat", "dog",
                                  agent_mod="small",
                                  patient_mod="large")},
            {"sentence": "the large fox chases the small hen.",
             "expected_core": _ev("chase", "fox", "hen",
                                  agent_mod="large",
                                  patient_mod="small")},
            {"sentence": "is the small cat quiet?",
             "expected_core": {"frame": "state", "entity": "cat",
                               "modifier": "small",
                               "property": "quiet",
                               "tense": "present",
                               "polarity": "positive"}},
            {"sentence": "the smallly cat chases the dog.",
             "expect": "no_parse"},
        ],
        "retention": [
            {"sentence": "the small dog chases the large bird.",
             "expected_core": _ev("chase", "dog", "bird",
                                  agent_mod="small",
                                  patient_mod="large")},
        ],
        "probe": "the small cat chases the large dog.",
    },
]


def _load_runtime(extra_morph=None, extra_lex=None):
    """The runtime's accumulated knowledge + the lesson's proposal."""
    store = GrammarStore.load(SEED_GRAMMAR)
    morph = MorphTable()
    for surface, entry in json.load(
            open(SEED_MORPH, encoding="utf-8")).items():
        morph.teach(surface, entry["lemma"], entry["form"],
                    provenance=entry["provenance"])
    merge_defects = []
    for entry in extra_morph or []:
        try:
            morph.teach(entry["surface"], entry["lemma"],
                        entry["form"],
                        provenance=f"lesson:{TEACHER_MODEL}")
        except Exception as exc:
            merge_defects.append(str(exc))
    lex = dict(CURRICULUM_LEX)
    lex.update(json.load(
        open(SEED_LEXICON, encoding="utf-8"))["lexicon"])
    lex.update(extra_lex or {})
    parser = ConstructionParser(Lexicon(lex), morph)
    return store, morph, parser, merge_defects


def _parse_core(parser, rules, sentence):
    result = parser.parse(rules, sentence)
    if result["status"] != "PARSED":
        return None
    return result["core"]


def _examine(parser, rules, cases):
    failures = []
    for case in cases:
        core = _parse_core(parser, rules, case["sentence"])
        if case.get("expect") == "no_parse":
            if core is not None:
                failures.append(f"should not parse: "
                                f"{case['sentence']!r}")
        elif core != case["expected_core"]:
            failures.append(f"miss: {case['sentence']!r} -> {core}")
    return failures


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if os.environ.get("CAS_TEACHER_BACKEND", "bedrock") != "bedrock":
        raise SystemExit("vocabulary lessons run on the Bedrock "
                         "teacher (standing never-CPU order)")
    import boto3
    region = os.environ.get("AWS_REGION", "us-west-2")
    runtime = boto3.Session().client("bedrock-runtime",
                                     region_name=region)
    snapshot = f"bedrock:{region}"
    print(f"teacher {TEACHER_MODEL} via AWS Bedrock ({region})")

    def ask(question, seed=None):
        response = runtime.converse(
            modelId=TEACHER_MODEL,
            system=[{"text": "You are a vocabulary teacher for a "
                             "symbolic language machine. Answer with "
                             "ONLY the JSON asked for - no prose."}],
            messages=[{"role": "user", "content": [{"text": question}]}],
            inferenceConfig={"maxTokens": 900,
                             "temperature": 0.0 if seed is None
                             else 0.7})
        text = response["output"]["message"]["content"][-1]["text"]
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        return text.strip()

    from cortex.router import HybridRouter

    only = os.environ.get("CAS_TARGETS")
    results = []
    for target in VOCAB_TARGETS:
        if only and target["lesson_id"] not in only.split(","):
            continue
        print(f"\n=== TEACHING {target['lesson_id']} ===")
        log = []
        accepted = None
        question = target["question"]
        for attempt in range(1, 5):
            reply = ask(question if attempt == 1
                        else question + " Previous attempt was "
                        f"rejected: {log[-1]['defect']}",
                        seed=None if attempt == 1 else attempt)
            value = extract_json_value(reply)
            defect = ("no JSON found" if value is None
                      else target["validator"](value))
            log.append({"attempt": attempt, "defect": defect,
                        "raw": reply[:300]})
            print(f"  {target['field']} attempt {attempt}: "
                  f"{'OK' if defect is None else defect}")
            if defect is None:
                accepted = value
                break
        if accepted is None:
            results.append({"lesson_id": target["lesson_id"],
                            "verdict": "ELICITATION_FAILED",
                            "log": log})
            continue

        extra_morph = accepted if target["kind"] == "morphology" \
            else []
        extra_lex = accepted if target["kind"] == "lexicon" else {}

        before = HybridRouter(mode="NATIVE_ONLY").turn(target["probe"])
        print(f"  BEFORE: {target['probe']!r} -> "
              f"{before['answer']['status']}")

        board = ApprenticeshipBoard()

        def ladder(meta, _target=target, _morph=extra_morph,
                   _lex=extra_lex):
            evidence = [{"stage": "PROPOSED", "passed": True,
                         "detail": "typed vocabulary proposal "
                                   "complete"},
                        {"stage": "SCHEMA_VALID", "passed": True,
                         "detail": "entries validated field-wise"}]
            store, morph, parser, merge_defects = _load_runtime(
                _morph, _lex)
            evidence.append({"stage": "MERGE_SAFE",
                             "passed": not merge_defects,
                             "detail": "; ".join(merge_defects)
                             or "merge law held - no prior knowledge "
                                "overwritten"})
            if merge_defects:
                return {"verdict": "REJECTED_MERGE_CONFLICT",
                        "evidence": evidence, "episode_digest": ""}
            rules = store.active_rules()
            failures = _examine(parser, rules, _target["held_out"])
            evidence.append(
                {"stage": "HELD_OUT_GENERALIZATION_PASS",
                 "passed": not failures,
                 "detail": "; ".join(failures)
                 or f"{len(_target['held_out'])} unseen cases parse "
                    f"through EXISTING constructions"})
            if failures:
                return {"verdict": "REJECTED_HELD_OUT",
                        "evidence": evidence, "episode_digest": ""}
            regressions = []
            for prior in rules:
                for guard in prior.get("regression_guard", []):
                    bindings = parser.match(prior, guard["sentence"])
                    core = (parser.realize(prior, bindings)["core"]
                            if bindings is not None else None)
                    if core != guard["expected_core"]:
                        regressions.append(
                            f"regression on "
                            f"{prior['construction_id']}: "
                            f"{guard['sentence']!r}")
            evidence.append(
                {"stage": "PRIOR_KNOWLEDGE_REGRESSION_PASS",
                 "passed": not regressions,
                 "detail": "; ".join(regressions)
                 or "every prior regression guard still holds"})
            if regressions:
                return {"verdict": "REJECTED_REGRESSION",
                        "evidence": evidence, "episode_digest": ""}
            return {"verdict": "PROMOTED_PROVISIONALLY",
                    "evidence": evidence, "episode_digest": ""}

        episode = board.teach(
            {"lesson_id": target["lesson_id"],
             "domain": "language_vocabulary",
             "target": "morph_table+lexicon",
             "teacher_model": TEACHER_MODEL,
             "teacher_revision": snapshot,
             "teacher_role": "lecturer",
             "examiner_identity":
                 "vocabulary_generalization_examiner",
             "provenance": "schema_constrained_field_elicitation"},
            ladder)
        verdict = episode["outcome"]["verdict"]
        print(f"  LADDER: {verdict}")

        after = None
        retention = None
        if verdict == "PROMOTED_PROVISIONALLY":
            # delayed retention: a FRESH runtime load must still parse
            # the retention cases
            store, morph, parser, _ = _load_runtime(extra_morph,
                                                    extra_lex)
            failures = _examine(parser, store.active_rules(),
                                target["retention"])
            retention = {"verdict": "PROMOTED_DURABLY"
                         if not failures else "RETENTION_FAILED",
                         "failures": failures}
            print(f"  RETENTION: {retention['verdict']}")
            if retention["verdict"] == "PROMOTED_DURABLY":
                # persist: MERGED morph (never raw), lexicon setdefault
                _, morph, _, _ = _load_runtime(extra_morph, {})
                merged = {surface: {"lemma": e["lemma"],
                                    "form": e["form"],
                                    "provenance": e["provenance"]}
                          for surface, e in
                          sorted(morph.to_json().items())}
                json.dump(merged, open(SEED_MORPH, "w",
                                       encoding="utf-8"), indent=1)
                if extra_lex:
                    seed_payload = json.load(open(SEED_LEXICON,
                                                  encoding="utf-8"))
                    for word, entry in extra_lex.items():
                        seed_payload["lexicon"].setdefault(word,
                                                           entry)
                    json.dump(seed_payload,
                              open(SEED_LEXICON, "w",
                                   encoding="utf-8"), indent=1)
                after = HybridRouter(mode="NATIVE_ONLY").turn(
                    target["probe"])
                print(f"  AFTER:  {target['probe']!r} -> "
                      f"{after['answer']['status']}")

        results.append({"lesson_id": target["lesson_id"],
                        "verdict": verdict, "retention": retention,
                        "proposal": accepted, "episode": episode,
                        "before": before, "after": after,
                        "log": log})

    slug = TEACHER_MODEL.replace("/", "_").replace(":", "_")
    run_tag = "+".join(r["lesson_id"] for r in results)[:80] or "run"
    out_path = os.path.join(HERE, "output",
                            f"vocabulary_{slug}_{run_tag}.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"event": "VOCABULARY_LESSONS",
                   "teacher": TEACHER_MODEL, "results": results},
                  fh, indent=1, sort_keys=True, default=str)
    print(f"\nsealed: {out_path}")
    for row in results:
        print(f"  {row['lesson_id']}: {row['verdict']}"
              + (f" -> {row['retention']['verdict']}"
                 if row.get("retention") else ""))


if __name__ == "__main__":
    main()
