"""CCB-D1: the Dialogue and Common-Ground Board.

Owns: utterance-act classification, the session assertion flow
(propose -> validate -> coordinator-commit), sound retrieval
entailment, conflict detection, correction/retraction/contestation,
pending-question state, and provenance-preserving clause rendering.

The frozen acceptance law (CONV_ACCEPTANCE_LAW_v0.1.md):
acknowledge only AFTER atomic commit; answer only with the source
preserved; never silently promote a user assertion into verified
knowledge; with no admissible record, ask or say i-do-not-know.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .assertions import SessionAssertionStore
from .intents import (IntentRejected, TransactionCoordinator,
                      make_lifecycle_intent, make_write_intent)

# Mutually-exclusive attribute classes: the minimal world knowledge
# conflict detection needs ('gray' vs 'brown' conflict; 'gray' vs
# 'quiet' do not). BOARD MACHINERY, disclosed - the future home of
# this map is the taught-knowledge protocol, not a growing hardcode.
ATTRIBUTE_CLASSES = {
    "color": {"gray", "brown"},
    "size": {"small", "large"},
}

GREETING_REPLIES = {
    ("hello",): ("GREETING", "hello."),
    ("hi",): ("GREETING", "hello."),
    ("goodbye",): ("CLOSING", "goodbye."),
    ("bye",): ("CLOSING", "goodbye."),
    ("thank", "you"): ("GRATITUDE", "you are welcome."),
    ("thanks",): ("GRATITUDE", "you are welcome."),
}


def _attribute_class(value: str) -> Optional[str]:
    for name, members in ATTRIBUTE_CLASSES.items():
        if value in members:
            return name
    return None


def _tense_compatible(query_tense, stored_tense) -> bool:
    """Both known -> must match. Either unknown (the legacy native
    lane carries no tense) -> compatible, disclosed weakest reading."""
    if query_tense is None or stored_tense is None:
        return True
    return query_tense == stored_tense


class DialogueBoard:
    def __init__(self, session_id: str = "session",
                 speaker_id: str = "user") -> None:
        self.session_id = session_id
        self.speaker_id = speaker_id
        self.store = SessionAssertionStore(session_id)
        self.coordinator = TransactionCoordinator(self.store)
        self.pending_question: Optional[Dict] = None
        self.tick = 0

    # ------------------------------------------------------------------
    def begin_turn(self) -> Tuple[str, int]:
        self.tick += 1
        return f"t{self.tick}", self.tick

    # ---------------------------------------------- act classification
    def classify_surface(self, tokens: List[str]) -> Optional[Dict]:
        """Full-token-match dialogue-layer forms. Anything not matched
        here flows to the grammar lanes unchanged."""
        words = tuple(t for t in tokens if t not in (".", "?", "!"))
        if words in GREETING_REPLIES:
            act, reply = GREETING_REPLIES[words]
            return {"act": act, "reply": reply}
        if words in (("yes",), ("no",)):
            return {"act": "POLAR_RESPONSE",
                    "polarity": words[0]}
        if len(words) == 7 and words[:6] == ("forget", "what", "i",
                                             "said", "about", "the"):
            return {"act": "RETRACTION", "entity_word": words[6]}
        if len(words) == 5 and words[:4] == ("tell", "me", "about",
                                             "the"):
            return {"act": "ENTITY_SUMMARY", "entity_word": words[4]}
        if tokens and tokens[0] == "actually,":
            return {"act": "CORRECTION",
                    "body_tokens": tokens[1:]}
        return None

    # ---------------------------------------------- assertion writing
    def record_assertion(self, proposition: Dict, clause: str,
                         tense, polarity, modality, turn_id: str,
                         provenance: str,
                         supersedes: List[str] = ()) -> Dict:
        """Propose the typed intent and hand it to the coordinator.
        Returns the COMMITTED record; raises typed on refusal or
        store fault - the caller may acknowledge only on return."""
        intent = make_write_intent(
            proposition, clause, tense, polarity, modality,
            self.speaker_id, self.session_id, turn_id, self.tick,
            provenance, supersedes)
        return self.coordinator.commit(intent)

    def apply_lifecycle(self, assertion_id: str, new_status: str,
                        reason: str, turn_id: str) -> Dict:
        return self.coordinator.commit(make_lifecycle_intent(
            assertion_id, new_status, reason, turn_id))

    # ---------------------------------------------- sound entailment
    def support_for(self, query: Dict,
                    query_tense=None) -> Optional[Dict]:
        """Does the session store SOUNDLY settle this proposition?
        -> {"verdict": "yes"/"no", "record": ...} from ACTIVE records,
        {"verdict": "contested", "records": [...]} when only
        conflicting/contested records touch it, else None. Sound rules
        only: equality, negation, conjunction membership. Disjunction,
        quantification, and prohibition support NOTHING singular -
        symmetry is never inferred."""
        for record in self.store.active():
            verdict = self._entails(record["proposition"], query,
                                    record.get("tense"), query_tense)
            if verdict is not None:
                return {"verdict": verdict, "record": record}
        touching = [r for r in self.store.contested()
                    if self._entails(r["proposition"], query,
                                     r.get("tense"), query_tense)
                    is not None
                    or self._conflicts(r["proposition"], query,
                                       r.get("tense"), query_tense)]
        if touching:
            return {"verdict": "contested", "records": touching}
        return None

    @staticmethod
    def _entails(stored: Dict, query: Dict, stored_tense,
                 query_tense) -> Optional[str]:
        if not _tense_compatible(query_tense, stored_tense):
            return None
        if stored == query:
            return "yes"
        if stored.get("pred") == "negation" \
                and stored.get("args") \
                and stored["args"][0] == query:
            return "no"
        if query.get("pred") == "negation" and query.get("args") \
                and stored == query["args"][0]:
            return "no"
        if stored.get("pred") == "conjunction":
            for part in stored.get("args", []):
                inner = DialogueBoard._entails(part, query, None,
                                               None)
                if inner is not None:
                    return inner
        return None

    # ---------------------------------------------- conflict detection
    @staticmethod
    def _conflicts(a: Dict, b: Dict, tense_a=None,
                   tense_b=None) -> bool:
        """Polarity conflict (X vs negation(X)) or exclusive-attribute
        conflict (property(e, gray) vs property(e, brown)). TENSE
        MATTERS: 'the cat chased the dog' (past) does NOT conflict
        with 'the cat does not chase the dog' (present) - a false
        conflict was caught live by the runtime canary. Top-level
        propositions only in v0.1 (conjunction-internal conflicts are
        an open item, disclosed)."""
        if not _tense_compatible(tense_a, tense_b):
            return False
        if a.get("pred") == "negation" and a.get("args") \
                and a["args"][0] == b:
            return True
        if b.get("pred") == "negation" and b.get("args") \
                and b["args"][0] == a:
            return True
        if a.get("pred") == "property" and b.get("pred") == "property":
            ea, va = (a.get("args") or [None, None])[:2]
            eb, vb = (b.get("args") or [None, None])[:2]
            if ea == eb and va != vb:
                cls_a, cls_b = _attribute_class(va), _attribute_class(vb)
                if cls_a is not None and cls_a == cls_b:
                    return True
        return False

    def conflicting_active(self, proposition: Dict,
                           tense=None) -> List[Dict]:
        return [r for r in self.store.active()
                if self._conflicts(r["proposition"], proposition,
                                   r.get("tense"), tense)]

    # ---------------------------------------------- wh unification
    def wh_bindings(self, template: Dict) -> List[Tuple[str, Dict]]:
        """Match a proposition template containing the marker 'wh'
        against ACTIVE assertions (conjunction conjuncts included).
        Returns (binding, record) pairs in commitment order."""
        results: List[Tuple[str, Dict]] = []

        def match(packet: Dict, record: Dict) -> None:
            if packet.get("pred") == "conjunction":
                for part in packet.get("args", []):
                    if isinstance(part, dict):
                        match(part, record)
                return
            if packet.get("pred") != template.get("pred"):
                return
            args_p = packet.get("args", [])
            args_t = template.get("args", [])
            if len(args_p) != len(args_t):
                return
            binding = None
            for actual, wanted in zip(args_p, args_t):
                if wanted == "wh":
                    binding = actual
                elif actual != wanted:
                    return
            if binding is not None \
                    and (binding, record) not in results:
                results.append((binding, record))

        for record in self.store.active():
            match(record["proposition"], record)
        return results

    # ---------------------------------------------- entity summary
    def about(self, entity: str) -> List[Dict]:
        return [r for r in self.store.active()
                if entity in self._atoms(r["proposition"])]

    @staticmethod
    def _atoms(packet) -> List[str]:
        atoms: List[str] = []
        if isinstance(packet, dict):
            for arg in packet.get("args", []):
                if isinstance(arg, str):
                    atoms.append(arg)
                else:
                    atoms.extend(DialogueBoard._atoms(arg))
        return atoms

    # ---------------------------------------------- clause rendering
    @staticmethod
    def packet_to_clause(packet: Dict, tense=None) -> str:
        """Naive regular English for a semantic packet (the REALIZE
        subboard owns proper rendering later)."""
        pred = packet.get("pred")
        args = packet.get("args", [])
        if pred == "property" and len(args) >= 2:
            return f"the {args[0]} is {args[1]}"
        if pred == "relation" and len(args) >= 3:
            suffix = "d" if tense == "past" else "s"
            clause = (f"the {args[1]} {args[0]}{suffix} the "
                      f"{args[2]}")
            if len(args) >= 4:
                clause += f" to the {args[3]}"
            return clause
        if pred == "negation" and args:
            inner = args[0]
            if inner.get("pred") == "relation" \
                    and len(inner.get("args", [])) >= 3:
                a = inner["args"]
                marker = "did not" if tense == "past" else "does not"
                clause = f"the {a[1]} {marker} {a[0]} the {a[2]}"
                if len(a) >= 4:
                    clause += f" to the {a[3]}"
                return clause
            if inner.get("pred") == "property" \
                    and len(inner.get("args", [])) >= 2:
                a = inner["args"]
                return f"the {a[0]} is not {a[1]}"
            return ("it is not the case that "
                    + DialogueBoard.packet_to_clause(inner, tense))
        if pred == "prohibition" and args:
            inner = args[0]
            if inner.get("pred") == "relation" \
                    and len(inner.get("args", [])) >= 3:
                a = inner["args"]
                return f"the {a[1]} must not {a[0]} the {a[2]}"
        if pred == "quantified" and len(args) == 2:
            inner = DialogueBoard.packet_to_clause(args[1], tense)
            if inner.startswith("the "):
                inner = inner[4:]
            return f"{args[0]} {inner}"
        if pred in ("conjunction", "disjunction"):
            joiner = " and " if pred == "conjunction" else " or "
            return joiner.join(
                DialogueBoard.packet_to_clause(part, tense)
                for part in args if isinstance(part, dict))
        if pred == "number" and len(args) >= 2:
            return f"the {args[0]} number is {args[1]}"
        if pred == "time" and args:
            return f"at {args[0]}"
        if pred == "location" and len(args) >= 2:
            return f"the {args[0]} is on the {args[1]}"
        if pred == "possession" and len(args) >= 2:
            return f"the {args[0]} has the {args[1]}"
        return json_clause(packet)


def json_clause(packet: Dict) -> str:
    import json as _json
    return _json.dumps(packet, sort_keys=True)
