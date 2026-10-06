"""The Organism — a reasoner that is told things over time and holds what it concludes.

The processor (`runtime.py`) answers one question against one premise set and
forgets. That is a calculator. What the revision-streams family needs is the
other thing: a session that is *told* facts, guesses and denials one event at a
time, asked questions in between, has some of what it was told taken back, and
must keep its held beliefs sound through all of it. This module is that
session. It owns ONE `Workspace`, ONE `CognitiveMemoryBoard`, one
`ReasoningProcessor`, a `Motivation` and a `Heartbeat`, and consumes
`events.Event`s.

What it is allowed to claim is fixed by
`docs/working/revision_streams_contract_2026_10_06.md` section 0, and this
docstring repeats the one sentence that matters: ground truth over a finite
event stream is a function of the stream, so a replayer that recomputes from
the log is always correct and *no item in this family can separate the organism
from it on correctness*. What the organism establishes is a convergence
contract -- a reasoner that holds conclusions, reuses them, and un-holds them
when their support dies agrees with recompute-from-scratch on every probe --
and that is not free; every ablation of the mechanisms below breaks it.

Four things are enforced here structurally, each with the failure it prevents:

    standing          conclusions landed on CONCLUDED YES are *held* (pid ->
                      the event that established them). When a given is
                      retracted or denied, the workspace cascade takes the
                      conclusion down and `Response.withdrawn` names it. A
                      reasoner that keeps a conclusion whose support has died
                      is holding a belief with no remaining reason.
    the retract rule  you may forget what you were TOLD (a FACT, or a given in
                      dispute). You may not forget what you DERIVED -- that is
                      refused and the refusal names the givens it rests on
                      (E-ORG-001) -- and you may not forget what you were never
                      told, including your own guesses (E-ORG-002). Letting a
                      caller "retract" a derivation would make the record lie
                      about where a belief came from.
    the heartbeat     not an event, never scored. Experience fades unless LEARN
                      refreshes it, motivation relaxes toward its constitution,
                      and every standing conclusion is audited: all of its
                      roots must still be ASSERTIVE, else E-ORG-003. The audit
                      is how a broken retraction cascade is caught *as a
                      structural fault* rather than as a wrong answer later.
    the firewall      `Motivation` may change what is asked (the self re-asks)
                      and how keenly; it cannot change what is answered. The
                      profile it produces reaches `run_in`, whose own signature
                      law keeps it out of `^6` and `^9`. The organism itself
                      never calls a bank. Tested as a hard law: the same stream
                      under `beta=0` and `beta=0.2` yields identical verdicts,
                      lacunae and contested keys on every ASK.

Cost is reported per event, as a design measurement with no empirical claim:
`Workspace.ask` calls made (through `MeteredWorkspace`) plus the propositions
`^8` scanned (`len(ws.props)` at the moment of the ask, the walk's input size).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ccb_r1"))

from cmb import CognitiveMemoryBoard  # noqa: E402
from rpm import DEFAULT_SUFFICIENCY, Terminal  # noqa: E402

from events import DEFAULT_RELATION, LESSON_RELATION, Event, EventKind, is_foreign  # noqa: E402
from foundations import Drive, FoundationProfile, reasoning_profile  # noqa: E402
from runtime import (  # noqa: E402
    EXPERIENCE_CELL,
    Episode,
    Phase,
    Problem,
    ReasoningProcessor,
)
from workspace import ASSERTIVE, Status, Workspace  # noqa: E402

#: The LEARN low-gain rule, applied to motivation as it is to the processor's
#: experience write: one outcome must not rewrite the machine's principles.
LOW_GAIN = 0.2

#: The RPM Desire gate reads `10 * g[F2]` against `DEFAULT_SUFFICIENCY`. Below
#: this level of Wisdom-desire the processor halts at NEEDS_DESIRE before it
#: reasons at all. The organism asks on the Wisdom rail (`Problem.target_channel`
#: defaults to `F2|A`), so this is the one motivational level that decides
#: whether a question is engaged.
ENGAGEMENT = DEFAULT_SUFFICIENCY / 10.0

#: Stage label for hypotheses that arrive from the stream, so they are never
#: confused with `^8`'s own route guesses (which are swept after each episode).
STREAM_STAGE = "stream"
#: Stage mark on a `leads_to` record derived from a foreign edge and a held lesson (§13).
LESSON_STAGE = "lesson"


class OrganismError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# ---- the metered workspace ----------------------------------------------------

class MeteredWorkspace(Workspace):
    """A `Workspace` that counts its `ask` calls and changes nothing else.

    The cost column of the family is "workspace reads + association edge
    visits". Reads are `ask` calls: `^6` asks once per link of every candidate
    route and the no-candidate path asks the query directly. Counting them here
    rather than in the organism means an ablation that overrides `ask` is still
    metered, because the meter sits above it in the MRO and only counts.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.asks = 0

    def ask(self, subject: str, relation: str, obj: str) -> str:
        self.asks += 1
        return super().ask(subject, relation, obj)


