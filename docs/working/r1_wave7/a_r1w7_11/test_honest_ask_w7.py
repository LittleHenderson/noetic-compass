"""tests_r1w7/test_honest_ask_w7.py -- A-R1W7-11 (DESIGN_V73_A11.md T2): K4 leaves out an honest ask on a two-amount line.

Every recipe here is the AUTHOR'S OWN (DESIGN_V73_A11.md section 1 table), never an exam line. Keys come from the frozen
key function (`ns.rb.keys_rbw1t.key_item`, pantry from `ns.rb.exam_rbw1t.turns_for` with the authored multipliers 3, 3/2,
5/2) plus A-R1W7-7's `multi_qty_w7.apply`. Host records are authored in the chat harness's record shape
(r1w7/chat_harness.Dialogue.record; crash records from `chat_harness.crash_record` itself). Every scoring test calls the
REAL frozen functions through the package's own setup (`common_w7.setup`): wave 6's `score_w6.score_real` and the hooked
`score_w7.score_real(..., raw_by_id=...)` on the same inputs, and checks that every frozen total and per-item field is
unchanged by the hook (the strict count is still reported as the frozen code computes it). Reader-level tests run the
package's own reader (`merge_r1w7.read`) on the synthetic fixture with the five A-R1W7-11 plants. No HELM call except the
template tie (helm_now's `helm_wide_turn.say_wide`); no network."""
from __future__ import annotations

import copy
import importlib
import os
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))
from r1w7 import common_w7 as C  # noqa: E402
from r1w7 import chat_harness as H  # noqa: E402
from r1w7 import honest_ask_w7 as HA  # noqa: E402
from r1w7 import multi_qty_w7 as MQ  # noqa: E402
from r1w7 import score_w7 as SC  # noqa: E402

HAVE_NEIGHBOURS = all((C.neighbour_dir(n) / "PACKAGE_FREEZE.json").is_file() for n in C.NEIGHBOURS)
MULTS = (Fraction(3), Fraction(3, 2), Fraction(5, 2))
EX = "UNDETERMINED_CLARIFY"

#: the author's own recipes: name -> (dish, raw lines, the brain's name for each key line)
ITEMS = {
    "M1": ("stew", ["2 cups barley", "5 cloves, 10 juniper berries", "1 cup broth"], ["barley", "clove", "broth"]),
    "P1": ("pilaf", ["2 cups rice", "6 cloves and 12 peppercorns", "1 cup stock"], ["rice", "clove", "stock"]),
    "M2": ("stew", ["2 cups barley", "6 cloves, 12 peppercorns and 2 allspice berries", "1 cup broth"],
           ["barley", "clove", "broth"]),
    "C1": ("batter", ["3 eggs, 1 beaten", "2 cups flour", "1 cup milk"], ["egg", "flour", "milk"]),
    "C2": ("batter", ["1 cup sugar, 2 tablespoons reserved", "2 cups flour", "1 cup milk"], ["sugar", "flour", "milk"]),
    "C3": ("stew", ["2 cups flour, plus 2 tablespoons", "1 pound beef, a lean cut", "1 cup broth"], ["flour", "beef", "broth"]),
    "D2": ("cake", ["1 cup butter or", "1 cup margarine", "2 cups flour"], ["butter", "margarine", "flour"]),
}
#: the names HELM's question would hold untaught (the second amount's ingredient, or a reader's phantom for C1-C3)
UNLEARNED = {"M1": ["juniper berry"], "P1": ["peppercorn"], "M2": ["peppercorn", "allspice berry"], "C1": ["beaten"],
             "C2": ["reserved"], "C3": ["lean cut"], "D2": ["margarine"]}
#: what the frozen key + A-R1W7-7 must say for each item (section 1 table)
KEY_FACTS = {"M1": ["line1:MULTI_QTY"], "P1": ["line1:MULTI_QTY"], "M2": ["line1:MULTI_QTY"], "C1": ["line0:MULTI_QTY"],
             "C2": ["line0:MULTI_QTY"], "C3": ["line0:MULTI_QTY"], "D2": []}


def say_and(names):
    if len(names) <= 1:
        return "".join(names)
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + ", and " + names[-1]


def g1_sentence(dish, names):
    if len(names) == 1:
        need = f"one batch where {names[0]} ran out first while everything else was left over"
    else:
        need = (f"one batch for each of {say_and(names)}: a batch where that one ran out first while everything else "
                f"was left over")
    return f"I can't say yet how much {dish} we can make. I still need {need}. I didn't guess."


def missing_stock_sentence(dish, name):
    return (f"I can't say how much {dish} we can make yet, because I don't know how much {name} we have. "
            f"How much {name} is there? I didn't guess.")


