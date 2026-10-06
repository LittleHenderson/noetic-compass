"""Revision streams — the oracle is the contract, and the generator obeys it.

`docs/working/revision_streams_contract_2026_10_06.md` was fixed before
`revision.py` was written; these tests pin the module to its sentences. One
test per transition rule, one per verdict rule, one per lacuna bound, one per
withdrawn bound; then the generator's discipline: determinism, a fingerprint
that moves when anything moves and stays put when a default knob is added,
ground truth computed never passed in, balance, fairness, paired worlds, and
the structural fact that the oracle reaches no CAS organ -- because an oracle
that shared machinery with the thing it scores would be scoring agreement
with itself.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / "scripts" / "cas_rpu"
sys.path.insert(0, str(PACKAGE))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

import events  # noqa: E402
from banks import HypothesisBank  # noqa: E402
from events import EventKind  # noqa: E402
from revision import (  # noqa: E402
    BALANCE_CEILING,
    CLASSES,
    MAX_HOPS,
    ROUTE_LIMIT,
    VARIANTS,
    Expectation,
    RevisionError,
    StreamDifficulty,
    StreamItem,
    StreamSet,
    Verdict,
    WithdrawnExpectation,
    final_state,
    generate_revision_set,
    guard_balance,
    guard_hypotheses_fresh,
    guard_route_bounds,
    pair_key,
    replay,
)

REFERENCE_N = 40
REFERENCE_SEED = 20261006


# ---- hand streams ------------------------------------------------------------

def chain(*nodes: str) -> list:
    return [events.fact(a, b) for a, b in zip(nodes, nodes[1:])]


def hand_stream(*parts) -> tuple:
    """Flatten events and lists of events into one stream."""
    out: list = []
    for part in parts:
        if isinstance(part, (list, tuple)):
            out.extend(part)
        else:
            out.append(part)
    return tuple(out)


def key(a: str, b: str) -> str:
    return pair_key((a, b))


def reachable(pairs, start: str) -> set[str]:
    """Nodes reachable from `start` by at least one edge -- a test-side BFS,
    kept separate from the module's so the two can disagree."""
    succ: dict[str, set[str]] = {}
    for s, o in pairs:
        succ.setdefault(s, set()).add(o)
    seen: set[str] = set()
    frontier = list(succ.get(start, ()))
    while frontier:
        node = frontier.pop()
        if node in seen:
            continue
        seen.add(node)
        frontier.extend(succ.get(node, ()))
    return seen


def designed(item: StreamItem) -> Expectation:
    return next(x for x in item.expectations if x.event_index == item.designed_probe_index)


def only(item: StreamItem, kind: EventKind, relation: str = events.DEFAULT_RELATION):
    found = [e for e in item.events if e.kind is kind and e.relation == relation]
    assert len(found) == 1, (item.item_id, kind, found)
    return found[0]


def reference(closed_world: bool = False) -> StreamSet:
    return generate_revision_set(REFERENCE_N, REFERENCE_SEED, closed_world=closed_world)


def by_variant(stream_set: StreamSet, variant: str) -> list[StreamItem]:
    found = [i for i in stream_set.items if i.variant == variant]
    assert found, variant
    return found


# ---- section 2: transitions -------------------------------------------------

