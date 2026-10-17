"""tap.py -- TAP: read a station and say it in CCE English, without changing the thought.

TAP_AND_INJECT.md section 1, in the owner's words: "interrupting a person while they are deep
in thought". At a station boundary the tap

  1. renders the station's content in the fixed twin wording (no draw in the first test);
  2. requires the round-trip receipt parse(render(C)) == C, and says NOTHING when it fails;
  3. cross-checks the CAS side with cas_validator.py, which never sees the English;
  4. prefixes the evidence tag: an admitted content is said as "I checked: ...", the user's
     content as "You said: ...", and UNDETERMINED as exactly "I cannot tell.";
  5. writes nothing: the station digest before the tap equals the digest after it, and the tap
     log is a separate log, so a run with taps replays identically without them.

A station field with NO CCE form is a FORM gap. A FORM gap contributes NO SENTENCE and is
counted -- it is never skipped silently and never approximated with a near sentence.
"""

from __future__ import annotations

import hashlib
import json

import cce_render
import roundtrip as RT
from content import CASContent, N, Refusal, State, Term

FIXED_UNDETERMINED = cce_render.FIXED_UNDETERMINED

# STATIONS.md section 2, one line each.
STATION_NAMES = {
    "S0": "thought head",
    "S1": "CJT trigger",
    "S2": "CJT bias",
    "S3": "CJT arrival",
    "S4": "operating point",
    "S5": "RPM link",
    "S6": "next stage",
}

STATION_STATES = ("SPOKEN", "FORM_GAP", "NO_EVIDENCE", "REFUSED")

# What CCE v0.1 has no sentence form for, named exactly as the station builders below name it.
# A station holding any of these contributes NO sentence and is counted as a FORM gap
# (TRANSLATOR_SPEC section 8: "Two of seven categories are only partly covered. That is stated,
# not hidden."). Each entry is a LACUNA cell in the coverage ledger, not a silence.
KNOWN_FORM_GAPS = (
    "order shape",          # S0: SINGLE / CHAIN / ALT / SUM
    "drive state",          # S0 in RB-I: pi_t and k_t are numbers in a log, not speech
    "yield Y_T",            # S3: min_i(x_i / a_i)
    "limiting reagent",     # S3
    "region",               # S4: CUTOFF / ACTIVE / SATURATION / BREAKDOWN
    "outcome",              # S4: INTENDED / OPPOSITE / OFF_AXIS / UNKNOWN
    "asom word",            # S4: the display word, never said alone
    "receipt sentence",     # S5: per-level EPS-after-ETA at answer time
)

# UNDECIDED IN SPEC: does TAP draw a wording, when the design says no draw and the spec requires every said wording to round-trip?
# This build says the fixed twin and offers wording=... for a later test; it never draws at random.
# UNDECIDED IN SPEC: when one station field has no CCE form, does the whole station stay silent or is the rest said?
# This build keeps the whole station silent and counts the FORM gap, because a partial sentence
# about a station would state less than the station holds while sounding complete.


class Station:
    """One station record.

    content      the CAS content that exists at the station and can be said
    unspeakable  the names of the fields that have NO CCE form (a FORM gap), e.g. a yield
                 number or an ASOM word. Never paraphrased, never dropped silently.
    """

    __slots__ = ("name", "content", "unspeakable", "faculty", "detail")

    def __init__(self, name: str, content: CASContent = None, unspeakable=(), faculty=None, detail=None):
        if name not in STATION_NAMES:
            raise ValueError("station %r is not one of %s" % (name, sorted(STATION_NAMES)))
        self.name = name
        self.content = content
        self.unspeakable = tuple(unspeakable)
        self.faculty = faculty
        self.detail = detail

    @property
    def speakable(self) -> bool:
        return self.content is not None and not self.unspeakable

    def digest(self) -> str:
        """What the station holds, as one digest. A tap must not move it."""
        payload = {"station": self.name,
                   "content": None if self.content is None else self.content.digest(),
                   "unspeakable": list(self.unspeakable),
                   "faculty": self.faculty}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False)
                              .encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return "Station(%s, %s)" % (self.name, "speakable" if self.speakable else "no sentence")


class World:
    """A tiny stand-in for the circuit: the stations one thought passes, plus the learned values
    and the path log. TAP must leave every one of them byte-identical."""

    def __init__(self, stations=(), learned=None, path_log=()):
        self.stations = {station.name: station for station in stations}
        self.learned = dict(learned or {})
        self.path_log = tuple(path_log)
        self.tap_log = []

    def digest(self) -> str:
        def plain(value):
            if isinstance(value, str):
                try:
                    return N.fraction_text(N.parse_number(value))
                except N.NumberRefusal:
                    return value
            return value

        payload = {
            "stations": sorted((name, station.digest()) for name, station in self.stations.items()),
            "learned": {key: plain(value) for key, value in sorted(self.learned.items())},
            "path_log": list(self.path_log),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False)
                              .encode("utf-8")).hexdigest()

    def station(self, name: str) -> Station:
        return self.stations[name]


