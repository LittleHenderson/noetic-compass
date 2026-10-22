"""helm_cas_address.py -- the CAS ADDRESS every receipt and every filed item HELM writes carries (schema `cas_address/1`).

Owner's fix G ("redeem 22x40", 2026-10-18) and the 28-cell pairing packet, stage 1 (owner word "build both",
2026-10-20; docs/working/helm_eye_pairing_28_cells_design_v1/DESIGN.md section 1). Census 2 (spec sheet 7.97) found that
no record HELM wrote carried both a Foundation and a Domain, so the cell of the 28 could not be read after the fact: the
address has to be written by the program that writes the record, at the moment it writes it. This module is the ONE place
the rules live. Every field is set by a NAMED rule below or stays `UNTAGGED`. There is no default and no guess.

THE ADDRESS
    {"schema": "cas_address/1",
     "foundation": F1..F7 | UNTAGGED,          the 7 Drives: F1 Unity, F2 Wisdom, F3 Vitality, F4 Connection,
                                               F5 Agency, F6 Structure, F7 Purpose
     "domain":     P | C | E | O | UNTAGGED,   the 4 Domains: Principled, Cognitive, Evaluative, Operational
     "cell":       "<F><D>" (one of 28, e.g. F2C) | UNTAGGED,
     "register":   T | A | f | E | UNTAGGED,   the 4 Registers: Transcendent, Analytical, Affective, Embodied
     "pathway":    A0 | D1..D7 | W1..W7 | P1..P7 | UNTAGGED,   the 22 Capability Pathways
     "element":    "^<n><D>" (one of 40, e.g. ^8C) | UNTAGGED, the 40 elements = 10 Noetics x 4 Domains
     "how":        {field: the rule id that set it, or "UNTAGGED"}}

THE RULES (first that applies sets the field; nothing applies -> UNTAGGED)
  Foundation  FND-1  the record itself names a Foundation (field foundation / drive / filed_at / desire / F: "F1".."F7",
                     or one of the seven canonical Drive names).
              FND-2  an item the Unity Eye wrote (source / by / station / kind names the Unity Eye) is F1: the owner's
                     ruling names the Eye the F1 watcher (eye/eye.py header, OWNER_RULING_UNITY_EYE_20261015).
              Honest limit: the live loop's own receipts name no Foundation, so their Foundation is UNTAGGED and their
              cell is UNTAGGED. That is census 2's finding, now carried on the record instead of lost.
  Domain      DOM-1  a status / reason / code word maps through the fixed table DOM_1_TABLE (the census-2 draft table,
                     promoted; the sub-rule id a..e is recorded). P: rules, caps, refusals, guards. C: readings,
                     lessons, answers, plans, questions (a question is a reading that stopped). E: verdicts, receipts,
                     checks, Eye findings. O: stock lines, batches, tool calls, files.
              DOM-2  an item KIND maps through DOM_2_TABLE (stock / batch / cube_write / tool_call / file -> O;
                     reading / lesson / coefficient / plan_step / question -> C; verdict / mark / receipt / whisper
                     -> E; rule / cap / refusal / guard / gate -> P).
              DOM-3  a trace row's STATION maps through DOM_3_TABLE (the loop's stations: the CCE skin is a receipt
                     pass / fail (E); S1 trigger names the prerequisites, a plan step (C); S2 Bias is the stock on
                     hand (O); S3 arrival checks presence (E); S5 RPM link is the gate, a guard (P); the readers are
                     readings (C); the store's cube_write is a file (O) and its eta_eps_receipt a receipt (E);
                     "brain" and "S6 next" rows go by their word (DOM-1)). Stations not in the table: UNTAGGED.
  Cell        CELL-1 Foundation x Domain when both are set.
  Register    REG-1a a faces sentence or a purpose clause carries f (word names FACE, PURPOSE or TRIAD).
              REG-1b a plan or a rule carries A (a plan; a refusal, guard, clamp or gate verdict: the rule that fired).
              REG-1c a stock or batch line carries E (STOCK_RECORDED, INVENTORY_RECORDED, a WITNESS record, S2 Bias).
              REG-1d a vision-level item (an owner ruling, the roadmap) carries T (kind ruling / roadmap; none today).
  Pathway     PATH-1 only an item that is a step of an RPM chain the prerequisite planner holds, and only when the
                     planner names the node (field pathway / pathway_node in A0, D1..D7, W1..W7, P1..P7). No planner
                     names a node today, so every pathway is UNTAGGED; no classifier is written for it.
  Element     ELE-1  only where the record already names a Noetic (field noetic = 0..9 or "^n", or a station string that
                     carries "^n": "S1 trigger ^8", "S2 Bias ^5", "S3 arrival ^9") AND the Domain is set:
                     element = "^<n><D>". No new Noetic classifier is written.

WHAT THE TAGS MAY DO. File and choose. They never enter a computed value, a coefficient, a verdict, a yield, the gate or a
receipt hash: helm_end_to_end_loop._finish hashes the turn's records with every address stripped (`without_address`), so
the receipt hash of a turn is the same with the switch ON and OFF (a test proves it). Old records without the field read
as all-UNTAGGED (`read_address`).

SWITCH: CAS_ADDRESS, `cas_address_on()`. Environment variable HELM_CAS_ADDRESS set to 0 / OFF / FALSE / NO switches it
off; otherwise ON. OFF: no record carries the field and every record is byte-identical to the code before this module
(a test pins the OFF records of a fixed sequence of turns to the sha256 computed on the pre-change code). The 28-cell
Eye (stage 2 of the packet, switch EYE_CELLS) is NOT built; nothing here pairs, whispers or chooses.

CLAIM STATUS: ENGINEERED-NOT-VALIDATED. No claim moved. Standard library only.
"""
from __future__ import annotations

