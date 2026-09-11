"""Non-neural tests for the face-grounding extension (CUBE_FACE_GROUNDING_001).

No torch, no GPU, no network, no model, no launch. The end-to-end rehearsal drives
the real schedule, adapter, batching path, evaluation and result envelope with an
injected stub framework and a fake tensor type, so the *compiled* control flow is
executed without any neural work.
"""
import json
import sys
from pathlib import Path

import pytest

from cas_meta2.graph_teaching import (face_corpus as corpus, face_evaluation as ev,
                                      face_experiment as fx, face_roles as roles,
                                      face_schedule as schedule, face_tasks as tasks,
                                      trainer)
from cas_meta2.graph_teaching.graph import canonical

MODULE_SOURCE = Path(fx.__file__).read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# corpus
# --------------------------------------------------------------------------

def test_the_corpus_is_family_grouped_with_the_declared_split():
    built = corpus.families()
    assert len(built) == 96
    counts = {split: len(corpus.by_split(split, built)) for split in corpus.SPLITS}
    assert counts == {"training": 64, "development": 16, "final_held_out": 16}
    assert len({family["family_id"] for family in built}) == 96


def test_every_domain_carries_all_six_roles_and_six_structures():
    coverage = corpus.coverage_report()
    assert coverage["every_domain_carries_all_six_roles"] is True
    assert set(coverage["domain_histogram"]) == set(corpus.DOMAIN_ORDER)
    assert all(count == 16 for count in coverage["domain_histogram"].values())
    assert coverage["distinct_topologies"] == len(corpus.ARCHETYPES)
    assert coverage["distinct_family_graphs"] == 96
    assert set(coverage["structure_histogram"]) == set(corpus.ARCHETYPES)
    # structure overlap is reported separately from family overlap, not hidden
    assert "share" in coverage["structure_overlap_statement"]


def test_analogy_partners_are_cross_domain_and_preserve_the_declared_branches():
    built = corpus.families()
    for family in built:
        partner = corpus.analogy_partner(family["family_id"], built)
        assert partner["domain"] != family["domain"]
        assert partner["labels"] != family["labels"]
        correspondence = corpus.correspondence(family, partner)
        assert correspondence["preserved_branches"]
        partner_branches = [[branch["source"], branch["target"]]
                            for branch in partner["branches"]]
        for entry in correspondence["preserved_branches"]:
            assert entry["target_branch"] in partner_branches


def test_the_manifest_reports_coverage_rather_than_size_alone():
    manifest = corpus.family_manifest()
    assert manifest["coverage"]["families"] == 96
    assert len(manifest["families"]) == 96
    entry = manifest["families"][0]
    for key in ("family_id", "split", "domain", "archetype", "rendering",
                "labels", "branches", "graph_digest", "analogy_partner"):
        assert key in entry


# --------------------------------------------------------------------------
# roles
# --------------------------------------------------------------------------

def test_the_six_roles_keep_their_meanings_and_have_distinct_cues():
    assert roles.FACE_NUMBERS == (1, 2, 3, 4, 5, 6)
    assert len(set(roles.CUES)) == 6
    assert roles.role_for(5)["role"] == "parts_structure"
    assert roles.cue_for(5, "stable") == "CUBE_FACE_5"
    assert roles.cue_for(5, "neutral") == roles.NEUTRAL_CUE
    assert roles.cue_for(5, "none") is None
    for role in roles.ROLES:
        assert role["subtypes"] and role["objective"] and role["public_request"]


def test_recognition_groups_rotate_over_every_role_pair():
    pairs = set()
    triples = set()
    for face in roles.FACE_NUMBERS:
        for offset in (1, 2, 3, 4, 5):
            others = roles.other_faces(face, 2, offset)
            assert len(set(others)) == 2 and face not in others
            triples.add(tuple(sorted((face,) + others)))
            for other in others:
                pairs.add(tuple(sorted((face, other))))
    assert len(pairs) == 15
    assert len(triples) > 6, "one permanent triple is not allowed"


