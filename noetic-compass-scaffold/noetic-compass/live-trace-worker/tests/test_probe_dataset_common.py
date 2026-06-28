import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from probe_dataset_common import load_labeled_scenarios  # noqa: E402


def test_load_labeled_scenarios_accepts_records_fixture(tmp_path: Path) -> None:
    fixture = {
        "schema_version": "cas_harness_mtc_dual_labeled_fixture.v1",
        "records": [
            {
                "id": "row-1",
                "prompt": "A reviewer receives a concrete case card.",
                "expected_cas_axes": {
                    "operator": "^2",
                    "domain": "P",
                    "element": "^2|P",
                },
            }
        ],
    }
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")

    scenarios = load_labeled_scenarios(path)

    assert len(scenarios) == 1
    assert scenarios[0].scenario_id == "row-1"
    assert scenarios[0].labels["operator"] == "^2"
    assert scenarios[0].labels["domain"] == "P"
    assert scenarios[0].labels["element"] == "^2|P"
