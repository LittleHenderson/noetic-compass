"""roundtrip.py -- the only acceptance test.

TRANSLATOR_SPEC.md section 5, the language form of epsilon after eta = id:

    eta (write) = render.  epsilon (read) = parse.
    CAS-first:     parse(render(C, w)) == C   after normalization, for every content and every w.
    English-first: for a CCE sentence E, let C = parse(E); then parse(render(C)) == C.
                   render(parse(E)) == E is NOT required.

A receipt is written once and never recomputed (Correction 2: prerequisite satisfaction is
one-directional). This module also carries the spec's three anti-cheat checks, because a
grammar that adds a made-up word to BOTH its parser and its renderer passes its own round trip:

    1. every word of a said sentence comes from a frozen lexicon tier;
    2. no previously covered cell of the coverage ledger may break;
    3. the CAS side is cross-checked by cas_validator.py, which never sees the English.
"""

from __future__ import annotations

import hashlib
import json
import random

import cas_validator
import cce_parse
import cce_render
import lexicon as LX
from content import CASContent, N, Refusal, Term

CCE_VERSION = LX.CCE_VERSION

# UNDECIDED IN SPEC: section 5 cross-checks the CAS side against the CAS compiler; may an independently written validator stand in for it?
# That compiler (api/notation/compiler.py) is not in this folder and is not importable here, so
# cas_validator.py -- written independently, with its own copy of the canon tables -- stands in
# its place. It is a smaller judge than the compiler: it checks the record's structure and the
# participants each definition forces, not the compiler's whole type system.


class Receipt:
    """One round-trip record: {content_hash_in, sentence, wording_id, seed, content_hash_out,
    ok, rejection_codes}. Never recomputed once written."""

    __slots__ = ("content_hash_in", "sentence", "wording_id", "seed", "content_hash_out", "ok",
                 "rejection_codes", "cached", "direction")

    def __init__(self, content_hash_in, sentence, wording_id, seed, content_hash_out, ok,
                 rejection_codes=(), cached=False, direction="cas_first"):
        self.content_hash_in = content_hash_in
        self.sentence = sentence
        self.wording_id = wording_id
        self.seed = seed
        self.content_hash_out = content_hash_out
        self.ok = bool(ok)
        self.rejection_codes = tuple(rejection_codes)
        self.cached = bool(cached)
        self.direction = direction

    def to_dict(self) -> dict:
        return {
            "content_hash_in": self.content_hash_in,
            "sentence": self.sentence,
            "wording_id": self.wording_id,
            "seed": self.seed,
            "content_hash_out": self.content_hash_out,
            "ok": self.ok,
            "rejection_codes": list(self.rejection_codes),
            "direction": self.direction,
            "cce_version": CCE_VERSION,
        }

    @property
    def receipt_id(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)
                              .encode("utf-8")).hexdigest()[:16]

    def __repr__(self) -> str:
        return "Receipt(%s, ok=%s, %s)" % (self.receipt_id, self.ok, self.rejection_codes)


class ReceiptLog:
    """A write-once receipt log. A row, once written, is handed back as it was written."""

    def __init__(self):
        self._rows = {}
        self.written = 0
        self.reused = 0
        self.recomputed = 0
        self.refused = 0

    @staticmethod
    def _key(content_hash_in, wording_id, seed, direction) -> tuple:
        return (content_hash_in, wording_id, seed, direction)

    def lookup(self, content_hash_in, wording_id, seed, direction="cas_first"):
        return self._rows.get(self._key(content_hash_in, wording_id, seed, direction))

    def store(self, receipt: Receipt) -> Receipt:
        key = self._key(receipt.content_hash_in, receipt.wording_id, receipt.seed, receipt.direction)
        if key in self._rows:                    # never overwrite a written receipt
            self.reused += 1
            stored = self._rows[key]
            stored.cached = True
            return stored
        self._rows[key] = receipt
        self.written += 1
        return receipt

    def rows(self):
        return tuple(self._rows.values())

    def stats(self) -> dict:
        return {"written": self.written, "reused": self.reused,
                "recomputed": self.recomputed, "refused": self.refused, "rows": len(self._rows)}