def _metered(factory) -> type:
    """The caller's Workspace class with the ask meter mixed in above it.

    `workspace_factory` exists so an ablations module can hand in a
    `Workspace` subclass with one rule deliberately broken. The ablation's
    overrides must stay in force -- that is the whole point of the ablation --
    and the work column must still be produced. Putting `MeteredWorkspace`
    first in the bases does both: its `ask` counts and defers to the
    ablation's, and its `__init__` defers to the ablation's dataclass init.
    """
    if not (isinstance(factory, type) and issubclass(factory, Workspace)):
        raise OrganismError(
            "E-ORG-005",
            f"workspace_factory must be a Workspace subclass, not {factory!r}",
        )
    if issubclass(factory, MeteredWorkspace):
        return factory
    if factory is Workspace:
        return MeteredWorkspace
    return type(f"Metered{factory.__name__}", (MeteredWorkspace, factory), {})


# ---- motivation -----------------------------------------------------------------

@dataclass(frozen=True)
class Want:
    """One episode's unmet request for information: the question and its gaps."""

    index: int
    relation: str
    query: tuple[str, str]
    lacunae: tuple[str, ...]


class Motivation:
    """The organism's ambition as a *state*, relaxing toward its constitution.

    The processor takes a fixed `FoundationProfile`. An organism's wanting
    moves: a gap it could not close makes it want to know more (`F2` Wisdom
    up); a dispute makes it want order (`F6` Structure up); a conclusion is
    purpose served (`F7` up) and slightly less hunger to know (`F2` down). Each
    heartbeat relaxes every level back toward the constitution by `relax`.

    Two guards, each with the failure it prevents:

    * **Low gain (E-ORG-004).** `beta` and `relax` are both capped at
      `LOW_GAIN`. A motivation that could swing by half on one outcome would
      let a single episode rewrite the organism's principles, which is the
      exact thing the processor's own LEARN rule (E-RT-003) forbids.
    * **Engagement is constitutional, not moody.** If the constitution wants
      to know (`g[F2] >= ENGAGEMENT`), perturbation may never relax it below
      that level. Without this, five answered questions at `beta=0.2` would
      drop Wisdom-desire under the RPM Desire gate and the sixth question
      would go unasked -- a verdict that depends on the organism's recent
      successes, which the hard law forbids. Ambition sets intensity; it does
      not flip whether the organism engages.
    """

    def __init__(
        self,
        constitution: FoundationProfile,
        relax: float = 0.1,
        beta: float = 0.05,
    ) -> None:
        for name, value in (("beta", beta), ("relax", relax)):
            if not (0.0 <= value <= LOW_GAIN):
                raise OrganismError(
                    "E-ORG-004",
                    f"{name}={value} is not low gain (must be in [0, {LOW_GAIN}]); one "
                    "outcome must not rewrite the organism's principles",
                )
        self.constitution = constitution
        self.beta = beta
        self.relax_rate = relax
        self.g: dict[Drive, float] = dict(constitution.g)
        self.owed: list[Want] = []
        self.perturbations: int = 0

    # -- the state ---------------------------------------------------------

    def _clamp(self, drive: Drive, value: float) -> float:
        floor = 0.0
        if drive is Drive.F2 and self.constitution.g[Drive.F2] >= ENGAGEMENT:
            floor = ENGAGEMENT
        return max(floor, min(1.0, value))

    def perturb(self, terminal: Terminal) -> None:
        """Feed one episode's outcome back into wanting, at low gain."""
        beta = self.beta
        if terminal is Terminal.NEEDS_INFORMATION:
            self.g[Drive.F2] = self._clamp(Drive.F2, self.g[Drive.F2] + beta)
        elif terminal is Terminal.INADMISSIBLE:
            self.g[Drive.F6] = self._clamp(Drive.F6, self.g[Drive.F6] + beta)
        elif terminal is Terminal.CONCLUDED:
            self.g[Drive.F7] = self._clamp(Drive.F7, self.g[Drive.F7] + beta)
            self.g[Drive.F2] = self._clamp(Drive.F2, self.g[Drive.F2] - beta / 2.0)
        else:
            return
        self.perturbations += 1

    def relax(self) -> None:
        """Move every level a `relax` fraction of the way back to the constitution."""
        for drive in Drive:
            home = self.constitution.g[drive]
            self.g[drive] = self._clamp(
                drive, self.g[drive] + self.relax_rate * (home - self.g[drive])
            )

    def profile(self) -> FoundationProfile:
        """This moment's ambition: current levels, the constitution's registers."""
        return FoundationProfile(g=dict(self.g), q=self.constitution.q)

    @property
    def engaged(self) -> bool:
        """Does the organism want to know enough to ask on its own?"""
        return self.g[Drive.F2] >= ENGAGEMENT

    # -- wants ---------------------------------------------------------------

    def owe(self, want: Want) -> None:
        if want.lacunae:
            self.owed.append(want)

    def discharge(self, wants: tuple[Want, ...]) -> None:
        self.owed = [w for w in self.owed if w not in wants]

    @staticmethod
    def _answered(ws: Workspace, key: str) -> bool:
        pos = ws.props.get(key)
        neg = ws.props.get("~" + key)
        return bool(
            (pos is not None and pos.status in ASSERTIVE)
            or (neg is not None and neg.status in ASSERTIVE)
        )

    def wants(self, ws: Workspace | None = None) -> tuple[str, ...]:
        """Lacuna keys of abstentions still unanswered, most recent first.

        A key is answered once the workspace holds it assertively in either
        polarity. Without a workspace nothing has been answered, so every owed
        key is still wanted.
        """
        out: list[str] = []
        for want in reversed(self.owed):
            for key in sorted(want.lacunae):
                if key in out:
                    continue
                if ws is not None and self._answered(ws, key):
                    continue
                out.append(key)
        return tuple(out)

    def owed_for(self, keys: tuple[str, ...]) -> tuple[Want, ...]:
        """The owed questions whose gaps include any of `keys`, most recent first,
        one per distinct question."""
        seen: set[tuple[str, tuple[str, str]]] = set()
        out: list[Want] = []
        for want in reversed(self.owed):
            if not set(want.lacunae) & set(keys):
                continue
            ident = (want.relation, want.query)
            if ident in seen:
                continue
            seen.add(ident)
            out.append(want)
        return tuple(out)

    def __str__(self) -> str:
        levels = " ".join(f"{d.value} {self.g[d]:.2f}" for d in Drive)
        return f"motivation {levels} (beta {self.beta}, relax {self.relax_rate})"


