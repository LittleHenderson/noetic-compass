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
    """The whole sequence runs inside ONE job: relationship tolerance,
    forward/backward sanity, bounded training with a learning curve, and the
    sealed evaluation only after the fit criterion — single arm."""
    source = inspect.getsource(competence.launch)
    assert "RELATIONSHIP_PRESERVATION_CHECK_FAILED" in source
    assert "FORWARD_BACKWARD_SANITY_FAILED" in source
    assert "REWIRE_TOLERANCE" in source
    assert "history_every=history_every" in source
    assert "evaluate_sealed(learner, seed=seed, arm=arm)" in source
    assert "arm = \"cas\"" in source
    assert "'cas', 'generic'" not in source


def test_result_claims_never_overstate():
    """The competence result must carry only negative/honest claims: no
    specialist claim, no two-arm comparison claim, sealed splits not read
    during training."""
    source = inspect.getsource(competence.launch)
    assert '"specialist_claimed": False' in source
    assert '"two_arm_comparison_claimed": False' in source
    assert '"sealed_splits_read": False' in source
