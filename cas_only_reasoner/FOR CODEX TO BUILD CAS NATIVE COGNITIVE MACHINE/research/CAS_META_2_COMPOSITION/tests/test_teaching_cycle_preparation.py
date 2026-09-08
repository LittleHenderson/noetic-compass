import importlib.util
import json
from pathlib import Path
import pytest
from cas_meta2.codec import validate_public

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_teaching_cycle", ROOT / "tools/prepare_teaching_cycle.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    # The guarded checker supplies a fresh base under this experiment's records.
    destination = tmp_path_factory.mktemp("preparation") / "material"
    module.prepare(destination)
    return destination


def test_preparation_records_no_delivered_learning(prepared):
    record = json.loads((prepared / "preparation_receipt.json").read_text())
    assert record["status"] == "PREPARED_NOT_TRAINED"
    assert record["counts"] == {"train": 256, "development": 64, "test_fresh": 64,
                                "test_context": 64, "test_names": 64}
    assert record["delivered_neural_cycles"] == record["optimizer_steps"] == 0
    assert record["new_paid_reservations"] == 0
    assert record["planned_minimum_stage_presentations_per_arm"] == 7168


def test_final_inputs_contain_only_permitted_fields(prepared):
    for name in ("test_fresh", "test_context", "test_names"):
        publics = json.loads((prepared / "evaluation_public" / (name + ".json")).read_text())
        gold = json.loads((prepared / "evaluator_private" / (name + ".json")).read_text())
        assert len(publics) == len(gold) == 64
        for public in publics:
            validate_public(public)
            assert "Worked answer" not in public["problem"] and "BIND" not in public["problem"]


def test_prepare_refuses_overwrite_or_outside_record_target(prepared):
    with pytest.raises(ValueError, match="FRESH_TEACHING_RECORD_DIRECTORY_REQUIRED"):
        module.prepare(prepared)
    with pytest.raises(ValueError, match="FRESH_TEACHING_RECORD_DIRECTORY_REQUIRED"):
        module.prepare(ROOT / "not-a-teaching-record")
