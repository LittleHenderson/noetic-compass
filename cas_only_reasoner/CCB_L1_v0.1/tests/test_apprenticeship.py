"""The Verified Cognitive Apprenticeship: learnable grammar under the
acceptance law. Teacher proposes; the student's ladder decides;
foreign commitments are prohibited."""

import copy

from lang.apprentice import Apprentice
from lang.constructions import (GrammarStore, MorphTable,
                                validate_construction)
from lang.lexicon import Lexicon

import pytest

# a small lexicon the STUDENT owns (nouns beyond the seed fragment)
LEX = {
    "the": {"pos": "article", "sense": "the"},
    "cat": {"pos": "noun", "sense": "cat"},
    "dog": {"pos": "noun", "sense": "dog"},
    "bird": {"pos": "noun", "sense": "bird"},
    "fox": {"pos": "noun", "sense": "fox"},
    "hen": {"pos": "noun", "sense": "hen"},
}

ACTIVE_PAST = {
    "construction_id": "active_past_transitive",
    "surface_pattern": ["NP:agent", "VERB:pred:past", "NP:patient"],
    "semantics": {"frame": "event", "predicate": "@pred",
                  "agent": "@agent", "patient": "@patient",
                  "tense": "past", "polarity": "positive"},
    "surface_meta": {"voice": "active"},
}

PASSIVE_PAST = {
    "construction_id": "passive_past",
    "surface_pattern": ["NP:patient", "was", "VERB:pred:participle",
                        "by", "NP:agent"],
    "semantics": {"frame": "event", "predicate": "@pred",
                  "agent": "@agent", "patient": "@patient",
                  "tense": "past", "polarity": "positive"},
    "surface_meta": {"voice": "passive"},
}


def _core(pred, agent, patient):
    return {"frame": "event", "predicate": pred, "agent": agent,
            "patient": patient, "tense": "past",
            "polarity": "positive"}


def _lesson(lesson_id, construction, positives, pairs=(), counters=(),
            ambiguity=(), morphology=()):
    return {"lesson_id": lesson_id, "lesson_type": "grammar_construction",
            "teacher_model": "hand_authored_seed_teacher",
            "teacher_revision": "seed-1",
            "teacher_confidence": 0.9,
            "construction": construction,
            "positive_examples": list(positives),
            "minimal_pairs": list(pairs),
            "counterexamples": list(counters),
            "ambiguity_cases": list(ambiguity),
            "morphology": list(morphology),
            "provenance": "seed_curriculum"}


ACTIVE_LESSON = _lesson(
    "L001_active_past", ACTIVE_PAST,
    positives=[
        {"sentence": "the cat chased the dog.",
         "expected_core": _core("chase", "cat", "dog")},
        {"sentence": "the fox chased the hen.",
         "expected_core": _core("chase", "fox", "hen")},
    ],
    pairs=[
        {"sentence_a": "the cat chased the dog.",
         "sentence_b": "the dog chased the cat.",
         "relation": "different_meaning"},
    ],
    counters=[{"sentence": "the cat chased."},
              {"sentence": "chased the dog the cat."}],
    ambiguity=[{"sentence": "the cat chased the dog.",
                "expect": "parsed"}],
    morphology=[{"surface": "chased", "lemma": "chase",
                 "form": "past_or_participle"}],
)

ACTIVE_HELD_OUT = [
    {"sentence": "the bird chased the fox.",
     "expected_core": _core("chase", "bird", "fox")},
    {"sentence": "the dog chased the bird.",
     "expected_core": _core("chase", "dog", "bird")},
    {"sentence": "the chased dog cat.", "expect": "no_parse"},
]

PASSIVE_LESSON = _lesson(
    "L002_passive_past", PASSIVE_PAST,
    positives=[
        {"sentence": "the dog was chased by the cat.",
         "expected_core": _core("chase", "cat", "dog")},
        {"sentence": "the hen was chased by the fox.",
         "expected_core": _core("chase", "fox", "hen")},
    ],
    pairs=[
        # THE minimal-pair law: active == passive, reversal differs
        {"sentence_a": "the cat chased the dog.",
         "sentence_b": "the dog was chased by the cat.",
         "relation": "same_meaning"},
        {"sentence_a": "the dog was chased by the cat.",
         "sentence_b": "the dog chased the cat.",
         "relation": "different_meaning"},
    ],
    counters=[{"sentence": "the dog was chased the cat."},
              {"sentence": "was the dog chased by the cat."}],
    ambiguity=[{"sentence": "the dog was chased by the cat.",
                "expect": "parsed"}],
)

