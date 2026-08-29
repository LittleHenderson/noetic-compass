"""Generate the seed grammar THROUGH the acceptance law.

Nothing is hand-inserted into the store: every construction below is
taught as a lesson and must climb the full ladder (including the
protected held-out channel) before it lands in
fixtures/seed_grammar.json. The teaching lexicon is EXTENDED (extra
nouns) so held-out generalization is real; the saved constructions
are lexicon-independent patterns and generalize to the runtime seed
lexicon by design - that is the compositional point.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lang.apprentice import Apprentice
from lang.constructions import GrammarStore, MorphTable
from lang.lexicon import Lexicon

TEACHING_LEX = {
    "the": {"pos": "article", "sense": "the"},
    "cat": {"pos": "noun", "sense": "cat"},
    "dog": {"pos": "noun", "sense": "dog"},
    "bird": {"pos": "noun", "sense": "bird"},
    "fox": {"pos": "noun", "sense": "fox"},
    "hen": {"pos": "noun", "sense": "hen"},
}


def core(pred, agent, patient, tense):
    return {"frame": "event", "predicate": pred, "agent": agent,
            "patient": patient, "tense": tense, "polarity": "positive"}


def lesson(lesson_id, construction, positives, pairs, counters,
           ambiguity, morphology=()):
    return {"lesson_id": lesson_id,
            "lesson_type": "grammar_construction",
            "teacher_model": "hand_authored_seed_teacher",
            "teacher_revision": "seed-1",
            "teacher_confidence": 0.9,
            "construction": construction,
            "positive_examples": positives,
            "minimal_pairs": pairs,
            "counterexamples": counters,
            "ambiguity_cases": ambiguity,
            "morphology": list(morphology),
            "provenance": "seed_curriculum_v1"}


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

PASSIVE_PRESENT = {
    "construction_id": "passive_present",
    "surface_pattern": ["NP:patient", "is", "VERB:pred:participle",
                        "by", "NP:agent"],
    "semantics": {"frame": "event", "predicate": "@pred",
                  "agent": "@agent", "patient": "@patient",
                  "tense": "present", "polarity": "positive"},
    "surface_meta": {"voice": "passive"},
}


def main():
    student = Apprentice(Lexicon(TEACHING_LEX), MorphTable(),
                         GrammarStore())

    episodes = []
    episodes.append(student.learn(
        lesson("SEED_L001_active_past", ACTIVE_PAST,
               positives=[
                   {"sentence": "the cat chased the dog.",
                    "expected_core": core("chase", "cat", "dog", "past")},
                   {"sentence": "the fox chased the hen.",
                    "expected_core": core("chase", "fox", "hen", "past")}],
               pairs=[{"sentence_a": "the cat chased the dog.",
                       "sentence_b": "the dog chased the cat.",
                       "relation": "different_meaning"}],
               counters=[{"sentence": "the cat chased."}],
               ambiguity=[{"sentence": "the cat chased the dog.",
                           "expect": "parsed"}],
               morphology=[{"surface": "chased", "lemma": "chase",
                            "form": "past_or_participle"}]),
        held_out_cases=[
            {"sentence": "the bird chased the fox.",
             "expected_core": core("chase", "bird", "fox", "past")},
            {"sentence": "the chased cat dog.", "expect": "no_parse"}]))

    episodes.append(student.learn(
        lesson("SEED_L002_passive_past", PASSIVE_PAST,
               positives=[
                   {"sentence": "the dog was chased by the cat.",
                    "expected_core": core("chase", "cat", "dog", "past")}],
               pairs=[
                   {"sentence_a": "the cat chased the dog.",
                    "sentence_b": "the dog was chased by the cat.",
                    "relation": "same_meaning"},
                   {"sentence_a": "the dog was chased by the cat.",
                    "sentence_b": "the dog chased the cat.",
                    "relation": "different_meaning"}],
               counters=[{"sentence": "the dog was chased the cat."}],
               ambiguity=[{"sentence": "the dog was chased by the cat.",
                           "expect": "parsed"}]),
        held_out_cases=[
            {"sentence": "the fox was chased by the bird.",
             "expected_core": core("chase", "bird", "fox", "past")}]))

    episodes.append(student.learn(
        lesson("SEED_L003_passive_present", PASSIVE_PRESENT,
               positives=[
                   {"sentence": "the dog is chased by the cat.",
                    "expected_core": core("chase", "cat", "dog",
                                          "present")}],
               pairs=[
                   {"sentence_a": "the dog is chased by the cat.",
                    "sentence_b": "the cat is chased by the dog.",
                    "relation": "different_meaning"}],
               counters=[{"sentence": "the dog is chased the cat."}],
               ambiguity=[{"sentence": "the dog is chased by the cat.",
                           "expect": "parsed"}]),
        held_out_cases=[
            {"sentence": "the hen is chased by the fox.",
             "expected_core": core("chase", "fox", "hen", "present")}]))

    for episode in episodes:
        assert episode["verdict"] == "PROMOTED_PROVISIONALLY", episode
        print(f"{episode['construction_id']}: {episode['verdict']}")

    # delayed retention -> durability, on fresh unseen cases
    for cid, case in (
            ("active_past_transitive",
             {"sentence": "the hen chased the bird.",
              "expected_core": core("chase", "hen", "bird", "past")}),
            ("passive_past",
             {"sentence": "the cat was chased by the hen.",
              "expected_core": core("chase", "hen", "cat", "past")}),
            ("passive_present",
             {"sentence": "the bird is chased by the cat.",
              "expected_core": core("chase", "cat", "bird",
                                    "present")})):
        result = student.confirm_retention(cid, [case])
        assert result["verdict"] == "PROMOTED_DURABLY", result
        print(f"{cid}: PROMOTED_DURABLY")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "fixtures", "seed_grammar.json")
    digest = student.store.save(out)
    # learned morphology TRAVELS WITH the learned grammar - without it
    # the regular -ed rule mis-lemmatizes (chased -> "chas")
    with open(os.path.join(os.path.dirname(out),
                           "seed_morphology.json"), "w",
              encoding="utf-8") as fh:
        json.dump(student.morph.to_json(), fh, indent=1, sort_keys=True)
    with open(os.path.join(os.path.dirname(out),
                           "seed_grammar_episodes.json"), "w",
              encoding="utf-8") as fh:
        json.dump(student.episodes, fh, indent=1, sort_keys=True)
    print(f"seed grammar sealed: {out} (digest {digest})")


if __name__ == "__main__":
    main()