import copy
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCHEMA = "cas_address/1"
UNTAGGED = "UNTAGGED"
CAS_ADDRESS_ENV = "HELM_CAS_ADDRESS"
CAS_ADDRESS_OFF_WORDS = ("0", "OFF", "FALSE", "NO")   # the only values that switch the address off

#: the canonical names (CLAUDE.md; docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md Clarifications 1, 8)
FOUNDATIONS: Dict[str, str] = {"F1": "Unity", "F2": "Wisdom", "F3": "Vitality", "F4": "Connection", "F5": "Agency",
                               "F6": "Structure", "F7": "Purpose"}
DOMAINS: Dict[str, str] = {"P": "Principled", "C": "Cognitive", "E": "Evaluative", "O": "Operational"}
REGISTERS: Dict[str, str] = {"T": "Transcendent", "A": "Analytical", "f": "Affective", "E": "Embodied"}
NOETICS: Dict[int, str] = {0: "Idea", 1: "Mind", 2: "Positive", 3: "Negative", 4: "Vibration", 5: "Female", 6: "Male",
                           7: "Rhythm", 8: "Above/Cause", 9: "Below/Effect"}
PATHWAYS: Tuple[str, ...] = ("A0",) + tuple(f"D{i}" for i in range(1, 8)) + tuple(f"W{i}" for i in range(1, 8)) + \
    tuple(f"P{i}" for i in range(1, 8))
CELLS: Tuple[str, ...] = tuple(f"{f}{d}" for f in FOUNDATIONS for d in DOMAINS)            # 28
ELEMENTS: Tuple[str, ...] = tuple(f"^{n}{d}" for n in NOETICS for d in DOMAINS)             # 40
FIELDS = ("foundation", "domain", "cell", "register", "pathway", "element")


def cas_address_on(value: Optional[bool] = None) -> bool:
    """The CAS_ADDRESS switch: an explicit argument wins; else HELM_CAS_ADDRESS = 0 / OFF / FALSE / NO is off; else on."""
    if value is not None:
        return bool(value)
    return os.environ.get(CAS_ADDRESS_ENV, "").strip().upper() not in CAS_ADDRESS_OFF_WORDS


