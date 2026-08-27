"""Golden traces for the CJT simulator, taken from the source documents.

The circularity the test-program review warned about — the same act defining the
semantics AND authoring the traces that check it — is avoided here because every
expected number below is printed in `docs/reference/pdf/CAS_Ohm_Quantification_Guide.pdf`.
The source is the oracle. If the simulator disagrees with these numbers, the
simulator is wrong.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from cjt_sim import (  # noqa: E402
    CjtError,
    CjtSpec,
    Region,
    Scale,
    beta_cascade,
    cascade,
    measure,
    r_parallel,
    r_series,
)


class GuidePage12SingleCjt(unittest.TestCase):
    """Guide p.12, "One CJT, measured from rail to effect".

    V=8.0, R=2.0, I=8/2=4.0, beta=1.5, E*=beta*I=6.0, below sat=8.5 so active
    region; observed I=3.7 -> dI=-0.3 -> "aligned within +/-0.5".
    """

    def setUp(self) -> None:
        self.spec = CjtSpec(
            label="worked_example",
            beta=1.5,
            cutoff=0.0,
            sat=8.5,
            bias="Q4 / strong",
            scale=Scale.DESIGN,
        )

    def test_forward_measurement_matches_the_guide(self) -> None:
        r = measure(self.spec, v=8.0, r_total=2.0, i_obs=3.7)
        self.assertAlmostEqual(r.i_pred, 4.0)
        self.assertAlmostEqual(r.e_star, 6.0)
        self.assertIs(r.region, Region.ACTIVE)

    def test_residual_and_tolerance_match_the_guide(self) -> None:
        r = measure(self.spec, v=8.0, r_total=2.0, i_obs=3.7)
        self.assertAlmostEqual(r.delta_i, -0.3)
        self.assertTrue(r.aligned, "the guide calls -0.3 aligned within +/-0.5")

    def test_a_residual_outside_the_band_is_flagged(self) -> None:
        r = measure(self.spec, v=8.0, r_total=2.0, i_obs=3.0)
        self.assertAlmostEqual(r.delta_i, -1.0)
        self.assertFalse(r.aligned)
        self.assertTrue(any("ResidualOutOfBand" in w for w in r.warnings))


class GuidePage13Cascade(unittest.TestCase):
    """Guide p.13, the understanding -> evaluation -> response cascade.

    Stage 1 V=6 R=3 I=2 beta=2.0 | Stage 2 V=5 R=5 I=1 beta=1.0 |
    Stage 3 V=4 R=2 I=2 beta=1.5 | beta_total = 2.0*1.0*1.5 = 3.0
    """

    STAGES = [
        ("understanding", 2.0, 6.0, 3.0, 2.0),
        ("evaluation", 1.0, 5.0, 5.0, 1.0),
        ("response", 1.5, 4.0, 2.0, 2.0),
    ]

    def _spec(self, label: str, beta: float) -> CjtSpec:
        return CjtSpec(
            label=label, beta=beta, cutoff=0.0, sat=100.0, bias=f"{label}_bias", scale=Scale.DESIGN
        )

    def test_each_stage_local_current_matches_the_guide(self) -> None:
        for label, beta, v, r, expected_i in self.STAGES:
            with self.subTest(stage=label):
                reading = measure(self._spec(label, beta), v=v, r_total=r)
                self.assertAlmostEqual(reading.i_pred, expected_i)

    def test_cascade_gain_multiplies_to_three(self) -> None:
        self.assertAlmostEqual(beta_cascade(2.0, 1.0, 1.5), 3.0)

    def test_evaluation_stage_is_the_unity_gain_stage(self) -> None:
        """The artifact's 'truth firewall' is beta=1.0 on evaluation.

        The phrase "unity gain" never appears in the guide; the guide states it
        numerically. Pinned so the claim stays anchored to its actual source.
        """
        evaluation = next(s for s in self.STAGES if s[0] == "evaluation")
        self.assertEqual(evaluation[1], 1.0)

    def test_cascade_runs_all_three_stages(self) -> None:
        readings = cascade(
            [(self._spec(lbl, b), v, r) for lbl, b, v, r, _ in self.STAGES]
        )
        self.assertEqual([r.label for r in readings], ["understanding", "evaluation", "response"])
        self.assertTrue(all(r.region is Region.ACTIVE for r in readings))


class GuidePage14Recursion(unittest.TestCase):
    """Guide p.14, parallel branch aggregation.

    R1=3, R2=6 -> 1/R_eq = 1/3 + 1/6 -> R_eq = 2; V_parent = 6 -> I_parent = 3.
    """

    def test_parallel_aggregation_matches_the_guide(self) -> None:
        self.assertAlmostEqual(r_parallel(3.0, 6.0), 2.0)

    def test_parent_current_matches_the_guide(self) -> None:
        spec = CjtSpec(
            label="parent", beta=1.0, cutoff=0.0, sat=100.0, bias="parent_bias", scale=Scale.DESIGN
        )
        reading = measure(spec, v=6.0, r_total=r_parallel(3.0, 6.0))
        self.assertAlmostEqual(reading.i_pred, 3.0)

    def test_series_resistance_adds(self) -> None:
        self.assertAlmostEqual(r_series(3.0, 6.0), 9.0)

    def test_a_healthy_parent_can_hide_a_starved_and_an_overloaded_branch(self) -> None:
        """Guide p.14's recursive measurement rule, as an executable assertion.

        "A healthy parent total can hide one overloaded branch and one starved
        branch that cancel numerically." Child probes must therefore be kept.
        """
        parent = measure(
            CjtSpec(label="parent", beta=1.0, cutoff=0.0, sat=100.0, bias="b", scale=Scale.DESIGN),
            v=6.0,
            r_total=r_parallel(3.0, 6.0),
        )
        starved = measure(
            CjtSpec(label="A", beta=1.0, cutoff=2.5, sat=100.0, bias="b", scale=Scale.DESIGN),
            v=6.0,
            r_total=3.0,
        )
        overloaded = measure(
            CjtSpec(label="B", beta=1.0, cutoff=0.0, sat=0.5, bias="b", scale=Scale.DESIGN),
            v=6.0,
            r_total=6.0,
        )
        self.assertIs(parent.region, Region.ACTIVE, "the parent total looks healthy")
        self.assertIs(starved.region, Region.CUTOFF)
        self.assertIs(overloaded.region, Region.SATURATION)


class HandbookRegionSemantics(unittest.TestCase):
    """Operating-region and construction rules from CAS PCBA Engineer."""

    def _spec(self, **kw) -> CjtSpec:
        base = dict(label="s", beta=1.0, cutoff=0.2, sat=0.8, bias="b", scale=Scale.UNIT)
        base.update(kw)
        return CjtSpec(**base)

    def test_there_is_no_bias_free_cjt(self) -> None:
        with self.assertRaises(CjtError) as ctx:
            self._spec(bias=None)
        self.assertEqual(ctx.exception.code, "E-CJT-001")

    def test_empty_active_region_is_rejected(self) -> None:
        """"sat>cutoff so the active region is non-empty"."""
        with self.assertRaises(CjtError) as ctx:
            self._spec(cutoff=0.8, sat=0.2)
        self.assertEqual(ctx.exception.code, "E-CJT-003")

    def test_unit_scale_enforces_the_open_simplex(self) -> None:
        """"sat ∈ (0,1] and cutoff ∈ [0,1) ... sat=0 or cutoff=1 is rejected"."""
        for bad in ({"sat": 0.0, "cutoff": 0.0}, {"cutoff": 1.0, "sat": 1.0}):
            with self.subTest(**bad), self.assertRaises(CjtError):
                self._spec(**bad)

    def test_design_scale_permits_the_guides_worked_example(self) -> None:
        """Preserved Conflict 3.1: the guide runs sat=8.5, off the unit scale.

        The simulator refuses to silently harmonize the two normalizations, so
        sat=8.5 is admissible only when the spec declares Scale.DESIGN.
        """
        self._spec(scale=Scale.DESIGN, sat=8.5, cutoff=0.0)  # accepted
        with self.assertRaises(CjtError):
            self._spec(scale=Scale.UNIT, sat=8.5, cutoff=0.0)  # rejected

    def test_cross_domain_bias_is_rejected(self) -> None:
        """E-CJT-008: a bias must not be lower in precedence than its target."""
        with self.assertRaises(CjtError) as ctx:
            self._spec(bias_domain="E", target_domain="C")
        self.assertEqual(ctx.exception.code, "E-CJT-008")
        self._spec(bias_domain="P", target_domain="E")  # principled charter is fine

    def test_saturation_latches_and_stronger_causes_do_nothing(self) -> None:
        spec = self._spec(beta=4.0, cutoff=0.1, sat=0.8)
        weak = measure(spec, v=0.5, r_total=1.0)
        strong = measure(spec, v=5.0, r_total=1.0)
        self.assertIs(weak.region, Region.SATURATION)
        self.assertIs(strong.region, Region.SATURATION)
        self.assertAlmostEqual(weak.e_star, strong.e_star, msg="both clamp at sat")

    def test_cutoff_produces_no_effect_and_halts_a_cascade(self) -> None:
        live = self._spec(label="live", cutoff=0.1)
        silent = self._spec(label="silent", cutoff=0.9, sat=1.0)
        readings = cascade([(live, 0.5, 1.0), (silent, 0.5, 1.0), (live, 0.5, 1.0)])
        self.assertEqual([r.label for r in readings], ["live", "silent"])
        self.assertIs(readings[-1].region, Region.CUTOFF)

    def test_breakdown_flips_to_the_involution_pair(self) -> None:
        spec = self._spec(beta=2.0, cutoff=0.05, sat=0.8)
        r = measure(spec, v=1.0, r_total=1.0, breakdown_at=1.5)
        self.assertIs(r.region, Region.BREAKDOWN)
        self.assertTrue(any("Breakdown" in w for w in r.warnings))


if __name__ == "__main__":
    unittest.main()
