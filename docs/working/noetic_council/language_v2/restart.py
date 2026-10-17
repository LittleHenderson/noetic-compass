"""restart.py -- RB-C4's RESTART_FALLBACK, wired into the language build.

WHERE THE MECHANISM COMES FROM
------------------------------
It is copied in, not invented. The source is `rb_c4/fitg.py` (read only; nothing in that folder
was edited):

  * `fit_routes` (fitg.py:150-179): "K starts (K = 8 only in DRAW; k = 0 = the consistency-checked
    start). fallback = RESTART_FALLBACK: start k = 0 only, then, if it leaves unexplained training
    rows, up to 8 seeded starts k = 1..8. Keep the start with the fewest unexplained training
    rows, ties to the lower k."
  * `route_fit_once` (fitg.py:96-147): one start -- assign rows to routes, refit each on its own
    rows, reassign to the clear best-explaining route (`CLEAR` = 21/20, fitg.py:51), repeat to a
    fixed point (cap `MAX_ITER` = 20, fitg.py:52), with the seeded draw only at
    `rng = _random.Random(seed) if k > 0 else None` (fitg.py:109).
  * The measured result, `rb_c4/RESULTS.md:43`: fired 8,828 times, an alternative start kept
    7,823 times; `RESULTS.md:52`: "a FIT-START win, not a proposal win."

WHAT A "FIT" IS IN THIS BUILD
-----------------------------
The language layer's only acceptance test is the round trip: `parse(render(C, w)) == C`
(`roundtrip.py:5-8`). A **content** is this build's row. A **wording** is this build's route:
`cce_render.wordings(content)` is the frozen list of lossless ways to say one content, CANON
first (`cce_render.Wording`). Start 0 says every content in the fixed twin; a seeded start says
each content in one of its other wordings, drawn from the seed. A content is **explained** when
the sentence said under its chosen wording reads back to the same content.

So: the fallback fires only when the fixed twin leaves a content unexplained, tries the seeded
wordings, and keeps the wording choice that explains the most contents. On the language build as
it stands that never happens -- `tap.world_demo()` reads back every station in the fixed twin --
and the reading says so rather than pretending to have helped. What it does buy is the
alternative before silence: a content whose CANON sentence fails read-back is retried in the
other wordings it has, instead of the tap saying nothing on the first failure.

AND THE WALL: A RESTART CANNOT SAY ANYTHING UNVERIFIED
------------------------------------------------------
A restart here proposes a wording. Nothing may be said until the round-trip receipt passes and
the independent CAS validator agrees, which is `tap.tap()`'s existing rule. `RestartResult.
accepted_forms` is the only reader that hands a sentence back as sayable, it demands a passing
`roundtrip.Receipt` for every candidate, and it refuses with `RESTART_RESULT_NOT_VERIFIED`
otherwise. A start that explains every content and is kept still cannot make a sentence sayable
without that receipt.

CLAIM CEILING (verbatim from the owning instruction):
    CONTROLLED ENGLISH ONLY. NOT OPEN CONVERSATION. FORM ONLY, NO MEANING CLAIM.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import random

import cce_parse
import cce_render
import roundtrip as RT

__all__ = [
    "MAX_STARTS", "MAX_ITER", "CLEAR", "FALLBACK_STARTS",
    "Saying", "StartRecord", "StartOutcome", "RestartLedger", "RestartResult",
    "RestartRefusal", "restart_fallback", "make_wording_start", "wording_refit",
    "default_seed_of", "wordings_of",
]

#: fitg.py:171 -- the fallback appends the seeded starts 1..8.
MAX_STARTS = 8
FALLBACK_STARTS = tuple(range(1, MAX_STARTS + 1))
#: fitg.py:52 -- "cap 20". fitg.py:51 -- "at least 21/20 times every other unblocked route".
MAX_ITER = 20
#: The clear-winner mark as an exact integer pair, so this module needs no float and no
#: `fractions` import (which this package's `numbers.py` shadowing makes order-sensitive): a
#: winner is clear when `winner * CLEAR_DEN >= CLEAR_NUM * other`. 21/20, exactly as fitg.py:51.
CLEAR = (21, 20)
CLEAR_NUM, CLEAR_DEN = CLEAR

#: Refusal codes.
RESTART_NEEDS_A_START = "RESTART_NEEDS_A_START"
RESTART_NEEDS_CONTENTS = "RESTART_NEEDS_CONTENTS"
RESTART_BAD_SEED_OF = "RESTART_BAD_SEED_OF"
RESTART_BAD_SEED = "RESTART_BAD_SEED"
RESTART_BAD_START = "RESTART_BAD_START"
RESTART_RESULT_NOT_VERIFIED = "RESTART_RESULT_NOT_VERIFIED"

# UNDECIDED IN SOURCES: which exact numbers the fallback uses, when fitg.py freezes 8 seeded starts and a 20-iteration cap -- fitg.py:52 and :171 give both numbers for rb_c4's own grammar fit and no source says whether another host must use the same two, so this build uses 8 and 20 exactly as rb_c4 froze them.
# UNDECIDED IN SOURCES: how a start is scored when the host has no yields, when fitg.py keeps the fewest unexplained rows and breaks ties by the exact residual sum -- fitg.py:167 compares `res` only, and `res` comes from yields this build does not have, so this build counts unexplained contents and breaks ties by the lower start index alone.
# UNDECIDED IN SOURCES: whether a wording that fails read-back may be retried within one start, when fitg.py reassigns a row only to a route that is a clear winner -- fitg.py:135-138 requires a `CLEAR` win before a row moves, so this build retries a failing content only with a wording whose support is a clear winner, which with one sentence per content never happens, and the start's own choice therefore stands.
# UNDECIDED IN SOURCES: whether the restart fallback belongs in the language layer at all, when FACULTIES.md section 2.3 puts it in pondering and no source says the language skin needs one -- the owning instruction names this build as one of the two the mechanisms must be wired into, so this build wires it into the tap as a retry before silence, and the reading states that on today's build it never fires.


class RestartRefusal(Exception):
    """A refusal with a stable code. Nothing here is ever a guess."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclasses.dataclass(frozen=True)