# ---- heartbeat -----------------------------------------------------------------

@dataclass(frozen=True)
class BeatReport:
    beat_no: int
    charge: float
    faults: tuple[str, ...]
    wants: tuple[str, ...]


class Heartbeat:
    """The tick that is not an event.

    Three things happen on every beat and none of them is a verdict: the
    experience cell decays (so experience fades unless LEARN refreshes it),
    motivation relaxes toward its constitution, and every standing conclusion
    is audited for a dead root. Beats are never scored.
    """

    def __init__(self) -> None:
        self.beats = 0
        self.reports: list[BeatReport] = []
        self.faults: list[str] = []

    def beat(self, organism: "Organism") -> BeatReport:
        self.beats += 1
        recalled = organism.memory.recall(EXPERIENCE_CELL, decay=True)
        organism.motivation.relax()
        faults = tuple(self.audit(organism))
        self.faults.extend(faults)
        report = BeatReport(
            beat_no=self.beats,
            charge=recalled.charge,
            faults=faults,
            wants=organism.motivation.wants(organism.ws),
        )
        self.reports.append(report)
        return report

    @staticmethod
    def audit(organism: "Organism") -> list[str]:
        """Every standing conclusion must rest on ASSERTIVE roots.

        The workspace cascade makes this true by construction, so on a healthy
        organism the audit is silent. It speaks when the cascade has been
        broken -- by an ablation, or by a retraction that reached the workspace
        behind the organism's back -- and it speaks before the broken belief
        can be answered from the record as if it were sound.
        """
        ws = organism.ws
        faults: list[str] = []
        for pid in sorted(organism.standing):
            prop = ws.props.get(pid)
            if prop is None:
                faults.append(
                    f"E-ORG-003 standing conclusion with dead root: {pid} (absent from the workspace)"
                )
                continue
            dead = [
                r for r in dict.fromkeys((pid,) + ws.roots(pid))
                if ws.props[r].status not in ASSERTIVE
            ]
            if dead:
                faults.append(
                    f"E-ORG-003 standing conclusion with dead root: {pid} "
                    f"(dead: {', '.join(dead)})"
                )
        return faults


