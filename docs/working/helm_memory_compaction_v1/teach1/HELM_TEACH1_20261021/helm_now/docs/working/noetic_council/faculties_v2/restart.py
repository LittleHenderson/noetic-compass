"""restart.py -- RB-C4's RESTART_FALLBACK, wired into this build.

WHERE THE MECHANISM COMES FROM
------------------------------
It is copied in, not invented. The source is `rb_c4/fitg.py` (read only; nothing in that
folder was edited):

  * `fit_routes` (fitg.py:150-179) is the fallback itself. Its docstring, verbatim: "K starts
    (K = 8 only in DRAW; k = 0 = the consistency-checked start). fallback = RESTART_FALLBACK:
    start k = 0 only, then, if it leaves unexplained training rows, up to 8 seeded starts
    k = 1..8. Keep the start with the fewest unexplained training rows, ties to the lower k."
  * `route_fit_once` (fitg.py:96-147) is one start: assign rows to routes, refit each route on
    its rows, reassign each row to the route that explains it best, repeat to a fixed point
    (cap `MAX_ITER` = 20, fitg.py:52), with `CLEAR` = 21/20 as the "clear winner" mark
    (fitg.py:51) and the seeded draw at `rng = _random.Random(seed) if k > 0 else None`
    (fitg.py:109).
  * `certain_set` (fitg.py:79-93) is the order-free consistency pass: a row that exactly one
    route can explain is certain, and ties are settled by greedy backward elimination.
  * The measured result is `rb_c4/RESULTS.md:43`: "RESTART_FALLBACK: fired 8,828 times (all
    families, 3 seeds); an alternative start was kept 7,823 times", and RESULTS.md:52: "The
    randomness win is a FIT-START win, not a proposal win." That is the whole claim: randomness
    changes WHERE FITTING STARTS. It never chooses the answer.

THE THREE RULES THIS MODULE KEEPS, IN THE SOURCE'S OWN SHAPE
------------------------------------------------------------
1. **Start 0 is the consistency-checked start and makes no draw.** fitg.py:109 hands start 0
   no generator, so start 0 is deterministic.
2. **The fallback fires only when start 0 leaves real rows unexplained**, and then tries the
   seeded starts 1..8 (fitg.py:169-171). The kept start is the one with the fewest unexplained
   rows; ties go to the lower start (fitg.py:167).
3. **Every start is recorded**: its seed, the start it tried, the rows it explained, and
   whether it was kept (fitg.py:176-179 records `start_kept`, `starts_used`, `iterations`,
   `fixed_point`, `train_residual_rows`, `fallback_fired`, `fallback_kept_alternative`).

AND THE WALL: A RESTART CANNOT ACCEPT ANYTHING
----------------------------------------------
A restart is a proposal. Its output is a list of canonical forms that go into the held buffer
as `HELD`, through the same faculty door every other proposal uses. Nothing here mints a
verdict (this module does not import the verifier's seal and cannot call `guard.verify`'s
private mint), and `RestartResult.accepted_forms` refuses with
`RESTART_RESULT_NOT_VERIFIED` unless every form it is asked to hand back carries a sealed
`ADMITTED` verdict from `guard.verify`. A start that explains 8 of 8 rows and is kept still
cannot be believed without that verdict; a start the verifier refuses stays `HELD` forever.
That is the same shape as the source, where a fit is handed to VERIFY and to the memory check
and is refused if they refuse.

WHAT IS DIFFERENT HERE, AND WHY (each is an `UNDECIDED IN SOURCES` line, listed in README.md)
---------------------------------------------------------------------------------------------
  * fitg.py scores a start by exact yields and breaks ties by an exact residual sum
    (fitg.py:65-76, 167). This build has no `y`, so a row is explained or it is not, and the
    tie-break is the lower start index alone.
  * fitg.py's routes are recipes with cells and coefficients. This build has no recipe book, so
    a route here is a named canonical form plus the cells it claims, and the caller names them.
  * fitg.py's SUM skeleton and BLEND skeleton get no restarts (fitg.py:6). This build has one
    kind of start, so the restriction has nothing to apply to.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import random
from fractions import Fraction

import guard
from guard import ADMITTED, GuardRefusal

__all__ = [
    "MAX_STARTS", "MAX_ITER", "CLEAR", "FALLBACK_STARTS",
    "Route", "StartRecord", "StartOutcome", "RestartLedger", "RestartResult",
    "RestartRefusal", "restart_fallback", "routes_from_reading", "restart_refit",
    "default_seed_of",
]

#: fitg.py:171 -- the fallback appends the seeded starts 1..8.
MAX_STARTS = 8
FALLBACK_STARTS = tuple(range(1, MAX_STARTS + 1))
#: fitg.py:52 -- "cap 20".
MAX_ITER = 20
#: fitg.py:51 -- "a clear winner: at least 21/20 times every other unblocked route's yield".
CLEAR = Fraction(21, 20)

#: Refusal codes.
RESTART_NEEDS_A_START = "RESTART_NEEDS_A_START"
RESTART_NEEDS_ROWS = "RESTART_NEEDS_ROWS"
RESTART_ROWS_MUST_BE_REAL = "RESTART_ROWS_MUST_BE_REAL"
RESTART_BAD_SEED_OF = "RESTART_BAD_SEED_OF"
RESTART_BAD_SEED = "RESTART_BAD_SEED"
RESTART_BAD_START = "RESTART_BAD_START"
RESTART_BAD_ROUTE = "RESTART_BAD_ROUTE"
RESTART_RESULT_NOT_VERIFIED = "RESTART_RESULT_NOT_VERIFIED"
RESTART_RESULT_IS_NOT_CANDIDATES = "RESTART_RESULT_IS_NOT_CANDIDATES"

# UNDECIDED IN SOURCES: which exact numbers the fallback uses, when fitg.py freezes 8 seeded starts and a 20-iteration fixed-point cap -- fitg.py:52 and :171 give both numbers for rb_c4's own grammar fit and no source says whether another host must use the same two, so this build uses 8 and 20 exactly as rb_c4 froze them and records them as constants rather than scaling them.
# UNDECIDED IN SOURCES: how a start is scored when the host has no yields, when fitg.py keeps the fewest unexplained rows and breaks ties by the exact residual sum -- fitg.py:167 compares `res` only, and `res` comes from yields that this build does not have, so this build counts unexplained rows and breaks ties by the lower start index alone, which is the second half of fitg.py's own rule with the first half absent.
# UNDECIDED IN SOURCES: whether the fallback may fire a second time within one fit call, when fitg.py fires once per call (`fallback and k == 0 and not fired`) -- fitg.py:169 sets `fired = True` before the starts are appended and never resets it, so this build fires at most once per call and records `fallback_fired` as a yes or no.
# UNDECIDED IN SOURCES: where a restart's candidate routes come from, when rb_c4's routes are recipes held by the grammar and this build has no grammar and no recipe book -- FACULTIES.md section 2.3 says pondering re-fits each group "with the RB-C4 restart fallback" and never says where the alternatives come from, so this build takes the routes from the caller, or from the Bias's own admitted facts when a fact names the cells it covers, and refuses with RESTART_NEEDS_A_START when nothing is named.


class RestartRefusal(Exception):
    """A refusal with a stable code. Nothing here is ever a guess."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- #