class Saying:
    """One candidate sentence: the content it says, the wording it uses, and the sentence.

    A route in rb_c4 is a recipe; here it is a wording of one content. `sentence` is what the
    wording produces -- a proposal until the round-trip receipt passes.
    """

    content_key: str
    wording_id: int
    sentence: str
    tier: str = ""
    wording: object = None

    @property
    def proposal(self) -> tuple:
        return (self.content_key, self.wording_id)


@dataclasses.dataclass(frozen=True)
class StartOutcome:
    """What one start produced: the contents it explains and the sentences it proposes."""

    start: int
    seed: int
    explained: tuple = ()
    candidates: tuple = ()
    iterations: int = 0
    fixed_point: bool = False
    refused: str = ""


@dataclasses.dataclass(frozen=True)
class StartRecord:
    """One line of the restart ledger: the seed, the start, the rows explained, and kept or not."""

    start: int
    seed: int
    rows_total: int
    rows_explained: int
    kept: bool
    iterations: int = 0
    fixed_point: bool = False
    refused: str = ""
    why: str = ""

    @property
    def unexplained(self) -> int:
        return self.rows_total - self.rows_explained

    def as_dict(self) -> dict:
        return {
            "start": self.start,
            "seed": self.seed,
            "rows_total": self.rows_total,
            "rows_explained": self.rows_explained,
            "kept": self.kept,
            "iterations": self.iterations,
            "fixed_point": self.fixed_point,
            "refused": self.refused,
            "why": self.why,
        }


