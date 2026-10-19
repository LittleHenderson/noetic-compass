"""ALIAS-WIDE lexicon v2: v1 (ALIAS_WIDE_LEXICON_v0_1.json, never edited) plus a short, source-tagged list of additions.

Admission rule: FROZEN_LEXICON_V2.json (written and pushed before this file). Sources:
  a = canonical colloquialism map (CLAUDE.md / Clarification 6), with closed surface variants
  b = verbs of the ten authoritative Noetic definitions, with closed inflections
  c = domain words in docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md (adds nothing beyond v1)
  d = words observed in the 99 DEV rows (real_dev_unparseables_99.jsonl). Never the sealed 98.

The switch:  reader("v1") -> the original aliaswide module, untouched.
             reader("v2") -> a separate copy of aliaswide whose word tables are rebuilt from v1 + ADDITIONS.
Only word lists change. Segmentation, hedges, polarity, leakage, numbers, verb-frame-first and the
MATCH / MISMATCH comparison are v1's code, unchanged.
"""
import copy
import importlib.util
import re
from pathlib import Path

import aliaswide as _v1

HERE = Path(__file__).resolve().parent
LEXICON_VERSION = "cce-v0.2-alias-wide-lexicon"
TIER_RANK = {"frame_tier": 0, "name_tier": 1, "noun_tier": 2}

# Each Noetic alias: (tier, noetic, regex, sources, colloquialism-test line).
NOETIC_ADDITIONS = [
    ("frame_tier", 2, r"draw(?:s|n|ing)? (?:you |me |one |us |someone |it )?(?:to|toward|towards)", "a+b+d",
     "'draws you toward' -> 'Drawn to it like a moth to a flame' (^2); definition verb 'attracted toward' (^2)"),
    ("frame_tier", 3, r"pushed[- ]away", "b+d",
     "'pushed away' / 'pushed-away response' -> visceral repulsion, definition verb 'repelled by' (^3); "
     "variant of v1's 'pushed away from'. Visceral, not analytical: passes the ^3 anti-drift check"),
    ("frame_tier", 4, r"resonant", "b+d",
     "'a resonant impression' -> 'Resonated' / 'Struck a chord' (^4); inflection of definition verb 'resonates with'"),
    ("frame_tier", 7, r"practice[- ]mak(?:es|ing)[- ]perfect", "a+d",
     "'practice-makes-perfect', 'practice making perfect' -> 'Practice makes perfect' (^7); hyphen / -ing variant"),
    ("noun_tier", 0, r"thoughts?", "d",
     "'a foundational thought' -> 'It's all in your head' (^0); v1 already holds 'a thought' for ^0. "
     "Frame phrases ('the thought came to me' ^9) still win because they are a higher tier"),
    ("noun_tier", 1, r"attention", "a+d",
     "'analytical attention' -> 'Paying attention' (^1); plain noun of the canon phrase"),
    ("noun_tier", 7, r"practic(?:e|es|ed|ing)", "a+d",
     "'practiced habit', 'practice-based' -> 'Practice makes perfect' (^7); key word of the canon phrase"),
    ("noun_tier", 7, r"repetitions?", "a+d",
     "'practice and repetition' -> 'You are what you repeatedly do' (^7); noun of 'repeatedly'"),
    ("noun_tier", 7, r"groove", "a+d",
     "'practice and groove' -> 'Getting into a groove' (^7); key word of the canon phrase"),
    ("noun_tier", 9, r"realizations?", "d",
     "'a realization' -> 'It just clicked' / 'The thought came to me' (^9). A landing word, not a trigger: "
     "passes the ^8-vs-^9 anti-drift check"),
]

# Each domain word: (domain, regex, sources, gloss line). Admitted only if it passes the FROZEN domain test
# (one domain's plain gloss, and no DEV segment containing it has a gold cell in another domain).
DOMAIN_ADDITIONS = [
    ("C", r"mental", "d", "'mental' is the plain gloss of 'cognitive' (of the mind); DEV: 'mental thinking', 'the mental arena'"),
]

