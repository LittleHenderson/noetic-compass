"""Numerical tests for the recurrent CJT wrapper (CAS_RDCJT_001 step two).

Plumbing verification, NOT a neural workload and NOT a claim about learning. Every
test here runs a hand-built four-wide stand-in module with real torch on CPU, because
the three things this step has to establish cannot be established without tensors:

* that depth one is the EXISTING computation, bitwise, and not merely close to it;
* that the gradient reaches the module through every pass — the failure this wrapper
  exists to prevent is a silent detach at pass two, which no list-based test can see;
* that a batch of eight is one optimizer update at every depth.

No model, no GPU, no AWS, no training run, no claim about the encoder or the
registered module. The stand-in is deliberately small enough to unroll by hand, and
the unroll below is written out longhand so that it can disagree with the loop.
"""
import pytest
import torch

from cas_meta2.recurrent_cjt import learner as ml
from cas_meta2.recurrent_cjt import recurrence as rc

WIDTH = 4
VOCABULARY = 8

#: The declared settings, restated in the unroll so a change in the module cannot
#: quietly move both sides of the comparison at once.
LAMBDA = 0.5
EPSILON = 1e-6


# --------------------------------------------------------------------------
# a stand-in for the registered ^6 transformation
# --------------------------------------------------------------------------

class TinyModule(torch.nn.Module):
    """Two matrices and a scalar, so a broken gradient path cannot hide in one of them."""

    def __init__(self, width=WIDTH):
        super().__init__()
        self.first = torch.nn.Parameter(
            torch.linspace(-0.5, 0.5, width * width).reshape(width, width))
        self.second = torch.nn.Parameter(
            torch.linspace(0.25, -0.75, width * width).reshape(width, width))
        self.scale = torch.nn.Parameter(torch.tensor(0.75))

    def forward(self, batched):
        return self.scale * torch.tanh(torch.tanh(batched @ self.first) @ self.second)


class TinyFramework:
    def __init__(self, torch_module=torch, seed=7):
        self.torch = torch_module
        self.device = torch_module.device("cpu")
        self.module = TinyModule()
        generator = torch_module.Generator().manual_seed(seed)
        self.projection = torch_module.randn((VOCABULARY, WIDTH),
                                            generator=generator)
        self.projection.requires_grad_(False)
        self.encoder = {"embed": self._embed, "encode": _encode,
                        "encode_problem": self._encode_problem}

    def _embed(self, token_id):
        return self.projection[token_id]

    def _encode_problem(self, public):
        return self.projection[torch.tensor(public["tokens"])].sum(dim=0)


def _encode(public):
    return list(range(len(public["tokens"]))), {
        slot: list(public["slots"][slot]) for slot in (0, 1, 2)}


def _public(record_id, tokens, slots):
    return {"record_id": record_id, "tokens": list(tokens),
            "slots": [list(entry) for entry in slots]}


#: Three teaching-shaped tasks. The third has a strict-subset option, so the
#: empty-content zero-vector branch is exercised rather than assumed.
TASKS = [
    {"record_id": "q%02d" % index, "op": "cas.cjt.operation.^6.decompose",
     "public": public, "encoded_options": ["alpha", "beta", "gamma"],
     "encoded_correct_index": index % 3}
    for index, public in enumerate([
        _public("q00", [0, 1, 2, 3], [[0, 1], [1, 2], [2, 3]]),
        _public("q01", [4, 5, 6], [[4, 5], [5, 6], [4, 6]]),
        _public("q02", [1, 2, 3, 4, 5], [[1, 2], [1, 2, 3], [1, 2, 3, 4]]),
        _public("q03", [6, 7], [[0, 6], [6, 7], [0, 7]]),
    ])
]


def _learner(*, depth=1, tasks=None, framework=None, reset_each_pass=False,
             accounting=None, torch_module=torch):
    framework = framework or TinyFramework(torch_module=torch_module)
    return ml.RecurrentGraphLearner(
        torch_module, framework, list(tasks or TASKS), framework.device, 0.003,
        depth=depth, reset_each_pass=reset_each_pass, accounting=accounting)