class TransitionTests(unittest.TestCase):
    def test_a_fact_confirms_a_guess(self):
        state = final_state(hand_stream(events.hypothesis("A", "B"), events.fact("A", "B")))
        self.assertEqual(state.pos, {("A", "B")})
        self.assertEqual(state.hyp, frozenset())

    def test_an_associative_fact_lives_apart_from_the_chained_relation(self):
        state = final_state(hand_stream(events.associate("A", "B")))
        self.assertEqual(state.assoc, {("A", "B")})
        self.assertEqual(state.pos, frozenset())

    def test_a_hypothesis_against_a_known_fact_or_denial_is_a_no_op(self):
        against_fact = final_state(hand_stream(events.fact("A", "B"), events.hypothesis("A", "B")))
        self.assertEqual(against_fact.hyp, frozenset())
        against_denial = final_state(hand_stream(events.negation("C", "D"), events.hypothesis("C", "D")))
        self.assertEqual(against_denial.hyp, frozenset())
        # Observable without the state: after the fact is withdrawn, nothing
        # names (A, B) as a guess -- the lacuna lower bound stays empty.
        result = replay(
            hand_stream(events.fact("A", "B"), events.hypothesis("A", "B"), events.retract("A", "B"), events.ask("A", "B")),
            closed_world=False,
        )
        self.assertIs(result.expectations[0].verdict, Verdict.UNKNOWN)
        self.assertEqual(result.expectations[0].lacunae_required, ())

    def test_a_negation_refutes_a_guess_and_neg_only_grows(self):
        state = final_state(hand_stream(events.hypothesis("A", "B"), events.negation("A", "B"), events.retract("A", "B")))
        self.assertEqual(state.hyp, frozenset())
        self.assertEqual(state.neg, {("A", "B")})

    def test_retract_of_a_derived_only_pair_is_refused(self):
        stream = hand_stream(chain("A", "B", "C"), events.ask("A", "C"), events.retract("A", "C"), events.ask("A", "C"))
        result = replay(stream, closed_world=False)
        self.assertEqual(result.refused, (3,))
        self.assertEqual([x.verdict for x in result.expectations], [Verdict.YES, Verdict.YES])
        self.assertEqual(final_state(stream).pos, {("A", "B"), ("B", "C")})
        # the refused mutation still gets its (empty) withdrawn record
        self.assertEqual(result.withdrawn, (WithdrawnExpectation(3),))

    def test_retract_of_a_pair_never_given_is_refused(self):
        result = replay(hand_stream(events.retract("A", "B"), events.retract("A", "B", events.ASSOCIATIVE_RELATION)), False)
        self.assertEqual(result.refused, (0, 1))

    def test_retract_of_a_contested_pair_leaves_it_merely_denied(self):
        stream = hand_stream(events.fact("A", "B"), events.negation("A", "B"), events.retract("A", "B"), events.ask("A", "B"))
        result = replay(stream, closed_world=False)
        self.assertEqual(result.refused, ())
        state = final_state(stream)
        self.assertEqual(state.pos, frozenset())
        self.assertEqual(state.neg, {("A", "B")})
        self.assertIs(result.expectations[0].verdict, Verdict.NO)

    def test_an_associative_retract_is_accepted_only_when_present(self):
        state = final_state(hand_stream(events.associate("A", "B"), events.retract("A", "B", events.ASSOCIATIVE_RELATION)))
        self.assertEqual(state.assoc, frozenset())

    def test_pos_and_hyp_are_disjoint(self):
        """A guess about a given is dead on arrival and a given confirms a
        guess, so nothing is ever both known and merely supposed."""
        stream = hand_stream(
            events.fact("A", "B"), events.hypothesis("A", "B"),
            events.hypothesis("C", "D"), events.fact("C", "D"),
            events.hypothesis("E", "F"), events.negation("E", "F"), events.hypothesis("E", "F"),
            chain("P", "Q", "R"), events.ask("P", "R"), events.hypothesis("P", "R"),
            events.retract("A", "B"), events.hypothesis("A", "B"),
        )
        for cut in range(len(stream) + 1):
            state = final_state(stream[:cut])
            self.assertEqual(state.pos & state.hyp, frozenset(), cut)
        for item in reference().items:
            for cut in range(len(item.events) + 1):
                state = final_state(item.events[:cut])
                self.assertEqual(state.pos & state.hyp, frozenset(), (item.item_id, cut))

    def test_a_guess_about_a_held_conclusion_is_a_no_op(self):
        """F(a,b) F(b,c) F(c,d) A(b,d) H(b,d) R(c,d) A(a,d): the organism holds
        (b,d) DERIVED when the guess arrives, so the guess never registers and
        the final abstention names no lacuna."""
        stream = hand_stream(
            chain("a", "b", "c", "d"), events.ask("b", "d"), events.hypothesis("b", "d"),
            events.retract("c", "d"), events.ask("a", "d"),
        )
        result = replay(stream, closed_world=False)
        self.assertEqual([x.verdict for x in result.expectations], [Verdict.YES, Verdict.UNKNOWN])
        self.assertEqual(result.expectations[1].lacunae_required, ())
        self.assertEqual(result.expectations[1].lacunae_admissible, (key("a", "d"),))
        self.assertEqual(final_state(stream[:5]).hyp, frozenset())
        self.assertEqual(final_state(stream[:5]).held, {("b", "d")})

    def test_a_hypothesis_is_never_emitted_on_a_held_pair(self):
        """E-RS-010. Held: the guess would silently not register. Uncertain:
        whether it registers depends on a derivation the oracle cannot see."""
        held = hand_stream(chain("A", "B", "C"), events.ask("A", "C"), events.hypothesis("A", "C"))
        with self.assertRaises(RevisionError) as ctx:
            guard_hypotheses_fresh(held)
        self.assertEqual(ctx.exception.code, "E-RS-010")
        uncertain = hand_stream(
            chain("A", "B", "C"), chain("A", "X", "C"), events.ask("A", "C"),
            events.negation("B", "C"), events.hypothesis("A", "C"),
        )
        with self.assertRaises(RevisionError) as ctx:
            guard_hypotheses_fresh(uncertain)
        self.assertEqual(ctx.exception.code, "E-RS-010")
        # Dead pairs are untracked again, and a guess after the fact is fine.
        guard_hypotheses_fresh(hand_stream(chain("A", "B", "C"), events.ask("A", "C"), events.retract("B", "C"), events.hypothesis("A", "C")))
        guard_hypotheses_fresh(hand_stream(chain("A", "B", "C"), events.ask("A", "C"), events.ask("A", "D"), events.hypothesis("A", "D")))
        for stream_set in (reference(), generate_revision_set(48, 4)):
            for item in stream_set.items:
                guard_hypotheses_fresh(item.events)
                asked_yes = {(x.subject, x.obj) for x in item.expectations if x.verdict is Verdict.YES}
                for e in item.events:
                    if e.kind is EventKind.HYPOTHESIS:
                        self.assertNotIn(e.pair, asked_yes, (item.item_id, e))

    def test_an_event_the_contract_gives_no_semantics_is_refused_not_guessed(self):
        for bad in (
            events.hypothesis("A", "B", events.ASSOCIATIVE_RELATION),
            events.negation("A", "B", events.ASSOCIATIVE_RELATION),
            events.ask("A", "B", events.ASSOCIATIVE_RELATION),
            events.fact("A", "B", "owns"),
            events.retract("A", "B", "owns"),
        ):
            with self.assertRaises(RevisionError, msg=str(bad)) as ctx:
                replay((bad,), closed_world=False)
            self.assertEqual(ctx.exception.code, "E-RS-009")


# ---- section 3: the verdict order, one method per rule ----------------------

