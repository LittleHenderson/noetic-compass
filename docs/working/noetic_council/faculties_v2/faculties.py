"""faculties.py -- the four faculties, each one writing candidates and nothing else.

WHAT THIS MODULE DOES
---------------------
FACULTIES.md section 2 names the faculties and gives each one operational definition. This
module implements the four the owning instruction names, with the signatures it gives:

  * ``wondering(bias, held, surface)``          -- FACULTIES.md 2.2
  * ``pondering(bias, held, unexplained, refit)``-- FACULTIES.md 2.3
  * ``imagination(bias, held, world_builder)``   -- FACULTIES.md 2.4
  * ``self_notice(inner_faculty)``               -- FACULTIES.md 2.5 (nested thought)

Everything each one produces goes into the held buffer as `HELD`. Each returns a
`FacultyReport` that has been through `guard.check_faculty_return`, so a report that carries a
Bias write or an admitted candidate is refused before the caller sees it.

Four rules hold across the whole module, and each is enforced somewhere a test can watch:

  1. **Nothing but `HELD` is written.** Faculties build `held.Proposal` objects and call
     `held.put`. `put` refuses any `claimed_state` other than `HELD`, and the report is
     refused by the guard if it carries an admitted candidate.
  2. **No faculty writes the Bias.** Each faculty takes a Bias and immediately narrows it to a
     `guard.BiasReading`, an object with no `write` method at all. The Bias itself refuses a
     writer named `FACULTY:<faculty>` (the copied Bias's one-writer rule), and
     `guard.believe` refuses a faculty coordinator by name.
  3. **No faculty sleeps inside another by accident.** `self_notice` runs an inner faculty and
     records one level receipt per level, re-reading the buffer at each level (`epsilon` after
     `eta`). A level whose read-back does not match what the faculty said it wrote invalidates
     every parent (`CHAIN_INVALIDATED`, RB2's G5).
  4. **Imagination labels a daydream and never calls it anything else.** The candidate goes in
     with `label=DAYDREAM` and the world id. Only `held.settle` on a real verdict changes that
     label, and only to `INSIGHT`.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT verify anything. No faculty calls `guard.verify`, and no faculty is given
    evidence to call it with. Verification is the drive loop's step 6 and `guard.verify`.
  * It does NOT decide which candidate is right, true or useful. A faculty's output is a list
    of proposals in the buffer with the faculty's name on them.
  * It does NOT write the recipe book. There is no writer and no book in this build; the book
    is the Bias in the design, and `guard.believe` is the only door to it.
  * It does NOT score a Noetic label. The `phi` field carries the design label from
    CAS_MAPPING.md section 4 as text, because that file's own builder check says the exact
    `Φ<...>` spelling must be compiled before any `Φ` word is written into a record. It is a
    label here, not a compiled word.
  * It does NOT draw randomly. There is no draw in any faculty in this build: wondering's
    order is the caller's order, pondering's grouping is a sort, imagination's worlds come
    from the builder the caller supplies. Where the design allows a seeded draw (imagination's
    K draws per tick), the seed is carried on the proposal when the caller supplies one.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM.
"""

from __future__ import annotations

import dataclasses

import guard
import restart
from guard import REFUSE_INTERNAL_WITNESS
from held import DAYDREAM, HELD, HeldRefusal, Proposal

__all__ = [
    "FACULTIES", "FACULTY_LABELS", "MAX_NESTING_DEPTH",
    "wondering", "pondering", "imagination", "self_notice",
    "Unexplained", "ImaginedWorld", "DaydreamStore", "FacultyReport", "LevelReceipt",
    "FacultiesRefusal",
]

#: The faculties the design names, in the design's order. Exactly four. "Contemplation" is
#: not here because FACULTIES.md never names it: the closest concepts are pondering (2.3) and
#: self-notice (2.5), and inventing a sixth faculty would invent a claim.
FACULTIES = ("wondering", "pondering", "imagination", "self_notice")

#: The design label each faculty carries (CAS_MAPPING.md section 4, and per-faculty cards in
#: FACULTIES.md section 2). A label for the design, never a score, never a compiled Phi word.
FACULTY_LABELS = {
    "wondering": "^8->^9",
    "pondering": "^6",
    "imagination": "^0",
    "self_notice": "(nesting operator; no Noetic label claimed)",
}

