from copy import deepcopy
import json
import pytest
from cas_meta1.curriculum import (generate_dataset, validate_dataset, permitted_view,
                                 rule_select, write_dataset, check_public, BASE_VALUES)

@pytest.fixture
def small():
    return generate_dataset(counts={"train": 54, "validation": 18, "test": 27})

def test_balanced_independent_instance_and_template_splits(small):
    receipt = validate_dataset(small)
    assert receipt["unique_formal_instances"] == 99
    assert receipt["neural_outcomes_checked"] is False
    groups = [set(row["provenance"]["template_id"] for row in rows) for rows in small.values()]
    assert not (groups[0] & groups[1] or groups[1] & groups[2] or groups[0] & groups[2])

def test_public_view_excludes_teacher_answers_and_identity(small):
    row = small["test"][0]
    public = permitted_view(row)
    assert set(public) == {"problem", "observations"}
    public["observations"][0]["values"][0] = 0.0
    assert row["public"]["observations"][0]["values"][0] != 0.0

@pytest.mark.parametrize("stage,procedure", [("first",0),("second",1),("final",2)])
def test_independently_authored_parser_anchors(stage, procedure):
    public = {"problem": f"The {stage} stage result is needed for violet.",
              "observations": [{"slot": i, "tag": tag, "values": list(BASE_VALUES)}
                               for i, tag in enumerate(["amber", "violet", "teal"])]}
    assert rule_select(public) == {"procedure": procedure, "binding": 1}

def test_corrupt_binding_rejected(small):
    small["test"][0]["target"]["binding"] = (small["test"][0]["target"]["binding"] + 1) % 3
    with pytest.raises(ValueError, match="SURFACE_ROUNDTRIP"):
        validate_dataset(small)

def test_duplicate_formal_instance_rejected(small):
    small["test"][1] = deepcopy(small["test"][0])
    with pytest.raises(ValueError, match="DUPLICATE_OR_SPLIT_LEAKAGE"):
        validate_dataset(small)

def test_private_field_injection_rejected(small):
    public = permitted_view(small["test"][0])
    public["target"] = {"procedure": 0}
    with pytest.raises(ValueError, match="PUBLIC_FIELDS"):
        check_public(public)

def test_ambiguous_task_rejected(small):
    public = permitted_view(small["test"][0])
    public["problem"] = "First and final for amber."
    with pytest.raises(ValueError, match="AMBIGUOUS"):
        rule_select(public)

def test_nonfinite_and_boolean_payloads_rejected(small):
    for bad in [True, float("nan"), float("inf")]:
        public = permitted_view(small["test"][0])
        public["observations"][0]["values"][0] = bad
        with pytest.raises(ValueError, match="INPUT_OUTSIDE"):
            check_public(public)

def test_dataset_writer_splits_test_gold(tmp_path):
    manifest = write_dataset(tmp_path / "data", counts={"train": 9, "validation": 9, "test": 9})
    public = json.loads((tmp_path / "data/test_public.json").read_text())
    assert all(set(item) == {"problem", "observations"} for item in public)
    assert set(manifest["sha256"]) == {"train.json","validation.json","test_public.json","test_private.json"}
    with pytest.raises(FileExistsError):
        write_dataset(tmp_path / "data")

def test_deterministic_generation():
    counts = {"train": 9, "validation": 9, "test": 9}
    assert generate_dataset(11, counts) == generate_dataset(11, counts)
    assert generate_dataset(11, counts) != generate_dataset(12, counts)
