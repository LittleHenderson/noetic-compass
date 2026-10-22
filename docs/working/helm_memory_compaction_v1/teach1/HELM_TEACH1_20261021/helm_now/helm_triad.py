"""helm_triad.py -- the Purpose / Wisdom / Power triad as a wrapper around HELM's canonical recipe brain.

WHAT THIS IS (plain words)
--------------------------
Each ingredient can carry three faces: Purpose (is it meant for this?), Wisdom (do we know how to use it?) and
Power (can it actually do the job?). Each face sits on ONE scale (owner ruling 2026-10-18, "same 4 stage values
for all three faces"): RISING 1/4, PEAK 1, WANING 1/2, ABSENT 0. The lowest face sets how much of the ingredient
really counts (owner ruling "min"):

    x_eff = min(Purpose, Wisdom, Power) * stock          (exact Fractions)

The licensed brain then answers on x_eff exactly as it answers today. The answer gains two bottlenecks: which
ingredient runs out first (the brain's), and which FACE of it is to blame: the EARLIEST face that is not at Peak,
in RPM order Purpose -> Wisdom -> Power (owner ruling "earliest"). The face with the smallest value is reported
beside it and never decides.

One more face sits on the whole recipe: the recipe's Purpose (the RPM Gate's door question). ABSENT -> the answer
is UNDETERMINED and the gate needs "the Purpose of Omega_X" (ask the user; never guess). RISING / WANING -> the
brain's yield Y_T is reported and the expected yield is eta * Y_T (Clarification 9 production efficiency).

Wisdom follows rule C (owner ruling 2026-10-18 night: "drops only by a named event with evidence [C]."): it never
drifts down. A lower Wisdom is accepted only through one of three named events, each with an evidence receipt:
STORAGE_FAULT, CORRECTION, UNEXPLAINED_YIELD. A lower Wisdom with no event is refused and logged.
(DWP-T2, Documents/Codex/2026-10-18/dwp_t2/RESULTS.md: status word C_EARNED_KEEP, SYNTHETIC_ONLY.)

Every face write is written, read back (eta_teach o eps_read) and receipted. Receipts sit in an append-only log
kept apart from the stored records, so a reload can check every record against its receipt.

WHAT THIS IS NOT
----------------
* Nothing here is learned. No gradient. Zero learned parameters. Face stages are INPUTS, each with a named source.
* It does not edit the sealed package or helm_brain_canonical.py. `TriadBrain` takes a brain and a triad table.
* Default is OFF: `TriadBrain(brain)` passes every call straight through, so existing behaviour is unchanged.
  Turning it on (`enabled=True`) with no stated faces gives the brain's own answers (every face reads Peak).
* It does not touch helm_end_to_end_loop.py or helm_chat.py (another builder owns those).

CLAIM CEILING: ENGINEERED-NOT-VALIDATED, SYNTHETIC_ONLY. The triad's existence in any real mind, model or kitchen
is not claimed. Face stages are stored per ingredient (coordinator choice; the 28 drive cells and the 22 pathways
are NOT read).
"""
from __future__ import annotations

import copy
import hashlib
import json
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

CLAIM_CEILING = "ENGINEERED-NOT-VALIDATED; SYNTHETIC_ONLY; zero learned parameters; faces are stated inputs"

# ------------------------------------------------------------------ the one scale (owner ruling)
RISING, PEAK, WANING, ABSENT = "RISING", "PEAK", "WANING", "ABSENT"
STAGE_VALUE: Dict[str, Fraction] = {RISING: Fraction(1, 4), PEAK: Fraction(1), WANING: Fraction(1, 2),
                                    ABSENT: Fraction(0)}
VALUE_STAGE: Dict[Fraction, str] = {v: k for k, v in STAGE_VALUE.items()}
#: Coordinator choice: Wisdom climbs 0 -> 1/4 -> 1/2 -> 1 (on the one scale: ABSENT, RISING, WANING, PEAK).
WISDOM_RUNGS: Tuple[str, ...] = (ABSENT, RISING, WANING, PEAK)

