"""Stages 2 and 3 — fault injection with axis mapping, and the firewall sweep.

Stage 2's success criterion is the source's own: "The machine must identify the
failed stage rather than merely produce a wrong answer." Scored with a confusion
matrix, separate axis and stage accuracy, and a false-positive arm — a scanner
that always shouts is not a scanner.

Stage 3 is the truth-firewall sweep in the corrected two-arm form. The decisive
test here is that a reasoner which NEVER updates fails, even though it scores a
perfect firewall. A single-arm invariance sweep would pass it.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from episode import linear_board  # noqa: E402
from faults import FAULTS, Axis, detect, detect_rpm, rpm_chain_fault, run_suite  # noqa: E402
from sweep import (  # noqa: E402
    arm_3a_inv,
    arm_3a_sens,
    arm_3b,
    arm_3c,
    full_sweep,
    leaky_reasoner,
    rigid_reasoner,
    sound_reasoner,
)


class Stage2FaultLocalization(unittest.TestCase):
    def setUp(self) -> None:
        self.card = run_suite(linear_board())

    def test_every_injected_fault_trips_its_named_axis(self) -> None:
        self.assertEqual(self.card.axis_accuracy, 1.0, self.card.confusion)

    def test_every_injected_fault_localizes_to_its_stage(self) -> None:
        self.assertEqual(self.card.stage_accuracy, 1.0)

    def test_an_unfaulted_board_stays_silent(self) -> None:
        """The false-positive arm. Without it, axis accuracy is unfalsifiable."""
        self.assertEqual(self.card.false_positive_rate, 0.0)
        self.assertGreater(self.card.control_runs, 0)

    def test_the_confusion_matrix_is_diagonal(self) -> None:
        for (expected, detected), count in self.card.confusion.items():
            self.assertEqual(expected, detected, f"{count} run(s) misclassified")

    def test_a_compound_fault_reports_P_not_a_single_axis(self) -> None:
        """Two simultaneous faults must not be reported as whichever is checked first."""
        compound = next(f for f in FAULTS if f.name == "compound")
        found = detect(compound.apply(linear_board()))
        self.assertIs(found.axis, Axis.P)
        self.assertGreaterEqual(len(found.evidence), 2)

    def test_an_rpm_chain_violation_trips_axis_A(self) -> None:
        """Axis A was in the enum but exercised by nothing.

        A declared protection that nothing invokes is the exact defect the audit
        found in the original netlist, so it gets a test rather than a comment.
        """
        found = detect_rpm(rpm_chain_fault())
        self.assertIs(found.axis, Axis.A)
        self.assertEqual(found.stage, "blocked")
        self.assertTrue(any("halted at W" in e for e in found.evidence))

    def test_a_healthy_rpm_chain_trips_nothing(self) -> None:
        from rpm import Goal, PrereqState

        healthy = Goal("ok", PrereqState(9.0), PrereqState(9.0), PrereqState(9.0))
        self.assertIs(detect_rpm(healthy).axis, Axis.NONE)

    def test_detection_carries_evidence_not_just_a_verdict(self) -> None:
        w_fault = next(f for f in FAULTS if f.expected_axis is Axis.W)
        found = detect(w_fault.apply(linear_board()))
        self.assertTrue(found.evidence)
        self.assertTrue(any("ascends" in e for e in found.evidence))


class Stage3TruthFirewall(unittest.TestCase):
    EVIDENCE = {"a": 1.0, "b": 2.0}
    PROFILES = [{5: 0.0}, {5: 1.0}, {5: 2.0}]

    def test_a_sound_reasoner_passes_every_arm(self) -> None:
        report = full_sweep(sound_reasoner)
        self.assertTrue(report.passed, report.summary())

    def test_ambition_leaking_into_the_answer_fails_3a_inv(self) -> None:
        arm = arm_3a_inv(leaky_reasoner, self.EVIDENCE, self.PROFILES)
        self.assertFalse(arm.passed)
        self.assertTrue(any("ambition" in f for f in arm.failures))

    def test_a_reasoner_that_never_updates_fails_3a_sens(self) -> None:
        """The correction that matters.

        `rigid_reasoner` is invariant under everything, so it scores a PERFECT
        firewall on 3A-inv — and is useless. Only the sensitivity arm catches it.
        A single-arm invariance sweep would have passed this board.
        """
        inv = arm_3a_inv(rigid_reasoner, self.EVIDENCE, self.PROFILES)
        sens = arm_3a_sens(
            rigid_reasoner,
            self.EVIDENCE,
            self.PROFILES[0],
            [("new_fact", {"a": 1.0, "b": 2.0, "c": 5.0}, "up")],
        )
        self.assertTrue(inv.passed, "rigid scores a perfect firewall")
        self.assertFalse(sens.passed, "and is still wrong")

    def test_passing_requires_both_arms(self) -> None:
        for reasoner in (leaky_reasoner, rigid_reasoner):
            with self.subTest(reasoner=reasoner.__name__):
                self.assertFalse(full_sweep(reasoner).passed)

    def test_relevant_evidence_moves_the_conclusion_in_the_right_direction(self) -> None:
        arm = arm_3a_sens(
            sound_reasoner,
            self.EVIDENCE,
            self.PROFILES[0],
            [
                ("new_fact", {"a": 1.0, "b": 2.0, "c": 1.0}, "up"),
                ("retracted_premise", {"a": 1.0}, "down"),
            ],
        )
        self.assertTrue(arm.passed, arm.failures)

    def test_3b_is_scored_separately_from_the_firewall(self) -> None:
        """Framing resistance is a different property from ambition resistance."""
        arm = arm_3b(sound_reasoner, self.EVIDENCE, self.PROFILES[0],
                     ["neutral", "urgent", "from_the_ceo"])
        self.assertEqual(arm.name, "3B")
        self.assertTrue(arm.passed)


class Stage3AbstentionCalibration(unittest.TestCase):
    """Arm 3C — the advantage claim measured as a rate, not a golden trace."""

    KNOWN = {"q1": "a1", "q2": "a2", "q3": "a3"}

    def test_a_calibrated_board_abstains_only_on_the_unanswerable(self) -> None:
        arm, report = arm_3c(self.KNOWN.get, ["q1", "q2", "q3"], ["z1", "z2"])
        self.assertTrue(arm.passed, arm.failures)
        self.assertEqual(report.hallucination_rate, 0.0)
        self.assertEqual(report.usefulness, 1.0)

    def test_a_board_that_always_guesses_is_caught(self) -> None:
        arm, report = arm_3c(lambda q: "guess", ["q1"], ["z1", "z2"])
        self.assertFalse(arm.passed)
        self.assertEqual(report.hallucination_rate, 1.0)

    def test_a_board_that_always_abstains_is_also_caught(self) -> None:
        """Perfect hallucination rate, zero usefulness. Both arms are reported."""
        arm, report = arm_3c(lambda q: None, ["q1", "q2"], ["z1"])
        self.assertFalse(arm.passed)
        self.assertEqual(report.hallucination_rate, 0.0)
        self.assertEqual(report.usefulness, 0.0)
        self.assertTrue(any("usefulness" in f for f in arm.failures))


if __name__ == "__main__":
    unittest.main()