#: Chapter 27's depth cap. The drive loop is iterative (Phi_D) and does not spend it.
MAX_NESTING_DEPTH = 5

#: Refusal codes.
SURFACE_NOT_A_SURFACE = "SURFACE_NOT_A_SURFACE"
PONDERING_RUNS_ONLY_WHEN_IDLE = "PONDERING_RUNS_ONLY_WHEN_IDLE"
PONDERING_NEEDS_A_REFIT = "PONDERING_NEEDS_A_REFIT"
UNEXPLAINED_NEEDS_ROWS = "UNEXPLAINED_NEEDS_ROWS"
UNEXPLAINED_ROWS_MUST_BE_REAL = "UNEXPLAINED_ROWS_MUST_BE_REAL"
IMAGINATION_NEEDS_A_WORLD_BUILDER = "IMAGINATION_NEEDS_A_WORLD_BUILDER"
WORLD_NOT_AN_IMAGINED_WORLD = "WORLD_NOT_AN_IMAGINED_WORLD"
WORLD_HAS_NO_ROWS = "WORLD_HAS_NO_ROWS"
NESTING_DEPTH_CAP = "NESTING_DEPTH_CAP"
NESTING_NEEDS_A_FACULTY = "NESTING_NEEDS_A_FACULTY"
NESTING_DEPTH_NOT_RECORDED = "NESTING_DEPTH_NOT_RECORDED"
NESTED_RUN_RETURNED_NO_REPORT = "NESTED_RUN_RETURNED_NO_REPORT"
CHAIN_INVALIDATED = "CHAIN_INVALIDATED"

# UNDECIDED IN DESIGN: whether the faculty checks "idle" itself or the drive loop guarantees it -- FACULTIES.md section 2.3 says the pass "runs only when no new input is queued" and does not say who decides that, so this build requires the Unexplained record to say it is idle and refuses PONDERING_RUNS_ONLY_WHEN_IDLE when it says otherwise, while the drive loop separately never calls pondering on a tick with queued input.
# UNDECIDED IN DESIGN: how the residual rows are ordered within and between binding cells -- FACULTIES.md section 2.3 says pondering "decomposes the residual rows by which cell binds them" and gives no tie order, so this build sorts groups by cell name and rows by row id, which makes the pass byte-reproducible.
# UNDECIDED IN DESIGN: how many grammar draws imagination takes per F5 tick -- FACULTIES.md section 2.4 gives "K seeded grammar draws per F5 tick (K PROPOSED 8, as LSR-T7/RB-C4)", a PROPOSED number the owner has not accepted, so this build draws nothing itself and takes whatever worlds the caller's builder returns, recording K as given.
# UNDECIDED IN DESIGN: whether an imagined world may be built out of rows another imagined world produced -- FACULTIES.md section 2.4 says a world is built from the book and does not say whether a daydream may be a premise, so this build refuses a world whose rows are not tagged INTERNAL and does not look at where INTERNAL rows came from, which leaves the question open rather than answering it.
# UNDECIDED IN DESIGN: what a per-level receipt must contain -- Chapter 27's Theorem 27.3 states that epsilon(n) after eta(n) equals the identity at every depth independently and FACULTIES.md section 2.5 says "every level carries its own receipt" without saying what it records, so this build records the faculty, the candidates it wrote, the forms it said it wrote, and the re-read result of an actual read-back of the buffer.
# UNDECIDED IN DESIGN: what a failed inner level does to the candidates it already wrote -- FACULTIES.md section 2.5 says "a failed receipt at level n invalidates every parent" and does not say whether the already-written candidates are withdrawn, marked or left, so this build leaves them in the buffer (nothing here deletes a candidate) and refuses to record any parent level.
# UNDECIDED IN DESIGN: whether the exact Phi word may be written into a record -- CAS_MAPPING.md section 4 lists "the exact Phi<...> spelling must be compiled in the site compiler (464fd4ad) before any Phi word is written into a record" as an open builder check, so this build records each faculty's design label (for example ^8->^9) and never a compiled Phi word.


