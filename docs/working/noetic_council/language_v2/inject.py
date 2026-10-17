"""inject.py -- INJECT: bring CCE English into a station.

TAP_AND_INJECT.md section 2, in the owner's words: "asking someone to think about something".
An utterance arrives at a station boundary and:

  1. is parsed, or refused with a typed code (NOT_CCE, AMBIGUOUS, SLOT_TYPE, SAME_IDEA_TRIGGER,
     UNDECLARED_NAME, HEDGE, VAGUE_QUANTITY, NEST_TOO_DEEP, OPERATOR_DISCIPLINE, or an exactness
     code from numbers.py);
  2. passes the English-first receipt: parse(render(C)) == C. Wording may change; content may not;
  3. carries evidence USER_SAID with its turn index -- the spec blocks a user request from
     becoming a system instruction;
  4. routes to a station and a faculty by the routing table below;
  5. starts a STATE CHANGE at that station (a HELD candidate, a question record, a head record,
     a witness). It never writes a value.

A refused or unparsed utterance writes NOTHING and produces a CLARIFY asking for a CCE
restatement, with one rendered example. A parse that fails the English-first receipt also writes
nothing: never a write without a receipt.
"""

from __future__ import annotations

import cce_parse
import cce_render
import roundtrip as RT
from content import CASContent, N, Refusal, State, Term
from tap import STATION_NAMES, Station

# Undetermined / refusal words are structural, never aversion (MAP.md F14, TAP_AND_INJECT 2.4).
FACULTIES = ("fit", "asking", "integration", "wondering", "refusal", "self_notice", "curiosity")

# What an accepted utterance may change at a station. A kind of record, never a value.
WRITE_KINDS = ("HEAD_RECORD", "HELD_CANDIDATE", "QUESTION_RECORD", "WITNESS", "STOCK_WITNESS",
               "GATE_RECORD")

EXAMPLE = 'Ana is a Mind. Ana is attracted toward "the offer".'

# TRANSLATOR_SPEC.md section 6, the gate table: what a turn may be, and what it must never do.
GATE_ROWS = (
    ("ANSWER", "the sentence parses and every slot the turn needs is filled with evidence",
     ("task_active", "claim_supported"), "an answer with an empty slot"),
    ("CLARIFY", "the sentence parses and a named slot is empty",
     ("lacunarity_detected", "unfilled_slot_present"), "filling the slot"),
    ("CLARIFY", "the sentence does not parse (NOT_CCE, AMBIGUOUS, HEDGE, VAGUE_QUANTITY)",
     ("restatement_requested",), "guessing a parse"),
    ("REFUSE_CLAIM", "a claim is asked for and there is no evidence path",
     ("evidence_gap",), "an invented fact"),
    ("ANSWER", "nothing to ask and nothing to answer", ("KNOWLEDGE_MISSING",),
     "a dressed-up answer"),
)


def gate(utterance: str, claim_asked: bool = False, evidence_path: bool = False,
         minds=("I", "you")) -> dict:
    """The gate table of TRANSLATOR_SPEC.md section 6, as a decision, not as prose.

    Returns {"situation", "turn", "facts", "sentence", "never"} plus the typed code when the
    sentence did not parse. UNDETERMINED is always the fixed sentence.
    """
    report = cce_parse.parse_report(utterance, minds=minds)
    if report["content"] is None:
        return {"situation": "did_not_parse", "turn": "CLARIFY",
                "facts": ("restatement_requested",), "code": report["code"],
                "sentence": None, "example": EXAMPLE,
                "never": "guessing a parse"}
    content = report["content"]
    if content.gate == "UNDETERMINED":
        return {"situation": "nothing_to_say", "turn": "ANSWER", "facts": ("KNOWLEDGE_MISSING",),
                "code": None, "sentence": cce_render.FIXED_UNDETERMINED,
                "never": "a dressed-up answer"}
    if content.turn == "CLARIFY":
        return {"situation": "named_slot_empty", "turn": "CLARIFY",
                "facts": ("lacunarity_detected", "unfilled_slot_present"), "code": None,
                "sentence": cce_render.render(content), "never": "filling the slot"}
    if claim_asked and not evidence_path:
        return {"situation": "no_evidence_path", "turn": "REFUSE_CLAIM", "facts": ("evidence_gap",),
                "code": None, "sentence": cce_render.FIXED_UNDETERMINED, "never": "an invented fact"}
    return {"situation": "supported", "turn": content.turn, "facts": ("task_active", "claim_supported"),
            "code": None, "sentence": cce_render.render(content), "never": "an answer with an empty slot"}


class InjectRecord:
    __slots__ = ("utterance", "status", "code", "detail", "content", "station", "faculty", "write",
                 "receipt", "evidence", "turn_index", "example", "wrote_value")

    def __init__(self, utterance, status, code=None, detail="", content=None, station=None,
                 faculty=None, write=None, receipt=None, evidence="USER_SAID", turn_index=0,
                 example=None, wrote_value=False):
        self.utterance = utterance
        self.status = status
        self.code = code
        self.detail = detail
        self.content = content
        self.station = station
        self.faculty = faculty
        self.write = write
        self.receipt = receipt
        self.evidence = evidence
        self.turn_index = turn_index
        self.example = example
        self.wrote_value = wrote_value

    def record(self) -> dict:
        return {
            "utterance": self.utterance,
            "status": self.status,
            "code": self.code,
            "detail": self.detail,
            "station": self.station,
            "faculty": self.faculty,
            "write": self.write,
            "wrote_value": self.wrote_value,
            "evidence": self.evidence,
            "turn_index": self.turn_index,
            "content_hash": None if self.content is None else self.content.digest(),
            "receipt": None if self.receipt is None else self.receipt.to_dict(),
        }

    def __repr__(self) -> str:
        return "InjectRecord(%s, %s -> %s)" % (self.status, self.utterance[:40], self.station)


