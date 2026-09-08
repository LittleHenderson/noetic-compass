"""Static/pure admission checks only. These do not execute neural training."""
import ast
import builtins
from copy import deepcopy
from pathlib import Path

import pytest

from cas_meta2.teaching_cycle import gpu_adapter as adapter
from cas_meta2.teaching_cycle import data

SOURCE = Path(adapter.__file__).read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
FORBIDDEN = {"torch", "numpy", "sqlite3", "boto3", "botocore", "casformer", "cas_cjt"}


def test_no_neural_provider_or_database_import_at_module_scope():
    for node in TREE.body:
        if isinstance(node, ast.Import):
            assert not {name.name.split(".")[0] for name in node.names} & FORBIDDEN
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in FORBIDDEN


def test_cuda_entry_fails_before_tensor_import_on_laptop(monkeypatch):
    original = builtins.__import__
    def forbidden(name, *args, **kwargs):
        assert name.split(".")[0] not in FORBIDDEN
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", forbidden)
    monkeypatch.setattr(adapter.platform, "system", lambda: "Windows")
    with pytest.raises(ValueError, match="LINUX_WORKER_REQUIRED"):
        adapter._cuda()


def test_missing_explicit_enable_fails_before_tensor_import(monkeypatch):
    monkeypatch.setattr(adapter.platform, "system", lambda: "Linux")
    monkeypatch.delenv("CAS_META2_RUN_TEACHING_CYCLE", raising=False)
    with pytest.raises(ValueError, match="EXPLICIT_ENABLE_REQUIRED"):
        adapter._cuda()


def test_update_path_checks_before_optimizer_step():
    method = next(n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef) and n.name == "teach")
    segment = ast.get_source_segment(SOURCE, method)
    assert segment.index("validate_records(records, self._record_registry)") < segment.index("self._logits(publics)")
    assert segment.index("NONFINITE_LOSS") < segment.index("loss.backward()")
    assert segment.index("NONFINITE_OR_NONCUDA_GRADIENT") < segment.index("self.optimizer.step()")
    assert segment.count("self.optimizer.step()") == 1
    assert "OUT_OF_SCOPE_STATE_CHANGED" in segment


def test_prediction_signature_has_no_target_or_teacher():
    method = next(n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef) and n.name == "predict")
    assert [arg.arg for arg in method.args.args] == ["self", "publics"]
    assert "self.torch.no_grad()" in ast.get_source_segment(SOURCE, method)


def test_receipt_does_not_claim_provider_identity_or_native_learning():
    assert '"execution_mode": "cuda"' in SOURCE
    assert '"provider_identity_proved": False' in SOURCE
    assert '"accepted_weights_updated": False' in SOURCE
    assert '"checkpoint_digest_kind": "model_state_tensor_manifest_sha256"' in SOURCE
    assert 'path.open("xb")' in SOURCE
    assert "weights_only=True" in SOURCE
    assert '"gpu_name": torch.cuda.get_device_name(self.device)' in SOURCE
    assert "tensor.detach().contiguous().reshape(-1).view(torch.uint8).cpu()" in SOURCE


def test_public_state_identity_checks_scope_before_snapshot():
    method = next(n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef) and n.name == "state_identity")
    segment = ast.get_source_segment(SOURCE, method)
    assert segment.index("self._check_scope()") < segment.index("self._snapshot()")
    assert '"checkpoint_sha256": state_sha' in segment


@pytest.mark.parametrize("records", [[], {}, [{"split": "test"}], [{"split": "validation"}]])
def test_non_training_records_rejected_without_neural_execution(records):
    with pytest.raises(ValueError):
        adapter.validate_records(records, {})


def test_only_valid_integer_binding_target_is_consumed():
    case = data.build_dataset()["splits"]["train"][0]
    registry, _ = adapter.validate_training_plan([case])
    record = data.make_cycle(case)[0]
    assert adapter.validate_records([record], registry) == ([record["public"]], [case["target_binding"]])
    for target in (True, -1, 3, "0"):
        with pytest.raises(ValueError, match="BINDING_TARGET_INVALID"):
            adapter.validate_records([{**record, "target_binding": target}], registry)


def test_training_plan_is_closed_to_forged_family_target_and_stage():
    case = data.build_dataset()["splits"]["train"][0]
    registry, identities = adapter.validate_training_plan([case])
    record = data.make_cycle(case)[0]
    assert len(registry) == 42
    assert set(identities) == {"training_cases_sha256", "record_registry_sha256"}
    for patch in ({"family_id": "forged"}, {"stage": "pretend"},
                  {"target_binding": (case["target_binding"] + 1) % 3}, {"teacher_note": "extra"}):
        with pytest.raises(ValueError, match="RECORD_OUTSIDE_TRAINING_PLAN"):
            adapter.validate_records([{**record, **patch}], registry)


def test_relabeling_held_out_case_does_not_add_it_to_training_registry():
    dataset = data.build_dataset()
    registry, _ = adapter.validate_training_plan(dataset["splits"]["train"][:1])
    held_out = deepcopy(dataset["splits"]["test_fresh"][0])
    held_out["split"] = "train"
    with pytest.raises(ValueError, match="RECORD_OUTSIDE_TRAINING_PLAN"):
        adapter.validate_records(data.make_cycle(held_out)[:1], registry)


def test_duplicate_nontrain_and_noncanonical_cases_rejected():
    dataset = data.build_dataset()
    case = dataset["splits"]["train"][0]
    with pytest.raises(ValueError, match="DUPLICATE_TRAINING_FAMILY"):
        adapter.validate_training_plan([case, case])
    with pytest.raises(ValueError, match="TRAINING_CASE_REQUIRED"):
        adapter.validate_training_plan(dataset["splits"]["development"][:1])
    with pytest.raises(ValueError):
        adapter.validate_training_plan([{**case, "family_id": "forged"}])


def test_registry_is_deepcopied_and_binds_whole_record():
    case = data.build_dataset()["splits"]["train"][0]
    original = deepcopy(case)
    registry, identities = adapter.validate_training_plan([case])
    case["observations"][0]["values"][0] = 999
    assert adapter.validate_records(data.make_cycle(original)[:1], registry)
    assert adapter.validate_training_plan([original])[1] == identities


def test_checkpoint_and_builder_bind_training_plan():
    assert '"plan_identity": self.plan_identity' in SOURCE
    build = next(n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef) and n.name == "build_matched_learners")
    assert [arg.arg for arg in build.args.args] == ["training_cases"]
    constructor = next(n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    assert "training_cases" in [arg.arg for arg in constructor.args.kwonlyargs]