class FacultiesRefusal(Exception):
    """A refusal with a stable code. Nothing here is ever a guess."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- #
# The record every faculty returns
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class LevelReceipt:
    """One level's receipt: which faculty ran, what it wrote, and whether the read-back held.

    `epsilon_of_eta` is the level's own check: after the faculty wrote its candidates (`eta`),
    the buffer was read back (`epsilon`) and the forms that came back must be exactly the
    forms the faculty said it wrote. That is Theorem 27.3's `epsilon(n) after eta(n) = id(n)`
    read at the size of one level.
    """

    level: int
    faculty: str
    wrote: tuple = ()
    forms_written: tuple = ()
    forms_read_back: tuple = ()
    epsilon_of_eta: bool = False
    phi: str = ""
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "level": self.level,
            "faculty": self.faculty,
            "wrote": list(self.wrote),
            "forms_written": list(self.forms_written),
            "forms_read_back": list(self.forms_read_back),
            "epsilon_of_eta": self.epsilon_of_eta,
            "phi": self.phi,
            "detail": self.detail,
        }


@dataclasses.dataclass(frozen=True)
class FacultyReport:
    """What a faculty hands back. Candidates live in the buffer; this is the accounting.

    `reason` is filled when the faculty wrote nothing (no candidates to surface, nothing
    unexplained, no world built) so that "nothing happened" is always a recorded word and
    never a silence.
    """

    faculty: str
    tick: int
    wrote: tuple = ()
    proposals: tuple = ()
    levels: tuple = ()
    reason: str = ""
    k: object = None

    @property
    def wrote_nothing(self) -> bool:
        return not self.wrote

    def as_dict(self) -> dict:
        return {
            "faculty": self.faculty,
            "tick": self.tick,
            "wrote": list(self.wrote),
            "proposals": [
                {
                    "canonical_form": p.canonical_form,
                    "target": p.target,
                    "world": p.world,
                    "label": p.label,
                    "seed": p.seed,
                }
                for p in self.proposals
            ],
            "levels": [level.as_dict() for level in self.levels],
            "reason": self.reason,
            "k": self.k,
        }


def _reading(bias) -> guard.BiasReading:
    """Narrow whatever Bias a caller passes to the read-only view a faculty is allowed."""
    return guard.bias_reading(bias)


def _write(held, faculty, forms, *, label=None, world=None, seed=None, phi="", tick=None):
    """Put each `(canonical_form, target)` pair in the buffer as HELD. Returns (entries, proposals)."""
    entries = []
    proposals = []
    for item in forms:
        if isinstance(item, str):
            form, target = item, ""
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            form, target = item
        else:
            raise FacultiesRefusal(
                SURFACE_NOT_A_SURFACE,
                f"{faculty} was handed {item!r}; a candidate is a canonical form, or a "
                f"(form, target) pair",
            )
        proposal = Proposal(
            canonical_form=form,
            faculty=faculty,
            target=target if isinstance(target, str) else "",
            phi=phi or FACULTY_LABELS[faculty],
            seed=seed,
            world=world,
            label=label,
            claimed_state=HELD,
        )
        entries.append(held.put(proposal, tick=tick))
        proposals.append(proposal)
    return tuple(entries), tuple(proposals)


# --------------------------------------------------------------------------- #
# 2.2 Wondering
# --------------------------------------------------------------------------- #
def wondering(bias, held, surface, *, tick=None):
    """Surface related candidates into the held buffer as `HELD`.

    `surface` is either a callable that takes the `BiasReading` and returns candidates, or an
    iterable of candidates. A candidate is a canonical form, or a `(canonical_form, target)`
    pair. The order is the caller's order, unchanged: FACULTIES.md section 2.2 fixes the
    retrieval order as "layout distance, then canonical form", and that order belongs to the
    retriever the caller supplies, not to this function.

    What it must not do, and does not: admit anything, refuse anything, call the verifier, or
    touch the Bias. The Candidates land `HELD` and stay `HELD` until a real verdict moves them.
    """
    reading = _reading(bias)
    if callable(surface):
        candidates = surface(reading)
    elif isinstance(surface, (tuple, list)):
        candidates = surface
    else:
        raise FacultiesRefusal(
            SURFACE_NOT_A_SURFACE,
            f"wondering needs a surface to retrieve from (a callable or an iterable), got "
            f"{type(surface).__name__}",
        )
    candidates = tuple(candidates)
    if not candidates:
        return guard.check_faculty_return(
            "wondering",
            FacultyReport(
                faculty="wondering",
                tick=held.tick,
                reason="SURFACED_NOTHING",
            ),
        )
    entries, proposals = _write(held, "wondering", candidates, tick=tick)
    report = FacultyReport(
        faculty="wondering",
        tick=held.tick,
        wrote=tuple(entry.candidate_id for entry in entries),
        proposals=proposals,
        reason="SURFACED",
    )
    return guard.check_faculty_return("wondering", report)


# --------------------------------------------------------------------------- #
# 2.3 Pondering
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class Unexplained:
    """The stored residual, and whether the tick is idle.

    FACULTIES.md section 2.3: pondering "takes the **stored residual** (rows the current book
    does not explain, kept from earlier ticks)". Those rows are real rows; an `INTERNAL` row
    is refused here with the design's own code, because an imagined row is not unexplained
    real data.
    """

    rows: tuple = ()
    idle: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.idle, bool):
            raise FacultiesRefusal(
                PONDERING_RUNS_ONLY_WHEN_IDLE,
                f"idle is a yes or no, got {self.idle!r}; the pass runs only when no new "
                f"input is queued",
            )
        for row in self.rows:
            if not isinstance(row, guard.Row):
                raise FacultiesRefusal(
                    UNEXPLAINED_ROWS_MUST_BE_REAL,
                    f"the stored residual holds rows, got {type(row).__name__}",
                )
            if row.tag == guard.INTERNAL:
                raise FacultiesRefusal(
                    REFUSE_INTERNAL_WITNESS,
                    f"row {row.row_id!r} is tagged INTERNAL; the residual is unexplained REAL "
                    f"data, and pondering breaks down real data, not imagined data",
                )


def _cell_of(row) -> str:
    if isinstance(row.data, dict):
        cell = row.data.get("cell")
        if isinstance(cell, str) and cell:
            return cell
    return "NO_CELL"


def pondering(bias, held, unexplained, refit=None, *, tick=None, routes=None,
              restart_ledger=None):
    """Break the stored residual down by binding cell and try fitting it again.

    `unexplained` is an `Unexplained` record. The pass refuses unless it says the tick is
    idle: FACULTIES.md section 2.3 and DRIVE_LOOP.md section 2 both say pondering is the
    idle-time action.

    `refit` is the caller's fallback. FACULTIES.md section 2.3 is explicit that the restart
    fallback is `refit`'s job ("(b) re-fits with the RB-C4 restart fallback on each group"), so
    when `refit` is None this build runs `restart.restart_refit`: RB-C4's fallback, copied in
    from `rb_c4/fitg.py`, over the routes the caller names (or the routes the Bias's own facts
    name). Every seed and every start it tries is recorded in `restart_ledger` when one is
    passed, and in a fresh ledger either way.

    Every refit lands `HELD`. Nothing here admits one: "Results go to the buffer as `HELD`,
    never straight into the book; F6 later verifies them on real rows" (FACULTIES.md 2.3).
    """
    reading = _reading(bias)
    if not isinstance(unexplained, Unexplained):
        raise FacultiesRefusal(
            UNEXPLAINED_ROWS_MUST_BE_REAL,
            f"pondering takes an Unexplained record, got {type(unexplained).__name__}",
        )
    if not unexplained.idle:
        raise FacultiesRefusal(
            PONDERING_RUNS_ONLY_WHEN_IDLE,
            "this tick has new input queued, so the idle pass does not run; pondering is the "
            "idle-time action (FACULTIES.md 2.3, DRIVE_LOOP.md 2)",
        )
    if not unexplained.rows:
        return guard.check_faculty_return(
            "pondering",
            FacultyReport(faculty="pondering", tick=held.tick, reason="NOTHING_UNEXPLAINED"),
        )
    used_restart = refit is None
    if used_restart:
        refit = restart.restart_refit(routes or (), ledger=restart_ledger)
    elif not callable(refit):
        raise FacultiesRefusal(
            PONDERING_NEEDS_A_REFIT,
            f"pondering needs a refit callable, got {type(refit).__name__}",
        )

    groups: dict = {}
    for row in unexplained.rows:
        groups.setdefault(_cell_of(row), []).append(row)
    entries = []
    proposals = []
    for cell in sorted(groups):
        group = tuple(sorted(groups[cell], key=lambda row: row.row_id))
        produced = tuple(refit(group, reading) or ())
        written, written_proposals = _write(held, "pondering", produced, tick=tick)
        entries.extend(written)
        proposals.extend(written_proposals)
    if used_restart:
        reason = "REFIT_RESTART_FALLBACK" if entries else "REFIT_RESTART_FALLBACK_PRODUCED_NOTHING"
    else:
        reason = "REFIT" if entries else "REFIT_PRODUCED_NOTHING"
    report = FacultyReport(
        faculty="pondering",
        tick=held.tick,
        wrote=tuple(entry.candidate_id for entry in entries),
        proposals=tuple(proposals),
        reason=reason,
    )
    return guard.check_faculty_return("pondering", report)


# --------------------------------------------------------------------------- #
# 2.4 Imagination (an internal SDG)
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class ImaginedWorld:
    """One imagined world: a recipe, the rows it simulates, and its name.

    The rows an imagined world simulates are `INTERNAL` (Rule P). `guard.ImaginedEvidence`
    checks that when the world is built, so a world that tried to carry a `REAL` row would be
    refused at construction.
    """

    world_id: str
    recipe: str
    rows: tuple = ()
    target: str = ""
    seed: object = None

    def __post_init__(self) -> None:
        if not isinstance(self.world_id, str) or not self.world_id.strip():
            raise FacultiesRefusal(
                WORLD_NOT_AN_IMAGINED_WORLD, f"an imagined world needs a name, got {self.world_id!r}"
            )
        if not isinstance(self.recipe, str) or not self.recipe.strip():
            raise FacultiesRefusal(
                WORLD_NOT_AN_IMAGINED_WORLD, f"world {self.world_id!r} names no recipe"
            )
        if not self.rows:
            raise FacultiesRefusal(
                WORLD_HAS_NO_ROWS,
                f"world {self.world_id!r} simulates no rows, so there is nothing it could "
                f"ever be matched against",
            )
        # Builds the imagined evidence here so a world is well-formed the moment it exists.
        # The object is not kept: it exists to be refused, never to verify anything.
        guard.ImaginedEvidence(self.world_id, self.rows)

    def evidence(self) -> guard.ImaginedEvidence:
        """The imagined world's rows, as the type that can never be verified with."""
        return guard.ImaginedEvidence(self.world_id, self.rows)

    def daydreamed_forms(self) -> tuple:
        out = []
        for row in self.rows:
            if isinstance(row.data, dict):
                form = row.data.get("canonical_form")
                if isinstance(form, str) and form:
                    out.append(form)
        return tuple(out)