def route(content: CASContent) -> dict:
    """The routing table of TAP_AND_INJECT.md section 2.2, as CCE can express it today.

    # UNDECIDED IN SPEC: which station a plain frame claim starts, since the design file only PROPOSES it?
    # This build sends a frame claim to S5 as a witness, a recipe to S2 as a held candidate, a stock
    # statement to S1, a fact or an edge to S5, a gate word to S3, a question (CLARIFY) to S5 as a
    # question record, and a bare topic to S0 as a head record.
    # UNDECIDED IN SPEC: is the turn index that tags USER_SAID evidence part of the content record or provenance outside it?
    # This build keeps it outside: the record holds the word USER_SAID, the index stays in the
    # InjectRecord.
    """
    kinds = {relation[0] for relation in content.relations}
    if content.turn == "CLARIFY":
        return {"station": "S5", "faculty": "asking", "write": "QUESTION_RECORD"}
    if content.gate == "UNDETERMINED":
        return {"station": "S3", "faculty": "refusal", "write": "GATE_RECORD"}
    if content.recipe is not None or content.fractal:
        return {"station": "S2", "faculty": "fit", "write": "HELD_CANDIDATE"}
    if "stock" in kinds:
        return {"station": "S1", "faculty": "integration", "write": "STOCK_WITNESS"}
    if kinds:
        return {"station": "S5", "faculty": "integration", "write": "WITNESS"}
    if content.omega and not content.terms:
        return {"station": "S0", "faculty": "fit", "write": "HEAD_RECORD"}
    if content.terms:
        return {"station": "S5", "faculty": "integration", "write": "WITNESS"}
    return {"station": "S5", "faculty": "integration", "write": "QUESTION_RECORD"}


def inject(utterance: str, station: Station = None, turn_index: int = 0, minds=("I", "you")) -> InjectRecord:
    """Parse an utterance and start a state change at a station, or refuse and write nothing."""
    report = cce_parse.parse_report(utterance, minds=minds)
    if report["content"] is None:
        # The spec's gate table: CLARIFY asking for a CCE restatement, with one rendered example.
        return InjectRecord(utterance, "REFUSED", code=report["code"], detail=report["detail"],
                            station=None if station is None else station.name, faculty=None,
                            write=None, example=EXAMPLE, turn_index=turn_index)
    content = report["content"]
    receipt = RT.english_first(utterance, minds=minds)
    if not receipt.ok:
        return InjectRecord(utterance, "REFUSED", code=(receipt.rejection_codes or ("UNSAYABLE",))[0],
                            detail="the English-first receipt failed; nothing is written",
                            content=content, station=None if station is None else station.name,
                            receipt=receipt, turn_index=turn_index)
    placement = route(content)
    if station is not None and station.name != placement["station"]:
        # An utterance may be delivered to the station the sender names; the routing table is what
        # says which faculty starts there. The arrival station is recorded, never overwritten.
        placement = dict(placement)
        placement["delivered_to"] = station.name
    spoken_evidence = CASContent(turn=content.turn, omega=content.omega, terms=content.terms,
                                 recipe=content.recipe, relations=content.relations,
                                 evidence="NONE" if content.gate == "UNDETERMINED" else "USER_SAID",
                                 gate=content.gate, lacunae=content.lacunae, reason=content.reason,
                                 fractal=content.fractal)
    return InjectRecord(utterance, "ACCEPTED", content=spoken_evidence,
                        station=placement["station"], faculty=placement["faculty"],
                        write={"kind": placement["write"], "station": placement["station"],
                               "value_written": False,
                               "note": "a state change (a record), never a value"},
                        receipt=receipt, evidence="USER_SAID", turn_index=turn_index)


def deliver(utterance: str, station: Station, turn_index: int = 0, minds=("I", "you")) -> dict:
    """Bring the utterance INTO the station: the content now exists there.

    Returns {"record": InjectRecord, "station": Station}. On a refusal the station is returned
    exactly as it was: nothing entered.
    """
    record = inject(utterance, station, turn_index, minds)
    if record.status != "ACCEPTED":
        return {"record": record, "station": station, "entered": False}
    content = record.content
    arrived = Station(station.name, CASContent(
        turn=content.turn, omega=content.omega, terms=content.terms, recipe=content.recipe,
        relations=content.relations, evidence="NONE", gate=content.gate,
        lacunae=content.lacunae, reason=content.reason, fractal=content.fractal),
        unspeakable=station.unspeakable, faculty=record.faculty)
    return {"record": record, "station": arrived, "entered": True}


def check_routing_table() -> dict:
    """Every route names a real station and a real faculty, and every write is a record kind."""
    rows = []
    samples = [
        CASContent(turn="CLARIFY", omega="Ω_x", lacunae=("the stock of Ω_leaves",)),
        CASContent(gate="UNDETERMINED"),
        CASContent(terms=(Term(2, slots={"M": "I", "I": '"x"'}),)),
        CASContent(omega="Ω_x"),
        CASContent(relations=(("leads_to", '"a"', '"b"'),)),
        CASContent(relations=(("stock", "2", "Ω_x"),)),
        CASContent(turn="ACK", omega="Ω_y"),
    ]
    for content in samples:
        placement = route(content)
        good = (placement["station"] in STATION_NAMES and placement["faculty"] in FACULTIES
                and placement["write"] in WRITE_KINDS)
        rows.append({"content_hash": content.digest()[:12], "placement": placement, "ok": good})
    return {"ok": all(row["ok"] for row in rows), "rows": rows}