class RestartLedger:
    """Append-only record of every start every call tried. Nothing is ever removed."""

    def __init__(self) -> None:
        self._rows: list = []

    def record(self, row: StartRecord) -> StartRecord:
        if not isinstance(row, StartRecord):
            raise RestartRefusal(
                RESTART_BAD_START, f"the ledger holds StartRecords, got {type(row).__name__}"
            )
        self._rows.append(row)
        return row

    def rows(self) -> tuple:
        return tuple(self._rows)

    def attempts(self) -> int:
        return len(self._rows)

    def kept_alternatives(self) -> int:
        return sum(1 for row in self._rows if row.kept and row.start > 0)

    def fired(self) -> int:
        return sum(1 for row in self._rows if row.start > 0)

    def as_dicts(self) -> tuple:
        return tuple(row.as_dict() for row in self._rows)

    def digest(self) -> str:
        payload = json.dumps([row.as_dict() for row in self._rows], sort_keys=True,
                             separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _mark_kept(self, start: int) -> None:
        for row in self._rows:
            if row.start == start and not row.kept:
                object.__setattr__(row, "kept", True)
                return
        raise RestartRefusal(
            RESTART_BAD_START,
            f"no ledger line for start {start} exists, so nothing can be marked kept",
        )

    def __len__(self) -> int:
        return len(self._rows)

    def __repr__(self) -> str:
        return "RestartLedger(%d starts, %d kept alternatives)" % (
            len(self._rows), self.kept_alternatives()
        )


class RestartResult:
    """What the fallback hands back: candidate sentences, and the record of every start tried.

    There is no `ok`, no `admitted`, no `said` and no method that returns a truth word.
    `proposed_sayings` is what a caller may try to say. `accepted_forms` is the only reader that
    hands sentences back as sayable, it demands a passing round-trip receipt for every candidate,
    and it refuses otherwise.
    """

    def __init__(self, candidates, *, start_kept, ledger, rows_total, fallback_fired) -> None:
        if not isinstance(ledger, RestartLedger):
            raise RestartRefusal(
                RESTART_BAD_START, f"a restart result carries its ledger, got {type(ledger).__name__}"
            )
        self._candidates = tuple(candidates)
        self._start_kept = start_kept
        self._ledger = ledger
        self._rows_total = rows_total
        self._fallback_fired = bool(fallback_fired)

    @property
    def start_kept(self) -> int:
        return self._start_kept

    @property
    def rows_total(self) -> int:
        return self._rows_total

    @property
    def fallback_fired(self) -> bool:
        return self._fallback_fired

    @property
    def rows_explained(self) -> int:
        for row in self._ledger.rows():
            if row.kept:
                return row.rows_explained
        return 0

    @property
    def unexplained(self) -> int:
        return self._rows_total - self.rows_explained

    @property
    def starts_used(self) -> int:
        return self._ledger.attempts()

    def receipt(self) -> tuple:
        """fitg.py:176-179's receipt fields, in the same names."""
        return (
            ("start_kept", self._start_kept),
            ("starts_used", self.starts_used),
            ("train_residual_rows", self.unexplained),
            ("fallback_fired", self._fallback_fired),
            ("fallback_kept_alternative", self._fallback_fired and self._start_kept > 0),
        )

    def as_dict(self) -> dict:
        return {
            "start_kept": self._start_kept,
            "starts_used": self.starts_used,
            "rows_total": self._rows_total,
            "rows_explained": self.rows_explained,
            "unexplained": self.unexplained,
            "fallback_fired": self._fallback_fired,
            "fallback_kept_alternative": self._fallback_fired and self._start_kept > 0,
            "candidates": [
                {"content": item.content_key, "wording_id": item.wording_id,
                 "sentence": item.sentence, "tier": item.tier}
                for item in self._candidates
            ],
            "starts": [row.as_dict() for row in self._ledger.rows()],
        }

    def proposed_sayings(self) -> tuple:
        """The sentences this restart proposes. Each one still needs its receipt to be said."""
        return tuple(self._candidates)

    def accepted_forms(self, receipts) -> tuple:
        """Return the sentences that carry a passing round-trip receipt, or refuse.

        `receipts` maps a content key to a `roundtrip.Receipt`. Refuses unless every proposed
        content has one, unless each is a receipt this package produced, and unless each passed.
        """
        if not isinstance(receipts, dict):
            raise RestartRefusal(
                RESTART_RESULT_NOT_VERIFIED,
                f"a restart result is accepted by receipts keyed by content, got "
                f"{type(receipts).__name__}; nothing about a start makes a sentence sayable",
            )
        accepted = []
        for item in self._candidates:
            receipt = receipts.get(item.content_key)
            if receipt is None:
                raise RestartRefusal(
                    RESTART_RESULT_NOT_VERIFIED,
                    f"the kept start {self._start_kept} proposes a sentence for "
                    f"{item.content_key!r} and no receipt was given for it",
                )
            if not isinstance(receipt, RT.Receipt):
                raise RestartRefusal(
                    RESTART_RESULT_NOT_VERIFIED,
                    f"the object given for {item.content_key!r} is not a round-trip receipt",
                )
            if not receipt.ok:
                raise RestartRefusal(
                    RESTART_RESULT_NOT_VERIFIED,
                    f"the receipt for {item.content_key!r} did not hold "
                    f"({list(receipt.rejection_codes)}); a restart never says it anyway",
                )
            accepted.append(item)
        return tuple(accepted)

    def __repr__(self) -> str:
        return "RestartResult(start_kept=%r, explained=%d/%d, %d sentence(s))" % (
            self._start_kept, self.rows_explained, self._rows_total, len(self._candidates)
        )


def default_seed_of(start: int) -> int:
    """The seed a start is given when the caller names no seed function, recorded on every line."""
    if isinstance(start, bool) or not isinstance(start, int) or start < 0:
        raise RestartRefusal(RESTART_BAD_SEED, f"a start index is a non-negative integer, got {start!r}")
    return 20261016 * 1000 + start


def restart_fallback(fit_start, contents, *, seed_of=None, max_starts=MAX_STARTS, ledger=None,
                     fallback=True):
    """fitg.py:150-179 in this build's words: start 0, then the seeded starts if it left rows.

    `fit_start(start, seed)` runs one start and returns a `StartOutcome`. The order of the source
    is kept: run start 0 (no draw); if it left contents unexplained and `fallback`, run the seeded
    starts 1..max_starts; keep the fewest unexplained, ties to the lower start; record every start
    in the ledger with its seed, its start, its explained count and whether it was kept.
    """
    materialised = tuple(contents)
    if not materialised:
        raise RestartRefusal(
            RESTART_NEEDS_CONTENTS,
            "a restart with no content has nothing to explain; it would return the wording it "
            "was handed and claim a fit",
        )
    if not callable(fit_start):
        raise RestartRefusal(
            RESTART_NEEDS_A_START,
            f"the fallback needs one start to run, got {type(fit_start).__name__}",
        )
    if isinstance(max_starts, bool) or not isinstance(max_starts, int) or max_starts < 0:
        raise RestartRefusal(RESTART_BAD_START, f"max_starts is a non-negative integer, got {max_starts!r}")
    seeds = default_seed_of if seed_of is None else seed_of
    if not callable(seeds):
        raise RestartRefusal(RESTART_BAD_SEED_OF, f"a seed function must be callable, got {type(seeds).__name__}")
    book = ledger if ledger is not None else RestartLedger()
    if not isinstance(book, RestartLedger):
        raise RestartRefusal(RESTART_BAD_START, f"a ledger is a RestartLedger, got {type(book).__name__}")

    looped = [0]
    fired = False
    best = None
    index = 0
    while index < len(looped):
        start = looped[index]
        index += 1
        seed = 0 if start == 0 else seeds(start)
        outcome = fit_start(start, seed)
        if not isinstance(outcome, StartOutcome):
            raise RestartRefusal(
                RESTART_BAD_START,
                f"start {start} returned {type(outcome).__name__}; a start returns a StartOutcome",
            )
        explained = 0 if outcome.refused else len(outcome.explained)
        book.record(StartRecord(
            start=start,
            seed=seed,
            rows_total=len(materialised),
            rows_explained=explained,
            kept=False,
            iterations=outcome.iterations,
            fixed_point=outcome.fixed_point,
            refused=outcome.refused,
            why=("FALLBACK_FIRED" if start > 0 else "CONSISTENCY_CHECKED_START"),
        ))
        if not outcome.refused and (best is None or explained > best[0]):
            best = (explained, start, outcome)
        if fallback and start == 0 and not fired and (best is None or best[0] < len(materialised)):
            fired = True
            looped.extend(range(1, max_starts + 1))

    if best is None:
        return RestartResult((), start_kept=0, ledger=book, rows_total=len(materialised),
                             fallback_fired=fired)
    explained, start_kept, outcome = best
    book._mark_kept(start_kept)
    return RestartResult(outcome.candidates, start_kept=start_kept, ledger=book,
                         rows_total=len(materialised), fallback_fired=fired)


def wordings_of(content) -> tuple:
    """Every lossless wording of one content, CANON first (cce_render.wordings)."""
    return tuple(cce_render.wordings(content))


def make_wording_start(contents, *, render=None, read_back=None, tables=None):
    """One start over these contents: fitg.py:118-147's loop, on read-backs instead of yields.

    A start says every content in one of its wordings: start 0 in the fixed twin (the first
    wording, no draw), a seeded start in a wording drawn from the seed. A content is explained
    when its sentence reads back to the same content. The reassignment step keeps a content on
    its wording unless another wording is a clear winner by support (`CLEAR`, fitg.py:51), which
    is fitg.py:135-138's rule with one sentence standing in for one row's witness count.

    `tables` lets a caller hand in its own wording lists, which is how a test exercises the
    mechanism on a supplied host (the way `rb_c4`'s own fixtures did). Left out, the real
    `cce_render.wordings` is used.
    """
    materialised = tuple(contents)
    if not materialised:
        raise RestartRefusal(RESTART_NEEDS_CONTENTS, "no content was named, so no start can say anything")
    renderer = cce_render.render if render is None else render
    parser = _default_read_back if read_back is None else read_back
    tables = tuple(wordings_of(content) for content in materialised) if tables is None else tuple(
        tuple(table) for table in tables)
    for content, table in zip(materialised, tables):
        if not table:
            raise RestartRefusal(
                RESTART_NEEDS_A_START,
                f"the content {getattr(content, 'omega', content)!r} has no wording, so it has "
                f"no start",
            )

    def key_of(index):
        return "c%d" % (index,)

    def fit_start(start, seed):
        rng = random.Random(seed) if start > 0 else None          # fitg.py:109
        chosen = []
        for table in tables:
            if rng is not None and len(table) > 1:
                chosen.append(rng.randrange(len(table)))
            else:
                chosen.append(0)                                   # start 0: the fixed twin
        fixed, iterations, explained = False, 0, ()
        for iterations in range(1, MAX_ITER + 1):
            sentences = {}
            explained_now = []
            for index, (content, table) in enumerate(zip(materialised, tables)):
                sentence = renderer(content, table[chosen[index]])
                sentences[index] = sentence
                if parser(sentence) == content:
                    explained_now.append(key_of(index))
            new = list(chosen)
            for index, (content, table) in enumerate(zip(materialised, tables)):
                if key_of(index) in explained_now:
                    continue
                support = {}
                for option in range(len(table)):
                    support[option] = sum(
                        1 for other, other_table in zip(range(len(materialised)), tables)
                        if other_table is table and parser(renderer(materialised[other], table[option]))
                        == materialised[other]
                    )
                best_option = max(range(len(table)), key=lambda option: (support[option], -option))
                clear = all(support[best_option] * CLEAR_DEN >= CLEAR_NUM * support[other]
                            for other in range(len(table)) if other != best_option)
                if clear and support[best_option] > 0:
                    new[index] = best_option
            if new == chosen:
                fixed = True
                break
            chosen = new
        explained = tuple(
            key_of(index) for index, (content, table) in enumerate(zip(materialised, tables))
            if parser(renderer(content, table[chosen[index]])) == content
        )
        candidates = []
        for index, (content, table) in enumerate(zip(materialised, tables)):
            if key_of(index) not in explained:
                continue
            wording = table[chosen[index]]
            candidates.append(Saying(key_of(index), wording.wid,
                                     renderer(content, wording), wording.tier, wording))
        return StartOutcome(start=start, seed=seed, explained=explained,
                            candidates=tuple(candidates), iterations=iterations,
                            fixed_point=fixed)

    fit_start.contents = materialised
    return fit_start


def _default_read_back(sentence):
    """Parse a said sentence; a sentence that is not CCE reads back as nothing."""
    report = cce_parse.parse_report(sentence)
    return report["content"]


def wording_refit(*, seed_of=None, max_starts=MAX_STARTS, ledger=None, render=None,
                  read_back=None):
    """A `say` callable for the tap: choose wordings with the restart fallback.

    It returns the `RestartResult` so the caller can read the ledger, the kept start and the
    receipt, and it never returns anything the round-trip receipt has not accepted: the caller
    still asks `roundtrip.round_trip` for each sentence, and `tap.tap` already refuses to say a
    sentence whose receipt did not hold.
    """
    book = ledger if ledger is not None else RestartLedger()

    def choose(contents):
        contents = tuple(contents)
        if not contents:
            raise RestartRefusal(RESTART_NEEDS_CONTENTS, "the tap has nothing to say")
        start = make_wording_start(contents, render=render, read_back=read_back)
        return restart_fallback(start, contents, seed_of=seed_of, max_starts=max_starts,
                               ledger=book)

    choose.ledger = book
    return choose