PASSIVE_HELD_OUT = [
    {"sentence": "the fox was chased by the bird.",
     "expected_core": _core("chase", "bird", "fox")},
    {"sentence": "the cat was chased by the hen.",
     "expected_core": _core("chase", "hen", "cat")},
]


def _student():
    return Apprentice(Lexicon(LEX), MorphTable(), GrammarStore())


def _taught_student():
    student = _student()
    assert student.learn(ACTIVE_LESSON, ACTIVE_HELD_OUT)["verdict"] \
        == "PROMOTED_PROVISIONALLY"
    assert student.learn(PASSIVE_LESSON, PASSIVE_HELD_OUT)["verdict"] \
        == "PROMOTED_PROVISIONALLY"
    return student


# ---------------------------------------------------------- the ladder
def test_active_then_passive_promote_through_the_full_ladder():
    student = _taught_student()
    active = {r["construction_id"] for r in student.store.active_rules()}
    assert active == {"active_past_transitive", "passive_past"}
    episode = student.episodes[-1]
    stages = [s["stage"] for s in episode["stages"]]
    assert stages == ["PROPOSED", "SCHEMA_VALID", "COMPILED",
                      "POSITIVE_EXAMPLES_PASS", "CONTRAST_TESTS_PASS",
                      "HELD_OUT_GENERALIZATION_PASS",
                      "PRIOR_GRAMMAR_REGRESSION_PASS",
                      "AMBIGUITY_BEHAVIOR_PASS",
                      "DETERMINISTIC_REPLAY",
                      "PROMOTED_PROVISIONALLY"]
    assert all(s["passed"] for s in episode["stages"])


def test_one_construction_covers_unseen_sentences():
    """The compositional point: ONE passive rule + the lexicon handles
    noun pairs never seen in any lesson."""
    student = _taught_student()
    result = student.parser.parse(
        student.store.active_rules(),
        "the bird was chased by the dog.")
    assert result["status"] == "PARSED"
    assert result["core"] == _core("chase", "dog", "bird")


def test_minimal_pair_law_passive_equals_active():
    student = _taught_student()
    active_core = student._core_of_all("the cat chased the dog.")
    passive_core = student._core_of_all("the dog was chased by the cat.")
    reversed_core = student._core_of_all("the dog chased the cat.")
    assert active_core == passive_core          # voice is surface only
    assert active_core != reversed_core         # roles are core


# ----------------------------------------------------- rejection rungs
def test_wrong_semantics_lesson_dies_at_positive_examples():
    bad_rule = copy.deepcopy(PASSIVE_PAST)
    bad_rule["construction_id"] = "passive_wrong_roles"
    # teacher misunderstands: maps the patient slot to agent
    bad_rule["semantics"]["agent"] = "@patient"
    bad_rule["semantics"]["patient"] = "@agent"
    lesson = copy.deepcopy(PASSIVE_LESSON)
    lesson["lesson_id"] = "L_bad_roles"
    lesson["construction"] = bad_rule
    student = _student()
    student.learn(ACTIVE_LESSON, ACTIVE_HELD_OUT)
    episode = student.learn(lesson, PASSIVE_HELD_OUT)
    assert episode["verdict"] == "REJECTED_POSITIVE_EXAMPLES"
    assert "passive_wrong_roles" not in student.store.rules


def test_contrast_collapse_is_fatal():
    """A rule that makes role reversal MEAN THE SAME dies at the
    contrast rung - the fault-injection of language learning."""
    symmetric = {
        "construction_id": "symmetric_chase",
        "surface_pattern": ["NP:x", "VERB:pred:past", "NP:y"],
        "semantics": {"frame": "event", "predicate": "@pred",
                      "agent": "fixed", "patient": "fixed",
                      "tense": "past", "polarity": "positive"},
        "surface_meta": {},
    }
    lesson = _lesson(
        "L_symmetric", symmetric,
        positives=[{"sentence": "the cat chased the dog.",
                    "expected_core": {"frame": "event",
                                      "predicate": "chase",
                                      "agent": "fixed",
                                      "patient": "fixed",
                                      "tense": "past",
                                      "polarity": "positive"}}],
        pairs=[{"sentence_a": "the cat chased the dog.",
                "sentence_b": "the dog chased the cat.",
                "relation": "different_meaning"}],
        morphology=[{"surface": "chased", "lemma": "chase",
                     "form": "past_or_participle"}],
    )
    episode = _student().learn(lesson, [])
    assert episode["verdict"] == "REJECTED_CONTRASTS"


def test_no_held_out_channel_no_promotion():
    """The teacher may not examine its own lesson: without the
    protected channel the ladder stops."""
    student = _student()
    episode = student.learn(ACTIVE_LESSON, held_out_cases=None)
    assert episode["verdict"] == "REJECTED_NO_HELD_OUT_CHANNEL"
    assert not student.store.rules


