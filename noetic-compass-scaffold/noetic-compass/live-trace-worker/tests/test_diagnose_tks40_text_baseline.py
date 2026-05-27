from __future__ import annotations

import json
import importlib.util
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "diagnose_tks40_text_baseline.py"
)
SPEC = importlib.util.spec_from_file_location("diagnose_tks40_text_baseline", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def _scenario(label: str, idx: int) -> dict:
    return {
        "id": f"{label}-{idx}",
        "prompt": f"marker {label} example {idx} asks what to preserve.",
        "expected_cas_axes": {
            "domain": label.split("|")[1],
            "operator": label.split("|")[0],
            "element": label,
        },
    }


def test_diagnostic_reports_text_baseline_and_top_features(tmp_path: Path):
    labels = ["^0|P", "^1|P", "^0|C", "^1|C"]
    scenarios = [_scenario(label, idx) for label in labels for idx in range(6)]
    scenario_path = tmp_path / "scenarios.json"
    output_path = tmp_path / "report.json"
    scenario_path.write_text(json.dumps({"scenarios": scenarios}), encoding="utf-8")

    report = module.diagnose(
        scenario_path=scenario_path,
        output_path=output_path,
        test_size=0.25,
        seed=7,
        top_k=3,
        samples_per_label=1,
    )

    assert output_path.exists()
    assert report["schema_version"] == "cas_harness_text_baseline_diagnostic.v2"
    assert report["n_classes"] == 4
    assert report["split"]["train_test_group_overlap_count"] == 0
    assert 0.0 <= report["text_baseline"]["test_accuracy"] <= 1.0
    assert report["text_baseline"]["n_features"] > 0
    assert set(report["top_predictive_features_per_class"]) == set(labels)
    assert all(report["sample_prompts_per_class"][label] for label in labels)


def test_diagnostic_can_use_foundation_label_and_fixed_split(tmp_path: Path):
    scenarios = []
    for split in ("train", "val", "test"):
        for idx, label in enumerate(("F1|T", "F1|A", "F2|T", "F2|A")):
            scenarios.append(
                {
                    "id": f"{split}-{label}-{idx}",
                    "prompt": f"{label} marker example {split} {idx}",
                    "expected_cas_axes": {"foundation": label},
                    "metadata": {
                        "split": split,
                        "counterfactual_pair_id": f"{split}-{idx}",
                    },
                }
            )
    scenario_path = tmp_path / "foundation.json"
    output_path = tmp_path / "foundation-report.json"
    scenario_path.write_text(json.dumps({"scenarios": scenarios}), encoding="utf-8")

    report = module.diagnose(
        scenario_path=scenario_path,
        output_path=output_path,
        label_key="foundation",
        axis_name="foundation28",
        group_key="metadata.counterfactual_pair_id",
        split_key="metadata.split",
        test_split="test",
        top_k=2,
    )

    assert report["axis"] == "foundation28"
    assert report["label_key"] == "foundation"
    assert report["split"]["kind"] == "fixed split by metadata.split; test_split=test"
    assert report["split"]["train_count"] == 8
    assert report["split"]["test_count"] == 4
    assert set(report["top_predictive_features_per_class"]) == {"F1|T", "F1|A", "F2|T", "F2|A"}