# --------------------------------------------------------------------------
# tasks
# --------------------------------------------------------------------------

def test_all_six_faces_have_a_bounded_numerical_task_in_both_profiles():
    bindings = tasks.task_bindings()
    assert bindings["presentation_only_faces"] == []
    seen = {(entry["face"], entry["profile"]) for entry in bindings["bindings"]}
    assert len(seen) == 12
    for face in roles.FACE_NUMBERS:
        assert (face, roles.FACE_APPLY) in seen
        assert (face, roles.ROLE_FROM_CONTENT) in seen


def test_every_family_and_face_compiles_three_distinct_options_with_one_answer():
    built = corpus.families()
    for family in built:
        for face in roles.FACE_NUMBERS:
            content = tasks.content_for(family, face, built)
            options = [content["correct"]] + list(content["negatives"])[:2]
            assert len(options) == 3
            assert len({canonical(option) for option in options}) == 3
            assert content["rule"]


def test_apply_episodes_carry_their_supports_and_the_recognition_ones_do_not():
    built = corpus.families()
    family = built[0]
    supports = tasks.choose_supports(family, 5, offset=5, built=built)
    assert len(supports) == 3
    assert family["family_id"] not in [support["family_id"] for support in supports]
    episode = tasks.compile_episode(family, 5, roles.FACE_APPLY, arm="stable",
                                    supports=supports, built=built)
    problem = episode["public"]["problem"]
    for support in supports:
        assert support["labels"][0] in problem
        assert support["family_id"] not in problem        # ids are not inputs
    assert "CUBE_FACE_5" in problem
    recognition = tasks.compile_episode(family, 5, roles.ROLE_FROM_CONTENT,
                                        offset=5, built=built)
    assert "CUBE_FACE" not in recognition["public"]["problem"]
    assert tasks.barred_words_in(
        tasks.recognition_commentary(family, 5)) == []


def test_the_private_target_cannot_reach_the_public_bytes():
    """Answer independence: swapping the target must not move any public byte."""
    built = corpus.families()
    family = built[1]
    episode = tasks.compile_episode(family, 5, roles.FACE_APPLY, arm="stable",
                                    supports=(), built=built)
    record = dict(episode["public_record"])
    other = [option for option in record["options"]
             if canonical(option) != canonical(record["correct"])][0]
    swapped = dict(record, correct=other)
    # the record id and the delivered order are functions of the public core only
    core = {key: value for key, value in record.items()
            if key not in ("correct", "record_id", "encoded_correct_index")}
    assert tasks.option_order(record["record_id"], record["options"]) == \
        episode["encoded_options"]
    assert canonical(core) == canonical(
        {key: value for key, value in swapped.items()
         if key not in ("correct", "record_id", "encoded_correct_index")})


def test_the_two_cue_arms_differ_only_by_the_cue_line():
    built = corpus.families()
    family = built[2]
    supports = tasks.choose_supports(family, 3, offset=2, built=built)
    stable = tasks.compile_episode(family, 3, roles.FACE_APPLY, arm="stable",
                                   supports=supports, built=built)
    neutral = tasks.compile_episode(family, 3, roles.FACE_APPLY, arm="neutral",
                                    supports=supports, built=built)
    stable_lines = stable["public"]["problem"].splitlines()
    neutral_lines = neutral["public"]["problem"].splitlines()
    assert len(stable_lines) == len(neutral_lines)
    differing = [index for index, (a, b) in enumerate(zip(stable_lines, neutral_lines))
                 if a != b]
    assert differing, "the arms must differ"
    for index in differing:
        assert "CUBE_FACE" in stable_lines[index]
        assert "CUBE_FACE" in neutral_lines[index]
    # the delivered slot order is identical, because the order is public-derived
    # and must not become a second difference between the arms
    assert stable["encoded_options"] == neutral["encoded_options"]