# What a route is here
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class Route:
    """One candidate account of some rows: a canonical form and the cells it claims.

    In rb_c4 a route is a recipe and its cells are its terms (fitg.py:102 `terms[q]`). Here the
    recipe book is not in this build, so a route is what the caller can honestly name: a form,
    and the cells it claims to explain. The empirical part -- which route explains which row --
    is decided by the rows themselves, exactly as fitg.py:104-108 decides it.
    """

    form: str
    target: str = ""
    cells: tuple = ()

    def __post_init__(self) -> None:
        if not isinstance(self.form, str) or not self.form.strip():
            raise RestartRefusal(
                RESTART_BAD_ROUTE, f"a route names a canonical form, got {self.form!r}"
            )
        if isinstance(self.cells, str):
            object.__setattr__(self, "cells", (self.cells,))
        for cell in self.cells:
            if not isinstance(cell, str) or not cell.strip():
                raise RestartRefusal(
                    RESTART_BAD_ROUTE, f"route {self.form!r} claims a cell named {cell!r}"
                )

    def claims(self, cell) -> bool:
        return cell in self.cells

    @property
    def proposal(self) -> tuple:
        return (self.form, self.target)


# --------------------------------------------------------------------------- #
# One start, and the record of it
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class StartOutcome:
    """What one start produced: the rows it explains and the candidates it proposes.

    `refused` is how a start that cannot fit at all reports itself, the way fitg.py's
    `route_fit_once` returns a refusal string (fitg.py:126, 144) instead of a fit.
    """

    start: int
    seed: int
    explained: tuple = ()
    candidates: tuple = ()
    iterations: int = 0
    fixed_point: bool = False
    refused: str = ""


