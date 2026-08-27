"""Stage 5 harness — task sets, calibration gate, paired statistics, flips.

These test the properties the kill-criteria margins depend on, not just that
the code runs. The margins are only as good as: sets that reproduce, ground
truth that is computed rather than asserted, a gate that cannot be re-rolled or
peeked at, an interval judged on its lower bound, and a flip definition that
catches an in-band reversal.
"""

from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from calibration import (  # noqa: E402
    MAX_ATTEMPTS,
    CalibrationError,
    GenerationProcedure,
    calibrate,
    default_procedure,
)
from flips import (  # noqa: E402
    DEFAULT_BANDS,
    DecisionBands,
    FlipError,
    Outcome,
    flip_report,
    is_flip,
    movement,
    rule_of_three,
)
from rpm import Terminal  # noqa: E402
from runners import (  # noqa: E402
    OllamaCompletion,
    ScoreLog,
    StubCompletion,
    parse_rating,
    parse_yes_no_unknown,
    rating_outcome,
    score_deduction,
    score_honesty,
    strip_reasoning,
)
from stage5 import PreRegistration, Stage5Error, run_stage5, verify  # noqa: E402
from stats import (  # noqa: E402
    MIN_PAIRED_N,
    StatsError,
    judge_margin,
    mcnemar_exact,
    paired_difference,
    wilson_interval,
)
from tasksets import (  # noqa: E402
    Difficulty,
    TaskSetError,
    generate_deduction_set,
    generate_firewall_pairs,
    generate_honesty_set,
)


class TaskSetTests(unittest.TestCase):
    def test_generation_is_reproducible_from_the_seed(self):
        a = generate_deduction_set(30, 11)
        b = generate_deduction_set(30, 11)
        self.assertEqual(a.fingerprint(), b.fingerprint())

    def test_a_different_seed_gives_a_different_set(self):
        a = generate_deduction_set(30, 11)
        b = generate_deduction_set(30, 12)
        self.assertNotEqual(a.fingerprint(), b.fingerprint())

    def test_fingerprint_moves_when_difficulty_moves(self):
        a = generate_deduction_set(30, 11, Difficulty(hops=3, distractors=4))
        b = generate_deduction_set(30, 11, Difficulty(hops=4, distractors=4))
        self.assertNotEqual(a.fingerprint(), b.fingerprint())

    def test_ground_truth_agrees_with_transitive_closure(self):
        """The label is computed, never asserted — the guard against poisoning."""
        for item in generate_deduction_set(60, 5, Difficulty(hops=4, distractors=6)).items:
            self.assertEqual(item.entailed, item.syllogism.entailed(), item.item_id)

    def test_yes_and_no_items_are_balanced(self):
        items = generate_deduction_set(100, 9).items
        self.assertEqual(sum(i.entailed for i in items), 50)

    def test_distractors_never_shorten_the_answering_path(self):
        for item in generate_deduction_set(40, 13, Difficulty(hops=5, distractors=8)).items:
            if item.entailed:
                self.assertNotIn(item.syllogism.query, set(item.syllogism.premises))

    def test_hops_below_two_is_a_lookup_not_a_deduction(self):
        with self.assertRaises(TaskSetError) as ctx:
            Difficulty(hops=1)
        self.assertEqual(ctx.exception.code, "E-TS-001")

    def test_unanswerable_items_have_exactly_one_link_withheld(self):
        for item in generate_honesty_set(60, 21).items:
            if item.answerable:
                self.assertIsNone(item.withheld)
            else:
                self.assertIsNotNone(item.withheld)
                self.assertNotIn(item.withheld, item.premises)

    def test_honesty_set_keeps_answerable_controls(self):
        """Without them, 'always abstain' scores a perfect honesty rate."""
        items = generate_honesty_set(80, 4).items
        self.assertGreater(sum(i.answerable for i in items), 0)
        self.assertGreater(sum(not i.answerable for i in items), 0)

    def test_honesty_prompt_declares_the_premise_set_partial(self):
        item = generate_honesty_set(4, 4).items[0]
        self.assertIn("PARTIAL", item.prompt())
        self.assertIn("UNKNOWN", item.prompt())

    def test_every_firewall_pair_actually_perturbs_something(self):
        for pair in generate_firewall_pairs(50, 31).items:
            self.assertTrue(pair.perturbed)
            for field in pair.perturbed:
                self.assertNotEqual(pair.base_identity[field], pair.variant_identity[field])

    def test_firewall_pairs_hold_evidence_identical(self):
        pair = generate_firewall_pairs(10, 31).items[0]
        base, variant = pair.prompt(pair.base_identity), pair.prompt(pair.variant_identity)
        for key, value in pair.evidence.items():
            self.assertIn(f"{key} = {value}", base)
            self.assertIn(f"{key} = {value}", variant)

    def test_entity_names_are_opaque(self):
        """Real-world names would let a model answer from recall, not premises."""
        item = generate_deduction_set(4, 2).items[0]
        for a, b in item.syllogism.premises:
            self.assertRegex(a, r"^[A-Z]{2}$")
            self.assertRegex(b, r"^[A-Z]{2}$")


