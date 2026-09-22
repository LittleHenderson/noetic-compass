"""Regression checks for Q3's learner-visible headers and malformed JSON boundary.

Fixtures keep the first real record per family, then rehash deliberate edits.
No model, compiler, or full dataset regeneration is involved.
"""
import hashlib
import json
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import q3_load

DATA = HERE / "data" / "q3_v0_4"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def data_copy(tmp_path):
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    for family in q3_load.FAMILIES:
        for side in ("visible", "sealed"):
            name = f"{side}_{family}_train.jsonl"
            with (DATA / name).open(encoding="utf-8") as source:
                body = source.readline().encode("utf-8")
            (tmp_path / name).write_bytes(body)
            manifest["files"][name] = {"records": 1, "sha256": hashlib.sha256(body).hexdigest()}
    write_json(tmp_path / "manifest.json", manifest)
    return tmp_path


def rewrite_header(data_dir, family, field, value):
    name = f"visible_{family}_train.jsonl"
    row = json.loads((data_dir / name).read_text(encoding="utf-8"))
    row[field] = value
    body = (json.dumps(row) + "\n").encode("utf-8")
    (data_dir / name).write_bytes(body)
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"][name]["sha256"] = hashlib.sha256(body).hexdigest()
    write_json(data_dir / "manifest.json", manifest)


@pytest.mark.parametrize("text", ["1e999", "-1e999", '{"x": [1e999]}', "[1.8e308]", "NaN", "Infinity"])
def test_nonfinite_numbers_never_enter_json_data(text):
    with pytest.raises(q3_load.Q3LoadError, match="^NONFINITE_NUMBER:"):
        q3_load.strict_loads(text, "probe.json")


def test_finite_numbers_and_declared_invalid_inputs_remain_data():
    assert q3_load.strict_loads('{"x": [1.25, -3e20, 1e-200, 0.0]}') == {
        "x": [1.25, -3e20, 1e-200, 0.0]
    }


@pytest.mark.parametrize("declaration", [None, [], 1, "visible"])
def test_nonobject_visibility_declaration_has_a_loader_error(data_copy, declaration):
    manifest = json.loads((data_copy / "manifest.json").read_text(encoding="utf-8"))
    manifest["visibility"]["A"] = declaration
    write_json(data_copy / "manifest.json", manifest)
    with pytest.raises(q3_load.Q3LoadError, match="^MANIFEST_MALFORMED:"):
        q3_load.manifest_of(data_copy)


@pytest.mark.parametrize("field", ["visible", "withheld"])
@pytest.mark.parametrize("value", [None, "record_id", {}, [None, []]])
def test_visibility_fields_must_be_lists_of_names(data_copy, field, value):
    manifest = json.loads((data_copy / "manifest.json").read_text(encoding="utf-8"))
    manifest["visibility"]["A"][field] = value
    write_json(data_copy / "manifest.json", manifest)
    with pytest.raises(q3_load.Q3LoadError, match="^MANIFEST_MALFORMED:"):
        q3_load.manifest_of(data_copy)


@pytest.mark.parametrize("family", q3_load.FAMILIES)
@pytest.mark.parametrize("door", [q3_load.load_visible, q3_load.load_split])
def test_real_headers_still_load(data_copy, family, door):
    assert len(door(data_copy, family, "train")) == 1


@pytest.mark.parametrize("family", q3_load.FAMILIES)
@pytest.mark.parametrize("door", [q3_load.load_visible, q3_load.load_split])
@pytest.mark.parametrize("value", [{"answer": True}, "reconstruction: answer=True", None])
def test_mode_cannot_carry_an_answer(data_copy, family, door, value):
    rewrite_header(data_copy, family, "mode", value)
    with pytest.raises(q3_load.Q3LoadError, match="^WRONG_MODE:"):
        door(data_copy, family, "train")


@pytest.mark.parametrize("family", ["A", "C"])
@pytest.mark.parametrize("door", [q3_load.load_visible, q3_load.load_split])
@pytest.mark.parametrize("value", [{"answer": True}, "cas.op.other/1.0", None])
def test_operation_id_is_the_fixed_family_contract(data_copy, family, door, value):
    rewrite_header(data_copy, family, "operation_id", value)
    with pytest.raises(q3_load.Q3LoadError, match="^WRONG_OPERATION_ID:"):
        door(data_copy, family, "train")
