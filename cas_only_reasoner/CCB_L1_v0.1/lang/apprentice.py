"""Verified Cognitive Apprenticeship (Phase L2): the
LanguageLessonPacket and the grammar acceptance law.

    Foreign proposals are permitted.
    Foreign commitments are prohibited.

The teacher proposes a construction with examples, minimal pairs,
counterexamples, and ambiguity cases. The student runs the promotion
ladder; the teacher's confidence is INFORMATIONAL and grants nothing;
held-out generalization cases come from a channel the teacher does
not control; failing any stage stops the ladder with a typed verdict;
every promotion carries the full evidence trail and remains
rollback-able.

Ladder: PROPOSED -> SCHEMA_VALID -> COMPILED ->
POSITIVE_EXAMPLES_PASS -> CONTRAST_TESTS_PASS ->
HELD_OUT_GENERALIZATION_PASS -> PRIOR_GRAMMAR_REGRESSION_PASS ->
AMBIGUITY_BEHAVIOR_PASS -> PROMOTED_PROVISIONALLY ->
DELAYED_RETENTION_PASS -> PROMOTED_DURABLY
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Dict, List, Optional

from .constructions import (ConstructionParser, GrammarStore,
                            MorphTable, validate_construction)
from .lexicon import Lexicon

LESSON_REQUIRED = ("lesson_id", "lesson_type", "teacher_model",
                   "teacher_revision", "construction",
                   "positive_examples", "minimal_pairs",
                   "counterexamples", "ambiguity_cases", "provenance")


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class Apprentice:
    """The student. Owns the lexicon, morph table, and grammar store;
    runs the acceptance law over teacher lessons."""

    def __init__(self, lexicon: Lexicon, morph: MorphTable,
                 store: GrammarStore) -> None:
        self.lexicon = lexicon
        self.morph = morph
        self.store = store
        self.parser = ConstructionParser(lexicon, morph)
        self.episodes: List[Dict] = []

    # ------------------------------------------------------------------
    def learn(self, lesson: Dict,
              held_out_cases: Optional[List[Dict]] = None) -> Dict:
        """The full ladder. held_out_cases come from the PROTECTED
        channel (separate templates and seeds) - never from the
        teacher's own lesson. Returns the sealed teaching episode."""
        stages: List[Dict] = []
        rule = lesson.get("construction", {})

        def stage(name: str, passed: bool, detail: str) -> bool:
            stages.append({"stage": name, "passed": passed,
                           "detail": detail})
            return passed

        def seal(verdict: str) -> Dict:
            episode = {
                "lesson_id": lesson.get("lesson_id"),
                "teacher_model": lesson.get("teacher_model"),
                "teacher_revision": lesson.get("teacher_revision"),
                "teacher_confidence_informational_only":
                    lesson.get("teacher_confidence"),
                "construction_id": rule.get("construction_id"),
                "stages": stages,
                "verdict": verdict,
                "provenance": lesson.get("provenance"),
            }
            episode["episode_digest"] = _digest(episode)
            self.episodes.append(episode)
            return episode

        # PROPOSED: the packet itself must be complete and typed
        missing = [f for f in LESSON_REQUIRED if f not in lesson]
        if not stage("PROPOSED", not missing,
                     f"missing fields: {missing}" if missing
                     else "typed lesson packet complete"):
            return seal("REJECTED_MALFORMED_LESSON")

        # SCHEMA_VALID
        defects = validate_construction(rule)
        if not stage("SCHEMA_VALID", not defects, "; ".join(defects)
                     or "construction schema valid"):
            return seal("REJECTED_SCHEMA")

        # COMPILED: morphology the lesson supplies is taught first
        # (provenance-marked), then the rule must actually match its
        # own first positive example
        for morph_entry in lesson.get("morphology", []):
            self.morph.teach(morph_entry["surface"],
                             morph_entry["lemma"], morph_entry["form"],
                             provenance=f"lesson:{lesson['lesson_id']}")
        first = lesson["positive_examples"][0]
        compiled = self.parser.match(rule, first["sentence"]) is not None
        if not stage("COMPILED", compiled,
                     f"rule matches first positive example: {compiled}"):
            return seal("REJECTED_UNCOMPILABLE")

        # POSITIVE_EXAMPLES_PASS: every positive example yields the
        # intended CORE meaning
        failures = []
        for example in lesson["positive_examples"]:
            bindings = self.parser.match(rule, example["sentence"])
            if bindings is None:
                failures.append(f"no match: {example['sentence']}")
                continue
            frame = self.parser.realize(rule, bindings)
            if frame["core"] != example["expected_core"]:
                failures.append(f"wrong core for {example['sentence']}: "
                                f"{frame['core']}")
        if not stage("POSITIVE_EXAMPLES_PASS", not failures,
                     "; ".join(failures) or
                     f"{len(lesson['positive_examples'])} examples ok"):
            return seal("REJECTED_POSITIVE_EXAMPLES")

        # CONTRAST_TESTS_PASS: minimal pairs - equal cores where
        # required equal, DIFFERENT cores where required different
        failures = []
        for pair in lesson["minimal_pairs"]:
            # contrasts hold across the WHOLE grammar including the
            # candidate: the active/passive same-meaning pair spans
            # two constructions
            core_a = self._grammar_core(rule, pair["sentence_a"])
            core_b = self._grammar_core(rule, pair["sentence_b"])
            if pair["relation"] == "same_meaning":
                if core_a is None or core_b is None or core_a != core_b:
                    failures.append(f"expected same meaning: "
                                    f"{pair['sentence_a']!r} vs "
                                    f"{pair['sentence_b']!r}")
            elif pair["relation"] == "different_meaning":
                if core_a is not None and core_a == core_b:
                    failures.append(f"collapsed contrast: "
                                    f"{pair['sentence_a']!r} vs "
                                    f"{pair['sentence_b']!r}")
        for counter in lesson["counterexamples"]:
            if self.parser.match(rule, counter["sentence"]) is not None:
                failures.append(f"counterexample wrongly matched: "
                                f"{counter['sentence']!r}")
        if not stage("CONTRAST_TESTS_PASS", not failures,
                     "; ".join(failures) or "contrasts held"):
            return seal("REJECTED_CONTRASTS")

        # HELD_OUT_GENERALIZATION_PASS: PROTECTED-channel cases only
        if held_out_cases is None:
            stage("HELD_OUT_GENERALIZATION_PASS", False,
                  "no protected held-out cases supplied - the teacher "
                  "may not examine its own lesson")
            return seal("REJECTED_NO_HELD_OUT_CHANNEL")
        failures = []
        for case in held_out_cases:
            core = self._grammar_core(rule, case["sentence"])
            if case.get("expect") == "no_parse":
                if core is not None:
                    failures.append(f"should not parse: "
                                    f"{case['sentence']!r}")
            elif core != case["expected_core"]:
                failures.append(f"held-out miss: {case['sentence']!r} "
                                f"-> {core}")
        if not stage("HELD_OUT_GENERALIZATION_PASS", not failures,
                     "; ".join(failures) or
                     f"{len(held_out_cases)} unseen cases ok"):
            return seal("REJECTED_HELD_OUT")

        # PRIOR_GRAMMAR_REGRESSION_PASS: previously ACTIVE rules still
        # parse their recorded regression sentences identically
        failures = []
        for prior in self.store.active_rules():
            for guard in prior.get("regression_guard", []):
                bindings = self.parser.match(prior, guard["sentence"])
                core = (self.parser.realize(prior, bindings)["core"]
                        if bindings is not None else None)
                if core != guard["expected_core"]:
                    failures.append(
                        f"regression on {prior['construction_id']}: "
                        f"{guard['sentence']!r}")
        if not stage("PRIOR_GRAMMAR_REGRESSION_PASS", not failures,
                     "; ".join(failures) or "no prior rule regressed"):
            return seal("REJECTED_REGRESSION")

        # AMBIGUITY_BEHAVIOR_PASS: ambiguous inputs must yield
        # alternatives or clarification, never one invented certainty
        failures = []
        candidate_rules = self.store.active_rules() + [rule]
        for case in lesson["ambiguity_cases"]:
            result = self.parser.parse(candidate_rules,
                                       case["sentence"])
            if case.get("expect") == "ambiguous_or_unknown":
                if result["status"] == "PARSED":
                    failures.append(f"invented certainty on "
                                    f"{case['sentence']!r}")
            elif case.get("expect") == "parsed":
                if result["status"] != "PARSED":
                    failures.append(f"failed to parse unambiguous "
                                    f"{case['sentence']!r}")
        if not stage("AMBIGUITY_BEHAVIOR_PASS", not failures,
                     "; ".join(failures) or "ambiguity honest"):
            return seal("REJECTED_AMBIGUITY")

        # PROMOTED_PROVISIONALLY -> deterministic replay check
        replay_first = self._core_of(rule, first["sentence"])
        replay_second = self._core_of(rule, first["sentence"])
        if not stage("DETERMINISTIC_REPLAY",
                     replay_first == replay_second,
                     "replay identical"):
            return seal("REJECTED_REPLAY")

        stage("PROMOTED_PROVISIONALLY", True,
              "all gates passed; promoting with rollback preserved")
        stored = dict(rule)
        stored["regression_guard"] = [
            {"sentence": example["sentence"],
             "expected_core": example["expected_core"]}
            for example in lesson["positive_examples"]]
        self.store.add_active(stored,
                              provenance=f"lesson:{lesson['lesson_id']}"
                                         f"|teacher:"
                                         f"{lesson['teacher_model']}")
        return seal("PROMOTED_PROVISIONALLY")

    # ------------------------------------------------------------------
    def confirm_retention(self, construction_id: str,
                          retention_cases: List[Dict]) -> Dict:
        """DELAYED_RETENTION_PASS -> PROMOTED_DURABLY: after other
        work (or a process boundary), the rule still parses unseen
        retention cases; only then is durability recorded."""
        rule = self.store.rules.get(construction_id)
        if rule is None or rule["state"] != "ACTIVE":
            return {"verdict": "NOT_ACTIVE",
                    "construction_id": construction_id}
        failures = []
        for case in retention_cases:
            bindings = self.parser.match(rule, case["sentence"])
            core = (self.parser.realize(rule, bindings)["core"]
                    if bindings is not None else None)
            if core != case["expected_core"]:
                failures.append(case["sentence"])
        if failures:
            self.store.quarantine(construction_id,
                                  f"delayed retention failed: {failures}")
            return {"verdict": "QUARANTINED_RETENTION_FAILURE",
                    "failures": failures}
        rule["durability"] = "PROMOTED_DURABLY"
        return {"verdict": "PROMOTED_DURABLY",
                "construction_id": construction_id}

    # ------------------------------------------------------------------
    def _core_of(self, rule: Dict, sentence: str) -> Optional[Dict]:
        bindings = self.parser.match(rule, sentence)
        if bindings is None:
            return None
        return self.parser.realize(rule, bindings)["core"]

    def _grammar_core(self, candidate: Dict,
                      sentence: str) -> Optional[Dict]:
        """Parse against the whole grammar PLUS the candidate rule -
        contrasts and held-out cases span constructions."""
        rules = self.store.active_rules() + [candidate]
        result = self.parser.parse(rules, sentence)
        return result.get("core") if result["status"] == "PARSED" \
            else None

    def _core_of_all(self, sentence: str) -> Optional[Dict]:
        result = self.parser.parse(self.store.active_rules(), sentence)
        return result.get("core") if result["status"] == "PARSED" \
            else None