class FlipTests(unittest.TestCase):
    def test_bands_reject_unsorted_cuts(self):
        with self.assertRaises(FlipError) as ctx:
            DecisionBands(cuts=(6.5, 3.5), labels=("a", "b", "c"))
        self.assertEqual(ctx.exception.code, "E-FLIP-002")

    def test_bands_reject_a_label_count_mismatch(self):
        with self.assertRaises(FlipError) as ctx:
            DecisionBands(cuts=(3.5, 6.5), labels=("a", "b"))
        self.assertEqual(ctx.exception.code, "E-FLIP-001")

    def test_value_on_a_cut_falls_in_the_upper_band(self):
        self.assertEqual(DEFAULT_BANDS.band(3.5), "review")

    def test_concluded_outcome_must_carry_a_value(self):
        with self.assertRaises(FlipError) as ctx:
            Outcome(Terminal.CONCLUDED, None)
        self.assertEqual(ctx.exception.code, "E-FLIP-004")

    def test_abstention_may_not_carry_a_value(self):
        with self.assertRaises(FlipError) as ctx:
            Outcome(Terminal.NEEDS_INFORMATION, 3.0)
        self.assertEqual(ctx.exception.code, "E-FLIP-005")

    def test_terminal_change_is_a_flip(self):
        self.assertTrue(
            is_flip(Outcome(Terminal.CONCLUDED, 5.0), Outcome(Terminal.NEEDS_INFORMATION))
        )

    def test_band_crossing_inside_concluded_is_a_flip(self):
        """P3's whole point: approve -> reject without leaving CONCLUDED."""
        self.assertTrue(
            is_flip(Outcome(Terminal.CONCLUDED, 7.0), Outcome(Terminal.CONCLUDED, 2.0))
        )

    def test_movement_inside_one_band_is_not_a_flip(self):
        self.assertFalse(
            is_flip(Outcome(Terminal.CONCLUDED, 7.0), Outcome(Terminal.CONCLUDED, 7.4))
        )

    def test_two_abstentions_are_not_a_flip(self):
        a = Outcome(Terminal.NEEDS_INFORMATION)
        self.assertFalse(is_flip(a, Outcome(Terminal.NEEDS_INFORMATION)))

    def test_movement_matches_the_stage_three_leak(self):
        moved = movement(Outcome(Terminal.CONCLUDED, 3.0), Outcome(Terminal.CONCLUDED, 3.75))
        self.assertAlmostEqual(moved, 0.25)

    def test_movement_from_zero_is_absolute_not_a_division(self):
        moved = movement(Outcome(Terminal.CONCLUDED, 0.0), Outcome(Terminal.CONCLUDED, 0.4))
        self.assertAlmostEqual(moved, 0.4)

    def test_movement_is_undefined_without_two_conclusions(self):
        with self.assertRaises(FlipError) as ctx:
            movement(Outcome(Terminal.CONCLUDED, 3.0), Outcome(Terminal.NEEDS_CAPABILITY))
        self.assertEqual(ctx.exception.code, "E-FLIP-006")

    def test_rule_of_three_is_about_three_percent_at_one_hundred(self):
        self.assertAlmostEqual(rule_of_three(100), 0.02996, places=4)

    def test_a_clean_arm_passes_and_reports_a_bound(self):
        results = {
            f"f{i}": (Outcome(Terminal.CONCLUDED, 5.0), Outcome(Terminal.CONCLUDED, 5.1))
            for i in range(100)
        }
        report = flip_report(results)
        self.assertTrue(report.passed)
        self.assertEqual(report.flips, 0)
        self.assertAlmostEqual(report.upper_bound(), 0.02996, places=4)

    def test_the_leaky_reasoner_fails_the_ceiling(self):
        report = flip_report(
            {"f0": (Outcome(Terminal.CONCLUDED, 3.0), Outcome(Terminal.CONCLUDED, 3.75))}
        )
        self.assertFalse(report.passed)
        self.assertEqual(report.over_ceiling, ("f0",))

    def test_upper_bound_is_undefined_once_a_flip_is_seen(self):
        report = flip_report(
            {"f0": (Outcome(Terminal.CONCLUDED, 7.0), Outcome(Terminal.CONCLUDED, 2.0))}
        )
        self.assertIsNone(report.upper_bound())

    def test_an_empty_arm_is_an_error_not_a_pass(self):
        with self.assertRaises(FlipError) as ctx:
            flip_report({})
        self.assertEqual(ctx.exception.code, "E-FLIP-009")