class DaydreamStore:
    """The imagined-world store: worlds, and whether a real world ever matched one.

    ARCHITECTURE.md section 3 gives it "imagined worlds (recipe set + INTERNAL rows + matched
    flag)" with "the matched-world count" as its reading. This is that store, and nothing
    else: it holds what the builder produced and a flag.
    """

    def __init__(self) -> None:
        self._worlds: dict = {}
        self._order: list = []
        self._matched: dict = {}

    def remember(self, world) -> str:
        if not isinstance(world, ImaginedWorld):
            raise FacultiesRefusal(
                WORLD_NOT_AN_IMAGINED_WORLD, f"the store holds ImaginedWorlds, got {type(world).__name__}"
            )
        if world.world_id not in self._worlds:
            self._order.append(world.world_id)
        self._worlds[world.world_id] = world
        return world.world_id

    def worlds(self) -> tuple:
        return tuple(self._worlds[wid] for wid in self._order)

    def get(self, world_id):
        return self._worlds.get(world_id)

    def note_admission(self, world_id, candidate_id, tick) -> bool:
        """Mark a world matched by a real admission. Returns True when it is now matched."""
        if world_id is None:
            return False
        if world_id not in self._worlds:
            raise FacultiesRefusal(
                WORLD_NOT_AN_IMAGINED_WORLD,
                f"no imagined world named {world_id!r} is in this store",
            )
        if world_id in self._matched:
            return True
        self._matched[world_id] = {"candidate_id": candidate_id, "tick": tick}
        return True

    def is_matched(self, world_id) -> bool:
        return world_id in self._matched

    def matched_count(self) -> int:
        return len(self._matched)

    def daydream_count(self) -> int:
        """Worlds that no real admission ever matched. A daydream, by FACULTIES.md 2.4."""
        return len(self._order) - len(self._matched)