PURPOSE, WISDOM, POWER = "PURPOSE", "WISDOM", "POWER"
RPM_ORDER: Tuple[str, ...] = (PURPOSE, WISDOM, POWER)          # owner ruling: earliest; book: Desire = Purpose
NONE_RAW_STOCK = "NONE_RAW_STOCK"
UNDETERMINED = "UNDETERMINED"
UNKNOWN = "UNKNOWN"                                             # a face whose stored record failed its receipt

UNSTATED_NEUTRAL = "UNSTATED_NEUTRAL"                           # nothing stored: reads Peak, labelled
EVENTS = ("STORAGE_FAULT", "CORRECTION", "UNEXPLAINED_YIELD")


class TriadRefused(RuntimeError):
    """A triad write or answer is refused. Carries a stable code."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(obj: Any) -> str:
    return hashlib.sha256(_canon(obj).encode("ascii")).hexdigest()


def ftext(v: Optional[Fraction]) -> Optional[str]:
    if v is None:
        return None
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


# ------------------------------------------------------------------ the triad table (stored inputs, receipted)
class TriadTable:
    """Per-ingredient faces + one Purpose per recipe. Sparse: only stated faces are stored.

    A stored record: {"scope": "ingredient"|"recipe", "name", "face", "stage", "source", "evidence", "seq"}.
    The receipt log is append-only and kept apart from the records."""

    def __init__(self) -> None:
        self.records: Dict[str, str] = {}               # key -> JSON text of the record (the store)
        self.receipt_log: List[Dict[str, Any]] = []     # append-only
        self.events: List[Dict[str, Any]] = []
        self.refusals: List[Dict[str, Any]] = []
        self.unknown: Dict[str, Dict[str, Any]] = {}    # key -> STORAGE_FAULT evidence (face reads UNKNOWN)
        self._seq = 0

    # ---- keys and reads
    @staticmethod
    def key(scope: str, name: str, face: str) -> str:
        return f"{scope}|{name}|{face}"

    def record(self, scope: str, name: str, face: str) -> Optional[Dict[str, Any]]:
        text = self.records.get(self.key(scope, name, face))
        return None if text is None else json.loads(text)

    def stage(self, name: str, face: str) -> str:
        """The stage an ingredient face reads as: stored, UNKNOWN (faulted) or PEAK (unstated, neutral)."""
        k = self.key("ingredient", name, face)
        if k in self.unknown:
            return UNKNOWN
        rec = self.record("ingredient", name, face)
        return PEAK if rec is None else rec["stage"]

    def source(self, name: str, face: str) -> str:
        rec = self.record("ingredient", name, face)
        return UNSTATED_NEUTRAL if rec is None else rec["source"]

    def recipe_purpose(self, product: str) -> Tuple[str, str]:
        k = self.key("recipe", product, PURPOSE)
        if k in self.unknown:
            return UNKNOWN, "STORAGE_FAULT"
        rec = self.record("recipe", product, PURPOSE)
        return (PEAK, UNSTATED_NEUTRAL) if rec is None else (rec["stage"], rec["source"])

    def last_receipt(self, key: str) -> Optional[Dict[str, Any]]:
        for r in reversed(self.receipt_log):
            if r["key"] == key:
                return r
        return None

    def stored_value_count(self) -> int:
        return len(self.records)

    def snapshot(self) -> Dict[str, Any]:
        out = {}
        for k in sorted(self.records):
            rec = json.loads(self.records[k])
            out[k] = [rec["stage"], rec["source"]]
        for k in sorted(self.unknown):
            out[k] = [UNKNOWN, "STORAGE_FAULT"]
        return out

    def snapshot_digest(self) -> str:
        return digest(self.snapshot())

    # ---- writes
    def _refuse(self, code: str, key: str, detail: str) -> None:
        self.refusals.append({"code": code, "key": key, "detail": detail})
        raise TriadRefused(code, f"{key}: {detail}")

    def _check_event(self, key: str, scope: str, name: str, new_stage: str, event: Dict[str, Any]) -> None:
        kind = event.get("event")
        if kind not in EVENTS:
            self._refuse("WISDOM_DROP_NEEDS_EVENT", key, f"unknown event {kind!r}")
        ev = event.get("evidence")
        if not isinstance(ev, dict) or not ev:
            self._refuse("WISDOM_DROP_NEEDS_EVENT", key, f"{kind} without an evidence receipt")
        if kind == "STORAGE_FAULT":
            last = self.last_receipt(key)
            if (last is None or ev.get("receipt_digest") != last["digest"]
                    or not ev.get("read_back_digest") or ev.get("read_back_digest") == last["digest"]):
                self._refuse("WISDOM_DROP_NEEDS_EVENT", key,
                             "STORAGE_FAULT evidence must name this record's receipt and a different read-back")
        elif kind == "CORRECTION":
            if not ev.get("source") or not ev.get("corrected_statement_digest"):
                self._refuse("WISDOM_DROP_NEEDS_EVENT", key, "CORRECTION needs a named source and a statement digest")
        else:  # UNEXPLAINED_YIELD
            need = ("product", "stock_digest", "made", "eta_observed", "requirement")
            if any(ev.get(n) in (None, "") for n in need):
                self._refuse("WISDOM_DROP_NEEDS_EVENT", key, "UNEXPLAINED_YIELD evidence incomplete")
            eta_obs = Fraction(ev["eta_observed"])
            p_rec = self.record(scope, name, PURPOSE)
            pw_rec = self.record(scope, name, POWER)
            if p_rec is None or pw_rec is None:
                self._refuse("WISDOM_DROP_NEEDS_EVENT", key,
                             "UNEXPLAINED_YIELD needs Purpose and Power stated for this ingredient")
            if not eta_obs < min(STAGE_VALUE[p_rec["stage"]], STAGE_VALUE[pw_rec["stage"]]):
                self._refuse("WISDOM_DROP_NEEDS_EVENT", key, "Purpose or Power explains the yield")
            if STAGE_VALUE[new_stage] != eta_obs:
                self._refuse("WISDOM_DROP_NEEDS_EVENT", key, "the new Wisdom must equal the observed strength")
            last = self.last_receipt(key)
            if last is None or digest(json.loads(self.records[key])) != last["digest"]:
                self._refuse("WISDOM_DROP_NEEDS_EVENT", key, "the Wisdom record fails its receipt (storage fault?)")

    def set_face(self, scope: str, name: str, face: str, stage: str, source: str, evidence: str,
                 event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Admissibility -> write -> read back (eta_teach o eps_read) -> receipt. Returns the receipt."""
        key = self.key(scope, name, face)
        if scope not in ("ingredient", "recipe"):
            self._refuse("SCOPE_INVALID", key, scope)
        if face not in RPM_ORDER or (scope == "recipe" and face != PURPOSE):
            self._refuse("FACE_INVALID", key, face)
        if stage not in STAGE_VALUE:
            self._refuse("STAGE_NOT_ON_THE_ONE_SCALE", key, str(stage))
        if not source or source == UNSTATED_NEUTRAL:
            self._refuse("SOURCE_REQUIRED", key, "a stored face needs a named source")
        if not evidence:
            self._refuse("EVIDENCE_REQUIRED", key, "a stored face needs an evidence digest (sentence, ledger row)")
        if face == WISDOM and scope == "ingredient":
            old = self.record(scope, name, WISDOM)
            # compared with the last RECEIPTED Wisdom only: a first statement, or a re-statement after a caught
            # storage fault (the faulted value was never taken), has nothing to drop from.
            lower = (old is not None and STAGE_VALUE[stage] < STAGE_VALUE[old["stage"]])
            if lower:
                if event is None:
                    self._refuse("WISDOM_DROP_NEEDS_EVENT", key, f"{old['stage']} -> {stage} with no named event")
                self._check_event(key, scope, name, stage, event)
        self._seq += 1
        rec = {"scope": scope, "name": name, "face": face, "stage": stage, "source": source,
               "evidence": evidence, "seq": self._seq}
        self.records[key] = _canon(rec)                         # eta_teach: the write
        back = json.loads(self.records[key])                    # eps_read: read it back
        ok = back == rec
        if not ok:
            raise TriadRefused("READ_BACK_MISMATCH", key)
        receipt = {"key": key, "seq": self._seq, "digest": digest(back), "read_back_ok": ok,
                   "event": None if event is None else event["event"]}
        self.receipt_log.append(receipt)
        self.unknown.pop(key, None)
        if event is not None:
            logged = {"event": event["event"], "key": key, "new_stage": stage,
                      "evidence": copy.deepcopy(event["evidence"])}
            logged["evidence_receipt"] = digest(logged)
            self.events.append(logged)
        return dict(receipt)

    # ---- save / reload (records and receipts are saved apart)
    def save(self) -> Tuple[str, str]:
        return _canon(self.records), _canon(self.receipt_log)

    @classmethod
    def load(cls, records_text: str, receipts_text: str) -> "TriadTable":
        """Reload. Every record is read back and checked against its last receipt. A mismatch is a STORAGE_FAULT:
        the value is NOT taken, the face reads UNKNOWN (answers that need it are UNDETERMINED) until re-stated."""
        t = cls()
        t.receipt_log = json.loads(receipts_text)
        t._seq = max((r["seq"] for r in t.receipt_log), default=0)
        for key, text in json.loads(records_text).items():
            last = t.last_receipt(key)
            got = digest(json.loads(text))
            if last is not None and got == last["digest"]:
                t.records[key] = text
                continue
            ev = {"event": "STORAGE_FAULT", "key": key,
                  "evidence": {"receipt_digest": None if last is None else last["digest"], "read_back_digest": got}}
            ev["evidence_receipt"] = digest(ev)
            t.events.append(ev)
            t.refusals.append({"code": "DROP_REFUSED_NO_EVENT" if key.endswith("|" + WISDOM) else "RECORD_REFUSED",
                               "key": key, "detail": "read-back does not match its receipt; value not taken"})
            t.unknown[key] = ev
        for r in t.receipt_log:                                  # a receipted record that vanished is a fault too
            if r["key"] not in t.records and r["key"] not in t.unknown and t.last_receipt(r["key"]) is r:
                ev = {"event": "STORAGE_FAULT", "key": r["key"],
                      "evidence": {"receipt_digest": r["digest"], "read_back_digest": "MISSING"}}
                ev["evidence_receipt"] = digest(ev)
                t.events.append(ev)
                t.unknown[r["key"]] = ev
        return t