# ---- the response -----------------------------------------------------------------

@dataclass(frozen=True)
class Response:
    """What one event did to the organism, and what the organism said back.

    `verdict`, `lacunae` and `contested` are set only by an ASK. `withdrawn`
    names standing conclusions that are no longer ASSERTIVE after this event.
    `satisfied` names wants this event closed; `resolved` holds the episodes
    of the organism's own re-asks, which are never scored. `work` is
    `work_asks + work_scanned`.
    """

    event: Event
    index: int
    accepted: bool
    code: str | None
    note: str
    episode: Episode | None
    terminal: Terminal | None
    verdict: str | None
    lacunae: tuple[str, ...]
    contested: tuple[str, ...]
    withdrawn: tuple[str, ...]
    satisfied: tuple[str, ...]
    resolved: tuple[Episode, ...]
    work_asks: int
    work_scanned: int
    work: int
    beat: BeatReport
    #: How an ASK was answered: "walk" (the ten-phase cycle), "hit" (a validated
    #: held YES, no walk), "miss" (record-first on, nothing held),
    #: "rejected:<check>" (a held record failed validation; the walk answered),
    #: or "disabled" (record-first off). Non-ASK events carry "".
    route: str = "walk"
    records_examined: int = 0
    dependency_edges_checked: int = 0

    def __str__(self) -> str:
        head = f"[{self.index:03d}] {self.event}"
        if self.event.kind is EventKind.ASK:
            tail = f"-> {self.verdict} [{self.route}]"
            if self.lacunae:
                tail += f"; lacunae {', '.join(self.lacunae)}"
            if self.contested:
                tail += f"; contested {', '.join(self.contested)}"
        else:
            tail = "ACCEPTED" if self.accepted else f"REFUSED {self.code}"
            if self.note:
                tail += f": {self.note}"
        if self.withdrawn:
            tail += f"; withdrawn {', '.join(self.withdrawn)}"
        if self.satisfied:
            tail += f"; satisfied {', '.join(self.satisfied)}"
        if self.resolved:
            tail += f"; resolved {len(self.resolved)} re-ask(s)"
        return f"{head}  {tail}  (work {self.work})"


@dataclass
class _Outcome:
    """The handler's half of a Response, before the beat and the metering."""

    accepted: bool = True
    code: str | None = None
    note: str = ""
    episode: Episode | None = None
    verdict: str | None = None
    lacunae: tuple[str, ...] = ()
    contested: tuple[str, ...] = ()
    satisfied: tuple[str, ...] = ()
    resolved: tuple[Episode, ...] = field(default_factory=tuple)
    terminal: Terminal | None = None
    route: str = ""
    records_examined: int = 0
    dependency_edges_checked: int = 0


# ---- the organism -----------------------------------------------------------------

