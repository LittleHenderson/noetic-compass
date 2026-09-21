"""The canonical 28 Foundations, as ONE tested coordinate for the Expression Lab.

Owner ruling, 2026-09-21 (chat, with the PDF attached): "CANONICAL 28 FOUNDATIONS" -- the document
"28 Foundations 1.0" (file `28 fOUNDATIONS 1.0.pdf`, 399,302 bytes, sha256
2c27443f447bd69901372edb1316be56a92490afc6f88055ce0c84ce7a871017). This closes discrepancy DR-4 of
OPERATION_CONTRACTS.json ("three 28-way namespaces, owner decision pending"): when the lab needs a
28-way Foundation coordinate, THIS is it. The owner also ruled the same day that no part of CAS is
excluded from Helm's expression space: the 40 Elements, the 28 Foundations, and every expression and
notation built from them.

What the grid is: 7 Foundations x 4 Worlds.
    Worlds       a = Spiritual, b = Mental, c = Emotional, d = Physical
    Foundations  1 desire to be and be with God / 2 wisdom, insight, and knowledge /
                 3 life, vitality, and health / 4 companionship, love, and friendship /
                 5 worldly power, influence, and control / 6 material food and things /
                 7 lust, sex, and reproduction
    symbol       "<foundation><world>", e.g. "3b" = Mental life, vitality, and health
    number       the document numbers them 1..28 world by world: 1a..7a = 1..7, 1b..7b = 8..14,
                 1c..7c = 15..21, 1d..7d = 22..28.  index() is that number minus one.

The definitions are read from a byte copy of the repository's capture
(`docs/working/gate2_closure/matched_ab_20260726/tootra_28_full_definitions.json`), vendored under
`foundations28_source/` and pinned by hash. They are returned VERBATIM and never paraphrased.

THE RULE THAT HAS ALREADY COST ONE EXPERIMENT (SMALL-MODEL-SEMANTIC-MATCH-v1): the CAS drive labels
F1..F7 (Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose) are a POSITION-BY-POSITION
relabelling (`docs/reference/tks_28_foundations_translation_key.md`), not paraphrases. Foundation 5 is
"worldly power, influence, and control", not "Agency". So this module converts POSITIONS only
(`"3b" <-> "F3|A"`) and never hands out a CAS drive name as the meaning of a Foundation.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / "foundations28_source" / "tootra_28_full_definitions.json"
SOURCE_SHA256 = "487d76354094d8e102935e43eacfa4f3194d059bcda375ad51422771f53f00fc"   # raw == LF-normalised (the file is LF)
SOURCE_ORIGIN = "docs/working/gate2_closure/matched_ab_20260726/tootra_28_full_definitions.json"
CANON_DOCUMENT = {"title": "28 Foundations 1.0", "file": "28 fOUNDATIONS 1.0.pdf", "bytes": 399302, "pages": 7,
                  "sha256_raw": "2c27443f447bd69901372edb1316be56a92490afc6f88055ce0c84ce7a871017",
                  "owner_ruling": "CANONICAL 28 FOUNDATIONS", "ruled_on": "2026-09-21"}

WORLDS = ("a", "b", "c", "d")
WORLD_NAMES = {"a": "Spiritual", "b": "Mental", "c": "Emotional", "d": "Physical"}
FOUNDATION_NUMBERS = (1, 2, 3, 4, 5, 6, 7)
# position-by-position only; see the module docstring
REGISTER_OF_WORLD = {"a": "T", "b": "A", "c": "f", "d": "E"}
WORLD_OF_REGISTER = {r: w for w, r in REGISTER_OF_WORLD.items()}


class Foundation28Error(ValueError):
    """A symbol, index or CAS position that is not one of the 28."""


def _load():
    raw = SOURCE.read_bytes()
    digest = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    if digest != SOURCE_SHA256:
        raise Foundation28Error("FOUNDATIONS28_SOURCE_CHANGED: %s != pinned %s" % (digest[:16], SOURCE_SHA256[:16]))
    data = json.loads(raw.decode("utf-8"))
    if data["world_map"] != WORLD_NAMES or sorted(data["definitions"]) != sorted(symbols()):
        raise Foundation28Error("FOUNDATIONS28_SOURCE_SHAPE: world map or the 28 symbols differ from the canon grid")
    return data


def symbols():
    """The 28 symbols in the document's own numbered order: 1a..7a, 1b..7b, 1c..7c, 1d..7d."""
    return ["%d%s" % (k, w) for w in WORLDS for k in FOUNDATION_NUMBERS]