class TapRecord:
    """What one tap did, in the spec's terms."""

    __slots__ = ("station", "state", "sentence", "wording_id", "receipt", "missing", "code",
                 "content_hash", "wrote_nothing", "digest_before", "digest_after")

    def __init__(self, station, state, sentence=None, wording_id=None, receipt=None, missing=(),
                 code=None, content_hash=None, wrote_nothing=True, digest_before=None,
                 digest_after=None):
        self.station = station
        self.state = state
        self.sentence = sentence
        self.wording_id = wording_id
        self.receipt = receipt
        self.missing = tuple(missing)
        self.code = code
        self.content_hash = content_hash
        self.wrote_nothing = wrote_nothing
        self.digest_before = digest_before
        self.digest_after = digest_after

    def record(self) -> dict:
        return {
            "station": self.station,
            "state": self.state,
            "sentence": self.sentence,
            "wording_id": self.wording_id,
            "missing_form": list(self.missing),
            "code": self.code,
            "content_hash": self.content_hash,
            "wrote_nothing": self.wrote_nothing,
            "digest_unchanged": (self.digest_before == self.digest_after
                                 if self.digest_before is not None and self.digest_after is not None
                                 else None),
            "receipt": None if self.receipt is None else self.receipt.to_dict(),
        }

    def __repr__(self) -> str:
        return "TapRecord(%s, %s, %r)" % (self.station, self.state, self.sentence)


def _with_evidence(content: CASContent, evidence: str) -> CASContent:
    """The evidence word is content (TRANSLATOR_SPEC section 2). A tap says admitted content as
    'I checked: ...' and the user's content as 'You said: ...'.

    A turn that is not an ANSWER carries no evidence prefix: "I checked: New subject: ..." would
    claim something was checked that was not.
    """
    if content.evidence == evidence or content.turn != "ANSWER" or content.gate != "RIGHT_PATH":
        return content
    return CASContent(turn=content.turn, omega=content.omega, terms=content.terms,
                      recipe=content.recipe, relations=content.relations, evidence=evidence,
                      gate=content.gate, lacunae=content.lacunae, reason=content.reason,
                      fractal=content.fractal)


def tap(station: Station, world: World = None, wording=None, ledger=None) -> TapRecord:
    """Read one station. Says nothing at all when the station has no form."""
    before = world.digest() if world is not None else None
    missing = tuple(station.unspeakable)
    if station.content is None:
        record = TapRecord(station.name, "NO_EVIDENCE", code="NO_PROBE",
                           digest_before=before, digest_after=before)
        return _logged(world, record)
    if missing:
        # A FORM gap: the station holds content that CCE cannot say. No sentence, counted.
        record = TapRecord(station.name, "FORM_GAP", missing=missing, code="NO_FORM",
                           content_hash=station.content.digest(),
                           digest_before=before, digest_after=before)
        return _logged(world, record)
    spoken = _with_evidence(station.content, "CHECKED")
    try:
        receipt = RT.round_trip(spoken, wording)
    except Refusal as exc:
        record = TapRecord(station.name, "REFUSED", code=exc.code,
                           content_hash=station.content.digest(),
                           digest_before=before, digest_after=before)
        return _logged(world, record)
    if not receipt.ok:
        # Rule: a sentence that fails read-back is refused, and the tap says nothing.
        record = TapRecord(station.name, "REFUSED", code=(receipt.rejection_codes or ("UNSAYABLE",))[0],
                           content_hash=station.content.digest(), receipt=receipt,
                           digest_before=before, digest_after=before)
        return _logged(world, record)
    independent = RT.check_independent(spoken)
    if not independent["ok"]:
        record = TapRecord(station.name, "REFUSED", code="INDEPENDENT_CHECK_FAILED",
                           content_hash=station.content.digest(), receipt=receipt,
                           digest_before=before, digest_after=before)
        return _logged(world, record)
    record = TapRecord(station.name, "SPOKEN", sentence=receipt.sentence,
                       wording_id=receipt.wording_id, receipt=receipt,
                       content_hash=station.content.digest(),
                       digest_before=before, digest_after=before)
    return _logged(world, record)