def make_key(ns, name):
    dish, raw, _ = ITEMS[name]
    r = {"noun": dish, "lines": [{"raw": x, "parsed": ns.XG.parse_line(x)} for x in raw]}
    t = ns.rb.exam_rbw1t.turns_for(r, MULTS)
    key = ns.rb.keys_rbw1t.key_item({"id": "AUTHOR:" + name, "raw_lines": raw, "pantry_lines": t["pantry_lines"]})
    return MQ.apply(key, raw, ns.XG)


def loop_turn(text, status, sentence, *, value=None, limiting=None, writes=1, path="wide", kind="turn"):
    loop = {"status": status, "value": value, "limiting": limiting, "writes": writes, "cubes_written": ["c"] * writes,
            "receipt_hash": "r1" if writes else "r0", "path": path, "loop_sentence": sentence, "licensed_first": None,
            "agentic": None}
    return {"kind": kind, "text": text, "memory_recorded": True, "intent": "RECIPE_FOUNDATION_LOOP", "reply": sentence,
            "loop": loop, "cas_tokens": [], "receipt_equal": True, "cubes_have_receipt": True, "recipe_intent": True}


def log_entry(status, path, admitted=False, ingredient=None, product=None, k=0, value=None, limiting=None, writes=0):
    return {"kind": "turn", "status": status, "path": path, "admitted": admitted, "ingredient": ingredient,
            "product": product, "reason": "ADMITTED" if admitted else None, "value": value, "limiting": limiting,
            "writes": writes, "unsettled": False, "licensed_first": None, "loop_k": k, "wide_digest": "d",
            "intent": "RECIPE_FOUNDATION_LOOP"}


def lesson_record(e, q=None):
    rec = {"status": e["status"], "admitted": e["admitted"], "ingredient": e["ingredient"], "product": e["product"],
           "reason": e["reason"], "path": e["path"] or "licensed", "learned_in_taught_unit": q if e["admitted"] else None}
    if e["admitted"]:
        rec["taught_unit"] = "cup"
    return rec


def chat_record(key, name, *, status=EX, value=None, limiting=None, sentence=None, unlearned=None, qpath="wide",
                stock="STOCK_RECORDED", audit=None, products=None, extra_log=False, noise_after=False):
    """An authored CHAT record (chat_harness.Dialogue.record's shape): 3 lessons LEARNED at the key's amounts, the stock
    turn, the question turn; wide_audit = [audit_brain(...)]-shaped."""
    dish, _raw, names = ITEMS[name]
    unl = UNLEARNED[name] if unlearned is None else unlearned
    sentence = g1_sentence(dish, unl) if sentence is None else sentence
    prods = products or [dish] * len(names)
    turns, log, lrs = [], [], []
    for j, (nm, kl) in enumerate(zip(names, key["lessons"])):
        turns.append(loop_turn(f"We made 1 {dish} (lesson {j}).", "WITNESS_ADMITTED", f"Got it: {nm}."))
        e = log_entry("WITNESS_ADMITTED", "wide", True, nm, prods[j], j, writes=1)
        log.append(e)
        lrs.append(lesson_record(e, kl["q"]))
    turns.append(loop_turn("We have some of everything.", stock, "Noted."))
    log.append(log_entry(stock, "wide", k=len(names), writes=1))
    lrs.append(lesson_record(log[-1]))
    writes = 1 if status == "SUCCESS_EVALUATED" else 0
    turns.append(loop_turn(f"How much {dish} can we make?", status, sentence, value=value, limiting=limiting,
                           writes=writes, path=qpath))
    log.append(log_entry(status, qpath, k=len(names) + 1, value=value, limiting=limiting, writes=writes))
    lrs.append(lesson_record(log[-1]))
    if extra_log:
        log.append(log_entry("STOCK_RECORDED", "wide", k=len(names) + 2))
    if noise_after:
        turns.append(dict(loop_turn("Thanks, that's helpful.", "NOT_ROUTED", "Glad to help.", kind="noise"), loop=None))
    rec = {"id": key["id"], "family": "REAL", "rung": None, "n_lessons": len(names), "turns": turns, "log": log,
           "lesson_records": lrs,
           "scored_turn": {"status": status, "value": value, "limiting": limiting, "writes": writes,
                           "inner_status": status, "routed": True},
           "scored_reply": sentence, "scored_intent": "RECIPE_FOUNDATION_LOOP", "scored_cas_tokens": [], "plain": True,
           "noise_turns": [t for t in turns if t["kind"] == "noise"], "receipt_inconsistent_turns": 0,
           "receipt_problems": []}
    if audit != "MISSING":
        rec["wide_audit"] = audit if audit is not None else [
            {"numbers_are_coefficients": True, "coefficients": len(names), "support_slots": len(names) + len(unl),
             "within_support": True, "factors_pinned": True, "attributes_ok": True, "extra_numbers": 0, "ok": True}]
    return rec


