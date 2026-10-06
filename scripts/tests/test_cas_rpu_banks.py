"""The three reasoning banks and the two laws that keep them honest.

The laws, both from the sources rather than invented here:

  association is not deduction   `^8 -> ^9` with no `^6` between them is the
                                 cognitive short circuit, and is refused.
  gain is not truth              `^6` and `^9` run at unity gain. A stage that
                                 evaluates at gain converts Desire into
                                 justification.
"""

from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from cjt_sim import Region  # noqa: E402

from banks import (  # noqa: E402
    UNITY,
    BankError,
    BankTrace,
    Candidate,
    DecompositionBank,
    HypothesisBank,
    InferenceBank,
)
from workspace import Status, Workspace  # noqa: E402


def graph(*edges, closed=False, relation="leads_to"):
    ws = Workspace(closed_world=closed)
    for edge in edges:
        if len(edge) == 3:
            a, rel, b = edge
        else:
            a, b = edge
            rel = relation
        ws.fact(a, rel, b)
    return ws


class GainRegimeTests(unittest.TestCase):
    def test_generation_runs_above_unity(self):
        self.assertGreater(HypothesisBank().spec.beta, UNITY)

    def test_generation_at_or_below_unity_is_refused(self):
        for beta in (1.0, 0.5):
            with self.assertRaises(BankError) as ctx:
                HypothesisBank(beta=beta)
            self.assertEqual(ctx.exception.code, "E-BANK-001")

    def test_evaluation_and_inference_run_at_exactly_unity(self):
        self.assertEqual(DecompositionBank().spec.beta, UNITY)
        self.assertEqual(InferenceBank().spec.beta, UNITY)

    def test_a_non_unity_evaluation_gain_is_refused(self):
        """The truth firewall. 1.02 is a stage that exaggerates by 2%."""
        for beta in (1.02, 0.98, 2.0):
            with self.assertRaises(BankError) as ctx:
                DecompositionBank.guard_unity(beta)
            self.assertEqual(ctx.exception.code, "E-BANK-002")


class ShortCircuitTests(unittest.TestCase):
    def test_association_straight_to_conclusion_is_refused(self):
        trace = BankTrace()
        trace.fire("^8")
        with self.assertRaises(BankError) as ctx:
            trace.fire("^9")
        self.assertEqual(ctx.exception.code, "E-BANK-003")

    def test_the_middle_stage_makes_the_same_path_legal(self):
        trace = BankTrace()
        trace.fire("^8")
        trace.fire("^6")
        trace.fire("^9")
        self.assertEqual(trace.stages, ["^8", "^6", "^9"])

    def test_the_hypothesis_bank_has_no_way_to_return_a_verdict(self):
        """`^8` cannot conclude because its output type cannot express a
        conclusion. That is a property of the signature, not a convention."""
        signature = inspect.signature(HypothesisBank.surface)
        self.assertIn("list[Candidate]", str(signature.return_annotation))
        self.assertFalse(
            [n for n in dir(HypothesisBank) if "verdict" in n or "conclude" in n]
        )