# ---------------------------------------------------------------------------------------------------- the tables
#: DOM-1: (regex over the status / reason / code word, Domain, sub-rule id). First match wins. The census-2 draft table
#: promoted: refusals before everything (a refused lesson is a rule firing), questions before the O words (a question
#: about stock is a reading that stopped, not a stock line).
DOM_1_TABLE: Tuple[Tuple[str, str, str], ...] = (
    (r"REFUS|GUARD|CUT_|CLAMPED|ALWAYS_ASK|LEARNING_DISABLED|VIOLAT", "P", "DOM-1a rules, caps, refusals, guards"),
    (r"ADMITTED|SUCCESS_EVALUATED|^EVALUATED$|UNDETERMINED|PLAN|LEARNED|READ$|REPLAY|NOT_MINE", "C",
     "DOM-1b readings, lessons, answers, plans"),
    (r"^CLARIFY|^ASK|QUESTION|^NO_|^AMOUNT_|^UNIT_|^SAME_INGREDIENT|^UNREAD_", "C",
     "DOM-1e a question = a reading that stopped"),
    (r"COMPLETE|EXITED|SKIPPED|CHECK|VERIF|FINDING|WHISPER|REPORT|PASS|FAIL|ADMIT$", "E",
     "DOM-1c verdicts, receipts, checks, Eye findings"),
    (r"INVENTORY_RECORDED|STOCK_RECORDED|^WITNESS|RECORDED|TOOL|FILE|^STOCK$", "O",
     "DOM-1d stock, batches, tools, files"),
)
#: DOM-2: an item kind -> Domain
DOM_2_TABLE: Dict[str, str] = {"stock": "O", "batch": "O", "cube_write": "O", "tool_call": "O", "file": "O",
                               "store_read": "O",
                               "reading": "C", "lesson": "C", "coefficient": "C", "plan_step": "C", "question": "C",
                               "verdict": "E", "mark": "E", "receipt": "E", "whisper": "E",
                               "rule": "P", "cap": "P", "refusal": "P", "guard": "P", "gate": "P"}
#: DOM-3: a trace row's station -> Domain, or "WORD" (go by the row's word, DOM-1), or "WHAT" (go by the row's `what`)
DOM_3_TABLE: Dict[str, str] = {"CCE skin": "E", "S0 atlas head": "C", "English in": "C", "English in (wide)": "C",
                               "Stock frame": "C", "S1 trigger ^8": "C", "S2 Bias ^5": "O", "S3 arrival ^9": "E",
                               "S5 RPM link": "P", "outside circuit": "O", "brain": "WORD", "S6 next": "WORD",
                               "store": "WHAT"}
#: DOM-3 for the store station's `what`: a cube write is a file (O); an eta/epsilon receipt is a receipt (E)
DOM_3_STORE_WHAT: Dict[str, str] = {"cube_write": "O", "eta_eps_receipt": "E"}
#: REG-1: (regex over the word, Register, sub-rule id). First match wins.
REG_1_TABLE: Tuple[Tuple[str, str, str], ...] = (
    (r"FACE|PURPOSE|TRIAD", "f", "REG-1a a faces sentence or a purpose clause"),
    (r"PLAN|REFUS|GUARD|CLAMPED|VIOLAT|^GATE$", "A", "REG-1b a plan or a rule that fired"),
    (r"STOCK_RECORDED|INVENTORY_RECORDED|^WITNESS|^STOCK$|^stock", "E", "REG-1c a stock or batch line"),
)
REG_1_KIND: Dict[str, Tuple[str, str]] = {"stock": ("E", "REG-1c a stock or batch line"),
                                          "batch": ("E", "REG-1c a stock or batch line"),
                                          "plan_step": ("A", "REG-1b a plan or a rule that fired"),
                                          "rule": ("A", "REG-1b a plan or a rule that fired"),
                                          "gate": ("A", "REG-1b a plan or a rule that fired"),
                                          "refusal": ("A", "REG-1b a plan or a rule that fired"),
                                          "guard": ("A", "REG-1b a plan or a rule that fired"),
                                          "ruling": ("T", "REG-1d a vision-level item"),
                                          "roadmap": ("T", "REG-1d a vision-level item")}
