"""Revision streams — the oracle, the item generator, and the fingerprint.

This is the executable form of sections 0-7 and 11 of
`docs/working/revision_streams_contract_2026_10_06.md`, as amended on the same
day after an independent cross-check ran the live Workspace against the
section 2-5 oracle on every section 7 variant (96 streams, 187 probes, zero
disagreements) and on the edge streams the contract defines. The amendments
(verdict order, lacuna walk graph, hypothesis no-op, per-pair holding state)
make the oracle agree with the organism where the organism's behaviour is
principled and already pinned by runtime tests. Where this module and the
contract disagree, the contract wins and this module is wrong.

What this family is allowed to claim (contract section 0)
---------------------------------------------------------
Ground truth over a finite event stream is a function of the stream, so
recomputing from the log is always a correct solver with no truth maintenance
in it. `replay()` below *is* that solver: two sets plus two more for guesses
and associations, in-order add/discard, and a BFS per ask. It has no CAS in
it, no banks, no workspace, no organism -- deliberately, because an oracle that
shared machinery with the thing it scores would be scoring agreement with
itself. The consequence is stated first so nobody reads a results table as
more than it is: **no item in this family can separate a correct organism from
a correct replayer on correctness.** What the family establishes is

1. a **convergence contract** -- a reasoner that holds beliefs across
   episodes, derives once and reuses, and un-derives when support dies,
   agrees with recompute-from-scratch on every probe; and
2. a **diagnostic suite** -- each item class detects a failure mode of a
   held-belief reasoner, and each control is labelled for what it is.

It is not a necessity proof, and the forbidden wordings ("load-bearing"
without "relative to the solver that lacks it", "necessary", "superior") are
forbidden here too.

Discipline copied from `scripts/ccb_r1/tasksets.py`
----------------------------------------------------
* Opaque two-letter tokens sampled from AA..ZZ, so nothing can be answered
  from world knowledge.
* `StreamDifficulty.canonical()` always emits the original knobs and emits a
  later knob only when it is non-default, so adding a knob never changes a
  fingerprint already on record.
* `StreamSet.fingerprint()` is SHA-256 over `json.dumps(canonical(),
  sort_keys=True, separators=(",", ":"))`, byte-identical in method.
* Ground truth is COMPUTED, never passed in: `StreamItem` recomputes the
  oracle on construction and refuses anything that disagrees (E-RS-005).
* Rejection and redraw, bounded at 64 attempts, then the last fault is raised.

Rejection codes
---------------
    E-RS-001  hops < 2: a one-hop query is a lookup, not a chain.
    E-RS-002  probes_before < 1: the stale variants need a standing conclusion.
    E-RS-003  distractors < 0 or interleave < 0.
    E-RS-004  an argument fault: n too small for every class to have both a
              diagnostic and a control item, an unknown or repeated class, an
              item whose mechanism, variant or designed probe is malformed.
    E-RS-005  the designed verdict (or a passed-in expectation) disagrees with
              the oracle. The item is rejected; the generator redraws.
    E-RS-006  fairness: a probe has more simple routes, or a longer one, than
              the bank `^8` walks (limit 8, max_hops 6). Rejected and redrawn,
              so no failure is attributable to a design constant.
    E-RS-007  balance: one verdict exceeds the ceiling share of probes in a
              class (60% unless the generator was given another).
    E-RS-008  the AA..ZZ pool cannot name that many nodes.
    E-RS-009  an event the contract gives no semantics for: a HYPOTHESIS,
              NEGATION or ASK under a relation other than `leads_to`, or a
              FACT or RETRACT under a relation that is neither `leads_to` nor
              `co_occurs`. The oracle refuses to invent a reading.
    E-RS-010  a HYPOTHESIS on a pair the organism currently holds, or may
              hold, from an earlier YES ask (contract sections 2 and 12). The
              workspace's outcome there depends on whether the derivation
              survived, which the oracle cannot know, so the generator never
              emits one; rejected and redrawn.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Iterable, Iterator, Sequence

import events
from events import ASSOCIATIVE_RELATION, DEFAULT_RELATION, LESSON_RELATION, Event, EventKind, is_foreign

__all__ = [
    "BALANCE_CEILING",
    "CLASSES",
    "MAX_HOPS",
    "ROUTE_LIMIT",
    "VARIANTS",
    "Expectation",
    "OracleState",
    "ReplayResult",
    "RevisionError",
    "RouteBound",
    "StreamDifficulty",
    "StreamItem",
    "StreamSet",
    "Verdict",
    "WithdrawnExpectation",
    "final_state",
    "generate_revision_set",
    "guard_balance",
    "guard_hypotheses_fresh",
    "guard_route_bounds",
    "pair_key",
    "replay",
]


class RevisionError(RuntimeError):
    """Raised when the contract is breached or cannot be honoured."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class Verdict(str, Enum):
    """The four answers an ASK can have. Spelled as the encoder spells them."""

    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"
    INADMISSIBLE = "INADMISSIBLE"


Pair = tuple[str, str]

#: The bank's `limit` and `max_hops` (`banks.HypothesisBank.surface`). Copied
#: rather than imported because this module may not reach the bank; the test
#: file, which may, pins them equal.
ROUTE_LIMIT = 8
MAX_HOPS = 6

#: Contract section 6: no single verdict may exceed this share of the probes
#: in any class. Warm-up probes are mostly YES, so 50% is not achievable in R
#: and C; 60% is the registered ceiling. The generator takes the ceiling as an
#: argument and `StreamSet.summary()` reports the measured share per class, so
#: the registered number can be set from data rather than the other way round.
BALANCE_CEILING = 0.60

#: Contract section 7, verbatim: class -> (diagnostic variants, control variants).
VARIANTS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "R": (("R-simple", "R-stale", "R-deep"), ("R-control", "R-revive")),
    "H": (("H-bridge", "H-refute"), ("H-control", "H-confirm")),
    "C": (("C-blocked", "C-stale"), ("C-bypassed", "C-unrelated")),
    "N": (("N-gap",), ("N-control", "N-actionable")),
}
CLASSES = tuple(VARIANTS)

#: Per-pair holding state (contract section 5 as amended). HELD: the last ask
#: on the pair was YES and no mutation has touched its route since. UNCERTAIN:
#: a mutation removed a clean edge that lay on some route, but another clean
#: route survives, so the organism's one derivation may or may not have
#: fallen. A pair in neither state is untracked (never asked YES, asked and
#: not YES, or DEAD until a later YES ask holds it again).
_HELD = "HELD"
_UNCERTAIN = "UNCERTAIN"


