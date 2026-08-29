"""Phase 4.2: native-first routing with three runtime modes.

    NATIVE_ONLY        CCB-L1 only - the cortex never runs
    CORTEX_DIAGNOSTIC  cortex proposals are RECORDED but cannot affect
                       commitment (ablation lane)
    HYBRID_COMMIT      validated cortex proposals enter the same
                       kernel bridge the native path uses; commitment
                       stays with CAS

Routing law: native first (faster, deterministic, honest); the cortex
is invoked only when native parsing fails typed; when neither route
yields an admissible interpretation the answer is a typed no-answer -
"the cortex produced text" is never "the system understood."
Every turn produces a sealed TurnTrace.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Dict, List, Optional

_CAS_ONLY = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
for _board in ("CCB_L1_v0.1", "CAS_RRK_v0.1"):
    _path = os.path.join(_CAS_ONLY, _board)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from lang.discourse import DiscourseError  # noqa: E402
from lang.grammar import ParseError  # noqa: E402
from lang.kernel_bridge import answer_question, decode_verdict  # noqa: E402
from lang.l1 import CCB_L1  # noqa: E402
from lang.lexicon import LexiconError  # noqa: E402

from .firewall import AuthorityFirewall  # noqa: E402
from .proposal import ProposalRejected, validate_proposal  # noqa: E402

MODES = ("NATIVE_ONLY", "CORTEX_DIAGNOSTIC", "HYBRID_COMMIT")


def core_state_renderable(core) -> bool:
    return (isinstance(core, dict) and core.get("frame") == "state"
            and core.get("entity") and core.get("property"))


def render_clause(core) -> str:
    """Naive regular English for a frame core (the REALIZE subboard
    owns proper rendering later)."""
    if core.get("frame") == "state":
        mod = core.get("modifier")
        return ("the " + (f"{mod} " if mod else "")
                + f"{core.get('entity')} is {core.get('property')}")
    verb = core.get("predicate") or ""
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
        inflected = verb[:-1] + ("ied" if core.get("tense") == "past"
                                 else "ies")
    else:
        inflected = verb + ("d" if core.get("tense") == "past"
                            else "s")
    agent_mod = core.get("agent_mod")
    patient_mod = core.get("patient_mod")
    clause = ("the " + (f"{agent_mod} " if agent_mod else "")
              + f"{core.get('agent')} {inflected} "
              + "the " + (f"{patient_mod} " if patient_mod else "")
              + f"{core.get('patient')}")
    if core.get("recipient"):
        clause += f" to the {core.get('recipient')}"
    return clause

SEED_PATH = os.path.join(_CAS_ONLY, "CCB_L1_v0.1", "fixtures",
                         "seed_lexicon.json")


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class HybridRouter:
    def __init__(self, mode: str = "NATIVE_ONLY",
                 cortex=None) -> None:
        if mode not in MODES:
            raise ValueError(f"unknown mode {mode!r}; modes are {MODES}")
        if mode != "NATIVE_ONLY" and cortex is None:
            raise ValueError(f"mode {mode} requires a cortex")
        self.mode = mode
        self.cortex = cortex
        self.firewall = AuthorityFirewall()
        self.seed = json.load(open(SEED_PATH, encoding="utf-8"))
        self.traces: List[Dict] = []
        # The GROUNDED vocabulary: lexicon senses + entities the CMB
        # actually knows. The lexical grounding gate (live Gate 4
        # closure, 2026-08-28) checks every cortex-proposed atom
        # against THIS set - the cortex's own unknown-word self-report
        # is never trusted alone.
        self.grounded = {entry["sense"]
                         for entry in self.seed["lexicon"].values()}
        for fact in self.seed["cmb_facts"]:
            self.grounded.update(fact.get("args", []))
        # THE LEARNED GRAMMAR (apprenticeship Phase L5): constructions
        # promoted through the acceptance law load from the sealed
        # seed store and parse NATIVELY - taught English never touches
        # the cortex again. Coverage counters are the Phase L6
        # teacher-dependence metric.
        from lang.constructions import (ConstructionParser, GrammarStore,
                                        MorphTable)
        from lang.lexicon import Lexicon
        grammar_path = os.path.join(_CAS_ONLY, "CCB_L1_v0.1",
                                    "fixtures", "seed_grammar.json")
        self.grammar = (GrammarStore.load(grammar_path)
                        if os.path.exists(grammar_path)
                        else GrammarStore())
        morph = MorphTable()
        morph_path = os.path.join(_CAS_ONLY, "CCB_L1_v0.1",
                                  "fixtures", "seed_morphology.json")
        if os.path.exists(morph_path):
            for surface, entry in json.load(
                    open(morph_path, encoding="utf-8")).items():
                morph.teach(surface, entry["lemma"], entry["form"],
                            provenance=entry["provenance"])
        # cross-sentence discourse state: the entities of the LAST
        # committed turn - the pronoun lesson's antecedent pool
        self.discourse_entities = []
        self.gram_parser = ConstructionParser(
            Lexicon(self.seed["lexicon"]), morph)
        self.coverage = {"native_l1": 0, "native_gram": 0,
                         "cortex": 0, "refused": 0}
        # CCB-D1: the Dialogue and Common-Ground Board (CONV v0.1).
        # Session-scoped; a fresh router is a fresh session - no
        # leakage across sessions by construction.
        d1_path = os.path.join(_CAS_ONLY, "CCB_D1_v0.1")
        if d1_path not in sys.path:
            sys.path.insert(0, d1_path)
        from dialogue import DialogueBoard
        self.dialogue = DialogueBoard(session_id="session")

    # ------------------------------------------------------------------
    def _native(self, sentence: str) -> Dict:
        board = CCB_L1(self.seed)
        try:
            meaning = board.parse(sentence)
            return {"status": "PARSED", "meaning": meaning}
        except ParseError as exc:
            return {"status": "UNSUPPORTED_LANGUAGE",
                    "error": {"word": exc.args[0],
                              "message": exc.message()}}
        except DiscourseError as exc:
            # battery-found crash (2026-08-28): an unresolved pronoun
            # raised straight through the router. Typed, never a crash.
            return {"status": "UNRESOLVED_REFERENCE",
                    "error": {"word": "it", "message": str(exc)}}
        except LexiconError as exc:
            return {"status": "UNSUPPORTED_LANGUAGE",
                    "error": {"word": "?", "message": str(exc)}}

    def _answer_conjunction_question(self, packet: Dict, gram: Dict,
                                     trace: Dict) -> Dict:
        """Restricted-question answering: every conjunct must be
        settled - by the verified record or by a session assertion -
        before 'yes'; the reply names its sources (the goal's
        no-laundering table)."""
        query_tense = gram["core"].get("tense")
        sources = []
        conflicted = []
        for part in packet.get("args", []):
            verdict = None
            part_conflicts = self.dialogue.conflicting_active(
                part, query_tense)
            try:
                kernel = self._kernel_answer({"pred": "question",
                                              "args": [part]})
                if kernel["kernel_status"] == "CONCLUDED":
                    verdict = "VERIFIED"
            except Exception:
                pass
            if verdict is None:
                support = self.dialogue.support_for(part, query_tense)
                if support and support.get("verdict") == "yes":
                    verdict = "USER_ASSERTED"
                elif support and support.get("verdict") == "no":
                    verdict = "USER_DENIED"
            if part_conflicts:
                # a conjunct someone contests is NEVER affirmed
                # silently (audit finding: the restricted question
                # suppressed a verified/user conflict)
                conflicted.append(
                    (part, verdict, part_conflicts[0]))
            sources.append(verdict)
        trace.setdefault("dialogue", {})["retrieval"] = {
            "conjunct_sources": sources,
            "conjunct_conflicts": [
                r["assertion_id"] for _, _, r in conflicted]}
        clause = render_clause(gram["core"])
        if conflicted:
            part, verdict, conflict_record = conflicted[0]
            part_clause = self.dialogue.packet_to_clause(part)
            told = self.dialogue.packet_to_clause(
                conflict_record["proposition"],
                conflict_record.get("tense"))
            if verdict == "VERIFIED":
                text = (f"i have conflicting information: the "
                        f"verified record says {part_clause}; you "
                        f"told me {told}.")
            else:
                text = (f"i have conflicting information about "
                        f"whether {part_clause}: you told me "
                        f"{told}. i cannot answer until it is "
                        f"settled.")
            trace["answer"] = {"status": "ANSWERED", "text": text,
                               "frame_core": gram["core"],
                               "conjunct_sources": sources,
                               "source_class": "CONFLICT"}
            return self._seal(trace, committed=True)
        if sources and any(v == "USER_DENIED" for v in sources):
            text = (f"based on what you told me, no - part of this "
                    f"is denied by what you said.")
            source_class = "USER_ASSERTED"
        elif sources and all(v == "VERIFIED" for v in sources):
            text = f"yes, the verified record says {clause}."
            source_class = "VERIFIED"
        elif sources and all(v is not None for v in sources):
            if all(v == "USER_ASSERTED" for v in sources):
                text = f"based on what you told me, yes, {clause}."
                source_class = "USER_ASSERTED"
            else:
                text = (f"based on what you told me and the verified "
                        f"record, yes, {clause}.")
                source_class = "MIXED"
        else:
            text = f"i do not know whether {clause}."
            source_class = None
        trace["answer"] = {"status": "ANSWERED", "text": text,
                           "frame_core": gram["core"],
                           "conjunct_sources": sources,
                           "source_class": source_class}
        return self._seal(trace, committed=True)

    def _answer_gram_question(self, packet: Dict, gram: Dict,
                              trace: Dict) -> Dict:
        """Yes/no question over the two knowledge stores, sources
        NEVER collapsed (the frozen CONV acceptance law): verified ->
        named as the verified record; session -> 'based on what you
        told me'; both in conflict -> both shown; neither -> honest
        unknown."""
        core = gram["core"]
        query_tense = core.get("tense")
        support = self.dialogue.support_for(packet, query_tense)
        conflicts = self.dialogue.conflicting_active(packet,
                                                     query_tense)
        kernel_status = None
        try:
            kernel = self._kernel_answer(
                {"pred": "question", "args": [packet]})
            kernel_status = kernel["kernel_status"]
        except Exception as exc:
            trace.setdefault("dialogue", {})["kernel_error"] = \
                type(exc).__name__
        trace.setdefault("dialogue", {})["retrieval"] = {
            "kernel_status": kernel_status,
            "session_verdict": support and support.get("verdict"),
            "session_record": (support or {}).get(
                "record", {}).get("assertion_id"),
            "conflicting": [r["assertion_id"] for r in conflicts]}
        clause = render_clause(core)
        concluded = kernel_status == "CONCLUDED"
        support_record = (support or {}).get("record")
        session_conflict = [r for r in conflicts
                            if support_record is None
                            or r["assertion_id"]
                            != support_record["assertion_id"]]
        if concluded and conflicts:
            told = self.dialogue.packet_to_clause(
                conflicts[0]["proposition"],
                conflicts[0].get("tense"))
            text = (f"i have conflicting information: the verified "
                    f"record says {clause}; you told me {told}.")
            source_class = "CONFLICT"
        elif support and support.get("verdict") in ("yes", "no") \
                and session_conflict:
            # the session itself holds BOTH sides (audit finding: the
            # answer flipped with insertion order while the trace
            # listed the denial) - never affirm either
            first = self.dialogue.packet_to_clause(
                support_record["proposition"],
                support_record.get("tense"))
            second = self.dialogue.packet_to_clause(
                session_conflict[0]["proposition"],
                session_conflict[0].get("tense"))
            text = (f"i have conflicting information from you: you "
                    f"told me {first} and also {second} - i cannot "
                    f"answer until it is settled.")
            source_class = "CONTESTED"
        elif concluded:
            text = f"yes, the verified record says {clause}."
            source_class = "VERIFIED"
        elif support and support["verdict"] == "yes":
            text = f"based on what you told me, yes, {clause}."
            source_class = "USER_ASSERTED"
        elif support and support["verdict"] == "no":
            told = self.dialogue.packet_to_clause(
                support["record"]["proposition"],
                support["record"].get("tense"))
            text = (f"based on what you told me, no - you told me "
                    f"that {told}.")
            source_class = "USER_ASSERTED"
        elif support and support["verdict"] == "contested":
            text = ("you gave me conflicting statements about this - "
                    "i cannot answer until it is settled.")
            source_class = "CONTESTED"
        else:
            text = f"i do not know whether {clause}."
            source_class = None
        self._note_discourse(packet)
        trace["answer"] = {"status": "ANSWERED", "text": text,
                           "frame_core": core,
                           "source_class": source_class}
        return self._seal(trace, committed=True)

    def _math_student(self):
        if not hasattr(self, "_math_student_cache"):
            math_board = os.path.join(_CAS_ONLY,
                                      "CAS_MATH_LADDER_v0.1")
            m1_board = os.path.join(_CAS_ONLY, "CCB_M1_v0.1")
            for path in (math_board, m1_board):
                if path not in sys.path:
                    sys.path.insert(0, path)
            from mathschool import SkillStore, Student
            store_path = os.path.join(math_board, "fixtures",
                                      "math_skills.json")
            self._math_student_cache = Student(
                SkillStore.load(store_path))
        return self._math_student_cache

    _OP_WORD = {"add": "plus", "sub": "minus", "mul": "times",
                "div": "over"}
    _OP_SYMBOL = {"add": "+", "sub": "-", "mul": "*"}

    def _answer_math_query(self, gram: Dict, trace: Dict) -> Dict:
        from fractions import Fraction
        core = gram["core"]
        student = self._math_student()   # sets sys.path first
        from mathschool.mathir import number_to_words
        op = core.get("op")
        trace.setdefault("dialogue", {})["retrieval"] = {
            "math_op": op}

        def words(text: str) -> str:
            if "/" in text:
                p_, q_ = text.split("/")
                return number_to_words(Fraction(int(p_), int(q_)))
            return number_to_words(Fraction(int(text)))

        def seal_answer(text, source="exact_computation",
                        status="ANSWERED", committed=True):
            trace["answer"] = {"status": status, "text": text,
                               "frame_core": core,
                               "source_class": source}
            return self._seal(trace, committed)

        def cannot(result):
            return seal_answer(
                f"i have not learned "
                f"{result['missing_skill'].replace('_', ' ')} yet.",
                source=None, status="ANSWERED", committed=False)

        if op in ("add", "sub", "mul", "div"):
            result = student.solve(
                {"exercise_id": "bridge", "skill_id": "bridge",
                 "kind": "arith", "op": op, "a": core["x"],
                 "b": core["y"], "expected": None})
            if result["status"] == "CANNOT_MISSING_SKILL":
                return cannot(result)
            if result["status"] != "SOLVED":
                return seal_answer(
                    f"i cannot compute that: {result['detail']}",
                    source=None, committed=False)
            return seal_answer(
                f"{words(core['x'])} {self._OP_WORD[op]} "
                f"{words(core['y'])} is {words(result['answer'])}.")
        if op == "compare":
            result = student.solve(
                {"exercise_id": "bridge", "skill_id": "bridge",
                 "kind": "compare", "a": core["x"], "b": core["y"],
                 "expected": None})
            if result["status"] == "CANNOT_MISSING_SKILL":
                return cannot(result)
            verdict = result["answer"]
            asked = core.get("asked", "greater")
            x_w, y_w = words(core["x"]), words(core["y"])
            if verdict == asked:
                text = f"yes, {x_w} is {verdict} than {y_w}."
            elif verdict == "equal":
                text = f"no, {x_w} and {y_w} are equal."
            else:
                text = f"no, {x_w} is {verdict} than {y_w}."
            return seal_answer(text)
        if op == "solve":
            symbol = self._OP_SYMBOL.get(core.get("opword"))
            if symbol is None:
                return seal_answer(
                    "i cannot solve equations with that operation "
                    "yet.", source=None, committed=False)
            equation = (f"x {symbol} {core['b']} = {core['c']}")
            result = student.solve(
                {"exercise_id": "bridge", "skill_id": "bridge",
                 "kind": "solve", "equation": equation,
                 "variable": "x", "expected": None})
            if result["status"] == "CANNOT_MISSING_SKILL":
                return cannot(result)
            if result["status"] != "SOLVED":
                return seal_answer(
                    f"i cannot solve that: {result['detail']}",
                    source=None, committed=False)
            return seal_answer(
                f"x is {words(result['answer'])}. (verified by "
                f"substitution into the original equation)")
        return seal_answer(f"i do not know the operation {op!r}.",
                           source=None, committed=False)

    def _answer_wh_question(self, packet: Dict, gram: Dict,
                            trace: Dict) -> Dict:
        """'what'/'who': partial-proposition lookup over ACTIVE
        session assertions; multiple bindings are LISTED, never
        collapsed to one invented answer."""
        core = gram["core"]
        bindings = self.dialogue.wh_bindings(packet)
        trace.setdefault("dialogue", {})["retrieval"] = {
            "wh_bindings": [b for b, _ in bindings]}
        if core.get("patient") == "wh":
            question_clause = (f"what the {core.get('agent')} "
                               f"{core.get('predicate')}s")
        else:
            question_clause = (f"who {core.get('predicate')}s the "
                               f"{core.get('patient')}")
        if not bindings:
            text = (f"i do not know {question_clause} from the "
                    f"information i have.")
            source_class = None
        else:
            values = [b for b, _ in bindings]
            if core.get("patient") == "wh":
                filled = (f"the {core.get('agent')} "
                          f"{core.get('predicate')}s "
                          + " and ".join(f"the {v}" for v in values))
            else:
                filled = (" and ".join(f"the {v}" for v in values)
                          + (" chase" if len(values) > 1 else
                             f" {core.get('predicate')}s")
                          + f" the {core.get('patient')}")
                if len(values) > 1:
                    filled = (" and ".join(f"the {v}"
                                           for v in values)
                              + f" {core.get('predicate')} the "
                              + f"{core.get('patient')}")
            text = f"you told me that {filled}."
            source_class = "USER_ASSERTED"
        self._note_discourse(packet)
        trace["answer"] = {"status": "ANSWERED", "text": text,
                           "frame_core": core,
                           "source_class": source_class,
                           "wh_bindings": [b for b, _ in bindings]}
        return self._seal(trace, committed=True)

    def _record_assertion(self, trace: Dict, packet: Dict,
                          core, tense_hint=None) -> tuple:
        """The tell path. Returns (outcome, payload): ('stored',
        record) after the ATOMIC commit; ('clarification', None) when
        the new assertion conflicts unmarked with a prior one -
        never silently choose; ('fault', info) on a typed store
        fault - and then NO acknowledgment may be attached (the
        cardinal law)."""
        if trace.get("route") not in ("native", "native_gram"):
            # cortex-proposed readings are model guesses - never
            # promoted to user assertions
            return (None, None)
        tense = core.get("tense") if core else tense_hint
        if core and core.get("frame") in ("coordination",
                                          "disjunction"):
            # the record's tense derives from the conjuncts: uniform
            # -> that tense; disagreeing -> 'mixed', which matches NO
            # query (audit finding: a dropped tense became a
            # wildcard and affirmed a past claim never asserted)
            conjunct_tenses = {c.get("tense")
                               for c in core.get("conjuncts", [])
                               if isinstance(c, dict)}
            tense = (conjunct_tenses.pop()
                     if len(conjunct_tenses) == 1 else "mixed")
        polarity = core.get("polarity") if core else None
        modality = core.get("modality") if core else None
        # the clause renders from the PACKET - the committed truth -
        # never from the pretty frame core (smoke-found drop: the
        # acknowledgment for 'the cat does not chase the bird.' lost
        # its negation because render_clause ignores polarity)
        clause = self.dialogue.packet_to_clause(packet, tense)
        conflicts = self.dialogue.conflicting_active(packet, tense)
        dlg = trace.setdefault("dialogue", {})
        if conflicts:
            old_clause = conflicts[0]["clause"]
            self.dialogue.pending_question = {
                "type": "correction_confirmation",
                "candidate": {"proposition": packet, "clause": clause,
                              "tense": tense, "polarity": polarity,
                              "modality": modality},
                "conflicting_ids": [r["assertion_id"]
                                    for r in conflicts]}
            dlg["pending"] = "correction_confirmation"
            trace["answer"] = {
                "status": "CLARIFICATION_REQUESTED",
                "text": (f"you told me that {old_clause} and also "
                         f"that {clause}. is the second statement a "
                         f"correction?"),
                "frame_core": core}
            return ("clarification", None)
        try:
            record = self.dialogue.record_assertion(
                packet, clause, tense, polarity, modality,
                trace.get("turn_id", "t?"),
                provenance=f"user_turn:{trace.get('turn_id', 't?')}")
        except Exception as exc:
            dlg["assertion_fault"] = {"fault": type(exc).__name__,
                                      "detail": str(exc)[:200]}
            return ("fault", dlg["assertion_fault"])
        dlg["assertion"] = {"assertion_id": record["assertion_id"],
                            "record_digest": record["record_digest"],
                            "clause": record["clause"]}
        return ("stored", record)

    @staticmethod
    def _attach_assertion_result(trace: Dict, outcome, payload):
        """Acknowledgment ONLY after commit; a store fault yields the
        typed status and no acknowledgment at all."""
        if outcome == "stored":
            trace["answer"]["acknowledgment"] = \
                f"okay. you told me that {payload['clause']}."
            trace["answer"]["session_assertion"] = {
                "assertion_id": payload["assertion_id"],
                "record_digest": payload["record_digest"]}
        elif outcome == "fault":
            trace["answer"]["status"] = "ASSERTION_NOT_RECORDED"
            trace["answer"]["detail"] = (
                "i understood the sentence, but recording it failed "
                f"({payload['fault']}) - so i have NOT remembered it")

    def _dialogue_act_turn(self, act: Dict, sentence: str,
                           trace: Dict) -> Dict:
        """Social and dialogue-layer turns: no proposition stored, no
        verified knowledge changed - except through the typed intent
        path (retraction, correction, confirmed supersession)."""
        trace["route"] = "dialogue"
        dlg = trace.setdefault("dialogue", {})
        dlg["act"] = act["act"]
        kind = act["act"]
        if kind in ("GREETING", "CLOSING", "GRATITUDE"):
            trace["answer"] = {"status": "ANSWERED",
                               "text": act["reply"],
                               "dialogue_act": kind}
            return self._seal(trace, committed=True)
        if kind == "POLAR_RESPONSE":
            return self._polar_response_turn(act, trace)
        if kind == "RETRACTION":
            return self._retraction_turn(act, trace)
        if kind == "ENTITY_SUMMARY":
            return self._entity_summary_turn(act, trace)
        if kind == "CORRECTION":
            return self._correction_turn(act, sentence, trace)
        trace["answer"] = {"status": "UNSUPPORTED_LANGUAGE",
                           "detail": f"unhandled dialogue act {kind}"}
        return self._seal(trace, committed=False)

    def _polar_response_turn(self, act: Dict, trace: Dict) -> Dict:
        pending = self.dialogue.pending_question
        word = act["polarity"]
        if pending is None:
            trace["answer"] = {
                "status": "NO_PENDING_QUESTION",
                "text": (f"there is no pending question for "
                         f"'{word}' to answer.")}
            return self._seal(trace, committed=False)
        if pending["type"] == "correction_confirmation":
            candidate = pending["candidate"]
            conflicting = pending["conflicting_ids"]
            turn_id = trace.get("turn_id", "t?")
            self.dialogue.pending_question = None
            # STALENESS GUARD (audit finding, cardinal): every record
            # the confirmation would touch must STILL be ACTIVE -
            # a retraction in between makes the confirmation moot
            stale = [aid for aid in conflicting
                     if (self.dialogue.store.get(aid) or {}).get(
                         "lifecycle_status") != "ACTIVE"]
            if stale:
                trace["answer"] = {
                    "status": "NO_PENDING_QUESTION",
                    "text": ("the earlier statement this would "
                             "correct is no longer active - there is "
                             "nothing to confirm. tell me the "
                             "statement again if you want it "
                             "recorded.")}
                return self._seal(trace, committed=False)
            # every mutation below is TYPED-GUARDED: a store fault
            # yields the honest split status, never a crash, never a
            # claim (the cardinal law)
            try:
                if word == "yes":
                    old_clauses = []
                    record = self.dialogue.record_assertion(
                        candidate["proposition"], candidate["clause"],
                        candidate["tense"], candidate["polarity"],
                        candidate["modality"], turn_id,
                        provenance=f"user_turn:{turn_id}"
                                   f"+confirmed_correction",
                        supersedes=conflicting)
                    for aid in conflicting:
                        old = self.dialogue.store.get(aid)
                        old_clauses.append(old["clause"])
                        self.dialogue.apply_lifecycle(
                            aid, "SUPERSEDED",
                            f"corrected by {record['assertion_id']}",
                            turn_id)
                    trace.setdefault("dialogue", {})["assertion"] = {
                        "assertion_id": record["assertion_id"],
                        "record_digest": record["record_digest"],
                        "clause": record["clause"]}
                    trace["answer"] = {
                        "status": "ANSWERED",
                        "text": (f"understood. i will use "
                                 f"'{candidate['clause']}' in this "
                                 f"session. you previously said "
                                 f"'{'; '.join(old_clauses)}'."),
                        "session_assertion": {
                            "assertion_id": record["assertion_id"]}}
                    return self._seal(trace, committed=True)
                # 'no' - both statements stand, CONTESTED: neither
                # supports answers until settled
                record = self.dialogue.record_assertion(
                    candidate["proposition"], candidate["clause"],
                    candidate["tense"], candidate["polarity"],
                    candidate["modality"], turn_id,
                    provenance=f"user_turn:{turn_id}+not_a_correction")
                self.dialogue.apply_lifecycle(
                    record["assertion_id"], "CONTESTED",
                    "user affirmed both conflicting statements",
                    turn_id)
                for aid in conflicting:
                    self.dialogue.apply_lifecycle(
                        aid, "CONTESTED",
                        "user affirmed both conflicting statements",
                        turn_id)
                trace["answer"] = {
                    "status": "ANSWERED",
                    "text": ("understood. both statements stand as "
                             "contested - i will not answer from "
                             "either until it is settled.")}
                return self._seal(trace, committed=True)
            except Exception as exc:
                trace.setdefault("dialogue", {})["assertion_fault"] = {
                    "fault": type(exc).__name__,
                    "detail": str(exc)[:200]}
                trace["answer"] = {
                    "status": "ASSERTION_NOT_RECORDED",
                    "detail": ("recording your confirmation failed "
                               f"({type(exc).__name__}) - the "
                               "correction was NOT completed; the "
                               "session record may hold the new "
                               "statement without the supersession, "
                               "and both versions stay visible")}
                return self._seal(trace, committed=False)
        trace["answer"] = {"status": "NO_PENDING_QUESTION",
                           "text": f"i cannot apply '{word}' to the "
                                   f"pending item."}
        return self._seal(trace, committed=False)

    def _resolve_noun(self, word: str):
        entry = self.seed["lexicon"].get(word)
        if entry and entry.get("pos") == "noun":
            return entry["sense"]
        return None

    def _retraction_turn(self, act: Dict, trace: Dict) -> Dict:
        entity = self._resolve_noun(act["entity_word"])
        if entity is None:
            trace["answer"] = {
                "status": "UNSUPPORTED_LANGUAGE",
                "detail": f"i do not know the word "
                          f"{act['entity_word']!r}"}
            return self._seal(trace, committed=False)
        records = (self.dialogue.about(entity)
                   + self.dialogue.about_contested(entity))
        if not records:
            trace["answer"] = {
                "status": "ANSWERED",
                "text": (f"you have not told me anything about the "
                         f"{entity} this session.")}
            return self._seal(trace, committed=True)
        turn_id = trace.get("turn_id", "t?")
        clauses = []
        try:
            for record in records:
                self.dialogue.apply_lifecycle(
                    record["assertion_id"], "RETRACTED",
                    "user retraction", turn_id)
                clauses.append(record["clause"])
        except Exception as exc:
            trace.setdefault("dialogue", {})["assertion_fault"] = {
                "fault": type(exc).__name__}
            trace["answer"] = {
                "status": "ASSERTION_NOT_RECORDED",
                "detail": (f"the retraction failed partway "
                           f"({type(exc).__name__}) - retracted so "
                           f"far: {'; '.join(clauses) or 'nothing'}; "
                           "the rest still stands")}
            return self._seal(trace, committed=False)
        trace.setdefault("dialogue", {})["retracted"] = [
            r["assertion_id"] for r in records]
        trace["answer"] = {
            "status": "ANSWERED",
            "text": (f"understood. i will no longer use what you "
                     f"told me about the {entity}: "
                     + "; ".join(clauses) + ". the record of the "
                     "retraction is kept.")}
        return self._seal(trace, committed=True)

    def _entity_summary_turn(self, act: Dict, trace: Dict) -> Dict:
        entity = self._resolve_noun(act["entity_word"])
        if entity is None:
            trace["answer"] = {
                "status": "UNSUPPORTED_LANGUAGE",
                "detail": f"i do not know the word "
                          f"{act['entity_word']!r}"}
            return self._seal(trace, committed=False)
        verified_clauses = []
        for fact in self.seed["cmb_facts"]:
            args = fact.get("args", [])
            if fact.get("pred") == "has" and args \
                    and args[0] == entity:
                verified_clauses.append(f"the {args[0]} is {args[1]}")
        session_records = self.dialogue.about(entity)
        session_clauses = [r["clause"] for r in session_records]
        contested_clauses = [r["clause"] for r in
                             self.dialogue.about_contested(entity)]
        parts = []
        if verified_clauses:
            parts.append("the verified record says "
                         + " and ".join(verified_clauses) + ".")
        if session_clauses:
            parts.append("you told me that "
                         + "; ".join(session_clauses) + ".")
        if contested_clauses:
            parts.append("you gave me conflicting statements that "
                         "are still unsettled: "
                         + "; ".join(contested_clauses) + ".")
        if not parts:
            parts.append(f"i have no information about the "
                         f"{entity}.")
        trace.setdefault("dialogue", {})["retrieval"] = {
            "verified_count": len(verified_clauses),
            "session_count": len(session_clauses)}
        trace["answer"] = {"status": "ANSWERED",
                           "text": " ".join(parts),
                           "source_classes": {
                               "verified": len(verified_clauses),
                               "user_asserted": len(session_clauses)}}
        return self._seal(trace, committed=True)

    def _correction_turn(self, act: Dict, sentence: str,
                         trace: Dict) -> Dict:
        """'actually, X.' - parse X, supersede what it corrects,
        commit the new record. Supersession is explicit and audited;
        the old record stays in history."""
        body = sentence.split(" ", 1)[1] if " " in sentence else ""
        packet = core = None
        native = self._native(body)
        if native["status"] == "PARSED":
            packet = native["meaning"]
        else:
            gram = self.gram_parser.parse(self.grammar.active_rules(),
                                          body)
            if gram["status"] == "PARSED":
                mood = gram["frames"][0]["surface"].get("mood")
                if mood in (None, "declarative"):
                    core = gram["core"]
                    refused = self._resolve_pronouns(core, trace)
                    if refused is not None:
                        return refused
                    packet = self._frame_to_packet(core)
        if packet is None:
            trace["answer"] = {
                "status": "UNSUPPORTED_LANGUAGE",
                "detail": "i did not understand the corrected "
                          "statement after 'actually,'"}
            return self._seal(trace, committed=False)
        tense = core.get("tense") if core else "present"
        clause = (render_clause(core)
                  if core and core.get("frame") in ("event", "state")
                  else self.dialogue.packet_to_clause(packet, tense))
        conflicts = self.dialogue.conflicting_active(packet, tense)
        turn_id = trace.get("turn_id", "t?")
        try:
            record = self.dialogue.record_assertion(
                packet, clause, tense,
                core.get("polarity") if core else None,
                core.get("modality") if core else None,
                turn_id, provenance=f"user_turn:{turn_id}+correction",
                supersedes=[r["assertion_id"] for r in conflicts])
        except Exception as exc:
            trace.setdefault("dialogue", {})["assertion_fault"] = {
                "fault": type(exc).__name__}
            trace["answer"] = {
                "status": "ASSERTION_NOT_RECORDED",
                "detail": "recording the correction failed - "
                          "nothing was remembered or superseded"}
            return self._seal(trace, committed=False)
        old_clauses = []
        for prior in conflicts:
            old_clauses.append(prior["clause"])
            self.dialogue.apply_lifecycle(
                prior["assertion_id"], "SUPERSEDED",
                f"corrected by {record['assertion_id']}", turn_id)
        trace.setdefault("dialogue", {})["assertion"] = {
            "assertion_id": record["assertion_id"],
            "record_digest": record["record_digest"],
            "clause": record["clause"]}
        self._note_discourse(packet)
        if old_clauses:
            text = (f"understood. i will use '{clause}' in this "
                    f"session. you previously said "
                    f"'{'; '.join(old_clauses)}'.")
        else:
            # the user MARKED this a correction but nothing on the
            # record conflicts with it - say so, never silently
            # downgrade to a plain tell (audit finding)
            trace.setdefault("dialogue", {})[
                "correction_without_target"] = True
            text = (f"okay. you told me that {clause}. nothing i "
                    f"previously recorded conflicts with it, so "
                    f"nothing was superseded.")
        trace["answer"] = {"status": "ANSWERED", "text": text,
                           "session_assertion": {
                               "assertion_id": record["assertion_id"]}}
        return self._seal(trace, committed=True)

    def _note_discourse(self, packet) -> None:
        entities = HybridRouter._entity_atoms(packet)
        if entities:
            self.discourse_entities = entities

    def _resolve_pronouns(self, core: Dict,
                          trace: Dict) -> Optional[Dict]:
        """Resolve 'pron:*' bindings against the previous committed
        turn. One candidate -> resolve; several -> honest
        clarification; none -> honest refusal. Returns a sealed trace
        on refusal, None when the turn may proceed."""
        pron_slots = [(key, value) for key, value in core.items()
                      if isinstance(value, str)
                      and value.startswith("pron:")]
        if not pron_slots:
            return None
        candidates = list(dict.fromkeys(self.discourse_entities))
        if len(candidates) == 1:
            for key, value in pron_slots:
                core[key] = candidates[0]
            trace["pronoun_resolution"] = {
                "resolved": {key: candidates[0]
                             for key, _ in pron_slots},
                "antecedent_pool": candidates}
            return None
        if not candidates:
            trace["answer"] = {
                "status": "UNRESOLVED_PRONOUN",
                "frame_core": core,
                "detail": "the pronoun has no antecedent - no prior "
                          "sentence names an entity; say the noun "
                          "first. A guess is never invented"}
            return self._seal(trace, committed=False)
        trace["answer"] = {
            "status": "AMBIGUOUS_ANTECEDENT",
            "frame_core": core,
            "candidates": candidates,
            "detail": "the pronoun could name any of "
                      f"{candidates} from the previous sentence - "
                      "clarification needed, certainty is never "
                      "invented"}
        return self._seal(trace, committed=False)

    def _kernel_answer(self, meaning: Dict) -> Dict:
        result = answer_question(meaning, self.seed["cmb_facts"],
                                 self.seed["rules"])
        answer = decode_verdict(result["kernel_packet"], result["meaning"])
        return {"kernel_status": result["kernel_packet"]["terminal_status"],
                "answer": answer}

    # ------------------------------------------------------------------
    def turn(self, sentence: str) -> Dict:
        """One conversational turn -> sealed TurnTrace."""
        trace: Dict = {"input": sentence, "mode": self.mode,
                       "route": None, "cortex_proposal": None,
                       "validation": None, "commitment": None,
                       "answer": None}

        from lang.grammar import tokenize as _tokenize
        turn_id, _tick = self.dialogue.begin_turn()
        trace["turn_id"] = turn_id

        # CCB-D1 SURFACE ACTS: greetings, thanks, closings, bare
        # yes/no, retraction, entity summary, and the 'actually,'
        # correction prefix are DIALOGUE-layer forms - they update
        # dialogue state, never semantic knowledge, and only through
        # the typed intent path.
        act = self.dialogue.classify_surface(_tokenize(sentence))
        if self.dialogue.pending_question is not None \
                and (act is None or act["act"] != "POLAR_RESPONSE"):
            # the user moved on: a pending clarification is DROPPED
            # (recorded) rather than left armed - a stale bare 'yes.'
            # turns later superseded records it was never about
            # (audit finding, cardinal lens)
            trace.setdefault("dialogue", {})["pending_dropped"] = \
                self.dialogue.pending_question["type"]
            self.dialogue.pending_question = None
        if act is not None:
            return self._dialogue_act_turn(act, sentence, trace)

        native = self._native(sentence)
        if native["status"] == "PARSED":
            trace["route"] = "native"
            self.coverage["native_l1"] += 1
            committed = self._commit(native["meaning"], trace)
            return self._seal(trace, committed)

        # LEARNED GRAMMAR lane: constructions promoted through the
        # acceptance law parse here - natively, deterministically,
        # with no cortex. Ambiguity is reported, never resolved.
        gram = self.gram_parser.parse(self.grammar.active_rules(),
                                      sentence)
        if gram["status"] == "PARSED":
            trace["route"] = "native_gram"
            self.coverage["native_gram"] += 1
            trace["frame"] = gram["frames"][0]
            refused = self._resolve_pronouns(gram["core"], trace)
            if refused is not None:
                return refused
            packet = self._frame_to_packet(gram["core"])
            trace["commitment"] = {"by": "cas_learned_grammar",
                                   "construction": gram["frames"][0]
                                   ["surface"]["construction_id"]}
            mood = gram["frames"][0]["surface"].get("mood")
            if mood == "math_query":
                # THE MATHEMATICAL LANGUAGE BRIDGE: a taught English
                # construction linked to a CAS-Math operation. The
                # answer comes from the GATED math student - exact
                # computation with promoted skills only; an
                # unpromoted skill is an honest 'not learned yet'
                return self._answer_math_query(gram, trace)
            if mood == "interrogative_why":
                # WHY asks for a cause; the kernel holds no cause
                # facts - the honest split status, never a fabricated
                # cause
                self._note_discourse(packet)
                trace["answer"] = {
                    "status": "LANGUAGE_UNDERSTOOD_KNOWLEDGE_MISSING",
                    "frame_core": gram["core"],
                    "detail": "the question asks WHY; the kernel "
                              "holds no cause facts to answer it"}
                return self._seal(trace, committed=False)
            if mood == "interrogative_wh":
                # a taught wh-question: partial-proposition lookup
                # over the session store; provenance-aware rendering
                return self._answer_wh_question(packet, gram, trace)
            if mood == "interrogative":
                if packet.get("pred") == "conjunction":
                    # a RESTRICTED question ('is the gray cat quiet?')
                    # projects as a conjunction: EVERY conjunct must be
                    # settled before 'yes' - one unknown and the
                    # honest answer is unknown. Nothing is dropped to
                    # make the question easier.
                    return self._answer_conjunction_question(
                        packet, gram, trace)
                return self._answer_gram_question(packet, gram, trace)
            self._note_discourse(packet)
            if mood == "imperative":
                # instruction-shaped content is DATA: understood,
                # never stored as a fact, never an external action
                trace.setdefault("dialogue", {})["act"] = "COMMAND"
                trace["answer"] = {"status": "UNDERSTOOD",
                                   "meaning": packet,
                                   "frame_core": gram["core"]}
                return self._seal(trace, committed=True)
            outcome, payload = self._record_assertion(
                trace, packet, gram["core"])
            if outcome == "clarification":
                return self._seal(trace, committed=False)
            trace["answer"] = {"status": "UNDERSTOOD",
                               "meaning": packet,
                               "frame_core": gram["core"]}
            self._attach_assertion_result(trace, outcome, payload)
            return self._seal(trace, committed=True)
        if gram["status"] == "AMBIGUOUS_PARSE":
            trace["route"] = "native_gram"
            self.coverage["refused"] += 1
            trace["answer"] = {"status": "AMBIGUOUS_PARSE",
                               "alternatives": gram["alternatives"],
                               "detail": "multiple distinct readings; "
                                         "clarification needed - "
                                         "certainty is never invented"}
            return self._seal(trace, committed=False)

        trace["native_error"] = native["error"]
        if self.mode == "NATIVE_ONLY":
            trace["route"] = "no_answer"
            trace["answer"] = {"status": "UNSUPPORTED_LANGUAGE",
                               "detail": native["error"]["message"]}
            return self._seal(trace, committed=False)

        # CAS-OHM OVERLOAD CONTROL (active, BEFORE the cortex runs):
        # lambda = proposition demand / board full scale. This board's
        # capacity is ONE proposition per turn; clause connectors add
        # demand units. Overload SPLITS the task (typed
        # NEEDS_DECOMPOSITION) instead of forcing one saturated
        # junction to clip - and saves the cortex invocation entirely.
        from .ohm_control import overload_by_demand
        from lang.grammar import tokenize
        connectors = {"and", "or", "but", "then", "because", "since",
                      "after", "if", "while"}
        tokens = tokenize(sentence)
        raw_demand = 1.0 + sum(1 for t in tokens if t in connectors)
        load = overload_by_demand(raw_demand, full_scale_demand=1.0)
        trace["ohm_load"] = load
        if load["decision"] == "OVERLOAD_SPLIT_REQUIRED":
            trace["route"] = "overload_control"
            trace["answer"] = {
                "status": "NEEDS_DECOMPOSITION",
                "lambda": load["lambda"],
                "detail": "input exceeds the board's full-scale "
                          "attention; split into parts and ask them "
                          "one at a time"}
            return self._seal(trace, committed=False)

        # cortex-assisted routing: the cortex PROPOSES
        proposal = self.cortex.propose(sentence)
        self.firewall.submit("cortex", "ProposeSemanticPacket",
                             {"proposal_id": proposal["proposal_id"]})
        trace["route"] = "cortex"
        trace["cortex_proposal"] = proposal

        try:
            validation = validate_proposal(proposal)
        except ProposalRejected as exc:
            trace["validation"] = {"outcome": "REJECTED",
                                   "reason": str(exc)}
            trace["answer"] = {"status": "NEEDS_CLARIFICATION",
                               "detail": "cortex proposal rejected by "
                                         "validation: " + str(exc)}
            return self._seal(trace, committed=False)

        trace["validation"] = {"outcome": "ACCEPTED"
                               if validation["accepted"] is not None
                               else "NO_PACKET",
                               "note": validation["note"]}

        if validation["accepted"] is None:
            unknowns = proposal.get("unknown_tokens", [])
            trace["answer"] = {
                "status": "UNKNOWN_LEXEME" if unknowns
                else "NEEDS_CLARIFICATION",
                "unknown_tokens": unknowns,
                "detail": "the cortex reported no admissible "
                          "interpretation"}
            return self._seal(trace, committed=False)

        # LEXICAL GROUNDING GATE: every atom in a cortex packet must
        # be a sense or entity the machine actually knows. A
        # well-formed packet around an invented word (the live Gate 4
        # failure: property(glimmerfor, gray) committed as UNDERSTOOD)
        # is caught HERE, on the CAS side.
        ungrounded = sorted(set(self._atoms(validation["accepted"]))
                            - self.grounded)
        if ungrounded:
            trace["validation"]["grounding"] = {
                "outcome": "UNGROUNDED", "atoms": ungrounded}
            trace["answer"] = {"status": "UNGROUNDED_TERM",
                               "ungrounded_atoms": ungrounded,
                               "detail": "the proposal uses terms the "
                                         "machine has never learned; "
                                         "nothing is committed"}
            return self._seal(trace, committed=False)
        trace["validation"]["grounding"] = {"outcome": "GROUNDED"}

        # CONTENT-FAITHFULNESS GATE (battery v1 dev-split finding: the
        # dominant fabrication genus is a grounded packet that SILENTLY
        # DROPS content or invents a referent). Two rules:
        #   R1 no dropped known content - every input token that is a
        #      known content word must have its sense in the packet;
        #   R2 entities attested - every entity-slot atom must be the
        #      sense of some input token (verb/property slots stay
        #      free: synonym handling is the cortex's legitimate job).
        mismatch = self._content_mismatch(sentence,
                                          validation["accepted"])
        if mismatch:
            trace["validation"]["faithfulness"] = {
                "outcome": "CONTENT_MISMATCH", **mismatch}
            trace["answer"] = {"status": "CONTENT_MISMATCH",
                               **mismatch,
                               "detail": "the proposal drops or invents "
                                         "content; nothing is committed"}
            return self._seal(trace, committed=False)
        trace["validation"]["faithfulness"] = {"outcome": "FAITHFUL"}

        if self.mode == "CORTEX_DIAGNOSTIC":
            # recorded, but MUST NOT affect commitment
            trace["answer"] = {"status": "UNSUPPORTED_LANGUAGE",
                               "detail": "diagnostic mode: the proposal "
                                         "is recorded, never committed"}
            return self._seal(trace, committed=False)

        committed = self._commit(validation["accepted"], trace)
        return self._seal(trace, committed)

    def _content_mismatch(self, sentence: str, packet: Dict):
        """R1/R2 faithfulness check for cortex packets. Returns None
        when faithful, else a dict naming the violation."""
        from lang.grammar import tokenize
        tokens = [t for t in tokenize(sentence) if t not in (".", "?")]
        content_pos = ("noun", "adj", "verb")
        lexicon = self.seed["lexicon"]
        atoms = set(self._atoms(packet))
        # R1: known content words may not be dropped
        dropped = sorted({lexicon[t]["sense"] for t in tokens
                          if t in lexicon
                          and lexicon[t]["pos"] in content_pos
                          and lexicon[t]["sense"] not in atoms})
        if dropped:
            return {"rule": "R1_dropped_known_content",
                    "dropped": dropped}
        # R2: entity-slot atoms must be attested by input tokens
        token_senses = {lexicon[t]["sense"] for t in tokens if t in lexicon}
        unattested = sorted(set(self._entity_atoms(packet))
                            - token_senses)
        if unattested:
            return {"rule": "R2_unattested_entity",
                    "unattested": unattested}
        return None

    @staticmethod
    def _frame_to_packet(core: Dict) -> Dict:
        """Learned-grammar frames render to the legacy packet format.
        POLARITY IS NEVER DROPPED (ledger-round fix: a negative event
        frame used to project identically to its positive - the exact
        silently-dropped-content fabrication genus): negative frames
        wrap in the legacy negation packet."""
        if core.get("frame") in ("coordination", "disjunction"):
            # EVERY clause survives - dropping one is the fabrication
            # genus the faithfulness gate exists to catch; and/or stay
            # DISTINCT packets (the non-collapse law)
            pred = ("conjunction" if core["frame"] == "coordination"
                    else "disjunction")
            return {"pred": pred,
                    "args": [HybridRouter._frame_to_packet(conjunct)
                             for conjunct in core["conjuncts"]]}
        if core.get("frame") == "event":
            args = [core["predicate"], core["agent"], core["patient"]]
            quantifier = core.get("quantifier")
            if core.get("recipient"):
                # ditransitive: the recipient role SURVIVES (4-arg
                # relation) - dropping a role is the content-drop genus
                args.append(core["recipient"])
            inner = {"pred": "relation", "args": args}
            modifiers = []
            if core.get("agent_mod"):
                modifiers.append({"pred": "property",
                                  "args": [core["agent"],
                                           core["agent_mod"]]})
            if core.get("patient_mod"):
                modifiers.append({"pred": "property",
                                  "args": [core["patient"],
                                           core["patient_mod"]]})
            for role in ("agent", "patient", "recipient"):
                # PLURALITY IS NEVER DROPPED (same law as polarity):
                # 'the cats chase the dog' may not project identically
                # to 'the cat chases the dog'
                if core.get(role + "_number") == "plural":
                    modifiers.append({"pred": "number",
                                      "args": [core[role], "plural"]})
            if core.get("time"):
                # the temporal adverb SURVIVES projection
                modifiers.append({"pred": "time",
                                  "args": [core["time"]]})
            if modifiers:
                # attributive adjectives project as conjoined property
                # assertions - every modifier survives
                inner = {"pred": "conjunction",
                         "args": [inner] + modifiers}
            if quantifier:
                # the quantifier SURVIVES projection - 'every cat',
                # 'some cat', 'no cat' are THREE distinct meanings
                # (the non-collapse law)
                inner = {"pred": "quantified",
                         "args": [quantifier, inner]}
            if core.get("modality") == "prohibition":
                # 'must not' SURVIVES as a norm: a PROHIBITED chase is
                # not an absent chase ('does not' = polarity negative)
                # and not an asserted chase - three distinct meanings
                inner = {"pred": "prohibition", "args": [inner]}
        else:
            if core.get("location"):
                inner = {"pred": "location",
                         "args": [core.get("entity"),
                                  core.get("location")]}
            elif core.get("comparison"):
                # a comparative IS a two-place relation:
                # relation(bigger, cat, dog)
                inner = {"pred": "relation",
                         "args": [core.get("comparison"),
                                  core.get("entity"),
                                  core.get("than")]}
            else:
                inner = {"pred": "property",
                         "args": [core.get("entity"),
                                  core.get("property")]}
            state_mods = []
            if core.get("modifier"):
                # the restricting adjective SURVIVES projection -
                # 'is the gray cat quiet?' may not project identically
                # to 'is the cat quiet?'
                state_mods.append({"pred": "property",
                                   "args": [core.get("entity"),
                                            core.get("modifier")]})
            if core.get("possessor"):
                # possession SURVIVES: "the cat's bone" asserts
                # possession(cat, bone)
                state_mods.append({"pred": "possession",
                                   "args": [core.get("possessor"),
                                            core.get("entity")]})
            if core.get("relative"):
                # the relative clause SURVIVES as its own event packet
                state_mods.append(
                    HybridRouter._frame_to_packet(core["relative"]))
            if state_mods:
                inner = {"pred": "conjunction",
                         "args": [inner] + state_mods}
        if core.get("polarity") == "negative":
            return {"pred": "negation", "args": [inner]}
        return inner

    @staticmethod
    def _entity_atoms(packet) -> List[str]:
        """Entity-slot atoms only: property args[0]; relation args[1:]."""
        entities: List[str] = []
        if not isinstance(packet, dict):
            return entities
        pred = packet.get("pred")
        args = packet.get("args", [])
        if pred == "property" and args:
            entities.append(args[0])
        elif pred == "relation" and len(args) >= 3:
            entities.extend(args[1:])
        elif pred in ("negation", "question") and args:
            entities.extend(HybridRouter._entity_atoms(args[0]))
        elif pred in ("conjunction", "disjunction"):
            for part in args:
                entities.extend(HybridRouter._entity_atoms(part))
        elif pred == "quantified" and len(args) == 2:
            entities.extend(HybridRouter._entity_atoms(args[1]))
        elif pred in ("location", "possession") and len(args) == 2:
            entities.extend(a for a in args if isinstance(a, str))
        return entities

    @staticmethod
    def _atoms(packet) -> List[str]:
        """Every atom string inside a semantic packet."""
        atoms: List[str] = []
        if isinstance(packet, dict):
            for arg in packet.get("args", []):
                if isinstance(arg, str):
                    atoms.append(arg)
                else:
                    atoms.extend(HybridRouter._atoms(arg))
        return atoms

    # ------------------------------------------------------------------
    def _commit(self, meaning: Dict, trace: Dict) -> bool:
        """Commitment stays with CAS. Questions consult the verified
        kernel FIRST, then the session assertion store - sources never
        collapsed. Statements on native routes become session
        assertions through the typed intent path (CONV v0.1);
        acknowledgment attaches only AFTER the atomic commit."""
        if meaning.get("pred") == "question":
            kernel = self._kernel_answer(meaning)
            trace["commitment"] = {"by": "cas_kernel",
                                   "kernel_status": kernel["kernel_status"]}
            inner = (meaning.get("args") or [{}])[0]
            support = self.dialogue.support_for(inner, None)
            conflicts = self.dialogue.conflicting_active(inner)
            trace.setdefault("dialogue", {})["retrieval"] = {
                "kernel_status": kernel["kernel_status"],
                "session_verdict": support and support.get("verdict"),
                "conflicting": [r["assertion_id"]
                                for r in conflicts]}
            concluded = kernel["kernel_status"] == "CONCLUDED"
            if concluded and conflicts:
                clause = self.dialogue.packet_to_clause(inner)
                told = self.dialogue.packet_to_clause(
                    conflicts[0]["proposition"],
                    conflicts[0].get("tense"))
                trace["answer"] = {
                    "status": "ANSWERED",
                    "text": (f"i have conflicting information: the "
                             f"verified record says {clause}; you "
                             f"told me {told}."),
                    "source_class": "CONFLICT"}
            elif concluded:
                trace["answer"] = {"status": "ANSWERED",
                                   "text": kernel["answer"],
                                   "source_class": "VERIFIED"}
            elif support and support["verdict"] == "yes":
                clause = self.dialogue.packet_to_clause(
                    inner, support["record"].get("tense"))
                trace["answer"] = {
                    "status": "ANSWERED",
                    "text": (f"based on what you told me, yes, "
                             f"{clause}."),
                    "source_class": "USER_ASSERTED"}
            elif support and support["verdict"] == "no":
                told = self.dialogue.packet_to_clause(
                    support["record"]["proposition"],
                    support["record"].get("tense"))
                trace["answer"] = {
                    "status": "ANSWERED",
                    "text": (f"based on what you told me, no - you "
                             f"told me that {told}."),
                    "source_class": "USER_ASSERTED"}
            elif support and support["verdict"] == "contested":
                trace["answer"] = {
                    "status": "ANSWERED",
                    "text": ("you gave me conflicting statements "
                             "about this - i cannot answer until it "
                             "is settled."),
                    "source_class": "CONTESTED"}
            else:
                trace["answer"] = {"status": "ANSWERED",
                                   "text": kernel["answer"],
                                   "source_class": None}
        else:
            trace["commitment"] = {"by": "cas_parse_acknowledgement"}
            # the legacy native grammar covers PRESENT forms only,
            # so its statements carry tense 'present' (disclosed
            # annotation - conflict detection is tense-strict)
            outcome, payload = self._record_assertion(
                trace, meaning, core=None, tense_hint="present")
            if outcome == "clarification":
                self._note_discourse(meaning)
                return False
            trace["answer"] = {"status": "UNDERSTOOD",
                               "meaning": meaning}
            self._attach_assertion_result(trace, outcome, payload)
        self._note_discourse(meaning)
        return True

    def _seal(self, trace: Dict, committed: bool) -> Dict:
        trace["committed"] = committed
        # CAS-OHM test points for the CONV path: compute-only flow
        # decoration - it locates energized vs starved stations
        # (language failure vs memory-write failure vs
        # provenance-rendering fault); it never decides truth
        answer = trace.get("answer") or {}
        dlg = trace.get("dialogue") or {}
        parsed = trace.get("route") in ("native", "native_gram",
                                        "dialogue", "cortex")
        trace["conv_flow"] = {
            "tp_parse": "active" if parsed else "cutoff",
            "tp_semantic_packet": "active"
            if (answer.get("meaning") or answer.get("frame_core")
                or trace.get("frame") or dlg.get("act"))
            else "absent",
            "tp_write_intent": "active"
            if (dlg.get("assertion") or dlg.get("assertion_fault")
                or dlg.get("pending")) else "absent",
            "tp_session_commit": "active" if dlg.get("assertion")
            else ("cutoff" if dlg.get("assertion_fault")
                  else "absent"),
            "tp_retrieval": "active" if "retrieval" in dlg
            else "absent",
            "tp_answer": "active"
            if (answer.get("text") or answer.get("acknowledgment")
                or answer.get("status") == "UNDERSTOOD")
            else "cutoff",
            "authority_note": "compute-only: no truth, validity, "
                              "meaning, commitment, or permission "
                              "decision may read this record",
        }
        # the native CAS-Ohm attention record: COMPUTE-ONLY decoration,
        # authored AFTER the answer is decided; nothing above reads it
        from .attention import stage_record
        trace["cas_ohm"] = stage_record(trace)
        trace["trace_digest"] = _digest(trace)
        self.traces.append(trace)
        return trace