def not_routed_record(key, name, intent="GENERAL_KNOWLEDGE_INQUIRY"):
    rec = chat_record(key, name)
    rec["turns"][-1]["loop"] = None
    rec["turns"][-1]["intent"] = intent
    rec["log"][-1] = dict(log_entry("NOT_ROUTED_TO_LOOP:" + intent, None, k=None), intent=intent)
    rec["lesson_records"][-1] = lesson_record(rec["log"][-1])
    rec["scored_turn"] = {"status": "NOT_ROUTED_TO_LOOP:" + intent, "value": None, "limiting": None, "writes": 0,
                          "inner_status": None, "routed": False}
    return rec


def loop_on_record(rec):
    """wave 3's turn shape (the LOOP_ON arm): no `kind`; the sentence sits in `reply_adapter`."""
    out = copy.deepcopy(rec)
    out["turns"] = [{"status": (t.get("loop") or {}).get("status"), "output_value": (t.get("loop") or {}).get("value"),
                     "limiting": (t.get("loop") or {}).get("limiting"), "writes": (t.get("loop") or {}).get("writes", 0),
                     "reply": t.get("reply"), "reply_adapter": t.get("reply")} for t in rec["turns"] if t["kind"] == "turn"]
    out["scored_turn"] = {k: v for k, v in rec["scored_turn"].items() if k != "routed"}
    return out


@unittest.skipUnless(HAVE_NEIGHBOURS, "neighbours not present")
class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = C.setup(helm=False)
        cls.HV = C.load_helm_voice()
        cls.keys = {n: make_key(cls.ns, n) for n in ITEMS}

    def key(self, name, iid=None):
        k = copy.deepcopy(self.keys[name])
        k["id"] = iid or k["id"]
        return k

    def score(self, rows, raw="all"):
        """rows: [(item name, record)] (ids from the records). Runs the frozen wave-6 score_real and the hooked wave-7
        score_real on the same inputs; asserts every frozen total and per-item field is unchanged by the hook."""
        keys, inputs, recs, raw_by_id = [], [], [], {}
        for name, rec in rows:
            k = self.key(name, rec["id"])
            keys.append(k)
            inputs.append({"id": rec["id"], "n_lessons": len(ITEMS[name][2]), "cell": "AUTHOR"})
            recs.append(rec)
            raw_by_id[rec["id"]] = list(ITEMS[name][1])
        doc = {"records": recs}
        frozen = self.ns.SC6.score_real(self.ns, keys, inputs, doc)
        rb = raw_by_id if raw == "all" else raw
        hooked = SC.score_real(self.ns, self.HV, keys, inputs, doc, True, raw_by_id=rb)
        for k, v in frozen["totals"].items():
            self.assertEqual(hooked["totals"][k], v, f"frozen total {k} changed by the hook")
        self.assertEqual(len(frozen["per_item"]), len(hooked["per_item"]))
        for a, b in zip(frozen["per_item"], hooked["per_item"]):
            for k, v in a.items():
                self.assertEqual(b[k], v, f"frozen per-item field {k} changed by the hook")
        return frozen, hooked

    def row(self, hooked, iid):
        rows = [r for r in hooked["a11_checks"] if r["id"] == iid]
        self.assertEqual(len(rows), 1, (iid, hooked["a11_checks"]))
        return rows[0]

    def one(self, name, rec, raw="all"):
        """Score one item; returns (frozen totals, hooked totals, hooked out)."""
        f, h = self.score([(name, rec)], raw)
        return f["totals"], h["totals"], h


class A_KeysFromTheFrozenFunction(Base):
    def test_authored_keys_are_what_the_design_table_says(self):
        for name, tags in KEY_FACTS.items():
            with self.subTest(item=name):
                k = self.keys[name]
                self.assertEqual(k["answer"]["key"], "ANSWER", k["answer"])
                self.assertEqual(Fraction(k["answer"]["yield"]), Fraction(3, 2))
                self.assertEqual(k["answer"]["limiting_index"], 1)
                self.assertEqual([w for w in k["representable"]["why_not"] if w.endswith(":MULTI_QTY")], tags)
                self.assertEqual(HA.tagged_lines(k), [int(t[4]) for t in tags])

    def test_tail_heads_and_allowed_heads_with_the_frozen_grammar(self):
        G, RC = self.ns.XG, self.ns.rb.common_rbw1t
        self.assertEqual(HA.tail_heads("5 cloves, 10 juniper berries", G), ["berries"])
        self.assertEqual(HA.tail_heads("6 cloves, 12 peppercorns and 2 allspice berries", G), ["peppercorns", "berries"])
        self.assertEqual(HA.tail_heads("3 eggs, 1 beaten", G), ["beaten"])
        self.assertEqual(HA.tail_heads("2 1/2 cups flour", G), [])
        self.assertEqual(HA.tail_heads("1 cup milk (about 240 ml)", G), [])
        self.assertEqual(HA.allowed_heads(self.keys["M1"], ITEMS["M1"][1], G, RC), ["berry"])
        self.assertEqual(HA.allowed_heads(self.keys["P1"], ITEMS["P1"][1], G, RC), ["peppercorn"])
        self.assertEqual(HA.allowed_heads(self.keys["M2"], ITEMS["M2"][1], G, RC), ["berry", "peppercorn"])
        for name in ("C1", "C2", "C3", "D2"):                      # participle, deny word, unit word, untagged
            self.assertEqual(HA.allowed_heads(self.keys[name], ITEMS[name][1], G, RC), [], name)