# --------------------------------------------------------------------------
# the independent unroll: the declared recurrence written out longhand
# --------------------------------------------------------------------------

def inline_unrolled(module, encoded, depth, *, detach_between=False,
                    torch_module=torch):
    """s_k+1 = F(e + B(s_k, e)), with the feedback written out and no library calls.

    Deliberately NOT built on ``recurrence.run_passes``: if the loop and this
    disagree, one of them is wrong, and neither can vouch for the other.
    """
    state = torch_module.zeros_like(encoded)
    for pass_index in range(depth):
        if pass_index == 0:
            incoming = encoded
        else:
            input_rms = torch_module.sqrt(torch_module.mean(encoded * encoded))
            state_rms = torch_module.sqrt(torch_module.mean(state * state))
            scale = (LAMBDA * input_rms
                     / torch_module.sqrt(input_rms ** 2 + state_rms ** 2
                                         + EPSILON ** 2))
            incoming = encoded + scale * state
            if detach_between:
                incoming = incoming.detach()
        state = module(incoming.unsqueeze(0))[0]
    return state


def gradients_of(module, build):
    """The parameter gradients of one backward pass over ``build()``'s value."""
    module.zero_grad(set_to_none=True)
    value = build()
    (value * value).sum().backward()
    return {name: parameter.grad.detach().clone()
            for name, parameter in module.named_parameters()}


# --------------------------------------------------------------------------
# 1. depth one IS the existing computation
# --------------------------------------------------------------------------

def test_depth_one_is_the_existing_learner_bitwise():
    """The matched one-pass condition has to be the same computation, not a lookalike."""
    from cas_meta2.graph_teaching.real_framework import GraphLearner
    framework = TinyFramework()
    one_pass = GraphLearner(torch, framework, list(TASKS), framework.device, 0.003)
    recurrent = ml.RecurrentGraphLearner(torch, framework, list(TASKS),
                                         framework.device, 0.003, depth=1)
    for position, task in enumerate(TASKS):
        assert torch.equal(one_pass.forward(position), recurrent.forward(position)), (
            "depth one must reproduce GraphLearner.forward exactly at position %d"
            % position)
        assert one_pass.predict(task) == recurrent.predict(task)
        assert one_pass.scores(task) == recurrent.scores(task)
    # and the on-demand path, which is the one the frozen panel travels
    sealed = {"record_id": "sealed-1", "public": _public(
        "sealed-1", [2, 3, 5], [[2, 3], [3, 5], [2, 5]]),
        "encoded_options": ["alpha", "beta", "gamma"]}
    assert one_pass.predict(sealed) == recurrent.predict(sealed)


def test_the_wrapper_computes_the_declared_recurrence():
    """Depths 2, 4 and 8 must equal the hand-written unroll, not merely change."""
    framework = TinyFramework()
    learner = _learner(framework=framework)
    encoded = learner._problem_vectors[0]
    with torch.no_grad():
        for depth in (1, 2, 4, 8):
            learner.set_depth(depth)
            got = learner.value_at_depth(problem_vector=encoded)
            want = inline_unrolled(framework.module, encoded, depth)
            difference = float((got - want).abs().max())
            assert difference == 0.0, (
                "depth %d differs from the longhand unroll by %r"
                % (depth, difference))


def test_more_passes_change_the_answer_and_keep_the_width():
    learner = _learner(framework=TinyFramework())
    encoded = learner._problem_vectors[0]
    values = {}
    for depth in (1, 2, 4, 8):
        learner.set_depth(depth)
        values[depth] = learner.value_at_depth(problem_vector=encoded)
        assert tuple(values[depth].shape) == (WIDTH,)
    assert not torch.equal(values[1], values[2])
    assert not torch.equal(values[2], values[8])


