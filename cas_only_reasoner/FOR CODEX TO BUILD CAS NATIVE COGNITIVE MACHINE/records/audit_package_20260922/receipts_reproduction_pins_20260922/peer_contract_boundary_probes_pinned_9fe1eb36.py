"""Independent expected-contract probes against an exact Git object.
These tests are expected to FAIL against frozen 626cc84b; failures are evidence,
not a production test addition or a source fix. No neural imports or execution.
"""
import decimal
import subprocess
import sys
import types
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm3-lab')
PIN="9fe1eb36562b4d44dda788f93fca71316b8e8db2"
SOURCE="noetic-compass-scaffold/noetic-compass/api/cas_ohm/quantifiers.py"
raw=subprocess.check_output(["git","-C",str(ROOT),"show",f"{PIN}:{SOURCE}"])
m=types.ModuleType("frozen_ohm_contract_probe")
sys.modules[m.__name__]=m
exec(compile(raw,f"{PIN}:{SOURCE}","exec"),m.__dict__)

class ContractBoundaryAudit(unittest.TestCase):
    def assertRefused(self, fn):
        try:
            value=fn()
        except (ValueError,m.EligibilityError):
            return
        self.assertIsInstance(value,m.CensoredResult,"Invalid quantity must be refused or censored, not emitted as a usable value")

    def test_prediction_refuses_finite_input_overflow(self):
        self.assertRefused(lambda:m.i_pred(1e308,1e-308))

    def test_hidden_refuses_finite_input_overflow(self):
        self.assertRefused(lambda:m.r_hidden(1e308,0.1,2.0))

    def test_delta_rejects_nan_tolerance_instead_of_claiming_alignment(self):
        self.assertRefused(lambda:m.delta_current(100,0,tolerance=float("nan")))

    def test_interval_zero_denominator_is_refused_before_arithmetic(self):
        self.assertRefused(lambda:m.r_hidden(8,0,2,i_obs_interval=(1,2)))

    def test_admissible_trend_rejects_reversed_intervals(self):
        self.assertRefused(lambda:m.admissible_trend(2,8,axis="I_Q/test/profile",earlier_interval=(3,1),later_interval=(9,7),minimum_effect=0.1))

    def test_admissible_trend_rejects_unsupported_uncertainty_rule(self):
        self.assertRefused(lambda:m.admissible_trend(1.5,8,axis="I_Q/test/profile",earlier_interval=(1,2),later_interval=(7,9),minimum_effect=0.1,uncertainty_rule="made-up-rule"))

    def test_admissible_trend_preserves_exact_declared_decimal_evidence(self):
        D=decimal.Decimal
        result=m.admissible_trend(D("1.00000000000000000001"),D("1.00000000000000000004"),axis="I_Q/test/profile",earlier_interval=(D("1.00000000000000000000"),D("1.00000000000000000002")),later_interval=(D("1.00000000000000000003"),D("1.00000000000000000005")),minimum_effect=D("0.000000000000000000001"))
        self.assertEqual(result.verdict,m.TrendVerdict.RISING)

    def test_maturity_retains_exact_value_that_selected_the_band(self):
        exact=decimal.Decimal("2.49999999999999999999999999999999999999999999999999999")
        result=m.maturity_q4(exact)
        self.assertEqual(result.band,m.Band.Q1)
        self.assertEqual(decimal.Decimal(result.i_q_exact),exact)

if __name__=="__main__":
    unittest.main(verbosity=2)

