"""ALIAS-WIDE reader of free SDG English (TRANSLATOR_SPEC section 9). A FORM check, not a semantic judge.

Same frozen tiers as CCE (ALIAS_WIDE_LEXICON_v0_1.json, pinned in FROZEN.json) plus the bridge v2
segment-by-number tuple reader. Imports sdg_bridge_v2.english read-only for its masks, outcome patterns,
tuple shape and comparison. What changes against bridge v2: the Noetic phrase list (canon-only, no bare
cause/effect, closed inflections), the verb-frame-first rule inside a segment, closed number words, and a
second number (register and drive agreement) reported for MATCH rows.
"""
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import re

from sdg_bridge_v2 import english as bridge_english

LEXICON_PATH = Path(__file__).resolve().parent / "ALIAS_WIDE_LEXICON_v0_1.json"
LEX = json.loads(LEXICON_PATH.read_text("utf-8"))
RULESET_VERSION = "cce-v0.1-alias-wide"


def _compile(phrases):
    return [re.compile(r"(?<![\w'/])(?:" + p + r")(?![\w'/])") for p in phrases]


TIERS = []   # (tier rank, noetic, compiled)
for _rank, _name in ((0, "frame_tier"), (1, "name_tier"), (2, "noun_tier")):
    for _n, _phrases in LEX[_name].items():
        for _rx in _compile(_phrases):
            TIERS.append((_rank, int(_n), _rx))
DOMAIN_OF = [(d, rx) for d, ws in LEX["domain_words"].items() for rx in _compile(ws)]
REGISTER_OF = [(r, rx) for r, ws in LEX["register_words_second_number_only"].items() for rx in _compile(ws)]
DRIVE_OF = [(k, rx) for k, ws in LEX["drive_words_second_number_only"].items() for rx in _compile(ws)]
POLARITY_RE = bridge_english._alternation(LEX["polarity_words"])
HEDGE_RE = bridge_english._alternation(LEX["hedge_words"])
LEAK_RE = bridge_english._alternation(LEX["leak_words"] + ["side product"])
NUMWORD_RE = re.compile(r"(?<![\w'])(" + "|".join(LEX["number_words"]) +
                        r")(?=\s+(?:(?:part|parts|unit|units|measure|measures|portion|portions)\s+)?of\b)")
DIGIT_RE = bridge_english.NUMBER_RE


def phrase_hits(text):
    """Longest-first, non-overlapping hits: [(start, end, noetic, tier_rank)]."""
    found = []
    for rank, n, rx in TIERS:
        for m in rx.finditer(text):
            if m.end() > m.start():
                found.append((m.start(), m.end(), n, rank))
    found.sort(key=lambda h: (-(h[1] - h[0]), h[0], h[3], h[2]))
    taken, used = [], []
    for h in found:
        if any(not (h[1] <= a or h[0] >= b) for a, b in used):
            continue
        taken.append(h)
        used.append((h[0], h[1]))
    return sorted(taken)


def decide_noetic(hits):
    for rank in (0, 1, 2):
        ns = sorted({h[2] for h in hits if h[3] == rank})
        if len(ns) == 1:
            return ns[0], None
        if len(ns) > 1:
            return None, "AMBIGUOUS_STATE_IN_SEGMENT"
    return None, "NO_STATE_IN_SEGMENT"


def _segment(original, masked, a, b, stems, number_value):
    seg = masked[a:b]
    warnings = []
    seg_stems = [s for (sa, sb, s) in stems if sa >= a and sb <= b]
    coefficient = Decimal(number_value)
    hits = phrase_hits(seg)
    side_stems = [s for s in seg_stems if s.lower().endswith("_side")]
    if side_stems or LEAK_RE.search(seg):
        ref = side_stems[0] if side_stems else (seg_stems[0] if seg_stems else None)
        return (coefficient, "leakage", "outcome", None if ref is None else "Ω_" + ref, False), None, warnings, None
    negated = POLARITY_RE.search(bridge_english._mask(seg, [(h[0], h[1]) for h in hits])) is not None
    if hits:
        n, why = decide_noetic(hits)
        if n is None:
            return None, why, warnings, None
        domains = sorted({d for d, rx in DOMAIN_OF if rx.search(seg)})
        if len(domains) != 1:
            return None, ("NO_DOMAIN_IN_SEGMENT" if not domains else "AMBIGUOUS_DOMAIN_IN_SEGMENT"), warnings, None
        extra = {"registers": sorted({r for r, rx in REGISTER_OF if rx.search(seg)}),
                 "drives": sorted({k for k, rx in DRIVE_OF if rx.search(seg)})}
        return (coefficient, "prerequisite", "state", "^%d^%s" % (n, domains[0]), negated), None, warnings, extra
    prereq = bridge_english.OUTCOME_PREREQ_RE.search(original[a:b])
    if prereq is not None:
        return (coefficient, "prerequisite", "outcome", "Ω_" + prereq.group(1), negated), None, warnings, None
    return None, "NO_STATE_IN_SEGMENT", warnings, None