REG_1_STATION: Dict[str, Tuple[str, str]] = {"S5 RPM link": ("A", "REG-1b a plan or a rule that fired"),
                                             "S2 Bias ^5": ("E", "REG-1c a stock or batch line")}
#: the fields a record may name its Foundation in (FND-1), its word in (DOM-1), its Noetic in (ELE-1), its node in (PATH-1)
FOUNDATION_FIELDS = ("foundation", "drive", "filed_at", "desire", "F")
WORD_FIELDS = ("loop_status", "status", "reason", "code", "verdict", "outcome")
NOETIC_FIELDS = ("noetic",)
PATHWAY_FIELDS = ("pathway_node", "pathway")
EYE_WORDS = ("unity_eye", "unity eye", "unityeye")
_FOUND_RX = re.compile(r"^F[1-7]$")
_NOETIC_IN_STATION_RX = re.compile(r"\^(\d)\b")

#: every rule, by id, in plain words (a test prints this table; the docstring above is the long form)
RULES: Dict[str, str] = {
    "FND-1": "the record names its Foundation (F1..F7 or a canonical Drive name) in a foundation / drive / filed_at / "
             "desire / F field",
    "FND-2": "an item the Unity Eye wrote is F1 (the owner's ruling names the Eye the F1 watcher)",
    "DOM-1": "a status / reason / code word maps through DOM_1_TABLE (sub-rules a..e)",
    "DOM-2": "an item kind maps through DOM_2_TABLE",
    "DOM-3": "a trace row's station maps through DOM_3_TABLE (brain and S6 next rows go by their word)",
    "CELL-1": "Foundation x Domain when both are set",
    "REG-1a": "a faces sentence or a purpose clause carries f",
    "REG-1b": "a plan or a rule that fired carries A",
    "REG-1c": "a stock or batch line carries E",
    "REG-1d": "a vision-level item (ruling, roadmap) carries T",
    "PATH-1": "only a planner-named RPM chain node (A0, D1..D7, W1..W7, P1..P7) in a pathway / pathway_node field",
    "ELE-1": "only a Noetic the record already names (noetic field, or ^n in the station) x a set Domain",
}


# ---------------------------------------------------------------------------------------------------- the rules
def _first_word(record: Optional[Dict[str, Any]], word: Optional[str]) -> Optional[str]:
    if word:
        return word
    if not isinstance(record, dict):
        return None
    for k in WORD_FIELDS:
        v = record.get(k)
        if isinstance(v, str) and v and v != "None":
            return v
    inner = record.get("record")                    # "brain" rows: _emit(tick, "brain", what="writer", record=record)
    if isinstance(inner, dict):
        for k in WORD_FIELDS:
            v = inner.get(k)
            if isinstance(v, str) and v and v != "None":
                return v
    return None


def foundation_of(record: Optional[Dict[str, Any]], kind: Optional[str] = None) -> Tuple[str, str]:
    """FND-1, FND-2, else UNTAGGED."""
    if isinstance(record, dict):
        for k in FOUNDATION_FIELDS:
            v = record.get(k)
            if isinstance(v, str):
                if _FOUND_RX.match(v):
                    return v, "FND-1"
                for f, name in FOUNDATIONS.items():
                    if v.strip().lower() == name.lower():
                        return f, "FND-1"
        for k in ("source", "by", "station", "kind", "writer"):
            v = record.get(k)
            if isinstance(v, str) and v.strip().lower() in EYE_WORDS:
                return "F1", "FND-2"
    if isinstance(kind, str) and kind.strip().lower() in EYE_WORDS:
        return "F1", "FND-2"
    return UNTAGGED, UNTAGGED


def domain_of_word(word: Optional[str]) -> Tuple[str, str]:
    """DOM-1 over one word, else UNTAGGED."""
    if not word:
        return UNTAGGED, UNTAGGED
    for rx, dom, rid in DOM_1_TABLE:
        if re.search(rx, word):
            return dom, rid
    return UNTAGGED, UNTAGGED