def test_held_out_generalization_failure_rejects():
    student = _student()
    bad_held_out = [{"sentence": "the bird chased the fox.",
                     "expected_core": _core("chase", "fox", "bird")}]
    episode = student.learn(ACTIVE_LESSON, bad_held_out)
    assert episode["verdict"] == "REJECTED_HELD_OUT"


def test_regression_guard_protects_prior_grammar():
    """A new lesson may not break previously mastered constructions:
    the prior rules re-parse their guard sentences during every later
    promotion (stage passed in the passive episode)."""
    student = _taught_student()
    passive_episode = student.episodes[-1]
    regression_stage = [s for s in passive_episode["stages"]
                        if s["stage"] == "PRIOR_GRAMMAR_REGRESSION_PASS"]
    assert regression_stage and regression_stage[0]["passed"]
    active_rule = student.store.rules["active_past_transitive"]
    assert active_rule["regression_guard"]


def test_malformed_and_invalid_schema_rejected():
    student = _student()
    assert student.learn({"lesson_id": "L_bare"}, [])["verdict"] \
        == "REJECTED_MALFORMED_LESSON"
    broken = copy.deepcopy(ACTIVE_LESSON)
    broken["lesson_id"] = "L_broken_schema"
    broken["construction"] = {"construction_id": "x",
                              "surface_pattern": ["NP:a"],
                              "semantics": {"frame": "event",
                                            "predicate": "@missing"}}
    assert student.learn(broken, [])["verdict"] == "REJECTED_SCHEMA"
    assert validate_construction(ACTIVE_PAST) == []


def test_teacher_confidence_grants_nothing():
    """A 0.99-confidence wrong lesson dies exactly like a 0.1 one."""
    lesson = copy.deepcopy(PASSIVE_LESSON)
    lesson["lesson_id"] = "L_overconfident"
    lesson["teacher_confidence"] = 0.99
    lesson["construction"] = copy.deepcopy(PASSIVE_PAST)
    lesson["construction"]["construction_id"] = "overconfident_passive"
    lesson["construction"]["semantics"]["agent"] = "@patient"
    lesson["construction"]["semantics"]["patient"] = "@agent"
    student = _student()
    student.learn(ACTIVE_LESSON, ACTIVE_HELD_OUT)
    episode = student.learn(lesson, PASSIVE_HELD_OUT)
    assert episode["verdict"].startswith("REJECTED")
    assert episode["teacher_confidence_informational_only"] == 0.99


# ------------------------------------------- retention and durability
def test_delayed_retention_promotes_durably_or_quarantines():
    student = _taught_student()
    result = student.confirm_retention("passive_past", [
        {"sentence": "the hen was chased by the dog.",
         "expected_core": _core("chase", "dog", "hen")}])
    assert result["verdict"] == "PROMOTED_DURABLY"
    # a retention failure quarantines instead of lying
    student2 = _taught_student()
    result2 = student2.confirm_retention("passive_past", [
        {"sentence": "the hen was chased by the dog.",
         "expected_core": _core("chase", "hen", "dog")}])   # wrong
    assert result2["verdict"] == "QUARANTINED_RETENTION_FAILURE"
    assert student2.store.rules["passive_past"]["state"] == "QUARANTINED"


def test_grammar_store_persists_and_rejects_tampering():
    import json
    import os
    import tempfile

    student = _taught_student()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "grammar.json")
        digest = student.store.save(path)
        restored = GrammarStore.load(path)
        assert restored.store_digest() == digest
        assert {r["construction_id"] for r in restored.active_rules()} \
            == {"active_past_transitive", "passive_past"}
        payload = json.load(open(path, encoding="utf-8"))
        payload["rules"]["passive_past"]["semantics"]["agent"] = \
            "@patient"                                   # forged
        json.dump(payload, open(path, "w", encoding="utf-8"))
        with pytest.raises(Exception, match="tampered"):
            GrammarStore.load(path)


def test_ambiguity_is_reported_never_resolved_silently():
    """Two constructions yielding distinct cores for one sentence must
    surface as AMBIGUOUS_PARSE with alternatives."""
    student = _taught_student()
    rules = student.store.active_rules()
    shadow = copy.deepcopy(rules[0])
    shadow["construction_id"] = "shadow_swapped"
    shadow["semantics"] = dict(shadow["semantics"],
                               agent="@patient", patient="@agent")
    result = student.parser.parse(rules + [shadow],
                                  "the cat chased the dog.")
    assert result["status"] == "AMBIGUOUS_PARSE"
    assert len(result["alternatives"]) == 2