# --------------------------------------------------------------------------
# 2. the gradient reaches the module through every pass
# --------------------------------------------------------------------------

def test_the_gradient_reaches_the_module_through_every_pass():
    """The failure this wrapper prevents: a silent detach at pass two.

    The learner's own path and the longhand unroll must produce identical gradients
    at depth eight, and the deliberately detached unroll must produce different ones
    — otherwise this test could not have detected a detach.
    """
    framework = TinyFramework()
    learner = _learner(framework=framework, depth=8)
    encoded = learner._problem_vectors[0]
    module = framework.module

    through_the_learner = gradients_of(
        module, lambda: learner.value_at_depth(problem_vector=encoded))
    through_the_unroll = gradients_of(
        module, lambda: inline_unrolled(module, encoded, 8))
    detached = gradients_of(
        module, lambda: inline_unrolled(module, encoded, 8, detach_between=True))

    for name, value in through_the_learner.items():
        assert torch.equal(value, through_the_unroll[name]), (
            "the loop and the longhand unroll disagree on %s" % name)
        assert value.abs().sum().item() > 0.0, (
            "%s received no gradient at all" % name)
        assert not torch.equal(value, detached[name]), (
            "a detached unroll produced the same gradient on %s, so this test "
            "would not have caught a detach" % name)


def test_a_detached_pass_is_measurably_different_not_merely_possible():
    """The detach risk is a real one for this exact module, measured here."""
    framework = TinyFramework()
    module = framework.module
    encoded = framework.encoder["encode_problem"](TASKS[0]["public"])
    connected = gradients_of(module, lambda: inline_unrolled(module, encoded, 8))
    detached = gradients_of(
        module, lambda: inline_unrolled(module, encoded, 8, detach_between=True))
    relative = {}
    for name, value in connected.items():
        numerator = float((value - detached[name]).abs().sum())
        denominator = float(value.abs().sum()) or 1.0
        relative[name] = round(numerator / denominator, 6)
    assert all(gap > 0.01 for gap in relative.values()), (
        "detaching between passes barely moves the gradient (%r), so the risk "
        "would not be worth a module" % relative)


# --------------------------------------------------------------------------
# 3. one optimizer update per batch, whatever the depth
# --------------------------------------------------------------------------

