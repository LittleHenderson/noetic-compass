"""Session streams — the multi-session dataset obeys the oracle, the split map and the plan.

`docs/working/helm_eval_plan_draft_2026_10_06.md` §3.2–3.3, §4 and §8 fix
what `scripts/cas_rpu/sessions.py` must emit; `session_types.py` fixes the
shape. These tests pin: determinism and a fingerprint that moves with the
seeds; paired worlds byte-identical in events and boundaries; the split map
(session 1 carries no cross-session designed probe, every later session
carries at least one); designed verdicts that agree with the whole-stream
oracle in both worlds; the sixteen reused variants unchanged; tokens disjoint
across episodes; E-RS-010 and the route bounds over the whole stream; the
§8.3 table exactly; the untaught twins; the balance ceiling; the pinned
`generate_revision_set` fingerprints untouched; and that the walk-first
Organism agrees with the oracle on every probe of seeds 0..2 in both worlds.

`LessonSetTests` pins item class L (contract §13, `lessons=True`): the
`lessons=False` output byte-identical to the registered fingerprints; the
designed verdict sequence of every L variant in both worlds, L-edge's refused
retract and L-retract's withdrawn requirement; foreign relations unique per
stream and never reserved; the untaught twins GAP on every L designed probe;
the balance ceiling with L; and Organism agreement on every probe, withdrawal
and refusal of seeds 0..2, both worlds, primaries and twins.
"""

from __future__ import annotations

import random
import sys
import unittest
from dataclasses import replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / "scripts" / "cas_rpu"
sys.path.insert(0, str(PACKAGE))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

import events  # noqa: E402
from events import LESSON_RELATION, RESERVED_RELATIONS, EventKind, is_foreign  # noqa: E402
from organism import Organism  # noqa: E402
from revision import (  # noqa: E402
    BALANCE_CEILING,
    VARIANTS,
    RevisionError,
    StreamDifficulty,
    Verdict,
    _Design,
    _draw_item,
    generate_revision_set,
    guard_hypotheses_fresh,
    guard_route_bounds,
    pair_key,
    replay,
)
from session_types import EpisodeSpan, SeedStream, SessionError, SessionSet  # noqa: E402
from sessions import (  # noqa: E402
    CATALOG,
    CROSS_VARIANTS,
    EXISTING_VARIANTS,
    FOREIGN_RELATIONS,
    LESSON_VARIANTS,
    _draw_seed,
    _nodes,
    balance_report,
    generate_session_set,
    probe_owners,
)

#: Pinned in test_cas_rpu_revision.py (PR 248); copied so a regression here is caught here too.
REVISION_OPEN = "e8d18e66139859c06fa1656ed9204ceb895504c6023187408aa3637570aae341"
REVISION_CLOSED = "ccc1f5c80d22b9cc600921bbfc24954f5af5e00647b6d963e5e45247f4639bc3"

SEEDS = (0, 1, 2)


def gap(closed: bool) -> Verdict:
    return _Design.GAP.in_world(closed)


def components(stream: SeedStream) -> dict[str, str]:
    """node -> component root over every event of the stream (union-find over
    `sessions._nodes`: tokens, plus a `~r` node per foreign relation)."""
    parent: dict[str, str] = {}

    def find(t: str) -> str:
        parent.setdefault(t, t)
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t

    for e in stream.events:
        nodes = _nodes(e)
        for node in nodes:
            parent[find(node)] = find(nodes[0])
    return {t: find(t) for t in list(parent)}


def own_events(stream: SeedStream, span: EpisodeSpan) -> list[int]:
    """Indices of the events in `span` whose tokens share the designed probe's
    component -- the chain-connected part of the episode."""
    comp = components(stream)
    root = comp[stream.events[span.designed_probe_index].subject]
    return [j for j in range(span.start, span.end) if comp[_nodes(stream.events[j])[0]] == root]


def nominal_offsets(variant: str) -> tuple[int, ...]:
    return (CROSS_VARIANTS | LESSON_VARIANTS)[variant][3]


def span_of(stream: SeedStream, variant: str) -> EpisodeSpan:
    found = [ep for ep in stream.episodes if ep.variant == variant]
    assert len(found) == 1, (variant, found)
    return found[0]


def probes_of(stream: SeedStream, span: EpisodeSpan) -> list:
    k = list(stream.episodes).index(span)
    owners = probe_owners(stream)
    return [x for x in stream.expectations if owners[x.event_index] == k]


class SessionSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.open = generate_session_set(SEEDS)
        cls.closed = generate_session_set(SEEDS, closed_world=True)

    # -- shape and catalog -------------------------------------------------------

    def test_shape_and_catalog(self):
        self.assertIsInstance(self.open, SessionSet)
        self.assertEqual((self.open.kind, self.open.sessions, self.open.seed), ("session_streams", 5, 0))
        self.assertEqual(len(CATALOG), 27)
        self.assertEqual(set(EXISTING_VARIANTS), {v for m in VARIANTS for role in VARIANTS[m] for v in role})
        for stream in self.open.streams:
            self.assertEqual(sorted(ep.variant for ep in stream.episodes), sorted(CATALOG))
            self.assertEqual(stream.sessions, 5)
            for ep in stream.episodes:
                if ep.variant in CROSS_VARIANTS:
                    mechanism, role, _base, _offsets = CROSS_VARIANTS[ep.variant]
                    self.assertTrue(ep.cross_session, ep)
                else:
                    mechanism = next(m for m in VARIANTS if ep.variant in VARIANTS[m][0] + VARIANTS[m][1])
                    role = "diagnostic" if ep.variant in VARIANTS[mechanism][0] else "control"
                    self.assertFalse(ep.cross_session, ep)
                self.assertEqual((ep.mechanism, ep.role), (mechanism, role), ep)
                self.assertIs(stream.events[ep.designed_probe_index].kind, EventKind.ASK)
                self.assertTrue(ep.start <= ep.designed_probe_index < ep.end)
        self.assertEqual(CROSS_VARIANTS["C-cross"][0], "C")
        self.assertEqual(CROSS_VARIANTS["N-late"][0], "N")
        self.assertEqual({v for v, spec in CROSS_VARIANTS.items() if spec[1] == "control"}, {"X-hold", "T-exact"})

    def test_summary_counts(self):
        summary = self.open.summary()
        self.assertEqual((summary["streams"], summary["twins"], summary["sessions"]), (3, 3, 5))
        self.assertEqual(summary["cross_session_episodes"], 3 * len(CROSS_VARIANTS))
        self.assertEqual(set(summary["variants"]), set(CATALOG))
        self.assertEqual(summary["probes"], sum(len(s.expectations) for s in self.open.streams))

    # -- determinism and fingerprint ---------------------------------------------------

    def test_generation_is_deterministic_and_the_fingerprint_moves_with_the_seeds(self):
        again = generate_session_set(SEEDS)
        self.assertEqual(again, self.open)
        self.assertEqual(again.fingerprint(), self.open.fingerprint())
        self.assertNotEqual(generate_session_set((0, 1, 3)).fingerprint(), self.open.fingerprint())
        self.assertNotEqual(generate_session_set((0, 1)).fingerprint(), self.open.fingerprint())
        self.assertNotEqual(self.open.fingerprint(), self.closed.fingerprint())

    def test_twins_are_inside_the_fingerprint(self):
        without = generate_session_set(SEEDS, twins=False)
        self.assertEqual(without.twins, ())
        self.assertNotEqual(without.fingerprint(), self.open.fingerprint())

    # -- paired worlds -----------------------------------------------------------------

    def test_paired_worlds_are_byte_identical_in_events_and_boundaries(self):
        for o, c in zip(self.open.streams + self.open.twins, self.closed.streams + self.closed.twins):
            self.assertEqual(o.events, c.events)
            self.assertEqual(o.boundaries, c.boundaries)
            self.assertEqual(o.refused, c.refused)
            self.assertEqual([ep.canonical() | {"designed_verdict": None} for ep in o.episodes],
                             [ep.canonical() | {"designed_verdict": None} for ep in c.episodes])
            for xo, xc in zip(o.expectations, c.expectations):
                self.assertEqual((xo.event_index, xo.subject, xo.obj), (xc.event_index, xc.subject, xc.obj))
                if xo.verdict is Verdict.UNKNOWN:
                    self.assertIs(xc.verdict, Verdict.NO)
                    self.assertEqual(xc.lacunae_required, ())
                else:
                    self.assertEqual(xo, xc)
            for eo, ec in zip(o.episodes, c.episodes):
                if eo.designed_verdict == "UNKNOWN":
                    self.assertEqual(ec.designed_verdict, "NO")
                else:
                    self.assertEqual(eo.designed_verdict, ec.designed_verdict)

    # -- the split map -------------------------------------------------------------------

    def test_session_one_has_no_cross_session_designed_probe_and_every_later_session_has_one(self):
        for stream in self.open.streams + self.open.twins:
            covered = [stream.session_of(ep.designed_probe_index) for ep in stream.episodes if ep.cross_session]
            self.assertNotIn(0, covered)
            self.assertTrue(set(range(1, stream.sessions)) <= set(covered), (stream.seed, sorted(covered)))
            for ep in stream.episodes:
                sessions_touched = {stream.session_of(j) for j in own_events(stream, ep)}
                self.assertEqual(len(sessions_touched) > 1, ep.cross_session, ep)
                if ep.cross_session:
                    self.assertGreater(stream.session_of(ep.designed_probe_index), min(sessions_touched), ep)
                    # five sessions hold every layout uncompressed: one session per nominal offset
                    self.assertEqual(len(sessions_touched), len(set(nominal_offsets(ep.variant))), ep)

    def test_x_delay_waits_three_sessions_with_only_unrelated_episodes_between(self):
        for stream in self.open.streams:
            ep = span_of(stream, "X-delay")
            own = own_events(stream, ep)
            taught = stream.session_of(own[0])
            probed = stream.session_of(ep.designed_probe_index)
            self.assertEqual(probed, min(taught + 3, stream.sessions - 1))
            # the episode's own events form exactly two contiguous blocks: teach, probe
            runs = 1 + sum(1 for a, b in zip(own, own[1:]) if b != a + 1)
            self.assertEqual(runs, 2)
            # nothing of the episode sits in the sessions between
            self.assertFalse({stream.session_of(j) for j in own} & set(range(taught + 1, probed)))

    def test_a_session_without_a_probe_is_refused(self):
        stream = self.open.streams[0]
        j = next(i for i, e in enumerate(stream.events) if i > 0 and e.kind is not EventKind.ASK)
        with self.assertRaises(SessionError) as ctx:
            replace(stream, boundaries=(j, j + 1))
        self.assertEqual(ctx.exception.code, "E-SS-001")

    def test_session_counts(self):
        two = generate_session_set((0,), sessions=2)
        self.assertEqual(two.streams[0].sessions, 2)
        nine = generate_session_set((0,), sessions=9)
        self.assertEqual(nine.streams[0].sessions, 9)
        twelve = generate_session_set((0,), sessions=12)
        self.assertEqual(twelve.streams[0].sessions, 12)
        with self.assertRaises(SessionError) as ctx:
            generate_session_set((0,), sessions=13)
        self.assertEqual(ctx.exception.code, "E-SS-002")
        for bad in ({"sessions": 1}, {"seeds": ()}, {"seeds": (1, 1)}, {"ceiling": 0.0}):
            with self.assertRaises(RevisionError) as ctx:
                generate_session_set(**({"seeds": (0,)} | bad))
            self.assertEqual(ctx.exception.code, "E-RS-004")

    # -- the oracle over the whole stream ---------------------------------------------------

    def test_designed_verdicts_agree_with_the_whole_stream_oracle_in_both_worlds(self):
        for sset, closed in ((self.open, False), (self.closed, True)):
            for stream in sset.streams + sset.twins:
                truth = replay(stream.events, closed)
                self.assertEqual(truth.expectations, stream.expectations)
                self.assertEqual(truth.withdrawn, stream.withdrawn)
                self.assertEqual(truth.refused, stream.refused)
                by_index = {x.event_index: x.verdict for x in truth.expectations}
                for ep in stream.episodes:
                    self.assertEqual(by_index[ep.designed_probe_index].value, ep.designed_verdict, ep)

    def test_the_sixteen_reused_variants_are_the_draw_item_layouts(self):
        """Verdict sequence and length equal a standalone `_draw_item` draw, and the
        episode's own replay equals the whole-stream oracle on its probes."""
        diff = StreamDifficulty()
        for sset, closed in ((self.open, False), (self.closed, True)):
            for stream in sset.streams:
                for variant in EXISTING_VARIANTS:
                    ep = span_of(stream, variant)
                    standalone = _draw_item(random.Random(7), diff, ep.mechanism, variant)
                    self.assertEqual(ep.end - ep.start, len(standalone.stream), variant)
                    want = [standalone.designed[i].in_world(closed) for i in sorted(standalone.designed)]
                    got = [x.verdict for x in probes_of(stream, ep)]
                    self.assertEqual(got, want, variant)
                    self.assertEqual(standalone.designed[standalone.designed_probe].in_world(closed).value, ep.designed_verdict)
                    local = replay(stream.events[ep.start:ep.end], closed)
                    self.assertEqual([x.verdict for x in local.expectations], got, variant)
                    self.assertEqual([x.event_index + ep.start for x in local.expectations],
                                     [x.event_index for x in probes_of(stream, ep)], variant)

    def test_tokens_are_disjoint_across_episodes_and_drawn_without_replacement(self):
        laid, _truths = _draw_seed(random.Random(0), StreamDifficulty(), 5, 0)
        seen: dict[str, int] = {}
        for i, ep in enumerate(laid.episodes):
            for token in ep.tokens():
                self.assertNotIn(token, seen, f"{token} in episodes {seen.get(token)} and {i}")
                seen[token] = i
        self.assertEqual(len(seen), len({t for e in laid.events for t in (e.subject, e.obj)}))
        # every probe is attributed by tokens exactly as the layout says
        stream = self.open.streams[0]
        owners = probe_owners(stream)
        self.assertEqual(sorted(owners), [x.event_index for x in stream.expectations])
        for x in stream.expectations:
            ep = stream.episodes[owners[x.event_index]]
            self.assertTrue(ep.start <= x.event_index < ep.end)

    def test_guards_hold_over_the_whole_stream(self):
        for stream in self.open.streams + self.open.twins:
            guard_hypotheses_fresh(stream.events)
            bounds = guard_route_bounds(stream.events)
            self.assertEqual(len(bounds), len(stream.expectations))

    # -- the new variants ------------------------------------------------------------------

    def test_g_probe_matches_the_frozen_table_of_section_8_3(self):
        for sset, closed in ((self.open, False), (self.closed, True)):
            for stream in sset.streams:
                ep = span_of(stream, "G-probe")
                own = own_events(stream, ep)
                evs = {j: stream.events[j] for j in own}
                a, d = stream.events[ep.designed_probe_index].pair
                hyp = next(evs[j] for j in own if evs[j].kind is EventKind.HYPOTHESIS)
                b, c = hyp.pair
                self.assertEqual({e.pair for e in evs.values() if e.kind is EventKind.FACT and e.relation == "leads_to"
                                  and e.pair[0] in (a, b, c, d) and e.pair[1] in (a, b, c, d)}, {(a, b), (c, d), (b, c)})
                self.assertIn(events.associate(b, c), evs.values())
                steps = [x for x in probes_of(stream, ep) if x.subject == a and x.obj == d]
                self.assertEqual(len(steps), 6)
                want = [gap(closed), Verdict.NO, Verdict.NO, Verdict.INADMISSIBLE, Verdict.NO, Verdict.NO]
                self.assertEqual([x.verdict for x in steps], want)
                self.assertEqual(steps[3].event_index, ep.designed_probe_index)
                self.assertEqual(steps[3].contested_required, (pair_key((a, d)),))
                if not closed:
                    self.assertEqual(steps[0].lacunae_required, (pair_key((b, c)),))
                    self.assertEqual(set(steps[0].lacunae_admissible), {pair_key((a, d)), pair_key((b, c))})
                # sessions: 1-2 in k, 3-5 in k+1, 6 in k+2
                k = stream.session_of(steps[0].event_index)
                self.assertEqual([stream.session_of(x.event_index) - k for x in steps], [0, 0, 1, 1, 1, 2])
                # the mutations, in order, and their withdrawn records
                neg = next(j for j in own if evs[j] == events.negation(a, d))
                retracts = [j for j in own if evs[j] == events.retract(b, c)]
                promote = next(j for j in own if evs[j] == events.fact(b, c))
                self.assertTrue(steps[0].event_index < neg < steps[1].event_index)
                self.assertTrue(steps[2].event_index < promote < steps[3].event_index < retracts[0] < steps[4].event_index)
                self.assertTrue(steps[5].event_index < retracts[1])
                self.assertNotIn(neg, stream.refused)
                self.assertNotIn(retracts[0], stream.refused)
                self.assertIn(retracts[1], stream.refused)
                withdrawn = {w.event_index: w for w in stream.withdrawn}
                self.assertEqual((withdrawn[neg].required, withdrawn[neg].permitted), ((), ()))
                # balancing probes: ASK(c,d) -> YES in session k (plus the two ceiling probes)
                extra = [x for x in probes_of(stream, ep) if (x.subject, x.obj) != (a, d)]
                self.assertEqual([(x.subject, x.obj, x.verdict) for x in extra],
                                 [(c, d, Verdict.YES), (a, b, Verdict.YES), (c, d, Verdict.YES)])
                self.assertEqual([stream.session_of(x.event_index) - k for x in extra], [0, 0, 2])

    def test_d_restate_duplicate_fact_then_one_retract_is_a_gap_and_the_second_retract_is_refused(self):
        for sset, closed in ((self.open, False), (self.closed, True)):
            for stream in sset.streams:
                ep = span_of(stream, "D-restate")
                own = own_events(stream, ep)
                retracts = [j for j in own if stream.events[j].kind is EventKind.RETRACT]
                self.assertEqual(len(retracts), 2)
                link = stream.events[retracts[0]].pair
                self.assertEqual(stream.events[retracts[1]].pair, link)
                facts = [j for j in own if stream.events[j] == events.fact(*link)]
                self.assertEqual(len(facts), 2)
                self.assertTrue(stream.session_of(facts[1]) < stream.session_of(retracts[0]))
                self.assertNotIn(retracts[0], stream.refused)
                self.assertIn(retracts[1], stream.refused)
                probes = probes_of(stream, ep)
                self.assertEqual([x.verdict for x in probes], [Verdict.YES, gap(closed), Verdict.YES, gap(closed)])
                self.assertEqual(probes[1].event_index, ep.designed_probe_index)
                self.assertTrue(retracts[0] < ep.designed_probe_index < retracts[1])

    def test_c_cross_names_the_contested_link_and_the_retract_of_a_contested_pair_is_accepted(self):
        for sset, closed in ((self.open, False), (self.closed, True)):
            for stream in sset.streams:
                ep = span_of(stream, "C-cross")
                own = own_events(stream, ep)
                neg = next(j for j in own if stream.events[j].kind is EventKind.NEGATION)
                ret = next(j for j in own if stream.events[j].kind is EventKind.RETRACT)
                link = stream.events[neg].pair
                self.assertEqual(stream.events[ret].pair, link)
                self.assertNotIn(ret, stream.refused)
                probes = probes_of(stream, ep)
                self.assertEqual([x.verdict for x in probes],
                                 [Verdict.YES, Verdict.INADMISSIBLE, Verdict.INADMISSIBLE, gap(closed)])
                self.assertEqual(probes[1].event_index, ep.designed_probe_index)
                self.assertEqual(probes[1].contested_required, (pair_key(link),))
                sessions = [stream.session_of(x.event_index) for x in probes]
                self.assertEqual(sessions[1] - sessions[0], 1)
                self.assertEqual(sessions[2] - sessions[1], 1)

    def test_every_cross_session_variant_has_its_designed_verdict_sequence(self):
        want = {
            "X-delay": ["YES", "GAP"], "X-revive": ["YES", "GAP", "YES", "YES"],
            "X-deep": ["YES", "YES", "GAP", "GAP", "GAP", "GAP"], "X-correct": ["YES", "YES", "YES", "GAP"],
            "X-hold": ["YES", "YES", "GAP"], "D-restate": ["YES", "GAP", "YES", "GAP"],
            "C-cross": ["YES", "INADMISSIBLE", "INADMISSIBLE", "GAP"], "N-late": ["GAP", "YES", "GAP", "YES"],
            "T-compose": ["YES", "GAP"], "T-exact": ["YES", "GAP", "YES"],
            "G-probe": ["GAP", "NO", "YES", "YES", "NO", "INADMISSIBLE", "NO", "NO", "YES"],
        }
        designed_position = {
            "X-delay": 0, "X-revive": 3, "X-deep": 2, "X-correct": 1, "X-hold": 1, "D-restate": 1,
            "C-cross": 1, "N-late": 1, "T-compose": 0, "T-exact": 2, "G-probe": 5,
        }
        for sset, closed in ((self.open, False), (self.closed, True)):
            for stream in sset.streams:
                for variant, seq in want.items():
                    ep = span_of(stream, variant)
                    probes = probes_of(stream, ep)
                    self.assertEqual([x.verdict for x in probes], [_Design(v).in_world(closed) for v in seq], variant)
                    self.assertEqual(probes[designed_position[variant]].event_index, ep.designed_probe_index, variant)

    def test_t_compose_asks_a_pair_never_asked_before_and_n_late_turns_a_gap_into_a_yes(self):
        for stream in self.open.streams:
            ep = span_of(stream, "T-compose")
            probes = probes_of(stream, ep)
            a, e = probes[0].subject, probes[0].obj
            self.assertFalse(any(x.subject == a and x.obj == e for x in stream.expectations if x.event_index < ep.designed_probe_index))
            own = own_events(stream, ep)
            taught = stream.session_of(own[0])
            self.assertEqual(stream.session_of(ep.designed_probe_index), min(taught + 2, stream.sessions - 1))
            late = span_of(stream, "N-late")
            lp = probes_of(stream, late)
            self.assertEqual((lp[0].subject, lp[0].obj), (lp[1].subject, lp[1].obj))
            self.assertEqual(stream.session_of(lp[1].event_index) - stream.session_of(lp[0].event_index), 1)

    # -- twins -----------------------------------------------------------------------------

    def test_twins_untaught_x_and_t_probes_are_gaps_and_everything_else_is_unchanged(self):
        for sset, closed in ((self.open, False), (self.closed, True)):
            for primary, twin in zip(sset.streams, sset.twins):
                self.assertEqual(twin.twin_of, primary.seed)
                self.assertEqual(twin.seed, primary.seed)
                self.assertNotEqual(twin.context_id, primary.context_id)
                self.assertEqual(len(twin.events), len(primary.events))
                self.assertEqual(twin.boundaries, primary.boundaries)
                self.assertEqual([x.event_index for x in twin.expectations], [x.event_index for x in primary.expectations])
                xt = [ep for ep in primary.episodes if ep.variant[0] in "XT"]
                changed = [j for j, (p, t) in enumerate(zip(primary.events, twin.events)) if p != t]
                self.assertTrue(changed)
                for j in changed:
                    self.assertIs(primary.events[j].kind, EventKind.FACT)
                    self.assertIs(twin.events[j].kind, EventKind.FACT)
                    self.assertEqual(primary.events[j].relation, "leads_to")
                    self.assertTrue(any(ep.start <= j < ep.end for ep in xt), j)
                for ep_p, ep_t in zip(primary.episodes, twin.episodes):
                    self.assertEqual(ep_p.canonical() | {"designed_verdict": None}, ep_t.canonical() | {"designed_verdict": None})
                    if ep_p.variant[0] in "XT":
                        self.assertEqual(ep_t.designed_verdict, gap(closed).value, ep_t)
                    else:
                        self.assertEqual(ep_t.designed_verdict, ep_p.designed_verdict, ep_t)
                owners = probe_owners(primary)
                for xp, xtw in zip(primary.expectations, twin.expectations):
                    if primary.episodes[owners[xp.event_index]].variant[0] not in "XT":
                        self.assertEqual(xp, xtw)
                # the untaught chain is a gap on every X/T probe that was YES
                for xp, xtw in zip(primary.expectations, twin.expectations):
                    if primary.episodes[owners[xp.event_index]].variant[0] in "XT":
                        self.assertIn(xtw.verdict, (gap(closed),), (xp, xtw))

    def test_twins_do_not_touch_the_rng(self):
        without = generate_session_set(SEEDS, twins=False)
        for a, b in zip(self.open.streams, without.streams):
            self.assertEqual(a, b)

    # -- balance -------------------------------------------------------------------------------

    def test_balance_under_the_ceiling_in_both_worlds_over_twenty_seeds(self):
        for closed in (False, True):
            sset = generate_session_set(range(20), closed_world=closed)
            report = balance_report(sset)
            self.assertEqual(set(report["classes"]), set("RHCNXDTG"))
            for mechanism, entry in report["classes"].items():
                self.assertLessEqual(entry["max_share"], BALANCE_CEILING, (closed, mechanism, entry))
            self.assertIs(report["closed_world"], closed)
            twin_report = balance_report(sset, twins=True)
            self.assertEqual(twin_report["classes"]["G"], report["classes"]["G"])

    def test_a_tighter_ceiling_is_refused_with_e_rs_007(self):
        with self.assertRaises(RevisionError) as ctx:
            generate_session_set((0,), ceiling=0.5)
        self.assertEqual(ctx.exception.code, "E-RS-007")

    # -- what must not move ----------------------------------------------------------------------

    def test_generate_revision_set_fingerprints_are_untouched(self):
        self.assertEqual(generate_revision_set(40, 20261006).fingerprint(), REVISION_OPEN)
        self.assertEqual(generate_revision_set(40, 20261006, closed_world=True).fingerprint(), REVISION_CLOSED)

    # -- convergence ---------------------------------------------------------------------------

    def test_the_walk_first_organism_agrees_with_the_oracle_on_every_probe(self):
        for sset, closed in ((self.open, False), (self.closed, True)):
            for stream in sset.streams + sset.twins:
                responses = Organism(closed_world=closed).run_stream(stream.events)
                expected = {x.event_index: x for x in stream.expectations}
                disagreements = []
                for r in responses:
                    if r.verdict is None:
                        continue
                    x = expected[r.index]
                    if r.verdict != x.verdict.value:
                        disagreements.append((stream.seed, closed, r.index, r.verdict, x.verdict.value))
                    self.assertEqual(set(r.contested), set(x.contested_required), (stream.context_id, closed, r.index))
                    self.assertTrue(set(x.lacunae_required) <= set(r.lacunae) <= set(x.lacunae_admissible),
                                    (stream.context_id, closed, r.index, r.lacunae, x))
                self.assertEqual(disagreements, [])
                refused = tuple(r.index for r in responses if r.verdict is None and not r.accepted)
                self.assertEqual(refused, stream.refused, (stream.context_id, closed))


