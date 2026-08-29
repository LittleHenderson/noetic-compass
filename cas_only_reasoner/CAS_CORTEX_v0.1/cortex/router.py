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
        self.gram_parser = ConstructionParser(
            Lexicon(self.seed["lexicon"]), morph)
        self.coverage = {"native_l1": 0, "native_gram": 0,
                         "cortex": 0, "refused": 0}

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
            packet = self._frame_to_packet(gram["core"])
            trace["commitment"] = {"by": "cas_learned_grammar",
                                   "construction": gram["frames"][0]
                                   ["surface"]["construction_id"]}
            trace["answer"] = {"status": "UNDERSTOOD",
                               "meaning": packet,
                               "frame_core": gram["core"]}
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
        if core.get("frame") == "event":
            inner = {"pred": "relation",
                     "args": [core["predicate"], core["agent"],
                              core["patient"]]}
        else:
            inner = {"pred": "property",
                     "args": [core.get("entity"), core.get("property")]}
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
        elif pred == "relation" and len(args) == 3:
            entities.extend(args[1:])
        elif pred in ("negation", "question") and args:
            entities.extend(HybridRouter._entity_atoms(args[0]))
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
        """Commitment stays with CAS: questions go through the kernel;
        statements are acknowledged as parsed content (no durable
        write in v0.1)."""
        if meaning.get("pred") == "question":
            kernel = self._kernel_answer(meaning)
            trace["commitment"] = {"by": "cas_kernel",
                                   "kernel_status": kernel["kernel_status"]}
            trace["answer"] = {"status": "ANSWERED",
                               "text": kernel["answer"]}
        else:
            trace["commitment"] = {"by": "cas_parse_acknowledgement"}
            trace["answer"] = {"status": "UNDERSTOOD",
                               "meaning": meaning}
        return True

    def _seal(self, trace: Dict, committed: bool) -> Dict:
        trace["committed"] = committed
        # the native CAS-Ohm attention record: COMPUTE-ONLY decoration,
        # authored AFTER the answer is decided; nothing above reads it
        from .attention import stage_record
        trace["cas_ohm"] = stage_record(trace)
        trace["trace_digest"] = _digest(trace)
        self.traces.append(trace)
        return trace