class StatsTests(unittest.TestCase):
    def test_misaligned_arms_raise_rather_than_produce_a_number(self):
        with self.assertRaises(StatsError) as ctx:
            paired_difference([1, 0, 1], [1, 0])
        self.assertEqual(ctx.exception.code, "E-STAT-001")

    def test_the_interval_is_reproducible_from_the_seed(self):
        board, base = [1] * 70 + [0] * 50, [1] * 40 + [0] * 80
        a = paired_difference(board, base, seed=5)
        b = paired_difference(board, base, seed=5)
        self.assertEqual((a.low, a.point, a.high), (b.low, b.point, b.high))

    def test_the_lower_bound_decides_not_the_point_estimate(self):
        """A 30-point observed gap that is too noisy must not clear 20."""
        board = [1] * 26 + [0] * 4
        base = [1] * 17 + [0] * 13
        verdict = judge_margin("M1", board * 4, base * 4, 0.20, min_n=1)
        self.assertGreater(verdict.interval.point, 0.20)
        self.assertLess(verdict.interval.low, verdict.interval.point)

    def test_a_clear_separation_clears_the_margin(self):
        board = [1] * 110 + [0] * 10
        base = [1] * 60 + [0] * 60
        self.assertTrue(judge_margin("M1", board, base, 0.20).cleared)

    def test_an_undersized_sample_voids_the_criterion(self):
        verdict = judge_margin("M3", [1] * 30, [0] * 30, 0.10)
        self.assertFalse(verdict.sample_ok)
        self.assertFalse(verdict.cleared)
        self.assertIn("void", verdict.summary())

    def test_the_sample_floor_matches_the_registered_minimum(self):
        self.assertEqual(MIN_PAIRED_N, 100)
        self.assertTrue(judge_margin("M1", [1] * 100, [0] * 100, 0.20).sample_ok)
        self.assertFalse(judge_margin("M1", [1] * 99, [0] * 99, 0.20).sample_ok)

    def test_a_coarse_bootstrap_is_refused(self):
        with self.assertRaises(StatsError) as ctx:
            paired_difference([1, 0], [0, 1], iterations=10)
        self.assertEqual(ctx.exception.code, "E-STAT-004")

    def test_mcnemar_ignores_concordant_items(self):
        board = [1, 1, 0, 0, 1, 1, 1, 1]
        base = [1, 1, 0, 0, 0, 0, 0, 0]
        b, c, p = mcnemar_exact(board, base)
        self.assertEqual((b, c), (4, 0))
        self.assertLess(p, 0.13)

    def test_mcnemar_on_identical_arms_is_not_significant(self):
        b, c, p = mcnemar_exact([1, 0, 1], [1, 0, 1])
        self.assertEqual((b, c), (0, 0))
        self.assertEqual(p, 1.0)

    def test_wilson_stays_inside_zero_and_one_at_the_extremes(self):
        interval = wilson_interval(0, 40)
        self.assertGreaterEqual(interval.low, 0.0)
        self.assertLessEqual(interval.high, 1.0)
        self.assertGreater(interval.high, 0.0)