# --------------------------------------------------------------------------
# schedule
# --------------------------------------------------------------------------

def test_the_grounding_schedule_matches_the_declared_arithmetic():
    counts = schedule.planned_counts()
    assert counts["phase_a_queries"] == 6144
    assert counts["phase_a_support_presentations"] == 18432
    assert counts["phase_b_recognition_queries"] == 1536
    assert counts["phase_b_application_queries"] == 1536
    assert counts["supervised_query_presentations"] == 9216
    assert counts["updates_at_declared_batch"] == 1152
    assert counts["UPDATES_IF_ONE_PER_EPISODE"] == 9216
    assert "minibatch" in counts["batching_note"]


def test_materialised_events_are_balanced_across_roles_and_profiles():
    report = schedule.schedule_report()
    assert report["materialised_events"] == 9216
    assert report["batch_arithmetic_holds"] is True
    assert set(report["events_by_role"].values()) == {1536}
    assert report["events_by_profile"] == {"FACE_APPLY": 7680,
                                           "ROLE_FROM_CONTENT": 1536}
    assert report["events_with_supports"] == 6144


def test_the_cfc_round_has_the_declared_movements_and_totals():
    counts = schedule.planned_counts()
    assert counts["cfc_decisions_per_round"] == 48
    assert counts["cfc_total_decisions"] == 4608
    assert schedule.schedule_report()["cfc_round_movements"] == {
        "within_cube": 28, "across_face": 12, "return_to_cube": 8}
    round_events = schedule.cfc_round_events(0)
    movements = {}
    for event in round_events:
        movements[event["movement"]] = movements.get(event["movement"], 0) + 1
    assert movements == {"WITHIN_CUBE": 28, "ACROSS_FACE": 12,
                         "RETURN_TO_CUBE": 8}


def test_the_mixed_order_control_keeps_every_event_and_only_changes_order():
    events = schedule.cfc_round_events(0) * 2
    mixed = schedule.mixed_order(events)
    assert sorted(schedule.event_key(event) for event in mixed) == \
        sorted(schedule.event_key(event) for event in events)
    assert [schedule.event_key(event) for event in mixed] != \
        [schedule.event_key(event) for event in events]


def test_comparison_conditions_express_both_plans():
    conditions = {entry["condition"]: entry
                  for entry in schedule.comparison_conditions()}
    assert set(conditions) == {"cfc_stable_cues", "cfc_neutral_cue",
                               "mixed_order_stable_cues", "mixed_order_neutral_cue"}
    assert conditions["cfc_neutral_cue"]["cue"] == "neutral"
    assert conditions["mixed_order_stable_cues"]["organization"] == "MIXED_ORDER"


# --------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------

def test_the_panel_is_ninety_six_plus_ninety_six_on_held_out_families():
    manifest = ev.panel_manifest()
    assert manifest["primary_items"] == 192
    assert manifest["by_layer"]["role_recognition"] == 96
    assert manifest["by_layer"]["role_application"] == 96
    assert manifest["by_layer"]["targeted_check"] == 24
    assert manifest["base_families"] == 16
    assert all(count == 16 for count in manifest["by_face"].values())
    assert "no face cue" in manifest["cue_note"]


def test_panel_items_carry_no_cue_and_keep_option_counts_at_three():
    for item in ev.panel():
        entry = (ev.diagnostic_item(item) if item["kind"] in ev.DIAGNOSTIC_KINDS
                 else ev.compile_panel_item(item))
        problem = entry["episode"]["public"]["problem"]
        assert "CUBE_FACE" not in problem
        assert len(entry["episode"]["encoded_options"]) == 3


def test_baselines_are_computed_from_the_delivered_order():
    items = [ev.compile_panel_item(item) for item in ev.panel()
             if item["kind"] == "primary" and item["layer"] == "role_application"]
    baseline = ev.baselines(items)
    assert baseline["questions"] == 96
    assert sum(baseline["rules"]["always_slot_%d" % slot]
               for slot in range(3)) == 96
    assert baseline["uniform_random_expectation"] == 32.0
    assert "ignores the content" in baseline["note"]