def lesson_episodes(stream: SeedStream) -> list[EpisodeSpan]:
    return [ep for ep in stream.episodes if ep.mechanism == "L"]


def relations_of(stream: SeedStream, span: EpisodeSpan) -> list[str]:
    """The foreign relations an L episode uses, in first-appearance order."""
    out: list[str] = []
    for j in own_events(stream, span):
        e = stream.events[j]
        name = e.subject if e.relation == LESSON_RELATION else e.relation
        if is_foreign(name) and name not in out:
            out.append(name)
    return out


def organism_disagreements(stream: SeedStream, closed: bool) -> list[tuple]:
    """Every place the walk-first organism and the whole-stream oracle part:
    verdict, contested set, lacunae bounds, withdrawn bounds, refused indices."""
    responses = Organism(closed_world=closed).run_stream(stream.events)
    expected = {x.event_index: x for x in stream.expectations}
    withdrawn = {w.event_index: w for w in stream.withdrawn}
    out: list[tuple] = []
    for r in responses:
        if r.verdict is not None:
            x = expected[r.index]
            if r.verdict != x.verdict.value:
                out.append(("verdict", stream.context_id, closed, r.index, r.verdict, x.verdict.value))
            if set(r.contested) != set(x.contested_required):
                out.append(("contested", stream.context_id, closed, r.index, r.contested, x.contested_required))
            if not set(x.lacunae_required) <= set(r.lacunae) <= set(x.lacunae_admissible):
                out.append(("lacunae", stream.context_id, closed, r.index, r.lacunae, x.lacunae_required, x.lacunae_admissible))
        elif stream.events[r.index].kind in (EventKind.RETRACT, EventKind.NEGATION):
            w = withdrawn[r.index]
            if not set(w.required) <= set(r.withdrawn) <= set(w.permitted):
                out.append(("withdrawn", stream.context_id, closed, r.index, str(stream.events[r.index]), r.withdrawn, w.required, w.permitted))
    refused = tuple(r.index for r in responses if r.verdict is None and not r.accepted)
    if refused != stream.refused:
        out.append(("refused", stream.context_id, closed, refused, stream.refused))
    return out