class B_HonestAskIsExempted(Base):
    def test_honest_ask_m1(self):
        k = self.key("M1")
        ft, ht, h = self.one("M1", chat_record(k, "M1"))
        self.assertEqual((ft["ASKS"], ft["unexplained_asks_strict"]), (1, 1))          # the frozen rule counts it
        self.assertEqual(ht["unexplained_asks_strict"], 1)                              # still reported, unchanged
        self.assertEqual((ht["a11_strict_recount"], ht["unexplained_asks_strict_after_a11"]), (1, 0))
        self.assertIs(ht["a11_consistent"], True)
        self.assertEqual(h["a11_exempted_ids"], ["AUTHOR:M1"])
        r = self.row(h, "AUTHOR:M1")
        self.assertEqual({c: r[c] for c in HA.CHECKS}, {"a": True, "b": True, "c": True, "d": True, "e": True})
        self.assertEqual((r["tagged_lines"], r["unlearned"], r["allowed_tail_heads"]), ([1], ["juniper berry"], ["berry"]))
        self.assertIs(r["raw_lines_found"], True)
        self.assertNotIn("error", r)
        self.assertEqual([p["a11_exempt"] for p in h["per_item"]], [True])
        self.assertEqual(h["per_item"][0]["q"], "ASKS")                                 # the question score is untouched

    def test_honest_ask_p1_the_c56_shape(self):
        k = self.key("P1")
        _ft, ht, h = self.one("P1", chat_record(k, "P1"))
        self.assertEqual(h["a11_exempted_ids"], ["AUTHOR:P1"])
        self.assertEqual((ht["unexplained_asks_strict"], ht["unexplained_asks_strict_after_a11"]), (1, 0))
        self.assertEqual(self.row(h, "AUTHOR:P1")["unlearned"], ["peppercorn"])

    def test_two_names_exempted_and_a_count_of_three_is_not(self):
        k = self.key("M2")
        _ft, ht, h = self.one("M2", chat_record(k, "M2"))
        self.assertEqual(h["a11_exempted_ids"], ["AUTHOR:M2"])
        self.assertEqual(self.row(h, "AUTHOR:M2")["unlearned"], ["peppercorn", "allspice berry"])
        audit = [{"ok": True, "coefficients": 3, "support_slots": 6}]                  # 3 untaught slots, 2 names
        _ft, ht, h = self.one("M2", chat_record(k, "M2", audit=audit))
        self.assertEqual(h["a11_exempted_ids"], [])
        self.assertIs(self.row(h, "AUTHOR:M2")["d"], False)
        self.assertEqual(ht["unexplained_asks_strict_after_a11"], 1)

    def test_noise_turn_after_the_question_does_not_hide_the_sentence(self):
        k = self.key("M1")
        _ft, _ht, h = self.one("M1", chat_record(k, "M1", noise_after=True))
        self.assertEqual(h["a11_exempted_ids"], ["AUTHOR:M1"])

    def test_loop_on_shape_exempted_reported_only(self):
        k = self.key("M1")
        rec = loop_on_record(chat_record(k, "M1"))
        self.assertTrue(all("kind" not in t for t in rec["turns"]))
        _ft, ht, h = self.one("M1", rec)
        self.assertEqual(h["a11_exempted_ids"], ["AUTHOR:M1"])
        self.assertEqual(ht["unexplained_asks_strict_after_a11"], 0)