def imagination(bias, held, world_builder, *, store=None, tick=None, k=None):
    """Build hypothetical worlds and put their recipes in the buffer as DAYDREAM.

    `world_builder` is a callable that takes the `BiasReading` and returns `ImaginedWorld`
    objects. Each world's recipe enters the buffer as `HELD` with `label=DAYDREAM` and the
    world's name on it. FACULTIES.md section 2.4: "a **daydream** = an imagined world or
    recipe never confirmed by real rows. It stays in the imagined-world store." Nothing here
    promotes it: only `held.settle` on a real verdict turns the label into `INSIGHT`.

    A world that carries a `REAL` row cannot even be built (its own constructor checks), so
    imagination cannot manufacture real data by accident.
    """
    reading = _reading(bias)
    if not callable(world_builder):
        raise FacultiesRefusal(
            IMAGINATION_NEEDS_A_WORLD_BUILDER,
            f"imagination needs a world builder, got {type(world_builder).__name__}; the "
            f"grammar and the shape algebra are not in this build",
        )
    worlds = tuple(world_builder(reading, k) if k is not None else world_builder(reading))
    for world in worlds:
        if not isinstance(world, ImaginedWorld):
            raise FacultiesRefusal(
                WORLD_NOT_AN_IMAGINED_WORLD,
                f"the world builder returned {type(world).__name__}; a world is an ImaginedWorld",
            )
        if store is not None:
            store.remember(world)
    if not worlds:
        return guard.check_faculty_return(
            "imagination",
            FacultyReport(faculty="imagination", tick=held.tick, reason="BUILT_NO_WORLD", k=k),
        )
    entries = []
    proposals = []
    for world in worlds:
        written, written_proposals = _write(
            held,
            "imagination",
            ((world.recipe, world.target),),
            label=DAYDREAM,
            world=world.world_id,
            seed=world.seed,
            tick=tick,
        )
        entries.extend(written)
        proposals.extend(written_proposals)
    report = FacultyReport(
        faculty="imagination",
        tick=held.tick,
        wrote=tuple(entry.candidate_id for entry in entries),
        proposals=tuple(proposals),
        reason="BUILT_WORLDS",
        k=k,
    )
    return guard.check_faculty_return("imagination", report)


