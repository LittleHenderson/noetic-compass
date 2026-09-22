"""Malformed-input regression cases; no compiler, model or data regeneration.

Every file mutation uses a temporary copy. Row/manifest hashes are refreshed so
the tested content check, rather than an unrelated hash failure, rejects it.
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
    path.write_text(json.dumps(value), encoding="utf-8")


def write_data_file(directory, name, body, records=None):
    (directory / name).write_bytes(body)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"][name] = {"sha256": hashlib.sha256(body).hexdigest()}
    if records is not None:
        manifest["files"][name]["records"] = records
    write_json(directory / "manifest.json", manifest)


@pytest.fixture
def data_copy(tmp_path):
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    write_json(tmp_path / "manifest.json", manifest)
    for family in q3_load.FAMILIES:
        for side in ("visible", "sealed"):
            name = f"{side}_{family}_train.jsonl"
            with (DATA / name).open(encoding="utf-8") as source:
                body = source.readline().encode("utf-8")
            write_data_file(tmp_path, name, body, records=1)
    return tmp_path


@pytest.mark.parametrize("value", [None, [], {}, 17, ""])
def test_schema_is_a_nonempty_string_before_pin_lookup(data_copy, value):
    manifest = json.loads((data_copy / "manifest.json").read_text(encoding="utf-8"))
    manifest["schema"] = value
    write_json(data_copy / "manifest.json", manifest)
    with pytest.raises(q3_load.Q3LoadError, match="^MANIFEST_MALFORMED:"):
        q3_load.check_pins(data_copy)


@pytest.mark.parametrize("value", [None, [], "counts", {"A_train": True}, {"A_train": -1}])
def test_manifest_counts_are_typed_before_dataset_checks(data_copy, value):
    manifest = json.loads((data_copy / "manifest.json").read_text(encoding="utf-8"))
    manifest["counts"] = value
    write_json(data_copy / "manifest.json", manifest)
    with pytest.raises(q3_load.Q3LoadError, match="^MANIFEST_MALFORMED:"):
        q3_load.manifest_of(data_copy)


@pytest.mark.parametrize("value", [True, -1, [], "1"])
def test_file_record_counts_cannot_use_boolean_equality(data_copy, value):
    manifest = json.loads((data_copy / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"]["visible_A_train.jsonl"]["records"] = value
    write_json(data_copy / "manifest.json", manifest)
    with pytest.raises(q3_load.Q3LoadError, match="^MANIFEST_MALFORMED:"):
        q3_load.load_visible(data_copy, "A", "train")


@pytest.mark.parametrize("value", [None, [], {}, {"data_versions": []}, {"data_versions": None}])
def test_malformed_pin_index_is_refused(tmp_path, monkeypatch, value):
    pin_file = tmp_path / "pins.json"
    write_json(pin_file, value)
    monkeypatch.setattr(q3_load, "PINS", pin_file)
    with pytest.raises(q3_load.Q3LoadError, match="^PINS_MALFORMED:"):
        q3_load.check_pins(DATA)


@pytest.mark.parametrize("value", [None, [], {}, {"manifest_sha256": []}, {"manifest_sha256": 1}])
def test_malformed_version_pin_is_refused(tmp_path, monkeypatch, value):
    schema = q3_load.manifest_of(DATA)["schema"]
    pin_file = tmp_path / "pins.json"
    write_json(pin_file, {"data_versions": {schema: value}})
    monkeypatch.setattr(q3_load, "PINS", pin_file)
    with pytest.raises(q3_load.Q3LoadError, match="^PINS_MALFORMED:"):
        q3_load.check_pins(DATA)


def test_absent_version_and_wrong_pin_keep_existing_codes(tmp_path, monkeypatch):
    pin_file = tmp_path / "pins.json"
    monkeypatch.setattr(q3_load, "PINS", pin_file)
    write_json(pin_file, {"data_versions": {}})
    with pytest.raises(q3_load.Q3LoadError, match="^NO_PIN_FOR_THIS_DATA_VERSION:"):
        q3_load.check_pins(DATA)
    schema = q3_load.manifest_of(DATA)["schema"]
    write_json(pin_file, {"data_versions": {schema: {"manifest_sha256": "0" * 64}}})
    with pytest.raises(q3_load.Q3LoadError, match="^MANIFEST_NOT_THE_PINNED_ONE:"):
        q3_load.check_pins(DATA)


@pytest.mark.parametrize("value", [None, [], {}, {"contract_digest": []}, {"contract_digest": 17}, {"contract_digest": ""}])
def test_contract_digest_is_a_nonempty_string(tmp_path, value):
    contract = tmp_path / "contract.json"
    write_json(contract, value)
    with pytest.raises(q3_load.Q3LoadError, match="^CONTRACT_MALFORMED:"):
        q3_load.check_contract_binding(DATA, contract)


def test_well_formed_wrong_contract_keeps_existing_code(tmp_path):
    contract = tmp_path / "contract.json"
    write_json(contract, {"contract_digest": "0" * 64})
    with pytest.raises(q3_load.Q3LoadError, match="^CONTRACT_DIGEST_MISMATCH:"):
        q3_load.check_contract_binding(DATA, contract)


@pytest.mark.parametrize("kind", ["pins", "contract", "baselines", "row"])
def test_undecodable_bytes_have_a_loader_error(data_copy, monkeypatch, kind):
    if kind == "pins":
        path = data_copy / "pins.json"
        path.write_bytes(b"\xff")
        monkeypatch.setattr(q3_load, "PINS", path)
        call = lambda: q3_load.check_pins(data_copy)
    elif kind == "contract":
        path = data_copy / "contract.json"
        path.write_bytes(b"\xff")
        call = lambda: q3_load.check_contract_binding(data_copy, path)
    elif kind == "baselines":
        write_data_file(data_copy, "baselines.json", b"\xff")
        call = lambda: q3_load.load_dataset(data_copy, pinned=False)
    else:
        write_data_file(data_copy, "visible_A_train.jsonl", b"\xff", records=1)
        call = lambda: q3_load.load_visible(data_copy, "A", "train")
    with pytest.raises(q3_load.Q3LoadError, match="^NOT_UTF8:"):
        call()


def test_manifest_bad_utf8_retains_manifest_error(data_copy):
    (data_copy / "manifest.json").write_bytes(b"\xff")
    with pytest.raises(q3_load.Q3LoadError, match="^MANIFEST_MALFORMED:"):
        q3_load.manifest_of(data_copy)


def test_oversized_integer_is_a_loader_error():
    previous = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(640)
        with pytest.raises(q3_load.Q3LoadError, match="^MALFORMED_JSON:"):
            q3_load.strict_loads('{"value":' + "1" * 641 + "}", "oversized.json")
        assert q3_load.strict_loads("1" * 639) == int("1" * 639)
    finally:
        sys.set_int_max_str_digits(previous)


@pytest.mark.parametrize("text", ['"\\ud800"', '{"\\udfff": 1}', '{"value": ["\\ud800"]}'])
def test_unpaired_surrogates_never_reach_utf8_hashing(text):
    with pytest.raises(q3_load.Q3LoadError, match="^INVALID_UNICODE:"):
        q3_load.strict_loads(text)


def test_valid_surrogate_pair_and_utf8_remain_accepted():
    assert q3_load.strict_loads('"\\ud834\\udd1e"') == "\U0001d11e"
    assert q3_load.strict_loads('"\U0001d11e"'.encode("utf-8")) == "\U0001d11e"


@pytest.mark.parametrize("value", [[], {}, None])
def test_refusal_kind_cannot_trigger_unhashable_errors(data_copy, value):
    sealed_rows = [json.loads(line) for line in (DATA / "sealed_A_eval.jsonl").read_text(encoding="utf-8").splitlines()]
    index = next(i for i, row in enumerate(sealed_rows) if row["outcome"] == "INVALID_INPUT")
    visible_rows = [json.loads(line) for line in (DATA / "visible_A_eval.jsonl").read_text(encoding="utf-8").splitlines()]
    rid = q3_load._record_id(q3_load.manifest_of(data_copy)["seed"], "A", "train", 0)
    for side, row in (("visible", visible_rows[index]), ("sealed", sealed_rows[index])):
        row["record_id"] = rid
        if side == "sealed":
            row["refusal_kind"] = value
        write_data_file(data_copy, f"{side}_A_train.jsonl", (json.dumps(row) + "\n").encode(), records=1)
    with pytest.raises(q3_load.Q3LoadError, match="^REFUSAL_ROW_CARRIES_AN_ANSWER_OR_AN_UNKNOWN_KIND:"):
        q3_load.load_split(data_copy, "A", "train")


def test_deep_json_and_chains_have_loader_errors():
    previous = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(300)
        with pytest.raises(q3_load.Q3LoadError, match="^MALFORMED_JSON:"):
            q3_load.strict_loads("[" * 400 + "0" + "]" * 400)
        with pytest.raises(q3_load.Q3LoadError, match="^C_CHAIN_UNPARSEABLE:"):
            q3_load.evaluate_chain("compose(" * 400 + "0" + ",0)" * 400)
    finally:
        sys.setrecursionlimit(previous)


def test_recursive_ast_helper_failures_have_a_row_error(data_copy):
    row = json.loads((data_copy / "sealed_R_train.jsonl").read_text(encoding="utf-8"))
    ast = {"node": "Identifier", "name": "x"}
    for _ in range(100):
        ast = {"node": "Group", "child": ast}
    row["target_ast"] = ast
    row["target_canonical_ast"] = json.dumps(ast, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    write_data_file(data_copy, "sealed_R_train.jsonl", (json.dumps(row) + "\n").encode(), records=1)
    previous = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(180)
        with pytest.raises(q3_load.Q3LoadError, match="^ROW_TOO_DEEP:"):
            q3_load.load_split(data_copy, "R", "train")
    finally:
        sys.setrecursionlimit(previous)


@pytest.mark.parametrize("value", [None, [], {}, 7])
def test_direct_chain_input_type_is_refused(value):
    with pytest.raises(q3_load.Q3LoadError, match="^C_CHAIN_UNPARSEABLE:"):
        q3_load.evaluate_chain(value)


@pytest.mark.parametrize("family, split", [("unknown", "train"), ([], "train"), ("A", []), ("A", "unknown")])
def test_unknown_family_or_split_has_a_loader_error(family, split):
    with pytest.raises(q3_load.Q3LoadError, match="^UNKNOWN_FAMILY_OR_SPLIT:"):
        q3_load.load_visible(DATA, family, split)


def test_missing_pin_and_contract_keep_file_error(tmp_path, monkeypatch):
    path = tmp_path / "missing.json"
    monkeypatch.setattr(q3_load, "PINS", path)
    for call in (lambda: q3_load.check_pins(DATA), lambda: q3_load.check_contract_binding(DATA, path)):
        with pytest.raises(q3_load.Q3LoadError, match="^DATA_FILE_MISSING:"):
            call()