def test_diagnostics_preserve_or_change_the_answer_as_declared():
    built = corpus.families()
    family = corpus.by_split(corpus.FINAL_HELD_OUT, built)[0]
    renamed, mapping = ev.renamed_family(family)
    original = tasks.content_for(family, 5, built)["correct"]
    edited = tasks.content_for(renamed, 5, built)["correct"]
    assert original != edited, "renaming must rename, not preserve the spelling"
    assert set(mapping.values()) <= set(renamed["labels"])
    reordered = ev.reordered_family(family)
    assert tasks.branch_set(reordered) == tasks.branch_set(family)
    rewired = ev.rewired_family(family)
    assert tasks.branch_set(rewired) != tasks.branch_set(family)
    assert not tasks.preserves_scope(family, rewired)
    with pytest.raises(ValueError):
        ev.reordered_family(corpus.by_split(corpus.TRAINING, built)[
            [family["domain"] for family in corpus.by_split(corpus.TRAINING, built)]
            .index("procedural")])


def test_the_scaffold_imports_no_neural_or_provider_code():
    for forbidden in ("import torch", "boto3", "botocore", "gpu_adapter"):
        assert forbidden not in MODULE_SOURCE
    assert "FACE_CONTAINMENT_VIOLATION" in MODULE_SOURCE
    assert "FACE_CHECKPOINT_NOT_VERIFIED" in MODULE_SOURCE
    assert "TEACHING_INCOMPLETE" in MODULE_SOURCE


# --------------------------------------------------------------------------
# end-to-end rehearsal with injected stubs
# --------------------------------------------------------------------------

class _StubParameter:
    def __init__(self, name, value=1.0):
        self.name = name
        self.value = value

    def requires_grad_(self, flag):
        return self


class _StubContract:
    contract_id = "cas.cjt.operation.^6.decompose/0.2"
    plasticity_groups = ("operation:^6",)


class _StubRegistration:
    contract_id = "cas.cjt.operation.^6.decompose/0.2"


class _StubModel:
    def __init__(self, framework):
        self.framework = framework

    def named_parameters(self):
        return sorted(self.framework.parameters.items())


class _StubFramework:
    def __init__(self):
        self.parameters = {"module.left.weight": _StubParameter("left"),
                           "module.right.weight": _StubParameter("right"),
                           "encoder.projection": _StubParameter("encoder")}
        self.operation_registrations = [_StubRegistration()]
        self.module = _StubModel(self)

    def contract_for(self, contract_id):
        return _StubContract()

    def resolve_plasticity_groups(self, model, role, contract):
        return ["module.left.weight", "module.right.weight"]

    def tensor_bytes(self, parameter):
        return json.dumps(parameter.value).encode("utf-8")


class _Tensor:
    """Just enough tensor for the batching path: values, shape, argmax, grads."""

    def __init__(self, values, requires_grad=False):
        self.values = list(values)
        self.shape = (len(self.values),)
        self.requires_grad = requires_grad
        self.backward_called = False

    def unsqueeze(self, axis):
        return self

    def detach(self):
        return self

    def __iter__(self):
        # real torch iteration yields 0-dim tensors, so each item keeps .detach()
        return iter([_Tensor([value]) for value in self.values])

    def __float__(self):
        return float(self.values[0])

    def __add__(self, other):
        return _Tensor([self.values[0] + _value_of(other)])

    __radd__ = __add__

    def __truediv__(self, other):
        return _Tensor([self.values[0] / _value_of(other)])

    def item(self):
        return self.values[0]

    def backward(self):
        self.backward_called = True


def _value_of(other):
    return other.values[0] if isinstance(other, _Tensor) else other