class AssociationTests(unittest.TestCase):
    def test_association_crosses_relation_types_and_can_therefore_be_wrong(self):
        """`^8` follows any edge, so it surfaces a route whose links are not
        all of the queried relation. That route is a real candidate and a real
        possible error, which is what gives `^6` work to do."""
        ws = graph(("VS", "co_occurs", "DE"), ("DE", "leads_to", "IU"))
        candidates, reading = HypothesisBank().surface(ws, "VS", "IU", "leads_to")
        self.assertIs(reading.region, Region.ACTIVE)
        self.assertEqual([str(c) for c in candidates], ["VS -> DE -> IU"])

    def test_restricting_the_walk_makes_decomposition_a_rubber_stamp(self):
        """The defect this design avoids, demonstrated rather than asserted.

        With `associate_across=False` the trigger verifies its own output, so
        `^6` can never find a missing constituent and the deduction has
        silently moved into `^8`."""
        ws = graph(("VS", "co_occurs", "DE"), ("DE", "leads_to", "IU"))
        candidates, _ = HypothesisBank().surface(
            ws, "VS", "IU", "leads_to", associate_across=False
        )
        self.assertEqual(candidates, [])

    def test_a_cycle_is_not_a_route(self):
        ws = graph(("VS", "QS"), ("QS", "VS"), ("QS", "IU"))
        candidates, _ = HypothesisBank().surface(ws, "VS", "IU", "leads_to")
        for candidate in candidates:
            self.assertEqual(len(set(candidate.nodes)), len(candidate.nodes))

    def test_surfaced_routes_are_recorded_as_hypotheses_not_facts(self):
        ws = graph(("VS", "QS"), ("QS", "IU"))
        HypothesisBank().surface(ws, "VS", "IU", "leads_to")
        self.assertEqual(ws.ask("VS", "leads_to", "IU"), "UNKNOWN")


class DecompositionTests(unittest.TestCase):
    def test_a_complete_route_names_every_constituent(self):
        ws = graph(("VS", "QS"), ("QS", "IU"))
        candidate = Candidate("c", ("VS", "QS", "IU"), "leads_to")
        result = DecompositionBank().decompose(ws, candidate)
        self.assertTrue(result.complete)
        self.assertEqual(
            result.required, ("VS|leads_to|QS", "QS|leads_to|IU")
        )

    def test_a_missing_constituent_is_named_rather_than_swallowed(self):
        ws = graph(("VS", "co_occurs", "DE"), ("DE", "leads_to", "IU"))
        candidate = Candidate("c", ("VS", "DE", "IU"), "leads_to")
        result = DecompositionBank().decompose(ws, candidate)
        self.assertFalse(result.complete)
        self.assertEqual(result.missing, ("VS|leads_to|DE",))

    def test_decomposition_records_the_lacuna_it_found(self):
        ws = graph(("DE", "leads_to", "IU"))
        DecompositionBank().decompose(
            ws, Candidate("c", ("VS", "DE", "IU"), "leads_to")
        )
        self.assertIn("VS|leads_to|DE", ws.lacunae())

    def test_a_stage_in_cutoff_reports_nothing_supported(self):
        """A silent stage must not hand back a clean bill of health."""
        ws = graph(("VS", "QS"), ("QS", "IU"))
        candidate = Candidate("c", ("VS", "QS", "IU"), "leads_to")
        result = DecompositionBank().decompose(ws, candidate, v=0.001, r_total=5.0)
        self.assertIs(result.reading.region, Region.CUTOFF)
        self.assertFalse(result.complete)
        self.assertEqual(result.present, ())


