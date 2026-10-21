"""Tests for helm_cas_address.py (owner's fix G, stage 1 of the 28-cell packet) and its wiring in the live loop.

What is proved here, nothing more:
  - every field of cas_address/1 is set by a named rule or is UNTAGGED; every rule is exercised by name;
  - the live loop stamps every trace row, every turn receipt and the receipts it carries when the switch is ON;
  - the receipt hash of a turn is the same with the switch ON and OFF (tags touch no value);
  - with the switch OFF, a fixed sequence of turns produces records BYTE-IDENTICAL to the pre-change code: the sha256 of
    the OFF records is pinned to the value computed on the base commit 159c7d2b (this test file's own fixture, run there
    before this module existed); with the switch ON, stripping the address fields gives the same sha256.
Standard library only; no network; one process."""
from __future__ import annotations

import hashlib
import json
import os
import re
import unittest
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
import helm_test_pins as PINS                 # the one machine-neutral canonicalizer for record pins (SPEC 7.106 lesson)
try:
    import helm_cas_address as A
except ImportError:                                   # the fixture below also runs on the pre-change code
    A = None

#: sha256 of the MACHINE-NEUTRAL canon (helm_test_pins.canon) of fixture_records() with CAS_ADDRESS OFF and WIDE_UNITS_NOTE OFF.
#: History: the first pin (56f356ea...) hashed the raw records, which carry the licensed brain folder as an ABSOLUTE PATH
#: (trace[].brain.brain_dir); it held on the laptop (Windows) and failed on the Linux host in job c53 (SPEC 7.106). Since
#: 2026-10-21 the pin is taken over helm_test_pins.canon, which replaces absolute paths by their last component, so the same
#: records hash alike on every machine; test_helm_pin_hygiene.py enforces this for every record pin. Recompute (OFF code
#: unchanged since base 159c7d2b): python -c "import test_helm_cas_address as T; print(T.fixture_sha256())"
PINNED_OFF_SHA256 = "632bffc062804840c1c5d2699e81cd365d751799359ee5828efe46593ae51955"

FIXTURE_TURNS = [
    ("batch", ("Bread", {"Flour": 10, "Water": 8}, 5, "Flour")),
    ("turn", "There is 12 of Ω_Flour."),
    ("turn", "Topic: Ω_Bread."),
    ("turn", "There is 9 of Ω_Water."),
    ("turn", "Topic: Ω_Bread."),
    ("turn", "We made 1 scone from 2 cups flour and 1 cup cream and ran out of cream."),
    ("turn", "We have 4 cups flour and 3 cups cream."),
    ("turn", "How many scones can we make?"),
    ("turn", "We made 1 scone from 2 cups flour and 1 cup cream and ran out of flour."),
    ("turn", "How many scones can we make?"),
    ("turn", "We have 2 or 3 cups sugar."),
    ("turn", "We made 2 scones from 2 cups flour and 1 cup cream and ran out of flour."),
    ("turn", "What is the weather like?"),
]


def _canon(obj):
    return PINS.canon(obj)                    # sorted, compact, machine-neutral (absolute paths -> last component)


def fixture_records():
    """Run FIXTURE_TURNS on one loop (whatever the switches say) and return every record it wrote."""
    import helm_end_to_end_loop as E
    loop = E.HELMEndToEndLoop()
    results = []
    for tick, (kind, arg) in enumerate(FIXTURE_TURNS, start=1):
        if kind == "batch":
            results.append(loop.witness_batch(*arg, tick=tick))
        else:
            results.append(loop.process_turn(arg, tick=tick))
    store = list(loop.cube_store.write_history) if loop.cube_store is not None else None
    wide = loop.wide_book.learned_digest() if getattr(loop, "wide_book", None) is not None else None
    return {"results": results, "trace": loop.trace, "store_write_history": store,
            "licensed_digest": loop.brain.brain.learned_digest(), "wide_digest": wide}


def fixture_sha256(records=None):
    return PINS.canon_sha256(records if records is not None else fixture_records())