class Organism:
    """A persistent reasoning session over a stream of events.

    `profile` is the constitution (default: `reasoning_profile()`); `memory`
    the experience board; `closed_world` the workspace's reading of absence;
    `processor_kwargs` / `motivation_kwargs` are forwarded to the
    `ReasoningProcessor` and `Motivation`; `workspace_factory` is the
    `Workspace` subclass to hold beliefs in (an ablation hands in its own).
    """

    def __init__(
        self,
        profile: FoundationProfile | None = None,
        memory: CognitiveMemoryBoard | None = None,
        *,
        closed_world: bool = False,
        processor_kwargs: dict | None = None,
        motivation_kwargs: dict | None = None,
        workspace_factory: type = Workspace,
        record_first: bool = False,
        record_invalidation: str = "context",
        record_narrow=None,
    ) -> None:
        if record_invalidation not in ("context", "dependency"):
            raise OrganismError(
                "E-ORG-006",
                f"record_invalidation must be 'context' or 'dependency', not {record_invalidation!r}",
            )
        #: The guarded positive-answer path (memory contract M8). Off by default:
        #: the organism is then the walk-first reasoner unchanged. On, only a
        #: still-valid held YES may be served from the record; everything else
        #: falls back to the walk. `record_invalidation` is the directive's
        #: order of work: "context" first (any accepted mutation since the record
        #: was established invalidates it), "dependency" as the refinement (the
        #: record's own roots are checked, which the workspace cascade keeps
        #: exact).
        self.record_first = record_first
        self.record_invalidation = record_invalidation
        #: Optional narrowing step over the record candidates (memory contract
        #: M8.6, the "record-first with RPA" path). A callable
        #: `(key, candidates) -> candidates'` that may only REMOVE candidates;
        #: returning one the index did not offer is refused (E-ORG-007). The
        #: organism never imports an atlas; whatever narrows is injected, so a
        #: measured difference between the two record-first paths is
        #: attributable to the narrowing alone.
        self.record_narrow = record_narrow
        self.record_stats: dict[str, int] = {"hit": 0, "miss": 0, "rejected": 0}
        self.last_mutation: int = -1
        #: pid -> index of the ASK whose walk last established or re-validated the
        #: held YES (the record's `derived_at`). `standing` keeps the index that
        #: first established it; this is what the context check compares.
        self.validated_at: dict[str, int] = {}
        self.profile = profile or reasoning_profile()
        self.memory = memory or CognitiveMemoryBoard()
        self.ws: MeteredWorkspace = _metered(workspace_factory)(closed_world=closed_world)
        self.processor = ReasoningProcessor(
            self.profile, self.memory, **(processor_kwargs or {})
        )
        self.motivation = Motivation(self.profile, **(motivation_kwargs or {}))
        self.heartbeat = Heartbeat()
        #: conclusion pid -> index of the ASK event that established it.
        self.standing: dict[str, int] = {}
        self.log: list[Response] = []
        self.clock = 0
        self.asks_made = 0
        self.reasks_made = 0
        self._scanned = 0

    # -- the stream -----------------------------------------------------------

    def consume(self, event: Event) -> Response:
        """Apply one event, withdraw what fell, beat, and report."""
        index = self.clock
        self.clock += 1
        asks_before = self.ws.asks
        self._scanned = 0

        handler = {
            EventKind.FACT: self._fact,
            EventKind.HYPOTHESIS: self._hypothesis,
            EventKind.NEGATION: self._negation,
            EventKind.RETRACT: self._retract,
            EventKind.ASK: self._ask,
        }[event.kind]
        outcome = handler(event, index)
        if event.kind is not EventKind.ASK and outcome.accepted:
            self.last_mutation = index

        # Withdrawal runs before the beat so that a conclusion the cascade
        # took down is reported as withdrawn, not audited as a fault. The
        # audit is for conclusions still standing with a root that is not.
        withdrawn = self._withdraw()
        beat = self.heartbeat.beat(self)

        work_asks = self.ws.asks - asks_before
        response = Response(
            event=event,
            index=index,
            accepted=outcome.accepted,
            code=outcome.code,
            note=outcome.note,
            episode=outcome.episode,
            terminal=outcome.episode.terminal if outcome.episode is not None else outcome.terminal,
            verdict=outcome.verdict,
            lacunae=outcome.lacunae,
            contested=outcome.contested,
            withdrawn=withdrawn,
            satisfied=outcome.satisfied,
            resolved=outcome.resolved,
            work_asks=work_asks,
            work_scanned=self._scanned,
            work=work_asks + self._scanned + outcome.dependency_edges_checked,
            beat=beat,
            route=outcome.route,
            records_examined=outcome.records_examined,
            dependency_edges_checked=outcome.dependency_edges_checked,
        )
        self.log.append(response)
        return response

    def run_stream(self, events) -> list[Response]:
        return [self.consume(event) for event in events]

    # -- handlers ---------------------------------------------------------------

    def _fact(self, event: Event, index: int) -> _Outcome:
        wants_before = self.motivation.wants(self.ws)
        prop = self.ws.fact(event.subject, event.relation, event.obj)
        entailed = self._entail(event, prop)
        satisfied = self._closed(wants_before)
        resolved: tuple[Episode, ...] = ()
        if satisfied and self.motivation.engaged:
            resolved = self._resolve(satisfied, index)
        if prop.status is Status.CONTRADICTED:
            note = f"given, and now in dispute with its denial: {event.key}"
        else:
            note = f"given as {prop.status.value}"
        if entailed:
            note += f"; lesson applied: {', '.join(entailed)}"
        return _Outcome(note=note, satisfied=satisfied, resolved=resolved)

    def _entail(self, event: Event, prop) -> tuple[str, ...]:
        """Contract §13: a lesson `r entails leads_to` held together with an edge
        `s -[r]-> o` lands `s|leads_to|o` as a DERIVED record whose support names
        both. Nothing else is special: `^6` then finds the link present, a
        conclusion through it carries it in its support, and retracting the edge
        or the lesson cascades through `Workspace.retract`. A lesson is given,
        never induced, and no weight anywhere changes."""
        if prop.status is not Status.FACT:
            return ()                                   # in dispute, or absorbed: nothing to apply
        if event.relation == LESSON_RELATION:
            if event.obj != DEFAULT_RELATION or not is_foreign(event.subject):
                return ()
            edges = [p for p in list(self.ws.props.values())
                     if p.relation == event.subject and not p.negated and p.status in ASSERTIVE]
            lesson_pid = prop.pid
        elif is_foreign(event.relation):
            held = self.ws.props.get(f"{event.relation}|{LESSON_RELATION}|{DEFAULT_RELATION}")
            if held is None or held.status not in ASSERTIVE:
                return ()
            edges, lesson_pid = [prop], held.pid
        else:
            return ()
        landed = []
        for edge in edges:
            twin = self.ws.props.get(f"{edge.subject}|{DEFAULT_RELATION}|{edge.obj}")
            if twin is not None and twin.status in ASSERTIVE:
                continue                                # already given or derived: nothing to add
            derived = self.ws.derive(edge.subject, DEFAULT_RELATION, edge.obj, (edge.pid, lesson_pid),
                                     stage=LESSON_STAGE, cas="^9^C_{F2}|A")
            if derived.status is Status.DERIVED:
                landed.append(derived.pid)
        return tuple(landed)

    def _hypothesis(self, event: Event, index: int) -> _Outcome:
        before = self.ws.props.get(event.key)
        prop = self.ws.hypothesize(event.subject, event.relation, event.obj, stage=STREAM_STAGE)
        if prop.status is Status.RETRACTED:
            note = "dead on arrival: the claim is already denied as a given"
        elif before is not None and prop is before:
            note = f"no-op: the claim is already held as {prop.status.value}"
        else:
            note = "entered as a hypothesis; it carries no answer until confirmed"
        return _Outcome(note=note)

    def _negation(self, event: Event, index: int) -> _Outcome:
        wants_before = self.motivation.wants(self.ws)
        prop = self.ws.fact(event.subject, event.relation, event.obj, negated=True)
        satisfied = self._closed(wants_before)
        if prop.status is Status.CONTRADICTED:
            note = f"denied, and now in dispute with the given claim: {event.key}"
        else:
            note = "denied as a given"
        return _Outcome(note=note, satisfied=satisfied)

    def _retract(self, event: Event, index: int) -> _Outcome:
        """Forget a given. Refuse to forget a derivation or a guess.

        The rule is by the status of the positive pid, and it is the oracle's
        rule in workspace terms: ACCEPTED iff the pair is a given still in
        `pos` -- a FACT, or a given now in dispute.
        """
        pid = event.key
        prop = self.ws.props.get(pid)
        if prop is None or prop.status is Status.RETRACTED:
            return _Outcome(
                accepted=False,
                code="E-ORG-002",
                note=f"{pid} was never given; there is nothing to forget",
            )
        if prop.status is Status.HYPOTHESIS:
            return _Outcome(
                accepted=False,
                code="E-ORG-002",
                note=f"{pid} is a guess, not something you were told",
            )
        if prop.status is Status.ASSUMPTION:
            return _Outcome(
                accepted=False,
                code="E-ORG-002",
                note=f"{pid} is an assumption taken on for a branch, not a given",
            )
        if prop.status is Status.DERIVED or (
            prop.status is Status.CONTRADICTED and prop.support
        ):
            roots = ", ".join(self.ws.roots(pid))
            return _Outcome(
                accepted=False,
                code="E-ORG-001",
                note=f"that was derived, not given; it rests on {roots}",
            )
        was_disputed = prop.status is Status.CONTRADICTED
        self.ws.retract(pid)
        note = f"forgotten: {pid}"
        if was_disputed:
            counter = self.ws.props.get("~" + pid)
            if counter is not None and counter.status in ASSERTIVE:
                note += f"; the denial ~{pid} stands again"
        return _Outcome(note=note)

    def _ask(self, event: Event, index: int) -> _Outcome:
        self.asks_made += 1
        route = "disabled"
        examined = 0
        edges = 0
        if self.record_first:
            route, examined, edges = self._record_check(event, index)
            if route == "hit":
                self.record_stats["hit"] += 1
                self.motivation.perturb(Terminal.CONCLUDED)
                return _Outcome(
                    note="answered from the held record; no walk",
                    verdict="YES",
                    terminal=Terminal.CONCLUDED,
                    route=route,
                    records_examined=examined,
                    dependency_edges_checked=edges,
                )
            self.record_stats["miss" if route == "miss" else "rejected"] += 1
        problem = Problem(
            name=f"ask{self.asks_made}",
            relation=event.relation,
            premises=(),
            query=event.pair,
            closed_world=self.ws.closed_world,
        )
        episode, lacunae = self._reason(problem, index)
        if (
            episode.terminal is Terminal.CONCLUDED
            and episode.answer == "YES"
            and episode.conclusion is not None
        ):
            self.standing.setdefault(episode.conclusion.pid, index)
            self.validated_at[episode.conclusion.pid] = index
        return _Outcome(
            note=episode.note,
            episode=episode,
            verdict=episode.answer,
            lacunae=lacunae,
            contested=self._contested(episode),
            route=route,
            records_examined=examined,
            dependency_edges_checked=edges,
        )

    def _record_check(self, event: Event, index: int) -> tuple[str, int, int]:
        """The guarded positive-answer check (memory contract M8.1 step 5).

        Returns (route, records_examined, dependency_edges_checked). Only a
        held YES is a candidate; every uncertain check falls back to the walk
        and names what failed. `Workspace.ask` is never used here: it checks
        no roots, knows nothing of disputed routes, and has side effects
        (M8.3). Validity is read from the record and its support, so the work
        performed is the size of the support set walked, not the workspace.
        """
        key = event.key
        established = self.standing.get(key)
        if established is None:
            return "miss", 0, 0
        if self.record_narrow is not None:
            narrowed = tuple(self.record_narrow(key, (key,)))
            if any(c != key for c in narrowed):
                raise OrganismError(
                    "E-ORG-007",
                    f"the narrowing step returned {narrowed!r}, which the record index did not offer",
                )
            if not narrowed:
                return "rejected:narrowed-out", 1, 0
        prop = self.ws.props.get(key)
        if prop is None or prop.status not in ASSERTIVE:
            return "rejected:not-assertive", 1, 0
        if self.heartbeat.faults:
            return "rejected:faulted-organism", 1, 0
        counter = self.ws.props.get("~" + key)
        if counter is not None and counter.status in (*ASSERTIVE, Status.CONTRADICTED):
            return "rejected:denied-or-disputed", 1, 0
        if self.record_invalidation == "context" and self.last_mutation > self.validated_at.get(key, established):
            return "rejected:context-changed", 1, 0
        roots = self.ws.roots(key)
        edges = 0
        for pid in dict.fromkeys((key,) + roots):
            edges += 1
            if self.ws.props[pid].status not in ASSERTIVE:
                return f"rejected:dead-root", 1, edges
        return "hit", 1, edges

    # -- reasoning -------------------------------------------------------------------

    def _reason(self, problem: Problem, index: int) -> tuple[Episode, tuple[str, ...]]:
        """One episode against the living workspace, under this moment's ambition.

        Returns the episode and ITS lacunae: the gaps this episode hit, read
        back from the workspace at the mark FETCH recorded, before anything
        else can ask. Lacunae are reported only on an UNKNOWN; a YES, a NO or
        a dispute has no gap to name, and a denied pair is never a lacuna.
        """
        self._scanned += len(self.ws.props)
        episode = self.processor.run_in(
            self.ws, problem, profile=self.motivation.profile()
        )
        lacunae = self._lacunae(episode) if episode.answer == "UNKNOWN" else ()
        self.motivation.perturb(episode.terminal)
        if episode.terminal is Terminal.NEEDS_INFORMATION:
            self.motivation.owe(Want(index, problem.relation, problem.query, lacunae))
        return episode, lacunae

    def _lacunae(self, episode: Episode) -> tuple[str, ...]:
        fetch = next(s for s in episode.trace if s.phase is Phase.FETCH)
        return self.ws.lacunae(since=fetch.data["mark"])

    @staticmethod
    def _contested(episode: Episode) -> tuple[str, ...]:
        if episode.terminal is not Terminal.INADMISSIBLE:
            return ()
        keys: set[str] = set()
        for step in episode.trace:
            if step.phase is Phase.COMMIT:
                keys.update(step.data.get("contested", ()))
        return tuple(sorted(keys))

    def _closed(self, wants_before: tuple[str, ...]) -> tuple[str, ...]:
        still = set(self.motivation.wants(self.ws))
        return tuple(sorted(k for k in wants_before if k not in still))

    def _resolve(self, satisfied: tuple[str, ...], index: int) -> tuple[Episode, ...]:
        """Re-ask, on the organism's own initiative, what it was owed.

        Only when the organism wants to know (`g[F2] >= ENGAGEMENT`). The
        re-ask is a real episode -- it perturbs motivation and may owe a new
        want -- but its conclusion never enters `standing`: a self-ask is not
        a probe, and the withdrawn column is scored against probes.
        """
        owed = self.motivation.owed_for(satisfied)
        self.motivation.discharge(owed)
        episodes: list[Episode] = []
        for want in owed:
            self.reasks_made += 1
            problem = Problem(
                name=f"reask{self.reasks_made}",
                relation=want.relation,
                premises=(),
                query=want.query,
                closed_world=self.ws.closed_world,
            )
            episode, _ = self._reason(problem, index)
            episodes.append(episode)
        return tuple(episodes)

    def _withdraw(self) -> tuple[str, ...]:
        fallen = tuple(
            sorted(
                pid for pid in self.standing
                if self.ws.props[pid].status not in ASSERTIVE
            )
        )
        for pid in fallen:
            del self.standing[pid]
            self.validated_at.pop(pid, None)
        return fallen

    # -- inspection ---------------------------------------------------------------------

    def wants(self) -> tuple[str, ...]:
        return self.motivation.wants(self.ws)

    @property
    def faults(self) -> tuple[str, ...]:
        return tuple(self.heartbeat.faults)

    def report(self) -> str:
        world = "closed" if self.ws.closed_world else "open"
        lines = [
            f"organism   {world} world; {self.clock} event(s), {self.asks_made} ask(s), "
            f"{self.reasks_made} self re-ask(s), {self.heartbeat.beats} beat(s)",
            f"holding    {len(self.ws.assertive())} assertive proposition(s)",
        ]
        if self.standing:
            lines.append("standing")
            for pid in sorted(self.standing):
                lines.append(f"  {pid}  (since event {self.standing[pid]})")
        else:
            lines.append("standing   none")
        wants = self.wants()
        lines.append(f"wants      {', '.join(wants) if wants else 'nothing'}")
        if self.heartbeat.faults:
            lines.append(f"faults     {len(self.heartbeat.faults)}")
            lines += [f"  {f}" for f in self.heartbeat.faults]
        else:
            lines.append("faults     none")
        asks = sum(r.work_asks for r in self.log)
        scanned = sum(r.work_scanned for r in self.log)
        lines.append(f"work       asks {asks}, scanned {scanned}, total {asks + scanned}")
        if self.heartbeat.reports:
            lines.append(f"experience charge {self.heartbeat.reports[-1].charge:.4f}")
        lines.append(str(self.motivation))
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.report()