def round_trip(content: CASContent, wording=None, seed=None, log: ReceiptLog = None,
               minds=("I", "you"), copied=()) -> Receipt:
    """Render content, parse the sentence back, and compare normalized forms."""
    try:
        chosen = cce_render.resolve(content, wording)
        wording_id = chosen.wid
    except Refusal as exc:
        return Receipt(content.digest(), None, None, seed, None, False, (exc.code,))
    content_hash_in = content.digest()
    if log is not None:
        stored = log.lookup(content_hash_in, wording_id, seed)
        if stored is not None:
            log.reused += 1
            stored.cached = True
            return stored
    codes = []
    sentence = content_hash_out = None
    ok = False
    try:
        sentence = cce_render.render(content, chosen)
    except Refusal as exc:
        codes.append(exc.code)
    if sentence is not None:
        try:
            back = cce_parse.parse(sentence, minds=minds)
            content_hash_out = back.digest()
            if back == content:
                ok = True
            else:
                codes.append("CONTENT_CHANGED")
                ok = False
        except Refusal as exc:
            codes.append(exc.code)
        except N.NumberRefusal as exc:
            codes.append(exc.code)
    receipt = Receipt(content_hash_in, sentence, wording_id, seed, content_hash_out, ok, tuple(codes))
    if log is not None:
        log.store(receipt)
        if not ok:
            log.refused += 1
    return receipt


def english_first(sentence: str, log: ReceiptLog = None, minds=("I", "you")) -> Receipt:
    """The English-first receipt: C = parse(E); then parse(render(C)) == C."""
    try:
        content = cce_parse.parse(sentence, minds=minds)
    except Refusal as exc:
        return Receipt(None, sentence, None, None, None, False, (exc.code,), direction="english_first")
    inner = round_trip(content, None, None, None, minds)
    return Receipt(content.digest(), sentence, inner.wording_id, None, inner.content_hash_out,
                   inner.ok, inner.rejection_codes, direction="english_first")


def sayable(content: CASContent, cap: int = None, minds=("I", "you")) -> dict:
    """How many DISTINCT sentences of this content come back as the same content."""
    limit = cap if cap is not None else cce_render.MAX_WORDINGS
    table = cce_render.wordings(content, cap=limit)
    sentences, failures, wordings_ok = {}, [], 0
    for wording in table:
        receipt = round_trip(content, wording, None, None, minds)
        if receipt.ok:
            wordings_ok += 1
            sentences.setdefault(receipt.sentence, receipt.wording_id)
        else:
            failures.append({"wording_id": wording.wid, "sentence": receipt.sentence,
                             "codes": list(receipt.rejection_codes)})
    return {"content_hash": content.digest(), "wordings_tried": len(table),
            "wordings_ok": wordings_ok, "distinct_sentences": len(sentences),
            "sentences": tuple(sentences), "failures": tuple(failures)}


def say(content: CASContent, seed: int, cap: int = LX.DRAW_CAP, minds=("I", "you")) -> dict:
    """A seeded wording draw with read-back. Randomness only picks a wording; the read-back
    decides; the fixed twin is the fallback. 'I cannot tell.' is never drawn."""
    if content.gate == "UNDETERMINED":
        return {"sentence": cce_render.FIXED_UNDETERMINED, "drawn": False, "tries": 0,
                "wording_id": None, "receipt": round_trip(content, None, seed, None, minds)}
    options = cce_render.wordings(content)
    rng = random.Random(seed)
    for attempt in range(1, cap + 1):
        pick = options[rng.randrange(len(options))]
        receipt = round_trip(content, pick, seed, None, minds)
        if receipt.ok:
            return {"sentence": receipt.sentence, "drawn": True, "tries": attempt,
                    "wording_id": pick.wid, "seed": seed, "receipt": receipt}
    receipt = round_trip(content, None, seed, None, minds)      # the fixed twin
    if not receipt.ok:
        raise Refusal("NO_FORM", "even the fixed twin fails read-back: " + str(receipt.rejection_codes))
    return {"sentence": receipt.sentence, "drawn": False, "tries": cap, "wording_id": receipt.wording_id,
            "seed": seed, "receipt": receipt}


# --- the three anti-cheat checks -------------------------------------------------------------------------------
def check_lexicon(sentence: str, copied=()) -> dict:
    """Check 1: every word comes from a frozen tier. Names and copied slot words are not words."""
    if sentence is None:
        return {"ok": False, "invented": ["NO_SENTENCE"], "sentence": None}
    report = LX.lexicon_report(sentence, copied)
    report["check"] = "lexicon_only"
    return report


def check_regression(before, after) -> dict:
    """Check 2: no previously covered cell may break."""
    broken = []
    for cell, state in before.items():
        if state == "COVERED" and after.get(cell) != "COVERED":
            broken.append({"cell": cell, "was": state, "now": after.get(cell)})
    return {"check": "no_regression", "ok": not broken, "broken": broken,
            "cells_before": len(before), "cells_after": len(after)}


def check_independent(content: CASContent) -> dict:
    """Check 3: the CAS side, cross-checked by a validator that never sees the English."""
    report = cas_validator.report(content)
    report["check"] = "independent_validator"
    return report