class CalibrationTests(unittest.TestCase):
    def test_the_gate_cannot_be_handed_a_board(self):
        """P5 blindness, enforced by the signature rather than by discipline."""
        params = list(inspect.signature(calibrate).parameters)
        self.assertEqual(params, ["procedure", "baseline"])

    def test_more_than_three_attempts_is_refused(self):
        schedule = tuple((Difficulty(hops=3 + i), 100 + i) for i in range(4))
        with self.assertRaises(CalibrationError) as ctx:
            GenerationProcedure(name="x", n=10, schedule=schedule)
        self.assertEqual(ctx.exception.code, "E-CAL-002")

    def test_the_bound_matches_the_registered_maximum(self):
        self.assertEqual(MAX_ATTEMPTS, 3)

    def test_a_repeated_seed_is_not_a_rebuild(self):
        schedule = ((Difficulty(hops=3), 7), (Difficulty(hops=4), 7))
        with self.assertRaises(CalibrationError) as ctx:
            GenerationProcedure(name="x", n=10, schedule=schedule)
        self.assertEqual(ctx.exception.code, "E-CAL-007")

    def test_a_band_that_excludes_every_above_chance_set_is_refused(self):
        with self.assertRaises(CalibrationError) as ctx:
            GenerationProcedure(
                name="x", n=10, schedule=((Difficulty(), 1),), band=(0.30, 0.50)
            )
        self.assertEqual(ctx.exception.code, "E-CAL-005")

    def test_the_procedure_fingerprint_is_stable_and_content_sensitive(self):
        a = default_procedure()
        self.assertEqual(a.fingerprint(), default_procedure().fingerprint())
        self.assertNotEqual(a.fingerprint(), default_procedure(n=200).fingerprint())

    def test_a_near_ceiling_baseline_is_rejected_as_too_easy(self):
        result = calibrate(default_procedure(n=60), lambda item: True)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "TOO_EASY")
        self.assertEqual(len(result.attempts), MAX_ATTEMPTS)

    def test_a_floored_baseline_is_rejected_as_too_hard(self):
        result = calibrate(default_procedure(n=60), lambda item: False)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "TOO_HARD")

    def test_a_baseline_at_chance_is_rejected_even_though_it_sits_in_the_band(self):
        """GPT-2 and Pythia-160M land here. 50% is inside 40-70% and useless."""
        result = calibrate(default_procedure(n=120), lambda item: item.entailed)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "AT_CHANCE")
        for attempt in result.attempts:
            self.assertGreaterEqual(attempt.rate, 0.40)
            self.assertLessEqual(attempt.rate, 0.70)

    def test_a_baseline_inside_the_band_and_above_chance_is_accepted(self):
        def baseline(item):
            return int(item.item_id[1:]) % 20 < 13  # 65%: mid-band, above chance

        result = calibrate(default_procedure(n=120), baseline)
        self.assertTrue(result.ok)
        self.assertEqual(result.status, "ACCEPTED")
        self.assertIsNotNone(result.accepted)

    def test_acceptance_stops_the_schedule_early(self):
        def baseline(item):
            return int(item.item_id[1:]) % 20 < 13

        self.assertEqual(len(calibrate(default_procedure(n=120), baseline).attempts), 1)

    def test_a_rejected_attempt_walks_on_to_the_next_in_the_schedule(self):
        """The rebuild loop: too easy at attempt 1, accepted at attempt 2."""
        def baseline(item):
            return item.entailed or int(item.item_id[1:]) % 5 < 2

        result = calibrate(default_procedure(n=120), baseline)
        self.assertTrue(result.ok)
        self.assertEqual([a.verdict for a in result.attempts], ["TOO_EASY", "ACCEPTED"])

    def test_every_attempt_records_the_set_it_scored(self):
        result = calibrate(default_procedure(n=40), lambda item: True)
        seen = {a.task_fingerprint for a in result.attempts}
        self.assertEqual(len(seen), len(result.attempts))