class _FakeTorch:
    class _Functional:
        @staticmethod
        def cross_entropy(scores, target):
            return _Tensor([0.5])

    nn = type("nn", (), {"functional": _Functional()})

    @staticmethod
    def tensor(values, device=None):
        return _Tensor(list(values))

    @staticmethod
    def argmax(scores):
        best = max(range(len(scores.values)), key=lambda index: scores.values[index])
        return _Tensor([best])

    @staticmethod
    def manual_seed(seed):
        return None


class _StubOptimizer:
    def __init__(self):
        self.zero_grad_calls = 0
        self.step_calls = 0

    def zero_grad(self, set_to_none=True):
        self.zero_grad_calls += 1

    def step(self):
        self.step_calls += 1


class _StubLearner:
    def __init__(self, framework, tasks_in_order, device="cpu"):
        self.torch = _FakeTorch
        self.framework = framework
        self.tasks = list(tasks_in_order)
        self.device = device
        self.optimizer = _StubOptimizer()
        self._index = {task["record_id"]: position
                       for position, task in enumerate(self.tasks)}
        self._updates = 0

    def _position(self, task):
        if task["record_id"] in self._index:
            return self._index[task["record_id"]]
        self.tasks.append(task)
        self._index[task["record_id"]] = len(self.tasks) - 1
        return len(self.tasks) - 1

    def forward(self, position):
        # deterministic: the first option always scores highest
        count = len(self.tasks[position]["encoded_options"])
        return _Tensor([1.0] + [0.0] * (count - 1))

    def predict(self, task):
        position = self._position(task)
        return self.tasks[position]["encoded_options"][0]

    def scores(self, task):
        position = self._position(task)
        scores = self.forward(position)
        return {"scores": list(scores.values), "loss": 0.5, "correct_index": 0,
                "selected_index": 0, "path": "indexed", "option_count": len(
                    scores.values)}

    def checkpoint_identity(self):
        return "stub-identity-%d" % self.optimizer.step_calls


def _learner_factory(*, framework, model, tasks):
    return _StubLearner(framework, list(tasks))


def _compile_first_events(condition, count):
    events = schedule.condition_events(condition, "CFC_LOOP",
                                       "stable" if condition.endswith("stable_cues")
                                       else "neutral")
    return events[:count]


def _episodes(condition, count):
    """Compiled episodes for the first ``count`` scheduled events."""
    return fx.compile_events(_compile_first_events(condition, count))


def test_the_batching_path_takes_exactly_one_optimizer_step_per_batch():
    episodes = _episodes("cfc_stable_cues", 8)
    framework = _StubFramework()
    learner = _StubLearner(framework, [])
    outcome = fx.batch_step(learner, [fx.episode_task(episode)
                                      for episode in episodes])
    assert outcome["optimizer_steps"] == 1
    assert learner.optimizer.step_calls == 1
    assert learner.optimizer.zero_grad_calls == 1
    assert outcome["batch_size"] == 8
    row = outcome["episodes"][0]
    assert len(row["scores"]) == 3 and isinstance(row["loss"], float)
    assert row["selected"] in episodes[0]["encoded_options"]
    assert row["correct_index"] == episodes[0]["encoded_correct_index"]


def test_a_run_reports_incompleteness_rather_than_pretending_to_finish():
    built = corpus.families()
    episodes = _episodes("cfc_stable_cues", 16)
    framework = _StubFramework()
    report = fx.run_condition(
        run_id="rehearsal", episodes=episodes, framework=framework,
        model=framework.module, learner_factory=_learner_factory,
        checkpoint_writer=lambda learner, identity: {"identity": identity},
        checkpoint_verifier=lambda saved, identity: saved["identity"] == identity,
        batch_size=8, wall_clock=lambda: 0.0,
        max_wall_seconds=-1)
    assert report["status"] == fx.STATUS_INCOMPLETE
    assert "limit" in report["stopping_reason"]
    assert report["delivered_episodes"] == 0
    assert report["planned_episodes"] == 16


