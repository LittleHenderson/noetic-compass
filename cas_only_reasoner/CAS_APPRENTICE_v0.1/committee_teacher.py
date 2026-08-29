"""GOAL LESSON 20: the FIRST LIVE MULTI-TEACHER COMMITTEE LESSON.

Two live models with distinct identities: the PROPOSER
(qwen.qwen3-32b-v1:0, role lecturer) authors the lesson through the
same schema-constrained field elicitation; the CRITIC
(deepseek.v3-v1:0, role critic - a different model family) reviews
the assembled lesson packet and records an explicit vote. The board
validates the committee (composition, explicit votes, any reject
blocks typed); committee approval grants NOTHING - the student's
ten-stage acceptance ladder remains the final examiner.

The lesson content is a NORM construction ('the cat must not chase
the dog.' - prohibition modality), classified under the high-impact
domain behavioral_norms, which is exactly the kind of lesson the
faculty-committee rule exists for.

All inference is cloud GPU (AWS Bedrock) per the standing never-CPU
order.
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
from constrained_teacher import extract_json_value  # noqa: E402
from curriculum_teacher import (CURRICULUM_LEX, SEED_GRAMMAR,  # noqa: E402
                                SEED_MORPH, make_fields)
from lang.apprentice import Apprentice  # noqa: E402
from lang.constructions import (GrammarStore, MorphTable,  # noqa: E402
                                validate_construction)
from lang.lexicon import Lexicon  # noqa: E402

PROPOSER = os.environ.get("CAS_TEACHER_MODEL", "qwen.qwen3-32b-v1:0")
CRITIC = os.environ.get("CAS_CRITIC_MODEL", "deepseek.v3-v1:0")


def _ev(pred, agent, patient, **extra):
    base = {"frame": "event", "predicate": pred, "agent": agent,
            "patient": patient, "tense": "present",
            "polarity": "positive", "modality": "prohibition"}
    base.update(extra)
    return base


TARGET = {
    "construction_id": "prohibited_transitive",
    "lesson_id": "LIVE_L028_committee_prohibition",
    "description": (
        "the PROHIBITION construction 'the cat must not chase the "
        "dog.' - a NORM saying the chase is forbidden. Pattern "
        "order: NP:agent, literal 'must', literal 'not', "
        "VERB:pred:base, literal 'the', NP:patient. Meaning: an "
        "event with tense present, polarity POSITIVE (the norm "
        "itself is asserted - this is NOT the same as 'does not "
        "chase', which is polarity negative), plus modality "
        "'prohibition'"),
    "shape_hint": "the cat must not chase the dog.",
    "surface_meta": {"mood": "declarative",
                     "modality_marker": "must_not"},
    "scaffold_semantics": {
        "frame": "event", "predicate": "@pred", "agent": "@agent",
        "patient": "@patient", "tense": "present",
        "polarity": "positive", "modality": "prohibition"},
    "example_sentence_hint": ("shaped 'the X must not chase the "
                              "Y.'"),
    "expected_core_hint": json.dumps(_ev("chase", "<X>", "<Y>")),
    "held_out": [
        {"sentence": "the fox must not chase the hen.",
         "expected_core": _ev("chase", "fox", "hen")},
        {"sentence": "the dog must not chase the cat.",
         "expected_core": _ev("chase", "dog", "cat")},
        {"sentence": "must the not cat chase dog the.",
         "expect": "no_parse"},
    ],
    "retention": [
        {"sentence": "the hen must not chase the bird.",
         "expected_core": _ev("chase", "hen", "bird")},
    ],
    "probe": "the cat must not chase the dog.",
}

CRITIC_QUESTION = (
    "You are the CRITIC on a two-model teaching committee for a "
    "symbolic language machine. Another model authored this lesson. "
    "Review it against the target and vote.\n"
    "TARGET: {description}\n"
    "LESSON PACKET: {lesson}\n"
    "Checklist: (1) does the surface_pattern have exactly the "
    "described order of slots and literals? (2) does every positive "
    "example match that pattern and pair with a plausible "
    "expected_core? (3) are the counterexamples truly broken "
    "strings? (4) do the minimal pairs differ in meaning? "
    "Answer with ONLY this JSON and nothing else: "
    '{{"vote": "approve"}} or {{"vote": "reject", "reasons": '
    '["..."]}}')


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    import boto3
    region = os.environ.get("AWS_REGION", "us-west-2")
    runtime = boto3.Session().client("bedrock-runtime",
                                     region_name=region)
    snapshot = f"bedrock:{region}"
    print(f"proposer {PROPOSER} + critic {CRITIC} "
          f"via AWS Bedrock ({region})")

    def ask(model, context, question, seed=None):
        response = runtime.converse(
            modelId=model,
            system=[{"text": context}],
            messages=[{"role": "user", "content": [{"text": question}]}],
            inferenceConfig={"maxTokens": 900,
                             "temperature": 0.0 if seed is None
                             else 0.7})
        text = response["output"]["message"]["content"][-1]["text"]
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        return text.strip()

    from cortex.router import HybridRouter

    target = TARGET
    context = (
        "You are a grammar teacher for a symbolic language machine. "
        "Pattern slots: NP:agent / NP:patient match 'the NOUN'; "
        "VERB:pred:form matches a verb in that form (base, past, "
        "participle, present_3sg); lowercase words are literal "
        f"tokens. Target: {target['description']} Nouns: cat, dog, "
        "bird, fox, hen. Answer every question with ONLY the JSON "
        "asked for - no prose, no code fences.")

    print(f"\n=== TEACHING {target['construction_id']} "
          f"(committee) ===")
    log = []
    lesson = {"lesson_id": target["lesson_id"],
              "lesson_type": "grammar_construction",
              "teacher_model": PROPOSER,
              "teacher_revision": snapshot,
              "teacher_confidence": None,
              "provenance": "schema_constrained_field_elicitation"
                            "+two_model_committee"}
    pattern = None
    failed_field = None
    for field, question, validator in make_fields(target):
        accepted = None
        for attempt in range(1, 5):
            q = question if attempt == 1 else (
                f"{question} Your previous answer was rejected: "
                f"{log[-1]['defect']}")
            reply = ask(PROPOSER, context, q,
                        seed=None if attempt == 1 else attempt)
            value = extract_json_value(reply)
            defect = ("no JSON found" if value is None
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

    results = {"event": "COMMITTEE_LESSON", "proposer": PROPOSER,
               "critic": CRITIC, "log": log}
    out_path = os.path.join(
        HERE, "output", f"committee_{target['lesson_id']}.json")

    if failed_field:
        results["verdict"] = f"ELICITATION_FAILED_{failed_field}"
        json.dump(results, open(out_path, "w", encoding="utf-8"),
                  indent=1, sort_keys=True, default=str)
        print(f"  {results['verdict']}")
        return

    lesson["semantics_provenance"] = \
        "derived_from_teacher_pattern_by_schema_scaffold"
    lesson["construction"] = {
        "construction_id": target["construction_id"],
        "surface_pattern": lesson.pop("surface_pattern"),
        "semantics": target["scaffold_semantics"],
        "surface_meta": target["surface_meta"],
    }
    print(f"  assembled schema defects: "
          f"{validate_construction(lesson['construction'])}")

    # ---------------- THE CRITIC'S REVIEW (distinct model family)
    review = None
    critic_question = CRITIC_QUESTION.format(
        description=target["description"],
        lesson=json.dumps({k: lesson[k] for k in
                           ("construction", "morphology",
                            "positive_examples", "minimal_pairs",
                            "counterexamples", "ambiguity_cases")},
                          sort_keys=True))
    for attempt in range(1, 4):
        reply = ask(CRITIC, "You review lessons. Answer ONLY the "
                            "JSON asked for.", critic_question,
                    seed=None if attempt == 1 else attempt)
        value = extract_json_value(reply)
        ok = (isinstance(value, dict)
              and value.get("vote") in ("approve", "reject"))
        log.append({"field": "committee_review", "attempt": attempt,
                    "defect": None if ok else "invalid review JSON",
                    "raw": reply[:300]})
        print(f"  committee review attempt {attempt}: "
              f"{value.get('vote') if ok else 'invalid JSON'}")
        if ok:
            review = value
            break
    if review is None:
        results["verdict"] = "ELICITATION_FAILED_committee_review"
        json.dump(results, open(out_path, "w", encoding="utf-8"),
                  indent=1, sort_keys=True, default=str)
        print(f"  {results['verdict']}")
        return

    lesson["committee"] = [
        {"model": PROPOSER, "role": "lecturer", "vote": "approve",
         "reasons": ["author of the lesson"]},
        {"model": CRITIC, "role": "critic",
         "vote": review["vote"],
         "reasons": review.get("reasons", [])},
    ]

    before = HybridRouter(mode="NATIVE_ONLY").turn(target["probe"])
    print(f"  BEFORE: {target['probe']!r} -> "
          f"{before['answer']['status']}")

    SEED_LEXICON = os.path.join(LANE, "CCB_L1_v0.1", "fixtures",
                                "seed_lexicon.json")
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
         "domain": "behavioral_norms", "target": "grammar_store",
         "teacher_model": PROPOSER,
         "teacher_revision": snapshot,
         "teacher_role": "lecturer",
         "examiner_identity": "ccb_l1_acceptance_ladder",
         "committee": lesson["committee"],
         "provenance": "schema_constrained_field_elicitation"
                       "+two_model_committee"},
        ladder)
    verdict = episode["outcome"]["verdict"]
    print(f"  COMMITTEE: {[m['vote'] for m in lesson['committee']]}")
    print(f"  LADDER: {verdict}")

    after = None
    retention = None
    if verdict == "PROMOTED_PROVISIONALLY":
        retention = student.confirm_retention(
            target["construction_id"], target["retention"])
        print(f"  RETENTION: {retention['verdict']}")
        if retention["verdict"] == "PROMOTED_DURABLY":
            store.save(SEED_GRAMMAR)
            merged = {surface: {"lemma": e["lemma"],
                                "form": e["form"],
                                "provenance": e["provenance"]}
                      for surface, e in
                      sorted(student.morph.to_json().items())}
            json.dump(merged, open(SEED_MORPH, "w",
                                   encoding="utf-8"), indent=1)
            after = HybridRouter(mode="NATIVE_ONLY").turn(
                target["probe"])
            print(f"  AFTER:  {target['probe']!r} -> "
                  f"{after['answer']['status']}")

    results.update({"verdict": verdict, "retention": retention,
                    "lesson": lesson, "episode": episode,
                    "before": before, "after": after})
    json.dump(results, open(out_path, "w", encoding="utf-8"),
              indent=1, sort_keys=True, default=str)
    print(f"\nsealed: {out_path}")
    print(f"  {target['construction_id']}: {verdict}"
          + (f" -> {retention['verdict']}" if retention else ""))


if __name__ == "__main__":
    main()