@contextmanager
def switches(cas=None, units_note=None):
    """Set the two environment switches for one block; restore after. None = unset (the default)."""
    keys = {"HELM_CAS_ADDRESS": cas, "HELM_WIDE_UNITS_NOTE": units_note}
    old = {k: os.environ.get(k) for k in keys}
    try:
        for k, v in keys.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, obj


class A_Canon(unittest.TestCase):
    def test_canonical_names_and_counts(self):
        self.assertEqual(list(A.FOUNDATIONS), ["F1", "F2", "F3", "F4", "F5", "F6", "F7"])
        self.assertEqual(list(A.FOUNDATIONS.values()),
                         ["Unity", "Wisdom", "Vitality", "Connection", "Agency", "Structure", "Purpose"])
        self.assertEqual(list(A.DOMAINS), ["P", "C", "E", "O"])
        self.assertEqual(list(A.REGISTERS), ["T", "A", "f", "E"])
        self.assertEqual(len(A.PATHWAYS), 22)
        self.assertEqual(A.PATHWAYS[0], "A0")
        self.assertEqual(A.PATHWAYS[1:8], tuple(f"D{i}" for i in range(1, 8)))
        self.assertEqual(len(A.CELLS), 28)
        self.assertEqual(len(A.ELEMENTS), 40)
        self.assertEqual(list(A.NOETICS.values()), ["Idea", "Mind", "Positive", "Negative", "Vibration", "Female",
                                                    "Male", "Rhythm", "Above/Cause", "Below/Effect"])
        self.assertIn("F2C", A.CELLS)
        self.assertIn("^8C", A.ELEMENTS)

    def test_every_rule_has_a_sentence(self):
        for rid in ("FND-1", "FND-2", "DOM-1", "DOM-2", "DOM-3", "CELL-1", "REG-1a", "REG-1b", "REG-1c", "REG-1d",
                    "PATH-1", "ELE-1"):
            self.assertTrue(A.RULES[rid])
        print("\n[helm_cas_address] rules:", json.dumps(A.RULES, indent=1))


