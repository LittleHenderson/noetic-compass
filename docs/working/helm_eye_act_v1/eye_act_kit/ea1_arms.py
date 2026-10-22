"""EYE-ACT-1 arms and the one-world runner (PREREGISTRATION_EYE_ACT_V1.precode.md section 3). Standard library only.

A0 OFF, A1 HOLD, A2 ACT, A3 CONCERT run the live loop with switch HELM_EYE_ACT set by constructor argument.
R1 CHECKSUM_COPY, R2 REBUILD_ALWAYS and C1 RANDOM_REPAIR run the loop with the switch OFF plus a harness rule; they
never use the Eye. R2 and C1 re-derive with the same pure helpers the Eye uses (helm_eye_act.rederive_book and
verified_stock: the book's own writer and the loop's own trace), so the only difference from the Eye is WHEN they act
and that they do not detect, ledger or hold.
"""
from __future__ import annotations

import copy
import hashlib
import json
from fractions import Fraction
from typing import Any, Dict, List, Optional

import ea1_world as G

ARMS = ("A0", "A1", "A2", "A3", "R1", "R2", "C1")
EYE_MODE = {"A0": None, "A1": "HOLD", "A2": "ACT", "A3": "CONCERT", "R1": None, "R2": None, "C1": None}
SWEEP_EVERY = 4


def _canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def stock_digest(loop: Any) -> str:
    st = {n: [None if q is None else str(Fraction(q)), u] for n, (q, u) in sorted(getattr(loop, "wide_stock", {}).items())}
    return hashlib.sha256(_canon(st).encode()).hexdigest()


def state(loop: Any) -> Dict[str, Any]:
    return {"book": loop.wide_book.learned_digest(), "stock": stock_digest(loop), "writes": loop._store_writes()}


def outcome(res: Dict[str, Any], world: Dict[str, Any]) -> str:
    v = res.get("output_value")
    if res.get("loop_status") != "SUCCESS_EVALUATED" or v is None:
        return "ASK"
    ok = Fraction(str(v)) == Fraction(world["key_value"]) and res.get("limiting_reagent") == world["limiting"]
    return "RIGHT" if ok else "WRONG"


# ===================================================================== harness rules (no Eye)
class Rule:
    name = "NONE"

    def __init__(self, world: Dict[str, Any]):
        self.interventions = 0
        self.bytes_held = 0
        self.picks = 0
        self.picks_on_fault = 0
        self.picks_after_plant = 0

    def before(self, loop, text, tick, is_q, turn_no):  # noqa: D401
        pass

    def after(self, loop, tick):
        pass

    def on_write(self, loop):
        pass


class ChecksumCopy(Rule):
    """R1: keep a sha256 and a deep copy after every turn that changed the book or stock (and after a write the writer
    made); before every question, put the copy back if the live digest differs."""
    name = "R1"

    def __init__(self, world):
        super().__init__(world)
        self.kept = None

    def _keep(self, loop):
        st = state(loop)
        self.kept = {"book": st["book"], "stock": st["stock"],
                     "recipes": copy.deepcopy(loop.wide_book.recipes), "log": copy.deepcopy(loop.wide_book.witness_log),
                     "seed": loop.wide_book._seed, "stock_val": copy.deepcopy(dict(getattr(loop, "wide_stock", {})))}
        self.bytes_held = len(_canon({k: v for k, v in self.kept.items()}).encode())

    def after(self, loop, tick):
        st = state(loop)
        if self.kept is None or (st["book"], st["stock"]) != (self.kept["book"], self.kept["stock"]):
            self._keep(loop)

    def on_write(self, loop):
        self._keep(loop)

    def before(self, loop, text, tick, is_q, turn_no):
        if not is_q or self.kept is None:
            return
        st = state(loop)
        if (st["book"], st["stock"]) != (self.kept["book"], self.kept["stock"]):
            loop.wide_book.recipes = copy.deepcopy(self.kept["recipes"])
            loop.wide_book.witness_log = copy.deepcopy(self.kept["log"])
            loop.wide_book._seed = self.kept["seed"]
            loop.wide_stock = copy.deepcopy(self.kept["stock_val"])
            self.interventions += 1


class RebuildAlways(Rule):
    """R2: before every question, the book := its re-derivation and the stock := the verified stock, always."""
    name = "R2"

    def before(self, loop, text, tick, is_q, turn_no):
        if not is_q:
            return
        import helm_eye_act as EA
        st0 = state(loop)
        fresh = EA.rederive_book(loop.wide_book)
        loop.wide_book.recipes = copy.deepcopy(fresh.recipes)
        loop.wide_book.witness_log = copy.deepcopy(fresh.witness_log)
        loop.wide_book._seed = fresh._seed
        loop.wide_stock = dict(EA.verified_stock(loop))
        if state(loop) != st0:
            self.interventions += 1