def _parse(symbol):
    if not isinstance(symbol, str) or len(symbol) != 2 or symbol[0] not in "1234567" or symbol[1] not in WORLDS:
        raise Foundation28Error("NOT_A_FOUNDATION_SYMBOL: %r (expected one digit 1-7 and one world a-d, e.g. '3b')" % (symbol,))
    return int(symbol[0]), symbol[1]


def index(symbol):
    """0..27, the document's number minus one ("1a" -> 0, "1b" -> 7, "7d" -> 27)."""
    k, w = _parse(symbol)
    return 7 * WORLDS.index(w) + (k - 1)


def symbol(position):
    """Inverse of index(). Accepts a real int only -- not a bool, not a float that happens to equal one."""
    if isinstance(position, bool) or not isinstance(position, int) or not 0 <= position < 28:
        raise Foundation28Error("NOT_A_FOUNDATION_INDEX: %r (expected an int 0..27)" % (position,))
    return "%d%s" % (position % 7 + 1, WORLDS[position // 7])


def title(sym):
    """The document's own heading for the entry, e.g. "Mental life, vitality, and health"."""
    k, w = _parse(sym)
    return "%s %s" % (WORLD_NAMES[w], _load()["drive_map"][str(k)])


def definition(sym):
    """The full elaborated definition, verbatim from the pinned capture."""
    _parse(sym)
    return _load()["definitions"][sym]


def to_cas_position(sym):
    """The CAS Drive-x-Register POSITION of a Foundation: "3b" -> "F3|A". A position, not a meaning."""
    k, w = _parse(sym)
    return "F%d|%s" % (k, REGISTER_OF_WORLD[w])


def from_cas_position(position):
    """Inverse of to_cas_position(): "F3|A" -> "3b"."""
    if (not isinstance(position, str) or len(position) != 4 or position[0] != "F" or position[1] not in "1234567"
            or position[2] != "|" or position[3] not in WORLD_OF_REGISTER):
        raise Foundation28Error("NOT_A_CAS_DRIVE_REGISTER_POSITION: %r (expected e.g. 'F3|A'; registers are T, A, f, E)" % (position,))
    return "%s%s" % (position[1], WORLD_OF_REGISTER[position[3]])


# Things a careful reader of the canon document should know. Recorded, never silently "fixed".
KNOWN_DISCREPANCIES = [
    {"id": "F28-1", "where": "repository capture vs the PDF, entry 3b", "status": "FLAG_FOR_HUMAN_REVIEW",
     "detail": "the PDF ends the entry with the bare word 'Curiosity' (no full stop); the capture has 'Curiosity.'"},
    {"id": "F28-2", "where": "repository capture vs the PDF, entry 6b", "status": "FLAG_FOR_HUMAN_REVIEW",
     "detail": "the PDF runs two sentences together ('...occupy the mind's attention Conceptualizing sustainability...'); the capture inserts a full stop between them"},
    {"id": "F28-3", "where": "repository capture vs the PDF, entry 1c", "status": "FLAG_FOR_HUMAN_REVIEW",
     "detail": "the PDF uses double quotation marks around raptured / caught up / catching the Holy Ghost; the capture uses single quotation marks"},
    {"id": "F28-4", "where": "the PDF itself, page 6 (the coloured chart)", "status": "FLAG_FOR_HUMAN_REVIEW",
     "detail": "every row of the Mental, Emotional and Physical blocks is labelled with the suffix 'a' (only the first Mental row says '1b'); the table on page 1 and the 28 numbered definitions use b, c and d correctly. This module follows page 1 and the numbered definitions."},
    {"id": "F28-5", "where": "the PDF itself, page 1", "status": "NOTE",
     "detail": "the page-1 table prints the blocks as Spiritual | Emotional over Mental | Physical, while the numbered definitions run Spiritual, Mental, Emotional, Physical (a, b, c, d). The numbering 1..28 is taken from the numbered definitions. The heading 'EMOTIONTAL' is a spelling slip in the document."},
    {"id": "F28-6", "where": "word-level comparison, all 28 entries", "status": "MEASURED",
     "detail": "25 of 28 captured definitions are found verbatim in the PDF text (whitespace, hyphenation and curly quotes normalised); the other three differ only as F28-1..3 describe"},
]