@pytest.mark.parametrize("depth", [1, 2, 4, 8])
def test_one_optimizer_update_per_batch_at_every_depth(depth):
    accounting = rc.Accounting()
    learner = _learner(depth=depth, accounting=accounting)
    calls = []
    original = learner.optimizer.step

    def counting_step(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    learner.optimizer.step = counting_step
    batch = TASKS[:3]
    outcome = ml.recurrent_batch_step(learner, batch)
    assert len(calls) == 1, "a batch is ONE update"
    assert outcome["optimizer_steps"] == 1
    assert outcome["depth"] == depth
    assert len(outcome["episodes"]) == 3
    assert all(len(episode["scores"]) == 3 for episode in outcome["episodes"])
    report = accounting.report()
    assert report["optimizer_updates"] == 1
    assert report["sample_level_core_passes"] == depth * 3, (
        "eight passes over three questions is 24 sample passes, not 3 and not 8")
    assert report["batched_core_forward_calls"] == depth


def test_the_accounting_is_shared_with_the_learner_when_none_is_passed():
    accounting = rc.Accounting()
    learner = _learner(depth=4, accounting=accounting)
    ml.recurrent_batch_step(learner, TASKS[:2])
    report = accounting.report()
    assert report["sample_level_core_passes"] == 8
    assert report["optimizer_updates"] == 1


def test_the_batch_path_refuses_an_empty_batch():
    learner = _learner(depth=2)
    with pytest.raises(ValueError) as error:
        ml.recurrent_batch_step(learner, [])
    assert "RECURRENT_BATCH_EMPTY" in str(error.value)


# --------------------------------------------------------------------------
# 4. RESET_8 is a mechanism check
# --------------------------------------------------------------------------

def test_reset_eight_reproduces_depth_one_and_carried_eight_does_not():
    learner = _learner(framework=TinyFramework())
    encoded = learner._problem_vectors[0]

    learner.set_depth(1)
    learner.reset_each_pass = False
    one_pass = learner.value_at_depth(problem_vector=encoded)

    learner.set_depth(8)
    learner.reset_each_pass = True
    reset_eight = learner.value_at_depth(problem_vector=encoded)
    assert torch.equal(one_pass, reset_eight), (
        "eight computations with the state discarded must reproduce one pass exactly")

    learner.reset_each_pass = False
    carried_eight = learner.value_at_depth(problem_vector=encoded)
    assert not torch.equal(one_pass, carried_eight)


def test_the_evaluation_labels_map_to_the_declared_depths():
    assert ml.depth_and_reset("R1") == (1, False)
    assert ml.depth_and_reset("R2") == (2, False)
    assert ml.depth_and_reset("R4") == (4, False)
    assert ml.depth_and_reset("R8") == (8, False)
    assert ml.depth_and_reset("RESET_8") == (8, True)
    with pytest.raises(ValueError) as error:
        ml.depth_and_reset("R16")
    assert "EVALUATION_DEPTH_UNKNOWN" in str(error.value)


# --------------------------------------------------------------------------
# 5. the depth sweep: gains and losses, and the reset check
# --------------------------------------------------------------------------

#: A fixed outcome table with a net-zero depth, so a pooled average would hide it.
OUTCOMES = {
    "R1": [True, True, False, False],
    "R2": [True, False, True, False],
    "R4": [True, False, True, False],
    "R8": [False, False, True, True],
    "RESET_8": [True, True, False, False],
}


def stub_panel(outcomes=None, *, bump_weight=False, framework=None):
    table = outcomes or OUTCOMES

    def evaluate_panel(*, learner, items, built=None, phase):
        if bump_weight and framework is not None:
            with torch.no_grad():
                framework.module.scale.add_(0.5)
        return [{"item_id": "q%d" % index, "is_correct": table[phase][index]}
                for index in range(len(table[phase]))]

    return evaluate_panel


def test_the_sweep_reports_gains_and_losses_and_checks_reset():
    framework = TinyFramework()
    learner = _learner(framework=framework)
    payload = ml.depth_sweep(learner=learner, items=["ignored"],
                             evaluate_panel=stub_panel(framework=framework))
    report = payload["report"]
    assert report["tally"]["R2"] == {"gained": ["q2"], "lost": ["q1"],
                                     "gained_count": 1, "lost_count": 1, "net": 0,
                                     "compared_questions": 4}
    assert report["tally"]["R8"]["gained_count"] == 2
    assert report["tally"]["R8"]["lost_count"] == 2
    assert report["tally"]["R8"]["net"] == 0, (
        "eight passes fixed two and spoiled two: the net-zero result a pooled "
        "average would have hidden")
    assert report["reset_8_mechanism_check"]["identical_to_r1"] is True
    assert report["reset_8_mechanism_check"]["differing_items"] == []
    assert report["depth_selection"].startswith("none")
    assert payload["weights_unchanged"] is True
    assert payload["labels"] == ["R1", "R2", "R4", "R8", "RESET_8"]
    # the learner is left at the declared primary depth, not at the last label
    assert learner.depth == rc.PRIMARY_DEPTH
    assert learner.reset_each_pass is False


def test_the_reset_check_reports_a_difference_instead_of_tolerating_one():
    framework = TinyFramework()
    learner = _learner(framework=framework)
    table = dict(OUTCOMES, RESET_8=[True, True, False, True])
    payload = ml.depth_sweep(learner=learner, items=["ignored"],
                             evaluate_panel=stub_panel(table, framework=framework))
    check = payload["report"]["reset_8_mechanism_check"]
    assert check["identical_to_r1"] is False
    assert check["differing_items"] == ["q3"]
    assert "not a tolerated tolerance" in check["meaning"]


def test_the_sweep_measures_that_the_weights_did_not_move():
    framework = TinyFramework()
    learner = _learner(framework=framework)
    payload = ml.depth_sweep(
        learner=learner, items=["ignored"],
        evaluate_panel=stub_panel(framework=framework, bump_weight=True))
    assert payload["weights_unchanged"] is False, (
        "a sweep that changed a weight must say so, not assume it did not")
    assert payload["parameter_digest_before"] != payload["parameter_digest_after"]


def test_a_sweep_without_the_one_pass_baseline_is_refused():
    with pytest.raises(ValueError) as error:
        ml.sweep_report({"R8": [{"item_id": "q0", "is_correct": True}]})
    assert "SWEEP_REQUIRES_THE_ONE_PASS_BASELINE" in str(error.value)


# --------------------------------------------------------------------------
# 6. the boundaries
# --------------------------------------------------------------------------

def test_an_undeclared_depth_is_refused():
    learner = _learner(depth=1)
    for depth in (0, 3, 16, -1):
        with pytest.raises(ValueError) as error:
            learner.set_depth(depth)
        assert "RECURRENT_DEPTH_NOT_DECLARED" in str(error.value)
    with pytest.raises(ValueError) as error:
        _learner(depth=5)
    assert "RECURRENT_DEPTH_NOT_DECLARED" in str(error.value)


def test_there_is_still_no_way_to_let_a_checker_choose_the_depth():
    with pytest.raises(ValueError) as error:
        rc.select_best_depth({1: 0.4, 8: 0.9})
    assert "DEPTH_SELECTION_BY_CHECKER_IS_NOT_A_SUPPORTED_PATH" in str(error.value)
    learner = _learner(depth=4)
    assert not hasattr(learner, "select_best_depth")
    assert not hasattr(learner, "best_depth")


def test_the_learner_adds_no_trainable_parameters():
    from cas_meta2.graph_teaching.real_framework import GraphLearner
    framework = TinyFramework()
    one_pass = GraphLearner(torch, framework, list(TASKS), framework.device, 0.003)
    recurrent = ml.RecurrentGraphLearner(torch, framework, list(TASKS),
                                         framework.device, 0.003, depth=8)
    before = [name for name, _ in one_pass.module.named_parameters()]
    after = [name for name, _ in recurrent.module.named_parameters()]
    assert before == after
    assert len(list(recurrent.module.parameters())) == len(before)
    assert len(recurrent.optimizer.param_groups[0]["params"]) == len(before)
    assert recurrent.module is framework.module, (
        "the recurrence must share the ONE transformation, not build a second one")


def test_questions_do_not_contaminate_each_other():
    learner = _learner(depth=4)
    check = ml.state_isolation_check(learner=learner, position=1, other_position=3)
    assert check["repeatable"] is True
    assert check["order_independent"] is True
    assert check["a_borrowed_state_would_have_been_visible"] is True, (
        "if a borrowed state changed nothing, the isolation reading would be vacuous")
    assert check["depth"] == 4


def test_the_isolation_check_refuses_the_vacuous_setting():
    learner = _learner(depth=8, reset_each_pass=True)
    with pytest.raises(ValueError) as error:
        ml.state_isolation_check(learner=learner, position=1, other_position=3)
    assert "ISOLATION_CHECK_REQUIRES_A_CARRIED_STATE" in str(error.value)


# --------------------------------------------------------------------------
# 7. the numerical seam: one formula, two backends
# --------------------------------------------------------------------------

def test_the_tensor_path_agrees_with_the_reference_arithmetic():
    """The same loop on float64 tensors must reproduce the list reference exactly."""
    encoded_list = [1.0, -2.0, 3.0, 0.5]

    def core_list(vector):
        return [0.5 * value + 0.1 * (index + 1)
                for index, value in enumerate(vector)]

    expected = rc.run_passes(encoded_list, core_list, depth=8)

    def core_tensor(incoming):
        values = [float(value) for value in incoming]
        return list(torch.tensor([0.5 * value + 0.1 * (index + 1)
                                  for index, value in enumerate(values)],
                                 dtype=torch.float64))

    got = rc.run_passes(torch.tensor(encoded_list, dtype=torch.float64),
                        core_tensor, depth=8, cast=ml._keep,
                        zeros=lambda count: torch.zeros(count, dtype=torch.float64),
                        rms_fn=lambda values: ml.tensor_rms(torch, values))
    assert len(got) == len(expected) == 4
    for left, right in zip(got, expected):
        assert abs(float(left) - right) < 1e-12


def test_the_tensor_rms_refuses_plain_numbers_instead_of_promoting_them():
    """A state of plain floats is a state that left the graph. Say so."""
    with pytest.raises(ValueError) as error:
        ml.tensor_rms(torch, [0.0, 0.0, 0.0])
    assert "TENSOR_RMS_REQUIRES_TENSORS" in str(error.value)
    with pytest.raises(ValueError) as error:
        ml.tensor_rms(torch, [])
    assert "EMPTY" in str(error.value)


def test_the_tensor_rms_is_the_reference_rms():
    for values in ([1.0, -2.0, 3.0], [0.0, 0.0], [1e6, -1e6, 1e6]):
        tensor = torch.tensor(values, dtype=torch.float64)
        assert abs(ml.tensor_rms(torch, tensor) - rc.rms(values)) < 1e-9
        as_list = list(tensor)
        assert abs(ml.tensor_rms(torch, as_list) - rc.rms(values)) < 1e-9


def test_the_learner_report_states_its_scope():
    learner = _learner(depth=8, accounting=rc.Accounting())
    report = learner.depth_report()
    assert report["depth"] == 8
    assert report["reset_each_pass"] is False
    assert report["trainable_parameters"] == 3
    assert report["state_scope"].startswith("one fresh zero state per answer")



# --------------------------------------------------------------------------
# the compute label must equal the compute
# --------------------------------------------------------------------------

@pytest.mark.parametrize("depth", [1, 2, 4, 8])
def test_transformation_calls_counts_transformations_not_questions(depth):
    """At depth d, ONE question must report d transformation calls, not 1.

    The field used to be incremented once per passes() call - once per QUESTION -
    so at depth eight it reported 1 where eight transformations had run. Accounting
    was always right; this label was not, and a field named transformation_calls
    that silently counts questions is exactly the kind of number this project must
    not ship.
    """
    learner = _learner(depth=depth, framework=TinyFramework())
    encoded = learner._problem_vectors[0]
    with torch.no_grad():
        learner.value_at_depth(problem_vector=encoded)
    assert learner.transformation_calls == depth
    assert learner.questions_answered == 1
    report = learner.depth_report()
    assert report["transformation_calls"] == depth
    assert report["questions_answered"] == 1


def test_two_questions_at_depth_eight_report_sixteen_transformations():
    learner = _learner(depth=8, framework=TinyFramework())
    encoded = learner._problem_vectors[0]
    with torch.no_grad():
        learner.value_at_depth(problem_vector=encoded)
        learner.value_at_depth(problem_vector=encoded)
    assert learner.transformation_calls == 16
    assert learner.questions_answered == 2


def test_the_reported_transformation_calls_match_the_accounting(self=None):
    """The label and the ledger must agree: both count real core invocations."""
    accounting = rc.Accounting()
    learner = _learner(depth=4, framework=TinyFramework(), accounting=accounting)
    batch = list(learner.tasks[:2])
    ml.recurrent_batch_step(learner, batch)
    report = accounting.report()
    assert report["batched_core_forward_calls"] == 4      # one batched call per pass
    assert report["sample_level_core_passes"] == 8        # 4 passes x 2 questions
    assert report["optimizer_updates"] == 1
    # the learner counted one core invocation per question per pass
    assert learner.transformation_calls == 8