def pair_key(pair: Pair) -> str:
    """`s|leads_to|o` -- the workspace key the scorer compares on.

    The oracle works in pairs; lacunae, contested links and withdrawn
    conclusions are all `leads_to` claims, so the relation is fixed here.
    """
    return f"{pair[0]}|{DEFAULT_RELATION}|{pair[1]}"


def _keys(pairs: Iterable[Pair]) -> tuple[str, ...]:
    return tuple(sorted(pair_key(p) for p in pairs))


# ---- difficulty ------------------------------------------------------------

@dataclass(frozen=True)
class StreamDifficulty:
    """The knobs a schedule of stream difficulties is declared over.

    `hops` is the chain length; `distractors` are off-path edges from spare
    nodes; `probes_before` is how many times a standing conclusion is asked
    before the perturbation wherever a variant establishes one; `shadow` puts
    an associative `co_occurs` twin under the designated link so `^8` has a
    route to surface and `^6` has one to reject; `interleave` inserts that
    many unrelated facts between the perturbation and the designed probe.
    """

    hops: int = 3
    distractors: int = 4
    probes_before: int = 1
    shadow: bool = True
    interleave: int = 2

    def __post_init__(self) -> None:
        if self.hops < 2:
            raise RevisionError("E-RS-001", "hops must be >= 2; a 1-hop query is a lookup")
        if self.probes_before < 1:
            raise RevisionError(
                "E-RS-002", "probes_before must be >= 1; the stale variants need a held conclusion"
            )
        if self.distractors < 0 or self.interleave < 0:
            raise RevisionError("E-RS-003", "distractors and interleave must be >= 0")

    def canonical(self) -> dict:
        """Fingerprint form.

        The three original knobs are always emitted; `shadow` and `interleave`
        only when non-default. A registration must survive the generator
        gaining a knob, or every new knob silently voids every fingerprint on
        record.
        """
        base = {
            "hops": self.hops,
            "distractors": self.distractors,
            "probes_before": self.probes_before,
        }
        if not self.shadow:
            base["shadow"] = False
        if self.interleave != 2:
            base["interleave"] = self.interleave
        return base

    def label(self) -> str:
        tail = ("" if self.shadow else "-s0") + ("" if self.interleave == 2 else f"-i{self.interleave}")
        return f"h{self.hops}-d{self.distractors}-p{self.probes_before}{tail}"


# ---- what the oracle produces ----------------------------------------------

@dataclass(frozen=True)
class Expectation:
    """The oracle's answer to one ASK, at its position in the stream.

    `lacunae_*` and `contested_required` are sorted `s|leads_to|o` keys. A
    reported lacuna set is correct iff `required <= reported <= admissible`;
    the lower bound defeats "name nothing", the upper bound defeats "name the
    whole frontier product". Both are empty unless the verdict is UNKNOWN.
    """

    event_index: int
    subject: str
    obj: str
    verdict: Verdict
    lacunae_required: tuple[str, ...] = ()
    lacunae_admissible: tuple[str, ...] = ()
    contested_required: tuple[str, ...] = ()

    def canonical(self) -> dict:
        return {
            "event_index": self.event_index,
            "subject": self.subject,
            "obj": self.obj,
            "verdict": self.verdict.value,
            "lacunae_required": list(self.lacunae_required),
            "lacunae_admissible": list(self.lacunae_admissible),
            "contested_required": list(self.contested_required),
        }


@dataclass(frozen=True)
class WithdrawnExpectation:
    """What a held-belief reasoner must, and may, un-derive after a mutation.

    One per RETRACT or NEGATION event, refused ones included (then both sets
    are empty, since nothing changed). Correct iff `required <= reported <=
    permitted`. A capability column, not a correctness one: the replayer can
    produce it by recomputing its own earlier answers.
    """

    event_index: int
    required: tuple[str, ...] = ()
    permitted: tuple[str, ...] = ()

    def canonical(self) -> dict:
        return {
            "event_index": self.event_index,
            "required": list(self.required),
            "permitted": list(self.permitted),
        }


@dataclass(frozen=True)
class ReplayResult:
    expectations: tuple[Expectation, ...]
    withdrawn: tuple[WithdrawnExpectation, ...]
    refused: tuple[int, ...]


@dataclass(frozen=True)
class OracleState:
    """The four sets of contract section 2 plus the holding state, frozen, for
    tests that want to see a transition directly rather than infer it from a
    later verdict. Invariant, pinned by test: `pos & hyp == set()` -- a guess
    about a given is dead on arrival and a given confirms a guess."""

    pos: frozenset[Pair]
    neg: frozenset[Pair]
    hyp: frozenset[Pair]
    assoc: frozenset[Pair]
    held: frozenset[Pair] = frozenset()
    uncertain: frozenset[Pair] = frozenset()
    #: §13: pairs given under each foreign relation, and the relations whose lesson is held.
    other: tuple[tuple[str, frozenset[Pair]], ...] = ()
    ent: frozenset[str] = frozenset()


# ---- reachability ----------------------------------------------------------