def admit(content: CASContent, wording=None, ledger=None, log: ReceiptLog = None,
          minds=("I", "you"), copied=()) -> dict:
    """All three checks and the receipt together. A sentence may only be said when this passes."""
    receipt = round_trip(content, wording, None, log, minds)
    lexicon = check_lexicon(receipt.sentence, copied)
    independent = check_independent(content)
    regression = {"check": "no_regression", "ok": True, "broken": []}
    if ledger is not None:
        after = ledger.states()
        regression = check_regression(ledger.baseline(), after)
    ok = bool(receipt.ok and lexicon["ok"] and independent["ok"] and regression["ok"])
    return {"ok": ok, "receipt": receipt, "lexicon": lexicon, "independent": independent,
            "regression": regression,
            "reason": None if ok else "FAILED: " + ", ".join(
                name for name, passed in (("round_trip", receipt.ok), ("lexicon", lexicon["ok"]),
                                          ("independent", independent["ok"]),
                                          ("no_regression", regression["ok"])) if not passed)}


# --- the coverage ledger (TRANSLATOR_SPEC section 10, simplified to one universe) ------------------------------
PROBE_SLOTS = {
    0: {"I": '"p_i"'},
    1: {"M": "I", "I": '"p_i"', "ACT": "intakes"},
    2: {"M": "I", "I": '"p_i"'},
    3: {"M": "I", "I": '"p_i"'},
    4: {"I": '"p_i"', "M": "I", "D": "1/3"},      # a NON-TERMINATING degree on purpose
    5: {"M": "I", "I": '"p_i"'},
    6: {"I": '"p_i"', "J": '"p_j"'},
    7: {"M": "I", "I": '"p_i"', "R": "2", "U": "day", "P": "daily"},
    8: {"I": '"p_i"', "J": '"p_j"', "M": "I"},
    9: {"J": '"p_j"', "M": "I"},
}
REGISTER_VALUES = ("T", "A", "f", "E", None)


def probe_content(noetic: int, domain: str, register) -> CASContent:
    """One probe per cell, built from the cell's own coordinates with fixed placeholder names."""
    term = Term(noetic, slots=PROBE_SLOTS[noetic], domain=domain,
                register=(register,) if register else None)
    return CASContent(terms=(term,))


class CoverageLedger:
    """The four states of the Lacunarity Machine, used exactly as defined:
    COVERED (probe passes), NO_EVIDENCE (no rule claims the cell), LACUNA (probe fails and no
    rule claimed it), FADED (a rule claimed it and the probe fails)."""

    STATES = ("COVERED", "NO_EVIDENCE", "LACUNA", "FADED")

    def __init__(self):
        self._charges = {}
        self._probes = {}
        self._baseline = None

    def charge(self, cell) -> bool:
        """A frozen frame that can carry this cell's Noetic is the charge for the cell."""
        noetic = cell[0]
        return bool(cce_render.template_options(Term(noetic, slots=PROBE_SLOTS[noetic])))

    def probe(self, cell) -> dict:
        noetic, domain, register = cell
        charged = self.charge(cell)
        self._charges[cell] = charged
        receipt = round_trip(probe_content(noetic, domain, register))
        self._probes[cell] = receipt
        if receipt.ok:
            state = "COVERED"
        elif not charged:
            state = "LACUNA"
        elif receipt.sentence is None:
            state = "FADED"
        else:
            state = "FADED"
        return {"cell": cell, "state": state, "charged": charged,
                "sentence": receipt.sentence, "receipt_ok": receipt.ok,
                "codes": list(receipt.rejection_codes)}

    def cells(self):
        return tuple((noetic, domain, register) for noetic in range(10)
                     for domain in ("P", "C", "E", "O") for register in REGISTER_VALUES)

    def run(self) -> dict:
        rows = [self.probe(cell) for cell in self.cells()]
        counts = {state: 0 for state in self.STATES}
        for row in rows:
            counts[row["state"]] += 1
        covered_without_charge = sum(1 for row in rows
                                     if row["state"] == "COVERED" and not row["charged"])
        if self._baseline is None:
            self._baseline = {row["cell"]: row["state"] for row in rows}
        return {"cells": len(rows), "counts": counts, "rows": rows,
                "covered_without_charge": covered_without_charge,
                "not_covered": [row for row in rows if row["state"] != "COVERED"]}

    def states(self) -> dict:
        return {cell: ("COVERED" if self._probes[cell].ok else
                       ("LACUNA" if not self._charges.get(cell) else "FADED"))
                for cell in self._probes}

    def baseline(self) -> dict:
        return dict(self._baseline or {})