# Candidates considered and REFUSED, kept here so nobody re-proposes them without new evidence.
REFUSED = [
    ("domain", "O", "behaviou?r(?:s|al)?", "fails domain test (ii) in 2 DEV segments: 'who you are in operational behavior' "
     "(gold ^5^P) and 'a thought in operational behavior' (gold ^0^P). Both writers also wrote 'operational', so the "
     "fault is the writer's, but the frozen rule refuses on one violation"),
    ("domain", "E", "judg(?:e?ment|ing)", "fails domain test (ii): DEV 'breaking down a cognitive judgment' has gold ^6^C"),
    ("domain", "C", "thinking", "not a gloss of exactly one domain: DEV uses 'foundational thinking' (P) and 'cognitive thinking' (C)"),
    ("domain", "P", "realm|frame", "not a domain gloss: DEV uses 'evaluative realm', 'operational realm', 'foundational realm'"),
    ("noetic", 1, "thinking", "fails the colloquialism test as a state word: 'thinking' is the SDG writer's domain filler"),
    ("noetic", 8, "memory", "bare 'memory' is not a trigger: 'muscle memory' is ^7; trigger phrases already carry ^8"),
    ("mask", None, "shaped by (?:a|the) need for", "would drop real ^5 (DEV 'mental processing shaped by the need for vitality', gold ^5^C)"),
]


def merged_lexicon():
    """v1 dictionary plus every addition. Returns a new dict; v1 is not touched."""
    lex = copy.deepcopy(_v1.LEX)
    lex["version"] = LEXICON_VERSION
    for tier, n, rx, _src, _why in NOETIC_ADDITIONS:
        lex[tier].setdefault(str(n), []).append(rx)
    for d, rx, _src, _why in DOMAIN_ADDITIONS:
        lex["domain_words"][d].append(rx)
    return lex


def _rebuild(mod, lex):
    """Rebuild a fresh aliaswide copy's word tables exactly the way aliaswide.py builds them from its JSON."""
    mod.LEX = lex
    mod.RULESET_VERSION = "cce-v0.2-alias-wide"
    mod.TIERS = []
    for rank, name in ((0, "frame_tier"), (1, "name_tier"), (2, "noun_tier")):
        for n, phrases in lex[name].items():
            for rx in mod._compile(phrases):
                mod.TIERS.append((rank, int(n), rx))
    mod.DOMAIN_OF = [(d, rx) for d, ws in lex["domain_words"].items() for rx in mod._compile(ws)]
    mod.REGISTER_OF = [(r, rx) for r, ws in lex["register_words_second_number_only"].items() for rx in mod._compile(ws)]
    mod.DRIVE_OF = [(k, rx) for k, ws in lex["drive_words_second_number_only"].items() for rx in mod._compile(ws)]
    be = mod.bridge_english
    mod.POLARITY_RE = be._alternation(lex["polarity_words"])
    mod.HEDGE_RE = be._alternation(lex["hedge_words"])
    mod.LEAK_RE = be._alternation(lex["leak_words"] + ["side product"])
    mod.NUMWORD_RE = re.compile(r"(?<![\w'])(" + "|".join(lex["number_words"]) +
                                r")(?=\s+(?:(?:part|parts|unit|units|measure|measures|portion|portions)\s+)?of\b)")
    return mod


_CACHE = {}


def reader(version="v1"):
    """The switch. 'v1' = aliaswide as shipped; 'v2' = a separate module object with v1 + ADDITIONS."""
    if version == "v1":
        return _v1
    if version != "v2":
        raise ValueError("lexicon version must be 'v1' or 'v2', got %r" % (version,))
    if "v2" not in _CACHE:
        spec = importlib.util.spec_from_file_location("aliaswide_lexicon_v2", HERE / "aliaswide.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _CACHE["v2"] = _rebuild(mod, merged_lexicon())
    return _CACHE["v2"]


def additions_table():
    """Every v2 addition with its source tag, for the results file."""
    rows = [{"kind": "noetic", "tier": t, "target": "^%d" % n, "regex": rx, "source": s, "test": w}
            for t, n, rx, s, w in NOETIC_ADDITIONS]
    rows += [{"kind": "domain", "tier": "domain_words", "target": d, "regex": rx, "source": s, "test": w}
             for d, rx, s, w in DOMAIN_ADDITIONS]
    return rows