class B_Rules(unittest.TestCase):
    def test_nothing_known_is_all_untagged(self):
        a = A.address({})
        for k in A.FIELDS:
            self.assertEqual(a[k], A.UNTAGGED)
            self.assertEqual(a["how"][k], A.UNTAGGED)
        self.assertEqual(a["schema"], "cas_address/1")
        self.assertEqual(A.read_address({"no": "address"}), A.untagged())
        self.assertEqual(A.read_address(None), A.untagged())

    def test_fnd_1_fnd_2(self):
        self.assertEqual(A.foundation_of({"foundation": "F3"}), ("F3", "FND-1"))
        self.assertEqual(A.foundation_of({"drive": "Vitality"}), ("F3", "FND-1"))
        self.assertEqual(A.foundation_of({"filed_at": "F7"}), ("F7", "FND-1"))
        self.assertEqual(A.foundation_of({"foundation": "F8"}), (A.UNTAGGED, A.UNTAGGED))   # not a Drive
        self.assertEqual(A.foundation_of({"source": "unity_eye"}), ("F1", "FND-2"))
        self.assertEqual(A.foundation_of({}, kind="unity_eye"), ("F1", "FND-2"))
        self.assertEqual(A.foundation_of({"status": "WITNESS_ADMITTED"}), (A.UNTAGGED, A.UNTAGGED))

    def test_dom_1_words(self):
        cases = {"TEACH_REFUSED_RECEIPT_FAILED": "P", "REFUSE_NOT_VERIFIED": "P", "AGENTIC_PLAN_CLAMPED": "P",
                 "WITNESS_ADMITTED": "C", "SUCCESS_EVALUATED": "C", "EVALUATED": "C", "UNDETERMINED_CLARIFY": "C",
                 "AGENTIC_PLAN_EXECUTED": "C", "WIDE_NOT_MINE": "C", "ADMITTED": "C",
                 "CLARIFY_STOCK_NOT_RECORDED": "C", "CLARIFY_WIDE_NO_AMOUNT": "C", "NO_AMOUNT": "C",
                 "AMOUNT_IS_A_RANGE": "C", "UNIT_NOT_IN_TABLE": "C",
                 "VERIFIED_NO_RECIPE_CONTENT": "E", "READ_COMPLETED": "E",
                 "INVENTORY_RECORDED": "O", "STOCK_RECORDED": "O", "WITNESS": "O", "STOCK": "O",
                 "NOTHING_TO_SAVE": A.UNTAGGED, "REPAIRED_RETEACH_NEEDED": A.UNTAGGED,
                 "STATED_RECIPE_NOT_TAKEN": A.UNTAGGED}
        for word, dom in cases.items():
            self.assertEqual(A.domain_of_word(word)[0], dom, word)
        self.assertEqual(A.domain_of_word(None), (A.UNTAGGED, A.UNTAGGED))
        self.assertTrue(A.domain_of_word("REFUSED_X")[1].startswith("DOM-1a"))

    def test_dom_2_kinds_and_dom_3_stations(self):
        for kind, dom in (("stock", "O"), ("cube_write", "O"), ("lesson", "C"), ("verdict", "E"), ("gate", "P")):
            self.assertEqual(A.domain_of({}, kind=kind), (dom, f"DOM-2 kind {kind}"))
        self.assertEqual(A.domain_of({}, kind="unknown_kind"), (A.UNTAGGED, A.UNTAGGED))
        for station, dom in (("CCE skin", "E"), ("S1 trigger ^8", "C"), ("S2 Bias ^5", "O"), ("S3 arrival ^9", "E"),
                             ("S5 RPM link", "P"), ("English in (wide)", "C"), ("S0 atlas head", "C"),
                             ("outside circuit", "O")):
            self.assertEqual(A.domain_of({}, station=station), (dom, f"DOM-3 station {station}"))
        self.assertEqual(A.domain_of({"what": "cube_write"}, station="store")[0], "O")
        self.assertEqual(A.domain_of({"what": "eta_eps_receipt"}, station="store")[0], "E")
        self.assertEqual(A.domain_of({"what": "something_else"}, station="store")[0], A.UNTAGGED)
        self.assertEqual(A.domain_of({"loop_status": "STOCK_RECORDED"}, station="S6 next")[0], "O")
        self.assertEqual(A.domain_of({"what": "writer", "record": {"reason": "ADMITTED"}}, station="brain")[0], "C")
        for station in ("user", "header", "S4 operating point", "never heard of"):
            self.assertEqual(A.domain_of({"status": "STOCK"}, station=station), (A.UNTAGGED, A.UNTAGGED), station)

    def test_cell_1_needs_both(self):
        self.assertEqual(A.address({"foundation": "F2", "status": "WITNESS_ADMITTED"})["cell"], "F2C")
        self.assertEqual(A.address({"foundation": "F2"})["cell"], A.UNTAGGED)
        self.assertEqual(A.address({"status": "WITNESS_ADMITTED"})["cell"], A.UNTAGGED)
        a = A.address({"foundation": "F5", "loop_status": "STOCK_RECORDED"})
        self.assertEqual((a["cell"], a["how"]["cell"]), ("F5O", "CELL-1"))
        self.assertIn(a["cell"], A.CELLS)

    def test_reg_1(self):
        self.assertEqual(A.register_of({"loop_status": "CLARIFY_WIDE_FACE_NOT_HELD"}), ("f", A.REG_1_TABLE[0][2]))
        self.assertEqual(A.register_of({"reason": "REFUSED_PURPOSE_ABSENT"})[0], "f")   # a purpose clause first
        self.assertEqual(A.register_of({"loop_status": "TEACH_REFUSED_CONFLICT"})[0], "A")
        self.assertEqual(A.register_of({"loop_status": "AGENTIC_PLAN_EXECUTED"})[0], "A")
        self.assertEqual(A.register_of({"loop_status": "STOCK_RECORDED"})[0], "E")
        self.assertEqual(A.register_of({"loop_status": "WITNESS_ADMITTED"})[0], "E")
        self.assertEqual(A.register_of({"loop_status": "SUCCESS_EVALUATED"}), (A.UNTAGGED, A.UNTAGGED))
        self.assertEqual(A.register_of({}, kind="ruling")[0], "T")
        self.assertEqual(A.register_of({}, kind="stock")[0], "E")
        self.assertEqual(A.register_of({}, station="S5 RPM link")[0], "A")
        self.assertEqual(A.register_of({}, station="S2 Bias ^5")[0], "E")
        # a reader's row is a reading whatever it read: no register from the sentence's own status word
        self.assertEqual(A.register_of({"status": "STOCK"}, station="English in (wide)"), (A.UNTAGGED, A.UNTAGGED))

    def test_path_1_only_a_named_node(self):
        self.assertEqual(A.pathway_of({"pathway_node": "W3"}), ("W3", "PATH-1"))
        self.assertEqual(A.pathway_of({"pathway": "A0"}), ("A0", "PATH-1"))
        self.assertEqual(A.pathway_of({"pathway": "X9"}), (A.UNTAGGED, A.UNTAGGED))
        self.assertEqual(A.pathway_of({"loop_status": "WITNESS_ADMITTED"}), (A.UNTAGGED, A.UNTAGGED))

    def test_ele_1_only_a_named_noetic_with_a_domain(self):
        self.assertEqual(A.element_of({}, "C", station="S1 trigger ^8"), ("^8C", "ELE-1"))
        self.assertEqual(A.element_of({}, "O", station="S2 Bias ^5"), ("^5O", "ELE-1"))
        self.assertEqual(A.element_of({}, A.UNTAGGED, station="S1 trigger ^8"), (A.UNTAGGED, A.UNTAGGED))
        self.assertEqual(A.element_of({"noetic": 3}, "P"), ("^3P", "ELE-1"))
        self.assertEqual(A.element_of({"noetic": "^9"}, "E"), ("^9E", "ELE-1"))
        self.assertEqual(A.element_of({"noetic": True}, "E"), (A.UNTAGGED, A.UNTAGGED))
        self.assertEqual(A.element_of({"status": "STOCK"}, "O"), (A.UNTAGGED, A.UNTAGGED))
        for e in ("^8C", "^5O", "^3P", "^9E"):
            self.assertIn(e, A.ELEMENTS)

    def test_without_address_strips_nested_and_copies(self):
        rec = {"a": 1, "address": {"x": 1}, "inner": {"address": 2, "b": [{"address": 3, "c": 4}]}}
        out = A.without_address(rec)
        self.assertEqual(out, {"a": 1, "inner": {"b": [{"c": 4}]}})
        self.assertIn("address", rec)                   # the original is untouched

    def test_filed_item_and_histogram(self):
        items = [A.address_for_filed_item({"foundation": f"F{i}", "kind": "lesson"}) for i in range(1, 8)]
        items += [A.address_for_filed_item({"foundation": "F1", "status": "STOCK_RECORDED"})] * 8
        h = A.cell_histogram(items)
        self.assertEqual(h["items"], 15)
        self.assertEqual(h["grid_28"]["F1O"], 8)
        self.assertEqual(h["grid_28"]["F3C"], 1)
        self.assertEqual(h["cells_with_8_or_more"], 1)
        self.assertEqual(h["floor_20_of_28"], "STOP_NOT_EXERCISED")
        self.assertEqual(A.cell_histogram([])["items"], 0)


