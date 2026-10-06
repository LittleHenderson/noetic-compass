"""The CAS Reasoning Runtime — the part that was missing.

The component library already had organs: CJTs, a memory board, a differential
comparator, an RPM planner, a power model. What it did not have was a central
control unit that repeatedly schedules those organs until a reasoning task is
finished. Without one, CAS is a parts bin whose pieces never wake each other.

This module is that control unit. It supplies the seven mechanisms a native
reasoner needs and a board diagram does not provide:

    1. global workspace     `workspace.Workspace`
    2. scheduler            `ReasoningProcessor._cycle`, the ten phases
    3. branching and search  candidate list from ^8, tried in order
    4. binding/substitution `workspace.Pattern`
    5. backtracking         `Episode.backtracks`, on an incomplete ^6
    6. truth maintenance    `workspace.Status`, contradiction detection
    7. halting controller   `Terminal`, plus a hard tick bound

No language model is called from this file, and none can be: there is no
transport, no client, and no text in the reasoning path. The processor is
handed CAS-encoded premises and produces a CAS-encoded conclusion with a
complete derivation trace.

The instruction cycle
---------------------
    FETCH -> PRIME -> ASSOCIATE -> DECOMPOSE -> INFER -> COMPARE
          -> CHECK_PREREQUISITES -> COMMIT -> ACT -> LEARN

which is, in CAS terms: CMB recall; A-root and the Foundation engines; `^8`
candidate triggering; `^6` decomposition; `^9` conclusion; CDAB comparison;
RPM D->W->P; Schmitt commit; P->C->E->O descent; filtered low-gain feedback.

Two constitutional rules are enforced structurally, not by convention
---------------------------------------------------------------------
**The bias firewall.** Ambition may choose the question; it must not choose the
answer. `DecompositionBank.decompose` and `InferenceBank.land` have no
parameter through which a `FoundationProfile` could reach them. That is a
property of their signatures, checked by
`test_the_evaluation_banks_cannot_be_handed_the_ambition`, not a promise in a
docstring. The Foundation profile is consulted at PRIME (which question) and at
COMPARE (which candidate serves the stated ambitions) and nowhere in between.

**Domain descent.** P -> C -> E -> O. ACT will not run before the principled,
cognitive and evaluative phases have reported, and a stage whose bias sits
lower in precedence than its target is refused by `CjtSpec` itself.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ccb_r1"))

from cdab import Candidate as CdabCandidate, tournament  # noqa: E402
from cmb import CognitiveMemoryBoard, Tier  # noqa: E402
from rpm import (  # noqa: E402
    DEFAULT_SUFFICIENCY,
    Goal,
    Prereq,
    PrereqState,
    RpmPlanner,
    Terminal,
)

from banks import (  # noqa: E402
    BankError,
    BankTrace,
    Candidate,
    Decomposition,
    DecompositionBank,
    HypothesisBank,
    Inference,
    InferenceBank,
)
from foundations import (  # noqa: E402
    LAW_2,
    REASONING_RECIPES,
    Drive,
    FoundationProfile,
    Recipe,
    parse_subfoundation,
    reasoning_profile,
)
from workspace import ASSERTIVE, Proposition, Status, Workspace  # noqa: E402


class Phase(str, Enum):
    FETCH = "FETCH"
    PRIME = "PRIME"
    ASSOCIATE = "ASSOCIATE"
    DECOMPOSE = "DECOMPOSE"
    INFER = "INFER"
    COMPARE = "COMPARE"
    CHECK_PREREQUISITES = "CHECK_PREREQUISITES"
    COMMIT = "COMMIT"
    ACT = "ACT"
    LEARN = "LEARN"


#: ^5 Female in the Cognitive domain: the accumulated-experience cell the
#: processor reads at FETCH and writes back at LEARN.
EXPERIENCE_CELL = "C5"

#: The descent order ACT is gated on. O may not run before P, C and E.
DOMAIN_ORDER = ("P", "C", "E", "O")

PHASE_DOMAIN: dict[Phase, str] = {
    Phase.FETCH: "C",
    Phase.PRIME: "P",
    Phase.ASSOCIATE: "C",
    Phase.DECOMPOSE: "E",
    Phase.INFER: "C",
    Phase.COMPARE: "E",
    Phase.CHECK_PREREQUISITES: "E",
    Phase.COMMIT: "E",
    Phase.ACT: "O",
    Phase.LEARN: "P",
}


class RuntimeError_(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class Problem:
    """A reasoning task, already in CAS form.

    `premises` are triples. `query` is the claim to settle. `closed_world`
    decides whether an unclosable chain is a NO or an admission of ignorance;
    it is the single most consequential flag in the whole processor.
    """

    name: str
    relation: str
    premises: tuple[tuple[str, str, str], ...]
    query: tuple[str, str]
    target_channel: str = "F2|A"
    closed_world: bool = False
    negated_premises: tuple[tuple[str, str, str], ...] = ()

    @property
    def source(self) -> str:
        return self.query[0]

    @property
    def target(self) -> str:
        return self.query[1]


@dataclass
class Step:
    """One scheduled phase and what it did. The audit trail is the product."""

    tick: int
    phase: Phase
    domain: str
    note: str
    data: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.tick:02d}] {self.phase.value:<20} ^{self.domain}  {self.note}"


@dataclass
class Episode:
    """Everything one reasoning run produced."""

    problem: Problem
    terminal: Terminal
    answer: str
    trace: list[Step]
    workspace: Workspace
    candidates: list[Candidate]
    decompositions: list[Decomposition]
    backtracks: list[str]
    profile: FoundationProfile
    drive_totals: dict[Drive, float]
    conclusion: Proposition | None = None
    confidence: float = 0.0
    rpm_trace: list = field(default_factory=list)
    justification: dict | None = None
    note: str = ""

    @property
    def concluded(self) -> bool:
        return self.terminal is Terminal.CONCLUDED

    def report(self) -> str:
        lines = [
            f"problem   {self.problem.name}",
            f"query     {self.problem.source} -[{self.problem.relation}]-> {self.problem.target}",
            f"world     {'closed' if self.problem.closed_world else 'open'}",
            f"terminal  {self.terminal.value}",
            f"answer    {self.answer}   confidence {self.confidence:.2f}",
            "",
            "trace:",
        ]
        lines += [f"  {s}" for s in self.trace]
        if self.backtracks:
            lines += ["", "backtracked from:"] + [f"  {b}" for b in self.backtracks]
        if self.conclusion is not None:
            lines += ["", f"conclusion  {self.conclusion}", f"rests on    {', '.join(self.conclusion.support)}"]
        if self.note:
            lines += ["", f"note      {self.note}"]
        return "\n".join(lines)


@dataclass(frozen=True)
class CommitGate:
    """A Schmitt trigger. Two thresholds so ambiguity cannot make it chatter.

    A single threshold at 0.5 flips on every jitter around the boundary. The
    gap between `high` and `low` is the hysteresis band: once committed, the
    processor stays committed until confidence falls all the way to `low`.
    """

    high: float = 0.65
    low: float = 0.35

    def __post_init__(self) -> None:
        if not (0.0 <= self.low < self.high <= 1.0):
            raise RuntimeError_(
                "E-RT-001", f"need 0 <= low({self.low}) < high({self.high}) <= 1"
            )

    def decide(self, confidence: float, *, committed: bool = False) -> bool:
        if committed:
            return confidence > self.low
        return confidence >= self.high


class ReasoningProcessor:
    """CCB-R1: the board that reasons.

    Construct it with a Foundation profile (its ambitions) and optionally a
    memory board carrying prior experience. Call `run` with a `Problem`.
    """

    def __init__(
        self,
        profile: FoundationProfile | None = None,
        memory: CognitiveMemoryBoard | None = None,
        *,
        max_ticks: int = 64,
        gate: CommitGate | None = None,
        learn_beta: float = 0.05,
    ) -> None:
        if max_ticks < len(Phase):
            raise RuntimeError_(
                "E-RT-002", f"max_ticks={max_ticks} cannot complete one full cycle"
            )
        if not (0.0 < learn_beta <= 0.2):
            # "feedback ... normally feeding outcomes back into bias at low gain"
            raise RuntimeError_(
                "E-RT-003",
                f"learn_beta={learn_beta} is not low gain; one outcome must not "
                "rewrite the machine's principles",
            )
        self.profile = profile or reasoning_profile()
        self.memory = memory or CognitiveMemoryBoard()
        self.max_ticks = max_ticks
        self.gate = gate or CommitGate()
        self.learn_beta = learn_beta

        self.hypothesis = HypothesisBank()
        self.decomposition = DecompositionBank()
        self.inference = InferenceBank()

    # ---- the cycle -------------------------------------------------------

    def run(self, problem: Problem) -> Episode:
        """One problem, one fresh workspace. The original entry point.

        Loads the problem's premises into a new `Workspace` and reasons over
        it. For a workspace that outlives the episode -- an organism's -- use
        `run_in`, which this is a thin shell around.
        """
        ws = Workspace(closed_world=problem.closed_world)
        for subject, relation, obj in problem.premises:
            ws.fact(subject, relation, obj)
        for subject, relation, obj in problem.negated_premises:
            ws.fact(subject, relation, obj, negated=True)
        return self.run_in(ws, problem)

    def run_in(
        self,
        ws: Workspace,
        problem: Problem,
        *,
        profile: FoundationProfile | None = None,
    ) -> Episode:
        """The ten phases against a workspace the caller already holds.

        This is what makes an organism possible: the workspace persists across
        episodes, so conclusions landed earlier are *held*, retractions since
        then have already cascaded, and this episode reports only the gaps it
        itself hit (`ws.lacunae(since=mark)`).

        `profile` lets a caller supply this episode's ambition. It reaches
        PRIME, COMPARE and the RPM Desire gate -- and nothing else. The
        evaluation banks cannot take it; see the bias-firewall tests.

        Every exit sweeps the route hypotheses `^8` recorded this episode
        (`ws.sweep("^8")`), so the bank never re-triggers on its own output.
        """
        prof = profile or self.profile
        trace: list[Step] = []
        bank_trace = BankTrace()
        backtracks: list[str] = []
        decompositions: list[Decomposition] = []
        tick = 0
        loaded = len(problem.premises) + len(problem.negated_premises)

        def log(phase: Phase, note: str, **data) -> None:
            nonlocal tick
            tick += 1
            trace.append(Step(tick, phase, PHASE_DOMAIN[phase], note, data))

        def finish(terminal: Terminal, answer: str, note: str = "", **kw) -> Episode:
            ws.sweep("^8")
            return Episode(
                problem=problem,
                terminal=terminal,
                answer=answer,
                trace=trace,
                workspace=ws,
                candidates=kw.pop("candidates", []),
                decompositions=decompositions,
                backtracks=backtracks,
                profile=prof,
                drive_totals=prof.drive_totals(),
                note=note,
                **kw,
            )

        # 1 FETCH -- the workspace is what it is; experience comes out of memory.
        # `C5` is ^5 Female in the Cognitive domain -- accumulated experience,
        # "the Ideas a Mind is composed of". That is the cell a reasoner consults
        # when asking what it already brings to a problem of this kind.
        mark = ws.mark()
        held = len(ws.assertive())
        recalled = self.memory.recall(EXPERIENCE_CELL, decay=False)
        log(
            Phase.FETCH,
            f"{loaded} premise(s) loaded, {held} proposition(s) held; "
            f"CMB {'lacuna' if recalled.is_lacuna else f'charge {recalled.charge:.2f}'}",
            premises=loaded,
            held=held,
            lacuna=recalled.is_lacuna,
            mark=mark,
        )

        # 2 PRIME -- the Foundation engines set the target, and the recipe for
        # the outcome says what that target actually costs. The limiting
        # reagent is the bank's one real job: which prerequisite is thin
        # relative to the proportion the outcome needs.
        recipe = REASONING_RECIPES[
            "deduction" if not problem.closed_world else "deduction"
        ]
        yield_t = recipe.theoretical_yield(prof)
        limiting = recipe.limiting_reagent(prof)
        log(
            Phase.PRIME,
            f"target {problem.target_channel}; {recipe}; Y_T={yield_t:.3f}, "
            f"limiting reagent {limiting}; dominant {prof.dominant()}",
            target=problem.target_channel,
            theoretical_yield=yield_t,
            limiting_reagent=limiting,
            law=LAW_2,
        )

        # 3 ASSOCIATE -- ^8 surfaces candidates. It cannot conclude.
        bank_trace.fire("^8")
        candidates, r8 = self.hypothesis.surface(
            ws, problem.source, problem.target, problem.relation
        )
        log(
            Phase.ASSOCIATE,
            f"^8 {r8.region.value}: {len(candidates)} candidate route(s) surfaced",
            region=r8.region.value,
            candidates=[str(c) for c in candidates],
        )

        if not candidates:
            # Nothing to take apart. Ask the question directly anyway: an
            # unanswered `ask` is what records the lacuna, and without one the
            # processor would report "I need information" while being unable to
            # say which. Naming the frontier turns the abstention into a
            # request a caller can actually act on.
            direct = ws.ask(problem.source, problem.relation, problem.target)
            denial = ws.props.get(f"~{problem.source}|{problem.relation}|{problem.target}")
            if direct == "NO" and denial is not None and denial.status in ASSERTIVE:
                # The claim is held false, as given. That is an answer under
                # either world assumption, not an admission of ignorance.
                log(Phase.DECOMPOSE, "^6: the claim is explicitly denied in the premises")
                log(Phase.COMMIT, "explicit denial: NO")
                return finish(
                    Terminal.CONCLUDED, "NO", "explicitly denied", candidates=candidates
                )
            forward, backward = self._frontiers(ws, problem)
            log(
                Phase.DECOMPOSE,
                f"^6 had no candidate to decompose; {problem.source} reaches "
                f"{{{', '.join(forward) or 'nothing'}}}, {problem.target} is reached "
                f"from {{{', '.join(backward) or 'nothing'}}} -- no join",
                forward=forward,
                backward=backward,
            )
            return self._prerequisite_stop(
                ws, problem, trace, log, finish, prof, mark, wisdom=0.0, candidates=candidates
            )

        # 4-5 DECOMPOSE and INFER, with backtracking across candidates.
        landed: Inference | None = None
        chosen: Candidate | None = None
        for candidate in candidates:
            bank_trace.fire("^6")
            decomposition = self.decomposition.decompose(ws, candidate)
            decompositions.append(decomposition)
            log(
                Phase.DECOMPOSE,
                f"^6 {candidate}: {len(decomposition.present)}/"
                f"{len(decomposition.required)} constituent(s) supported",
                candidate=str(candidate),
                missing=list(decomposition.missing),
                contested=list(decomposition.contested),
            )
            if not decomposition.complete:
                what = "contested" if decomposition.blocked_only_by_dispute else "missing"
                backtracks.append(
                    f"{candidate}: {what} {', '.join(decomposition.missing)}"
                )
                continue

            bank_trace.fire("^9")
            inference = self.inference.land(ws, decomposition)
            log(
                Phase.INFER,
                f"^9 {inference.verdict} on {candidate}",
                candidate=str(candidate),
                verdict=inference.verdict,
            )
            if (
                inference.conclusion is not None
                and inference.conclusion.status is Status.CONTRADICTED
            ):
                # The route is sound but the conclusion it lands on is held
                # FALSE as a given. Deriving it did not make it true; it made
                # the workspace disagree with itself about this exact claim.
                # That is a dispute to report, never a YES to emit.
                key = inference.conclusion.key
                log(
                    Phase.COMMIT,
                    f"derived {key} but its denial is given: disputed",
                    contested=[key],
                )
                return finish(
                    Terminal.INADMISSIBLE,
                    "INADMISSIBLE",
                    f"contradictory premises on the queried route: {key}",
                    candidates=candidates,
                )
            if inference.verdict == "YES":
                landed, chosen = inference, candidate
                break
            backtracks.append(f"{candidate}: ^9 returned {inference.verdict}")

        if landed is None or chosen is None:
            log(
                Phase.INFER,
                f"no candidate survived ^6; backtracked {len(backtracks)} time(s)",
                backtracks=len(backtracks),
            )
            # Rule C -- contradiction is LOCAL to the question. A route whose
            # every absent link is held in both polarities is not unknown, it
            # is disputed, and the question is inadmissible until the dispute
            # is resolved. A contradiction elsewhere in the workspace, off every
            # surfaced route, does not poison this answer. (The earlier design
            # refused every question the moment any contradiction existed,
            # which made a living workspace useless after its first dispute.)
            disputed = [d for d in decompositions if d.blocked_only_by_dispute]
            if disputed:
                keys = sorted({k for d in disputed for k in d.contested})
                log(
                    Phase.COMMIT,
                    f"the only route(s) run through a disputed link: {', '.join(keys)}",
                    contested=keys,
                )
                return finish(
                    Terminal.INADMISSIBLE,
                    "INADMISSIBLE",
                    f"contradictory premises on the queried route: {', '.join(keys)}",
                    candidates=candidates,
                )
            # A denial that was GIVEN is knowledge, whatever association
            # surfaced. ^8 may have walked a partial route through a shadow or
            # a guess; ^6 found its links unsupported; and the question is
            # still settled, because the premises say the claim is false. The
            # no-candidate branch above consults the same denial; without this
            # check a reasoner would answer "I do not know" to a question it
            # was explicitly told the answer to, merely because something
            # reminded it of a route.
            denial = ws.props.get(f"~{problem.source}|{problem.relation}|{problem.target}")
            if denial is not None and denial.status in ASSERTIVE:
                log(Phase.COMMIT, "explicit denial outranks an unsupported route: NO")
                return finish(
                    Terminal.CONCLUDED, "NO", "explicitly denied", candidates=candidates
                )
            return self._prerequisite_stop(
                ws, problem, trace, log, finish, prof, mark, wisdom=2.0, candidates=candidates
            )

        # 6 COMPARE -- CDAB under a shared bias, so only real divergence shows.
        confidence = self._compare(ws, candidates, decompositions, chosen, log)

        # 7 CHECK PREREQUISITES -- RPM D -> W -> P on the goal itself.
        planner = RpmPlanner()
        goal = Goal(
            name=problem.name,
            d=PrereqState(score=10.0 * prof.g[_drive_of(problem.target_channel)]),
            w=PrereqState(score=10.0 * confidence),
            p=PrereqState(score=DEFAULT_SUFFICIENCY + 2.0),
        )
        result = planner.run(goal)
        log(
            Phase.CHECK_PREREQUISITES,
            f"RPM D={goal.d.score:.1f} W={goal.w.score:.1f} P={goal.p.score:.1f} "
            f"-> {result.terminal.value}",
            terminal=result.terminal.value,
        )
        if result.terminal is not Terminal.CONCLUDED:
            return finish(
                result.terminal,
                "UNKNOWN",
                f"RPM blocked at the first unmet prerequisite",
                candidates=candidates,
                confidence=confidence,
            )

        # 8 COMMIT -- Schmitt trigger, so a borderline case does not chatter.
        if not self.gate.decide(confidence):
            log(
                Phase.COMMIT,
                f"confidence {confidence:.2f} below commit threshold {self.gate.high}",
                confidence=confidence,
            )
            return finish(
                Terminal.NEEDS_INFORMATION,
                "UNKNOWN",
                "below the Schmitt commit threshold",
                candidates=candidates,
                confidence=confidence,
            )
        log(Phase.COMMIT, f"committed at confidence {confidence:.2f}", confidence=confidence)

        # 9 ACT -- only after P, C and E have all reported.
        reached = {PHASE_DOMAIN[s.phase] for s in trace}
        missing_domains = [d for d in ("P", "C", "E") if d not in reached]
        if missing_domains:
            raise RuntimeError_(
                "E-RT-004",
                f"ACT reached with {missing_domains} never run; domain descent violated",
            )
        log(Phase.ACT, f"emitting conclusion: {landed.conclusion}")

        # 10 LEARN -- low gain, so one episode cannot rewrite the constitution.
        self.memory.write(
            EXPERIENCE_CELL, self.learn_beta * confidence, Tier.EPISODIC
        )
        log(
            Phase.LEARN,
            f"CMB write at beta={self.learn_beta} (low gain, filtered)",
            beta=self.learn_beta,
        )

        if tick > self.max_ticks:  # pragma: no cover - bounded by construction
            raise RuntimeError_("E-RT-005", "tick budget exceeded")

        return finish(
            Terminal.CONCLUDED,
            "YES",
            candidates=candidates,
            conclusion=landed.conclusion,
            confidence=confidence,
            justification=ws.justification(landed.conclusion.pid),
        )

    # ---- helpers ---------------------------------------------------------

    def _compare(self, ws, candidates, decompositions, chosen, log) -> float:
        """CDAB comparison under a shared bias.

        The comparator's own rule is that alternatives must be matched on bias
        and gain, or it invents differences out of its own asymmetry. Every
        entrant therefore carries the same bias string and the same beta; only
        the activation -- how well supported the route is -- differs.
        """
        entrants: list[CdabCandidate] = []
        for decomposition in decompositions:
            supported = len(decomposition.present) / max(1, len(decomposition.required))
            # A shorter complete route is a better one: fewer links to be wrong.
            brevity = 1.0 / (1.0 + decomposition.candidate.hops)
            entrants.append(
                CdabCandidate(
                    label=str(decomposition.candidate),
                    bias="shared: premise set + query",
                    beta=1.0,
                    activation=supported * (0.75 + 0.25 * brevity),
                )
            )
        if len(entrants) < 2:
            confidence = entrants[0].activation if entrants else 0.0
            log(
                Phase.COMPARE,
                f"CDAB: single candidate, nothing to reject; activation {confidence:.2f}",
                winner=str(chosen),
            )
            return confidence

        difference = tournament(entrants)
        winner = difference.winner or str(chosen)
        best = max(e.activation for e in entrants)
        log(
            Phase.COMPARE,
            f"CDAB winner {winner} by margin {difference.margin:.3f} "
            f"(common mode {difference.common_mode_rejected:.2f} rejected)",
            winner=winner,
            margin=difference.margin,
        )
        return best

    @staticmethod
    def _frontiers(ws, problem) -> tuple[list[str], list[str]]:
        """What the source can reach, and what can reach the target.

        The two sets are the shape of the gap. A caller reading
        NEEDS_INFORMATION wants to know where the chain ran out, and this is
        that answer in the smallest honest form.
        """
        forward: set[str] = set()
        frontier = [problem.source]
        while frontier:
            node = frontier.pop()
            for prop in ws.assertive():
                if prop.subject == node and prop.relation == problem.relation:
                    if prop.obj not in forward:
                        forward.add(prop.obj)
                        frontier.append(prop.obj)
        backward = {
            prop.subject
            for prop in ws.assertive()
            if prop.obj == problem.target and prop.relation == problem.relation
        }
        return sorted(forward), sorted(backward)

    def _prerequisite_stop(self, ws, problem, trace, log, finish, prof, mark, *, wisdom, candidates):
        """RPM on a failed reasoning attempt: name which prerequisite is thin.

        This is the difference between "no" and "I do not have what I would
        need to say yes". Under an open world the missing links are a Wisdom
        block, and a Wisdom block is a request for information, not a verdict.
        """
        planner = RpmPlanner()
        goal = Goal(
            name=problem.name,
            d=PrereqState(score=10.0 * prof.g[_drive_of(problem.target_channel)]),
            w=PrereqState(score=wisdom),
            p=PrereqState(score=DEFAULT_SUFFICIENCY + 2.0),
        )
        lacunae = ws.lacunae(since=mark)

        # Descend into the block rather than merely naming it. The first
        # unmet prerequisite becomes a sub-desire -- "acquire the applicable
        # know-how" -- and the planner walks into it. The sub-goal cannot be
        # satisfied from inside this episode (the premise set is what it is),
        # so the descent bottoms out and reports which acquisition would
        # unblock the parent. That is the difference between "no" and "here is
        # the exact thing I would need".
        subgoals: dict[tuple[str, Prereq], Goal] = {}
        if lacunae:
            subgoals[(problem.name, Prereq.W)] = Goal(
                name=f"acquire {lacunae[0]}",
                d=PrereqState(score=goal.d.score),
                w=PrereqState(score=0.0),
                p=PrereqState(score=DEFAULT_SUFFICIENCY + 2.0),
            )
        result = planner.run(goal, subgoals)
        descended = [r.goal for r in result.trace if r.depth > 0]
        log(
            Phase.CHECK_PREREQUISITES,
            f"RPM W={wisdom:.1f} -> {result.terminal.value}; "
            f"{len(lacunae)} lacuna(e) recorded"
            + (f"; descended into {descended[0]!r}" if descended else ""),
            terminal=result.terminal.value,
            lacunae=list(lacunae),
            subgoals=descended,
        )
        if problem.closed_world and result.terminal is Terminal.NEEDS_INFORMATION:
            # A closed world declares the premise set complete, so an unclosable
            # chain is a legitimate NO rather than an admission of ignorance.
            log(Phase.COMMIT, "closed world: unclosable chain is a NO")
            return finish(
                Terminal.CONCLUDED, "NO", "closed-world reading", candidates=candidates
            )
        return finish(
            result.terminal,
            "UNKNOWN",
            f"first unmet prerequisite; lacunae: {', '.join(lacunae) or 'none'}",
            candidates=candidates,
            rpm_trace=list(result.trace),
        )


def _drive_of(ref: str) -> Drive:
    """Which Drive rail a sub-Foundation target sits on."""
    return parse_subfoundation(ref)[0]
