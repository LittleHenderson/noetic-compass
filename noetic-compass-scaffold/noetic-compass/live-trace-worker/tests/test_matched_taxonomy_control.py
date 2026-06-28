from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_matched_taxonomy_control.py"
)
SPEC = importlib.util.spec_from_file_location("run_matched_taxonomy_control", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
matched_taxonomy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = matched_taxonomy
SPEC.loader.exec_module(matched_taxonomy)


def test_linear_probe_contract_is_standard_scaler_balanced_logistic():
    probe = matched_taxonomy._build_linear_probe(C=0.25, max_iter=123)

    assert isinstance(probe, Pipeline)
    assert isinstance(probe.named_steps["standardscaler"], StandardScaler)

    logistic = probe.named_steps["logisticregression"]
    assert isinstance(logistic, LogisticRegression)
    assert logistic.C == 0.25
    assert logistic.max_iter == 123
    assert logistic.class_weight == "balanced"
    assert logistic.solver == "lbfgs"


def test_manifest_loader_aligns_label_mapping_by_sample_id():
    manifest = {
        "taxonomies": {
            "topic_4way": {
                "role": "coherent_matched",
                "labels": {"s0": "a", "s1": "b", "s2": "c", "s3": "d"},
                "parent_labels": {"s0": "p0", "s1": "p0", "s2": "p1", "s3": "p1"},
                "child_labels": {"s0": "x", "s1": "y", "s2": "x", "s3": "y"},
            }
        }
    }

    specs = matched_taxonomy.load_taxonomy_manifest(
        manifest,
        axis="40e",
        n_samples=4,
        sample_ids=np.array(["s0", "s1", "s2", "s3"], dtype=object),
    )

    assert len(specs) == 1
    assert specs[0].taxonomy_id == "topic_4way"
    assert specs[0].role == "coherent_matched"
    assert specs[0].labels.tolist() == ["a", "b", "c", "d"]
    assert specs[0].parent_labels.tolist() == ["p0", "p0", "p1", "p1"]
    assert specs[0].child_labels.tolist() == ["x", "y", "x", "y"]


def test_manifest_loader_skips_design_only_taxonomies_without_row_labels():
    manifest = {
        "controls": [
            {
                "id": "NC40_TOPIC_FRAME_V1",
                "role": "coherent_matched",
                "labels": ["class_a", "class_b", "class_c", "class_d"],
                "assignment_algorithm": "deterministic_min_cost_balanced_assignment",
            },
            {
                "id": "SCRAMBLED_DESIGN_ONLY",
                "role": "scrambled_control",
                "algorithm": "shuffle source labels at runtime",
            },
        ]
    }

    specs = matched_taxonomy.load_taxonomy_manifest(
        manifest,
        axis="40e",
        n_samples=8,
        sample_ids=np.array([f"s{i}" for i in range(8)], dtype=object),
    )

    assert specs == []


def _verdict_report(
    taxonomy_id: str,
    role: str,
    *,
    hidden_acc: float,
    hidden_f1: float,
    text_acc: float,
    text_f1: float,
    flat_lacunarity: float,
    class_count: int = 4,
    coherent: bool = True,
    nested: tuple[float, float, float] | None = None,
) -> dict:
    nested_report = {"status": "not_available"}
    if nested is not None:
        nested_report = {
            "status": "available",
            "parent_factor_lacunarity": nested[0],
            "child_factor_lacunarity": nested[1],
            "joint_class_lacunarity": nested[2],
        }
    return {
        "taxonomy_id": taxonomy_id,
        "role": role,
        "coherent": coherent,
        "class_count": class_count,
        "matched_cardinality_with_cas": True,
        "hidden_readout": {
            "best_layer": {
                "accuracy": hidden_acc,
                "macro_f1": hidden_f1,
            }
        },
        "text_baseline": {
            "accuracy": text_acc,
            "macro_f1": text_f1,
        },
        "lift_over_text": {
            "accuracy": hidden_acc - text_acc,
            "macro_f1": hidden_f1 - text_f1,
        },
        "shuffled_label_control": {
            "max_accuracy": 0.28,
        },
        "lacunarity": {
            "flat_best_layer": flat_lacunarity,
            "nested_best_layer": nested_report,
        },
    }


def test_verdict_passes_when_cas_clears_readout_and_lacunarity_gates():
    cas = _verdict_report(
        "cas_f28",
        "cas",
        hidden_acc=0.90,
        hidden_f1=0.90,
        text_acc=0.40,
        text_f1=0.40,
        flat_lacunarity=0.10,
        nested=(0.10, 0.10, 0.10),
    )
    control = _verdict_report(
        "topic_7x4",
        "coherent_matched",
        hidden_acc=0.80,
        hidden_f1=0.80,
        text_acc=0.40,
        text_f1=0.40,
        flat_lacunarity=0.40,
        nested=(0.30, 0.30, 0.30),
    )
    scrambled = _verdict_report(
        "scrambled",
        "scrambled_control",
        hidden_acc=0.25,
        hidden_f1=0.25,
        text_acc=0.24,
        text_f1=0.24,
        flat_lacunarity=0.20,
        coherent=False,
    )

    verdict = matched_taxonomy.build_verdict(
        cas_report=cas,
        taxonomy_reports=[cas, control, scrambled],
        axis="f28",
        cas_lift_threshold_pp=20.0,
        matched_margin_pp=5.0,
        scrambled_margin_pp=5.0,
    )

    assert verdict["status"] == "pass"
    assert verdict["decision"] == "PASS"
    assert verdict["pass"] is True
    assert verdict["grey"] is False
    assert verdict["falsify"] is False
    assert verdict["fail"] is False
    assert verdict["rules"]["f28_nested_lacunarity_ratio_gate"]["status"] == "PASS"


def test_verdict_fails_when_coherent_control_matches_lift_and_lacunarity():
    cas = _verdict_report(
        "cas_40e",
        "cas",
        hidden_acc=0.85,
        hidden_f1=0.85,
        text_acc=0.45,
        text_f1=0.45,
        flat_lacunarity=0.20,
    )
    control = _verdict_report(
        "topic_40way",
        "coherent_matched",
        hidden_acc=0.90,
        hidden_f1=0.90,
        text_acc=0.40,
        text_f1=0.40,
        flat_lacunarity=0.10,
    )
    scrambled = _verdict_report(
        "scrambled",
        "scrambled_control",
        hidden_acc=0.25,
        hidden_f1=0.25,
        text_acc=0.24,
        text_f1=0.24,
        flat_lacunarity=0.30,
        coherent=False,
    )

    verdict = matched_taxonomy.build_verdict(
        cas_report=cas,
        taxonomy_reports=[cas, control, scrambled],
        axis="40e",
        cas_lift_threshold_pp=20.0,
        matched_margin_pp=5.0,
        scrambled_margin_pp=5.0,
    )

    assert verdict["status"] == "falsify"
    assert verdict["decision"] == "FALSIFY"
    assert verdict["falsify"] is True
    assert verdict["fail"] is True
    assert verdict["fail_controls"][0]["taxonomy_id"] == "topic_40way"


def test_verdict_blocks_when_coherent_matched_taxonomy_is_missing():
    cas = _verdict_report(
        "cas_40e",
        "cas",
        hidden_acc=0.85,
        hidden_f1=0.85,
        text_acc=0.45,
        text_f1=0.45,
        flat_lacunarity=0.20,
    )
    scrambled = _verdict_report(
        "scrambled",
        "scrambled_control",
        hidden_acc=0.025,
        hidden_f1=0.025,
        text_acc=0.024,
        text_f1=0.024,
        flat_lacunarity=0.30,
        coherent=False,
    )

    verdict = matched_taxonomy.build_verdict(
        cas_report=cas,
        taxonomy_reports=[cas, scrambled],
        axis="40e",
        cas_lift_threshold_pp=20.0,
        matched_margin_pp=5.0,
        scrambled_margin_pp=5.0,
    )

    assert verdict["status"] == "blocked"
    assert verdict["decision"] == "BLOCKED"
    assert verdict["blocked"] is True
    assert verdict["falsify"] is False
    assert "missing externally supplied coherent matched taxonomy" in verdict["blocked_reasons"][0]


def test_f28_nested_ratio_gate_marks_grey_band():
    cas = _verdict_report(
        "cas_f28",
        "cas",
        hidden_acc=0.90,
        hidden_f1=0.90,
        text_acc=0.40,
        text_f1=0.40,
        flat_lacunarity=0.10,
        nested=(0.10, 0.10, 0.10),
    )
    control = _verdict_report(
        "topic_7x4",
        "coherent_matched",
        hidden_acc=0.80,
        hidden_f1=0.80,
        text_acc=0.40,
        text_f1=0.40,
        flat_lacunarity=0.40,
        nested=(0.20, 0.20, 0.20),
    )
    scrambled = _verdict_report(
        "scrambled",
        "scrambled_control",
        hidden_acc=0.25,
        hidden_f1=0.25,
        text_acc=0.24,
        text_f1=0.24,
        flat_lacunarity=0.20,
        coherent=False,
    )

    verdict = matched_taxonomy.build_verdict(
        cas_report=cas,
        taxonomy_reports=[cas, control, scrambled],
        axis="f28",
        cas_lift_threshold_pp=20.0,
        matched_margin_pp=5.0,
        scrambled_margin_pp=5.0,
    )

    assert verdict["status"] == "grey"
    nested_gate = verdict["rules"]["f28_nested_lacunarity_ratio_gate"]
    assert nested_gate["status"] == "GREY"
    assert nested_gate["controls"][0]["minimum_ratio"] == pytest.approx(2.0)


def _write_synthetic_runner_fixture(tmp_path: Path) -> dict[str, Path]:
    rng = np.random.default_rng(4040)
    classes = [("^0", "P"), ("^1", "P"), ("^2", "P"), ("^3", "P")]
    samples_per_class = 32
    hidden_dim = 12

    rows_layer0 = []
    rows_layer1 = []
    operators = []
    domains = []
    prompts = []
    sample_ids = []
    matched_labels = []
    matched_parents = []
    matched_children = []

    for class_index, (operator, domain) in enumerate(classes):
        signal = np.zeros(hidden_dim, dtype=np.float32)
        signal[class_index] = 6.0
        weaker_signal = np.zeros(hidden_dim, dtype=np.float32)
        weaker_signal[class_index + 4] = 2.0
        for sample_index in range(samples_per_class):
            global_index = class_index * samples_per_class + sample_index
            rows_layer0.append(signal + rng.normal(0.0, 0.05, size=hidden_dim).astype(np.float32))
            rows_layer1.append(weaker_signal + rng.normal(0.0, 0.20, size=hidden_dim).astype(np.float32))
            operators.append(operator)
            domains.append(domain)
            prompts.append(f"[fixture] neutral scenario {global_index}")
            sample_ids.append(f"s{global_index}")

            matched_class = sample_index % len(classes)
            matched_labels.append(f"topic_{matched_class}|function_{matched_class % 2}")
            matched_parents.append(f"topic_{matched_class}")
            matched_children.append(f"function_{matched_class % 2}")

    order = rng.permutation(len(operators))
    features = np.stack([np.asarray(rows_layer0), np.asarray(rows_layer1)], axis=1)[order]
    dataset = tmp_path / "matched_taxonomy_fixture.npz"
    metadata = tmp_path / "matched_taxonomy_fixture.metadata.json"
    manifest = tmp_path / "matched_taxonomy_manifest.json"
    output = tmp_path / "matched_taxonomy_report.json"

    np.savez(
        dataset,
        features=features.astype(np.float32),
        layers=np.array([0, 1]),
        labels_operator=np.asarray(operators, dtype=object)[order],
        labels_domain=np.asarray(domains, dtype=object)[order],
        prompts=np.asarray(prompts, dtype=object)[order],
        sample_ids=np.asarray(sample_ids, dtype=object)[order],
    )
    metadata.write_text(
        json.dumps({"model_id": "unit-test-model", "model_family": "synthetic"}),
        encoding="utf-8",
    )
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "matched_taxonomy_manifest.test",
                "taxonomies": [
                    {
                        "id": "topic_function_4way",
                        "role": "coherent_matched",
                        "labels": np.asarray(matched_labels, dtype=object)[order].tolist(),
                        "parent_labels": np.asarray(matched_parents, dtype=object)[order].tolist(),
                        "child_labels": np.asarray(matched_children, dtype=object)[order].tolist(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return {
        "dataset": dataset,
        "metadata": metadata,
        "manifest": manifest,
        "output": output,
    }


def test_runner_writes_json_report_with_required_control_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    paths = _write_synthetic_runner_fixture(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_matched_taxonomy_control.py",
            "--dataset",
            str(paths["dataset"]),
            "--metadata",
            str(paths["metadata"]),
            "--manifest",
            str(paths["manifest"]),
            "--output",
            str(paths["output"]),
            "--axis",
            "40e",
            "--layers",
            "all",
            "--test-size",
            "0.25",
            "--seed",
            "4040",
            "--shuffled-seeds",
            "101,202",
            "--probe-max-iter",
            "300",
            "--text-max-features",
            "128",
        ],
    )

    assert matched_taxonomy.main() == 0
    report = json.loads(paths["output"].read_text(encoding="utf-8"))

    assert report["schema_version"] == matched_taxonomy.SCHEMA_VERSION
    assert report["status"] == "completed"
    assert set(("pass", "grey", "fail")).issubset(report)
    assert set(("pass", "grey", "fail", "falsify")).issubset(report)
    assert report["verdict"]["status"] in {"pass", "grey", "falsify"}
    assert report["stage_scope"]["decision_stage"] == "Stage X.1"
    assert report["stage_scope"]["cross_architecture_extension"]["stage"] == "Stage X.2"
    assert report["stage_scope"]["cross_architecture_extension"]["status"] == "conditional_not_executed"
    assert report["split_manifest"]["content_sha256"]
    assert report["fixed_seeds"]["shuffled_label_seeds"] == [101, 202]
    assert report["fixed_seeds"]["shuffled_label_seed_count"] == 2
    assert report["run_settings"]["smoke_settings_used"] is False
    assert report["run_settings"]["selected_layers"] == [0, 1]
    assert report["run_settings"]["selected_layer_count"] == 2
    assert report["run_settings"]["selected_shuffled_seed_count"] == 2
    assert len(report["taxonomy_reports"]) == 3
    assert report["evidence_packet_requirements"]["coherent_cardinality_matched_alternative"] == (
        "present_externally_supplied"
    )
    assert report["method_contract"]["matched_alternative_label_source"].startswith(
        "externally supplied manifest labels"
    )

    cas_report = report["taxonomy_reports"][0]
    assert cas_report["taxonomy_id"] == "cas_40e"
    assert cas_report["hidden_readout"]["best_layer"]["accuracy"] >= 0.9
    assert cas_report["text_baseline"]["status"] == "completed"
    assert cas_report["shuffled_label_control"]["max_accuracy"] is not None
    assert cas_report["lacunarity"]["flat_best_layer"] is not None

    ids = {taxonomy["taxonomy_id"] for taxonomy in report["taxonomy_reports"]}
    assert "topic_function_4way" in ids
    assert any(taxonomy_id.startswith("scrambled_cas_seed_") for taxonomy_id in ids)


def test_runner_smoke_one_shuffled_seed_records_settings_and_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    paths = _write_synthetic_runner_fixture(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_matched_taxonomy_control.py",
            "--dataset",
            str(paths["dataset"]),
            "--metadata",
            str(paths["metadata"]),
            "--manifest",
            str(paths["manifest"]),
            "--output",
            str(paths["output"]),
            "--axis",
            "40e",
            "--layers",
            "1",
            "--test-size",
            "0.25",
            "--seed",
            "4040",
            "--shuffled-seeds",
            "101,202,303",
            "--smoke-one-shuffled-seed",
            "--probe-max-iter",
            "300",
            "--text-max-features",
            "128",
        ],
    )

    assert matched_taxonomy.main() == 0
    captured = capsys.readouterr()
    report = json.loads(paths["output"].read_text(encoding="utf-8"))

    assert "[matched-taxonomy] loaded dataset" in captured.err
    assert "taxonomy 1/3 start id=cas_40e" in captured.err
    assert "layer 1/1 start layer=1" in captured.err
    assert "control shuffled-label cas_40e seed 1/1 start seed=101" in captured.err
    assert "seed 2/3" not in captured.err

    assert report["method_contract"]["class_weight"] == "balanced"
    assert report["method_contract"]["solver"] == "lbfgs"
    assert report["run_settings"]["smoke_settings_used"] is True
    assert report["run_settings"]["smoke_one_shuffled_seed"] is True
    assert report["run_settings"]["method_changed_for_smoke"] is False
    assert report["run_settings"]["requested_shuffled_seed_count"] == 3
    assert report["run_settings"]["selected_shuffled_seed_count"] == 1
    assert report["run_settings"]["requested_shuffled_label_seeds"] == [101, 202, 303]
    assert report["run_settings"]["selected_shuffled_label_seeds"] == [101]
    assert report["run_settings"]["selected_layers"] == [1]
    assert report["run_settings"]["selected_layer_count"] == 1
    assert report["fixed_seeds"]["shuffled_label_seeds"] == [101]
    assert report["fixed_seeds"]["shuffled_label_seed_count"] == 1
    assert report["fixed_seeds"]["scrambled_taxonomy_seed"] == 101