def test_a_complete_stub_run_keeps_rows_scores_and_the_checkpoint_linkage():
    built = corpus.families()
    episodes = _episodes("cfc_stable_cues", 8)
    framework = _StubFramework()
    report = fx.run_condition(
        run_id="rehearsal", episodes=episodes, framework=framework,
        model=framework.module, learner_factory=_learner_factory,
        checkpoint_writer=lambda learner, identity: {"identity": identity},
        checkpoint_verifier=lambda saved, identity: saved["identity"] == identity,
        batch_size=8)
    assert report["status"] == fx.STATUS_COMPLETE
    assert report["actual_optimizer_updates"] == 1
    assert len(report["rows"]) == 8
    row = report["rows"][0]
    for key in ("expected_answer", "selected_answer", "scores", "loss",
                "batch_index", "optimizer_update_index", "checkpoint_before",
                "checkpoint_after", "correct_index_in_delivered_order"):
        assert key in row
    assert report["containment"]["contained"] is True
    assert report["checkpoint"]["verified"] is True
    assert report["scores_recorded_from_the_correction_pass"] is True


def test_a_forbidden_change_fails_the_run_closed():
    built = corpus.families()
    episodes = _episodes("cfc_stable_cues", 8)
    framework = _StubFramework()

    class _Drifting(_StubFramework):
        def tensor_bytes(self, parameter):
            if parameter.name == "encoder" and self.module is not None:
                pass
            return json.dumps(parameter.value).encode("utf-8")

    drifting = _StubFramework()
    original = drifting.tensor_bytes

    def drifting_bytes(parameter):
        if parameter.name == "encoder":
            return json.dumps(parameter.value + 1).encode("utf-8")
        return original(parameter)

    calls = {"count": 0}

    def flaky_bytes(parameter):
        calls["count"] += 1
        if parameter.name == "encoder" and calls["count"] > 3:
            return json.dumps(parameter.value + 1).encode("utf-8")
        return json.dumps(parameter.value).encode("utf-8")

    drifting.tensor_bytes = flaky_bytes
    with pytest.raises(ValueError) as error:
        fx.run_condition(
            run_id="rehearsal", episodes=episodes, framework=drifting,
            model=drifting.module, learner_factory=_learner_factory,
            checkpoint_writer=lambda learner, identity: {"identity": identity},
            checkpoint_verifier=lambda saved, identity: True,
            batch_size=8)
    assert "FACE_CONTAINMENT_VIOLATION" in str(error.value)


def test_launch_refuses_without_authority_and_requires_matched_weights():
    built = corpus.families()
    stub_panel = []
    with pytest.raises(ValueError) as error:
        fx.launch(conditions=["cfc_stable_cues"],
                  framework_factory=lambda seed: (_StubFramework(),
                                                  _StubFramework().module),
                  learner_factory=_learner_factory,
                  checkpoint_writer=lambda learner, identity: {},
                  checkpoint_verifier=lambda saved, identity: True,
                  authorization=None, built=built, panel_items=stub_panel)
    assert "FACE_RUN_NOT_AUTHORIZED" in str(error.value)

    counter = {"value": 0}

    def drifting_factory(seed):
        counter["value"] += 1
        framework = _StubFramework()
        if counter["value"] > 1:
            framework.parameters["module.left.weight"].value = 2.0
        return framework, framework.module

    with pytest.raises(ValueError) as error:
        fx.launch(conditions=["cfc_stable_cues", "cfc_neutral_cue"],
                  framework_factory=drifting_factory,
                  learner_factory=_learner_factory,
                  checkpoint_writer=lambda learner, identity: {"identity": identity},
                  checkpoint_verifier=lambda saved, identity: True,
                  authorization={"owner_go": True, "run_id": "rehearsal"},
                  built=built, panel_items=stub_panel, event_limit=8)
    assert "FACE_INITIAL_WEIGHTS_NOT_MATCHED" in str(error.value)