class RandomRepair(Rule):
    """C1: at A2's sweep times (turn 1, then every 4 turns), re-derive ONE object chosen at random (book or stock)."""
    name = "C1"

    def __init__(self, world):
        super().__init__(world)
        self.rng = G.rng_for("C1:" + world["seed"])
        self.since = None
        self.fault_obj = {"F1_TAMPER_COEFF": "book", "F3_SLIPPED_LESSON": "book", "F4_LOST_SOURCE": "book",
                          "F2_TAMPER_STOCK": "stock"}.get(world["kind"])
        self.planted = False

    def before(self, loop, text, tick, is_q, turn_no):
        import helm_eye_act as EA
        due = self.since is None or self.since >= SWEEP_EVERY
        if due:
            self.since = 0
            obj = self.rng.choice(("book", "stock"))
            self.picks += 1
            if self.planted:
                self.picks_after_plant += 1
                if obj == self.fault_obj:
                    self.picks_on_fault += 1
            st0 = state(loop)
            if obj == "book":
                fresh = EA.rederive_book(loop.wide_book)
                loop.wide_book.recipes = copy.deepcopy(fresh.recipes)
                loop.wide_book.witness_log = copy.deepcopy(fresh.witness_log)
                loop.wide_book._seed = fresh._seed
            else:
                loop.wide_stock = dict(EA.verified_stock(loop))
            if state(loop) != st0:
                self.interventions += 1
        self.since = (self.since or 0) + 1


RULES = {"R1": ChecksumCopy, "R2": RebuildAlways, "C1": RandomRepair}


# ===================================================================== one world, one arm
def run_world(world: Dict[str, Any], arm: str, planted: bool = True) -> Dict[str, Any]:
    import helm_end_to_end_loop as E2E
    import helm_wide_turn as WT
    loop = E2E.HELMEndToEndLoop(wide_brain=True, eye_act=EYE_MODE[arm] or "OFF")
    rule = RULES[arm](world) if arm in RULES else Rule(world)
    probes = {v: k for k, v in world["probes"].items()}
    items, statuses, plant_rec = {}, [], None
    for i, text in enumerate(world["turns"]):
        tick = i + 1
        if planted and i == world["plant_after"] + 1:
            plant_rec = G.plant(loop, world)
            if isinstance(rule, RandomRepair):
                rule.planted = world["kind"] != "CLEAN"
            if plant_rec.get("write"):
                rule.on_write(loop)
        is_q = WT.read_wide(text.strip(), last_topic=loop.last_topic).get("status") == "QUESTION"
        rule.before(loop, text, tick, is_q, i)
        res = loop.process_turn(text, tick=tick)
        rule.after(loop, tick)
        statuses.append(res.get("loop_status"))
        if i in probes:
            items[probes[i]] = {"outcome": outcome(res, world), "status": res.get("loop_status"),
                                "value": None if res.get("output_value") is None else str(res.get("output_value")),
                                "limiting": res.get("limiting_reagent")}
    eye = loop.eye_act
    ledger = eye.ledger if eye is not None else []
    restores_trace = [r for r in loop.trace if r.get("station") == "eye" and str(r.get("action", "")).startswith("RESTORE")]
    auto = [e for e in ledger if e["kind"] == "AUTONOMIC"]
    return {
        "seed": world["seed"], "kind": world["kind"], "arm": arm, "planted": planted, "plant": plant_rec,
        "items": items, "statuses": statuses,
        "final": state(loop),
        "interventions": len(auto) if eye is not None else rule.interventions,
        "holds": len([e for e in ledger if e["kind"] == "HOLD"]),
        "bytes_held": eye.bytes_held() if eye is not None else rule.bytes_held,
        "eye": None if eye is None else {
            "sweeps": len([e for e in ledger if e["kind"] == "SWEEP"]),
            "findings": sorted({f["code"] for e in ledger if e["kind"] == "SWEEP" for f in e["findings"]}),
            "requests": len([e for e in ledger if e["kind"] == "REQUEST"]),
            "replies": len([e for e in ledger if e["kind"] == "REPLY"]),
            "restores": len(auto), "restores_in_trace": len(restores_trace),
            "restores_verified": all(e.get("verified") for e in auto),
            "sweeps_pure": all(e.get("pure") for e in ledger if e["kind"] == "SWEEP")},
        "c1": None if arm != "C1" else {"picks": rule.picks, "picks_on_fault": rule.picks_on_fault,
                                        "picks_after_plant": rule.picks_after_plant},
    }
