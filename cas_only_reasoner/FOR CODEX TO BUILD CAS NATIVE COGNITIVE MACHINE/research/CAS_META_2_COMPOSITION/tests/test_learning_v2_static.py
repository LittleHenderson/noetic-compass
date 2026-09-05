"""Pure source/control checks. These are not neural learning evidence."""
import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

from cas_meta2 import campaign_v2 as campaign

ROOT = Path(__file__).resolve().parents[1]
TRAIN_TEXT = (ROOT / "cas_meta2/train_v2.py").read_text(encoding="utf-8")
TRAIN = ast.parse(TRAIN_TEXT)
CAMPAIGN_TEXT = (ROOT / "cas_meta2/campaign_v2.py").read_text(encoding="utf-8")
CAMPAIGN = ast.parse(CAMPAIGN_TEXT)


def source(tree, text, name):
    node = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
    return ast.get_source_segment(text, node)


def test_new_campaign_import_is_non_neural():
    assert "torch" not in sys.modules


def test_training_no_private_label_parse_and_old_parser_only_in_rule_arm():
    for node in ast.walk(TRAIN):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("read_json", "load", "loads"):
            assert "test_private.json" not in ast.get_source_segment(TRAIN_TEXT, node)
    assert 'file_hash(data / name)' in TRAIN_TEXT
    training = source(TRAIN, TRAIN_TEXT, "train_and_seal")
    assert 'if arm == "rule":\n            from .curriculum import parse_problem' in training
    assert "reference_task(" not in training and "verify_task(" not in training
    assert "grammar_mask" not in training and "rule_fallback" not in training


def test_freely_generated_validation_selects_checkpoint():
    training = source(TRAIN, TRAIN_TEXT, "train_and_seal")
    assert 'selection_key(validation) > selection_key(best["validation"])' in training
    assert "selected = generation_checked and" in training
    assert "epoch == 1 or epoch % config.validation_generation_interval == 0" in training
    assert 'validation["generation"] = generated_metrics(actions, validation_tasks)' in training
    assert 'validation_predictions' in training and 'test_gold_access' in training


def test_validation_generation_checks_deadline_around_each_batch():
    generation = source(TRAIN, TRAIN_TEXT, "_validation_generation")
    assert generation.count("require_time(deadline)") == 2
    assert generation.index("require_time(deadline)") < generation.index("predict_public(")
    assert generation.rindex("require_time(deadline)") > generation.index("predict_public(")


def test_registered_config_drives_real_training():
    run = source(CAMPAIGN, CAMPAIGN_TEXT, "run")
    assert 'registered_training = dict(spec["training"])' in run
    assert 'PolicyConfig(**registered_training["policy"])' in run
    assert 'TrainingConfig(**actual_training)' in run
    assert "V2_DATASET_SEED_MISMATCH" in run and "V2_DATASET_COUNT_MISMATCH" in run
    assert run.index("run_preflight(") < run.index("train_and_seal(")
    assert run.index("evaluate_sealed(") < run.index("report_evaluation_groups(")


def test_private_opening_stays_after_all_arms_sealed():
    text = source(CAMPAIGN, CAMPAIGN_TEXT, "evaluate_sealed")
    opening = text.index('tasks = _read(data / "test_private.json")')
    assert text.index("PREDICTION_SEAL_INVALID") < opening
    assert text.index("SEALED_CASE_ARM_COVERAGE_INVALID") < opening
    assert text.index("TEST_GOLD_OPENING_TIME_NOT_AFTER_SEAL") < opening


def test_v2_checkpoint_format_and_cuda_required():
    load = source(TRAIN, TRAIN_TEXT, "_load_checkpoint")
    assert 'require_cuda(device)' in load
    assert 'CHECKPOINT_FORMAT_MISMATCH' in load
    assert 'map_location=device, weights_only=True' in load
    assert 'CANDIDATE_CHECKPOINT_DIGEST_MISMATCH' in load


def test_spec_requires_exact_launch_binding(tmp_path, monkeypatch):
    spec = {"schema": "cas-meta2-experiment/2", "profile": "learning_v2", "entrypoint": "cas_meta2.campaign_v2"}
    path = tmp_path / "EXPERIMENT_V2.json"
    raw = json.dumps(spec).encode()
    path.write_bytes(raw)
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    monkeypatch.delenv("CAS_META2_EXPERIMENT_PROFILE", raising=False)
    with pytest.raises(ValueError, match="LAUNCHER_SPEC_BINDING_REQUIRED"):
        campaign.experiment_identity()
    for name, value in {"CAS_META2_EXPERIMENT_PROFILE": "learning_v2",
                        "CAS_META2_EXPERIMENT_ENTRYPOINT": "cas_meta2.campaign_v2",
                        "CAS_META2_EXPERIMENT_SPEC_SHA256": sha256(raw).hexdigest()}.items():
        monkeypatch.setenv(name, value)
    assert campaign.experiment_identity()["spec_sha256"] == sha256(raw).hexdigest()
    path.write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="LAUNCHER_SPEC_BINDING_REQUIRED"):
        campaign.experiment_identity()


def test_experiment_fields_have_exact_registered_defaults():
    spec = json.loads((ROOT / "EXPERIMENT_V2.json").read_bytes())
    assert spec["curriculum"]["counts"] == {"train": 768, "validation": 48, "test": 72}
    assert spec["curriculum"]["seed"] == 20260917
    assert spec["training"]["epochs"] == 100
    assert spec["evaluation"]["arms"] == list(campaign.ARMS)
    assert spec["execution"]["total_owner_cap_usd"] == "400.00"
    assert spec["execution"]["automatic_retries"] == 0