def _logged(world, record: TapRecord) -> TapRecord:
    if world is not None:
        record.digest_after = world.digest()
        record.wrote_nothing = record.digest_before == record.digest_after
        world.tap_log.append(record.record())      # the tap log is separate from the path log
    return record


def tap_all(world: World, order=None) -> dict:
    """Tap every station of a world and count what could and could not be said."""
    names = order or sorted(world.stations)
    records = [tap(world.stations[name], world) for name in names]
    counts = {state: 0 for state in STATION_STATES}
    for record in records:
        counts[record.state] += 1
    return {
        "records": records,
        "counts": counts,
        "sentences": [record.sentence for record in records if record.sentence is not None],
        "form_gaps": [{"station": record.station, "missing": list(record.missing)}
                      for record in records if record.state == "FORM_GAP"],
        "form_gap_count": counts["FORM_GAP"],
        "spoken_count": counts["SPOKEN"],
        "wrote_nothing": all(record.wrote_nothing for record in records),
    }


# --- station builders: real content of the shape STATIONS.md describes -----------------------------------------
def station_s0(omega: str, order_shape=None) -> Station:
    """The thought head. The Omega is sayable; the order's shape has no CCE form today."""
    unspeakable = ("order shape",) if order_shape is not None else ()
    return Station("S0", CASContent(omega=omega), unspeakable=unspeakable,
                   faculty="fit", detail={"order_shape": order_shape})


def station_s1(stock_amount, stock_of: str) -> Station:
    """The CJT trigger: the stock in memory."""
    content = CASContent(relations=(("stock", stock_amount, stock_of),))
    return Station("S1", content, faculty="integration", detail={"stock": (stock_amount, stock_of)})


def station_s2(recipe) -> Station:
    """The CJT bias: the recipe Theta(Omega). Speaks exactly, including p/q coefficients."""
    return Station("S2", CASContent(recipe=recipe), faculty="fit",
                   detail={"omega": recipe.omega})


def station_s3(yield_value=None, limiting=None, gate="RIGHT_PATH", region=None, outcome=None):
    """The CJT arrival. The gate word has a form. A yield number, a limiting reagent, a region
    and an outcome have none today: they are FORM gaps."""
    if gate == "UNDETERMINED":
        return Station("S3", CASContent(gate="UNDETERMINED"), faculty="refusal",
                       detail={"gate": gate})
    missing = tuple(name for name, value in (("yield Y_T", yield_value),
                                             ("limiting reagent", limiting),
                                             ("region", region),
                                             ("outcome", outcome)) if value is not None)
    return Station("S3", CASContent(), unspeakable=missing or ("yield Y_T",), faculty="self_notice",
                   detail={"yield": yield_value, "limiting": limiting, "region": region,
                           "outcome": outcome})


def station_s4(region=None, outcome=None) -> Station:
    """The operating point. No CCE form for either axis; the ASOM word is never said alone."""
    missing = tuple(name for name, value in (("region", region), ("outcome", outcome))
                    if value is not None) or ("region", "outcome")
    return Station("S4", CASContent(), unspeakable=missing, faculty="self_notice",
                   detail={"region": region, "outcome": outcome})


def station_s5(prerequisite: str, prerequisite_of: str, level: int = 1) -> Station:
    """The RPM link: the one-way prerequisite edge has a form; the receipt sentence does not."""
    content = CASContent(relations=(("needs_first", prerequisite_of, prerequisite),))
    return Station("S5", content, faculty="asking", detail={"level": level})


def station_s6(next_omega: str) -> Station:
    """The next stage: a new thought head has a form."""
    return Station("S6", CASContent(turn="ACK", omega=next_omega), faculty="curiosity")


def world_demo() -> World:
    """The world demo.py and test_all.py tap: six stations, one of them a FORM gap."""
    from content import Leakage, Recipe, RecipeTerm

    recipe = Recipe("Ω_dough", terms=(
        RecipeTerm("1/3", kind="state", state=State(5, domain="C")),
        RecipeTerm("2", kind="state", state=State(7, domain="O", register=("A",), drive="F6")),
    ), leakage=(Leakage("3/7", "Ω_steam"),), catalysts=("Ω_warmth",))
    return World(stations=(
        station_s0("Ω_dough", order_shape="CHAIN"),
        station_s1("4", "Ω_leaves"),
        station_s2(recipe),
        station_s3(yield_value="3/7", limiting="Male, cognitive", region="ACTIVE", outcome="INTENDED"),
        station_s5("Ω_leaves", "Ω_dough", level=1),
        station_s6("Ω_bread"),
    ), learned={"recipe_k0_slot0": "1/3", "recipe_k0_slot1": "7/10"},
        path_log=("S0", "S1", "S2", "S3", "S5", "S6"))