def domain_of(record: Optional[Dict[str, Any]], kind: Optional[str] = None, word: Optional[str] = None,
              station: Optional[str] = None) -> Tuple[str, str]:
    """DOM-3 (a station), DOM-1 (a word), DOM-2 (a kind), else UNTAGGED."""
    if station is not None:
        rule = DOM_3_TABLE.get(station)
        if rule is None:
            return UNTAGGED, UNTAGGED
        if rule == "WHAT":
            what = record.get("what") if isinstance(record, dict) else None
            dom = DOM_3_STORE_WHAT.get(what or "")
            return (dom, f"DOM-3 station {station} / {what}") if dom else (UNTAGGED, UNTAGGED)
        if rule == "WORD":
            dom, rid = domain_of_word(_first_word(record, word))
            return (dom, rid) if dom != UNTAGGED else (UNTAGGED, UNTAGGED)
        return rule, f"DOM-3 station {station}"
    w = _first_word(record, word)
    dom, rid = domain_of_word(w)
    if dom != UNTAGGED:
        return dom, rid
    if kind and kind in DOM_2_TABLE:
        return DOM_2_TABLE[kind], f"DOM-2 kind {kind}"
    return UNTAGGED, UNTAGGED


def register_of(record: Optional[Dict[str, Any]], kind: Optional[str] = None, word: Optional[str] = None,
                station: Optional[str] = None) -> Tuple[str, str]:
    """REG-1a..d, else UNTAGGED. A trace row goes by its station: S5 RPM link (A), S2 Bias (E); "brain" and "S6 next"
    rows by their own word; a reader's row is a reading, whatever sentence it read, so it stays UNTAGGED."""
    if station in REG_1_STATION:
        return REG_1_STATION[station]
    if station is not None and DOM_3_TABLE.get(station) != "WORD":
        return UNTAGGED, UNTAGGED
    w = _first_word(record, word)
    if w:
        for rx, reg, rid in REG_1_TABLE:
            if re.search(rx, w):
                return reg, rid
    if kind in REG_1_KIND:
        return REG_1_KIND[kind]
    return UNTAGGED, UNTAGGED


