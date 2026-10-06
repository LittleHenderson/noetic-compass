"""Controls — the recompute oracle, and the oracle with one rule broken.

Contract §0 states the limit of the Revision Streams family before anything
else: ground truth over a finite event stream is a function of the stream, so
a solver that keeps two sets of pairs and re-walks the graph on every ask is
correct on every probe with no truth maintenance in it. `ctl_recompute` is
that solver. It is the **first row of every table** and is pinned at 100% on
every column it can produce. No result in this family may be read as the
organism beating it on correctness.

Everything else here is `ctl_recompute` with exactly one rule removed. Each
control is constructed from the same `Replayer` with one field of `Rules`
flipped, so "oracle minus one rule" is a property of the code, not a label
on a table row. The purpose is to show that each item class detects the
failure mode it was built to detect: a class on which every broken control
still scores 100% is not diagnosing anything, and the experiment says so.

Two things are *not* controls and are not in this module: the `Organism`
(the thing under test) and the ablations (the organism with one workspace
rule removed). Controls have no CAS in them -- this module imports only the
standard library and `events` -- which is what makes them controls.

Cost
----
`Answer.work` counts, for each ask, the adjacency entries the replayer
expanded plus the pairs it filtered for the lacuna and contested columns.
It is reported next to the organism's own per-event work as a design
measurement. The replayer's cost grows with the graph on every ask; a
held-belief reasoner answers a standing conclusion from the record. That
comparison, and nothing stronger, is what the cost column is for.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, fields, replace
from typing import Callable, Sequence

from events import ASSOCIATIVE_RELATION, DEFAULT_RELATION, LESSON_RELATION, Event, EventKind, is_foreign

Pair = tuple[str, str]

YES, NO, UNKNOWN, INADMISSIBLE = "YES", "NO", "UNKNOWN", "INADMISSIBLE"


def key_of(pair: Pair, relation: str = DEFAULT_RELATION) -> str:
    """Pairs become workspace keys the way `scoring.py` expects them (§4)."""
    return f"{pair[0]}|{relation}|{pair[1]}"


# ---------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Answer:
    """One ASK answered by a control. Keys are `s|leads_to|o`, sorted."""

    event_index: int
    subject: str
    obj: str
    verdict: str
    lacunae: tuple[str, ...] = ()
    contested: tuple[str, ...] = ()
    work: int = 0

    @property
    def pair(self) -> Pair:
        return (self.subject, self.obj)


@dataclass(frozen=True)
class Withdrawn:
    """After a RETRACT/NEGATION: earlier YES answers this control no longer gives."""

    event_index: int
    keys: tuple[str, ...]


@dataclass(frozen=True)
class ControlRun:
    name: str
    answers: tuple[Answer, ...]
    withdrawn: tuple[Withdrawn, ...]
    refused: tuple[int, ...]
    work: int

    def verdicts(self) -> tuple[str, ...]:
        return tuple(a.verdict for a in self.answers)


# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Rules:
    """The rules of the recompute oracle. Every field True/"none" is the oracle.

    Each control flips exactly one. The field docstrings name the rule in the
    contract's words so a reader can see what a control is missing without
    reading its code.
    """

    #: §2 RETRACT: a given that is taken back leaves `pos`.
    forget: bool = True
    #: §2 HYPOTHESIS: a guess is not a given; it never enters `pos`.
    firewall: bool = True
    #: §3 rules 1 and 3: a pair in both `pos` and `neg` is contested, not
    #: overwritten by whichever statement came last.
    dispute: bool = True
    #: §3 rule 3: a dispute blocks only the routes it lies on.
    local: bool = True
    #: §4: an open-world UNKNOWN names the gap(s) that would close it.
    name_gaps: bool = True
    #: §3 rules 5/6: closed world answers NO where open answers UNKNOWN.
    honour_world: bool = True
    #: §2: events are applied in stream order; an ask sees only its past.
    in_order: bool = True
    #: "none" | "never_flush" | "flush_on_mutation" -- whether a first answer
    #: for a pair is memoised, and whether a mutation invalidates the memo.
    memo: str = "none"

    def differences(self, other: "Rules") -> tuple[str, ...]:
        return tuple(f.name for f in fields(self) if getattr(self, f.name) != getattr(other, f.name))


ORACLE_RULES = Rules()


# ---------------------------------------------------------------------------
# graph helpers
# ---------------------------------------------------------------------------

def _adjacency(pairs: set[Pair]) -> dict[str, list[str]]:
    adj: dict[str, set[str]] = {}
    for s, o in pairs:
        adj.setdefault(s, set()).add(o)
    return {k: sorted(v) for k, v in adj.items()}


def _reach(adj: dict[str, list[str]], s: str, t: str) -> tuple[bool, int]:
    """Is there a path of >= 1 edge from s to t? Returns (found, work)."""
    seen = {s}
    queue = deque([s])
    work = 0
    while queue:
        node = queue.popleft()
        for nxt in adj.get(node, ()):
            work += 1
            if nxt == t:
                return True, work
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return False, work


def _reach_star(adj: dict[str, list[str]], s: str, t: str) -> tuple[bool, int]:
    """Reflexive reach: `u == u` holds with no edge (§3, §4)."""
    if s == t:
        return True, 0
    return _reach(adj, s, t)


def _simple_routes(adj: dict[str, list[str]], s: str, t: str, *, max_hops: int = 6, limit: int = 64) -> tuple[list[tuple[str, ...]], int]:
    """Every simple (no repeated node) s→t route up to `max_hops`, breadth first.

    This is the graph `^8` surfaces (`HypothesisBank.surface` walks the same
    way with `max_hops=6`, `limit=8`); E-RS-006 keeps generated items inside
    those bounds, so on every scored probe the enumeration is complete. The
    `limit` here is only a runaway stop. Returns (routes, work).
    """
    routes: list[tuple[str, ...]] = []
    queue = deque([(s, (s,))])
    work = 0
    while queue and len(routes) < limit:
        node, path = queue.popleft()
        if len(path) - 1 >= max_hops:
            continue
        for nxt in adj.get(node, ()):
            work += 1
            if nxt in path:
                continue
            route = path + (nxt,)
            if nxt == t:
                routes.append(route)
            else:
                queue.append((nxt, route))
    return routes, work


# ---------------------------------------------------------------------------
# the replayer
# ---------------------------------------------------------------------------

@dataclass
class _State:
    pos: set[Pair] = field(default_factory=set)
    neg: set[Pair] = field(default_factory=set)
    hyp: set[Pair] = field(default_factory=set)
    assoc: set[Pair] = field(default_factory=set)
    #: §13 lessons: foreign-relation edges by relation, and the relations whose lesson is held.
    other: dict[str, set[Pair]] = field(default_factory=dict)
    ent: set[str] = field(default_factory=set)

    def copy(self) -> "_State":
        return _State(set(self.pos), set(self.neg), set(self.hyp), set(self.assoc),
                      {r: set(p) for r, p in self.other.items()}, set(self.ent))

    def entailed(self) -> set[Pair]:
        out: set[Pair] = set()
        for r in self.ent:
            out |= self.other.get(r, set())
        return out

    def foreign(self) -> set[Pair]:
        out: set[Pair] = set()
        for pairs in self.other.values():
            out |= pairs
        return out

    def given(self) -> set[Pair]:
        return self.pos | self.entailed()


class Replayer:
    """`(events, closed_world) -> ControlRun`, parameterised by `Rules`."""

    def __init__(self, name: str, rules: Rules = ORACLE_RULES) -> None:
        if rules.memo not in ("none", "never_flush", "flush_on_mutation"):
            raise ValueError(f"unknown memo rule {rules.memo!r}")
        self.name = name
        self.rules = rules

    def __repr__(self) -> str:
        diff = self.rules.differences(ORACLE_RULES)
        return f"{self.name}(oracle{'' if not diff else ' minus ' + ', '.join(diff)})"

    # ---- transitions (§2) ----------------------------------------------------

    def _apply(self, st: _State, ev: Event) -> bool:
        """Mutate `st` by one non-ASK event. Returns False when REFUSED."""
        r = self.rules
        pair = ev.pair
        if ev.kind in (EventKind.HYPOTHESIS, EventKind.NEGATION) and ev.relation != DEFAULT_RELATION:
            # The family's grammar keys denials and guesses by pair (§1). A
            # denied or guessed *association* has no semantics here; refusing
            # it is better than silently denying the `leads_to` pair.
            raise ValueError(f"{ev.kind.value} under relation {ev.relation!r} has no semantics in this family")
        if ev.kind is EventKind.FACT:
            if ev.relation == ASSOCIATIVE_RELATION:
                st.assoc.add(pair)
                return True
            if ev.relation == LESSON_RELATION:                      # §13: a lesson
                if ev.obj != DEFAULT_RELATION or not is_foreign(ev.subject):
                    raise ValueError(f"lesson {ev} has no semantics in this family")
                st.ent.add(ev.subject)
                st.hyp -= st.other.get(ev.subject, set())
                return True
            if ev.relation != DEFAULT_RELATION:                      # §13: a foreign edge
                st.other.setdefault(ev.relation, set()).add(pair)
                if ev.relation in st.ent:
                    st.hyp.discard(pair)
                return True
            if not r.dispute:
                st.neg.discard(pair)          # last writer wins: the denial is overwritten
            st.pos.add(pair)
            st.hyp.discard(pair)
            return True
        if ev.kind is EventKind.HYPOTHESIS:
            if not r.firewall:
                st.pos.add(pair)              # credulous: a guess is filed as a given
                return True
            if pair in st.given() or pair in st.neg:
                return True                   # dead on arrival; a no-op, still ACCEPTED
            st.hyp.add(pair)
            return True
        if ev.kind is EventKind.NEGATION:
            if not r.dispute:
                st.pos.discard(pair)          # last writer wins: the assertion is overwritten
            st.neg.add(pair)
            st.hyp.discard(pair)
            return True
        if ev.kind is EventKind.RETRACT:
            if ev.relation == LESSON_RELATION:                      # §13: withdraw a lesson
                if ev.obj != DEFAULT_RELATION or not is_foreign(ev.subject):
                    raise ValueError(f"lesson {ev} has no semantics in this family")
                if ev.subject not in st.ent:
                    return False
                if r.forget:
                    st.ent.discard(ev.subject)
                return True
            if ev.relation == ASSOCIATIVE_RELATION:
                target = st.assoc
            elif ev.relation == DEFAULT_RELATION:
                target = st.pos
            else:
                target = st.other.get(ev.relation, set())            # §13: a foreign edge
            if pair not in target:
                return False                  # never given, or held only as derived: REFUSED
            if r.forget:
                target.discard(pair)
            return True
        raise ValueError(f"not a mutation: {ev}")

    # ---- the verdict (§3, §4) ------------------------------------------------

    def _answer(self, st: _State, ev: Event, index: int, closed_world: bool) -> Answer:
        r = self.rules
        s, t = ev.pair
        world_closed = closed_world if r.honour_world else False
        given = st.given()
        contested = given & st.neg if r.dispute else set()
        clean = given - contested
        work = 0

        if not r.local and contested:
            # Global poison: any dispute anywhere refuses every question.
            keys = tuple(sorted(key_of(p) for p in contested))
            return Answer(index, s, t, INADMISSIBLE, (), keys, work)

        adj_clean = _adjacency(clean)
        found_clean, w = _reach(adj_clean, s, t)
        work += w
        if (s, t) in st.neg and found_clean:                                             # rule 1
            return Answer(index, s, t, INADMISSIBLE, (), (key_of((s, t)),), work)
        if found_clean:                                                                  # rule 2
            return Answer(index, s, t, YES, (), (), work)

        if contested:                                                                    # rule 3
            adj_all = _adjacency(clean | contested)
            routes, w = _simple_routes(adj_all, s, t)
            work += w
            if routes:
                on_route = {
                    (a, b) for route in routes for a, b in zip(route, route[1:]) if (a, b) in contested
                }
                keys = tuple(sorted(key_of(k) for k in on_route))
                return Answer(index, s, t, INADMISSIBLE, (), keys, work)

        if (s, t) in st.neg:                                                             # rule 4
            return Answer(index, s, t, NO, (), (), work)
        if world_closed:                                                                 # rule 5
            return Answer(index, s, t, NO, (), (), work)

        lacunae: tuple[str, ...] = ()
        if r.name_gaps:                                                                  # rule 6 + §4
            # The walk graph keeps contested links (^8 walks them) and drops
            # pairs that are only denied.
            untaught = st.foreign() - st.entailed()                 # §13: walked, not chained over
            g_all = (clean | contested | st.hyp | st.assoc | untaught) - (st.neg - given)
            adj_g = _adjacency(g_all)
            named = []
            for u, v in sorted((st.hyp | st.assoc | untaught) - clean - st.neg):
                a, w1 = _reach_star(adj_g, s, u)
                b, w2 = _reach_star(adj_g, v, t)
                work += w1 + w2 + 1
                if a and b:
                    named.append(key_of((u, v)))
            lacunae = tuple(named)      # exactly `required`; the query pair itself is admissible, not required
        return Answer(index, s, t, UNKNOWN, lacunae, (), work)

    # ---- the run ---------------------------------------------------------------

    def __call__(self, events: Sequence[Event], closed_world: bool = False) -> ControlRun:
        r = self.rules
        answers: list[Answer] = []
        withdrawn: list[Withdrawn] = []
        refused: list[int] = []
        memo: dict[Pair, Answer] = {}
        total_work = 0

        st = _State()
        final: _State | None = None
        if not r.in_order:
            # Order-blind: every ask is answered against the state after the
            # whole stream, as if the events were a set rather than a sequence.
            final = _State()
            for ev in events:
                if ev.kind is not EventKind.ASK:
                    self._apply(final, ev)

        yes_so_far: dict[Pair, int] = {}

        for index, ev in enumerate(events):
            if ev.kind is EventKind.ASK:
                if r.memo != "none" and ev.pair in memo:
                    hit = memo[ev.pair]
                    ans = replace(hit, event_index=index, work=1)
                else:
                    ans = self._answer(final if final is not None else st, ev, index, closed_world)
                    if r.memo != "none":
                        memo[ev.pair] = ans
                answers.append(ans)
                total_work += ans.work
                if ans.verdict == YES:
                    yes_so_far.setdefault(ans.pair, index)
                continue

            accepted = self._apply(st, ev)
            if not accepted:
                refused.append(index)
                continue
            if r.memo == "flush_on_mutation":
                memo.clear()
            if ev.kind in (EventKind.RETRACT, EventKind.NEGATION):
                # §5: re-answer every earlier YES against the current state.
                fallen: list[Pair] = []
                for pair in sorted(yes_so_far):
                    probe = Event(EventKind.ASK, pair[0], pair[1])
                    if r.memo != "none" and pair in memo:
                        again = memo[pair]
                    else:
                        again = self._answer(final if final is not None else st, probe, index, closed_world)
                        total_work += again.work
                    if again.verdict != YES:
                        fallen.append(pair)
                for pair in fallen:
                    yes_so_far.pop(pair, None)
                withdrawn.append(Withdrawn(index, tuple(key_of(p) for p in fallen)))

        return ControlRun(self.name, tuple(answers), tuple(withdrawn), tuple(refused), total_work)


# ---------------------------------------------------------------------------
# the controls
# ---------------------------------------------------------------------------

Control = Callable[[Sequence[Event], bool], ControlRun]

#: The headline. Two sets, in-order add/discard, BFS per ask. 100% by construction.
ctl_recompute = Replayer("ctl_recompute")
#: Final static graph; an ask sees the future. Fails exactly the staleness probes.
ctl_order_blind = Replayer("ctl_order_blind", replace(ORACLE_RULES, in_order=False))
#: RETRACT leaves `pos` untouched.
ctl_no_forget = Replayer("ctl_no_forget", replace(ORACLE_RULES, forget=False))
#: HYPOTHESIS enters `pos`.
ctl_credulous = Replayer("ctl_credulous", replace(ORACLE_RULES, firewall=False))
#: A later polarity overwrites the earlier one; nothing is ever contested.
ctl_last_writer = Replayer("ctl_last_writer", replace(ORACLE_RULES, dispute=False))
#: Any dispute anywhere refuses every ask.
ctl_global_poison = Replayer("ctl_global_poison", replace(ORACLE_RULES, local=False))
#: Never names a lacuna.
ctl_mute = Replayer("ctl_mute", replace(ORACLE_RULES, name_gaps=False))
#: Always open world.
ctl_fixed_world = Replayer("ctl_fixed_world", replace(ORACLE_RULES, honour_world=False))
#: First answer per pair, never invalidated.
ctl_memo = Replayer("ctl_memo", replace(ORACLE_RULES, memo="never_flush"))
#: Memo cleared on any mutation. Correct everywhere: the honest comparator for
#: transitive retraction, since it pays recompute on every ask after a change.
ctl_memo_flush = Replayer("ctl_memo_flush", replace(ORACLE_RULES, memo="flush_on_mutation"))

CONTROLS: tuple[Replayer, ...] = (
    ctl_recompute,
    ctl_order_blind,
    ctl_no_forget,
    ctl_credulous,
    ctl_last_writer,
    ctl_global_poison,
    ctl_mute,
    ctl_fixed_world,
    ctl_memo,
    ctl_memo_flush,
)

BY_NAME: dict[str, Replayer] = {c.name: c for c in CONTROLS}

#: Controls that are correct on every column by construction, and pinned so.
CORRECT_BY_CONSTRUCTION: tuple[str, ...] = ("ctl_recompute", "ctl_memo_flush")