class LessonSetTests(unittest.TestCase):
    """Item class L (contract §13): `generate_session_set(..., lessons=True)`."""

    #: The designed verdict sequence of each L variant (module doc of `sessions.py`)
    #: and the position of its designed probe in that sequence.
    WANT = {
        "L-before": (["GAP", "GAP", "YES", "YES"], 2),
        "L-apply": (["YES", "GAP", "YES", "GAP"], 2),
        "L-compose": (["YES", "GAP", "YES", "GAP"], 2),
        "L-retract": (["YES", "GAP", "YES", "GAP"], 1),
        "L-revive": (["YES", "GAP", "YES", "YES", "GAP"], 2),
        "L-specific": (["YES", "GAP", "YES"], 1),
        "L-edge": (["YES", "GAP", "GAP", "YES"], 2),
    }

    @classmethod
    def setUpClass(cls):
        cls.open = generate_session_set(SEEDS, lessons=True)
        cls.closed = generate_session_set(SEEDS, closed_world=True, lessons=True)
        cls.plain = generate_session_set(SEEDS)

    def worlds(self):
        return ((self.open, False), (self.closed, True))

    # -- the catalog, the fingerprints, the pairing ---------------------------------------

    def test_lessons_false_is_byte_identical_and_lessons_true_is_deterministic_and_different(self):
        self.assertEqual(generate_session_set(SEEDS, lessons=False), self.plain)
        self.assertEqual(generate_session_set(range(20), lessons=False).fingerprint(), ReferenceFingerprintTests.OPEN)
        self.assertEqual(generate_session_set(range(20), closed_world=True, lessons=False).fingerprint(),
                         ReferenceFingerprintTests.CLOSED)
        again = generate_session_set(SEEDS, lessons=True)
        self.assertEqual(again, self.open)
        self.assertEqual(again.fingerprint(), self.open.fingerprint())
        self.assertNotEqual(self.open.fingerprint(), self.plain.fingerprint())
        self.assertNotEqual(self.open.fingerprint(), self.closed.fingerprint())
        # the non-lesson episodes are drawn first from the same rng: their layouts are the plain set's
        for with_l, plain in zip(self.open.streams, self.plain.streams):
            self.assertEqual(sorted(ep.variant for ep in with_l.episodes), sorted(CATALOG + tuple(LESSON_VARIANTS)))
            self.assertEqual(sorted(ep.variant for ep in plain.episodes), sorted(CATALOG))
            for variant in CATALOG:
                a, b = span_of(with_l, variant), span_of(plain, variant)
                self.assertEqual(with_l.events[a.start:a.end].count(with_l.events[a.designed_probe_index]),
                                 plain.events[b.start:b.end].count(plain.events[b.designed_probe_index]), variant)

    def test_paired_worlds_are_byte_identical_with_lessons(self):
        for o, c in zip(self.open.streams + self.open.twins, self.closed.streams + self.closed.twins):
            self.assertEqual(o.events, c.events)
            self.assertEqual(o.boundaries, c.boundaries)
            self.assertEqual(o.refused, c.refused)
            self.assertEqual([w.canonical() for w in o.withdrawn], [w.canonical() for w in c.withdrawn])
            self.assertEqual([ep.canonical() | {"designed_verdict": None} for ep in o.episodes],
                             [ep.canonical() | {"designed_verdict": None} for ep in c.episodes])
            for xo, xc in zip(o.expectations, c.expectations):
                self.assertEqual((xo.event_index, xo.subject, xo.obj), (xc.event_index, xc.subject, xc.obj))
                if xo.verdict is Verdict.UNKNOWN:
                    self.assertIs(xc.verdict, Verdict.NO)
                else:
                    self.assertEqual(xo, xc)

    def test_shape_split_map_and_coverage_with_lessons(self):
        for sset, closed in self.worlds():
            self.assertEqual(sset.summary()["cross_session_episodes"], 3 * (len(CROSS_VARIANTS) + len(LESSON_VARIANTS)))
            for stream in sset.streams + sset.twins:
                self.assertEqual(len(stream.episodes), len(CATALOG) + len(LESSON_VARIANTS))
                for ep in lesson_episodes(stream):
                    mechanism, role, _base, offsets = LESSON_VARIANTS[ep.variant]
                    self.assertEqual((ep.mechanism, ep.role, ep.cross_session), ("L", role, True), ep)
                    self.assertIs(stream.events[ep.designed_probe_index].kind, EventKind.ASK)
                    touched = {stream.session_of(j) for j in own_events(stream, ep)}
                    self.assertEqual(len(touched), len(set(offsets)), ep)
                    self.assertGreater(stream.session_of(ep.designed_probe_index), min(touched), ep)
                covered = [stream.session_of(ep.designed_probe_index) for ep in stream.episodes if ep.cross_session]
                self.assertNotIn(0, covered)
                self.assertTrue(set(range(1, stream.sessions)) <= set(covered), (stream.seed, sorted(covered)))
                self.assertEqual(replay(stream.events, closed).expectations, stream.expectations)
                guard_hypotheses_fresh(stream.events)
                self.assertEqual(len(guard_route_bounds(stream.events)), len(stream.expectations))

    def test_tokens_are_disjoint_across_episodes_with_lessons(self):
        laid, _truths = _draw_seed(random.Random(0), StreamDifficulty(), 5, 0, True)
        seen: dict[str, int] = {}
        for i, ep in enumerate(laid.episodes):
            for token in ep.tokens():
                self.assertNotIn(token, seen, f"{token} in episodes {seen.get(token)} and {i}")
                seen[token] = i
        node_tokens = {t for e in laid.events if e.relation != LESSON_RELATION for t in (e.subject, e.obj)}
        self.assertEqual(len(seen), len(node_tokens))
        for stream in self.open.streams + self.open.twins:
            self.assertEqual(sorted(probe_owners(stream)), [x.event_index for x in stream.expectations])

    # -- the foreign relations ------------------------------------------------------------------

    def test_foreign_relations_are_unique_per_stream_and_never_reserved(self):
        self.assertFalse(set(FOREIGN_RELATIONS) & set(RESERVED_RELATIONS))
        for stream in self.open.streams + self.open.twins:
            used: dict[str, str] = {}
            for ep in lesson_episodes(stream):
                rels = relations_of(stream, ep)
                self.assertEqual(len(rels), 2 if ep.variant == "L-specific" else 1, (ep.variant, rels))
                for r in rels:
                    self.assertIn(r, FOREIGN_RELATIONS)
                    self.assertNotIn(r, used, f"{r} used by {used.get(r)} and {ep.variant}")
                    used[r] = ep.variant
            for e in stream.events:
                if e.relation == LESSON_RELATION:
                    self.assertIn(e.subject, FOREIGN_RELATIONS)
                    self.assertEqual(e.obj, "leads_to")
                elif e.relation not in RESERVED_RELATIONS:
                    self.assertIn(e.relation, FOREIGN_RELATIONS)
            foreign_events = [e for e in stream.events if is_foreign(e.relation) or e.relation == LESSON_RELATION]
            owners = probe_owners(stream)
            self.assertTrue(foreign_events)
            # only L episodes speak a foreign relation or a lesson
            for ep in stream.episodes:
                if ep.mechanism != "L":
                    for j in own_events(stream, ep):
                        self.assertIn(stream.events[j].relation, RESERVED_RELATIONS[:2], ep)
            self.assertTrue(all(owners[x.event_index] < len(stream.episodes) for x in stream.expectations))

    # -- the designed sequences ----------------------------------------------------------------

    def test_every_l_variant_has_its_designed_verdict_sequence_in_both_worlds(self):
        for sset, closed in self.worlds():
            for stream in sset.streams:
                for variant, (seq, position) in self.WANT.items():
                    ep = span_of(stream, variant)
                    probes = probes_of(stream, ep)
                    self.assertEqual([x.verdict for x in probes], [_Design(v).in_world(closed) for v in seq], variant)
                    self.assertEqual(probes[position].event_index, ep.designed_probe_index, variant)
                    self.assertEqual(ep.designed_verdict, _Design(seq[position]).in_world(closed).value, variant)

    def test_l_before_names_the_r_edges_twin_then_the_lesson_turns_the_gap_into_a_yes(self):
        for sset, closed in self.worlds():
            for stream in sset.streams:
                ep = span_of(stream, "L-before")
                own = own_events(stream, ep)
                probes = probes_of(stream, ep)
                r_edge = next(stream.events[j] for j in own if stream.events[j].kind is EventKind.FACT and is_foreign(stream.events[j].relation))
                lessons = [j for j in own if stream.events[j].relation == LESSON_RELATION]
                self.assertEqual(len(lessons), 1)
                self.assertEqual(stream.events[lessons[0]].subject, r_edge.relation)
                self.assertEqual([(x.subject, x.obj) for x in probes], [(probes[0].subject, probes[0].obj)] * 4)
                self.assertTrue(probes[1].event_index < lessons[0] < probes[2].event_index)
                k = [stream.session_of(x.event_index) for x in probes]
                self.assertEqual([s - k[0] for s in k], [0, 1, 1, 2])
                self.assertEqual(stream.session_of(lessons[0]), k[1])
                if not closed:
                    for x in probes[:2]:
                        self.assertEqual(x.lacunae_required, (pair_key(r_edge.pair),), x)
                    self.assertEqual(probes[2].lacunae_required, ())

    def test_l_apply_transfers_to_a_fresh_chain_two_sessions_later(self):
        for sset, closed in self.worlds():
            for stream in sset.streams:
                ep = span_of(stream, "L-apply")
                probes = probes_of(stream, ep)
                own = own_events(stream, ep)
                lesson_at = next(j for j in own if stream.events[j].relation == LESSON_RELATION)
                r = stream.events[lesson_at].subject
                designed = probes[2]
                taught_tokens = {t for j in own if stream.session_of(j) == stream.session_of(lesson_at)
                                 for t in (stream.events[j].subject, stream.events[j].obj)
                                 if stream.events[j].relation != LESSON_RELATION}
                fresh = [j for j in own if stream.session_of(j) == stream.session_of(designed.event_index)]
                fresh_tokens = {t for j in fresh for t in (stream.events[j].subject, stream.events[j].obj)}
                self.assertFalse(taught_tokens & fresh_tokens, "the fresh chain is over tokens the lesson never saw")
                self.assertIn(r, {stream.events[j].relation for j in fresh})
                self.assertFalse(any(x.subject == designed.subject and x.obj == designed.obj
                                     for x in stream.expectations if x.event_index < designed.event_index))
                self.assertTrue(lesson_at < probes[0].event_index)
                self.assertEqual(stream.session_of(designed.event_index) - stream.session_of(lesson_at), 2)

    def test_l_compose_mixes_two_entailed_edges_with_plain_ones_and_composes_across_a_boundary(self):
        for sset, closed in self.worlds():
            for stream in sset.streams:
                ep = span_of(stream, "L-compose")
                probes = probes_of(stream, ep)
                own = own_events(stream, ep)
                c0, ch = probes[0].subject, probes[0].obj
                foreign = [stream.events[j] for j in own if stream.events[j].kind is EventKind.FACT and is_foreign(stream.events[j].relation)]
                self.assertEqual(len(foreign), 2)
                self.assertEqual(len({e.relation for e in foreign}), 1)
                self.assertEqual({e.subject for e in foreign} & {c0}, {c0})
                self.assertEqual({e.obj for e in foreign} & {ch}, {ch})
                d = probes[2].obj
                self.assertEqual(probes[2].subject, c0)
                appended = next(j for j in own if stream.events[j] == events.fact(ch, d))
                self.assertTrue(probes[1].event_index < appended < probes[2].event_index)
                self.assertEqual(stream.session_of(probes[2].event_index) - stream.session_of(probes[0].event_index), 2)

    def test_l_retract_requires_the_held_conclusion_withdrawn_at_the_unlesson(self):
        for sset, closed in self.worlds():
            for stream in sset.streams:
                ep = span_of(stream, "L-retract")
                probes = probes_of(stream, ep)
                own = own_events(stream, ep)
                unlesson = [j for j in own if stream.events[j].kind is EventKind.RETRACT]
                self.assertEqual(len(unlesson), 1)
                self.assertEqual(stream.events[unlesson[0]].relation, LESSON_RELATION)
                self.assertNotIn(unlesson[0], stream.refused)
                self.assertTrue(probes[0].event_index < unlesson[0] < probes[1].event_index)
                w = {x.event_index: x for x in stream.withdrawn}[unlesson[0]]
                self.assertEqual(w.required, (pair_key((probes[0].subject, probes[0].obj)),))
                self.assertEqual(set(w.required) <= set(w.permitted), True)
                k = [stream.session_of(x.event_index) for x in probes]
                self.assertEqual([s - k[0] for s in k], [0, 1, 1, 2])
                self.assertEqual(stream.session_of(unlesson[0]), k[1])

    def test_l_revive_re_teaches_the_lesson_and_holds_across_a_further_boundary(self):
        for sset, closed in self.worlds():
            for stream in sset.streams:
                ep = span_of(stream, "L-revive")
                probes = probes_of(stream, ep)
                own = own_events(stream, ep)
                lessons = [j for j in own if stream.events[j].relation == LESSON_RELATION]
                self.assertEqual([stream.events[j].kind for j in lessons], [EventKind.FACT, EventKind.RETRACT, EventKind.FACT])
                self.assertEqual(len({stream.events[j].subject for j in lessons}), 1)
                self.assertTrue(lessons[0] < probes[0].event_index < lessons[1] < probes[1].event_index < lessons[2] < probes[2].event_index)
                self.assertNotIn(lessons[1], stream.refused)
                k = [stream.session_of(x.event_index) for x in probes]
                self.assertEqual([s - k[0] for s in k], [0, 1, 2, 3, 3])

    def test_l_specific_holds_a_lesson_for_r1_and_the_r2_edge_stays_a_gap(self):
        for sset, closed in self.worlds():
            for stream in sset.streams:
                ep = span_of(stream, "L-specific")
                probes = probes_of(stream, ep)
                own = own_events(stream, ep)
                r1 = next(stream.events[j].subject for j in own if stream.events[j].relation == LESSON_RELATION)
                foreign = [stream.events[j] for j in own if stream.events[j].kind is EventKind.FACT and is_foreign(stream.events[j].relation)]
                self.assertEqual(len(foreign), 2)
                r2_edge = next(e for e in foreign if e.relation != r1)
                self.assertEqual(r2_edge.obj, probes[1].obj, "the untaught edge is the last link")
                self.assertEqual((probes[0].subject, probes[0].obj), (probes[2].subject, probes[2].obj))
                self.assertEqual(probes[0].subject, probes[1].subject)
                if not closed:
                    self.assertEqual(probes[1].lacunae_required, (pair_key(r2_edge.pair),))
                self.assertEqual(stream.session_of(probes[1].event_index) - stream.session_of(probes[0].event_index), 1)

    def test_l_edge_retracts_the_entailed_edge_and_the_retract_of_its_twin_is_refused(self):
        for sset, closed in self.worlds():
            for stream in sset.streams:
                ep = span_of(stream, "L-edge")
                probes = probes_of(stream, ep)
                own = own_events(stream, ep)
                retracts = [j for j in own if stream.events[j].kind is EventKind.RETRACT]
                self.assertEqual(len(retracts), 2)
                edge, twin = stream.events[retracts[0]], stream.events[retracts[1]]
                self.assertTrue(is_foreign(edge.relation))
                self.assertEqual((twin.pair, twin.relation), (edge.pair, "leads_to"))
                self.assertNotIn(retracts[0], stream.refused)
                self.assertIn(retracts[1], stream.refused)
                self.assertTrue(probes[1].event_index < retracts[0] < probes[2].event_index < retracts[1] < probes[3].event_index)
                w = {x.event_index: x for x in stream.withdrawn}
                self.assertEqual(w[retracts[0]].required, (pair_key((probes[0].subject, probes[0].obj)),))
                self.assertEqual((w[retracts[1]].required, w[retracts[1]].permitted), ((), ()))
                # the lesson stands: the last probe runs through a fresh edge of the same relation
                lesson_at = next(j for j in own if stream.events[j].relation == LESSON_RELATION)
                self.assertEqual(stream.events[lesson_at].kind, EventKind.FACT)
                fresh = [stream.events[j] for j in own if retracts[1] < j < probes[3].event_index]
                self.assertEqual([e.relation for e in fresh], [edge.relation, "leads_to"])
                self.assertEqual((fresh[0].subject, fresh[1].obj), (probes[3].subject, probes[3].obj))
                if not closed:
                    self.assertEqual(probes[2].lacunae_required, (pair_key(edge.pair),), "the shadow under the retracted edge")

    # -- twins ---------------------------------------------------------------------------------

    def test_twins_replace_every_lesson_and_every_l_designed_probe_is_a_gap(self):
        for sset, closed in self.worlds():
            for primary, twin in zip(sset.streams, sset.twins):
                self.assertEqual(len(twin.events), len(primary.events))
                self.assertEqual(twin.boundaries, primary.boundaries)
                changed = [j for j, (p, t) in enumerate(zip(primary.events, twin.events)) if p != t]
                lessons = [j for j, e in enumerate(primary.events) if e.kind is EventKind.FACT and e.relation == LESSON_RELATION]
                self.assertTrue(set(lessons) <= set(changed))
                for j in lessons:
                    self.assertEqual((twin.events[j].kind, twin.events[j].relation), (EventKind.FACT, "leads_to"))
                self.assertFalse(any(e.relation == LESSON_RELATION and e.kind is EventKind.FACT for e in twin.events))
                owners = probe_owners(primary)
                for ep_p, ep_t in zip(primary.episodes, twin.episodes):
                    self.assertEqual(ep_p.canonical() | {"designed_verdict": None}, ep_t.canonical() | {"designed_verdict": None})
                    if ep_p.mechanism == "L":
                        self.assertEqual(ep_t.designed_verdict, gap(closed).value, ep_t)
                for xp, xtw in zip(primary.expectations, twin.expectations):
                    ep = primary.episodes[owners[xp.event_index]]
                    if ep.mechanism == "L":
                        self.assertEqual((xp.event_index, xp.subject, xp.obj), (xtw.event_index, xtw.subject, xtw.obj))
                        if xp.event_index == ep.designed_probe_index:
                            self.assertIs(xtw.verdict, gap(closed), (ep.variant, xp, xtw))
                        elif xp.verdict is Verdict.YES:
                            # a YES that rested on the lesson falls; one over plain edges
                            # (L-retract's sound half) stands: the oracle decides, pinned here
                            self.assertIn(xtw.verdict, (Verdict.YES, gap(closed)), (ep.variant, xp, xtw))
                            if xtw.verdict is Verdict.YES:
                                self.assertEqual(ep.variant, "L-retract", (xp, xtw))
                                self.assertNotEqual((xp.subject, xp.obj), (probes_of(primary, ep)[0].subject, probes_of(primary, ep)[0].obj))
                        else:
                            self.assertEqual(xp, xtw)
                    elif ep.variant[0] not in "XT":
                        self.assertEqual(xp, xtw)
                # every unlesson in the twin is refused: there was never a lesson to withdraw
                for j, e in enumerate(twin.events):
                    if e.kind is EventKind.RETRACT and e.relation == LESSON_RELATION:
                        self.assertIn(j, twin.refused)
                self.assertEqual(replay(twin.events, closed).expectations, twin.expectations)

    def test_twins_and_lessons_do_not_touch_the_rng(self):
        without = generate_session_set(SEEDS, twins=False, lessons=True)
        for a, b in zip(self.open.streams, without.streams):
            self.assertEqual(a, b)

    # -- balance -------------------------------------------------------------------------------

    def test_balance_under_the_ceiling_with_lessons_in_both_worlds_over_twenty_seeds(self):
        for closed in (False, True):
            sset = generate_session_set(range(20), closed_world=closed, lessons=True)
            report = balance_report(sset)
            self.assertEqual(set(report["classes"]), set("RHCNXDTGL"))
            for mechanism, entry in report["classes"].items():
                self.assertLessEqual(entry["max_share"], BALANCE_CEILING, (closed, mechanism, entry))
            self.assertEqual(report["classes"]["L"]["probes"], 20 * sum(len(seq) for seq, _ in self.WANT.values()))

    # -- convergence ---------------------------------------------------------------------------

    def test_the_walk_first_organism_agrees_with_the_oracle_on_every_lesson_stream_and_twin(self):
        for sset, closed in self.worlds():
            for stream in sset.streams + sset.twins:
                self.assertEqual(organism_disagreements(stream, closed), [])


class ReferenceFingerprintTests(unittest.TestCase):
    """The registered development set: seeds 0-19, five sessions, default difficulty,
    twins on. A run scored against a set with a different fingerprint is void."""

    OPEN = "9e0d35b0026ddfe363e265c1f2d7a07741011f331708fbb1c5aae5b412d5203a"
    CLOSED = "deae82a05c8af2e0768a22da1bf034372fa44a812f16bf3a37a8c4bd5822d760"

    def test_the_registered_fingerprints(self):
        from sessions import generate_session_set
        self.assertEqual(generate_session_set(range(20)).fingerprint(), self.OPEN)
        self.assertEqual(generate_session_set(range(20), closed_world=True).fingerprint(), self.CLOSED)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