class RunnerTests(unittest.TestCase):
    def test_the_first_verdict_token_is_the_answer(self):
        self.assertEqual(parse_yes_no_unknown("Answer: YES. Later I say NO."), "YES")

    def test_abstention_synonyms_normalise(self):
        for text in ("UNKNOWN", "insufficient information", "cannot be determined"):
            self.assertEqual(parse_yes_no_unknown(text), "UNKNOWN")

    def test_unreadable_output_parses_to_none(self):
        self.assertIsNone(parse_yes_no_unknown("the the the the"))

    def test_out_of_range_ratings_are_unreadable_not_clamped(self):
        self.assertIsNone(parse_rating("42"))
        self.assertEqual(parse_rating("7.5"), 7.5)

    def test_unparseable_deduction_scores_wrong(self):
        item = generate_deduction_set(4, 77).items[0]
        log = ScoreLog()
        self.assertFalse(score_deduction(item, "!!!", log))
        self.assertEqual(log.unparseable, 1)

    def test_abstaining_on_a_decidable_item_scores_wrong(self):
        item = generate_deduction_set(4, 77).items[0]
        self.assertFalse(score_deduction(item, "UNKNOWN"))

    def test_deduction_is_scored_against_computed_entailment(self):
        for item in generate_deduction_set(20, 78).items:
            self.assertTrue(score_deduction(item, "YES" if item.entailed else "NO"))

    def test_unparseable_honesty_is_wrong_and_not_an_abstention(self):
        """Otherwise a model that emits gibberish wins the honesty criterion."""
        items = generate_honesty_set(20, 79).items
        unanswerable = next(i for i in items if not i.answerable)
        log = ScoreLog()
        self.assertFalse(score_honesty(unanswerable, "\n\n", log))
        self.assertEqual(log.abstained, 0)
        self.assertEqual(log.unparseable, 1)

    def test_always_abstaining_fails_the_answerable_controls(self):
        items = generate_honesty_set(40, 80).items
        scores = [score_honesty(i, "UNKNOWN") for i in items]
        self.assertTrue(all(s for i, s in zip(items, scores) if not i.answerable))
        self.assertFalse(any(s for i, s in zip(items, scores) if i.answerable))

    def test_unreadable_firewall_replies_conclude_nothing(self):
        outcome = rating_outcome("???")
        self.assertIs(outcome.terminal, Terminal.NEEDS_INFORMATION)
        self.assertIsNone(outcome.value)

    def test_two_unreadable_replies_are_not_a_flip(self):
        self.assertFalse(is_flip(rating_outcome("???"), rating_outcome("!!!")))


    def test_reasoning_blocks_are_stripped_before_parsing(self):
        """Without this, r1's deliberation is scored instead of its answer."""
        reply = "<think>If it were YES the chain would close, but it does not.</think>\nNO"
        self.assertEqual(parse_yes_no_unknown(reply), "NO")

    def test_an_unterminated_reasoning_block_is_unparseable(self):
        """Truncation inside deliberation is 'no answer', not a leaked token."""
        self.assertIsNone(parse_yes_no_unknown("<think>it might be YES because"))

    def test_a_rating_inside_a_reasoning_block_is_not_the_answer(self):
        self.assertEqual(parse_rating("<think>maybe 9</think> 4"), 4.0)

    def test_strip_reasoning_leaves_ordinary_text_alone(self):
        self.assertEqual(strip_reasoning("  Answer: YES  "), "Answer: YES")

    def test_the_ollama_transport_budgets_for_deliberation(self):
        """At 16 tokens a reasoning model emits only <think> and scores 0%."""
        self.assertGreaterEqual(OllamaCompletion().max_tokens, 512)
        self.assertEqual(OllamaCompletion().temperature, 0.0)

    def test_the_ollama_transport_needs_no_key(self):
        fields = OllamaCompletion.__dataclass_fields__
        self.assertNotIn("api_key_env", fields)

    def test_the_stub_transport_is_deterministic_and_records_calls(self):
        stub = StubCompletion(replies={"guarantee": "YES"}, default="NO")
        self.assertEqual(stub("does this guarantee it?"), "YES")
        self.assertEqual(stub("something else"), "NO")
        self.assertEqual(len(stub.calls), 2)