def _successors(pairs: Iterable[Pair]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for s, o in pairs:
        out.setdefault(s, set()).add(o)
    return out


def _reach(graph_pairs: Iterable[Pair], s: str, t: str) -> bool:
    """A path of at least one edge from `s` to `t` over the given pairs."""
    succ = _successors(graph_pairs)
    seen: set[str] = set()
    frontier = list(succ.get(s, ()))
    while frontier:
        node = frontier.pop()
        if node == t:
            return True
        if node in seen:
            continue
        seen.add(node)
        frontier.extend(succ.get(node, ()))
    return False


def _reach_star(graph_pairs: Iterable[Pair], s: str, t: str) -> bool:
    """Reflexive reach: `s == t`, or a path of at least one edge.

    Sections 4 and 5 use this at the ends of a lacuna or a withdrawn
    conclusion, so a gap or a dead link at the very first or very last
    position still counts as lying on the route.
    """
    return s == t or _reach(graph_pairs, s, t)


def _simple_routes(graph_pairs: Iterable[Pair], s: str, t: str, *, stop_after: int) -> tuple[int, int]:
    """(number of simple routes s->t, length of the longest), enumerated by DFS.

    Enumeration stops once more than `stop_after` routes are seen: the guard
    rejects at that point anyway, and a dense hand graph should not make the
    generator enumerate forever.
    """
    succ = _successors(graph_pairs)
    routes = 0
    longest = 0
    stack: list[tuple[str, tuple[str, ...]]] = [(s, (s,))]
    while stack:
        node, path = stack.pop()
        for nxt in sorted(succ.get(node, ())):
            if nxt in path:
                continue  # a cycle is not a route
            if nxt == t:
                routes += 1
                longest = max(longest, len(path))
                if routes > stop_after:
                    return routes, longest
            else:
                stack.append((nxt, path + (nxt,)))
    return routes, longest


def _route_edges(graph_pairs: Iterable[Pair], s: str, t: str) -> set[Pair]:
    """Every edge lying on some simple route s->t (no repeated node).

    Rule 3.3 names the contested links on route with this. On the acyclic
    graphs the generator emits it coincides with the reflexive-reach*
    formulation; on a hand graph with cycles it is the one the organism's
    route-walking `^8` actually sees. E-RS-006 bounds the enumeration for
    anything the generator admits.
    """
    succ = _successors(graph_pairs)
    on_route: set[Pair] = set()
    stack: list[tuple[str, tuple[str, ...]]] = [(s, (s,))]
    while stack:
        node, path = stack.pop()
        for nxt in sorted(succ.get(node, ())):
            if nxt in path:
                continue
            if nxt == t:
                on_route.update(zip(path, path[1:] + (nxt,)))
            else:
                stack.append((nxt, path + (nxt,)))
    return on_route


# ---- the oracle ------------------------------------------------------------

class _Ledger:
    """Contract section 2: four sets of ordered pairs, replayed in stream
    order, plus the per-pair holding state of section 5 (as amended).

    Invariant: `pos & hyp == set()`. A FACT confirms a guess (`hyp.discard`),
    a HYPOTHESIS against a given is a no-op, and nothing else adds to `hyp`.
    """

    def __init__(self) -> None:
        self.pos: set[Pair] = set()
        self.neg: set[Pair] = set()
        self.hyp: set[Pair] = set()
        self.assoc: set[Pair] = set()
        self.tracked: dict[Pair, str] = {}
        # §13 lessons: foreign-relation edges and the relations whose lesson is held
        self.other: dict[str, set[Pair]] = {}
        self.ent: set[str] = set()

    # -- §13 views -----------------------------------------------------------

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

    # -- dispatch ------------------------------------------------------------

    def step(self, event: Event, index: int):
        """Apply one event. Returns an `Expectation` for an ASK, `(accepted,
        WithdrawnExpectation)` for a RETRACT or NEGATION, `True` otherwise."""
        if event.kind is EventKind.ASK:
            return self.ask(event, index)
        if event.kind in (EventKind.RETRACT, EventKind.NEGATION):
            return self.mutate(event, index)
        return self.apply(event, index)

    # -- non-mutating transitions ---------------------------------------------

    def apply(self, event: Event, index: int) -> bool:
        pair = event.pair
        kind, relation = event.kind, event.relation
        if kind is EventKind.FACT:
            if relation == DEFAULT_RELATION:
                self.pos.add(pair)
                self.hyp.discard(pair)  # a guess confirmed is no longer a guess
                return True
            if relation == ASSOCIATIVE_RELATION:
                self.assoc.add(pair)
                return True
            if relation == LESSON_RELATION:
                # §13: the lesson "subject entails leads_to"
                if event.obj != DEFAULT_RELATION or not is_foreign(event.subject):
                    raise _no_semantics(event, index)
                self.ent.add(event.subject)
                self.hyp -= self.other.get(event.subject, set())
                return True
            # §13: a foreign-relation edge; walked by ^8, chained over only when entailed
            self.other.setdefault(relation, set()).add(pair)
            if relation in self.ent:
                self.hyp.discard(pair)
            return True
        if kind is EventKind.HYPOTHESIS:
            _require_leads_to(event, index)
            # Dead on arrival against a known fact, a known denial, or a
            # conclusion the organism currently holds: the workspace keeps the
            # stronger record and the guess never registers.
            if pair in self.given() or pair in self.neg or self.tracked.get(pair) == _HELD:
                return True
            self.hyp.add(pair)
            return True
        raise RevisionError("E-RS-009", f"event {index}: {event} is not a state transition")

    # -- mutations and the withdrawn column (section 5, as amended) -----------

    def _transition(self, event: Event, index: int) -> bool:
        pair, relation = event.pair, event.relation
        if event.kind is EventKind.NEGATION:
            _require_leads_to(event, index)
            self.neg.add(pair)
            self.hyp.discard(pair)  # refutation; `neg` only grows within an item
            return True
        if relation == DEFAULT_RELATION:
            if pair in self.pos:
                self.pos.discard(pair)  # a contested pair is left merely denied
                return True
            return False  # never given, or held only as a derivation
        if relation == ASSOCIATIVE_RELATION:
            if pair in self.assoc:
                self.assoc.discard(pair)
                return True
            return False
        if relation == LESSON_RELATION:
            if event.obj != DEFAULT_RELATION or not is_foreign(event.subject):
                raise _no_semantics(event, index)
            if event.subject in self.ent:
                self.ent.discard(event.subject)
                return True
            return False
        # §13: a foreign-relation edge
        pairs = self.other.get(relation, set())
        if pair in pairs:
            pairs.discard(pair)
            return True
        return False

    def mutate(self, event: Event, index: int) -> tuple[bool, WithdrawnExpectation]:
        """A RETRACT or NEGATION, with what it does to held conclusions.

        `affected` is the event's pair when the mutation removed it from
        `clean` (a RETRACT takes it out of `pos`; a NEGATION makes it
        contested); otherwise nothing lay on any route and -- refused retract,
        denial of a pair never given, retract of a contested pair, retract of
        an association -- both sets are empty.

        A NEGATION of a pair that is HELD or UNCERTAIN kills it outright and
        it is REQUIRED: the organism's derived record is contradicted and
        falls, whether or not the pair was ever a clean edge. Every other
        tracked pair whose clean_before route passes through an affected edge
        is DEAD (REQUIRED if it was HELD, PERMITTED either way) when no clean
        route survives, and UNCERTAIN (PERMITTED) when one does -- the
        organism's one derivation may have rested on the dead route. Pairs no
        affected edge touches are unchanged and not permitted. DEAD pairs are
        untracked until a later YES ask holds them again.
        """
        pair = event.pair
        clean_before = self.clean()
        accepted = self._transition(event, index)
        clean_after = self.clean()
        # §13: a retracted lesson removes every entailed edge at once, so the
        # affected set is the difference, not the event's own pair.
        affected = clean_before - clean_after

        required: set[Pair] = set()
        permitted: set[Pair] = set()
        if event.kind is EventKind.NEGATION and pair in self.tracked:
            del self.tracked[pair]
            required.add(pair)
            permitted.add(pair)
        for q, state in list(self.tracked.items()):
            touched = any(
                _reach_star(clean_before, q[0], k[0]) and _reach_star(clean_before, k[1], q[1])
                for k in affected
            )
            if not touched:
                continue
            permitted.add(q)
            if _reach(clean_after, q[0], q[1]):
                self.tracked[q] = _UNCERTAIN
            else:
                if state == _HELD:
                    required.add(q)
                del self.tracked[q]
        return accepted, WithdrawnExpectation(index, _keys(required), _keys(permitted))

    # -- views ---------------------------------------------------------------

    def contested(self) -> set[Pair]:
        return self.given() & self.neg

    def clean(self) -> set[Pair]:
        return self.given() - self.neg

    def walk_graph(self) -> set[Pair]:
        """What `^8` walks: every pair the workspace holds a *positive record*
        of -- given, disputed, guessed or associated. The negation records
        themselves are not edges; a positive record under dispute is (the bank
        walks CONTRADICTED), and an associative shadow is walked even when its
        `leads_to` twin is denied, because it is a different proposition."""
        return self.pos | self.hyp | self.assoc | self.foreign()

    def snapshot(self) -> OracleState:
        return OracleState(
            frozenset(self.pos), frozenset(self.neg), frozenset(self.hyp), frozenset(self.assoc),
            frozenset(p for p, s in self.tracked.items() if s == _HELD),
            frozenset(p for p, s in self.tracked.items() if s == _UNCERTAIN),
            tuple(sorted((r, frozenset(ps)) for r, ps in self.other.items() if ps)),
            frozenset(self.ent),
        )

    # -- the verdict (section 3, as amended) and lacunae (section 4) ----------

    def ask(self, event: Event, index: int, closed_world: bool = False) -> Expectation:
        _require_leads_to(event, index)
        s, t = event.pair
        contested = self.contested()
        clean = self.clean()
        both = clean | contested

        if (s, t) in self.neg and _reach(clean, s, t):
            # 1 -- the chain is sound and the conclusion is denied as a given:
            # a dispute about this exact claim.
            expectation = Expectation(index, s, t, Verdict.INADMISSIBLE, contested_required=_keys([(s, t)]))
        elif _reach(clean, s, t):
            expectation = Expectation(index, s, t, Verdict.YES)  # 2
        elif _reach(both, s, t):
            # 3 -- reachable only through disputed links; name the contested
            # ones lying on some simple route. A denied pair reached this way
            # is a dispute, not knowledge, so this outranks rule 4.
            on_route = contested & _route_edges(both, s, t)
            expectation = Expectation(index, s, t, Verdict.INADMISSIBLE, contested_required=_keys(on_route))
        elif (s, t) in self.neg:
            # 4 -- an explicit denial with no route at all is knowledge, not a
            # gap, in both worlds.
            expectation = Expectation(index, s, t, Verdict.NO)
        elif closed_world:
            expectation = Expectation(index, s, t, Verdict.NO)  # 5
        else:
            required, admissible = self._lacunae(s, t, clean, contested)  # 6
            expectation = Expectation(
                index, s, t, Verdict.UNKNOWN,
                lacunae_required=_keys(required), lacunae_admissible=_keys(admissible),
            )

        if expectation.verdict is Verdict.YES:
            self.tracked[(s, t)] = _HELD
        else:
            self.tracked.pop((s, t), None)
        return expectation

    def _lacunae(self, s: str, t: str, clean: set[Pair], contested: set[Pair]) -> tuple[set[Pair], set[Pair]]:
        """Section 4, as amended. The walk graph keeps contested links and
        drops only pure denials (`neg - pos`): a gap beyond a disputed link is
        on a route `^8` walks, so it counts. A denied pair is never a lacuna
        itself; the frontier product is never admissible -- only guesses,
        associations and the query pair."""
        untaught = self.foreign() - self.entailed()          # §13: walked, not chained over
        g_all = (clean | contested | self.hyp | self.assoc | untaught) - (self.neg - self.given())
        candidates = self.hyp | self.assoc | untaught | {(s, t)}
        admissible = {
            (u, v) for (u, v) in candidates
            if (u, v) not in clean and (u, v) not in self.neg
            and _reach_star(g_all, s, u) and _reach_star(g_all, v, t)
        }
        required = admissible & (self.hyp | self.assoc | untaught)
        return required, admissible


def _require_leads_to(event: Event, index: int) -> None:
    """HYPOTHESIS, NEGATION and ASK carry `leads_to` only (E-RS-009)."""
    if event.relation != DEFAULT_RELATION:
        raise _no_semantics(event, index)


def _no_semantics(event: Event, index: int) -> RevisionError:
    return RevisionError(
        "E-RS-009",
        f"event {index}: the contract gives {event.kind.value} under relation "
        f"{event.relation!r} no semantics; the oracle will not invent one",
    )


def _replay_steps(stream: Sequence[Event], closed_world: bool) -> Iterator[tuple[int, Event, _Ledger, object]]:
    """Drive the ledger through the stream, yielding after every event.

    The fourth element is the event's product: an `Expectation` for an ASK;
    `(accepted, WithdrawnExpectation)` for a RETRACT or NEGATION, so a refused
    retract still yields its (empty) withdrawn record; `True` for any other
    accepted event. `replay()`, `final_state()` and both guards consume this
    one driver, so they can never drift apart on what state a probe is
    answered in.
    """
    ledger = _Ledger()
    for index, event in enumerate(stream):
        if event.kind is EventKind.ASK:
            yield index, event, ledger, ledger.ask(event, index, closed_world)
        else:
            yield index, event, ledger, ledger.step(event, index)


def replay(stream: Sequence[Event], closed_world: bool) -> ReplayResult:
    """The oracle. Sections 2-5 of the contract, in stream order.

    One `Expectation` per ASK; one `WithdrawnExpectation` per RETRACT or
    NEGATION (refused ones included, with empty sets); the indices of REFUSED
    events. Everything is sorted, so two replays of one stream are equal as
    values and byte-identical once canonicalised.
    """
    expectations: list[Expectation] = []
    withdrawn: list[WithdrawnExpectation] = []
    refused: list[int] = []
    for index, _event, _ledger, product in _replay_steps(stream, closed_world):
        if isinstance(product, Expectation):
            expectations.append(product)
        elif isinstance(product, tuple):
            accepted, record = product
            withdrawn.append(record)
            if not accepted:
                refused.append(index)
        # Any other product is an accepted FACT or HYPOTHESIS: no column.
    return ReplayResult(tuple(expectations), tuple(withdrawn), tuple(refused))


def final_state(stream: Sequence[Event]) -> OracleState:
    """The four sets and the holding state after the whole stream."""
    last = _Ledger()
    for _index, _event, last, _product in _replay_steps(stream, closed_world=False):
        pass
    return last.snapshot()


# ---- the guards (E-RS-006, E-RS-008) -----------------------------------------

@dataclass(frozen=True)
class RouteBound:
    event_index: int
    routes: int
    longest: int


def guard_route_bounds(
    stream: Sequence[Event], *, limit: int = ROUTE_LIMIT, max_hops: int = MAX_HOPS
) -> tuple[RouteBound, ...]:
    """Contract section 6, E-RS-006: for every probe, count simple routes s->t
    and the longest over the graph `^8` actually walks at that position --
    every positive record (`pos | contested | hyp | assoc`) plus every pair the
    organism would hold DERIVED from an earlier YES probe in the item, as a
    direct edge -- and refuse the stream if routes > `limit` or longest >
    `max_hops`. The bank stops at `limit` candidates and `max_hops` edges, so
    an item past either bound could fail for a design constant rather than a
    mechanism; this guard is what makes that attribution impossible.

    Earlier YES pairs are counted whether or not a later mutation would have
    un-derived them: a derivation killed by a negation is CONTRADICTED and
    still walked, one killed by a retract is RETRACTED and not, and counting
    all of them over-counts routes in the second case only. That can reject
    an item the organism might have seen fairly, never admit one it could
    not. Conservative in the right direction.
    """
    bounds: list[RouteBound] = []
    derived: set[Pair] = set()
    for index, event, ledger, product in _replay_steps(stream, closed_world=False):
        if not isinstance(product, Expectation):
            continue
        s, t = event.pair
        routes, longest = _simple_routes(ledger.walk_graph() | derived, s, t, stop_after=limit)
        if routes > limit or longest > max_hops:
            raise RevisionError(
                "E-RS-006",
                f"probe at event {index} ({s} -> {t}) has {routes} simple route(s), longest "
                f"{longest}; the bank walks at most {limit} routes of at most {max_hops} hops",
            )
        bounds.append(RouteBound(index, routes, longest))
        if product.verdict is Verdict.YES:
            derived.add((s, t))
    return tuple(bounds)


def guard_hypotheses_fresh(stream: Sequence[Event]) -> None:
    """E-RS-010: no HYPOTHESIS on a pair that is HELD or UNCERTAIN.

    When the organism holds the pair DERIVED the guess never registers; when
    its derivation has quietly fallen the guess does. The oracle cannot tell
    which, so a stream that asks it to is unscorable and the generator never
    emits one. (The oracle's own no-op covers the HELD case, where the outcome
    is determined; UNCERTAIN is exactly where it is not.)
    """
    ledger = _Ledger()
    for index, event in enumerate(stream):
        if event.kind is EventKind.HYPOTHESIS and event.pair in ledger.tracked:
            raise RevisionError(
                "E-RS-010",
                f"event {index}: hypothesis on {event.subject} -> {event.obj}, a pair "
                f"{ledger.tracked[event.pair].lower()} from an earlier YES ask",
            )
        ledger.step(event, index)


# ---- items -----------------------------------------------------------------

@dataclass(frozen=True)
class StreamItem:
    """One event stream and everything the oracle says about it.

    `expectations` and `withdrawn` are the oracle's output, nothing else:
    construction recomputes `replay(events, closed_world)` and refuses a
    disagreement (E-RS-005), so the only way to hold a `StreamItem` is to hold
    the oracle's answers. Use `StreamItem.build(...)` to let it fill them in.
    `designed_probe_index` is the probe the variant exists for and
    `designed_verdict` what the design says it must be; the oracle must agree
    on that probe too, and the generator asserts it on every probe.
    """

    item_id: str
    mechanism: str
    variant: str
    closed_world: bool
    events: tuple[Event, ...]
    expectations: tuple[Expectation, ...]
    withdrawn: tuple[WithdrawnExpectation, ...]
    designed_probe_index: int
    designed_verdict: Verdict

    def __post_init__(self) -> None:
        if self.mechanism not in VARIANTS:
            raise RevisionError("E-RS-004", f"{self.item_id}: mechanism {self.mechanism!r} not in {''.join(CLASSES)}")
        diagnostic, control = VARIANTS[self.mechanism]
        if self.variant not in diagnostic + control:
            raise RevisionError(
                "E-RS-004", f"{self.item_id}: {self.variant!r} is not a class-{self.mechanism} variant"
            )
        if not (0 <= self.designed_probe_index < len(self.events)) or (
            self.events[self.designed_probe_index].kind is not EventKind.ASK
        ):
            raise RevisionError(
                "E-RS-004", f"{self.item_id}: designed_probe_index {self.designed_probe_index} is not an ASK"
            )
        truth = replay(self.events, self.closed_world)
        if truth.expectations != self.expectations or truth.withdrawn != self.withdrawn:
            raise RevisionError(
                "E-RS-005", f"{self.item_id}: expectations disagree with the oracle; ground truth is computed, not passed in"
            )
        designed = next(x for x in self.expectations if x.event_index == self.designed_probe_index)
        if designed.verdict is not self.designed_verdict:
            raise RevisionError(
                "E-RS-005",
                f"{self.item_id}: designed verdict {self.designed_verdict.value} != oracle "
                f"{designed.verdict.value} at event {self.designed_probe_index}",
            )

    @classmethod
    def build(
        cls, item_id: str, mechanism: str, variant: str, closed_world: bool,
        stream: Sequence[Event], designed_probe_index: int, designed_verdict: Verdict,
    ) -> "StreamItem":
        """Construct with the oracle's answers filled in -- the only generator path."""
        truth = replay(stream, closed_world)
        return cls(
            item_id, mechanism, variant, closed_world, tuple(stream),
            truth.expectations, truth.withdrawn, designed_probe_index, designed_verdict,
        )

    @property
    def role(self) -> str:
        return "diagnostic" if self.variant in VARIANTS[self.mechanism][0] else "control"

    def canonical(self) -> dict:
        return {
            "item_id": self.item_id,
            "mechanism": self.mechanism,
            "variant": self.variant,
            "closed_world": self.closed_world,
            "events": [e.canonical() for e in self.events],
            "expectations": [x.canonical() for x in self.expectations],
            "withdrawn": [w.canonical() for w in self.withdrawn],
            "designed_probe_index": self.designed_probe_index,
            "designed_verdict": self.designed_verdict.value,
        }


@dataclass(frozen=True)
class StreamSet:
    """A generated set plus everything needed to reproduce and verify it.

    `ceiling` is the balance ceiling the set was admitted under. It gates
    acceptance and is reported by `summary()`, but it is not part of the
    canonical form: two sets with identical items are the same set whatever
    number they were judged against.
    """

    name: str
    kind: str
    seed: int
    difficulty: StreamDifficulty
    closed_world: bool
    items: tuple[StreamItem, ...] = field(default_factory=tuple)
    ceiling: float = BALANCE_CEILING

    def __len__(self) -> int:
        return len(self.items)

    def canonical(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "seed": self.seed,
            "difficulty": self.difficulty.canonical(),
            "closed_world": self.closed_world,
            "items": [i.canonical() for i in self.items],
        }

    def fingerprint(self) -> str:
        """SHA-256 over the canonical content. Pre-register this value; a run
        scored against a set with a different one is void."""
        blob = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def summary(self) -> dict:
        """Per class: items, the diagnostic/control split, variants, probes,
        the verdict mix, and the largest verdict share -- the number the
        balance ceiling is judged on, reported so the ceiling can be set from
        data."""
        classes: dict[str, dict] = {}
        for item in self.items:
            entry = classes.setdefault(
                item.mechanism,
                {"items": 0, "diagnostic": 0, "control": 0, "variants": {}, "probes": 0, "verdicts": {}},
            )
            entry["items"] += 1
            entry[item.role] += 1
            entry["variants"][item.variant] = entry["variants"].get(item.variant, 0) + 1
            for x in item.expectations:
                entry["probes"] += 1
                entry["verdicts"][x.verdict.value] = entry["verdicts"].get(x.verdict.value, 0) + 1
        for entry in classes.values():
            entry["variants"] = dict(sorted(entry["variants"].items()))
            entry["verdicts"] = dict(sorted(entry["verdicts"].items()))
            top_verdict, top = max(entry["verdicts"].items(), key=lambda kv: (kv[1], kv[0]))
            entry["max_share"] = round(top / entry["probes"], 4)
            entry["max_verdict"] = top_verdict
        return {
            "name": self.name,
            "closed_world": self.closed_world,
            "difficulty": self.difficulty.label(),
            "ceiling": self.ceiling,
            "items": len(self.items),
            "probes": sum(len(i.expectations) for i in self.items),
            "classes": dict(sorted(classes.items())),
        }


def guard_balance(items: Sequence[StreamItem], *, ceiling: float = BALANCE_CEILING) -> None:
    """Contract section 6, E-RS-007: within each class no verdict may exceed
    the ceiling share of probes. Judged in integers so 3/5 is exactly 60%.
    An unbalanced class lets a constant answer score above chance, which is
    the degenerate pass every diagnostic in this family exists to deny."""
    hundredths = round(ceiling * 100)
    for mechanism in sorted({i.mechanism for i in items}):
        counts: dict[Verdict, int] = {}
        total = 0
        for item in items:
            if item.mechanism != mechanism:
                continue
            for x in item.expectations:
                counts[x.verdict] = counts.get(x.verdict, 0) + 1
                total += 1
        for verdict, count in sorted(counts.items(), key=lambda kv: kv[0].value):
            if count * 100 > hundredths * total:
                raise RevisionError(
                    "E-RS-007",
                    f"class {mechanism}: {verdict.value} is {count}/{total} of probes, "
                    f"above the {hundredths}% ceiling",
                )


# ---- naming ----------------------------------------------------------------

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_POOL = [a + b for a in _ALPHABET for b in _ALPHABET]


def _names(rng: random.Random, count: int) -> list[str]:
    """Opaque two-letter tokens, drawn per item so item k's leftovers can never
    create routes in item k+j. Deliberately meaningless: a real-word entity
    could be answered from world knowledge and reported as reasoning."""
    if count > len(_POOL):
        raise RevisionError("E-RS-008", f"cannot name {count} distinct nodes from AA..ZZ")
    return rng.sample(_POOL, count)


# ---- the generator ---------------------------------------------------------

class _Design(str, Enum):
    """World-neutral designed verdicts. GAP is UNKNOWN in the open world and NO
    in the closed one -- the only difference between paired sets."""

    YES = "YES"
    NO = "NO"
    INADMISSIBLE = "INADMISSIBLE"
    GAP = "GAP"

    def in_world(self, closed_world: bool) -> Verdict:
        if self is _Design.GAP:
            return Verdict.NO if closed_world else Verdict.UNKNOWN
        return Verdict(self.value)


@dataclass
class _Draft:
    """A stream under construction: events plus (index -> designed verdict)."""

    stream: list[Event] = field(default_factory=list)
    designed: dict[int, _Design] = field(default_factory=dict)
    designed_probe: int = -1

    def say(self, *evs: Event) -> None:
        self.stream.extend(evs)

    def probe(self, event: Event, design: _Design, *, designed: bool = False) -> None:
        self.stream.append(event)
        self.designed[len(self.stream) - 1] = design
        if designed:
            self.designed_probe = len(self.stream) - 1


def _draw_item(rng: random.Random, diff: StreamDifficulty, mechanism: str, variant: str) -> _Draft:
    """Lay out one item's events for `variant`, exactly as section 7 lists it.

    Every variant shares a skeleton: backbone chain c0..ch over fresh tokens;
    designated link L = (ci, ci+1); when `shadow`, an associative twin under
    L; `distractors` off-path edges, each from its own spare node so a spare
    has exactly one out-edge and no spare is ever reachable from the chain --
    which is what lets distractors never create or shorten a queried route;
    `interleave` unrelated facts between the perturbation and the designed
    probe. The rng is consumed identically whatever world the set is for, so
    paired open/closed sets are byte-identical in events.

    Beyond the probe the variant exists for, each item carries exactly one
    further probe so that every item is close to balanced on its own and the
    class ceiling holds for any size: diagnostics with a severed chain probe
    the half that is still sound (the part that is known is known); R-control
    probes the retracted off-path pair (the retraction landed where it was
    aimed); every other control probes the reversed query (leads_to is
    directed). None of those extra probes is one on which the class's
    mechanism must fire -- which is why a contested pair is never asked
    directly inside a control: under rule 3 that is INADMISSIBLE, the
    contradiction mechanism itself.
    """
    h = diff.hops
    p = diff.probes_before
    n_dsrc = max(diff.distractors, 1)
    nodes = _names(rng, (h + 1) + (h - 1) + n_dsrc + 1 + 2 * diff.interleave)
    chain, rest = nodes[: h + 1], nodes[h + 1:]
    bypass_nodes, rest = rest[: h - 1], rest[h - 1:]
    dsrc, rest = rest[:n_dsrc], rest[n_dsrc:]
    hyp_src, rest = rest[0], rest[1:]
    inter_nodes = rest

    # R-deep needs (c0, c_{i+1}) to be a genuine derivation, so L is never the
    # first link there; everywhere else L is any link.
    i = rng.randrange(1, h) if variant == "R-deep" else rng.randrange(h)
    L: Pair = (chain[i], chain[i + 1])
    c0, ch = chain[0], chain[-1]

    backbone = [(chain[j], chain[j + 1]) for j in range(h)]
    distractor_targets = sorted(chain)
    distractors: list[Pair] = []
    for k in range(diff.distractors):
        src = dsrc[k]
        others = distractor_targets + sorted(d for d in dsrc if d != src)
        distractors.append((src, rng.choice(others)))
    # The off-path pair a control perturbs. With no distractors asked for, one
    # off-path fact is added so R-control / C-unrelated still have a target.
    if distractors:
        off: Pair = distractors[0]
        extra_off: list[Pair] = []
    else:
        off = (dsrc[0], rng.choice(distractor_targets))
        extra_off = [off]

    def setup(core: list[Event], *, with_bypass: bool = False) -> list[Event]:
        out = list(core)
        if diff.shadow:
            out.append(events.associate(*L))
        out += [events.fact(*d) for d in distractors]
        if variant in ("R-control", "C-unrelated"):
            out += [events.fact(*d) for d in extra_off]
        if with_bypass:
            legs = [c0] + bypass_nodes + [ch]
            out += [events.fact(legs[j], legs[j + 1]) for j in range(len(legs) - 1)]
        rng.shuffle(out)
        return out

    full = [events.fact(*e) for e in backbone]
    minus_l = [events.fact(*e) for e in backbone if e != L]
    interleave = [events.fact(inter_nodes[2 * k], inter_nodes[2 * k + 1]) for k in range(diff.interleave)]

    # The half of the chain that stays sound when L is cut: the longer side,
    # left on a tie; at least one side has an edge because hops >= 2.
    left, right = (c0, chain[i]), (chain[i + 1], ch)
    sound = left if i >= 1 and i >= h - 1 - i else right
    inter_pair: Pair = (c0, chain[i + 1])

    main = events.ask(c0, ch)
    reverse = events.ask(ch, c0)
    d = _Draft()

    if variant == "R-simple":
        d.say(*setup(full), events.retract(*L), *interleave)
        d.probe(main, _Design.GAP, designed=True)
        d.probe(events.ask(*sound), _Design.YES)
    elif variant == "R-stale":
        d.say(*setup(full))
        for _ in range(p):
            d.probe(main, _Design.YES)
        d.say(events.retract(*L), *interleave)
        d.probe(main, _Design.GAP, designed=True)
    elif variant == "R-deep":
        d.say(*setup(full))
        for _ in range(p):
            d.probe(events.ask(*inter_pair), _Design.YES)
            d.probe(main, _Design.YES)
        d.say(events.retract(*L), *interleave)
        d.probe(main, _Design.GAP, designed=True)
        d.probe(events.ask(*inter_pair), _Design.GAP)
    elif variant == "R-control":
        d.say(*setup(full))
        for _ in range(p):
            d.probe(main, _Design.YES)
        d.say(events.retract(*off), *interleave)
        d.probe(main, _Design.YES, designed=True)
        d.probe(events.ask(*off), _Design.GAP)
    elif variant == "R-revive":
        d.say(*setup(full), events.retract(*L))
        d.probe(main, _Design.GAP)
        d.say(events.fact(*L), *interleave)
        d.probe(main, _Design.YES, designed=True)
    elif variant == "H-bridge":
        d.say(*setup(minus_l + [events.hypothesis(*L)]), *interleave)
        d.probe(main, _Design.GAP, designed=True)
        d.probe(events.ask(*sound), _Design.YES)
    elif variant == "H-refute":
        d.say(*setup(minus_l + [events.hypothesis(*L)]))
        d.probe(main, _Design.GAP)
        d.say(events.negation(*L), *interleave)
        d.probe(main, _Design.GAP, designed=True)
        d.probe(events.ask(*sound), _Design.YES)
    elif variant == "H-control":
        d.say(*setup(full), events.hypothesis(hyp_src, rng.choice(chain)), *interleave)
        d.probe(main, _Design.YES, designed=True)
        d.probe(reverse, _Design.GAP)
    elif variant == "H-confirm":
        d.say(*setup(minus_l + [events.hypothesis(*L)]), events.fact(*L), *interleave)
        d.probe(main, _Design.YES, designed=True)
        d.probe(reverse, _Design.GAP)
    elif variant == "C-blocked":
        d.say(*setup(full), events.negation(*L), *interleave)
        d.probe(main, _Design.INADMISSIBLE, designed=True)
        d.probe(events.ask(*sound), _Design.YES)
    elif variant == "C-stale":
        d.say(*setup(full))
        for _ in range(p):
            d.probe(main, _Design.YES)
        d.say(events.negation(*L), *interleave)
        d.probe(main, _Design.INADMISSIBLE, designed=True)
    elif variant == "C-bypassed":
        d.say(*setup(full, with_bypass=True), events.negation(*L), *interleave)
        d.probe(main, _Design.YES, designed=True)
        d.probe(reverse, _Design.GAP)
    elif variant == "C-unrelated":
        d.say(*setup(full))
        for _ in range(p):
            d.probe(main, _Design.YES)
        d.say(events.negation(*off), *interleave)
        d.probe(main, _Design.YES, designed=True)
        d.probe(reverse, _Design.GAP)
    elif variant == "N-gap":
        d.say(*setup(minus_l), *interleave)
        d.probe(main, _Design.GAP, designed=True)
        d.probe(events.ask(*sound), _Design.YES)
    elif variant == "N-control":
        d.say(*setup(full), *interleave)
        d.probe(main, _Design.YES, designed=True)
        d.probe(reverse, _Design.GAP)
    elif variant == "N-actionable":
        d.say(*setup(minus_l), events.fact(*L), *interleave)
        d.probe(main, _Design.YES, designed=True)
        d.probe(reverse, _Design.GAP)
    else:  # pragma: no cover - VARIANTS is the only source of variant names
        raise RevisionError("E-RS-004", f"unknown variant {variant!r}")
    return d


#: Faults that mean "this draw was unlucky, draw again" rather than "the
#: request cannot be honoured".
_REDRAW = ("E-RS-005", "E-RS-006", "E-RS-010")


def _admit(item_id: str, mechanism: str, variant: str, draft: _Draft, closed_world: bool) -> StreamItem:
    """E-RS-005 on every probe, in BOTH worlds, then E-RS-010, then E-RS-006.

    Both worlds are checked whatever world the set is for, so acceptance never
    depends on `closed_world` and paired sets stand or fall together: that is
    what makes "byte-identical event streams" a property rather than a hope.
    """
    for world in (False, True):
        truth = replay(draft.stream, world)
        by_index = {x.event_index: x for x in truth.expectations}
        if set(by_index) != set(draft.designed):
            raise RevisionError("E-RS-005", f"{item_id}: a probe without a designed verdict")
        for index, design in draft.designed.items():
            want, got = design.in_world(world), by_index[index].verdict
            if want is not got:
                raise RevisionError(
                    "E-RS-005",
                    f"{item_id} ({variant}): designed {want.value} != oracle {got.value} "
                    f"at event {index} ({'closed' if world else 'open'} world)",
                )
    guard_hypotheses_fresh(draft.stream)
    guard_route_bounds(draft.stream)
    return StreamItem.build(
        item_id, mechanism, variant, closed_world, draft.stream,
        draft.designed_probe, draft.designed[draft.designed_probe].in_world(closed_world),
    )


def generate_revision_set(
    n: int,
    seed: int,
    difficulty: StreamDifficulty | None = None,
    closed_world: bool = False,
    classes: Sequence[str] = CLASSES,
    name: str = "revision_streams",
    ceiling: float = BALANCE_CEILING,
) -> StreamSet:
    """`n` items spread as evenly as possible over `classes`, each class half
    diagnostic and half control (rounded), shuffled within the class.

    Variants cycle through section 7's lists in order, so every variant
    appears once a class has as many items of a role as that role has
    variants. Each item is drawn, judged against the oracle on every probe in
    both worlds (E-RS-005), judged for a hypothesis on a held pair (E-RS-010)
    and against the bank's route bounds (E-RS-006), and redrawn on any of
    those faults, at most 64 times before the fault is raised. The finished
    set is judged against `ceiling` (E-RS-007) in both worlds. `closed_world`
    never touches the rng, so `generate_revision_set(seed=s)` and `(seed=s,
    closed_world=True)` emit byte-identical event streams and differ only by
    UNKNOWN -> NO.
    """
    classes = tuple(classes)
    if not classes or len(set(classes)) != len(classes) or any(c not in VARIANTS for c in classes):
        raise RevisionError("E-RS-004", f"classes must be distinct members of {''.join(CLASSES)}; got {classes!r}")
    if n < 2 * len(classes):
        raise RevisionError(
            "E-RS-004",
            f"n must be >= {2 * len(classes)} so every class has a diagnostic and a control item",
        )
    if not 0.0 < ceiling <= 1.0:
        raise RevisionError("E-RS-004", f"ceiling must be in (0, 1]; got {ceiling!r}")
    diff = difficulty or StreamDifficulty()
    rng = random.Random(seed)

    items: list[StreamItem] = []
    for position, mechanism in enumerate(classes):
        count = n // len(classes) + (1 if position < n % len(classes) else 0)
        diagnostic_n = round(count / 2)
        roles = [True] * diagnostic_n + [False] * (count - diagnostic_n)
        rng.shuffle(roles)
        diag_cycle = itertools.cycle(VARIANTS[mechanism][0])
        ctl_cycle = itertools.cycle(VARIANTS[mechanism][1])
        for k, is_diag in enumerate(roles):
            variant = next(diag_cycle) if is_diag else next(ctl_cycle)
            item_id = f"{mechanism.lower()}{k:04d}"
            for attempt in range(64):
                try:
                    items.append(_admit(item_id, mechanism, variant, _draw_item(rng, diff, mechanism, variant), closed_world))
                    break
                except RevisionError as exc:
                    if exc.code not in _REDRAW or attempt == 63:
                        raise
            else:  # pragma: no cover - the loop always breaks or raises
                raise RevisionError("E-RS-005", f"{item_id}: exhausted retries")

    guard_balance(items, ceiling=ceiling)
    # The paired world must pass the same ceiling, or acceptance would depend
    # on the world and the paired streams could not be byte-identical.
    guard_balance(
        [replace(i, closed_world=not closed_world, **_retruth(i, not closed_world)) for i in items],
        ceiling=ceiling,
    )
    return StreamSet(name, "revision_streams", seed, diff, closed_world, tuple(items), ceiling)


def _retruth(item: StreamItem, closed_world: bool) -> dict:
    truth = replay(item.events, closed_world)
    designed = next(x for x in truth.expectations if x.event_index == item.designed_probe_index)
    return {"expectations": truth.expectations, "withdrawn": truth.withdrawn, "designed_verdict": designed.verdict}