@dataclasses.dataclass(frozen=True)
class StartRecord:
    """One line of the restart ledger: the seed, the start, the rows explained, and kept or not.

    This is the record the owning instruction asks for -- "Every restart records its seed, the
    start it tried, the rows explained, and whether it was kept" -- and it carries the three
    fields fitg.py puts in its own receipt (fitg.py:176-179): `start_kept`, `iterations`,
    `fixed_point`.
    """

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

    def __len__(self) -> int:
        return len(self._rows)

    def _mark_kept(self, start: int) -> None:
        """Mark exactly one ledger line as the kept start, in place.

        Object.__setattr__ is used on the frozen record so a StartRecord stays immutable to
        every other caller. The flag only ever moves False -> True, only for a start that was
        actually run, and only for the single start the fallback kept. No line is removed.
        """
        for row in self._rows:
            if row.start == start and not row.kept:
                object.__setattr__(row, "kept", True)
                return
        raise RestartRefusal(
            RESTART_BAD_START,
            f"no ledger line for start {start} exists, so nothing can be marked kept",
        )

    def __repr__(self) -> str:
        return "RestartLedger(%d starts, %d kept alternatives)" % (
            len(self._rows), self.kept_alternatives()
        )


# --------------------------------------------------------------------------- #
# The result: proposals, and nothing anyone can believe without a verdict
# --------------------------------------------------------------------------- #
class RestartResult:
    """What the fallback hands back: candidate forms, and the record of every start tried.

    There is no `verdict`, no `admitted`, no `accepted` attribute and no method that returns a
    truth word. `proposed_forms` is what a faculty may put in the buffer as `HELD`.
    `accepted_forms` is the only reader that hands forms back as accepted, it demands one sealed
    `ADMITTED` verdict per form, and it refuses otherwise -- so a restart cannot accept a result
    the verifier refused, because it has no other way to say a result is accepted.
    """

    def __init__(self, candidates, *, start_kept, ledger, rows_total, fallback_fired) -> None:
        if not isinstance(ledger, RestartLedger):
            raise RestartRefusal(
                RESTART_BAD_START, f"a restart result carries its ledger, got {type(ledger).__name__}"
            )
        self._candidates = tuple(tuple(item) for item in candidates)
        self._start_kept = start_kept
        self._ledger = ledger
        self._rows_total = rows_total
        self._fallback_fired = bool(fallback_fired)

    # -- the record ---------------------------------------------------------- #
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
            "candidates": [list(item) for item in self._candidates],
            "starts": [row.as_dict() for row in self._ledger.rows()],
        }

    # -- the proposals: HELD, always ---------------------------------------- #
    def proposed_forms(self) -> tuple:
        """The candidates this restart proposes. They enter the buffer as `HELD`."""
        return tuple(self._candidates)

    # -- the only way to be accepted: a sealed verdict per form -------------- #
    def accepted_forms(self, verdicts) -> tuple:
        """Return the forms that carry a sealed `ADMITTED` verdict, or refuse.

        `verdicts` maps a canonical form to a verdict. Refuses unless every proposed form has
        one, and unless every verdict is one `guard.verify` minted, in the word `ADMITTED`, on
        real evidence. There is no flag, no argument and no second reader that skips this.
        """
        if not isinstance(verdicts, dict):
            raise RestartRefusal(
                RESTART_RESULT_NOT_VERIFIED,
                f"a restart result is accepted by verdicts keyed by form, got "
                f"{type(verdicts).__name__}; nothing about a start makes a form true",
            )
        accepted = []
        for form, _target in self._candidates:
            verdict = verdicts.get(form)
            if verdict is None:
                raise RestartRefusal(
                    RESTART_RESULT_NOT_VERIFIED,
                    f"the kept start {self._start_kept} proposes {form!r} and no verdict was "
                    f"given for it; a restart proposes and the verifier decides",
                )
            if not guard.is_verdict(verdict):
                raise RestartRefusal(
                    RESTART_RESULT_NOT_VERIFIED,
                    f"the object given for {form!r} is not a verdict minted by guard.verify()",
                )
            if verdict.word != ADMITTED:
                raise RestartRefusal(
                    RESTART_RESULT_NOT_VERIFIED,
                    f"the verifier decided {verdict.word} for {form!r}; a refused start is not "
                    f"handed back as accepted",
                )
            accepted.append(form)
        return tuple(accepted)

    def __repr__(self) -> str:
        return "RestartResult(start_kept=%r, explained=%d/%d, %d candidate(s))" % (
            self._start_kept, self.rows_explained, self._rows_total, len(self._candidates)
        )