def pathway_of(record: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    """PATH-1, else UNTAGGED."""
    if isinstance(record, dict):
        for k in PATHWAY_FIELDS:
            v = record.get(k)
            if isinstance(v, str) and v in PATHWAYS:
                return v, "PATH-1"
    return UNTAGGED, UNTAGGED


def noetic_of(record: Optional[Dict[str, Any]], station: Optional[str] = None) -> Optional[int]:
    if isinstance(record, dict):
        for k in NOETIC_FIELDS:
            v = record.get(k)
            if isinstance(v, bool):
                continue
            if isinstance(v, int) and v in NOETICS:
                return v
            if isinstance(v, str):
                m = re.fullmatch(r"\^?(\d)", v.strip())
                if m and int(m.group(1)) in NOETICS:
                    return int(m.group(1))
    s = station if station is not None else (record.get("station") if isinstance(record, dict) else None)
    if isinstance(s, str):
        m = _NOETIC_IN_STATION_RX.search(s)
        if m:
            return int(m.group(1))
    return None


def element_of(record: Optional[Dict[str, Any]], domain: str, station: Optional[str] = None) -> Tuple[str, str]:
    """ELE-1: a Noetic the record already names x a set Domain, else UNTAGGED."""
    n = noetic_of(record, station)
    if n is None or domain == UNTAGGED:
        return UNTAGGED, UNTAGGED
    return f"^{n}{domain}", "ELE-1"


def address(record: Optional[Dict[str, Any]] = None, *, kind: Optional[str] = None, word: Optional[str] = None,
            station: Optional[str] = None) -> Dict[str, Any]:
    """The cas_address/1 of one record: every field by a named rule or UNTAGGED; `how` names the rule per field."""
    f, f_how = foundation_of(record, kind)
    d, d_how = domain_of(record, kind, word, station)
    cell, cell_how = (f"{f}{d}", "CELL-1") if f != UNTAGGED and d != UNTAGGED else (UNTAGGED, UNTAGGED)
    r, r_how = register_of(record, kind, word, station)
    p, p_how = pathway_of(record)
    e, e_how = element_of(record, d, station)
    return {"schema": SCHEMA, "foundation": f, "domain": d, "cell": cell, "register": r, "pathway": p, "element": e,
            "how": {"foundation": f_how, "domain": d_how, "cell": cell_how, "register": r_how, "pathway": p_how,
                    "element": e_how}}


def untagged() -> Dict[str, Any]:
    """What a record without the field reads as: all UNTAGGED."""
    return {"schema": SCHEMA, **{k: UNTAGGED for k in FIELDS}, "how": {k: UNTAGGED for k in FIELDS}}


def read_address(record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The address a record carries; an old record without one reads as all UNTAGGED."""
    a = record.get("address") if isinstance(record, dict) else None
    return a if isinstance(a, dict) and a.get("schema") == SCHEMA else untagged()


# ---------------------------------------------------------------------------------------------------- the stamps
def address_for_trace_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """A loop trace row (helm_end_to_end_loop._emit): by its station (DOM-3), its word, its Noetic."""
    return address(row, station=row.get("station"))


def address_for_turn(loop_status: str, result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The turn receipt (the loop's result dict): by its loop_status word."""
    return address(result, word=loop_status)


def address_for_cube_receipt(receipt: Dict[str, Any]) -> Dict[str, Any]:
    """A cube-store write receipt: a file (DOM-2 cube_write -> O)."""
    return address(receipt, kind="cube_write", word="")


def address_for_recipe_receipt(record: Dict[str, Any]) -> Dict[str, Any]:
    """A brain record (writer or evaluate): by its reason / status word (DOM-1)."""
    return address(record)


def address_for_filed_item(item: Dict[str, Any], kind: Optional[str] = None) -> Dict[str, Any]:
    """A filed backlog item (the drive loop's or the Eye's): its Foundation by FND-1 / FND-2, its Domain by its word or
    kind. The filing program calls this at the moment it files; nothing here reads old files."""
    return address(item, kind=kind or (item.get("kind") if isinstance(item.get("kind"), str) else None))


def stamp_turn(result: Dict[str, Any], loop_status: str) -> Dict[str, Any]:
    """Stamp the turn receipt and the receipts it carries. The nested receipts are shallow-copied, never mutated in the
    brain's or the store's hands. Returns `result`."""
    result["address"] = address_for_turn(loop_status, result)
    rr = result.get("recipe_receipt")
    if isinstance(rr, dict) and "address" not in rr:
        result["recipe_receipt"] = dict(rr, address=address_for_recipe_receipt(rr))
    cr = result.get("cube_receipt")
    if isinstance(cr, dict) and "address" not in cr:
        result["cube_receipt"] = dict(cr, address=address_for_cube_receipt(cr))
    return result


def without_address(obj: Any) -> Any:
    """A deep copy with every `address` field removed (what a hash or a comparison must see: tags touch no value)."""
    if isinstance(obj, dict):
        return {k: without_address(v) for k, v in obj.items() if k != "address"}
    if isinstance(obj, list):
        return [without_address(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(without_address(v) for v in obj)
    return copy.deepcopy(obj)


# ---------------------------------------------------------------------------------------------------- the census
def cell_histogram(addresses: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Counts only: items per cell of the 28, per field tagged / UNTAGGED. For a re-census of records that carry the
    address (the packet's floor: 20 of 28 cells with 8 or more items)."""
    grid = {c: 0 for c in CELLS}
    tagged = {k: 0 for k in FIELDS}
    untag = {k: 0 for k in FIELDS}
    n = 0
    for a in addresses:
        n += 1
        for k in FIELDS:
            if a.get(k, UNTAGGED) == UNTAGGED:
                untag[k] += 1
            else:
                tagged[k] += 1
        if a.get("cell") in grid:
            grid[a["cell"]] += 1
    filled = sum(1 for v in grid.values() if v >= 8)
    return {"items": n, "grid_28": grid, "tagged": tagged, "untagged": untag,
            "cells_with_8_or_more": filled, "floor_20_of_28": "PASS_FLOOR" if filled >= 20 else "STOP_NOT_EXERCISED"}
