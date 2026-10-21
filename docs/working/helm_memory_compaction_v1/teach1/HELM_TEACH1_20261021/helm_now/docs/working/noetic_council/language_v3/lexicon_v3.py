"""ALIAS-WIDE lexicon v3 (2026-10-19): the LIVE word list, with the forbidden bare-word mappings removed.

What it is, in plain words
--------------------------
The frozen word lists (v1 = ALIAS_WIDE_LEXICON_v0_1.json, v2 = v1 + lexicon_v2.ADDITIONS) let some bare words pick a
Noetic by themselves: "female" -> ^5, "male" -> ^6, "negative" -> ^3, "positive" -> ^2, "vibration" -> ^4,
"rhythm" -> ^7, and the bare nouns "idea" / "a thought" -> ^0, "mind" -> ^1 (plus v2's bare nouns). On everyday
English that is exactly the forbidden mapping: "the female chef" is not ^5 Female, "a male voice" is not ^6 Male,
"the test came back negative" is not ^3 Negative (MAP.md section C NO-MAP list: grammatical gender and gendered
words; section D trap table; COVERAGE.md section 4, the LATENT risk).

v3 = v2 with those entries REMOVED. Nothing is added. Only these select a Noetic in v3:
  * the canonical colloquialisms (Clarification 6 / CLAUDE.md map) and their closed surface variants, and
  * the verbs of the ten authoritative definitions ("affinity for", "attracted toward", "adverse to", "repelled by",
    "resonates with", "impregnated with", "triggers", "brought to Mind", ...),
  * plus the two full slash names "Above/Cause" and "Below/Effect" (MAP.md F6 keeps those; bare "cause" and "effect"
    were already dropped in v1).
A sentence that holds only a removed bare word binds NO Noetic: it is UNDETERMINED ("I cannot tell"), with the
word listed under `no_map_words`. Negation words only set the F14 polarity flag (DENIED); "not" never makes ^3.

Frozen files are untouched: ALIAS_WIDE_LEXICON_v0_1.json and lexicon_v2.py are pinned by hash inside sealed wave
packages and the lexicon-v2 receipts. v3 reads them (the v2 additions are read with `ast`, so no import of
aliaswide / sdg_bridge_v2 is needed) and removes entries from a copy.

The switch: environment variable HELM_LEXICON_V3, default ON. "off" / "0" / "false" / "no" restores the frozen
path exactly (the live cube-store turn then uses aliaswide's v1 tables and its old valence words again).

Claim status: ENGINEERED-NOT-VALIDATED. A word-list change for the live English path; no meaning claim.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
V1_PATH = HERE / "ALIAS_WIDE_LEXICON_v0_1.json"
V2_PATH = HERE / "lexicon_v2.py"
LEXICON_VERSION = "cce-v0.3-alias-wide-lexicon-live-no-bare-names"
SWITCH_ENV = "HELM_LEXICON_V3"
CLAIM_STATUS = "ENGINEERED-NOT-VALIDATED"
TIER_NAMES = ("frame_tier", "name_tier", "noun_tier")

# Each removal: (tier, noetic, regex exactly as written in v1 or v2, where it came from, why it is removed).
# Rule (owner, 2026-10-19, "Ok I agree with all 3 cards"): only canonical colloquialisms and definition verbs select
# a Noetic. A bare Noetic name used as an everyday word, and a bare noun, are neither.
REMOVED: List[Tuple[str, int, str, str, str]] = [
    ("name_tier", 2, "positive", "v1",
     "everyday adjective ('the result was positive'); ^2 only via 'attracted toward' / 'affinity for' / 'drawn to'"),
    ("name_tier", 3, "negative", "v1",
     "everyday adjective ('the test came back negative'); ^3 is visceral aversion, only via 'can't stomach' / "
     "'rubs me the wrong way' / 'ten-foot pole' / 'adverse to' / 'repelled by'"),
    ("name_tier", 4, "vibration", "v1",
     "everyday noun ('the phone's vibration'); ^4 only via 'resonates with' / 'struck a chord' / 'hit me hard'"),
    ("name_tier", 5, "female", "v1",
     "gender word: NO-MAP (MAP.md C; trap table 'she / he / feminine noun'); ^5 only via 'sum of our experiences' / "
     "'who I am' / 'part of what makes me me' / 'impregnated with' / 'composed of'"),
    ("name_tier", 6, "male", "v1",
     "gender word: NO-MAP (MAP.md C; trap table); ^6 only via 'unpacking' / 'breaking it down' / "
     "'looking at what's underneath' / 'impregnated with another Idea'"),
    ("name_tier", 7, "rhythm", "v1",
     "everyday noun ('the rhythm of the song'); ^7 only via 'practice makes perfect' / 'muscle memory' / "
     "'getting into a groove' / 'entraining'"),
    ("noun_tier", 0, "ideas?", "v1", "bare noun ('I have an idea'); ^0 only via 'it's all in your head'"),
    ("noun_tier", 0, "a thought", "v1", "bare noun; ^0 only via 'it's all in your head'"),
    ("noun_tier", 1, "minds?", "v1",
     "bare noun ('never mind'; 'Ana is a Mind' is membership, F23); ^1 only via 'paying attention' / "
     "'making up your mind' / 'using your head' / the definition verbs"),
    ("noun_tier", 0, "thoughts?", "v2", "bare noun (v2 source d); same reason as 'a thought'"),
    ("noun_tier", 1, "attention", "v2", "bare noun (v2); the colloquialism is 'paying attention', kept in frame tier"),
    ("noun_tier", 7, "practic(?:e|es|ed|ing)", "v2",
     "bare word ('a medical practice'); the colloquialism 'practice makes perfect' is kept in frame tier"),
    ("noun_tier", 7, "repetitions?", "v2", "bare noun; the colloquialism 'you are what you repeatedly do' is kept"),
    ("noun_tier", 7, "groove", "v2", "bare noun; the colloquialism 'getting into a groove' is kept in frame tier"),
    ("noun_tier", 9, "realizations?", "v2", "bare noun; the colloquialisms 'it just clicked' / 'came to me' are kept"),
]

#: Valence words the live cube-store turn (cube_store/turn.py) must no longer read as ^2 / ^3 when the switch is ON.
VALENCE_WORDS_REMOVED = ("negative", "positive")


# ------------------------------------------------------------------------------------------------ building the tables
def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _v1_lexicon() -> Dict[str, Any]:
    return json.loads(V1_PATH.read_text("utf-8"))


def v2_additions() -> Tuple[list, list]:
    """lexicon_v2.NOETIC_ADDITIONS and DOMAIN_ADDITIONS, read as literals from the frozen file (no import)."""
    tree = ast.parse(V2_PATH.read_text("utf-8"))
    found: Dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ("NOETIC_ADDITIONS", "DOMAIN_ADDITIONS"):
                found[node.targets[0].id] = ast.literal_eval(node.value)
    return found["NOETIC_ADDITIONS"], found["DOMAIN_ADDITIONS"]


def merged_lexicon(version: str = "v3") -> Dict[str, Any]:
    """'v1' = the frozen JSON; 'v2' = v1 + lexicon_v2 additions (same as lexicon_v2.merged_lexicon());
    'v3' = v2 minus REMOVED. Always a new dict; no frozen file is touched."""
    if version not in ("v1", "v2", "v3"):
        raise ValueError("lexicon version must be 'v1', 'v2' or 'v3', got %r" % (version,))
    lex = copy.deepcopy(_v1_lexicon())
    if version == "v1":
        return lex
    noetic_add, domain_add = v2_additions()
    lex["version"] = "cce-v0.2-alias-wide-lexicon"
    for tier, n, rx, _src, _why in noetic_add:
        lex[tier].setdefault(str(n), []).append(rx)
    for d, rx, _src, _why in domain_add:
        lex["domain_words"][d].append(rx)
    if version == "v2":
        return lex
    lex["version"] = LEXICON_VERSION
    for tier, n, rx, _src, _why in REMOVED:
        words = lex[tier].get(str(n), [])
        if rx not in words:
            raise RuntimeError("lexicon_v3: removal %r not found in %s ^%d (frozen lists changed?)" % (rx, tier, n))
        words.remove(rx)
        if not words:
            del lex[tier][str(n)]
    return lex


def _compile(phrases):
    # identical to aliaswide._compile (whole-word, case-insensitive by lowercasing the text first)
    return [re.compile(r"(?<![\w'/])(?:" + p + r")(?![\w'/])") for p in phrases]


def _tiers(lex) -> List[Tuple[int, int, "re.Pattern[str]"]]:
    out = []
    for rank, name in enumerate(TIER_NAMES):
        for n, phrases in lex[name].items():
            for rx in _compile(phrases):
                out.append((rank, int(n), rx))
    return out


_TABLES: Dict[str, List[Tuple[int, int, Any]]] = {}


def tables(version: str = "v3"):
    if version not in _TABLES:
        _TABLES[version] = _tiers(merged_lexicon(version))
    return _TABLES[version]


LEX = merged_lexicon("v3")
TIERS = tables("v3")
POLARITY_RE = re.compile(r"(?<![\w'])(?:" + "|".join(re.escape(w) for w in LEX["polarity_words"]) + r")(?![\w'])")
NO_MAP_RE = re.compile(r"(?<![\w'/])(?:" + "|".join(rx for _t, _n, rx, _s, _w in REMOVED) + r")(?![\w'/])")


# ------------------------------------------------------------------------------------------------ reading
def phrase_hits(text: str, version: str = "v3"):
    """Longest-first, non-overlapping hits [(start, end, noetic, tier_rank)] on lowercased text.
    Same algorithm as aliaswide.phrase_hits; only the word tables differ."""
    found = []
    for rank, n, rx in tables(version):
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
    """Verb frame first (same rule as aliaswide.decide_noetic)."""
    for rank in (0, 1, 2):
        ns = sorted({h[2] for h in hits if h[3] == rank})
        if len(ns) == 1:
            return ns[0], None
        if len(ns) > 1:
            return None, "AMBIGUOUS_STATE_IN_SEGMENT"
    return None, "NO_STATE_IN_SEGMENT"


def _normalize(text: str) -> str:
    return text.replace("’", "'").replace("‘", "'").lower()


def read_noetic(text: str, version: str = "v3") -> Dict[str, Any]:
    """Which Noetic, if any, this English binds. status BOUND (one Noetic), AMBIGUOUS, or UNDETERMINED.
    polarity: 'DENIED' when a frozen polarity word is present (F14 flag only; it never changes the Noetic)."""
    lower = _normalize(text)
    hits = phrase_hits(lower, version)
    n, why = decide_noetic(hits)
    status = "BOUND" if n is not None else ("AMBIGUOUS" if why == "AMBIGUOUS_STATE_IN_SEGMENT" else "UNDETERMINED")
    masked = lower
    for a, b, _n, _r in hits:
        masked = masked[:a] + " " * (b - a) + masked[b:]
    no_map = sorted({m.group(0) for m in NO_MAP_RE.finditer(masked)}) if version == "v3" else []
    return {"noetic": n, "status": status, "reason": why, "hits": [[lower[a:b], k] for a, b, k, _r in hits],
            "polarity": "DENIED" if POLARITY_RE.search(masked) else None, "no_map_words": no_map,
            "lexicon": LEXICON_VERSION if version == "v3" else version}


# ------------------------------------------------------------------------------------------------ the switch
def switch_on() -> bool:
    """Default ON. HELM_LEXICON_V3=off|0|false|no restores the frozen path."""
    return os.environ.get(SWITCH_ENV, "on").strip().lower() not in ("off", "0", "false", "no")


def live_phrase_hits(text: str, frozen_reader: Optional[Any] = None):
    """The live path's Noetic phrase hits: v3 when the switch is ON; else the frozen reader's own phrase_hits
    (aliaswide, v1) exactly as before, or v1 tables when no frozen reader is loaded."""
    if switch_on():
        return phrase_hits(text, "v3")
    if frozen_reader is not None:
        return frozen_reader.phrase_hits(text)
    return phrase_hits(text, "v1")


def manifest() -> Dict[str, Any]:
    return {"lexicon": LEXICON_VERSION, "claim_status": CLAIM_STATUS, "switch_env": SWITCH_ENV,
            "switch_on": switch_on(), "v1_json_sha256": _sha256(V1_PATH), "lexicon_v2_py_sha256": _sha256(V2_PATH),
            "removed": [{"tier": t, "target": "^%d" % n, "regex": rx, "from": s, "why": w}
                        for t, n, rx, s, w in REMOVED],
            "valence_words_removed": list(VALENCE_WORDS_REMOVED)}


def aliaswide_reader():
    """A separate aliaswide module object with the v3 tables (for SDG-English parity checks). Needs sdg_bridge_v2 on
    the path, like lexicon_v2.reader('v2'); the live path never calls this."""
    import importlib.util
    import lexicon_v2  # noqa: WPS433 (deliberately lazy: imports aliaswide -> sdg_bridge_v2)
    spec = importlib.util.spec_from_file_location("aliaswide_lexicon_v3", HERE / "aliaswide.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod = lexicon_v2._rebuild(mod, merged_lexicon("v3"))
    mod.RULESET_VERSION = "cce-v0.3-alias-wide"
    return mod