class TheVerdictOrderOnHandStreams(unittest.TestCase):
    def test_rule_1_denied_but_reachable_is_inadmissible_naming_the_claim(self):
        stream = hand_stream(chain("A", "B", "C"), events.negation("A", "C"), events.ask("A", "C"))
        for world in (False, True):
            x = replay(stream, world).expectations[0]
            self.assertIs(x.verdict, Verdict.INADMISSIBLE)
            self.assertEqual(x.contested_required, (key("A", "C"),))
            self.assertEqual(x.lacunae_required, ())

    def test_rule_2_a_clean_route_is_yes(self):
        stream = hand_stream(chain("A", "B", "C", "D"), events.ask("A", "D"))
        for world in (False, True):
            self.assertIs(replay(stream, world).expectations[0].verdict, Verdict.YES)

    def test_rule_3_a_route_only_through_disputed_links_is_inadmissible(self):
        stream = hand_stream(chain("A", "B", "C", "D"), events.negation("B", "C"), events.ask("A", "D"))
        for world in (False, True):
            x = replay(stream, world).expectations[0]
            self.assertIs(x.verdict, Verdict.INADMISSIBLE)
            self.assertEqual(x.contested_required, (key("B", "C"),))

    def test_rule_4_a_denial_with_no_route_is_no_in_both_worlds(self):
        stream = hand_stream(events.negation("A", "C"), events.ask("A", "C"))
        for world in (False, True):
            x = replay(stream, world).expectations[0]
            self.assertIs(x.verdict, Verdict.NO)
            self.assertEqual((x.lacunae_required, x.lacunae_admissible, x.contested_required), ((), (), ()))

    def test_rule_5_a_closed_world_says_no(self):
        x = replay(hand_stream(chain("A", "B"), events.ask("A", "C")), closed_world=True).expectations[0]
        self.assertIs(x.verdict, Verdict.NO)
        self.assertEqual(x.lacunae_admissible, ())

    def test_rule_6_an_open_world_says_unknown_with_lacunae(self):
        x = replay(hand_stream(chain("A", "B"), events.ask("A", "C")), closed_world=False).expectations[0]
        self.assertIs(x.verdict, Verdict.UNKNOWN)
        self.assertEqual(x.lacunae_admissible, (key("A", "C"),))

    def test_rule_1_outranks_rule_2_and_rule_3_outranks_rule_4_and_the_worlds(self):
        """The order is the semantics: a sound chain to a denied claim is a
        dispute, not a YES; a denied claim reached only through a disputed
        link is a dispute, not knowledge; a disputed route is never a gap."""
        denied_and_clean = hand_stream(chain("A", "B", "C"), events.negation("A", "C"), events.ask("A", "C"))
        self.assertIs(replay(denied_and_clean, True).expectations[0].verdict, Verdict.INADMISSIBLE)
        disputed_route = hand_stream(chain("A", "B", "C"), events.negation("A", "B"), events.ask("A", "C"))
        self.assertIs(replay(disputed_route, True).expectations[0].verdict, Verdict.INADMISSIBLE)
        denied_and_disputed = hand_stream(chain("A", "B", "C"), events.negation("A", "B"), events.negation("A", "C"), events.ask("A", "C"))
        self.assertIs(replay(denied_and_disputed, True).expectations[0].verdict, Verdict.INADMISSIBLE)

    def test_a_contested_pair_asked_directly_is_inadmissible(self):
        """F(a,b) N(a,b) A(a,b): given and denied, with the one-edge route
        itself the disputed link. Rule 3, naming the pair, in both worlds."""
        stream = hand_stream(events.fact("a", "b"), events.negation("a", "b"), events.ask("a", "b"))
        for world in (False, True):
            x = replay(stream, world).expectations[0]
            self.assertIs(x.verdict, Verdict.INADMISSIBLE)
            self.assertEqual(x.contested_required, (key("a", "b"),))

    def test_a_denied_pair_behind_a_disputed_route_is_inadmissible(self):
        """F(a,b) F(b,c) N(b,c) N(a,c) A(a,c): the denial of (a,c) does not
        settle it while a route stands in dispute; the dispute is (b,c)."""
        stream = hand_stream(chain("a", "b", "c"), events.negation("b", "c"), events.negation("a", "c"), events.ask("a", "c"))
        for world in (False, True):
            x = replay(stream, world).expectations[0]
            self.assertIs(x.verdict, Verdict.INADMISSIBLE)
            self.assertEqual(x.contested_required, (key("b", "c"),))

    def test_a_denied_pair_behind_a_partial_route_is_no_in_both_worlds(self):
        """F(a,b) Q(b,c) N(a,c) A(a,c): a guess is not a route, so the explicit
        denial is knowledge -- NO, open or closed, and no lacunae."""
        stream = hand_stream(events.fact("a", "b"), events.hypothesis("b", "c"), events.negation("a", "c"), events.ask("a", "c"))
        for world in (False, True):
            x = replay(stream, world).expectations[0]
            self.assertIs(x.verdict, Verdict.NO)
            self.assertEqual((x.lacunae_required, x.lacunae_admissible, x.contested_required), ((), (), ()))

    def test_rule_3_names_contested_links_on_simple_routes_only(self):
        """A contested edge reachable from s and reaching t but only via a
        repeated node lies on no simple route and is not named."""
        stream = hand_stream(
            chain("A", "B", "C"), events.fact("B", "X"), events.fact("X", "B"),
            events.negation("B", "C"), events.negation("X", "B"), events.ask("A", "C"),
        )
        x = replay(stream, False).expectations[0]
        self.assertIs(x.verdict, Verdict.INADMISSIBLE)
        self.assertEqual(x.contested_required, (key("B", "C"),))

    def test_contested_required_uses_reflexive_reach(self):
        nodes = ("A", "B", "C", "D")
        for first, second in (("A", "B"), ("C", "D")):
            stream = hand_stream(chain(*nodes), events.negation(first, second), events.ask("A", "D"))
            x = replay(stream, closed_world=False).expectations[0]
            self.assertIs(x.verdict, Verdict.INADMISSIBLE)
            self.assertEqual(x.contested_required, (key(first, second),), (first, second))

    def test_contested_required_names_only_the_disputed_links_on_route(self):
        stream = hand_stream(
            chain("A", "B", "C"), chain("X", "Y"),
            events.negation("B", "C"), events.negation("X", "Y"),
            events.ask("A", "C"),
        )
        self.assertEqual(replay(stream, False).expectations[0].contested_required, (key("B", "C"),))

    def test_section_11_negation_of_a_derived_only_pair_makes_the_re_ask_inadmissible(self):
        stream = hand_stream(chain("A", "B", "C"), events.ask("A", "C"), events.negation("A", "C"), events.ask("A", "C"))
        verdicts = [x.verdict for x in replay(stream, False).expectations]
        self.assertEqual(verdicts, [Verdict.YES, Verdict.INADMISSIBLE])

    def test_section_11_hypothesis_then_fact_then_retract_forgets_the_maybe(self):
        stream = hand_stream(events.hypothesis("A", "B"), events.fact("A", "B"), events.retract("A", "B"), events.ask("A", "B"))
        x = replay(stream, False).expectations[0]
        self.assertIs(x.verdict, Verdict.UNKNOWN)
        self.assertEqual(x.lacunae_required, ())
        self.assertEqual(final_state(stream).hyp, frozenset())


# ---- section 4: lacunae -----------------------------------------------------