# --------------------------------------------------------------------------- #
# 2.5 Self-notice / nested thought
# --------------------------------------------------------------------------- #
def _level_receipt(level, report, held, faculty_name="self_notice") -> LevelReceipt:
    """Re-read the buffer after the faculty's write, and compare. This is epsilon after eta."""
    forms_read = []
    detail = ""
    ok = True
    for candidate_id in report.wrote:
        try:
            entry = held.get(candidate_id)
        except HeldRefusal as exc:
            ok = False
            detail = f"read-back failed: {exc.code}"
            break
        forms_read.append(entry.canonical_form)
    forms_written = tuple(proposal.canonical_form for proposal in report.proposals)
    if ok and tuple(forms_read) != forms_written:
        ok = False
        detail = (
            f"the faculty wrote {list(forms_written)} and the buffer read back "
            f"{forms_read}, so the level's receipt does not hold"
        )
    if ok and not detail:
        detail = f"read back {len(forms_read)} candidate(s) exactly as written"
    return LevelReceipt(
        level=level,
        faculty=faculty_name,
        wrote=tuple(report.wrote),
        forms_written=forms_written,
        forms_read_back=tuple(forms_read),
        epsilon_of_eta=ok,
        phi=FACULTY_LABELS.get(faculty_name, ""),
        detail=detail,
    )