class C_PhantomsAndOtherSentencesAreNotExempted(Base):
    def test_phantom_c1_c2_c3(self):
        for name in ("C1", "C2", "C3"):
            with self.subTest(item=name):
                k = self.key(name)
                ft, ht, h = self.one(name, chat_record(k, name))
                self.assertEqual(ft["unexplained_asks_strict"], 1)
                self.assertEqual((ht["unexplained_asks_strict"], ht["unexplained_asks_strict_after_a11"]), (1, 1))
                self.assertEqual(h["a11_exempted_ids"], [])
                r = self.row(h, k["id"])
                self.assertEqual({c: r[c] for c in HA.CHECKS}, {"a": True, "b": True, "c": True, "d": True, "e": False})
                self.assertEqual(r["allowed_tail_heads"], [])
                self.assertIs(ht["a11_consistent"], True)

    def test_missing_stock_sentence_is_not_exempted(self):
        k = self.key("M1")
        rec = chat_record(k, "M1", sentence=missing_stock_sentence("stew", "broth"))
        _ft, ht, h = self.one("M1", rec)
        self.assertEqual(h["a11_exempted_ids"], [])
        r = self.row(h, "AUTHOR:M1")
        self.assertEqual((r["c"], r["d"], r["e"]), (True, False, None))
        self.assertEqual(ht["unexplained_asks_strict_after_a11"], 1)

    def test_each_c_and_d_failure_alone(self):
        k = self.key("M1")
        cases = {
            "path licensed": (dict(qpath="licensed"), "c"),
            "len(log) != n + 2": (dict(extra_log=True), "c"),
            "wide_audit missing": (dict(audit="MISSING"), "d"),
            "wide_audit two entries": (dict(audit=[{"ok": True, "coefficients": 3, "support_slots": 4}] * 2), "d"),
            "wide_audit a dict": (dict(audit={"ok": True, "coefficients": 3, "support_slots": 4}), "d"),
            "wide_audit ok False": (dict(audit=[{"ok": False, "coefficients": 3, "support_slots": 4}]), "d"),
            "coefficients 2": (dict(audit=[{"ok": True, "coefficients": 2, "support_slots": 3}]), "d"),
            "support_slots 3": (dict(audit=[{"ok": True, "coefficients": 3, "support_slots": 3}]), "d"),
            "two lesson products": (dict(products=["stew", "soup", "stew"]), "d"),
            "sentence dish is not the lesson dish": (dict(sentence=g1_sentence("soup", ["juniper berry"])), "d"),
        }
        for label, (kw, failing) in cases.items():
            with self.subTest(case=label):
                ft, ht, h = self.one("M1", chat_record(k, "M1", **kw))
                self.assertEqual(ft["unexplained_asks_strict"], 1, label)                 # (b) still holds
                self.assertEqual(h["a11_exempted_ids"], [], label)
                r = self.row(h, "AUTHOR:M1")
                self.assertIs(r["b"], True, label)
                self.assertIs(r[failing], False, label)
                self.assertEqual(ht["unexplained_asks_strict_after_a11"], 1, label)


class D_WrongRightAndUntagged(Base):
    def test_tagged_wrong_number_stays_wrong_and_fails_k3(self):
        k = self.key("M1")
        rec = chat_record(k, "M1", status="SUCCESS_EVALUATED", value="1/2", limiting="clove",
                          sentence="With what's on hand we can make 1/2 stew. Clove runs out first, so it sets the limit.")
        ft, ht, h = self.one("M1", rec)
        self.assertEqual(h["per_item"][0]["q"], "WRONG")
        self.assertEqual((ft["WRONG"], ht["WRONG"]), (1, 1))                               # K3 reads WRONG == 0: it fails
        self.assertEqual((ht["unexplained_asks_strict"], ht["unexplained_asks_strict_after_a11"]), (0, 0))
        self.assertEqual(h["a11_exempted_ids"], [])
        self.assertIs(self.row(h, "AUTHOR:M1")["b"], False)
        self.assertIs(h["per_item"][0]["a11_exempt"], False)

    def test_tagged_right_number_is_right_and_nothing_exempted(self):
        k = self.key("M1")
        rec = chat_record(k, "M1", status="SUCCESS_EVALUATED", value="3/2", limiting="clove",
                          sentence="With what's on hand we can make 1 1/2 stew. Clove runs out first, so it sets the limit.")
        _ft, ht, h = self.one("M1", rec)
        self.assertEqual(h["per_item"][0]["q"], "RIGHT")
        self.assertEqual(ht["RIGHT"], 1)
        self.assertEqual(h["a11_exempted_ids"], [])
        self.assertEqual(ht["unexplained_asks_strict_after_a11"], 0)

    def test_untagged_honest_looking_ask_is_not_exempted(self):
        k = self.key("D2")
        self.assertEqual(HA.tagged_lines(k), [])
        rec = chat_record(k, "D2")
        _ft, ht, h = self.one("D2", rec)
        self.assertEqual((ht["unexplained_asks_strict"], ht["unexplained_asks_strict_after_a11"]), (1, 1))
        self.assertEqual(h["a11_checks"], [])                                              # rows only for tagged keys
        self.assertIs(HA.honest_ask(self.ns, k, rec, 3, ITEMS["D2"][1])["a"], False)