class LivingWorkspaceBankTests(unittest.TestCase):
    """Behaviours a bank needs once the workspace outlives one episode."""

    def test_a_direct_premise_is_answered_without_deriving_itself(self):
        """Asking about a fact you already hold used to raise E-WS-003
        (self-support). A living workspace is asked that constantly."""
        ws = graph(("VS", "QS"))
        candidate = Candidate("c", ("VS", "QS"), "leads_to")
        result = InferenceBank().land(ws, DecompositionBank().decompose(ws, candidate))
        self.assertEqual(result.verdict, "YES")
        self.assertIs(result.conclusion.status, Status.FACT)
        self.assertIn("direct hit", result.note)

    def test_a_standing_conclusion_is_answered_from_the_record(self):
        ws = graph(("VS", "QS"), ("QS", "IU"))
        ws.derive("VS", "leads_to", "IU", ("VS|leads_to|QS", "QS|leads_to|IU"))
        candidate = Candidate("c", ("VS", "QS", "IU"), "leads_to")
        result = InferenceBank().land(ws, DecompositionBank().decompose(ws, candidate))
        self.assertEqual(result.verdict, "YES")
        self.assertIs(result.conclusion.status, Status.DERIVED)
        self.assertIn("already held", result.note)

    def test_association_walks_contested_links_so_decomposition_can_name_them(self):
        ws = graph(("VS", "QS"), ("QS", "IU"))
        ws.fact("QS", "leads_to", "IU", negated=True)
        candidates, _ = HypothesisBank().surface(ws, "VS", "IU", "leads_to")
        self.assertEqual([str(c) for c in candidates], ["VS -> QS -> IU"])

    def test_association_walks_stream_hypotheses_but_not_its_own_route_guesses(self):
        ws = graph(("VS", "QS"))
        ws.hypothesize("QS", "leads_to", "IU", stage="stream")
        ws.hypothesize("VS", "leads_to", "IU", stage="^8")   # a prior guess of its own
        candidates, _ = HypothesisBank().surface(ws, "VS", "IU", "leads_to")
        self.assertEqual([str(c) for c in candidates], ["VS -> QS -> IU"])

    def test_association_does_not_walk_negations(self):
        ws = Workspace()
        ws.fact("VS", "leads_to", "IU", negated=True)
        candidates, _ = HypothesisBank().surface(ws, "VS", "IU", "leads_to")
        self.assertEqual(candidates, [])

    def test_decomposition_reports_contested_separately_from_missing(self):
        ws = graph(("VS", "QS"))
        ws.fact("QS", "leads_to", "IU")
        ws.fact("QS", "leads_to", "IU", negated=True)
        result = DecompositionBank().decompose(
            ws, Candidate("c", ("VS", "QS", "IU", "TR"), "leads_to")
        )
        self.assertEqual(result.missing, ("QS|leads_to|IU", "IU|leads_to|TR"))
        self.assertEqual(result.contested, ("QS|leads_to|IU",))
        self.assertFalse(result.blocked_only_by_dispute)

    def test_a_route_blocked_only_by_dispute_says_so(self):
        ws = graph(("VS", "QS"))
        ws.fact("QS", "leads_to", "IU")
        ws.fact("QS", "leads_to", "IU", negated=True)
        result = DecompositionBank().decompose(
            ws, Candidate("c", ("VS", "QS", "IU"), "leads_to")
        )
        self.assertTrue(result.blocked_only_by_dispute)


class InferenceTests(unittest.TestCase):
    def setUp(self):
        self.bank = InferenceBank()
        self.decomposer = DecompositionBank()

    def test_a_complete_decomposition_lands_a_derived_conclusion(self):
        ws = graph(("VS", "QS"), ("QS", "IU"))
        result = self.bank.land(
            ws,
            self.decomposer.decompose(
                ws, Candidate("c", ("VS", "QS", "IU"), "leads_to")
            ),
        )
        self.assertEqual(result.verdict, "YES")
        self.assertEqual(
            result.conclusion.support, ("VS|leads_to|QS", "QS|leads_to|IU")
        )

    def test_an_incomplete_decomposition_is_unknown_under_an_open_world(self):
        ws = graph(("QS", "IU"))
        result = self.bank.land(
            ws,
            self.decomposer.decompose(
                ws, Candidate("c", ("VS", "QS", "IU"), "leads_to")
            ),
        )
        self.assertEqual(result.verdict, "UNKNOWN")
        self.assertIsNone(result.conclusion)

    def test_the_same_gap_is_no_under_a_closed_world(self):
        """The world assumption decides, not the bank's mood."""
        ws = graph(("QS", "IU"), closed=True)
        result = self.bank.land(
            ws,
            self.decomposer.decompose(
                ws, Candidate("c", ("VS", "QS", "IU"), "leads_to")
            ),
        )
        self.assertEqual(result.verdict, "NO")

    def test_the_note_names_which_constituents_were_unsupported(self):
        ws = graph(("QS", "IU"))
        result = self.bank.land(
            ws,
            self.decomposer.decompose(
                ws, Candidate("c", ("VS", "QS", "IU"), "leads_to")
            ),
        )
        self.assertIn("VS|leads_to|QS", result.note)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
