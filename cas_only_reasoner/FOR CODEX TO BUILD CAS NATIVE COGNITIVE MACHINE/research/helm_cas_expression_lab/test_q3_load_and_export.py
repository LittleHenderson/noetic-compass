"""Tests for the lab's load boundary (`q3_load.py`) and the exporter's check mode.

Every refusal is provoked with a REAL edit to a COPY of the committed data: the loader must name what is wrong,
and the exporter must refuse to call anything valid that it could not verify.

Run:  python -m pytest research/helm_cas_expression_lab/test_q3_load_and_export.py -q     (a few seconds)
"""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import q3_load  # noqa: E402

DATA = HERE / "data" / "q3_v0_3"
EXPORTER = HERE / "q3_export_behavior_pairs.py"


@pytest.fixture()
def copy(tmp_path):
    target = tmp_path / "q3"
    shutil.copytree(DATA, target, ignore=shutil.ignore_patterns("*.jsonl.bak"))
    return target


def _rewrite(data_dir, name, change, fix_manifest=True):
    """Edit one data file; by default ALSO update the manifest hash, i.e. a careful forger, so the content checks must catch it."""
    path = data_dir / name
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = change(rows) or rows
    body = ("\n".join(r if isinstance(r, str) else json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + "\n").encode("utf-8")
    path.write_bytes(body)
    if fix_manifest:
        manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
        manifest["files"][name] = {"records": len(rows), "sha256": hashlib.sha256(body).hexdigest()}
        (data_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _code(error):
    return str(error.value).split(":")[0]


# --- the committed data loads cleanly through both doors ------------------------------------------------
def test_every_committed_file_loads_and_rechecks():
    total = 0
    for fam in q3_load.FAMILIES:
        for split in q3_load.SPLITS:
            pairs = q3_load.load_split(DATA, fam, split)
            assert len(pairs) == len(q3_load.load_visible(DATA, fam, split)) > 0
            total += len(pairs)
    assert total == 10376
    assert q3_load.check_contract_binding(DATA) == json.loads((HERE / "OPERATION_CONTRACTS.json").read_text(encoding="utf-8"))["contract_digest"]


# --- refusals ------------------------------------------------------------------------------------------
def test_an_edited_file_is_refused_by_hash(copy):
    _rewrite(copy, "sealed_A_eval.jsonl", lambda rows: rows[:-1] + [dict(rows[-1], trace="edited")], fix_manifest=False)
    with pytest.raises(q3_load.Q3LoadError) as error:
        q3_load.load_split(copy, "A", "eval")
    assert _code(error) == "FILE_HASH_MISMATCH"


def test_a_flipped_answer_is_refused_even_when_the_manifest_was_updated_to_match(copy):
    def flip(rows):
        row = next(r for r in rows if r["outcome"] != "INVALID_INPUT")
        row["target"] = not row["target"]
    _rewrite(copy, "sealed_A_eval.jsonl", flip)
    with pytest.raises(q3_load.Q3LoadError) as error:
        q3_load.load_split(copy, "A", "eval")
    assert _code(error) == "SEALED_TARGET_DISAGREES_WITH_REFERENCE"


def test_an_invalid_row_sealed_as_valid_and_a_valid_row_sealed_as_invalid_are_refused(copy):
    def make_invalid(rows):
        next(r for r in rows if isinstance(r["observation"].get("operator"), int) and not isinstance(r["observation"]["operator"], bool)
             and 0 <= r["observation"]["operator"] <= 9 and set(r["observation"]) == {"operator", "source", "target"}
             and r["observation"]["source"][0] in "PCEO" and isinstance(r["observation"]["source"][1], int))["observation"]["operator"] = True
    _rewrite(copy, "visible_A_dev.jsonl", make_invalid)
    with pytest.raises(q3_load.Q3LoadError) as error:
        q3_load.load_split(copy, "A", "dev")
    assert _code(error) in ("REFERENCE_REFUSES_A_ROW_SEALED_AS_VALID", "SEALED_SAYS_INVALID_BUT_REFERENCE_ACCEPTS")


def test_nan_duplicate_keys_duplicate_ids_and_non_objects_are_refused(copy):
    cases = [
        (lambda rows: rows[:1] + ['{"record_id": "x1", "family": "C", "observation": NaN}'] + rows[1:], "NONFINITE_NUMBER"),
        (lambda rows: rows[:1] + ['{"record_id": "x2", "record_id": "x3", "family": "C"}'] + rows[1:], "DUPLICATE_JSON_KEYS"),
        (lambda rows: rows + [dict(rows[0])], "DUPLICATE_RECORD_ID"),
        (lambda rows: rows + ['["not", "an", "object"]'], "ROW_NOT_AN_OBJECT"),
        (lambda rows: rows + ['{"family": "C", "observation": "3"}'], "MISSING_RECORD_ID"),
    ]
    for change, expected in cases:
        shutil.copy(DATA / "visible_C_dev.jsonl", copy / "visible_C_dev.jsonl")
        shutil.copy(DATA / "manifest.json", copy / "manifest.json")
        _rewrite(copy, "visible_C_dev.jsonl", change)
        with pytest.raises(q3_load.Q3LoadError) as error:
            q3_load.load_visible(copy, "C", "dev")
        assert _code(error) == expected, (expected, str(error.value))


def test_a_visible_file_carrying_a_withheld_field_is_refused(copy):
    _rewrite(copy, "visible_A_train.jsonl", lambda rows: [dict(rows[0], target=True)] + rows[1:])
    with pytest.raises(q3_load.Q3LoadError) as error:
        q3_load.load_visible(copy, "A", "train")
    assert _code(error) == "WITHHELD_OR_UNDECLARED_FIELD_IN_VISIBLE_FILE"


def test_data_bound_to_another_contract_is_refused(copy):
    manifest = json.loads((copy / "manifest.json").read_text(encoding="utf-8"))
    manifest["operation_contracts_digest"] = "e97b8aa60195563b9a073c727452e1ed321ed8a83248d1267e535c59662d6d01"      # what v0.2 still cites
    (copy / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(q3_load.Q3LoadError) as error:
        q3_load.check_contract_binding(copy)
    assert _code(error) == "CONTRACT_DIGEST_MISMATCH"
    # and the committed v0.2 data set really is in that state -- kept on disk as the reviewed artifact, refused for use
    with pytest.raises(q3_load.Q3LoadError):
        q3_load.check_contract_binding(HERE / "data" / "q3_v0_2")


# --- the exporter ---------------------------------------------------------------------------------------
def _export(*args):
    return subprocess.run([sys.executable, str(EXPORTER), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_check_mode_matches_the_committed_report_and_writes_nothing():
    report = DATA / "sealed_view" / "EXPORT_REPORT.json"
    before = report.read_bytes()
    run = _export()
    assert run.returncode == 0 and "Q3_EXPORT_CHECK_PASS" in run.stdout and run.stdout.count("EXPORT_MATCH") == 12, run.stdout[-600:]
    assert report.read_bytes() == before
    committed = json.loads(before.decode("utf-8"))
    assert sum(f["records"] for f in committed["files"].values()) == 10376 and chr(92) not in before.decode("utf-8")


def test_check_mode_reports_drift_and_does_not_repair_the_report(copy):
    report = copy / "sealed_view" / "EXPORT_REPORT.json"
    data = json.loads(report.read_text(encoding="utf-8"))
    data["files"]["behavior_pairs_A_eval.jsonl"]["sha256"] = "0" * 64
    report.write_text(json.dumps(data), encoding="utf-8")
    before = report.read_bytes()
    run = _export("--data", str(copy))
    assert run.returncode == 1 and "EXPORT_DRIFT behavior_pairs_A_eval.jsonl" in run.stdout and "Q3_EXPORT_CHECK_FAIL" in run.stdout
    assert report.read_bytes() == before


def test_the_exporter_refuses_tampered_or_misbound_data(copy):
    def flip(rows):
        row = next(r for r in rows if r["outcome"] != "INVALID_INPUT")
        row["target"] = not row["target"]
    _rewrite(copy, "sealed_A_train.jsonl", flip)
    run = _export("--data", str(copy))
    assert run.returncode == 2 and "EXPORT_REFUSED:SEALED_TARGET_DISAGREES_WITH_REFERENCE" in run.stdout
    run = _export("--data", str(HERE / "data" / "q3_v0_2"))
    assert run.returncode == 2 and "EXPORT_REFUSED:CONTRACT_DIGEST_MISMATCH" in run.stdout


def test_the_exporter_source_fails_closed_without_a_validator():
    source = EXPORTER.read_text(encoding="utf-8")
    assert "VALIDATOR_MISSING" in source and "validator = None" not in source and "if validator is not None" not in source


# --- separation -----------------------------------------------------------------------------------------
def test_no_learner_file_uses_the_evaluators_door():
    offenders = [p.name for p in HERE.rglob("learner*.py") if re.search(r"load_split|sealed_", p.read_text(encoding="utf-8"))]
    assert not offenders, "EVALUATOR_DOOR_USED_BY_A_LEARNER:%s" % offenders