# --------------------------------------------------------------------------- #
# The fallback
# --------------------------------------------------------------------------- #
def default_seed_of(start: int) -> int:
    """The seed a start is given when the caller names no seed function.

    fitg.py derives its seeds from the run (`seed_of(k)`), and this build has no run, so the
    seed is a pure function of the start index. It is recorded on every ledger line, so a
    restart replays byte for byte.
    """
    if isinstance(start, bool) or not isinstance(start, int) or start < 0:
        raise RestartRefusal(RESTART_BAD_SEED, f"a start index is a non-negative integer, got {start!r}")
    return 20261016 * 1000 + start


def _check_rows(rows) -> tuple:
    materialised = tuple(rows)
    if not materialised:
        raise RestartRefusal(
            RESTART_NEEDS_ROWS,
            "a restart with no rows has nothing to explain; it would return the start it was "
            "handed and claim a fit",
        )
    for row in materialised:
        if not isinstance(row, guard.Row):
            raise RestartRefusal(
                RESTART_ROWS_MUST_BE_REAL, f"a restart fits rows, got {type(row).__name__}"
            )
        if row.tag != guard.REAL:
            raise RestartRefusal(
                guard.REFUSE_INTERNAL_WITNESS,
                f"row {row.row_id!r} is tagged {row.tag}; the fallback re-fits unexplained REAL "
                f"rows, and an INTERNAL row is not one (Rule P)",
            )
    return materialised


