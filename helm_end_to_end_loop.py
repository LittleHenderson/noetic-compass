"""helm_end_to_end_loop.py -- HELM's live loop, wired to the ONE canonical brain (fix C, 2026-10-18).

THE CIRCUIT (one user turn)
---------------------------
    user text
      -> CCE skin      language_v3/cce.py: parse, then the round trip parse(render(C)) == C.
                       Parse fails or the round trip differs -> typed CLARIFY, ZERO writes.
                       No checker loaded -> NOT_VERIFIED, refuse. (The old shim that said "verified" when the
                       checker was missing is gone.)
      -> S0 atlas head the topic is looked up in the canonical brain's address map (helm_brain_canonical.py)
      -> S1 trigger ^8 the product brings its own prerequisite list to mind (the brain's recipe support)
      -> S2 Bias ^5    the stock on hand (this session's verified stock, with a version and digest)
      -> S3 arrival ^9 what is present, what is ABSENT, which requirements are still unlearned
      -> S4 operating point   the valve (a written rule, ENGINEERED-NOT-VALIDATED; G-ABSENT kept)
      -> S5 RPM link   the_loop_v3 rpm_gate with a real GateRequest (no label field). On REPAIR,
                       repair_performer/actor.perform_repair opens the child goal, runs it, glues the child's
                       ACTUAL result back, and asks the parent's own gate again.
      -> brain         only after PROCEED: the canonical brain answers, with its eta/epsilon read-back
      -> store         cube store write ONLY after the gate passed and the read-back receipt passed;
                       the written cube is then read back from the store and compared.
      -> S6 next       what the turn waits for (nothing, or the user's answer to a CLARIFY)

A missing ingredient is ABSENT. It goes to the RPM gate and the turn ends UNDETERMINED with a CLARIFY question
unless a repair child finds the real amount. No quantity is ever invented (the old fill-with-ten shortcut is gone).

TEACHING
--------
`witness_batch(...)` is the teaching channel: one batch the user actually made (stock before, amount made,
which ingredient ran out first). It passes the CCE form receipt, the gate, and the brain's OWN writer
(candidate, eta/epsilon receipt, memory check). When the brain's writer refuses -- for example because the new
batch contradicts a requirement it already holds -- that refusal IS the detected failure: it is turned into an
RpmCause, the gate answers REPAIR, and the repair performer opens a real child (a replay of every witnessed
batch on a fresh brain). Nothing in this path is a planted flag.

EVERYDAY ENGLISH IN (fix H, 2026-10-18)
---------------------------------------
Text that is not in the checked form first goes to `helm_english_in.read` (a deterministic reader). If the reader
restates it as checked-form content, that content is rendered to a checked-form sentence, parsed back, and the turn
continues EXACTLY as a checked-form turn (same CCE round trip, gate, brain, store, receipts). A witnessed-batch
report goes to `witness_batch`. A reader question ("how much flour?", "I don't know an ingredient called X")
ends the turn as CLARIFY_ENGLISH_<code> with zero writes. Text the reader does not claim takes the old paths below.

OUTSIDE THE CIRCUIT (unchanged, stated so nobody assumes otherwise): the agentic-goal path (helm_agentic_executor)
and read-only cube-store queries in free English. Both write nothing through this loop's recipe path.

Station names S0..S6 follow the LM-T6 circuit names given in the owner's fix-C order. "CCE skin", "brain" and
"store" are not LM-T6 stations; they are labeled as what they are.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sys
from decimal import Decimal
from fractions import Fraction
from typing import Any, Callable, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
COUNCIL = os.path.join(HERE, "docs", "working", "noetic_council")
for sub in [
    HERE,
    os.path.join(COUNCIL, "language_v3"),
    os.path.join(COUNCIL, "cube_store"),
    os.path.join(COUNCIL, "repair_performer"),
]:
    if os.path.exists(sub) and sub not in sys.path:
        sys.path.insert(0, sub)

from helm_brain_canonical import (CanonicalRecipeBrain, CanonicalBrainRefused, exact_amount, frac_text,
                                  EVALUATED)
from tks_meta_valve_controller import TKSMetaValveController
from helm_agentic_executor import AgenticExecutionEngine
import helm_english_in

#: Rule 6 (STOCK_FRAME_REQUIRED, 2026-10-19): what HELM says when a sentence names an ingredient but states no stock.
NOTHING_TO_SAVE_LINE = "I don't have anything to save from that. Nothing was saved."
from helm_voice import reader_question_text

# Canonical CCE translator (language_v3). Missing -> every turn is NOT_VERIFIED and refused.
try:
    import cce
except ImportError:
    cce = None

# The real gate, the real GateRequest and the real repair performer (repair_performer/actor.py loads them).
import actor as repair_actor          # noqa: E402
RPM = repair_actor.G                  # the_loop_v3/rpm_gate.py
GateRequest = repair_actor.L.GateRequest

# Unified cube store
try:
    from store import CubeStore
    from cube import CubeNode, Core, Face, Branch, Provenance
    from turn import TurnProcessor, INVENTORY_NODE_ID
except ImportError:
    CubeStore = None
    TurnProcessor = None
    INVENTORY_NODE_ID = "cube_inventory_on_hand"

#: The fix-C trace (HELM_LIVE_TRACE_20261018.jsonl) is kept as it was; fix H writes its own file beside it.
FIX_C_TRACE_PATH = os.path.join(HERE, "docs", "working", "traces", "HELM_LIVE_TRACE_20261018.jsonl")
DEFAULT_TRACE_PATH = os.path.join(HERE, "docs", "working", "traces", "HELM_LIVE_TRACE_ENGLISH_IN_20261018.jsonl")


# -----------------------------------------------------------------------------
# 1. Everyday English voice (what a person reads). No CAS words, no invented numbers.
# -----------------------------------------------------------------------------
def _amount_words(text: Optional[str]) -> str:
    if text is None:
        return "?"
    v = Fraction(text)
    if v.denominator == 1:
        return str(v.numerator)
    as_dec = Decimal(v.numerator) / Decimal(v.denominator)
    if Fraction(str(as_dec)) == v:
        return str(as_dec.normalize())
    return f"{v.numerator}/{v.denominator}"


class HELMVoiceAdapter:
    @staticmethod
    def format_success(product: str, yield_text: str, limiting: str, receipt_hash: Optional[str] = None) -> str:
        tail = f" [receipt: {receipt_hash}]" if receipt_hash else ""
        return (f"Good news: with what's on hand we can make {_amount_words(yield_text)} {product}. "
                f"{limiting} runs out first, so it sets the limit.{tail}")

    @staticmethod
    def format_missing(product: str, missing: List[str], saved: bool = False,
                       said_gone: Optional[List[str]] = None) -> str:
        names = " and ".join(missing)
        tail = "I didn't guess." if saved else "I didn't guess, and nothing was saved."
        if said_gone and set(missing) <= set(said_gone):     # the user told us it is gone: say that, not "unknown"
            return (f"I can't make {product} right now: there's no {names} on hand. When there is, tell me how much. "
                    f"{tail}")
        ask = f"How much {missing[0]} is there?" if len(missing) == 1 else f"How much {names} is there?"
        return (f"I can't say how much {product} we can make yet, because I don't know how much {names} we have. "
                f"{ask} {tail}")

    @staticmethod
    def format_unlearned(product: str, unlearned: List[str], saved: bool = False) -> str:
        names = " or ".join(unlearned)
        tail = "I didn't guess." if saved else "I didn't guess, and nothing was saved."
        return (f"I don't know yet how much {names} goes into {product}: I haven't seen a batch where that ran "
                f"out first. Tell me about one batch like that. {tail}")

    @staticmethod
    def format_clarify_not_checked() -> str:
        return ("I can't check that one yet. Right now I can only work with stock and recipe requests written in "
                "the checked form, for example \"There is 12 of Ω_Flour.\" or \"Topic: Ω_Bread.\" "
                "Nothing was saved.")

    @staticmethod
    def format_round_trip_failed() -> str:
        return ("I couldn't read that back exactly the way you wrote it, so I didn't act on it. "
                "Nothing was saved. Could you say it again?")

    @staticmethod
    def format_not_verified() -> str:
        return "My checker for written statements isn't loaded, so I won't act on anything. Nothing was saved."

    @staticmethod
    def format_clarify(missing_slot: str = "information") -> str:
        return ("I can't answer that question because it doesn't match any verified facts or recipes I have. "
                "What materials or goals would you like to work with?")

    @staticmethod
    def format_stock_recorded(stocks: Dict[str, str], words: Optional[Dict[str, str]] = None) -> str:
        words = words or {}
        items = ", ".join(words.get(k) or f"{_amount_words(v)} {k}" for k, v in stocks.items())
        return f"Got it: {items} on hand."

    @staticmethod
    def format_absent_recorded(names: List[str]) -> str:
        return f"Noted: no {' or '.join(n.lower() for n in names)} on hand."

    @staticmethod
    def format_conflict(product: str, ingredient: str, old: str, new: str) -> str:
        return (f"Two batches disagree about how much {ingredient} goes into one {product}: an earlier batch says "
                f"{_amount_words(old)}, this one says {_amount_words(new)}. I didn't change anything. "
                f"Which batch is right?")

    @staticmethod
    def format_teach_refused(product: str, reason: str) -> str:
        return (f"I couldn't learn from that {product} batch ({reason.replace('_', ' ').lower()}). "
                f"I didn't change anything.")

    @staticmethod
    def format_learned(product: str, ingredient: str, value: str) -> str:
        return f"Learned: one {product} needs {_amount_words(value)} {ingredient}."

    @staticmethod
    def format_brain_undetermined(product: str, gate: Optional[str]) -> str:
        why = {"G1": "I'm missing part of its recipe", "G2": "there's no usable stock",
               "G3": "two ingredients tie for running out first", "G4": "its recipe is marked unreliable",
               "G5": "two recipes overlap"}.get(gate or "", "the brain couldn't settle it")
        return f"I can't give a sure answer for {product} with this stock: {why}. I didn't guess."

    @staticmethod
    def format_stated_recipe() -> str:
        return ("I can't take a recipe as stated. I learn how much each ingredient needs from batches you actually "
                "made: what you started with, how much you made, and what ran out first. Nothing was saved.")


# -----------------------------------------------------------------------------
# 2. The loop
# -----------------------------------------------------------------------------
def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _h16(obj: Any) -> str:
    return hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()[:16]


def _strip_omega(name: str) -> str:
    return name[2:] if name.startswith("Ω_") else name


class HELMEndToEndLoop:
    """One running loop. `brain` and `cube_store` may be shared between loops (a later session on the same store)."""

    def __init__(self, cube_store: Optional[Any] = None, brain: Optional[CanonicalRecipeBrain] = None,
                 default_aperture: Any = "0.75", trace_path: Optional[str] = None,
                 brain_dir: Optional[str] = None, **_ignored: Any):
        # Station S0's brain: the canonical recipe brain. The 22x40 cookie brain is never constructed here.
        self.brain = brain if brain is not None else CanonicalRecipeBrain(brain_dir=brain_dir)
        self.valve = TKSMetaValveController(default_aperture=Decimal(str(default_aperture)))
        self.agentic_engine = AgenticExecutionEngine(workspace_root=HERE)
        if cube_store is not None:
            self.cube_store = cube_store
        elif CubeStore is not None:
            self.cube_store = CubeStore(context_id="helm_e2e_unified")
        else:
            self.cube_store = None
        self.turn_processor = TurnProcessor(self.cube_store) if (self.cube_store and TurnProcessor) else None
        self.stock: Dict[str, Fraction] = {}       # S2 Bias ^5: this session's verified stock
        self.bias_version = 1
        self.trace: List[Dict[str, Any]] = []
        self.trace_path = trace_path
        self.ignored_constructor_args = sorted(_ignored)   # e.g. old valve_weights_path: never loaded
        # fix H: what the English reader needs from the conversation, all of it the user's own words
        self.declared_absent: set = set()               # ingredients the user said are gone (never re-glued)
        self.units: Dict[str, str] = {}                 # unit words the user gave per ingredient ("cups")
        self.last_topic: Optional[str] = None           # the product the conversation is on ("bake a batch")
        self._pending_words: Dict[str, Dict[str, str]] = {}

    # ------------------------------------------------------------------ trace
    def _emit(self, tick: int, station: str, **fields: Any) -> Dict[str, Any]:
        rec = {"tick": tick, "station": station}
        rec.update(fields)
        rec = json.loads(_canon(rec))
        self.trace.append(rec)
        if self.trace_path:
            os.makedirs(os.path.dirname(os.path.abspath(self.trace_path)), exist_ok=True)
            with open(self.trace_path, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(_canon(rec) + "\n")
        return rec

    def _store_writes(self) -> int:
        return len(self.cube_store.write_history) if self.cube_store is not None else 0

    def _bias_digest(self) -> str:
        return hashlib.sha256(_canon({"stock": {k: frac_text(v) for k, v in sorted(self.stock.items())},
                                      "brain": self.brain.brain.learned_digest(),
                                      "version": self.bias_version}).encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------ English helper (kept for helm_chat)
    def extract_ingredient_quantities(self, text: str) -> Dict[str, Decimal]:
        """Explicit amounts only ('10 Flour', 'Flour: 10'). A mention WITHOUT an amount is NOT filled in."""
        inputs: Dict[str, Decimal] = {}
        for ing in self.brain.ingredients:
            if re.search(rf"\b(?:without|no|zero)\s+(?:units?\s+of\s+)?{ing}\b", text, re.IGNORECASE):
                continue
            m = re.search(rf"(\d+(?:\.\d+)?)\s*(?:units? of\s*)?{ing}\b|\b{ing}[:\s]+(\d+(?:\.\d+)?)", text,
                          re.IGNORECASE)
            if m:
                inputs[ing] = Decimal(m.group(1) or m.group(2))
        return inputs

    # ------------------------------------------------------------------ CCE skin
    def verify_cce_round_trip(self, content_or_text: Any) -> Dict[str, Any]:
        """Parse (when given text), then check parse(render(C)) == C exactly. Missing checker = NOT_VERIFIED."""
        if cce is None:
            return {"verified": False, "rejection": "NOT_VERIFIED_NO_CHECKER", "receipt_id": None, "content": None}
        content = content_or_text
        if isinstance(content_or_text, str):
            try:
                content = cce.parse(content_or_text)
            except cce.Refusal as exc:
                return {"verified": False, "rejection": f"CCE_PARSE_REFUSED:{exc.code}", "content": None,
                        "receipt_id": hashlib.sha256(content_or_text.encode("utf-8")).hexdigest()[:16]}
            except Exception as exc:     # a crash in the parser is a refusal, never a pass
                return {"verified": False, "rejection": f"CCE_PARSE_EXCEPTION:{type(exc).__name__}",
                        "content": None,
                        "receipt_id": hashlib.sha256(content_or_text.encode("utf-8")).hexdigest()[:16]}
        if not isinstance(content, dict):
            return {"verified": False, "rejection": "UNSUPPORTED_TYPE", "receipt_id": None, "content": None}
        rt = cce.round_trip(content)
        explicit_equal = False
        if rt.get("ok"):
            try:
                back = cce.parse(cce.render(content))
                explicit_equal = cce.normalize(back) == cce.normalize(content)
            except Exception:
                explicit_equal = False
        verified = bool(rt.get("ok")) and explicit_equal
        return {"verified": verified, "content_hash_in": rt.get("content_hash_in"),
                "content_hash_out": rt.get("content_hash_out"), "sentence": rt.get("sentence"),
                "receipt_id": rt.get("receipt_id"), "parse_render_parse_equal": explicit_equal,
                "rejection": rt.get("rejection") if not verified else None, "content": content}

    # ------------------------------------------------------------------ gate
    def _gate_request(self, tick: int, proposal: str, prerequisites: List[str], unsatisfied: List[str],
                      state_label: str) -> Any:
        cause = RPM.RpmCause(blocked_node="P" if unsatisfied else None, depth=0,
                             unsatisfied=tuple(unsatisfied), state_label=state_label)
        return GateRequest(turn=tick, coordinator="helm-live-loop", bias_version=self.bias_version,
                           bias_digest=self._bias_digest(), proposal_text=proposal,
                           prerequisites=tuple(prerequisites), cause=cause)

    def _run_gate_with_repair(self, tick: int, request: Any,
                              open_child: Callable[..., Dict[str, Any]]) -> Tuple[Any, List[Dict[str, Any]], str]:
        """Ask the gate. On REPAIR hand the request to the real repair performer, once per named gap, until the
        parent's own gate passes or a child cannot realize its gap. Returns (final verdict, ledger, outcome)."""
        verdict = RPM.rpm_gate(request)
        self._emit(tick, "S5 RPM link", what="gate", request=request.as_dict(), verdict=verdict.as_dict())
        if verdict.verdict != RPM.REPAIR:
            return verdict, [], "NO_REPAIR_NEEDED" if verdict.verdict == RPM.PROCEED else "REFUSED"
        ledger: List[Dict[str, Any]] = []
        current = request
        for _ in range(len(request.cause.unsatisfied)):
            out = repair_actor.perform_repair(current, open_child, ledger)
            self._emit(tick, "S5 RPM link", what="repair_performer", outcome=out["outcome"],
                       child_run=out.get("child_run"), ledger=ledger[-6:],
                       after=out["after"].as_dict() if out.get("after") is not None else None)
            if out["outcome"] == repair_actor.REPAIRED:
                return out["after"], ledger, repair_actor.REPAIRED
            after = out.get("after")
            if after is None or after.verdict != RPM.REPAIR:
                return (after or out["parent_verdict"]), ledger, out["outcome"]
            gap = out["parent_verdict"].gap
            remaining = tuple(u for u in current.cause.unsatisfied if u != gap)
            current = GateRequest(turn=current.turn, coordinator=current.coordinator,
                                  bias_version=current.bias_version + 1, bias_digest=current.bias_digest,
                                  proposal_text=current.proposal_text, prerequisites=current.prerequisites,
                                  cause=RPM.RpmCause(blocked_node=None, depth=0, unsatisfied=remaining,
                                                     state_label=current.cause.state_label))
        return RPM.rpm_gate(current), ledger, repair_actor.NOT_REPAIRED

    # ------------------------------------------------------------------ store
    def _face(self, text: str, populated: bool) -> Any:
        return Face(availability="populated" if populated else "unknown", human_text=text)

    def _write_stock_cubes(self, stocks: Dict[str, Fraction], tick: int) -> Dict[str, Any]:
        if self.cube_store is None or CubeStore is None:
            return {"written": [], "read_back_ok": False, "note": "NO_STORE"}
        written = []
        inv = self.cube_store.nodes.get(INVENTORY_NODE_ID)
        names = sorted(set(([] if inv is None else inv.faces["face_5"].structured.get("items", []))) | set(stocks))
        inv_faces = {f"face_{i}": Face(availability="populated", human_text="Verified stock on hand.",
                                       structured={"items": names} if i == 5 else {}) for i in range(1, 7)}
        node = CubeNode(node_id=INVENTORY_NODE_ID,
                        core=Core(label="Current Inventory", kind="instance",
                                  identity_statement="Verified session inventory (CCE round trip + RPM gate)."),
                        faces=inv_faces, revision=(inv.revision + 1) if inv else 1, turn_index=tick,
                        provenance=Provenance(source="USER_SAID"))
        self.cube_store.write_cube(node)
        written.append(INVENTORY_NODE_ID)
        for name, amount in stocks.items():
            item_id = f"item_{name.lower()}"
            prev = self.cube_store.nodes.get(item_id)
            amt = frac_text(amount)
            faces = {f"face_{i}": self._face(f"{amt} {name}" if i == 1 else "Constituent of inventory.", i == 1)
                     for i in range(1, 7)}
            self.cube_store.write_cube(CubeNode(
                node_id=item_id, core=Core(label=name, kind="instance",
                                           identity_statement=f"Stock constituent: {amt} units of {name}."),
                faces=faces, revision=(prev.revision + 1) if prev else 1, turn_index=tick,
                provenance=Provenance(source="USER_SAID")))
            written.append(item_id)
            self.cube_store.write_branch(Branch(
                branch_id=f"branch_inv_{name.lower()}_{tick}_{len(self.cube_store.branches)}",
                context_id=self.cube_store.context_id, source_node_id=INVENTORY_NODE_ID, predicate="contains",
                target_node_id=item_id, commonality={"amount": amt, "unit": name}))
        read_back = {name: self._stored_amount(name) for name in stocks}
        ok = all(read_back[n] == frac_text(stocks[n]) for n in stocks)
        return {"written": written, "read_back": read_back, "read_back_ok": ok}

    def _stored_amount(self, name: str) -> Optional[str]:
        """The latest verified amount of `name` in the cube store (USER_SAID or CHECKED), or None."""
        if self.cube_store is None:
            return None
        node = self.cube_store.nodes.get(f"item_{name.lower()}")
        if node is None or node.provenance.source not in ("USER_SAID", "CHECKED"):
            return None
        latest = None
        for b in self.cube_store.branches:
            if (b.source_node_id == INVENTORY_NODE_ID and b.target_node_id == node.node_id
                    and b.predicate == "contains" and b.commonality):
                latest = b.commonality
        if latest is None or latest.get("absent"):      # the latest word on it is "none on hand"
            return None
        return latest.get("amount")

    def _write_event_cube(self, node_id: str, label: str, statement: str, source: str, tick: int,
                          kind: str = "event") -> Dict[str, Any]:
        if self.cube_store is None or CubeStore is None:
            return {"written": [], "read_back_ok": False, "note": "NO_STORE"}
        faces = {f"face_{i}": self._face(statement if i == 1 else "No further decomposition recorded.", i == 1)
                 for i in range(1, 7)}
        prev = self.cube_store.nodes.get(node_id)
        self.cube_store.write_cube(CubeNode(node_id=node_id, core=Core(label=label, kind=kind,
                                                                         identity_statement=statement),
                                            faces=faces, revision=(prev.revision + 1) if prev else 1,
                                            turn_index=tick, provenance=Provenance(source=source)))
        back = self.cube_store.get_cube(node_id, view_profile="Authoring")
        ok = back is not None and back.core.identity_statement == statement and back.provenance.source == source
        return {"written": [node_id], "read_back_ok": bool(ok)}

    # ------------------------------------------------------------------ results
    def _new_result(self, text: str, tick: int) -> Dict[str, Any]:
        return {"user_prompt": text, "tick": tick, "cce_round_trip": None, "valve_telemetry": None,
                "gate_verdict": None, "repair": None, "recipe_receipt": None, "cube_receipt": None,
                "output_value": None, "total_output": None, "output": None, "limiting_reagent": None,
                "everyday_english_response": "", "response": "", "text": "", "loop_status": "INITIATED",
                "receipt_hash": None, "cubes_written": [], "cubes_read": []}

    def _finish(self, result: Dict[str, Any], tick: int, status: str, message: str, writes_before: int,
                next_step: str) -> Dict[str, Any]:
        result["loop_status"] = status
        for k in ("everyday_english_response", "response", "text"):
            result[k] = message
        if self.cube_store is not None:
            result["cubes_written"] = list(self.cube_store.write_history[writes_before:])
        turn_records = [r for r in self.trace if r.get("tick") == tick]
        result["receipt_hash"] = _h16({"status": status, "records": turn_records, "message": message})
        self._emit(tick, "S6 next", loop_status=status, next=next_step,
                   cubes_written=result["cubes_written"], receipt_hash=result["receipt_hash"], said=message)
        return result

    # ------------------------------------------------------------------ the turn
    def process_turn(self, user_english: str, tick: int = 1,
                     current_inventory: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """One user turn through the circuit. `current_inventory`, if given, is rendered as checked-form stock
        sentences and goes through the same parse and round trip as the text; it is never trusted on its own."""
        result = self._new_result(user_english, tick)
        writes_before = self._store_writes()
        text = user_english.strip()
        if current_inventory:
            extra = " ".join(f"There is {Decimal(str(v)).normalize():f} of Ω_{k}." for k, v in
                             current_inventory.items())
            text = (text + " " + extra).strip()
        self._emit(tick, "user", text=text)

        if cce is None:
            self._emit(tick, "CCE skin", verified=False, rejection="NOT_VERIFIED_NO_CHECKER")
            return self._finish(result, tick, "REFUSE_NOT_VERIFIED", HELMVoiceAdapter.format_not_verified(),
                                writes_before, "STOP")

        rt = self.verify_cce_round_trip(text)
        result["cce_round_trip"] = {k: v for k, v in rt.items() if k != "content"}
        self._emit(tick, "CCE skin", **result["cce_round_trip"])
        if rt["content"] is None:
            return self._not_checked_turn(text, tick, result, writes_before)
        return self._checked_turn(rt, tick, result, writes_before)

    def _checked_turn(self, rt: Dict[str, Any], tick: int, result: Dict[str, Any],
                      writes_before: int) -> Dict[str, Any]:
        """Everything after the CCE parse. Checked-form text and English restated by the reader both run this."""
        if not rt["verified"]:
            return self._finish(result, tick, "CLARIFY_ROUND_TRIP_FAILED",
                                HELMVoiceAdapter.format_round_trip_failed(), writes_before, "WAIT_FOR_USER")
        content = rt["content"]

        if content.get("recipe") is not None:
            return self._finish(result, tick, "STATED_RECIPE_NOT_TAKEN", HELMVoiceAdapter.format_stated_recipe(),
                                writes_before, "WAIT_FOR_USER: a witnessed batch")

        said: List[str] = []
        # Absences: "There is no Ω_X." -> X is ABSENT (not zero): out of the working stock, recorded in the store,
        # and never glued back from an older stored amount.
        absent_names = []
        for rel in content.get("relations", []):
            if rel and rel[0] == "absent" and isinstance(rel[1], str):
                name = _strip_omega(rel[1])
                if name not in absent_names:
                    absent_names.append(name)
        if absent_names:
            ok, msg = self._declare_absent(absent_names, tick, result)
            if not ok:
                return self._finish(result, tick, "CLARIFY_STOCK_NOT_RECORDED", msg, writes_before, "WAIT_FOR_USER")
            said.append(msg)

        stocks: Dict[str, Fraction] = {}
        for s in content.get("stocks", []):
            ref = s.get("ref", {})
            if "outcome" not in ref:
                return self._finish(result, tick, "CLARIFY_NOT_A_STOCK", HELMVoiceAdapter.format_clarify_not_checked(),
                                    writes_before, "WAIT_FOR_USER")
            stocks[_strip_omega(ref["outcome"])] = exact_amount(s["amount"])
        if stocks:
            ok, msg = self._declare_stocks(stocks, tick, result)
            if not ok:
                return self._finish(result, tick, "CLARIFY_STOCK_NOT_RECORDED", msg, writes_before, "WAIT_FOR_USER")
            said.append(msg)

        topic = content.get("topic")
        if topic:
            return self._run_request(topic, tick, result, writes_before, said)
        if stocks or absent_names:
            msg = " ".join(said) if said else "Noted: that's marked as not on hand."
            return self._finish(result, tick, "INVENTORY_RECORDED", msg, writes_before, "DONE")
        return self._finish(result, tick, "VERIFIED_NO_RECIPE_CONTENT", HELMVoiceAdapter.format_clarify_not_checked(),
                            writes_before, "WAIT_FOR_USER")

    # ------------------------------------------------------------------ everyday English in (fix H)
    def read_english(self, text: str) -> Dict[str, Any]:
        """The English reader's reading of `text`, using this conversation's own words (last topic, units)."""
        return helm_english_in.read(text, self.brain.ingredients, list(self.brain.products),
                                    last_topic=self.last_topic, known_units=self.units)

    def wants_turn(self, text: str) -> bool:
        """True when this loop would act on `text`: checked form, or English the reader claims."""
        if cce is not None:
            try:
                cce.parse(text.strip())
                return True
            except Exception:
                pass
        return self.read_english(text)["status"] != "NOT_MINE"

    def _english_turn(self, text: str, reading: Dict[str, Any], tick: int, result: Dict[str, Any],
                      writes_before: int) -> Dict[str, Any]:
        result["english_in"] = reading
        self._emit(tick, "English in", what="helm_english_in.read", reader=reading["reader"],
                   status=reading["status"], rules=reading["rules"], stocks=reading["stocks"],
                   absent=reading["absent"], topic=reading["topic"], witness=reading["witness"],
                   ignored=reading["ignored"], clarify=reading["clarify"], checked_form=reading["checked_form"],
                   round_trip_ok=reading["round_trip_ok"], lexicon_sha256=reading["lexicon"]["sha256"],
                   frame_form=reading.get("frame_form"), unframed=reading.get("unframed") or [])
        if reading["status"] == "NOTHING_TO_SAVE":
            # rule 6: an ingredient was named, but not as stock, and the sentence is not about our kitchen
            return self._finish(result, tick, "NOTHING_TO_SAVE", NOTHING_TO_SAVE_LINE, writes_before, "DONE")
        if reading["status"] == "CLARIFY":
            code = reading["clarify"]["code"]
            return self._finish(result, tick, f"CLARIFY_ENGLISH_{code}",
                                reader_question_text(code, reading["clarify"].get("slots") or {}), writes_before,
                                f"WAIT_FOR_USER: {code}")
        if reading["status"] == "WITNESS":
            w = reading["witness"]
            res = self.witness_batch(w["product"], w["stock_before"], w["made"], w["ran_out"], tick=tick)
            res["user_prompt"] = text
            res["english_in"] = reading
            if res["loop_status"] == "WITNESS_ADMITTED":
                for name, v in w["stock_words"].items():
                    if v.get("unit") and name not in self.units:
                        self.units[name] = v["unit"]
                if w.get("made_unit") and w["product"] not in self.units:
                    self.units[w["product"]] = w["made_unit"]      # "loaves": the word the yield is counted in
                self.last_topic = w["product"]
            return res
        # CONTENT: rule 6 again, from the reading alone -- no stock or absence is written without its stock frame,
        # and the frame form must parse back to the same frames.
        frame_ok, frame_why = helm_english_in.check_frame_form(reading)
        self._emit(tick, "Stock frame", what="stock_frame_check", ok=frame_ok, why=frame_why,
                   frame_form=reading.get("frame_form"))
        if not frame_ok:
            return self._finish(result, tick, "CLARIFY_ROUND_TRIP_FAILED",
                                HELMVoiceAdapter.format_round_trip_failed(), writes_before, "WAIT_FOR_USER")
        # CONTENT: the reader's checked-form sentence goes through the SAME parse + round trip as typed checked form.
        checked = reading["checked_form"]
        rt = self.verify_cce_round_trip(checked)
        result["cce_round_trip"] = {k: v for k, v in rt.items() if k != "content"}
        result["checked_form"] = checked
        same = (rt["content"] is not None and cce.normalize(rt["content"]) == cce.normalize(reading["content"]))
        self._emit(tick, "CCE skin", what="english_in_restated", checked_form=checked, same_as_reading=same,
                   **result["cce_round_trip"])
        if not same:
            return self._finish(result, tick, "CLARIFY_ROUND_TRIP_FAILED",
                                HELMVoiceAdapter.format_round_trip_failed(), writes_before, "WAIT_FOR_USER")
        self._pending_words = {s["name"]: s for s in reading["stocks"]}
        try:
            return self._checked_turn(rt, tick, result, writes_before)
        finally:
            self._pending_words = {}

    def _not_checked_turn(self, text: str, tick: int, result: Dict[str, Any], writes_before: int) -> Dict[str, Any]:
        reading = self.read_english(text)
        if reading["status"] != "NOT_MINE":
            return self._english_turn(text, reading, tick, result, writes_before)
        lower = text.lower()
        agentic_keywords = ["audit", "run", "inspect", "verify local environment", "dispatch", "write file",
                            "read file"]
        if any(kw in lower for kw in agentic_keywords):
            dag = self.agentic_engine.decompose_goal(text)
            plan_res = self.agentic_engine.execute_dag(dag)
            result["agentic_plan_result"] = plan_res
            self._emit(tick, "outside circuit", what="agentic_executor", completed=plan_res["all_steps_completed"])
            status = "AGENTIC_PLAN_EXECUTED" if plan_res["all_steps_completed"] else "AGENTIC_PLAN_CLAMPED"
            return self._finish(result, tick, status, AgenticExecutionEngine.speak_plan_result(plan_res),
                                writes_before, "DONE")
        if any(w in lower for w in ["quantum", "tuesday", "electron sandwich", "superstring"]):
            return self._finish(result, tick, "CLARIFY_REFUSAL", HELMVoiceAdapter.format_clarify("physical recipe"),
                                writes_before, "WAIT_FOR_USER")
        if self.turn_processor is not None and self.turn_processor.classify_turn(text)[0] == "READ":
            rec = self.turn_processor.process_turn(text)
            result.update({"cube_receipt": rec.to_dict(), "operation": rec.operation, "cubes_read": rec.cubes_read})
            self._emit(tick, "outside circuit", what="cube_store_read", operation=rec.operation,
                       cubes_read=rec.cubes_read)
            if self._store_writes() != writes_before:
                return self._finish(result, tick, "READ_WROTE_REFUSED", "A read tried to write; refused.",
                                    writes_before, "STOP")
            if rec.cubes_read:
                return self._finish(result, tick, "READ_COMPLETED", rec.response_text, writes_before, "DONE")
            # A "read" that touched no cube answered nothing: it is a question the circuit cannot check.
        return self._finish(result, tick, "CLARIFY_NOT_CCE", HELMVoiceAdapter.format_clarify_not_checked(),
                            writes_before, "WAIT_FOR_USER")

    def _declare_stocks(self, stocks: Dict[str, Fraction], tick: int, result: Dict[str, Any]) -> Tuple[bool, str]:
        for name, amount in stocks.items():
            if amount <= 0:
                return False, f"An amount of {name} has to be more than zero. Nothing was saved."
            if Fraction(float(amount)) != amount:
                return False, f"I can't hold {frac_text(amount)} of {name} exactly. Nothing was saved."
        names = {k: frac_text(v) for k, v in stocks.items()}
        self._emit(tick, "S2 Bias ^5", what="stock_proposed", stocks=names, bias_version=self.bias_version)
        request = self._gate_request(tick, "record the stated stock", sorted(stocks), [], "Ω_stock")
        verdict = RPM.rpm_gate(request)
        self._emit(tick, "S5 RPM link", what="gate", request=request.as_dict(), verdict=verdict.as_dict())
        if verdict.verdict != RPM.PROCEED:
            return False, "I couldn't record that stock. Nothing was saved."
        content = cce.empty_content()
        content["stocks"] = [{"amount": frac_text(v), "ref": {"outcome": f"Ω_{k}"}} for k, v in stocks.items()]
        receipt = self.verify_cce_round_trip(content)
        receipt.pop("content", None)
        self._emit(tick, "store", what="eta_eps_receipt", kind="cce_round_trip_of_stored_content", receipt=receipt)
        if not receipt["verified"]:
            return False, HELMVoiceAdapter.format_round_trip_failed()
        write = self._write_stock_cubes(stocks, tick)
        self._emit(tick, "store", what="cube_write", **write)
        self.stock.update(stocks)
        self.bias_version += 1
        result["cube_receipt"] = write
        words = {}
        for name in stocks:
            self.declared_absent.discard(name)
            said = self._pending_words.get(name)
            if said:
                words[name] = said["words"]
                if said.get("unit") and name not in self.units:
                    self.units[name] = said["unit"]
        result["stock_recorded"] = [{"name": k, "amount": v, "words": words.get(k), "unit":
                                     (self._pending_words.get(k) or {}).get("unit", "")} for k, v in names.items()]
        return True, HELMVoiceAdapter.format_stock_recorded(names, words)

    def _declare_absent(self, names: List[str], tick: int, result: Dict[str, Any]) -> Tuple[bool, str]:
        """The user said these are gone. Gate, round trip, then the store records the absence (read back)."""
        self._emit(tick, "S2 Bias ^5", what="absent_proposed", names=names, bias_version=self.bias_version)
        request = self._gate_request(tick, "record the stated absence", sorted(names), [], "Ω_stock")
        verdict = RPM.rpm_gate(request)
        self._emit(tick, "S5 RPM link", what="gate", request=request.as_dict(), verdict=verdict.as_dict())
        if verdict.verdict != RPM.PROCEED:
            return False, "I couldn't record that. Nothing was saved."
        content = cce.empty_content()
        content["relations"] = [["absent", f"Ω_{n}"] for n in names]
        receipt = self.verify_cce_round_trip(content)
        receipt.pop("content", None)
        self._emit(tick, "store", what="eta_eps_receipt", kind="cce_round_trip_of_stored_absence", receipt=receipt)
        if not receipt["verified"]:
            return False, HELMVoiceAdapter.format_round_trip_failed()
        write = self._write_absent_cubes(names, tick)
        self._emit(tick, "store", what="cube_write", **write)
        for n in names:
            self.stock.pop(n, None)
            self.declared_absent.add(n)
            self._emit(tick, "S2 Bias ^5", what="declared_absent", name=n)
        self.bias_version += 1
        result["absent_recorded"] = list(names)
        return True, HELMVoiceAdapter.format_absent_recorded(names)

    def _write_absent_cubes(self, names: List[str], tick: int) -> Dict[str, Any]:
        if self.cube_store is None or CubeStore is None:
            return {"written": [], "read_back_ok": False, "note": "NO_STORE"}
        written = []
        if INVENTORY_NODE_ID not in self.cube_store.nodes:       # a branch needs its inventory node to exist
            inv_faces = {f"face_{i}": Face(availability="populated", human_text="Verified stock on hand.",
                                           structured={"items": sorted(names)} if i == 5 else {})
                         for i in range(1, 7)}
            self.cube_store.write_cube(CubeNode(
                node_id=INVENTORY_NODE_ID, core=Core(label="Current Inventory", kind="instance",
                                                     identity_statement="Verified session inventory (CCE round trip "
                                                                        "+ RPM gate)."),
                faces=inv_faces, revision=1, turn_index=tick, provenance=Provenance(source="USER_SAID")))
            written.append(INVENTORY_NODE_ID)
        for name in names:
            item_id = f"item_{name.lower()}"
            prev = self.cube_store.nodes.get(item_id)
            faces = {f"face_{i}": self._face(f"no {name} on hand" if i == 1 else "Constituent of inventory.", i == 1)
                     for i in range(1, 7)}
            self.cube_store.write_cube(CubeNode(
                node_id=item_id, core=Core(label=name, kind="instance",
                                           identity_statement=f"Stock constituent: no {name} on hand (user said)."),
                faces=faces, revision=(prev.revision + 1) if prev else 1, turn_index=tick,
                provenance=Provenance(source="USER_SAID")))
            written.append(item_id)
            self.cube_store.write_branch(Branch(
                branch_id=f"branch_inv_{name.lower()}_{tick}_{len(self.cube_store.branches)}",
                context_id=self.cube_store.context_id, source_node_id=INVENTORY_NODE_ID, predicate="contains",
                target_node_id=item_id, commonality={"absent": True, "unit": name}))
        read_back = {n: self._stored_amount(n) for n in names}
        return {"written": written, "read_back": read_back, "read_back_ok": all(v is None for v in read_back.values())}

    def _stock_child(self, glued: Dict[str, Fraction], product: str) -> Callable[..., Dict[str, Any]]:
        def open_child(sub_goal, gap, kind, depth):
            m = re.fullmatch(r"the stock of Ω_(\w+)", gap or "")
            if m:
                name = m.group(1)
                if name in self.declared_absent:
                    return {"ok": False, "detail": f"the user said there is no {name}; nothing is glued back",
                            "clarify": f"the stock of Ω_{name}"}
                found = self._stored_amount(name)
                if found is None:
                    return {"ok": False, "detail": f"no verified amount of {name} in the cube store",
                            "clarify": f"the stock of Ω_{name}"}
                glued[name] = Fraction(found)
                return {"ok": True, "detail": f"cube store holds {found} of {name} (verified earlier)"}
            m = re.fullmatch(r"the requirement of Ω_(\w+) for Ω_(\w+)", gap or "")
            if m:
                name = m.group(1)
                rows = [r for r in self.brain.witness_log if r["product"] == product]
                replay = self.brain.replay(rows)
                learned_on_replay = any(r["admitted"] and row["ran_out"] == name for r, row in zip(replay, rows))
                return {"ok": False, "detail": f"replayed {len(rows)} witnessed batch(es) of {product}; "
                        f"{name} was {'learned' if learned_on_replay else 'never witnessed as running out first'}"
                        "; a requirement cannot be made up", "clarify": gap}
            return {"ok": False, "detail": f"no child knows how to realize {gap!r}"}
        return open_child

    def _run_request(self, topic: str, tick: int, result: Dict[str, Any], writes_before: int,
                     said: List[str]) -> Dict[str, Any]:
        product = self.brain.product_of(topic)
        self._emit(tick, "S0 atlas head", topic=topic, product=product, brain=self.brain.provenance())
        if product is None:
            msg = (f"I don't know a recipe for {_strip_omega(topic)}. I know {', '.join(self.brain.products)}. "
                   f"Nothing was saved.")
            return self._finish(result, tick, "CLARIFY_UNKNOWN_PRODUCT", msg, writes_before, "WAIT_FOR_USER")
        self.last_topic = product
        support = self.brain.support_of(product)
        self._emit(tick, "S1 trigger ^8", product=product, prerequisites=support,
                   requirements=self.brain.requirements(product))
        self._emit(tick, "S2 Bias ^5", what="stock_on_hand", bias_version=self.bias_version,
                   bias_digest=self._bias_digest(), stock={k: frac_text(v) for k, v in self.stock.items()})
        absent = [c for c in support if c not in self.stock]
        unlearned = self.brain.unlearned(product)
        self._emit(tick, "S3 arrival ^9", present=[c for c in support if c in self.stock], absent=absent,
                   unlearned_requirements=unlearned)
        allowed, telem = self.valve.evaluate_reagents(tick, product, support, list(self.stock), "EXACT")
        result["valve_telemetry"] = telem.as_dict()
        self._emit(tick, "S4 operating point", valve=telem.as_dict())

        unsatisfied = [f"the stock of Ω_{c}" for c in absent] + \
                      [f"the requirement of Ω_{c} for Ω_{product}" for c in unlearned]
        request = self._gate_request(tick, f"compute Ω_{product} from the stock on hand", support, unsatisfied,
                                     f"Ω_{product}")
        glued: Dict[str, Fraction] = {}
        verdict, ledger, outcome = self._run_gate_with_repair(tick, request, self._stock_child(glued, product))
        result["gate_verdict"] = verdict.as_dict()
        result["repair"] = {"outcome": outcome, "ledger": ledger, "glued": {k: frac_text(v) for k, v in glued.items()}}

        if verdict.verdict != RPM.PROCEED:
            still_absent = [c for c in absent if c not in glued]
            saved = bool(said)          # stock said in this same turn WAS recorded; say so honestly
            if still_absent:
                msg = HELMVoiceAdapter.format_missing(product, still_absent, saved=saved,
                                                      said_gone=sorted(self.declared_absent))
            elif unlearned:
                msg = HELMVoiceAdapter.format_unlearned(product, unlearned, saved=saved)
            else:
                msg = f"I can't work out {product} right now. I didn't guess, and nothing was saved."
            if said:
                msg = " ".join(said) + " " + msg
            clarify = cce.empty_content()
            clarify.update(turn="CLARIFY", topic=f"Ω_{product}", lacunae=[verdict.gap or unsatisfied[0]])
            rt = self.verify_cce_round_trip(clarify)
            self._emit(tick, "CCE skin", what="clarify_said", sentence=rt.get("sentence"), verified=rt["verified"])
            return self._finish(result, tick, "UNDETERMINED_CLARIFY", msg, writes_before,
                                f"WAIT_FOR_USER: {verdict.gap}")

        if glued:
            # The child's ACTUAL result is inserted into the working stock, then S3 and S4 are read again.
            self.stock.update(glued)
            self.bias_version += 1
            self._emit(tick, "S2 Bias ^5", what="glued_from_child", glued={k: frac_text(v) for k, v in glued.items()},
                       bias_version=self.bias_version)
            allowed, telem = self.valve.evaluate_reagents(tick, product, support, list(self.stock), "EXACT")
            result["valve_telemetry"] = telem.as_dict()
            self._emit(tick, "S4 operating point", valve=telem.as_dict())
        if not allowed:
            return self._finish(result, tick, f"VALVE_HALT_{telem.gate_interlock}",
                                HELMVoiceAdapter.format_missing(product, telem.missing_reagents or ["an ingredient"]),
                                writes_before, "WAIT_FOR_USER")

        receipt = self.brain.evaluate(product, {c: self.stock[c] for c in self.brain.ingredients if c in self.stock})
        result["recipe_receipt"] = receipt
        self._emit(tick, "brain", **receipt)
        if receipt["status"] != EVALUATED:
            msg = HELMVoiceAdapter.format_brain_undetermined(product, receipt.get("gate"))
            return self._finish(result, tick, "BRAIN_UNDETERMINED", (" ".join(said) + " " + msg) if said else msg,
                                writes_before, "WAIT_FOR_USER")
        y, lim = receipt["yield"], receipt["limiting_reagent"]
        result.update({"output_value": y, "total_output": y, "output": y, "limiting_reagent": lim})
        statement = (f"Theoretical yield {y} of {product} from stock "
                     f"{', '.join(f'{frac_text(self.stock[c])} {c}' for c in support)}; limiting reagent {lim}; "
                     f"brain {receipt['learned_digest'][:16]}")
        write = self._write_event_cube(f"yield_{product.lower()}_t{tick}", f"{product} yield", statement,
                                       "CHECKED", tick, kind="instance")
        self._emit(tick, "store", what="cube_write", **write)
        result["cube_receipt"] = write
        msg = HELMVoiceAdapter.format_success(product, y, lim, _h16(receipt))
        if said:
            msg = " ".join(said) + " " + msg
        return self._finish(result, tick, "SUCCESS_EVALUATED", msg, writes_before, "DONE")

    # ------------------------------------------------------------------ teaching channel
    def witness_batch(self, product: str, stock_before: Dict[str, Any], made: Any, ran_out: str,
                      tick: int = 1) -> Dict[str, Any]:
        """One batch the user actually made. Through: CCE form receipt -> gate -> the brain's own writer ->
        (admitted) store write with read-back, or (refused) a DETECTED failure -> gate REPAIR -> repair child."""
        result = self._new_result(f"[witnessed batch] {product}", tick)
        writes_before = self._store_writes()
        prod = self.brain.product_of(product)
        stock = {self.brain.ingredient_of(k) or k: exact_amount(v) for k, v in stock_before.items()}
        made_f = exact_amount(made)
        self._emit(tick, "user", what="witnessed_batch", product=product,
                   stock_before={k: frac_text(v) for k, v in stock.items()}, made=frac_text(made_f), ran_out=ran_out)
        if prod is None:
            return self._finish(result, tick, "CLARIFY_UNKNOWN_PRODUCT",
                                f"I don't know a recipe called {product}. Nothing was saved.", writes_before,
                                "WAIT_FOR_USER")
        form = cce.empty_content() if cce is not None else None
        if form is None:
            return self._finish(result, tick, "REFUSE_NOT_VERIFIED", HELMVoiceAdapter.format_not_verified(),
                                writes_before, "STOP")
        form.update(topic=f"Ω_{prod}", stocks=[{"amount": frac_text(v), "ref": {"outcome": f"Ω_{k}"}}
                                               for k, v in stock.items()] +
                    [{"amount": frac_text(made_f), "ref": {"outcome": f"Ω_{prod}"}}])
        rt = self.verify_cce_round_trip(form)
        result["cce_round_trip"] = {k: v for k, v in rt.items() if k != "content"}
        self._emit(tick, "CCE skin", **result["cce_round_trip"])
        if not rt["verified"]:
            return self._finish(result, tick, "CLARIFY_ROUND_TRIP_FAILED",
                                HELMVoiceAdapter.format_round_trip_failed(), writes_before, "WAIT_FOR_USER")
        support = self.brain.support_of(prod)
        absent = [c for c in support if c not in stock]
        self._emit(tick, "S1 trigger ^8", product=prod, prerequisites=support)
        self._emit(tick, "S3 arrival ^9", present=[c for c in support if c in stock], absent=absent)
        request = self._gate_request(tick, f"teach Ω_{prod} from a witnessed batch", support,
                                     [f"the stock of Ω_{c}" for c in absent], f"Ω_{prod}")
        verdict = RPM.rpm_gate(request)
        self._emit(tick, "S5 RPM link", what="gate", request=request.as_dict(), verdict=verdict.as_dict())
        result["gate_verdict"] = verdict.as_dict()
        if verdict.verdict != RPM.PROCEED:
            return self._finish(result, tick, "UNDETERMINED_CLARIFY",
                                f"That batch report is missing how much {', '.join(absent)} you started with. "
                                f"I didn't guess, and nothing was saved.", writes_before, f"WAIT_FOR_USER: {verdict.gap}")

        try:
            record = self.brain.witness(prod, stock, made_f, self.brain.ingredient_of(ran_out) or ran_out)
        except CanonicalBrainRefused as exc:
            self._emit(tick, "brain", what="witness_refused_by_adapter", code=exc.code, detail=exc.detail)
            return self._finish(result, tick, "CLARIFY_BATCH_NOT_USABLE",
                                HELMVoiceAdapter.format_teach_refused(prod, exc.code), writes_before,
                                "WAIT_FOR_USER")
        result["recipe_receipt"] = record
        self._emit(tick, "brain", what="writer", record=record)

        if record["admitted"]:
            eta = record.get("eta_eps", {})
            if not (eta.get("pass") and record.get("memory_check_ok")):
                return self._finish(result, tick, "REFUSE_RECEIPT_INCONSISTENT",
                                    "The brain's own check did not hold, so nothing was saved.", writes_before, "STOP")
            cell_name = record["ran_out"]
            value = self.brain.requirements(prod)[cell_name]
            statement = (f"Witnessed batch {record['made']} of {prod}; {cell_name} ran out first; "
                         f"requirement {value} {cell_name} per {prod}; receipt pass")
            write = self._write_event_cube(f"batch_{prod.lower()}_{self.brain._seed}", f"{prod} batch", statement,
                                           "USER_SAID", tick)
            self._emit(tick, "store", what="cube_write", **write)
            return self._finish(result, tick, "WITNESS_ADMITTED",
                                HELMVoiceAdapter.format_learned(prod, cell_name, value), writes_before, "DONE")

        # ---- A REAL, DETECTED FAILURE: the brain's own writer refused the batch.
        detected = {"detected_by": "rb2.writer_b.teach_step_b (the canonical brain's own writer)",
                    "reason": record["reason"], "candidate": record["candidate"], "detail": record.get("detail")}
        self._emit(tick, "S3 arrival ^9", what="failure_detected", **detected)
        ing = record["ran_out"]
        gap = f"a requirement of Ω_{ing} for Ω_{prod} that agrees with every witnessed batch"
        request = self._gate_request(tick, f"teach Ω_{prod} from a witnessed batch", support, [gap], f"Ω_{prod}")
        rows = [r for r in self.brain.witness_log if r["product"] == prod]

        def replay_child(sub_goal, gap, kind, depth):
            replay = self.brain.replay(rows)
            ok = all(r["admitted"] for r in replay)
            return {"ok": ok, "detail": json.dumps(replay, default=str)}

        verdict, ledger, outcome = self._run_gate_with_repair(tick, request, replay_child)
        result["gate_verdict"] = verdict.as_dict()
        result["repair"] = {"outcome": outcome, "ledger": ledger, "detected": detected}
        if outcome == repair_actor.REPAIRED:
            msg = "The batches agree on a second look, but I haven't changed anything. Please tell me the batch again."
            return self._finish(result, tick, "REPAIRED_RETEACH_NEEDED", msg, writes_before, "WAIT_FOR_USER")
        detail = record.get("detail") or {}
        if record["reason"] == "REFUSED_CONFLICT":
            msg = HELMVoiceAdapter.format_conflict(prod, ing, detail.get("old"), detail.get("new"))
        else:
            msg = HELMVoiceAdapter.format_teach_refused(prod, record["reason"])
        return self._finish(result, tick, "CONFLICT_UNDETERMINED" if record["reason"] == "REFUSED_CONFLICT"
                            else f"TEACH_REFUSED_{record['reason']}", msg, writes_before, f"WAIT_FOR_USER: {gap}")


# -----------------------------------------------------------------------------
# 3. The live end-to-end trace (EXECUTION_QUEUE row 15)
# -----------------------------------------------------------------------------
def run_live_trace(trace_path: str = DEFAULT_TRACE_PATH) -> Dict[str, Any]:
    """A real sequence of turns through the whole path, every receipt written to a JSONL file."""
    if os.path.exists(trace_path):
        os.remove(trace_path)
    os.makedirs(os.path.dirname(os.path.abspath(trace_path)), exist_ok=True)
    loop = HELMEndToEndLoop(trace_path=trace_path)
    loop._emit(0, "header", what="HELM live end-to-end trace (fix H: everyday English in; two free-English turns "
                                 "added at ticks 11-12)", date="2026-10-18",
               run_at_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               python=sys.version.split()[0], platform=sys.platform, brain=loop.brain.provenance(),
               valve=loop.valve.status_summary(), gate_claim_ceiling=RPM.CLAIM_CEILING,
               repair_claim_ceiling=repair_actor.CLAIM_CEILING, english_reader=helm_english_in.READER_VERSION,
               english_reader_claim_status=helm_english_in.CLAIM_STATUS,
               english_reader_lexicon_sha256=helm_english_in.LEXICON_SHA256)
    outcomes = []
    outcomes.append(loop.witness_batch("Bread", {"Flour": 10, "Water": 8}, 5, "Flour", tick=1))
    outcomes.append(loop.witness_batch("Bread", {"Flour": 10, "Water": 2}, 2, "Water", tick=2))
    outcomes.append(loop.process_turn("There is 12 of Ω_Flour.", tick=3))
    outcomes.append(loop.process_turn("Topic: Ω_Bread.", tick=4))                       # must be UNDETERMINED
    outcomes.append(loop.process_turn("How much bread could we bake with whatever is around?", tick=5))  # CLARIFY
    outcomes.append(loop.process_turn("There is 9 of Ω_Water.", tick=6))
    outcomes.append(loop.process_turn("Topic: Ω_Bread.", tick=7))                       # SUCCESS
    outcomes.append(loop.witness_batch("Bread", {"Flour": 10, "Water": 8}, 4, "Flour", tick=8))  # real conflict
    # A later session on the same cube store and brain: its working stock is empty, so the repair child
    # must fetch Water from the store and glue the real amount back.
    later = HELMEndToEndLoop(cube_store=loop.cube_store, brain=loop.brain, trace_path=trace_path)
    outcomes.append(later.process_turn("There is 20 of Ω_Flour.", tick=9))
    outcomes.append(later.process_turn("Topic: Ω_Bread.", tick=10))                     # REPAIRED -> SUCCESS
    # Fix H: a third session on the same store and brain, in everyday English only. The same receipts as the
    # checked-form ticks 3-4 and 6-7 must come back: UNDETERMINED for missing water, then SUCCESS after water.
    third = HELMEndToEndLoop(cube_store=loop.cube_store, brain=loop.brain, trace_path=trace_path)
    outcomes.append(third.process_turn("We have 12 cups of flour and no water. Can we bake bread?", tick=11))
    outcomes.append(third.process_turn("Now we've got 9 cups of water — how much bread can we make?", tick=12))
    summary = [{"tick": o["tick"], "loop_status": o["loop_status"], "said": o["response"],
                "cubes_written": o["cubes_written"]} for o in outcomes]
    with open(trace_path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return {"trace_path": trace_path, "sha256": digest, "turns": summary}


if __name__ == "__main__":
    out = run_live_trace(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TRACE_PATH)
    for row in out["turns"]:
        print(f"tick {row['tick']:>2}  {row['loop_status']:<28} writes={len(row['cubes_written'])}  {row['said']}")
    print("trace:", out["trace_path"])
    print("sha256:", out["sha256"])