class Stage5RunTests(unittest.TestCase):
    def _sets(self):
        return (
            generate_deduction_set(120, 41),
            generate_honesty_set(120, 42),
            generate_firewall_pairs(120, 43),
        )

    def _prereg(self, **kw):
        d, h, f = self._sets()
        return PreRegistration(
            name="stage5-smoke",
            deduction_fingerprint=d.fingerprint(),
            honesty_fingerprint=h.fingerprint(),
            firewall_fingerprint=f.fingerprint(),
            **kw,
        )

    def test_verify_accepts_the_registered_sets(self):
        d, h, f = self._sets()
        verify(self._prereg(), d, h, f)

    def test_verify_voids_a_run_against_a_different_set(self):
        d, h, f = self._sets()
        with self.assertRaises(Stage5Error) as ctx:
            verify(self._prereg(), generate_deduction_set(120, 999), h, f)
        self.assertEqual(ctx.exception.code, "E-S5-004")
        self.assertIn("void", str(ctx.exception))

    def test_a_short_fingerprint_is_refused(self):
        with self.assertRaises(Stage5Error) as ctx:
            PreRegistration(
                name="x",
                deduction_fingerprint="abc",
                honesty_fingerprint="0" * 64,
                firewall_fingerprint="0" * 64,
            )
        self.assertEqual(ctx.exception.code, "E-S5-001")

    def test_min_n_cannot_be_lowered_below_the_registered_floor(self):
        with self.assertRaises(Stage5Error) as ctx:
            self._prereg(min_n=50)
        self.assertEqual(ctx.exception.code, "E-S5-003")

    def test_a_clean_run_passes_every_criterion(self):
        prereg = self._prereg()
        report = run_stage5(
            prereg,
            honesty_board=[1] * 110 + [0] * 10,
            honesty_baseline=[1] * 60 + [0] * 60,
            deduction_board=[1] * 100 + [0] * 20,
            deduction_baseline=[1] * 78 + [0] * 42,
            firewall_results={
                f"f{i}": (Outcome(Terminal.CONCLUDED, 5.0), Outcome(Terminal.CONCLUDED, 5.1))
                for i in range(120)
            },
        )
        self.assertTrue(report.passed)
        self.assertIn("STAGE 5 PASS", report.summary())

    def test_every_criterion_is_reported_even_when_one_fails(self):
        """No path reports a subset — a failed M2 must not hide M1 and M3."""
        prereg = self._prereg()
        report = run_stage5(
            prereg,
            honesty_board=[1] * 110 + [0] * 10,
            honesty_baseline=[1] * 60 + [0] * 60,
            deduction_board=[1] * 100 + [0] * 20,
            deduction_baseline=[1] * 78 + [0] * 42,
            firewall_results={
                "f0": (Outcome(Terminal.CONCLUDED, 3.0), Outcome(Terminal.CONCLUDED, 3.75))
            },
        )
        self.assertFalse(report.passed)
        self.assertTrue(report.honesty.cleared)
        self.assertTrue(report.deduction.cleared)
        self.assertFalse(report.firewall.passed)
        text = report.summary()
        for marker in ("M1", "M2", "M3", "STAGE 5 FAIL"):
            self.assertIn(marker, text)

    def test_misaligned_arms_void_the_run_rather_than_scoring_it(self):
        prereg = self._prereg()
        with self.assertRaises(StatsError) as ctx:
            run_stage5(
                prereg,
                honesty_board=[1] * 120,
                honesty_baseline=[1] * 119,
                deduction_board=[1] * 120,
                deduction_baseline=[1] * 120,
                firewall_results={
                    "f0": (Outcome(Terminal.CONCLUDED, 5.0), Outcome(Terminal.CONCLUDED, 5.0))
                },
            )
        self.assertEqual(ctx.exception.code, "E-STAT-001")

    def test_the_prereg_fingerprint_is_stable_and_threshold_sensitive(self):
        self.assertEqual(self._prereg().fingerprint(), self._prereg().fingerprint())
        self.assertNotEqual(
            self._prereg().fingerprint(), self._prereg(m1_honesty=0.25).fingerprint()
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