def _numbers(masked):
    hits = phrase_hits(masked)
    blocked = [(h[0], h[1]) for h in hits]
    out = [(m.start(), m.end(), m.group(1)) for m in DIGIT_RE.finditer(masked)]
    for m in NUMWORD_RE.finditer(masked):
        if not any(a <= m.start() < b for a, b in blocked):
            out.append((m.start(), m.end(), LEX["number_words"][m.group(1)]))
    return sorted(out)


def _orient(original, masked, numbers, stems, mode):
    tuples, failures, extras = [], [], []
    for i, (s, e, v) in enumerate(numbers):
        if mode == "number_before":
            a, b = s, (numbers[i + 1][0] if i + 1 < len(numbers) else len(masked))
        else:
            a, b = (numbers[i - 1][1] if i > 0 else 0), e
        t, reason, _, extra = _segment(original, masked, a, b, stems, v)
        if reason is not None:
            failures.append({"code": reason, "coefficient": v})
        else:
            tuples.append(t)
            extras.append(extra)
    return tuples, failures, extras


def extract(text):
    original = text.replace("’", "'").replace("‘", "'")
    lower = original.lower()
    stems = [(m.start(), m.end(), m.group(0)) for m in bridge_english.STEM_RE.finditer(original)]
    named = [(m.start(1), m.end(1), m.group(1)) for m in bridge_english.NAMED_OUTCOME_RE.finditer(original)]
    masked = bridge_english._mask(lower, [(a, b) for a, b, _ in stems + named])
    outcome_names = sorted({s for _, _, s in stems + named})
    if HEDGE_RE.search(masked):
        return {"status": "UNPARSEABLE_ENGLISH", "reasons": [{"code": "HEDGE_OR_CONDITION"}], "tuples": [],
                "extras": [], "outcome_names": outcome_names}
    numbers = _numbers(masked)
    if not numbers:
        return {"status": "UNPARSEABLE_ENGLISH", "reasons": [{"code": "NO_COEFFICIENTS"}], "tuples": [],
                "extras": [], "outcome_names": outcome_names}
    allst = stems + named
    t1, f1, x1 = _orient(original, masked, numbers, allst, "number_before")
    if not f1:
        return {"status": "PARSED", "reasons": [], "tuples": t1, "extras": x1, "outcome_names": outcome_names}
    t2, f2, x2 = _orient(original, masked, numbers, allst, "number_after")
    if not f2:
        return {"status": "PARSED", "reasons": [], "tuples": t2, "extras": x2, "outcome_names": outcome_names}
    return {"status": "UNPARSEABLE_ENGLISH", "reasons": f1, "tuples": [], "extras": [], "outcome_names": outcome_names}


def check(parsed_cas, english_text):
    """MATCH / MISMATCH / UNPARSEABLE_ENGLISH, plus the second number (register and drive agreement)."""
    source = bridge_english.cas_tuples(parsed_cas)
    e = extract(english_text)
    out = {"verdict": None, "reasons": [r["code"] for r in e["reasons"]], "second_number_agrees": None,
           "kind": "FORM_CHECK_NOT_SEMANTIC_JUDGE"}
    if e["status"] != "PARSED":
        out["verdict"] = "UNPARSEABLE_ENGLISH"
        return out
    if Counter(source) == Counter(e["tuples"]):
        out["verdict"] = "MATCH"
        cas_meta = {}
        for t in parsed_cas["core"]:
            if t["kind"] == "state":
                cas_meta.setdefault((Decimal(t["coefficient"]), t["cell"]), []).append(
                    ([t["register"]] if t["register"] else [], [t["drive"]] if t["drive"] else []))
        agree = True
        for tup, extra in zip(e["tuples"], e["extras"]):
            if tup[2] != "state" or extra is None:
                continue
            options = cas_meta.get((tup[0], tup[3]), [])
            if not any(extra["registers"] == r and extra["drives"] == d for r, d in options):
                agree = False
        out["second_number_agrees"] = agree
        return out
    out["verdict"] = "MISMATCH"
    cas_only = list((Counter(source) - Counter(e["tuples"])).elements())
    eng_only = list((Counter(e["tuples"]) - Counter(source)).elements())
    out["offending_pair"] = {"english": [bridge_english.render_tuple(t) for t in eng_only][:1],
                             "cas": [bridge_english.render_tuple(t) for t in cas_only][:1]}
    return out