# ------------------------------------------------------------------ face arithmetic (programmed, never learned)
def faces_of(table: TriadTable, name: str) -> Tuple[str, str, str]:
    return tuple(table.stage(name, f) for f in RPM_ORDER)  # type: ignore[return-value]


def eta_ingredient(stages: Tuple[str, ...]) -> Optional[Fraction]:
    """Owner ruling 'min'. None when any face is UNKNOWN."""
    if UNKNOWN in stages:
        return None
    return min(STAGE_VALUE[s] for s in stages)


def face_blamed(stages: Tuple[str, ...]) -> str:
    """Owner ruling 'earliest': the first face, Purpose -> Wisdom -> Power, that is not at Peak."""
    for f, s in zip(RPM_ORDER, stages):
        if s == UNKNOWN or STAGE_VALUE[s] < 1:
            return f
    return NONE_RAW_STOCK


def face_binding(stages: Tuple[str, ...]) -> str:
    """REPORT ONLY: the face with the smallest value (ties by RPM order)."""
    if UNKNOWN in stages:
        return UNKNOWN
    v = [STAGE_VALUE[s] for s in stages]
    if min(v) >= 1:
        return NONE_RAW_STOCK
    return RPM_ORDER[min(range(3), key=lambda k: (v[k], k))]


def epsilon_faces(stages: Tuple[str, ...]) -> Optional[Dict[str, str]]:
    """REPORT ONLY: Clarification 9 excess capacity per face (a = 1 per face): face - eta."""
    e = eta_ingredient(stages)
    if e is None:
        return None
    return {f: ftext(STAGE_VALUE[s] - e) for f, s in zip(RPM_ORDER, stages)}