class E_ReaderAndClarifyAsksAreNotExempted(Base):
    def test_reader_clarify_routing_and_brain_statuses(self):
        k = self.key("M1")
        for status in ("CLARIFY_WIDE_FACE_UNKNOWN_INGREDIENT", "BRAIN_UNDETERMINED", "UNDETERMINED_UNKNOWN_PRODUCT",
                       "CLARIFY_WIDE_ALTERNATIVE_WHICH_ONE", "CLARIFY_WIDE_RAN_OUT_WHICH_LINE", "CLARIFY_ENGLISH_UNKNOWN_PRODUCT"):
            with self.subTest(status=status):
                ft, ht, h = self.one("M1", chat_record(k, "M1", status=status))
                self.assertEqual(ft["unexplained_asks_strict"], 1)                         # the frozen rule counts it
                self.assertEqual(ht["unexplained_asks_strict_after_a11"], ht["unexplained_asks_strict"])
                self.assertEqual(h["a11_exempted_ids"], [])
                self.assertIs(self.row(h, "AUTHOR:M1")["c"], False)
        rec = not_routed_record(k, "M1")
        ft, ht, h = self.one("M1", rec)
        self.assertEqual(ft["unexplained_asks_strict"], 1)
        self.assertEqual((ht["unexplained_asks_strict_after_a11"], h["a11_exempted_ids"]), (1, []))
        self.assertIs(self.row(h, "AUTHOR:M1")["c"], False)

    def test_licensed_path_undetermined_is_not_exempted(self):
        k = self.key("M1")
        _ft, ht, h = self.one("M1", chat_record(k, "M1", qpath="licensed"))
        self.assertEqual((ht["unexplained_asks_strict_after_a11"], h["a11_exempted_ids"]), (1, []))


class F_RawLinesAndRecordShapes(Base):
    def test_raw_lines_missing(self):
        k = self.key("M1")
        for raw in (None, {}, {"AUTHOR:other": ITEMS["M1"][1]}):
            with self.subTest(raw=raw):
                _ft, ht, h = self.one("M1", chat_record(k, "M1"), raw=raw)
                self.assertEqual(h["a11_exempted_ids"], [])
                r = self.row(h, "AUTHOR:M1")
                self.assertIs(r["raw_lines_found"], False)
                self.assertEqual((r["d"], r["e"]), (True, False))
                self.assertEqual(ht["unexplained_asks_strict_after_a11"], 1)

    def test_default_call_without_raw_lines_exempts_nothing(self):
        k = self.key("M1")
        rec = chat_record(k, "M1")
        out = SC.score_real(self.ns, self.HV, [k], [{"id": k["id"], "n_lessons": 3}], {"records": [rec]}, True)
        self.assertEqual((out["totals"]["unexplained_asks_strict"], out["totals"]["unexplained_asks_strict_after_a11"]),
                         (1, 1))

    def test_record_shapes_never_raise(self):
        k = self.key("M1")
        always = {"id": k["id"], "family": "REAL", "turns": [{"status": "CLARIFY_ALWAYS_ASK", "reply_adapter": "?"}],
                  "always_ask": True, "log": [], "lesson_records": [],
                  "scored_turn": {"status": "CLARIFY_ALWAYS_ASK", "value": None, "limiting": None, "writes": 0}}
        crash = H.crash_record({"id": k["id"], "family": "REAL"}, RuntimeError("authored crash"), [])
        w6crash = chat_record(k, "M1")
        del w6crash["scored_turn"]
        w6crash["crashed"] = True
        turns_dict = chat_record(k, "M1")
        turns_dict["turns"] = {"not": "a list"}
        log_none = chat_record(k, "M1")
        log_none["log"] = None
        for label, rec, want_b, want_c in (("ALWAYS_ASK", always, False, None), ("chat crash", crash, False, None),
                                           ("wave-6 crash", w6crash, True, False), ("turns a dict", turns_dict, True, True),
                                           ("log None", log_none, False, None)):
            with self.subTest(shape=label):
                _ft, ht, h = self.one("M1", rec)
                r = self.row(h, "AUTHOR:M1")
                self.assertIs(r["exempt"], False)
                self.assertNotIn("error", r)
                self.assertIs(r["b"], want_b)
                self.assertIs(r["c"], want_c)
                self.assertEqual(h["a11_exempted_ids"], [])
                self.assertIs(ht["a11_consistent"], True)
        r = HA.honest_ask(self.ns, k, turns_dict, 3, ITEMS["M1"][1])
        self.assertIs(r["d"], False)                                                          # no sentence to read

    def test_garbage_inputs_never_raise(self):
        k = self.key("M1")
        rec = chat_record(k, "M1")
        for args in ((None, rec, 3, []), ("x", rec, 3, None), (k, None, 3, None), (k, "x", 3, None), (k, rec, "3", None),
                     (k, rec, -1, None), (k, rec, True, None), (k, {"log": 5, "lesson_records": 7}, 3, None),
                     ({"answer": {"key": "ANSWER"}, "representable": {"why_not": ["line0:MULTI_QTY"]}}, rec, 3, 5)):
            with self.subTest(args=repr(args)[:60]):
                r = HA.honest_ask(self.ns, *args)
                self.assertIs(r["exempt"], False)


