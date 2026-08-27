"""The Stage 5 comparison runner — the piece that turns the parts into a verdict.

Two concerns. The mechanical one: arms must stay aligned item for item, a
failed item must be recorded rather than dropped, and an undersized run must be
refused rather than reported.

The substantive one is `VerdictTests`. Pointed at different simulated models the
runner must reach *different* verdicts — pass for one, fail for another. A
runner that returns the same answer whatever it is pointed at is not measuring
anything, which was exactly the defect that made the board arm useless.

Simulated models throughout: no network, no keys.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))
sys.path.insert(0, str(REPO / "scripts" / "tests"))

import run_comparison as rc  # noqa: E402
from stats import MIN_PAIRED_N  # noqa: E402
from test_ccb_r1_wrap import (  # noqa: E402
    fabricating_model,
    leaking_rater,
    plausible_model,
    sound_model,
)


def _run(model, argv):
    out = Path(tempfile.mkdtemp()) / "result.json"
    with mock.patch.object(rc, "build_completion", return_value=model), \
         mock.patch.object(rc, "load_dotenv", return_value=0):
        code = rc.main(argv + ["--out", str(out)])
    return code, json.loads(out.read_text())


class DryRunTests(unittest.TestCase):
    def test_a_dry_run_spends_nothing(self):
        calls: list[str] = []
        with mock.patch.object(rc, "build_completion",
                               side_effect=AssertionError("must not build a transport")), \
             mock.patch.object(rc, "load_dotenv", return_value=0):
            self.assertEqual(rc.main(["--dry-run", "--n", "100"]), 0)
        self.assertEqual(calls, [])

    def test_the_estimate_is_an_upper_bound_per_arm(self):
        per_arm, total = rc.estimate(100)
        self.assertEqual(total, sum(per_arm.values()))
        # The wrapped honesty arm costs two calls only when the gate releases.
        self.assertEqual(per_arm["honesty wrapped"], 200)
        self.assertEqual(per_arm["honesty bare"], 100)


class SampleFloorTests(unittest.TestCase):
    def test_an_undersized_run_is_refused_rather_than_reported(self):
        with mock.patch.object(rc, "load_dotenv", return_value=0):
            with self.assertRaises(SystemExit) as ctx:
                rc.main(["--n", str(MIN_PAIRED_N - 1)])
        self.assertIn("void", str(ctx.exception))


class AlignmentTests(unittest.TestCase):
    def test_a_failed_item_is_scored_zero_not_dropped(self):
        """Dropping would shorten one arm and void the paired statistics."""
        items = [object(), object(), object()]
        arm = rc.score_arm("x", items, ["YES", None, "NO"], lambda i, a, log: a == "YES")
        self.assertEqual(len(arm.scores), 3)
        self.assertEqual(arm.failures, 1)
        self.assertEqual(arm.scores, [1, 0, 0])

    def test_a_transport_failure_counts_as_unreadable(self):
        arm = rc.score_arm("x", [object()], [None], lambda i, a, log: True)
        self.assertEqual(arm.log.unparseable, 1)
        self.assertEqual(arm.log.scored, 1)

    def test_parallel_preserves_order(self):
        got = rc._parallel([3, 1, 2], lambda x: x * 10, workers=3, retries=0)
        self.assertEqual(got, [30, 10, 20])

    def test_a_permanently_failing_item_resolves_to_none(self):
        def boom(_x):
            raise OSError("down")

        self.assertEqual(rc._parallel([1, 2], boom, workers=2, retries=0), [None, None])

    def test_call_counters_record_what_was_spent(self):
        counter = rc.Counter()
        counted = counter.wrap(lambda p: "YES")
        counted("a")
        counted("b")
        self.assertEqual(counter.calls, 2)

    def test_firewall_transport_holes_retain_pair_ids(self):
        pair = rc.generate_firewall_pairs(1, 20260831).items[0]

        def boom(_prompt):
            raise OSError("down")

        wrapped, bare = rc.run_firewall([pair], 1, 0, boom, boom)
        self.assertEqual(wrapped.failure_ids, (pair.pair_id,))
        self.assertEqual(wrapped.invalid_ids, (pair.pair_id,))
        self.assertEqual(bare.failure_ids, (pair.pair_id,))
        self.assertEqual(bare.invalid_ids, (pair.pair_id,))

    def test_firewall_materializes_an_iterator_for_both_arms(self):
        pair = rc.generate_firewall_pairs(1, 20260831).items[0]
        wrapped, bare = rc.run_firewall(iter([pair]), 1, 0, lambda _: "5.0", lambda _: "5.0")
        self.assertEqual(tuple(wrapped.results), (pair.pair_id,))
        self.assertEqual(tuple(bare.results), (pair.pair_id,))


class VerdictTests(unittest.TestCase):
    """Different models must reach different verdicts, or nothing is measured."""

    ARGV = ["--n", "100", "--ladder", "default", "--workers", "8", "--retries", "0"]

    def test_a_model_the_pipeline_helps_passes(self):
        code, result = _run(fabricating_model, self.ARGV)
        self.assertEqual(code, 0)
        self.assertTrue(result["passed"])
        self.assertTrue(result["m1"]["cleared"])
        self.assertTrue(result["m3"]["cleared"])

    def test_a_sound_model_fails_the_deduction_margin(self):
        """The pipeline adds nothing to a model that already reasons correctly."""
        code, result = _run(sound_model, self.ARGV)
        self.assertEqual(code, 1)
        self.assertFalse(result["passed"])
        self.assertFalse(result["m3"]["cleared"])
        self.assertTrue(result["m1"]["cleared"])  # it still gains on abstention

    def test_a_fluent_non_sequitur_fails_everything_it_can(self):
        code, result = _run(plausible_model, self.ARGV)
        self.assertEqual(code, 1)
        self.assertFalse(result["m1"]["cleared"])
        self.assertFalse(result["m3"]["cleared"])

    def test_the_compute_matched_control_is_always_reported(self):
        """Without it, a wrapped win could be architecture or just more inference."""
        _, result = _run(sound_model, self.ARGV)
        self.assertIn("bare_cot_rate", result["m3"])


class ResultFileTests(unittest.TestCase):
    ARGV = ["--n", "100", "--ladder", "default", "--workers", "8", "--retries", "0"]

    def test_every_set_is_fingerprinted_in_the_record(self):
        _, result = _run(sound_model, self.ARGV)
        for key in ("prereg_fingerprint", "deduction_fingerprint",
                    "honesty_fingerprint", "firewall_fingerprint"):
            self.assertEqual(len(result[key]), 64, key)

    def test_the_provider_is_pinned(self):
        _, result = _run(sound_model, self.ARGV)
        self.assertEqual(result["provider"], "deepseek")
        self.assertEqual(result["temperature"], 0.0)
        self.assertEqual(result["n"], 100)

    def test_unreadable_and_failure_counts_are_recorded_per_arm(self):
        _, result = _run(sound_model, self.ARGV)
        self.assertIn("deduction/wrapped", result["unparseable"])
        self.assertIn("honesty/bare", result["transport_failures"])

    def test_the_call_spend_is_recorded_per_arm(self):
        _, result = _run(sound_model, self.ARGV)
        self.assertGreater(sum(result["calls"].values()), 0)
        self.assertIn("h_wrapped", result["calls"])

    def test_m2_reports_wrapped_criterion_and_bare_control_separately(self):
        _, result = _run(sound_model, self.ARGV)
        m2 = result["m2"]
        self.assertEqual(m2["criterion_arm"], "wrapped")
        self.assertEqual(m2["causal_interpretation"], "NOT_ASSIGNED_BY_DIAGNOSTICS")
        for arm in (m2["wrapped"], m2["bare_control"]):
            self.assertIn("flipped_ids", arm)
            self.assertIn("over_ceiling_ids", arm)
            self.assertIn("invalid_ids", arm)
            self.assertIn("failure_ids", arm)

    def test_console_reports_both_m2_id_lists(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            _run(sound_model, self.ARGV)
        rendered = stdout.getvalue()
        self.assertIn("M2 wrapped flipped_ids=", rendered)
        self.assertIn("M2 bare control flipped_ids=", rendered)
        self.assertIn("over_ceiling_ids=", rendered)

    def test_m2_serializes_per_pair_a_a_boundary_diagnostics(self):
        _, result = _run(sound_model, self.ARGV)
        diagnostics = result["m2"]["wrapped_diagnostics"]
        self.assertEqual(len(diagnostics), 100)
        first = diagnostics[sorted(diagnostics)[0]]
        self.assertEqual(first["pair_id"], sorted(diagnostics)[0])
        self.assertTrue(first["outbound_prompts_match"])
        self.assertTrue(first["raw_replies_match"])
        self.assertTrue(first["parsed_outcomes_match"])
        self.assertEqual(first["classification"], "NO_DIVERGENCE")
        self.assertEqual(
            first["base"]["outbound_prompt_sha256"],
            first["variant"]["outbound_prompt_sha256"],
        )
        self.assertEqual(first["base"]["outcome"]["raw"], "5.0")

    def test_m2_id_lists_are_populated_for_a_leaky_bare_control(self):
        def model(prompt: str) -> str:
            if "Rate the strength of this case" in prompt:
                return leaking_rater(prompt)
            return sound_model(prompt)

        _, result = _run(model, self.ARGV)
        m2 = result["m2"]
        self.assertTrue(m2["wrapped"]["passed"])
        self.assertFalse(m2["bare_control"]["passed"])
        self.assertGreater(len(m2["bare_control"]["flipped_ids"]), 0)
        self.assertGreater(len(m2["bare_control"]["over_ceiling_ids"]), 0)

    def test_unreadable_firewall_coverage_cannot_serialize_as_pass(self):
        def model(prompt: str) -> str:
            if "Rate the strength of this case" in prompt:
                return "???"
            return sound_model(prompt)

        _, result = _run(model, self.ARGV)
        wrapped = result["m2"]["wrapped"]
        self.assertFalse(result["m2"]["passed"])
        self.assertFalse(wrapped["complete"])
        self.assertEqual(len(wrapped["invalid_ids"]), 100)
        self.assertEqual(wrapped["failure_ids"], [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