def self_notice(inner_faculty, *, depth=1, held=None, as_faculty="self_notice"):
    """Run one faculty inside this one and record a receipt at each level.

    `inner_faculty` is a zero-argument callable that runs a faculty and returns its
    `FacultyReport` (or the report of a `self_notice` already wrapped around one). `as_faculty`
    names the faculty that runs at *this* level, because the design's nesting words name a
    faculty per level (`Φ<^8->^9, ^6, ^0>`: wondering, then pondering, then imagination). It
    defaults to `self_notice` itself.

    Nesting is done by wrapping, innermost first:

        def running_wondering():  return wondering(bias, held, surface)
        def wondering_level():    return self_notice(running_wondering, depth=1,
                                                     held=held, as_faculty="wondering")
        report = self_notice(wondering_level, depth=2, held=held, as_faculty="imagination")

    That gives two receipts, levels 1 to 2, naming wondering and then imagination -- one per
    level, exactly as FACULTIES.md section 2.5 and Chapter 27's Theorem 27.3 require, and the
    two labels spell the design's own example word `^8->^9 . ^0` (CAS_MAPPING.md section 4).
    `depth` is checked against the cap *before* the inner faculty runs, and the recorded level
    count must agree with it; `held` is the buffer the read-back reads.

    A level whose receipt fails invalidates every parent: `CHAIN_INVALIDATED`, and no parent
    receipt is recorded.
    """
    if isinstance(depth, bool) or not isinstance(depth, int) or depth < 1:
        raise FacultiesRefusal(
            NESTING_DEPTH_NOT_RECORDED, f"a nesting depth is a positive integer, got {depth!r}"
        )
    if depth > MAX_NESTING_DEPTH:
        raise FacultiesRefusal(
            NESTING_DEPTH_CAP,
            f"depth {depth} is past the design's cap of {MAX_NESTING_DEPTH} (Chapter 27); the "
            f"inner faculty was not run, and nothing was written",
        )
    if as_faculty not in FACULTIES:
        raise FacultiesRefusal(
            NESTING_NEEDS_A_FACULTY,
            f"as_faculty must name one of the design's faculties {list(FACULTIES)}, got "
            f"{as_faculty!r}; this build invents no faculty",
        )
    if not callable(inner_faculty):
        raise FacultiesRefusal(
            NESTING_NEEDS_A_FACULTY,
            f"self_notice runs a faculty and was given {type(inner_faculty).__name__}",
        )
    inner = inner_faculty()
    if not isinstance(inner, FacultyReport):
        raise FacultiesRefusal(
            NESTED_RUN_RETURNED_NO_REPORT,
            f"the inner faculty returned {type(inner).__name__}; self_notice reads a "
            f"FacultyReport, so a level with no report cannot be receipted",
        )
    if held is None:
        raise FacultiesRefusal(
            NESTING_NEEDS_A_FACULTY,
            "self_notice needs the buffer to read back (pass held=...); a receipt that is not "
            "checked against a store is decoration",
        )
    receipt = _level_receipt(depth, inner, held, as_faculty)
    levels = tuple(inner.levels) + (receipt,)
    if not receipt.epsilon_of_eta:
        raise FacultiesRefusal(
            CHAIN_INVALIDATED,
            f"level {depth} ({as_faculty}, running {inner.faculty}) did not hold: "
            f"{receipt.detail}. A failed level invalidates every parent, so no parent receipt "
            f"is recorded",
        )
    if len(levels) != depth:
        raise FacultiesRefusal(
            NESTING_DEPTH_NOT_RECORDED,
            f"this call reports depth {depth} but the run recorded {len(levels)} level(s); the "
            f"reported depth must be the number of receipts",
        )
    report = FacultyReport(
        faculty="self_notice",
        tick=held.tick,
        wrote=inner.wrote,
        proposals=inner.proposals,
        levels=levels,
        reason=f"NESTED:{as_faculty}",
        k=inner.k,
    )
    return guard.check_faculty_return("self_notice", report)
