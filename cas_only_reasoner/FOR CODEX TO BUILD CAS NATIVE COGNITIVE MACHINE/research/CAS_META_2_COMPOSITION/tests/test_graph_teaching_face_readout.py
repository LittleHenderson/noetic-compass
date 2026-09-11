"""Non-neural tests for the CFC-pilot readout (recovering attempt 004's detail).

No torch, no GPU, no network, no AWS, no reservation. The readout's control flow is
driven with stub factories and a numpy-backed fake tensor type, so the zero-update
guarantee and the recovery gate are executed rather than asserted in prose.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from cas_meta2.graph_teaching import face_corpus as corpus
from cas_meta2.graph_teaching import face_evaluation as ev
from cas_meta2.graph_teaching import face_readout as ro

MODULE_SOURCE = Path(ro.__file__).read_text(encoding="utf-8")
CONDITIONS = ["cfc_stable_cues", "cfc_neutral_cue", "mixed_order_stable_cues",
              "mixed_order_neutral_cue"]
CHECKPOINT_DIR = "records/place/checkpoints"
HASHES = {name: hashlib.sha256(name.encode()).hexdigest() for name in CONDITIONS}


def _config(**extra):
    config = {"schema": "cas.cube-face-readout-config/1", "job": "rehearsal",
              "condition_order": list(CONDITIONS),
              "conditions": {name: {"checkpoint": "checkpoint_%s.pt" % name,
                                    "sha256": HASHES[name]}
                             for name in CONDITIONS},
              "checkpoint_dir": CHECKPOINT_DIR,
              "expected_totals": {name: {"role_application": {"correct": 1, "total": 2}}
                                  for name in CONDITIONS}}
    config.update(extra)
    return config


# --------------------------------------------------------------------------
# plan
# --------------------------------------------------------------------------

def test_the_plan_binds_the_four_delivered_conditions_and_the_panel():
    built, conditions, panel, plan = ro.compile_plan(_config())
    assert [entry["condition"] for entry in conditions] == CONDITIONS
    assert [entry["cue"] for entry in conditions] == ["stable", "neutral",
                                                      "stable", "neutral"]
    assert [entry["organization"] for entry in conditions] == ["CFC_LOOP", "CFC_LOOP",
                                                               "MIXED_ORDER",
                                                               "MIXED_ORDER"]
    assert plan["panel"]["primary_items"] == 192
    assert plan["panel"]["by_layer"] == {"role_application": 96,
                                         "role_recognition": 96,
                                         "targeted_check": 24}
    assert plan["optimizer_updates"] == 0 and plan["training"] is False
    assert len(plan["declared_pairs"]) == 4
    assert len(panel) == 216


def test_the_plan_refuses_a_missing_checkpoint_directory_or_unknown_condition():
    with pytest.raises(ValueError) as error:
        ro.compile_plan({key: value for key, value in _config().items()
                         if key != "checkpoint_dir"})
    assert "READOUT_CHECKPOINT_DIR_REQUIRED" in str(error.value)

    config = _config()
    config["condition_order"] = list(CONDITIONS) + ["no_such_condition"]
    config["conditions"]["no_such_condition"] = {"checkpoint": "x.pt",
                                                 "sha256": "a" * 64}
    with pytest.raises(ValueError) as error:
        ro.compile_plan(config)
    assert "READOUT_CONDITION_UNKNOWN" in str(error.value)

    config = _config()
    del config["conditions"]["cfc_stable_cues"]["sha256"]
    with pytest.raises(ValueError) as error:
        ro.compile_plan(config)
    assert "READOUT_CHECKPOINT_SHA_REQUIRED" in str(error.value)


# --------------------------------------------------------------------------
# the checkpoint gate
# --------------------------------------------------------------------------

class _Tensor:
    def __init__(self, values):
        self.array = np.asarray(values, dtype="float64")

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.array


class _FakeCheckpointTorch:
    """Enough of ``torch`` to load a checkpoint-shaped object, and nothing more."""

    def __init__(self, payload):
        self.payload = payload
        self.loads = []

    def load(self, path, map_location=None, weights_only=None):
        self.loads.append({"path": str(path), "map_location": map_location,
                           "weights_only": weights_only})
        return self.payload


def _write_checkpoint(tmp_path, name="checkpoint_cfc_stable_cues.pt", *, state=None,
                      order=("module.weight",), identity=None, condition="cfc_stable_cues",
                      schema="cas.cube-face-checkpoint/1"):
    state = {"module.weight": _Tensor([1.0, 2.0])} if state is None else state
    if identity is None:
        from cas_meta2.graph_teaching import face_worker as worker
        identity = worker._state_digest(state, list(order))
    payload = {"schema": schema, "condition": condition, "identity": identity,
               "parameter_order": list(order), "state": state}
    path = tmp_path / name
    path.write_bytes(b"checkpoint bytes")
    return path, payload


def test_a_checkpoint_is_used_only_when_its_file_hash_and_its_identity_agree(tmp_path):
    path, payload = _write_checkpoint(tmp_path)
    loaded = ro.load_verified(torch=_FakeCheckpointTorch(payload), path=path,
                              expected_sha256=ro.sha256_file(path),
                              condition="cfc_stable_cues")
    assert loaded["identity"] == payload["identity"]
    assert loaded["bytes"] == path.stat().st_size
    assert loaded["state"] is payload["state"]


def test_a_changed_checkpoint_file_fails_closed_before_it_is_read(tmp_path):
    path, payload = _write_checkpoint(tmp_path)
    fake = _FakeCheckpointTorch(payload)
    with pytest.raises(ValueError) as error:
        ro.load_verified(torch=fake, path=path, expected_sha256="b" * 64,
                         condition="cfc_stable_cues")
    assert "READOUT_CHECKPOINT_HASH" in str(error.value)
    assert fake.loads == [], "the file was read despite failing its hash"


def test_a_checkpoint_whose_tensors_do_not_match_its_recorded_identity_is_refused(tmp_path):
    path, payload = _write_checkpoint(tmp_path)
    payload["state"] = {"module.weight": _Tensor([9.0, 9.0])}
    with pytest.raises(ValueError) as error:
        ro.load_verified(torch=_FakeCheckpointTorch(payload), path=path,
                         expected_sha256=ro.sha256_file(path),
                         condition="cfc_stable_cues")
    assert "READOUT_CHECKPOINT_IDENTITY_MISMATCH" in str(error.value)


def test_a_checkpoint_for_another_condition_or_schema_is_refused(tmp_path):
    path, payload = _write_checkpoint(tmp_path, condition="cfc_neutral_cue")
    with pytest.raises(ValueError) as error:
        ro.load_verified(torch=_FakeCheckpointTorch(payload), path=path,
                         expected_sha256=ro.sha256_file(path),
                         condition="cfc_stable_cues")
    assert "READOUT_CHECKPOINT_CONDITION" in str(error.value)

    path, payload = _write_checkpoint(tmp_path, name="second.pt",
                                      schema="something-else")
    with pytest.raises(ValueError) as error:
        ro.load_verified(torch=_FakeCheckpointTorch(payload), path=path,
                         expected_sha256=ro.sha256_file(path),
                         condition="cfc_stable_cues")
    assert "READOUT_CHECKPOINT_SCHEMA" in str(error.value)


def test_a_missing_checkpoint_is_refused_rather_than_skipped(tmp_path):
    with pytest.raises(ValueError) as error:
        ro.load_verified(torch=_FakeCheckpointTorch({}), path=tmp_path / "absent.pt",
                         expected_sha256="c" * 64, condition="cfc_stable_cues")
    assert "READOUT_CHECKPOINT_MISSING" in str(error.value)


# --------------------------------------------------------------------------
# the panel is compiled once and answered without updates
# --------------------------------------------------------------------------

class _Module:
    """A module whose parameters are plain numpy-backed tensors."""

    def __init__(self, values, *, ignore_loads=False, drift_after=None):
        self.values = dict(values)
        self.ignore_loads = ignore_loads
        self.drift_after = drift_after
        self.reads = 0

    def named_parameters(self):
        return [(name, _Tensor(value)) for name, value in sorted(self.values.items())]

    def state_dict(self):
        self.reads += 1
        if self.drift_after is not None and self.reads > self.drift_after:
            self.values = {name: [value[0] + 1.0] + list(value[1:])
                           for name, value in self.values.items()}
        return {name: _Tensor(value) for name, value in sorted(self.values.items())}

    def load_state_dict(self, state):
        if self.ignore_loads:
            return
        self.values = {name: list(tensor.array) for name, tensor in state.items()}


class _Learner:
    def __init__(self, module, tasks):
        self.module = module
        self.tasks = tasks
        self.device = "cpu"
        self.condition_tag = None
        self.torch = None
        self.optimizer = _Optimizer()
        self.calls = 0

    def predict(self, task):
        return task["encoded_options"][0]

    def scores(self, task):
        self.calls += 1
        return {"scores": [0.5, 0.25, 0.25], "loss": 0.5,
                "correct_index": task["encoded_correct_index"], "selected_index": 0}


class _Optimizer:
    def __init__(self):
        self.steps = 0

    def step(self):
        self.steps += 1

    def zero_grad(self, **kwargs):
        return None


def _rig(*, ignore_loads=False, drift_after=None, order=("module.left.weight",
                                                         "module.right.weight")):
    """A stratified small panel: a truncated head would never reach the diagnostics.

    The same lesson as the worker smoke: a slice of the panel contains only primary
    items, so a readout that mishandled the 24 diagnostics would pass unnoticed.
    """
    built = corpus.families()
    full = ev.panel(built)
    diagnostics = [item for item in full if item["kind"] in ev.DIAGNOSTIC_KINDS]
    small = full[:4] + diagnostics[:2]
    assert len(small) == 6, small
    entries, tasks = ro.panel_entries(built, small)
    state = {name: _Tensor([1.0, 2.0, 3.0]) for name in order}
    from cas_meta2.graph_teaching import face_worker as worker
    identity = worker._state_digest(state, list(order))
    # the rebuilt module starts away from the trained weights, so a module that
    # silently ignores the load is detected rather than accidentally matching
    module = _Module({name: [0.0, 0.0, 0.0] for name in order},
                     ignore_loads=ignore_loads, drift_after=drift_after)
    learner = _Learner(module, tasks)

    def framework_factory(torch, device, encoder, config):
        return object(), object()

    def learner_factory(torch, framework, model, tasks_in, device, learning_rate):
        learner.tasks = tasks_in
        return learner

    loaded = {"state": state, "identity": identity, "parameter_order": list(order),
              "sha256": "d" * 64, "bytes": 123}
    spec = {"condition": "cfc_stable_cues", "organization": "CFC_LOOP", "cue": "stable",
            "checkpoint": "checkpoint_cfc_stable_cues.pt", "sha256": "d" * 64}
    return {"built": built, "panel": small, "tasks": tasks, "loaded": loaded,
            "spec": spec, "framework_factory": framework_factory,
            "learner_factory": learner_factory, "learner": learner,
            "entries": entries, "identity": identity}


def _read(rig, **overrides):
    arguments = {"condition_spec": rig["spec"], "built": rig["built"],
                 "panel": rig["panel"], "tasks": rig["tasks"], "encoder": object(),
                 "torch": None, "device": "cpu", "config": {"seed": 20260912},
                 "loaded": rig["loaded"],
                 "framework_factory": rig["framework_factory"],
                 "learner_factory": rig["learner_factory"]}
    arguments.update(overrides)
    return ro.read_condition(**arguments)


def test_a_readout_answers_the_panel_and_measures_that_nothing_changed():
    rig = _rig()
    report = _read(rig)
    assert report["optimizer_updates"] == 0
    assert report["parameters_unchanged_by_readout"] is True
    assert report["parameter_digest_trained"] == rig["identity"]
    assert report["parameter_digest_after_readout"] == rig["identity"]
    assert report["parameter_digest_rebuilt_initial"] != rig["identity"], \
        "the stub rebuild must differ from the trained weights for this test to bite"
    assert report["checkpoint"]["identity_recomputed_in_place"] == rig["identity"]
    assert rig["learner"].optimizer.steps == 0, "an optimizer step was taken"
    assert rig["learner"].calls == 12, "each question must be answered twice"
    assert len(report["before_rows"]) == 6 and len(report["after_rows"]) == 6
    for row in report["after_rows"]:
        for key in ("item_id", "layer", "face", "expected_answer", "selected_answer",
                    "is_correct", "scores", "correct_index_in_delivered_order"):
            assert key in row
    assert set(report["layers"]["layers"]) == {"role_application", "role_recognition",
                                               "targeted_check"}
    assert "macro_accuracy" in report["layers"]["layers"]["role_application"]
    assert "before_after" in report["layers"]
    assert report["milestone"]["role_application_target"] == 0.70
    assert report["totals"]["role_application"]["total"] == 2
    assert report["totals"]["role_recognition"]["total"] == 2
    assert report["totals"]["targeted_check"]["total"] == 2
    assert "reconstructed initial" in report["boundary"]["before_readings"]
    kinds = {row["kind"] for row in report["after_rows"]}
    assert kinds & set(ev.DIAGNOSTIC_KINDS), kinds


def test_a_module_that_changes_during_the_readout_fails_closed():
    rig = _rig(drift_after=1)          # the digest after the before-pass differs
    with pytest.raises(ValueError) as error:
        _read(rig)
    assert "READOUT_UPDATED_DURING_BEFORE" in str(error.value)


def test_a_module_that_changes_after_the_checkpoint_is_loaded_fails_closed():
    rig = _rig(drift_after=3)          # the digest after the after-pass differs
    with pytest.raises(ValueError) as error:
        _read(rig)
    assert "READOUT_UPDATED_DURING_AFTER" in str(error.value)


def test_a_module_that_does_not_take_the_checkpoint_fails_closed():
    rig = _rig(ignore_loads=True)
    with pytest.raises(ValueError) as error:
        _read(rig)
    assert "READOUT_LOADED_IDENTITY" in str(error.value)


def test_a_rebuilt_module_with_a_different_parameter_order_fails_closed():
    rig = _rig(order=("module.left.weight", "module.other.weight"))
    rig["loaded"]["parameter_order"] = ["module.left.weight", "module.right.weight"]
    with pytest.raises(ValueError) as error:
        _read(rig)
    assert "READOUT_PARAMETER_ORDER_CHANGED" in str(error.value)


# --------------------------------------------------------------------------
# the recovery gate
# --------------------------------------------------------------------------

def _totals(correct=76, total=96):
    return {"totals": {"role_application": {"correct": correct, "total": total,
                                            "accuracy": correct / total}}}


def test_the_recovery_reports_a_mismatch_instead_of_presenting_new_numbers():
    plan = {"expected_totals": {"cfc_stable_cues":
                                {"role_application": {"correct": 76, "total": 96}}}}
    matched = ro.reproduction_check({"cfc_stable_cues": _totals()}, plan)
    assert matched["reproduced"] is True and matched["mismatches"] == []
    assert matched["checked"] == 1

    drifted = ro.reproduction_check({"cfc_stable_cues": _totals(correct=75)}, plan)
    assert drifted["reproduced"] is False
    assert drifted["mismatches"] == [{"condition": "cfc_stable_cues",
                                      "layer": "role_application",
                                      "recomputed": {"correct": 75, "total": 96,
                                                     "accuracy": 75 / 96},
                                      "published": {"correct": 76, "total": 96}}]
    assert "failed recovery" in drifted["gate"]


def test_the_recovery_gate_refuses_to_run_with_nothing_to_check_against():
    with pytest.raises(ValueError) as error:
        ro.reproduction_check({"cfc_stable_cues": _totals()}, {})
    assert "READOUT_EXPECTED_TOTALS_REQUIRED" in str(error.value)

    with pytest.raises(ValueError) as error:
        ro.reproduction_check({"cfc_stable_cues": _totals()},
                              {"expected_totals": {"other": {}}})
    assert "READOUT_EXPECTED_TOTALS_MISSING" in str(error.value)


# --------------------------------------------------------------------------
# the zero-update guarantee is structural, not just asserted
# --------------------------------------------------------------------------

def test_the_readout_module_contains_no_training_path_at_all():
    """A future edit that adds training to the readout must fail this suite."""
    for forbidden in ("batch_step", "run_condition", "optimizer.step", ".step()",
                      "loss.backward", "backward()", "trainer.", "torch.save",
                      "import torch", "condition_events"):
        assert forbidden not in MODULE_SOURCE, forbidden
    # the zero-update claim is measured per condition, not merely stated once
    assert "parameters_unchanged_by_readout" in MODULE_SOURCE
    assert "READOUT_UPDATED_DURING_BEFORE" in MODULE_SOURCE
    assert "READOUT_UPDATED_DURING_AFTER" in MODULE_SOURCE


# --------------------------------------------------------------------------
# delivery
# --------------------------------------------------------------------------

def _report(readouts=None, reproduced=True):
    readouts = readouts or {
        "cfc_stable_cues": {
            "checkpoint": {"sha256": "e" * 64, "identity": "f" * 64, "bytes": 10},
            "parameters_unchanged_by_readout": True,
            "totals": {"role_application": {"correct": 76, "total": 96,
                                            "accuracy": 76 / 96}},
            "milestone": {"role_application_met": True}}}
    return {"readouts": readouts,
            "reproduction": {"checked": 1, "mismatches": [], "reproduced": reproduced,
                             "gate": "..."},
            "paired": {"role_application|cfc_stable_cues|mixed_order_stable_cues":
                       {"only_first_correct": 3, "only_second_correct": 1,
                        "discordant_pairs": 4}},
            "baselines": {"role_application": {"questions": 96}},
            "panel": {"items": 216, "by_layer": {"role_application": 96},
                      "note": ro.PANEL_NOTE},
            "boundary": {"no_optimizer_step": True},
            "conditions": []}


def test_delivery_declares_both_payloads_so_collection_cannot_drop_them(tmp_path):
    results = tmp_path / "results"
    artifacts = results / "artifacts"
    artifacts.mkdir(parents=True)
    plan = {"corpus_digest": "a" * 64, "expected_totals": {}, "panel": {}}
    report = ro.deliver(results=results, artifacts=artifacts, job="job-readout",
                        plan=plan, report=_report())
    declared = [entry["name"] for entry in report["artifacts"]]
    assert sorted(declared) == ["measurements.json", "readout.json"], declared
    envelope = report["envelope"]
    assert envelope["status"] == ro.STATUS_COMPLETE
    assert envelope["failure"] is None
    assert envelope["optimizer_updates"] == 0 and envelope["training_performed"] is False
    assert [entry["name"] for entry in envelope["artifacts"]] == declared
    assert envelope["measurements_sha256"] == ro.sha256_file(
        results / "measurements.json")
    for entry in report["artifacts"]:
        path = artifacts / entry["name"]
        assert entry["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = json.loads((artifacts / "manifest.json").read_bytes())
    assert [entry["name"] for entry in manifest["artifacts"]] == declared
    assert (artifacts / "measurements.json").read_bytes() == \
        (results / "measurements.json").read_bytes()
    payload = json.loads((artifacts / "readout.json").read_bytes())
    assert payload["readout"]["reproduction"]["reproduced"] is True
    assert (results / "result.json.sha256").read_text().strip() == \
        hashlib.sha256((results / "result.json").read_bytes()).hexdigest()


def test_a_failed_recovery_is_delivered_as_a_failure_never_as_the_result(tmp_path):
    results = tmp_path / "results"
    artifacts = results / "artifacts"
    artifacts.mkdir(parents=True)
    report = ro.deliver(results=results, artifacts=artifacts, job="job-readout",
                        plan={"corpus_digest": "a" * 64}, report=_report(
                            reproduced=False))
    envelope = report["envelope"]
    assert envelope["status"] == ro.STATUS_FAILED
    assert envelope["failure"]["message"] == \
        "READOUT_DOES_NOT_REPRODUCE_THE_DELIVERED_TOTALS"
    assert envelope["artifacts"], "the evidence is still declared for collection"


def test_run_drives_the_whole_flow_with_an_injected_readout(tmp_path):
    results = tmp_path / "results"
    artifacts = results / "artifacts"
    artifacts.mkdir(parents=True)
    seen = {}

    def stub_readout(config, *, torch, device, built, conditions, panel, plan, root):
        seen.update({"conditions": [entry["condition"] for entry in conditions],
                     "root": str(root), "updates": plan["optimizer_updates"],
                     "items": len(panel)})
        return _report()

    report = ro.run(_config(), torch=None, device="cpu", results=results,
                    artifacts=artifacts, root=tmp_path, readout=stub_readout)
    assert seen["conditions"] == CONDITIONS
    assert seen["updates"] == 0 and seen["items"] == 216
    assert report["envelope"]["status"] == ro.STATUS_COMPLETE
    assert len(report["artifacts"]) == 2


def test_the_paired_report_answers_every_declared_comparison_per_layer():
    readouts = {}
    for name in CONDITIONS:
        rows = []
        for item in ev.panel(corpus.families()):
            rows.append({"item_id": item["item_id"], "layer": item["layer"],
                         "face": item["face"], "is_correct": name.startswith("cfc")})
        readouts[name] = {"after_rows": rows}
    report = ro.paired_report(readouts)
    assert len(report) == 4 * 3
    entry = report["role_application|cfc_stable_cues|mixed_order_stable_cues"]
    assert entry["first"] == "cfc_stable_cues"
    assert entry["second"] == "mixed_order_stable_cues"
    assert entry["only_first_correct"] == 96
    assert entry["discordant_pairs"] == 96
    assert "McNemar" in entry["note"]
