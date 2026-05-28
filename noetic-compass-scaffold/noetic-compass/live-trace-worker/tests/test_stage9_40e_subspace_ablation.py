from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_stage9_40e_subspace_ablation.py"
)
SPEC = importlib.util.spec_from_file_location("run_stage9_40e_subspace_ablation", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
stage9_ablation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage9_ablation)


def _write_synthetic_separable_fixture(tmp_path: Path) -> dict[str, Path]:
    rng = np.random.default_rng(9040)
    classes = [("^0", "P"), ("^1", "P"), ("^2", "P"), ("^3", "P")]
    samples_per_class = 28
    hidden_dim = 24

    rows = []
    operators = []
    domains = []
    prompts = []
    scenarios = []
    for class_index, (operator, domain) in enumerate(classes):
        class_signal = np.zeros(hidden_dim, dtype=np.float32)
        class_signal[class_index] = 7.0
        for sample_index in range(samples_per_class):
            nuisance = rng.normal(0.0, 0.04, size=hidden_dim).astype(np.float32)
            rows.append(class_signal + nuisance)
            operators.append(operator)
            domains.append(domain)
            prompt = f"[fixture] synthetic prompt {operator} {domain} {sample_index}"
            prompts.append(prompt)
            scenarios.append(
                {
                    "id": f"{operator}-{domain}-{sample_index}",
                    "operator": operator,
                    "domain": domain,
                    "prompt": prompt,
                }
            )

    order = rng.permutation(len(rows))
    features = np.asarray(rows, dtype=np.float32)[order][:, np.newaxis, :]
    operators_arr = np.asarray(operators, dtype=object)[order]
    domains_arr = np.asarray(domains, dtype=object)[order]
    prompts_arr = np.asarray(prompts, dtype=object)[order]

    dataset = tmp_path / "synthetic_stage9_40e.npz"
    metadata = tmp_path / "synthetic_stage9_40e.metadata.json"
    scenario_json = tmp_path / "synthetic_stage9_40e.scenarios.json"
    probe_report = tmp_path / "synthetic_stage9_40e.probe_report.json"

    np.savez(
        dataset,
        features=features,
        layers=np.array([0]),
        labels_domain=domains_arr,
        labels_operator=operators_arr,
        prompts=prompts_arr,
    )
    metadata.write_text(
        json.dumps({"model_id": "unit-test-synthetic-model", "capture": "stage9-40e-fixture"}),
        encoding="utf-8",
    )
    scenario_json.write_text(json.dumps(scenarios), encoding="utf-8")
    probe_report.write_text(
        json.dumps(
            {
                "axis": "40_element_operator_x_domain",
                "best_layer": {"layer": 0, "test_acc": 0.95625},
                "controls": {
                    "shuffled_label_hidden_best_layer": {
                        "mean_test_acc": 0.02619,
                        "std_test_acc": 0.01,
                        "max_test_acc": 0.05,
                        "trials": 20,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return {
        "dataset": dataset,
        "metadata": metadata,
        "scenarios": scenario_json,
        "probe_report": probe_report,
    }


@pytest.fixture()
def synthetic_ablation_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    paths = _write_synthetic_separable_fixture(tmp_path)
    output = tmp_path / "subspace_ablation_report.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_stage9_40e_subspace_ablation.py",
            "--dataset",
            str(paths["dataset"]),
            "--metadata",
            str(paths["metadata"]),
            "--scenarios",
            str(paths["scenarios"]),
            "--probe-report",
            str(paths["probe_report"]),
            "--output",
            str(output),
            "--layers",
            "best",
            "--test-size",
            "0.25",
            "--seed",
            "9040",
            "--probe-max-iter",
            "500",
            "--random-control-trials",
            "5",
            "--guard-margin-pp",
            "5",
        ],
    )

    assert stage9_ablation.main() == 0
    return json.loads(output.read_text(encoding="utf-8"))


def test_true_subspace_ablation_damages_synthetic_separable_signal(
    synthetic_ablation_report: dict,
):
    result = synthetic_ablation_report["per_layer"][0]

    assert result["original_accuracy"] >= 0.9
    assert result["ablated_accuracy"] <= 0.45
    assert result["true_disruption"] >= 0.45
    assert result["guard"]["status"] == "passed"


def test_random_same_rank_controls_are_reported_separately(synthetic_ablation_report: dict):
    result = synthetic_ablation_report["per_layer"][0]
    controls = result["random_same_rank_controls"]

    assert "random_same_rank_controls" in result
    assert controls["trials"] == 5
    assert controls["rank"] == result["subspace"]["rank"]
    assert controls["mean_disruption"] is not None
    assert controls["max_disruption"] is not None
    assert len(controls["all_trials"]) == 5
    assert "shuffled_baseline" in result
    assert result["shuffled_baseline"]["source"] == "probe_report.controls.shuffled_label_hidden_best_layer"


def test_report_refuses_accept_suppress_packet_verdicts(synthetic_ablation_report: dict):
    serialized = json.dumps(synthetic_ablation_report)

    assert synthetic_ablation_report["packet_decision"] == "not_applicable_ablation_diagnostic_only"
    assert "ACCEPT" not in serialized
    assert "SUPPRESS" not in serialized


def test_method_label_and_provenance_fields_exist(synthetic_ablation_report: dict):
    artifacts = {
        artifact["artifact_id"]: artifact
        for artifact in synthetic_ablation_report["provenance"]["artifacts"]
    }

    assert synthetic_ablation_report["axis"] == "40_element_operator_x_domain"
    assert synthetic_ablation_report["base_method_label"] == "S9-40E-ORIGINAL-BASELINE-READOUT"
    assert synthetic_ablation_report["ablation_tier"] == "LOGIT-SUBSPACE-PROJECTION-ABLATION"
    assert synthetic_ablation_report["method_label"] == (
        "S9-40E-ORIGINAL-BASELINE-READOUT + LOGIT-SUBSPACE-PROJECTION-ABLATION"
    )
    assert synthetic_ablation_report["chance_baseline"]["accuracy"] == pytest.approx(0.025)
    assert set(artifacts) == {
        "activation_dataset_npz",
        "metadata_json",
        "scenario_json",
        "probe_eval_report_json",
    }
    assert all(artifact["content_sha256"] for artifact in artifacts.values())
    assert synthetic_ablation_report["dataset_summary"]["model_id"] == "unit-test-synthetic-model"