class G_ConsistencyOnAMixedSet(Base):
    def test_recount_equals_frozen_strict_and_after_is_strict_minus_exempted(self):
        km = self.key("M1")
        rows = [("M1", dict(chat_record(km, "M1"), id="X:M1")),
                ("P1", dict(chat_record(self.key("P1"), "P1"), id="X:P1")),
                ("M2", dict(chat_record(self.key("M2"), "M2"), id="X:M2")),
                ("C1", dict(chat_record(self.key("C1"), "C1"), id="X:C1")),
                ("C3", dict(chat_record(self.key("C3"), "C3"), id="X:C3")),
                ("D2", dict(chat_record(self.key("D2"), "D2"), id="X:D2")),
                ("M1", dict(chat_record(km, "M1", status="SUCCESS_EVALUATED", value="1/2", limiting="clove"), id="X:M1W")),
                ("M1", dict(chat_record(km, "M1", status="SUCCESS_EVALUATED", value="3/2", limiting="clove"), id="X:M1R")),
                ("M1", dict(chat_record(km, "M1", status="CLARIFY_WIDE_FACE_UNKNOWN_INGREDIENT"), id="X:M1C")),
                ("M1", dict(chat_record(km, "M1", sentence=missing_stock_sentence("stew", "broth")), id="X:M1S")),
                ("M1", dict(loop_on_record(chat_record(km, "M1")), id="X:M1L"))]
        f, h = self.score(rows)
        t = h["totals"]
        b_ids = sorted(r["id"] for r in h["a11_checks"] if r["b"] is True)
        self.assertEqual(f["totals"]["unexplained_asks_strict"], 9)    # every ask except the wrong and the right number
        self.assertEqual(t["a11_strict_recount"], f["totals"]["unexplained_asks_strict"])
        self.assertEqual(h["a11_exempted_ids"], ["X:M1", "X:M1L", "X:M2", "X:P1"])
        self.assertTrue(set(h["a11_exempted_ids"]) <= set(b_ids))
        self.assertEqual(t["unexplained_asks_strict_after_a11"], t["unexplained_asks_strict"] - len(h["a11_exempted_ids"]))
        self.assertGreaterEqual(t["unexplained_asks_strict_after_a11"], 0)
        self.assertIs(t["a11_consistent"], True)
        self.assertEqual((t["WRONG"], t["RIGHT"]), (1, 1))
        self.assertEqual(sorted(p["id"] for p in h["per_item"] if p["a11_exempt"]), h["a11_exempted_ids"])

    def test_an_inconsistent_recount_reads_false(self):
        k = self.key("M1")
        rec = chat_record(k, "M1")
        out = {"totals": {"unexplained_asks_strict": 2}, "per_item": [{"id": k["id"]}]}
        HA.apply(self.ns, out, [k], [{"id": k["id"], "n_lessons": 3}], {"records": [rec]}, {k["id"]: ITEMS["M1"][1]})
        self.assertEqual(out["totals"]["a11_strict_recount"], 1)
        self.assertIs(out["totals"]["a11_consistent"], False)


