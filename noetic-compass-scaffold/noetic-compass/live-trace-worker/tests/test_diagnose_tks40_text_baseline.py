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
    assert report["schema_version"] == "cas_harness_tks40_text_baseline_diagnostic.v1"
    assert report["n_classes"] == 4
    assert report["split"]["train_test_group_overlap_count"] == 0
    assert 0.0 <= report["text_baseline"]["test_accuracy"] <= 1.0
    assert report["text_baseline"]["n_features"] > 0
    assert set(report["top_predictive_features_per_class"]) == set(labels)
    assert all(report["sample_prompts_per_class"][label] for label in labels)