def restart_fallback(fit_start, rows, *, seed_of=None, max_starts=MAX_STARTS, ledger=None,
                     fallback=True):
    """fitg.py:150-179 in this build's words: start 0, then the seeded starts if it left rows.

    `fit_start(start, seed)` runs one start and returns a `StartOutcome` (or raises; a start
    that cannot fit returns ``StartOutcome(..., refused="WHY")``, the way fitg.py returns a
    refusal string). The order of the source is kept:

      1. run start 0 (which makes no draw);
      2. if it left real rows unexplained, and `fallback`, run the seeded starts 1..max_starts
         (fitg.py:169-171);
      3. keep the start with the fewest unexplained rows, ties to the lower start
         (fitg.py:167);
      4. record every start in the ledger, with its seed, its start, its explained rows and
         whether it was kept.
    """
    materialised = _check_rows(rows)
    if not callable(fit_start):
        raise RestartRefusal(
            RESTART_NEEDS_A_START,
            f"the fallback needs one start to run, got {type(fit_start).__name__}; without a "
            f"route source there is nothing to try",
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
    best = None                      # (unexplained, start, outcome)
    index = 0
    while index < len(looped):
        start = looped[index]
        index += 1
        seed = 0 if start == 0 else seeds(start)     # fitg.py:109-162: start 0 is given no generator
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise RestartRefusal(RESTART_BAD_SEED, f"start {start} was given the seed {seed!r}")
        outcome = fit_start(start, seed)
        if not isinstance(outcome, StartOutcome):
            raise RestartRefusal(
                RESTART_BAD_START,
                f"start {start} returned {type(outcome).__name__}; a start returns a StartOutcome",
            )
        explained = 0 if outcome.refused else len(outcome.explained)
        record = StartRecord(
            start=start,
            seed=seed,
            rows_total=len(materialised),
            rows_explained=explained,
            kept=False,
            iterations=outcome.iterations,
            fixed_point=outcome.fixed_point,
            refused=outcome.refused,
            why=("FALLBACK_FIRED" if start > 0 else "CONSISTENCY_CHECKED_START"),
        )
        book.record(record)
        if not outcome.refused and (best is None or explained > best[0]):
            best = (explained, start, outcome)
        if fallback and start == 0 and not fired and (best is None or best[0] < len(materialised)):
            fired = True
            looped.extend(range(1, max_starts + 1))      # fitg.py:171 `ks += list(range(1, 9))`

    if best is None:
        return RestartResult(
            (),
            start_kept=0,
            ledger=book,
            rows_total=len(materialised),
            fallback_fired=fired,
        )
    explained, start_kept, outcome = best
    # Mark the kept start on the ledger line it already has. The ledger is append-only in
    # meaning: no line is removed, and exactly one line per call says it was kept.
    book._mark_kept(start_kept)
    return RestartResult(
        outcome.candidates,
        start_kept=start_kept,
        ledger=book,
        rows_total=len(materialised),
        fallback_fired=fired,
    )


# --------------------------------------------------------------------------- #
# The host this build supplies: routes over cell-binding, exact counts, seeded starts
# --------------------------------------------------------------------------- #
def routes_from_reading(reading):
    """The routes the Bias itself already holds: one per admitted fact that names its cells.

    Not a guess: a fact that does not name the cells it covers cannot be a route, because the
    only empirical question a restart asks is "which cells does this account explain".
    """
    routes = []
    if reading is None:
        return tuple(routes)
    for key in getattr(reading, "keys", ()):
        try:
            fact = reading.read(key)
        except GuardRefusal:                      # pragma: no cover - keys() came from the same reading
            continue
        if not isinstance(fact, dict):
            continue
        form = fact.get("canonical_form")
        cells = fact.get("cells")
        if isinstance(form, str) and form and cells:
            routes.append(Route(form, fact.get("target", ""), tuple(cells)))
    return tuple(routes)


def _cell_of(row):
    data = row.data if isinstance(row.data, dict) else {}
    cell = data.get("cell")
    return cell if isinstance(cell, str) and cell else "NO_CELL"


def _form_of(row):
    data = row.data if isinstance(row.data, dict) else {}
    form = data.get("canonical_form")
    return form if isinstance(form, str) and form else ""


def make_start(routes):
    """One start over these routes: fitg.py:118-147's loop, on exact counts instead of yields.

    fitg.py's loop, step for step:

      * **assign** every row to a route. A row that exactly one route can take is *certain* and
        is assigned without a draw (fitg.py:104-108 `certain_set`). Every other row is assigned
        by the start: start 0 takes the lowest route index and makes no draw; a seeded start
        draws among the routes that claim the row's cell (fitg.py:109-117).
      * **fit each route on its own rows** -- the route's witnessed form is the form most of its
        assigned rows carry, ties to the lowest form name. This is fitg.py:123-127's "refit each
        route on its rows" (`typed_wrm(S, mine)`), with counts standing in for yields.
      * **reassign** each row to the route that explains it best. A row is explained only when
        its form matches the route's witnessed form and that route's support is a clear winner
        (`CLEAR` = 21/20, fitg.py:51, 135-138); otherwise the row stays unexplained.
      * repeat to a fixed point, cap `MAX_ITER` = 20 (fitg.py:52, 120).

    The seed's only job is the first assignment, exactly as in fitg.py: it changes where the
    fitting starts and nothing else. The rows decide the rest.
    """
    materialised = tuple(routes)
    if not materialised:
        raise RestartRefusal(
            RESTART_NEEDS_A_START,
            "no route was named, so no start can fit anything; a restart needs at least one "
            "candidate account to start from",
        )
    for route in materialised:
        if not isinstance(route, Route):
            raise RestartRefusal(RESTART_BAD_ROUTE, f"routes are Routes, got {type(route).__name__}")

    def claims(index, row):
        return materialised[index].claims(_cell_of(row))

    def witnessed_and_support(rows, assign):
        """Each route's witnessed form on its own rows, and that form's support."""
        witnessed, support = {}, {}
        for index in range(len(materialised)):
            mine = [_form_of(row) for row, owner in zip(rows, assign)
                    if owner == index and _form_of(row)]
            if not mine:
                witnessed[index], support[index] = "", 0
                continue
            counts = {}
            for form in mine:
                counts[form] = counts.get(form, 0) + 1
            best_form = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
            witnessed[index], support[index] = best_form, counts[best_form]
        return witnessed, support

    def fit_start(start, seed):
        rows = tuple(fit_start.rows)              # named by the caller, never a global
        rng = random.Random(seed) if start > 0 else None      # fitg.py:109
        options = [[index for index in range(len(materialised)) if claims(index, row)]
                   for row in rows]
        assign = []
        for row, routes_that_fit in zip(rows, options):
            if len(routes_that_fit) == 1:
                assign.append(routes_that_fit[0])          # certain: one route can take it
            elif not routes_that_fit:
                assign.append(None)
            elif rng is not None:
                assign.append(routes_that_fit[rng.randrange(len(routes_that_fit))])
            else:
                assign.append(routes_that_fit[0])          # start 0: no draw, lowest index
        fixed, iterations = False, 0
        for iterations in range(1, MAX_ITER + 1):
            witnessed, support = witnessed_and_support(rows, assign)
            new = []
            for row, routes_that_fit in zip(rows, options):
                form = _form_of(row)
                eligible = [index for index in routes_that_fit if witnessed[index] == form and form]
                if not eligible:
                    new.append(None)
                    continue
                ranked = sorted(eligible, key=lambda index: (-support[index], index))
                winner = ranked[0]
                clear = all(support[winner] >= CLEAR * support[other] for other in ranked[1:])
                new.append(winner if clear else None)
            if new == list(assign):
                fixed = True
                break
            assign = new
        explained = tuple(
            row.row_id for row, owner in zip(rows, assign)
            if owner is not None and witnessed.get(owner, "") == _form_of(row) and _form_of(row)
        )
        chosen = []
        for owner in assign:
            if owner is None:
                continue
            if materialised[owner].proposal not in chosen:
                chosen.append(materialised[owner].proposal)
        return StartOutcome(
            start=start,
            seed=seed,
            explained=explained,
            candidates=tuple(chosen),
            iterations=iterations,
            fixed_point=fixed,
        )

    fit_start.rows = ()          # the caller names the rows; an empty fit explains nothing
    return fit_start


def restart_refit(routes, *, seed_of=None, max_starts=MAX_STARTS, ledger=None):
    """A `refit` callable for `faculties.pondering`: fit one group with the restart fallback.

    It has the same signature pondering already uses -- `refit(group, reading)` -- and it
    returns `(canonical_form, target)` pairs, which pondering puts in the buffer as `HELD`.
    The ledger it fills is the one the caller passed, so every seed and every start stays
    readable after the pass.
    """
    book = ledger if ledger is not None else RestartLedger()
    named = tuple(routes)

    def refit(group, reading=None):
        group = tuple(group)
        if not group:
            return ()
        available = named or routes_from_reading(reading)
        if not available:
            raise RestartRefusal(
                RESTART_NEEDS_A_START,
                "the group has no route to start from: no route was named and the Bias holds no "
                "fact that names the cells it covers",
            )
        start = make_start(available)
        start.rows = group
        result = restart_fallback(
            start,
            group,
            seed_of=seed_of,
            max_starts=max_starts,
            ledger=book,
        )
        return result.proposed_forms()

    refit.ledger = book
    return refit