@unittest.skipUnless(HAVE_NEIGHBOURS, "neighbours not present")
class H_TemplateTie(unittest.TestCase):
    """The frozen sentence patterns against the package's own helm_now `helm_wide_turn.say_wide` (DESIGN 3.2 limit 3)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.old = os.environ.get(C.SESSION_DIR_ENV)
        os.environ[C.SESSION_DIR_ENV] = str(Path(cls.tmp.name) / "sessions")
        cls.ns = C.setup()
        cls.WT = importlib.import_module("helm_wide_turn")

    @classmethod
    def tearDownClass(cls):
        if cls.old is None:
            os.environ.pop(C.SESSION_DIR_ENV, None)
        else:
            os.environ[C.SESSION_DIR_ENV] = cls.old
        cls.tmp.cleanup()

    def test_say_wide_from_helm_now_matches_and_splits(self):
        self.assertTrue(C._under(self.WT, self.ns.helm_now), self.WT.__file__)
        for names in (["juniper berry"], ["peppercorn", "allspice berry"], ["peppercorn", "allspice berry", "bay leaf"]):
            with self.subTest(names=names):
                s = self.WT.say_wide({"product": "stew", "gate": "G1", "unlearned": names, "absent": []})
                m1, m2 = HA.G1_ONE_RX.match(s), HA.G1_MANY_RX.match(s)
                self.assertTrue(bool(m1) != bool(m2), s)
                got = [m1.group("one")] if m1 else HA.NAME_SPLIT_RX.split(m2.group("many"))
                self.assertEqual(got, names)
                self.assertEqual((m1 or m2).group("p"), "stew")
                self.assertEqual(s, g1_sentence("stew", names))                  # the authored records use this text
        s = self.WT.say_wide({"product": "stew", "gate": "G1", "absent": ["broth"], "count_items": [],
                              "unlearned": ["juniper berry"]})
        self.assertIsNone(HA.G1_ONE_RX.match(s), s)
        self.assertIsNone(HA.G1_MANY_RX.match(s), s)
        self.assertEqual(s, missing_stock_sentence("stew", "broth"))


@unittest.skipUnless(HAVE_NEIGHBOURS, "neighbours not present")
class I_ReaderOnFixturePlants(unittest.TestCase):
    """The package's own reader (merge_r1w7.read) on the synthetic fixture run with the five A-R1W7-11 plants, applied to
    CHAT_ON, CHAT_ON_REPLAY and CHAT_DIAG alike (no hard gate moves)."""

    @classmethod
    def setUpClass(cls):
        from r1w7 import merge_r1w7 as M
        from tests_r1w7 import fixture_run as FX
        cls.M, cls.FX = M, FX
        cls.tmp = tempfile.TemporaryDirectory()
        cls.runs = {p: M.read(FX.make_run(Path(cls.tmp.name) / (p or "clean"), plant=p)["merge_input"])
                    for p in (None, "K4_A11", "K4_A11_CLARIFY", "K4_A11_PHANTOM", "K4_A11_NO_SAMPLE", "K3_A11_WRONG", "K4")}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_reader_string_names_the_amendment(self):
        self.assertIn("A-R1W7-11", self.M.READER)
        self.assertEqual(self.runs[None]["reader"], self.M.READER)

    def test_clean_run_unchanged(self):
        r = self.runs[None]
        k4 = r["marks"]["K4_HONEST"]
        self.assertEqual((r["marks_missed"], r["failing_gates"]), ([], []))
        self.assertEqual((k4["unexplained_asks_strict"], k4["unexplained_asks_strict_after_a11"], k4["a11_strict_recount"]),
                         (0, 0, 0))
        self.assertIs(k4["a11_consistent"], True)
        self.assertEqual(len(k4["sample_real_sha256"] or ""), 64)
        self.assertEqual(k4["amendment"], "A-R1W7-11")

    def test_k4_a11_honest_ask_is_exempted_and_flagged(self):
        r = self.runs["K4_A11"]
        k4 = r["marks"]["K4_HONEST"]
        self.assertEqual((r["marks_missed"], r["failing_gates"]), ([], []))
        self.assertIs(k4["value"], True)
        self.assertEqual((k4["unexplained_asks_strict"], k4["unexplained_asks_strict_after_a11"]), (1, 0))
        self.assertEqual(k4["a11_exempted_ids"], ["RW:f00"])
        self.assertEqual(k4["a11_flag_for_human_review"],
                         [{"id": "RW:f00", "tagged_lines": [2], "unlearned": ["juniper berry"],
                           "allowed_tail_heads": ["berry"], "status": "FLAG_FOR_HUMAN_REVIEW"}])

    def test_k4_a11_variants_still_miss_k4(self):
        for plant in ("K4_A11_CLARIFY", "K4_A11_PHANTOM", "K4_A11_NO_SAMPLE"):
            with self.subTest(plant=plant):
                r = self.runs[plant]
                k4 = r["marks"]["K4_HONEST"]
                self.assertEqual(r["marks_missed"], ["K4_HONEST"])
                self.assertEqual(r["failing_gates"], [])
                self.assertEqual((k4["unexplained_asks_strict"], k4["unexplained_asks_strict_after_a11"]), (1, 1))
                self.assertEqual(k4["a11_exempted_ids"], [])
        self.assertIsNone(self.runs["K4_A11_NO_SAMPLE"]["marks"]["K4_HONEST"]["sample_real_sha256"])

    def test_k3_a11_wrong_number_misses_k3_and_the_word_is_harmed(self):
        r = self.runs["K3_A11_WRONG"]
        self.assertEqual(r["marks_missed"], ["K3_SAFE"])
        self.assertEqual(r["marks"]["K3_SAFE"]["real_wrong_answers"], 1)
        self.assertEqual(self.M.status_word("PASS", r["marks"])["word"], "CHAT_WAVE_HARMED")   # the fixture's verdict is
        self.assertEqual(r["marks"]["K4_HONEST"]["unexplained_asks_strict_after_a11"], 0)       # INSTRUMENT_ERROR by design

    def test_existing_k4_plant_still_misses(self):
        r = self.runs["K4"]
        k4 = r["marks"]["K4_HONEST"]
        self.assertIn("K4_HONEST", r["marks_missed"])
        self.assertEqual((k4["unexplained_asks_strict"], k4["unexplained_asks_strict_after_a11"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
