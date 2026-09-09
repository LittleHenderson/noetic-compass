"""Pure tests for the single-arm competence sequence: fit criterion, outcome
mapping, and the stage structure. No torch, no GPU, no AWS."""
import inspect

import pytest

from cas_meta2.graph_teaching import competence


def test_fit_criterion_is_a_registered_deterministic_rule():
    met = competence.fit_criterion({"a": 1.0, "b": 1.0, "c": 1.0},
                                   {"a": 0.9, "b": 0.9, "c": 0.9})
    assert met["met"] is True and met["margin"] == pytest.approx(0.1)
    not_met = competence.fit_criterion({"a": 1.0}, {"a": 0.99})
    assert not_met["met"] is False and not_met["margin"] == pytest.approx(0.01)
    # the REAL trainer returns per-op {"total": float} dicts (run 003's
    # preserved crash was int + dict summation here)
    met_dict = competence.fit_criterion({"a": {"total": 1.0}, "b": {"total": 1.1}},
                                        {"a": {"total": 0.9}, "b": {"total": 0.9}})
    assert met_dict["met"] is True and met_dict["margin"] == pytest.approx(0.15)


def test_outcome_is_one_of_the_three_registered_sentences():
    assert competence.outcome(False, False, 0) == "DID_NOT_FIT"
    assert competence.outcome(True, False, 0) == "DID_NOT_FIT"  # stage3 skipped
    assert competence.outcome(True, True, 6) == "LEARNED_AND_TRANSFERRED"
    assert competence.outcome(True, True, 5) == "LEARNED_NO_TRANSFER"
    assert competence.outcome(True, True, 12) == "LEARNED_AND_TRANSFERRED"


def test_difference_uses_norms_and_dot_only():
    class Tensor:
        def __init__(self, value):
            self.value = value

        def item(self):
            return self.value

    class Torch:
        class linalg:
            @staticmethod
            def vector_norm(tensor):
                return tensor

        @staticmethod
        def dot(a, b):
            return Tensor(a.value * b.value)

    assert competence._difference(Torch, Tensor(3.0), Tensor(4.0)) == pytest.approx(1.0)
    assert competence._difference(Torch, Tensor(2.0), Tensor(2.0)) == pytest.approx(0.0)


def test_launch_sequence_keeps_the_registered_structure():
    """The whole sequence runs inside ONE job: the stage-1 gate is on module
    INPUT distinguishability (output differences are reported, not gated),
    the forward/backward sanity, bounded training with a learning curve, and
    the sealed evaluation only after the fit criterion — single arm. A
    stage-1 failure returns a result with the preserved numbers, never a
    bare exception."""
    source = inspect.getsource(competence.launch)
    assert '"STAGE1_CHECK_FAILED"' in source
    assert 'stage1_passes(relationship_check, sanity)' in source
    assert "history_every=history_every" in source
    assert "evaluate_sealed(learner, seed=seed, arm=arm)" in source
    assert "arm = \"cas\"" in source
    assert "'cas', 'generic'" not in source
    gate_source = inspect.getsource(competence.stage1_passes)
    assert '"input_difference"' in gate_source
    assert '"output_difference"' not in gate_source


def test_stage1_gate_uses_input_distinguishability():
    """The registered gate: same-token rewiring must produce a distinguishable
    module INPUT beyond the reorder baseline; outputs are reported without
    gating; sanity needs finite losses and nonzero gradients."""
    def row(rewire_input, reorder_input):
        return {"connector_rewire_same_tokens": {"input_difference": rewire_input},
                "connection_list_reorder": {"input_difference": reorder_input}}

    good_sanity = {"per_target_loss": [1.0, 1.1, 1.2],
                   "per_target_max_gradient_norm": [0.1, 0.2, 0.3]}
    assert competence.stage1_passes([row(1e-3, 1e-5)], good_sanity) is True
    assert competence.stage1_passes([row(1e-6, 1e-5)], good_sanity) is False
    assert competence.stage1_passes([row(1e-3, 1e-5)],
                                    {"per_target_loss": [1.0, 1.0, float("nan")],
                                     "per_target_max_gradient_norm": [0.1]}) is False
    assert competence.stage1_passes([row(1e-3, 1e-5)],
                                    {"per_target_loss": [1.0],
                                     "per_target_max_gradient_norm": [0.0]}) is False


def test_result_claims_never_overstate():
    """The competence result must carry only negative/honest claims: no
    specialist claim, no two-arm comparison claim, sealed splits not read
    during training."""
    source = inspect.getsource(competence.launch)
    assert '"specialist_claimed": False' in source
    assert '"two_arm_comparison_claimed": False' in source
    assert '"sealed_splits_read": False' in source