class LacunaTests(unittest.TestCase):
    def test_lacuna_required_names_the_shadowed_gap(self):
        stream = hand_stream(chain("A", "B"), events.associate("B", "C"), chain("C", "D"), events.ask("A", "D"))
        x = replay(stream, False).expectations[0]
        self.assertIs(x.verdict, Verdict.UNKNOWN)
        self.assertEqual(x.lacunae_required, (key("B", "C"),))
        self.assertIn(key("B", "C"), x.lacunae_admissible)
        for item in by_variant(reference(), "N-gap"):
            shadow = only(item, EventKind.FACT, events.ASSOCIATIVE_RELATION)
            self.assertEqual(designed(item).lacunae_required, (pair_key(shadow.pair),), item.item_id)

    def test_lacuna_required_names_a_hypothesised_gap_too(self):
        stream = hand_stream(chain("A", "B"), events.hypothesis("B", "C"), chain("C", "D"), events.ask("A", "D"))
        self.assertEqual(replay(stream, False).expectations[0].lacunae_required, (key("B", "C"),))

    def test_lacuna_admissible_includes_the_query_pair_but_not_the_frontier_product(self):
        bare = hand_stream(chain("A", "B"), chain("C", "D"), events.ask("A", "D"))
        x = replay(bare, False).expectations[0]
        self.assertEqual(x.lacunae_admissible, (key("A", "D"),))
        self.assertEqual(x.lacunae_required, ())
        shadowed = hand_stream(chain("A", "B"), events.associate("B", "C"), chain("C", "D"), events.ask("A", "D"))
        y = replay(shadowed, False).expectations[0]
        self.assertEqual(set(y.lacunae_admissible), {key("A", "D"), key("B", "C")})
        for frontier in (key("A", "C"), key("B", "D")):
            self.assertNotIn(frontier, y.lacunae_admissible)

    def test_lacuna_bounds_exclude_denied_pairs(self):
        stream = hand_stream(
            chain("A", "B"), events.associate("B", "C"), events.hypothesis("B", "C"), chain("C", "D"),
            events.negation("B", "C"), events.ask("A", "D"),
        )
        x = replay(stream, False).expectations[0]
        self.assertIs(x.verdict, Verdict.UNKNOWN)
        self.assertNotIn(key("B", "C"), x.lacunae_required)
        self.assertNotIn(key("B", "C"), x.lacunae_admissible)
        self.assertEqual(x.lacunae_admissible, (key("A", "D"),))
        for item in by_variant(reference(), "H-refute"):
            refuted = only(item, EventKind.NEGATION)
            x = designed(item)
            self.assertIs(x.verdict, Verdict.UNKNOWN)
            self.assertNotIn(pair_key(refuted.pair), x.lacunae_required, item.item_id)
            self.assertNotIn(pair_key(refuted.pair), x.lacunae_admissible, item.item_id)
            self.assertEqual(x.lacunae_required, ())

    def test_a_gap_beyond_a_contested_link_is_a_lacuna(self):
        """F(a,b) Q(b,c) F(c,d) N(a,b) A(a,d): the walk graph keeps the
        disputed (a,b), so the guess beyond it is on a route `^8` walks and
        must be named; the disputed link itself is never a lacuna."""
        stream = hand_stream(
            events.fact("a", "b"), events.hypothesis("b", "c"), events.fact("c", "d"),
            events.negation("a", "b"), events.ask("a", "d"),
        )
        x = replay(stream, False).expectations[0]
        self.assertIs(x.verdict, Verdict.UNKNOWN)
        self.assertEqual(x.lacunae_required, (key("b", "c"),))
        self.assertEqual(set(x.lacunae_admissible), {key("b", "c"), key("a", "d")})
        self.assertNotIn(key("a", "b"), x.lacunae_admissible)

    def test_a_pure_denial_still_blocks_the_lacuna_walk(self):
        """N(b,c) with no positive record: a denial that was never given
        positively is not a path, so nothing beyond it is reachable."""
        stream = hand_stream(events.fact("a", "b"), events.negation("b", "c"), events.hypothesis("c", "d"), events.fact("d", "e"), events.ask("a", "e"))
        x = replay(stream, False).expectations[0]
        self.assertIs(x.verdict, Verdict.UNKNOWN)
        self.assertEqual(x.lacunae_required, ())
        self.assertEqual(x.lacunae_admissible, (key("a", "e"),))

    def test_an_unreachable_guess_or_shadow_is_not_a_lacuna(self):
        stream = hand_stream(chain("A", "B"), events.hypothesis("X", "Y"), events.associate("P", "Q"), events.ask("A", "C"))
        x = replay(stream, False).expectations[0]
        self.assertEqual(x.lacunae_admissible, (key("A", "C"),))

    def test_lacunae_are_empty_off_unknown_and_everywhere_in_a_closed_world(self):
        stream = hand_stream(chain("A", "B"), events.associate("B", "C"), chain("C", "D"), events.ask("A", "D"), events.ask("A", "B"))
        closed = replay(stream, True).expectations
        for x in closed:
            self.assertEqual((x.lacunae_required, x.lacunae_admissible), ((), ()))
        self.assertEqual(replay(stream, False).expectations[1].lacunae_admissible, ())


# ---- section 5: withdrawn ----------------------------------------------------

class WithdrawnTests(unittest.TestCase):
    def test_withdrawn_required_and_permitted(self):
        for first, second in (("A", "B"), ("C", "D")):
            stream = hand_stream(chain("A", "B", "C", "D"), events.ask("A", "D"), events.retract(first, second))
            w = replay(stream, False).withdrawn
            self.assertEqual(w, (WithdrawnExpectation(4, (key("A", "D"),), (key("A", "D"),)),), (first, second))
        for item in by_variant(reference(), "R-stale"):
            retract = only(item, EventKind.RETRACT)
            x = designed(item)
            (w,) = item.withdrawn
            self.assertEqual(w.event_index, item.events.index(retract))
            self.assertEqual(w.required, (key(x.subject, x.obj),), item.item_id)
            self.assertLessEqual(set(w.required), set(w.permitted))

    def test_a_second_clean_route_makes_withdrawal_permitted_not_required(self):
        """The organism's one derivation may have rested on the dead route
        while the other survives: it may withdraw, it need not."""
        stream = hand_stream(chain("A", "B", "C"), chain("A", "X", "C"), events.ask("A", "C"), events.negation("B", "C"))
        (w,) = replay(stream, False).withdrawn
        self.assertEqual(w.required, ())
        self.assertEqual(w.permitted, (key("A", "C"),))
        self.assertEqual(final_state(stream).uncertain, {("A", "C")})
        self.assertEqual(final_state(stream).held, frozenset())
        for item in by_variant(reference(), "C-unrelated") + by_variant(reference(), "R-control"):
            for w in item.withdrawn:
                self.assertEqual((w.required, w.permitted), ((), ()), (item.item_id, item.variant))

    def test_an_uncertain_pair_that_then_dies_is_permitted_not_required(self):
        stream = hand_stream(
            chain("A", "B", "C"), chain("A", "X", "C"), events.ask("A", "C"),
            events.negation("B", "C"), events.retract("X", "C"),
        )
        first, second = replay(stream, False).withdrawn
        self.assertEqual((first.required, first.permitted), ((), (key("A", "C"),)))
        self.assertEqual((second.required, second.permitted), ((), (key("A", "C"),)))
        self.assertEqual(final_state(stream).uncertain, frozenset())

    def test_a_denial_of_a_held_conclusion_is_required_withdrawn(self):
        """F(a,b) F(b,c) A(a,c) N(a,c): the derived record is contradicted and
        falls, though (a,c) was never a clean edge."""
        stream = hand_stream(chain("a", "b", "c"), events.ask("a", "c"), events.negation("a", "c"))
        (w,) = replay(stream, False).withdrawn
        self.assertEqual(w.required, (key("a", "c"),))
        self.assertEqual(w.permitted, (key("a", "c"),))
        self.assertEqual(final_state(stream).held, frozenset())

    def test_withdrawn_ages_out(self):
        """A(c0,c3) R(L) F(L) R(L) N(d0,d1): a conclusion withdrawn once is
        untracked until asked YES again, so a later retract of the revived
        link, or an unrelated denial, withdraws nothing."""
        stream = hand_stream(
            chain("c0", "c1", "c2", "c3"), events.fact("d0", "d1"), events.ask("c0", "c3"),
            events.retract("c1", "c2"), events.fact("c1", "c2"), events.retract("c1", "c2"), events.negation("d0", "d1"),
        )
        first, second, denial = replay(stream, False).withdrawn
        self.assertEqual((first.required, first.permitted), ((key("c0", "c3"),), (key("c0", "c3"),)))
        self.assertEqual((second.required, second.permitted), ((), ()))
        self.assertEqual((denial.required, denial.permitted), ((), ()))
        self.assertEqual(final_state(stream).held, frozenset())

    def test_a_yes_ask_holds_the_pair_again(self):
        stream = hand_stream(
            chain("A", "B", "C"), events.ask("A", "C"), events.retract("B", "C"), events.fact("B", "C"),
            events.ask("A", "C"), events.retract("B", "C"),
        )
        first, second = replay(stream, False).withdrawn
        self.assertEqual(first.required, (key("A", "C"),))
        self.assertEqual(second.required, (key("A", "C"),))

    def test_a_non_yes_ask_untracks_the_pair(self):
        stream = hand_stream(
            chain("A", "B", "C"), events.ask("A", "C"), events.negation("B", "C"),
            events.ask("A", "C"), events.retract("A", "B"),
        )
        result = replay(stream, False)
        self.assertEqual([x.verdict for x in result.expectations], [Verdict.YES, Verdict.INADMISSIBLE])
        self.assertEqual((result.withdrawn[1].required, result.withdrawn[1].permitted), ((), ()))

    def test_an_off_path_mutation_permits_nothing(self):
        stream = hand_stream(chain("A", "B", "C"), chain("X", "Y"), events.ask("A", "C"), events.retract("X", "Y"))
        self.assertEqual(replay(stream, False).withdrawn, (WithdrawnExpectation(4),))

    def test_only_yes_asks_can_be_withdrawn(self):
        stream = hand_stream(chain("A", "B"), events.ask("A", "C"), events.retract("A", "B"))
        self.assertEqual(replay(stream, False).withdrawn, (WithdrawnExpectation(2),))

    def test_a_refused_retract_withdraws_nothing(self):
        stream = hand_stream(chain("A", "B", "C"), events.ask("A", "C"), events.retract("A", "C"))
        result = replay(stream, False)
        self.assertEqual(result.refused, (3,))
        self.assertEqual(result.withdrawn, (WithdrawnExpectation(3),))

    def test_every_retract_and_negation_gets_a_record_in_order(self):
        stream = hand_stream(chain("A", "B"), events.negation("P", "Q"), events.retract("A", "B"), events.retract("Z", "Z2"))
        self.assertEqual([w.event_index for w in replay(stream, False).withdrawn], [1, 2, 3])