# ------------------------------------------------------------------ the wrapper
class TriadBrain:
    """Wraps a canonical brain (helm_brain_canonical.CanonicalRecipeBrain or anything with the same calls).

    enabled=False (the default): every call passes straight through; nothing is added.
    enabled=True: answers on x_eff, the recipe-Purpose door, face attribution, Wisdom rule C."""

    LEARNED_PARAMETERS = 0

    def __init__(self, brain: Any, table: Optional[TriadTable] = None, enabled: bool = False) -> None:
        self.brain = brain
        self.table = table if table is not None else TriadTable()
        self.enabled = bool(enabled)

    # ---- passthroughs
    def __getattr__(self, name: str) -> Any:
        return getattr(self.brain, name)

    def parameter_count(self) -> Dict[str, Any]:
        n_ing = len(getattr(self.brain, "ingredients", []))
        n_rec = len(getattr(self.brain, "products", {}))
        return {"learned_parameters": self.LEARNED_PARAMETERS,
                "stored_values": self.table.stored_value_count(),
                "stored_value_ceiling": 3 * n_ing + n_rec,
                "note": "stored values are stated INPUTS with sources, not parameters; each is a 2-bit stage symbol"}

    # ---- the door (recipe Purpose)
    def door(self, product: str) -> Dict[str, Any]:
        stage, source = self.table.recipe_purpose(product)
        if stage in (ABSENT, UNKNOWN):
            return {"unsatisfied": f"the Purpose of Ω_{product}", "eta_recipe": None, "stage": stage, "source": source}
        return {"unsatisfied": None, "eta_recipe": STAGE_VALUE[stage], "stage": stage, "source": source}

    def effective_stock(self, product: str, stock: Dict[str, Fraction]) -> Tuple[Dict[str, Fraction], List[str]]:
        support = self.brain.support_of(product)
        out, unknown = dict(stock), []
        for name in support:
            if name not in stock:
                continue                                         # an absent support cell stays absent (never filled)
            e = eta_ingredient(faces_of(self.table, name))
            if e is None:
                unknown.append(name)
                continue
            out[name] = e * Fraction(stock[name])
        return out, unknown

    def evaluate(self, product: str, stock: Dict[str, Fraction]) -> Dict[str, Any]:
        if not self.enabled:
            return self.brain.evaluate(product, stock)
        door = self.door(product)
        base = {"product": product, "triad": "ON", "triad_depth": 1, "triad_snapshot": self.table.snapshot(),
                "triad_digest": self.table.snapshot_digest(), "recipe_purpose_stage": door["stage"],
                "recipe_purpose_source": door["source"], "learned_parameters_added": 0}
        if door["unsatisfied"] is not None:
            base.update({"status": UNDETERMINED, "label": UNDETERMINED, "gate": "PURPOSE_ABSENT"
                         if door["stage"] == ABSENT else "PURPOSE_UNKNOWN",
                         "unsatisfied": door["unsatisfied"], "yield": None, "limiting_reagent": None,
                         "repair": "ASK the user what the outcome is for; never invent a Purpose"})
            return base
        x_eff, unknown = self.effective_stock(product, stock)
        if unknown:
            base.update({"status": UNDETERMINED, "label": UNDETERMINED, "gate": "TRIAD_FACE_UNKNOWN",
                         "unknown_faces": unknown, "yield": None, "limiting_reagent": None})
            return base
        raw = self.brain.evaluate(product, stock)                # report only: today's bottleneck on raw stock
        rec = dict(self.brain.evaluate(product, x_eff))
        rec.update(base)
        support = self.brain.support_of(product)
        rec["raw_limiting_ingredient"] = raw.get("limiting_reagent")
        rec["eta_ingredient"] = {n: ftext(eta_ingredient(faces_of(self.table, n))) for n in support}
        rec["face_sources"] = {n: {f: self.table.source(n, f) for f in RPM_ORDER} for n in support}
        rec["eta_recipe"] = ftext(door["eta_recipe"])
        lim = rec.get("limiting_reagent")
        if isinstance(lim, str):
            st = faces_of(self.table, lim)
            rec["face_blamed"] = face_blamed(st)
            rec["face_binding"] = face_binding(st)
            rec["epsilon_faces"] = epsilon_faces(st)
        else:
            zeroed = [n for n in support if n in stock and eta_ingredient(faces_of(self.table, n)) == 0]
            rec["face_blamed"] = UNDETERMINED
            rec["zeroed_by"] = {n: face_blamed(faces_of(self.table, n)) for n in zeroed}
        y = rec.get("yield")
        rec["yield_theoretical"] = y
        if y is not None and rec.get("status") != UNDETERMINED:
            rec["yield"] = ftext(door["eta_recipe"] * Fraction(y))
        rec["yield_expected"] = rec["yield"] if rec.get("status") != UNDETERMINED else None
        return rec

    # ---- teaching: convert the witnessed batch before the sealed writer sees it
    def witness(self, product: str, stock_before: Dict[str, Fraction], made: Any, ran_out: str) -> Dict[str, Any]:
        if not self.enabled:
            return self.brain.witness(product, stock_before, made, ran_out)
        made_f = Fraction(str(made))
        door = self.door(product)
        if door["unsatisfied"] is not None:
            code = "TRIAD_CONTRADICTION" if made_f > 0 else "REFUSED_PURPOSE_ABSENT"
            raise TriadRefused(code, f"{product}: recipe Purpose {door['stage']}, made {ftext(made_f)}")
        x_eff, unknown = self.effective_stock(product, stock_before)
        if unknown:
            raise TriadRefused("TRIAD_FACE_UNKNOWN", ", ".join(unknown))
        y_theoretical = made_f / door["eta_recipe"]             # the writer learns Y_T, not Y_A
        rec = dict(self.brain.witness(product, x_eff, y_theoretical, ran_out))
        rec["triad_snapshot"] = self.table.snapshot()
        rec["triad_digest"] = self.table.snapshot_digest()
        rec["board_fed_to_writer"] = {k: ftext(Fraction(v)) for k, v in x_eff.items()}
        rec["yield_fed_to_writer"] = ftext(y_theoretical)
        return rec

    # ---- Wisdom rule C: the UNEXPLAINED_YIELD path, with evidence the adapter computes itself
    def wisdom_drop_from_yield(self, product: str, stock: Dict[str, Fraction], made: Any, ran_out: str,
                               source: str = "OBSERVED_YIELDS") -> Dict[str, Any]:
        """A witnessed batch where `ran_out` made less than its Purpose and Power allow. The observed strength is
        eta_obs = made * a / stock (a = the brain's own learned, write-once requirement). Accepted only through
        TriadTable's UNEXPLAINED_YIELD checks."""
        made_f = Fraction(str(made))
        req = self.brain.requirements(product).get(ran_out)
        if req is None:
            raise TriadRefused("WISDOM_DROP_NEEDS_EVENT", f"{ran_out}: requirement not learned for {product}")
        eta_obs = made_f * Fraction(req) / Fraction(stock[ran_out])
        if eta_obs not in VALUE_STAGE:
            raise TriadRefused("WISDOM_DROP_NEEDS_EVENT", f"observed strength {ftext(eta_obs)} is not on the one scale")
        ev = {"product": product, "stock_digest": digest({k: ftext(Fraction(v)) for k, v in stock.items()}),
              "made": ftext(made_f), "ran_out": ran_out, "requirement": req, "eta_observed": ftext(eta_obs)}
        return self.table.set_face("ingredient", ran_out, WISDOM, VALUE_STAGE[eta_obs], source,
                                   evidence=digest(ev), event={"event": "UNEXPLAINED_YIELD", "evidence": ev})


def score3(key: Any, got: Any) -> str:
    """The 3-valued rule (rb/common.py, DWP-T1): UNDETERMINED is not wrong."""
    if key == UNDETERMINED:
        return "RIGHT" if got == UNDETERMINED else "WRONG"
    if got == UNDETERMINED:
        return "UNDETERMINED"
    return "RIGHT" if got == key else "WRONG"


if __name__ == "__main__":
    from helm_brain_canonical import CanonicalRecipeBrain
    tb = TriadBrain(CanonicalRecipeBrain(), enabled=True)
    print(json.dumps({"claim_ceiling": CLAIM_CEILING, "parameter_count": tb.parameter_count()}, indent=1))