class C_LoopStamps(unittest.TestCase):
    def test_switch_default_on_and_off_words(self):
        with switches(cas=None):
            self.assertTrue(A.cas_address_on())
        for w in ("0", "OFF", "off", "false", "No"):
            with switches(cas=w):
                self.assertFalse(A.cas_address_on(), w)
        with switches(cas="1"):
            self.assertTrue(A.cas_address_on())
        self.assertTrue(A.cas_address_on(True))
        self.assertFalse(A.cas_address_on(False))

    def test_every_record_stamped_when_on(self):
        with switches(cas=None):
            rec = fixture_records()
        for row in rec["trace"]:
            self.assertIn("address", row, row)
            self.assertEqual(row["address"]["schema"], "cas_address/1")
            self.assertIn(row["address"]["domain"], list(A.DOMAINS) + [A.UNTAGGED])
        for res in rec["results"]:
            self.assertEqual(res["address"]["schema"], "cas_address/1")
            self.assertEqual(res["address"], A.address_for_turn(res["loop_status"]))
            for k in ("recipe_receipt", "cube_receipt"):
                if isinstance(res[k], dict):
                    self.assertIn("address", res[k], k)
            # the S6 row of the turn carries the same word, hence the same Domain, as the turn receipt
            s6 = [r for r in rec["trace"] if r["tick"] == res["tick"] and r["station"] == "S6 next"][-1]
            self.assertEqual(s6["address"]["domain"], res["address"]["domain"])
        # the stations that name a Noetic carry an element; nothing else does
        for row in rec["trace"]:
            if row["station"] in ("S1 trigger ^8", "S2 Bias ^5", "S3 arrival ^9"):
                self.assertNotEqual(row["address"]["element"], A.UNTAGGED, row["station"])
            else:
                self.assertEqual(row["address"]["element"], A.UNTAGGED, row["station"])
        # the live loop names no Foundation: honest UNTAGGED cells (census 2's finding, now on the record)
        h = A.cell_histogram([r["address"] for r in rec["trace"]] + [r["address"] for r in rec["results"]])
        self.assertEqual(h["tagged"]["foundation"], 0)
        self.assertEqual(h["tagged"]["cell"], 0)
        self.assertGreater(h["tagged"]["domain"], 0)
        print("\n[helm_cas_address] live-loop fixture histogram:", json.dumps(h))

    def test_receipt_hash_identical_on_and_off(self):
        with switches(cas="0"):
            off = fixture_records()
        with switches(cas=None):
            on = fixture_records()
        self.assertEqual([r["receipt_hash"] for r in off["results"]], [r["receipt_hash"] for r in on["results"]])
        self.assertEqual([r["loop_status"] for r in off["results"]], [r["loop_status"] for r in on["results"]])
        self.assertEqual([r["response"] for r in off["results"]], [r["response"] for r in on["results"]])

    def test_off_is_byte_identical_to_the_pre_change_code(self):
        with switches(cas="0", units_note=None):
            off = fixture_records()
        for path, v in _walk(off):
            self.assertFalse(path.endswith("/address"), path)
        off_sha = fixture_sha256(off)
        self.assertEqual(off_sha, PINNED_OFF_SHA256, "OFF records differ from the pre-change code (base 159c7d2b)")
        with switches(cas="0", units_note="1"):      # stage 1c ON changes none of these turns either
            self.assertEqual(fixture_sha256(), PINNED_OFF_SHA256)
        with switches(cas=None, units_note="1"):     # both ON: the address is the ONLY difference
            on = fixture_records()
        self.assertNotEqual(fixture_sha256(on), PINNED_OFF_SHA256)
        self.assertEqual(fixture_sha256(A.without_address(on)), PINNED_OFF_SHA256)

    def test_tags_are_not_read_by_the_loop_or_the_wide_turn(self):
        with open(os.path.join(HERE, "helm_wide_turn.py"), encoding="utf-8") as fh:
            self.assertNotIn("address", fh.read().lower().replace("address map", ""))
        with open(os.path.join(HERE, "helm_end_to_end_loop.py"), encoding="utf-8") as fh:
            src = fh.read()
        uses = [ln.strip() for ln in src.splitlines() if "helm_cas_address" in ln]
        self.assertEqual(len(uses), 7, uses)          # import, 3 switch reads, 3 stamps/strips: nothing else
        self.assertTrue(all("cas_address_on()" in u or "address_for_trace_row" in u or "without_address" in u
                            or "stamp_turn" in u or u.startswith("import helm_cas_address") for u in uses), uses)
        self.assertNotIn("address", re.sub(r"helm_cas_address(?:\.\w+)?|address_for_trace_row|without_address|"
                                           r"stamp_turn|rec\[\"address\"\]|# .*", "", src).lower().replace("address map", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