# ---- difficulty ------------------------------------------------------------

class DifficultyTests(unittest.TestCase):
    def test_defaults_match_the_contract(self):
        d = StreamDifficulty()
        self.assertEqual((d.hops, d.distractors, d.probes_before, d.shadow, d.interleave), (3, 4, 1, True, 2))
        self.assertEqual(d.label(), "h3-d4-p1")

    def test_hops_below_two_is_a_lookup(self):
        with self.assertRaises(RevisionError) as ctx:
            StreamDifficulty(hops=1)
        self.assertEqual(ctx.exception.code, "E-RS-001")

    def test_the_stale_variants_need_a_probe_before(self):
        with self.assertRaises(RevisionError) as ctx:
            StreamDifficulty(probes_before=0)
        self.assertEqual(ctx.exception.code, "E-RS-002")

    def test_negative_counts_are_refused(self):
        for kw in ({"distractors": -1}, {"interleave": -1}):
            with self.assertRaises(RevisionError) as ctx:
                StreamDifficulty(**kw)
            self.assertEqual(ctx.exception.code, "E-RS-003")

    def test_label_suffixes_appear_only_when_non_default(self):
        self.assertEqual(StreamDifficulty(shadow=False).label(), "h3-d4-p1-s0")
        self.assertEqual(StreamDifficulty(interleave=5).label(), "h3-d4-p1-i5")
        self.assertEqual(StreamDifficulty(hops=4, distractors=6, probes_before=2, shadow=False, interleave=0).label(), "h4-d6-p2-s0-i0")

    def test_adding_a_default_knob_does_not_change_an_existing_fingerprint(self):
        """The original knobs are always emitted; a later knob only when set.
        A registration must survive the generator gaining a capability."""
        self.assertEqual(StreamDifficulty().canonical(), {"hops": 3, "distractors": 4, "probes_before": 1})
        self.assertEqual(StreamDifficulty(shadow=False).canonical()["shadow"], False)
        self.assertEqual(StreamDifficulty(interleave=0).canonical()["interleave"], 0)
        stream_set = generate_revision_set(8, 3)
        legacy = dict(stream_set.canonical())
        legacy["difficulty"] = {"hops": 3, "distractors": 4, "probes_before": 1}
        blob = json.dumps(legacy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.assertEqual(stream_set.fingerprint(), hashlib.sha256(blob).hexdigest())


# ---- the generator ---------------------------------------------------------

class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.open = reference(False)
        cls.closed = reference(True)

    def test_generation_is_deterministic_per_seed(self):
        a, b = generate_revision_set(24, 11), generate_revision_set(24, 11)
        self.assertEqual(a.fingerprint(), b.fingerprint())
        self.assertEqual(a, b)
        self.assertNotEqual(a.fingerprint(), generate_revision_set(24, 12).fingerprint())

    def test_fingerprint_changes_when_any_item_changes(self):
        base = generate_revision_set(16, 5)
        items = list(base.items)
        items[7] = replace(items[7], item_id="zz9999")
        renamed = replace(base, items=tuple(items))
        self.assertNotEqual(base.fingerprint(), renamed.fingerprint())
        other = generate_revision_set(16, 6)
        swapped = replace(base, items=base.items[:3] + (other.items[3],) + base.items[4:])
        self.assertNotEqual(base.fingerprint(), swapped.fingerprint())
        self.assertNotEqual(base.fingerprint(), replace(base, name="other").fingerprint())

    def test_fingerprint_moves_when_difficulty_moves(self):
        a = generate_revision_set(16, 5, StreamDifficulty(hops=3))
        b = generate_revision_set(16, 5, StreamDifficulty(hops=4))
        self.assertNotEqual(a.fingerprint(), b.fingerprint())

    def test_every_class_is_balanced_between_diagnostic_and_control_halves(self):
        for n in (8, 12, 20, 40, 44):
            for mechanism, entry in generate_revision_set(n, 1).summary()["classes"].items():
                self.assertEqual(entry["diagnostic"] + entry["control"], entry["items"], (n, mechanism))
                self.assertEqual(entry["diagnostic"], round(entry["items"] / 2), (n, mechanism))
                self.assertLessEqual(abs(entry["diagnostic"] - entry["control"]), 1, (n, mechanism))
                self.assertGreater(entry["diagnostic"], 0)
                self.assertGreater(entry["control"], 0)

    def test_diagnostic_and_control_items_are_shuffled_within_a_class(self):
        roles = [i.role for i in self.open.items if i.mechanism == "R"]
        self.assertNotEqual(roles, sorted(roles))
        self.assertNotEqual(roles, sorted(roles, reverse=True))

    def test_no_verdict_exceeds_the_balance_ceiling_in_any_class(self):
        self.assertEqual(BALANCE_CEILING, 0.60)
        for n in range(8, 61, 4):
            for seed in (1, 2):
                for world in (False, True):
                    summary = generate_revision_set(n, seed, closed_world=world).summary()
                    for mechanism, entry in summary["classes"].items():
                        for verdict, count in entry["verdicts"].items():
                            self.assertLessEqual(count * 100, 60 * entry["probes"], (n, seed, world, mechanism, verdict))

    def test_the_balance_guard_refuses_a_lopsided_class(self):
        stream = hand_stream(chain("A", "B", "C"), events.ask("A", "C"), events.ask("A", "B"), events.ask("B", "C"))
        yes_heavy = [StreamItem.build("n0000", "N", "N-control", False, stream, 2, Verdict.YES)]
        with self.assertRaises(RevisionError) as ctx:
            guard_balance(yes_heavy)
        self.assertEqual(ctx.exception.code, "E-RS-007")
        self.assertIn("class N", str(ctx.exception))
        guard_balance(self.open.items)

    def test_summary_reports_the_split_and_the_verdict_mix_per_class(self):
        summary = self.open.summary()
        self.assertEqual(summary["items"], REFERENCE_N)
        self.assertEqual(set(summary["classes"]), set(CLASSES))
        for entry in summary["classes"].values():
            self.assertEqual(entry["probes"], sum(entry["verdicts"].values()))
            self.assertEqual(entry["items"], sum(entry["variants"].values()))
            self.assertEqual(entry["max_share"], round(max(entry["verdicts"].values()) / entry["probes"], 4))
            self.assertEqual(entry["verdicts"][entry["max_verdict"]], max(entry["verdicts"].values()))
            self.assertLessEqual(entry["max_share"], BALANCE_CEILING)
        self.assertEqual(summary["probes"], sum(len(i.expectations) for i in self.open.items))
        self.assertEqual(summary["ceiling"], BALANCE_CEILING)

    def test_the_ceiling_is_a_parameter_and_a_reported_number(self):
        """The generator judges against the ceiling it was given and the set
        reports the measured share, so the registered number can be set from
        data rather than the variants bent to fit a number."""
        self.assertEqual(generate_revision_set(16, 3, ceiling=0.75).ceiling, 0.75)
        with self.assertRaises(RevisionError) as ctx:
            generate_revision_set(16, 3, ceiling=0.50)
        self.assertEqual(ctx.exception.code, "E-RS-007")
        with self.assertRaises(RevisionError) as ctx:
            generate_revision_set(16, 3, ceiling=0.0)
        self.assertEqual(ctx.exception.code, "E-RS-004")
        # The ceiling gates acceptance; it is not content, so it is not fingerprinted.
        self.assertEqual(generate_revision_set(16, 3, ceiling=0.75).fingerprint(), generate_revision_set(16, 3).fingerprint())
        self.assertNotIn("ceiling", generate_revision_set(16, 3).canonical())

    def test_ground_truth_is_computed_by_the_oracle_never_passed_in(self):
        """The generator path has no verdict or expectation parameter; the
        item recomputes the oracle and refuses to hold anything else."""
        self.assertNotIn("verdict", inspect.signature(generate_revision_set).parameters)
        self.assertNotIn("expectations", inspect.signature(generate_revision_set).parameters)
        self.assertNotIn("expectations", inspect.signature(StreamItem.build).parameters)
        stream = hand_stream(chain("A", "B", "C"), events.ask("A", "C"))
        with self.assertRaises(RevisionError) as ctx:
            StreamItem.build("r0000", "R", "R-control", False, stream, 2, Verdict.NO)
        self.assertEqual(ctx.exception.code, "E-RS-005")
        good = StreamItem.build("r0000", "R", "R-control", False, stream, 2, Verdict.YES)
        tampered = (replace(good.expectations[0], verdict=Verdict.UNKNOWN),)
        with self.assertRaises(RevisionError) as ctx:
            StreamItem("r0000", "R", "R-control", False, good.events, tampered, good.withdrawn, 2, Verdict.UNKNOWN)
        self.assertEqual(ctx.exception.code, "E-RS-005")
        with self.assertRaises(RevisionError) as ctx:
            StreamItem("r0000", "R", "R-control", False, good.events, good.expectations, (WithdrawnExpectation(0),), 2, Verdict.YES)
        self.assertEqual(ctx.exception.code, "E-RS-005")
        for item in self.open.items:
            truth = replay(item.events, item.closed_world)
            self.assertEqual(item.expectations, truth.expectations, item.item_id)
            self.assertEqual(item.withdrawn, truth.withdrawn, item.item_id)

    def test_malformed_items_are_refused_with_the_argument_code(self):
        stream = hand_stream(chain("A", "B", "C"), events.ask("A", "C"))
        for args in (("Z", "R-simple", 2), ("R", "H-bridge", 2), ("R", "R-simple", 0), ("R", "R-simple", 9)):
            mechanism, variant, probe = args
            with self.assertRaises(RevisionError, msg=args) as ctx:
                StreamItem.build("x0000", mechanism, variant, False, stream, probe, Verdict.YES)
            self.assertEqual(ctx.exception.code, "E-RS-004")

    def test_too_few_items_or_bad_classes_are_refused(self):
        for kwargs in ({"n": 7}, {"n": 8, "classes": ("R", "R")}, {"n": 8, "classes": ()}, {"n": 8, "classes": ("R", "Q")}):
            with self.assertRaises(RevisionError, msg=kwargs) as ctx:
                generate_revision_set(seed=1, **kwargs)
            self.assertEqual(ctx.exception.code, "E-RS-004")
        self.assertEqual(len(generate_revision_set(2, 1, classes=("N",))), 2)

    def test_open_and_closed_sets_differ_only_by_unknown_to_no(self):
        self.assertNotEqual(self.open.fingerprint(), self.closed.fingerprint())
        self.assertEqual(len(self.open), len(self.closed))
        for o, c in zip(self.open.items, self.closed.items):
            self.assertEqual(o.events, c.events, o.item_id)
            self.assertEqual([e.canonical() for e in o.events], [e.canonical() for e in c.events])
            self.assertEqual(o.withdrawn, c.withdrawn)
            self.assertEqual((o.item_id, o.mechanism, o.variant, o.designed_probe_index), (c.item_id, c.mechanism, c.variant, c.designed_probe_index))
            self.assertEqual(len(o.expectations), len(c.expectations))
            for x, y in zip(o.expectations, c.expectations):
                self.assertEqual((x.event_index, x.subject, x.obj, x.contested_required), (y.event_index, y.subject, y.obj, y.contested_required))
                self.assertEqual((y.lacunae_required, y.lacunae_admissible), ((), ()))
                if x.verdict is Verdict.UNKNOWN:
                    self.assertIs(y.verdict, Verdict.NO)
                else:
                    self.assertIs(y.verdict, x.verdict)
                    self.assertEqual((x.lacunae_required, x.lacunae_admissible), ((), ()))
        opens = {x.verdict for i in self.open.items for x in i.expectations}
        self.assertIn(Verdict.UNKNOWN, opens)
        self.assertNotIn(Verdict.UNKNOWN, {x.verdict for i in self.closed.items for x in i.expectations})

    def test_route_bound_guard_rejects_items_the_processor_could_not_fairly_see(self):
        dense = hand_stream(
            [events.fact("S", f"M{k}") for k in range(9)], [events.fact(f"M{k}", "T") for k in range(9)],
            events.ask("S", "T"),
        )
        with self.assertRaises(RevisionError) as ctx:
            guard_route_bounds(dense)
        self.assertEqual(ctx.exception.code, "E-RS-006")
        self.assertIn("9 simple route", str(ctx.exception))
        long = hand_stream(chain("A", "B", "C", "D", "E", "F", "G", "H"), events.ask("A", "H"))
        with self.assertRaises(RevisionError) as ctx:
            guard_route_bounds(long)
        self.assertEqual(ctx.exception.code, "E-RS-006")
        self.assertIn("longest 7", str(ctx.exception))
        # exactly at the bounds is fair
        eight = hand_stream(
            [events.fact("S", f"M{k}") for k in range(8)], [events.fact(f"M{k}", "T") for k in range(8)],
            events.ask("S", "T"),
        )
        self.assertEqual(guard_route_bounds(eight)[0].routes, 8)
        six = hand_stream(chain("A", "B", "C", "D", "E", "F", "G"), events.ask("A", "G"))
        self.assertEqual(guard_route_bounds(six)[0].longest, 6)
        for item in self.open.items:
            for bound in guard_route_bounds(item.events):
                self.assertLessEqual(bound.routes, ROUTE_LIMIT, item.item_id)
                self.assertLessEqual(bound.longest, MAX_HOPS, item.item_id)

    def test_the_route_guard_counts_held_derivations_and_walks_disputed_links(self):
        """What `^8` walks: positive records, including a link under dispute
        and a conclusion the organism holds from an earlier YES."""
        held = hand_stream(chain("A", "B", "C"), events.ask("A", "C"), events.ask("A", "C"))
        first, second = guard_route_bounds(held)
        self.assertEqual((first.routes, second.routes), (1, 2))
        disputed = hand_stream(chain("A", "B", "C"), events.negation("B", "C"), events.ask("A", "C"))
        self.assertEqual(guard_route_bounds(disputed)[0].routes, 1)
        shadow_of_denied = hand_stream(chain("A", "B"), events.associate("B", "C"), events.negation("B", "C"), events.ask("A", "C"))
        self.assertEqual(guard_route_bounds(shadow_of_denied)[0].routes, 1)
        denial_only = hand_stream(chain("A", "B"), events.negation("B", "C"), events.ask("A", "C"))
        self.assertEqual(guard_route_bounds(denial_only)[0].routes, 0)

    def test_route_bound_constants_match_the_banks_defaults(self):
        params = inspect.signature(HypothesisBank.surface).parameters
        self.assertEqual(params["limit"].default, ROUTE_LIMIT)
        self.assertEqual(params["max_hops"].default, MAX_HOPS)

    def test_a_chain_longer_than_the_bank_walks_is_refused_as_unfair(self):
        with self.assertRaises(RevisionError) as ctx:
            generate_revision_set(8, 1, StreamDifficulty(hops=MAX_HOPS + 1))
        self.assertEqual(ctx.exception.code, "E-RS-006")

    def test_every_variant_of_every_class_appears_at_n_sufficiently_large(self):
        seen = {i.variant for i in self.open.items}
        for mechanism, (diagnostic, control) in VARIANTS.items():
            for variant in diagnostic + control:
                self.assertIn(variant, seen, variant)
                self.assertTrue(variant.startswith(mechanism + "-"))
        self.assertEqual(
            VARIANTS,
            {
                "R": (("R-simple", "R-stale", "R-deep"), ("R-control", "R-revive")),
                "H": (("H-bridge", "H-refute"), ("H-control", "H-confirm")),
                "C": (("C-blocked", "C-stale"), ("C-bypassed", "C-unrelated")),
                "N": (("N-gap",), ("N-control", "N-actionable")),
            },
        )

    def test_the_designed_verdict_is_asserted_on_every_probe_of_every_item(self):
        for stream_set in (self.open, self.closed):
            for item in stream_set.items:
                asks = [k for k, e in enumerate(item.events) if e.kind is EventKind.ASK]
                self.assertEqual([x.event_index for x in item.expectations], asks, item.item_id)
                self.assertIn(item.designed_probe_index, asks)
                self.assertIs(designed(item).verdict, item.designed_verdict, item.item_id)
                self.assertEqual(replay(item.events, item.closed_world).refused, (), item.item_id)
                for x in item.expectations:
                    with self.assertRaises(RevisionError, msg=item.item_id) as ctx:
                        StreamItem(
                            item.item_id, item.mechanism, item.variant, item.closed_world, item.events,
                            tuple(replace(y, verdict=Verdict.INADMISSIBLE if y.verdict is not Verdict.INADMISSIBLE else Verdict.YES) if y is x else y for y in item.expectations),
                            item.withdrawn, item.designed_probe_index, item.designed_verdict,
                        )
                    self.assertEqual(ctx.exception.code, "E-RS-005")

    def test_each_variant_has_the_designed_verdict_the_contract_lists(self):
        expected = {
            "R-simple": Verdict.UNKNOWN, "R-stale": Verdict.UNKNOWN, "R-deep": Verdict.UNKNOWN,
            "R-control": Verdict.YES, "R-revive": Verdict.YES,
            "H-bridge": Verdict.UNKNOWN, "H-refute": Verdict.UNKNOWN, "H-control": Verdict.YES, "H-confirm": Verdict.YES,
            "C-blocked": Verdict.INADMISSIBLE, "C-stale": Verdict.INADMISSIBLE, "C-bypassed": Verdict.YES, "C-unrelated": Verdict.YES,
            "N-gap": Verdict.UNKNOWN, "N-control": Verdict.YES, "N-actionable": Verdict.YES,
        }
        for item in self.open.items:
            self.assertIs(item.designed_verdict, expected[item.variant], item.item_id)
            self.assertEqual(item.role, "diagnostic" if item.variant in VARIANTS[item.mechanism][0] else "control")
        for item in self.closed.items:
            want = expected[item.variant]
            self.assertIs(item.designed_verdict, Verdict.NO if want is Verdict.UNKNOWN else want, item.item_id)

    def test_the_stale_variants_hold_the_conclusion_probes_before_times(self):
        for p in (1, 2):
            diff = StreamDifficulty(probes_before=p)
            for variant in ("R-stale", "C-stale"):
                mechanism = variant[0]
                # Draw single-class sets; the balance ceiling is judged per
                # class and a p=2 set is YES-heavy there, so build items via
                # the oracle directly rather than through a whole set.
                try:
                    items = by_variant(generate_revision_set(8, 2, diff, classes=(mechanism,)), variant)
                except RevisionError as exc:
                    self.assertEqual(exc.code, "E-RS-007")
                    self.assertEqual(p, 2)
                    continue
                for item in items:
                    verdicts = [x.verdict for x in item.expectations]
                    self.assertEqual(verdicts[:p], [Verdict.YES] * p, item.item_id)
                    self.assertEqual(len(verdicts), p + 1)

    def test_r_deep_holds_an_intermediate_and_loses_both_on_retract(self):
        for item in by_variant(generate_revision_set(48, 4), "R-deep"):
            verdicts = [x.verdict for x in item.expectations]
            self.assertEqual(verdicts, [Verdict.YES, Verdict.YES, Verdict.UNKNOWN, Verdict.UNKNOWN], item.item_id)
            inter, main = item.expectations[0], item.expectations[1]
            self.assertEqual(inter.subject, main.subject)
            self.assertNotEqual(inter.obj, main.obj)
            self.assertNotIn((inter.subject, inter.obj), {e.pair for e in item.events if e.kind is EventKind.FACT}, "the held intermediate must be a derivation, not a given")

    def test_r_revive_abstains_between_retract_and_re_assert(self):
        for item in by_variant(self.open, "R-revive"):
            self.assertEqual([x.verdict for x in item.expectations], [Verdict.UNKNOWN, Verdict.YES], item.item_id)

    def test_interleave_facts_are_unrelated_to_everything_else(self):
        for item in self.open.items:
            mentions: dict[str, int] = {}
            for e in item.events:
                for node in e.pair:
                    mentions[node] = mentions.get(node, 0) + 1
            lonely = [e for e in item.events if e.kind is EventKind.FACT and mentions[e.subject] == 1 and mentions[e.obj] == 1]
            self.assertGreaterEqual(len(lonely), 2, item.item_id)
        plain = generate_revision_set(8, 9, StreamDifficulty(interleave=0))
        self.assertLess(sum(len(i.events) for i in plain.items), sum(len(i.events) for i in generate_revision_set(8, 9).items))

    def test_distractors_never_create_or_shorten_a_queried_route(self):
        """A spare node is never reachable from the chain, so an off-path edge
        cannot alter any probe the item asks about: strip every fact whose
        subject the designed probe cannot reach and every verdict stands."""
        busy = generate_revision_set(16, 21, StreamDifficulty(distractors=8))
        for item in busy.items:
            x = designed(item)
            given = {e.pair for e in item.events if e.kind is not EventKind.ASK and e.relation == events.DEFAULT_RELATION}
            on_chain = reachable(given, x.subject) | {x.subject}
            stripped = tuple(e for e in item.events if not (e.kind is EventKind.FACT and e.relation == events.DEFAULT_RELATION and e.subject not in on_chain))
            self.assertLess(len(stripped), len(item.events), item.item_id)
            for world in (False, True):
                full = [y.verdict for y in replay(item.events, world).expectations]
                thin = [y.verdict for y in replay(stripped, world).expectations]
                self.assertEqual(full, thin, (item.item_id, item.variant, world))

    def test_the_shadow_is_an_associative_twin_of_the_designated_link(self):
        """The shadow sits under L: the chain's given facts reach its source
        from the designed probe's subject and reach the designed object from
        its target. In N-gap L is never given, so the shadow is the gap."""
        for item in self.open.items:
            shadow = only(item, EventKind.FACT, events.ASSOCIATIVE_RELATION)
            x = designed(item)
            facts = {e.pair for e in item.events if e.kind is EventKind.FACT and e.relation == events.DEFAULT_RELATION}
            self.assertIn(shadow.subject, reachable(facts, x.subject) | {x.subject}, (item.item_id, item.variant))
            self.assertIn(x.obj, reachable(facts, shadow.obj) | {shadow.obj}, (item.item_id, item.variant))
            if item.variant == "N-gap":
                self.assertNotIn(shadow.pair, facts)
            elif not item.variant.startswith("H-") or item.variant in ("H-control", "H-confirm"):
                self.assertIn(shadow.pair, facts, (item.item_id, item.variant))
        for item in generate_revision_set(8, 2, StreamDifficulty(shadow=False)).items:
            self.assertFalse([e for e in item.events if e.relation == events.ASSOCIATIVE_RELATION])

    def test_entity_names_are_opaque(self):
        for item in self.open.items:
            for e in item.events:
                self.assertRegex(e.subject, r"^[A-Z]{2}$")
                self.assertRegex(e.obj, r"^[A-Z]{2}$")

    def test_tokens_are_drawn_per_item(self):
        """Sharing a pool across items would let item k's leftovers create
        routes in item k+j once the organism is shared; it never is, but the
        streams must not depend on that."""
        first, second = self.open.items[0], self.open.items[1]
        a = {n for e in first.events for n in e.pair}
        b = {n for e in second.events for n in e.pair}
        self.assertNotEqual(a, b)

    def test_item_ids_are_per_class_and_dense(self):
        for mechanism in CLASSES:
            ids = sorted(i.item_id for i in self.open.items if i.mechanism == mechanism)
            self.assertEqual(ids, [f"{mechanism.lower()}{k:04d}" for k in range(len(ids))])


class PurityTests(unittest.TestCase):
    ALLOWED = {"__future__", "dataclasses", "enum", "hashlib", "json", "random", "typing", "itertools", "events"}

    def test_the_oracle_imports_no_cas_organ(self):
        """The oracle must have no CAS in it: an oracle sharing machinery with
        the organism would score agreement with itself (contract section 0)."""
        source = (PACKAGE / "revision.py").read_text()
        tree = ast.parse(source)
        imported: set[str] = set()
        plain: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
                plain |= names
                imported |= names
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertEqual(imported, self.ALLOWED, imported ^ self.ALLOWED)
        self.assertIn("events", plain, "the shared Event type must come from events.py")
        for banned in ("organism", "runtime", "banks", "workspace", "foundations", "encoder", "repl", "demo",
                       "ccb_r1", "tasksets", "calibration", "cjt_sim", "cmb", "cdab", "rpm", "sys", "os", "string"):
            self.assertNotIn(f"import {banned}", source, banned)
            self.assertNotIn(f"from {banned} ", source, banned)
        self.assertNotIn("__import__", source)
        self.assertNotIn("importlib", source)
        self.assertNotIn("open(", source)

    def test_the_module_states_what_the_family_may_claim(self):
        doc = ast.get_docstring(ast.parse((PACKAGE / "revision.py").read_text())) or ""
        for phrase in ("convergence contract", "diagnostic suite", "correct solver", "not a necessity proof"):
            self.assertIn(phrase, doc, phrase)


class ReferenceFingerprintTests(unittest.TestCase):
    """Pre-registered. A run scored against a set with another fingerprint is void."""

    OPEN = "e8d18e66139859c06fa1656ed9204ceb895504c6023187408aa3637570aae341"
    CLOSED = "ccc1f5c80d22b9cc600921bbfc24954f5af5e00647b6d963e5e45247f4639bc3"

    def test_reference_fingerprints_are_stable(self):
        open_fp = reference(False).fingerprint()
        closed_fp = reference(True).fingerprint()
        self.assertEqual(
            open_fp, self.OPEN,
            f"open-world reference fingerprint moved: n={REFERENCE_N} seed={REFERENCE_SEED} "
            f"{StreamDifficulty().label()} open={open_fp} closed={closed_fp}",
        )
        self.assertEqual(
            closed_fp, self.CLOSED,
            f"closed-world reference fingerprint moved: n={REFERENCE_N} seed={REFERENCE_SEED} "
            f"{StreamDifficulty().label()} open={open_fp} closed={closed_fp}",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
