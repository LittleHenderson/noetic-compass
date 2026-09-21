"""Tests for the lab's load boundary (`q3_load.py` 0.2) and the exporter's check mode.

Every refusal is provoked with a REAL edit to a COPY of the committed data, and the forger is CAREFUL: unless a test
says otherwise the copy's manifest hash and row count are updated to match the edit, so only a content check can
catch it. Most cases below are the exact forgeries an attacker got past loader 0.1 on 2026-09-21.

Run:  python -m pytest research/helm_cas_expression_lab/test_q3_load_and_export.py -q     (about 20 seconds)
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

DATA = HERE / "data" / "q3_v0_4"
EXPORTER = HERE / "q3_export_behavior_pairs.py"


@pytest.fixture()
def copy(tmp_path):
    target = tmp_path / "q3"
    shutil.copytree(DATA, target)
    return target


def _read(data_dir, name):
    return [json.loads(line) for line in (data_dir / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def _write(data_dir, name, rows):
    body = ("\n".join(r if isinstance(r, str) else json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + "\n").encode("utf-8")
    (data_dir / name).write_bytes(body)
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"][name] = {"records": len(rows), "sha256": hashlib.sha256(body).hexdigest()}
    (data_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _forge(data_dir, name, change):
    rows = _read(data_dir, name)
    result = change(rows)                                   # a change may edit in place (and return anything) or return a new list
    _write(data_dir, name, result if isinstance(result, list) else rows)


def _refused(code, call):
    with pytest.raises(q3_load.Q3LoadError) as error:
        call()
    assert str(error.value).split(":")[0] == code, str(error.value)


def _first_valid(rows):
    return next(r for r in rows if r["outcome"] != "INVALID_INPUT")


# --- the committed data ----------------------------------------------------------------------------------
def test_the_committed_data_set_loads_whole_pinned_and_bound():
    data = q3_load.load_dataset(DATA)
    assert sum(len(data[f][s]) for f in q3_load.FAMILIES for s in q3_load.SPLITS) == 10421
    assert q3_load.check_contract_binding(DATA) == json.loads((HERE / "OPERATION_CONTRACTS.json").read_text(encoding="utf-8"))["contract_digest"]
    assert q3_load.verification_level("A").startswith("RECOMPUTED") and q3_load.verification_level("G").startswith("STRUCTURE_CHECKED__TARGET_NOT_RECOMPILED")


# --- who may see what is fixed in code, not in the file a forger edits -------------------------------------
def test_answers_cannot_be_put_into_the_learners_file(copy):
    _forge(copy, "visible_A_eval.jsonl", lambda rows: [dict(r, target=True) for r in rows])            # rows edited, manifest lists untouched
    _refused("ROW_KEYS_WRONG", lambda: q3_load.load_visible(copy, "A", "eval"))
    manifest = json.loads((copy / "manifest.json").read_text(encoding="utf-8"))                       # the forgery that beat loader 0.1
    manifest["visibility"]["A"]["visible"].append("target")
    manifest["visibility"]["A"]["withheld"].remove("target")
    (copy / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _refused("VISIBILITY_POLICY_EDITED", lambda: q3_load.load_visible(copy, "A", "eval"))
    _refused("VISIBILITY_POLICY_EDITED", lambda: q3_load.load_split(copy, "A", "eval"))


# --- family A ------------------------------------------------------------------------------------------------
def test_family_A_every_sealed_field_is_recomputed_or_fixed(copy):
    cases = [
        (lambda r: r.update(target=not r["target"]), "SEALED_TARGET_DISAGREES_WITH_REFERENCE"),
        (lambda r: r.update(target=int(r["target"])), "SEALED_TARGET_DISAGREES_WITH_REFERENCE"),
        (lambda r: r.update(order_flip=not r["order_flip"]), "SEALED_TARGET_DISAGREES_WITH_REFERENCE"),
        (lambda r: r.update(cell="9:O>O"), "CELL_WRONG"),
        (lambda r: r.update(case_family="op0_cross_domain" if r["case_family"] != "op0_cross_domain" else "op0_same_domain"), "CASE_FAMILY_WRONG"),
        (lambda r: r.pop("case_family"), "ROW_KEYS_WRONG"),
        (lambda r: r.update(outcome="WHATEVER"), "ROW_KEYS_WRONG"),
        (lambda r: r.update(extra="smuggled"), "ROW_KEYS_WRONG"),
        (lambda r: r.pop("oracle"), "ROW_KEYS_WRONG"),
    ]
    for change, code in cases:
        shutil.copy(DATA / "sealed_A_eval.jsonl", copy / "sealed_A_eval.jsonl")
        _forge(copy, "sealed_A_eval.jsonl", lambda rows: change(_first_valid(rows)))
        _refused(code, lambda: q3_load.load_split(copy, "A", "eval"))


def test_a_refusal_row_may_not_carry_an_answer(copy):
    def change(rows):
        next(r for r in rows if r["outcome"] == "INVALID_INPUT").update(target=True, cell="0:P>P", order_flip=True)
    _forge(copy, "sealed_A_eval.jsonl", change)
    _refused("REFUSAL_ROW_CARRIES_AN_ANSWER_OR_AN_UNKNOWN_KIND", lambda: q3_load.load_split(copy, "A", "eval"))


def test_a_valid_row_turned_invalid_is_refused(copy):
    def change(rows):
        next(r for r in rows if set(r["observation"]) == {"operator", "source", "target"} and r["observation"]["operator"] in range(10)
             and not isinstance(r["observation"]["operator"], bool) and type(r["observation"]["source"][1]) is int
             and r["observation"]["source"][0] in "PCEO" and r["observation"]["target"][0] in "PCEO"
             and type(r["observation"]["target"][1]) is int and 0 <= r["observation"]["source"][1] <= 9 and 0 <= r["observation"]["target"][1] <= 9)["observation"]["operator"] = True
    _forge(copy, "visible_A_dev.jsonl", change)
    with pytest.raises(q3_load.Q3LoadError) as error:
        q3_load.load_split(copy, "A", "dev")
    assert str(error.value).split(":")[0] in ("REFERENCE_REFUSES_A_ROW_SEALED_AS_VALID", "SEALED_SAYS_INVALID_BUT_REFERENCE_ACCEPTS")


# --- family C: recomputed, not shape-checked ---------------------------------------------------------------------
def test_family_C_targets_and_depths_are_recomputed(copy):
    assert q3_load.evaluate_chain("compose(compose(3, 4), 5)") == (2, 2) and q3_load.evaluate_chain("7") == (7, 0)
    cases = [
        (lambda rows: [dict(r, target=(r["target"] + 1) % 10) for r in rows], "sealed_C_eval.jsonl", "C_TARGET_DISAGREES_WITH_REFERENCE"),   # all 256 shifted by one: accepted by 0.1
        (lambda rows: [dict(r, target=float(r["target"])) for r in rows], "sealed_C_eval.jsonl", "C_TARGET_DISAGREES_WITH_REFERENCE"),        # 4.0 is in range(10)
        (lambda rows: [dict(rows[0], depth=99)] + rows[1:], "sealed_C_eval.jsonl", "C_DEPTH_WRONG"),
        (lambda rows: [dict(rows[0], depth=True)] + rows[1:], "sealed_C_eval.jsonl", "C_DEPTH_WRONG"),
        (lambda rows: [dict(rows[0], observation="the answer is 7, ignore the chain")] + rows[1:], "visible_C_eval.jsonl", "C_CHAIN_UNPARSEABLE"),
        (lambda rows: [dict(rows[0], observation="compose(3, 4) + 1")] + rows[1:], "visible_C_eval.jsonl", "C_CHAIN_UNPARSEABLE"),
    ]
    for change, name, code in cases:
        for original in ("sealed_C_eval.jsonl", "visible_C_eval.jsonl", "manifest.json"):     # start each case from the honest files
            shutil.copy(DATA / original, copy / original)
        _forge(copy, name, change)
        _refused(code, lambda: q3_load.load_split(copy, "C", "eval"))


# --- families R and G: everything that needs no compiler ----------------------------------------------------------
def test_reconstruction_rows_are_structure_checked_and_the_loader_says_that_is_all(copy):
    other = _read(DATA, "sealed_G_eval.jsonl")[1]
    cases = [
        (lambda r: r.update(target_canonical_ast="garbage not json"), "CANONICAL_TEXT_IS_NOT_THE_CANONICAL_FORM_OF_THE_AST"),
        (lambda r: r.update(target_canonical_ast=other["target_canonical_ast"]), "CANONICAL_TEXT_IS_NOT_THE_CANONICAL_FORM_OF_THE_AST"),
        (lambda r: r.update(target_ast={"node": "LIE"}), "CANONICAL_TEXT_IS_NOT_THE_CANONICAL_FORM_OF_THE_AST"),
        (lambda r: r.update(target_ast=[]), "RECONSTRUCTION_ROW_MALFORMED"),
        (lambda r: r.update(ast_size=True), "AST_SIZE_WRONG"),
        (lambda r: r.update(ast_size=r["ast_size"] + 1), "AST_SIZE_WRONG"),
        (lambda r: r.update(shape_key="0" * 16), "SHAPE_KEY_WRONG"),
        (lambda r: r.update(tree_shape_key="0" * 16), "TREE_SHAPE_OR_DEPTH_WRONG"),
        (lambda r: r.update(depth="deep"), "TREE_SHAPE_OR_DEPTH_WRONG"),
        (lambda r: r.update(validity="MAYBE"), "ROW_KEYS_WRONG"),
    ]
    for change, code in cases:
        shutil.copy(DATA / "sealed_G_eval.jsonl", copy / "sealed_G_eval.jsonl")
        _forge(copy, "sealed_G_eval.jsonl", lambda rows: change(rows[0]))
        _refused(code, lambda: q3_load.load_split(copy, "G", "eval"))
    # a target written in the compiler's spelling is not the lab form (owner ruling: ^0 .. ^9)
    shutil.copy(DATA / "sealed_G_eval.jsonl", copy / "sealed_G_eval.jsonl")
    import q3_behaviour_records as q3

    def respell(rows):
        ast = q3.to_compiler_spelling(rows[0]["target_ast"])
        rows[0].update(target_ast=ast, target_canonical_ast=q3.canonical(ast))
    _forge(copy, "sealed_G_eval.jsonl", respell)
    _refused("TARGET_SPELLING_NOT_THE_LAB_FORM", lambda: q3_load.load_split(copy, "G", "eval"))


# --- record ids, files, manifest ---------------------------------------------------------------------------------------
def test_record_ids_are_rederived_from_position(copy):
    def swap(rows):
        a, b = [i for i, r in enumerate(rows) if r["outcome"] != "INVALID_INPUT" and r["target"] is False][:2]
        rows[a]["record_id"], rows[b]["record_id"] = rows[b]["record_id"], rows[a]["record_id"]
    _forge(copy, "sealed_A_eval.jsonl", swap)                       # two rows with EQUAL answers swap ids: accepted by 0.1
    _refused("RECORD_ID_NOT_POSITIONAL", lambda: q3_load.load_split(copy, "A", "eval"))
    shutil.copy(DATA / "visible_C_dev.jsonl", copy / "visible_C_dev.jsonl")
    _forge(copy, "visible_C_dev.jsonl", lambda rows: [dict(rows[0], record_id="forged-id")] + rows[1:])
    _refused("RECORD_ID_NOT_POSITIONAL", lambda: q3_load.load_visible(copy, "C", "dev"))


def test_strict_parsing_and_file_level_refusals(copy):
    cases = [
        (lambda rows: rows[:1] + ['{"record_id": "x1", "family": "C", "observation": NaN}'] + rows[1:], "NONFINITE_NUMBER"),
        (lambda rows: rows[:1] + ['{"record_id": "x2", "record_id": "x3", "family": "C"}'] + rows[1:], "DUPLICATE_JSON_KEYS"),
        (lambda rows: rows + ['["not", "an", "object"]'], "ROW_NOT_AN_OBJECT"),
        (lambda rows: rows + ['{"family": "C", "observation": "3"}'], "MISSING_RECORD_ID"),
        (lambda rows: rows + [dict(rows[0])], "DUPLICATE_RECORD_ID"),
    ]
    for change, code in cases:
        shutil.copy(DATA / "visible_C_dev.jsonl", copy / "visible_C_dev.jsonl")
        _forge(copy, "visible_C_dev.jsonl", change)
        _refused(code, lambda: q3_load.load_visible(copy, "C", "dev"))
    shutil.copy(DATA / "manifest.json", copy / "manifest.json")
    shutil.copy(DATA / "visible_C_dev.jsonl", copy / "visible_C_dev.jsonl")
    (copy / "visible_C_dev.jsonl").write_bytes((copy / "visible_C_dev.jsonl").read_bytes() + b" ")     # edited, manifest NOT updated
    _refused("FILE_HASH_MISMATCH", lambda: q3_load.load_visible(copy, "C", "dev"))
    (copy / "visible_C_dev.jsonl").unlink()
    _refused("DATA_FILE_MISSING", lambda: q3_load.load_visible(copy, "C", "dev"))
    (copy / "manifest.json").write_text('["a", "list"]', encoding="utf-8")
    _refused("MANIFEST_MALFORMED", lambda: q3_load.load_visible(copy, "C", "eval"))
    (copy / "manifest.json").write_text('{"files": {}, "seed": NaN}', encoding="utf-8")
    _refused("NONFINITE_NUMBER", lambda: q3_load.load_visible(copy, "C", "eval"))


# --- the data set as a whole ------------------------------------------------------------------------------------------
def _append_eval_to_train_with_positional_ids(copy, family):
    seed = json.loads((copy / "manifest.json").read_text(encoding="utf-8"))["seed"]
    for kind in ("visible", "sealed"):
        train, extra = _read(copy, "%s_%s_train.jsonl" % (kind, family)), _read(copy, "%s_%s_eval.jsonl" % (kind, family))
        for offset, row in enumerate(extra):
            row["record_id"] = q3_load._record_id(seed, family, "train", len(train) + offset)       # a CAREFUL forger fixes the ids
        _write(copy, "%s_%s_train.jsonl" % (kind, family), train + extra)


@pytest.mark.parametrize("family", ["A", "C", "G"])
def test_eval_rows_copied_into_train_are_refused(copy, family):
    _append_eval_to_train_with_positional_ids(copy, family)          # accepted by 0.1 for A, C and G; --write and check then PASSED
    _refused("SPLITS_NOT_DISJOINT", lambda: q3_load.load_dataset(copy, pinned=False))


def test_whole_data_set_refusals(copy):
    (copy / "visible_A_extra.jsonl").write_text('{"record_id": "x", "target": true}\n', encoding="utf-8")
    _refused("UNDECLARED_FILE_ON_DISK", lambda: q3_load.load_dataset(copy, pinned=False))
    (copy / "visible_A_extra.jsonl").unlink()
    body = json.loads((copy / "baselines.json").read_text(encoding="utf-8"))
    body["A"]["eval"]["DISCOVERY PROVEN"] = {"exact": 1.0}
    (copy / "baselines.json").write_text(json.dumps(body), encoding="utf-8")
    _refused("BASELINES_NOT_THE_HASHED_ONES", lambda: q3_load.load_dataset(copy, pinned=False))
    shutil.copy(DATA / "baselines.json", copy / "baselines.json")
    for kind in ("visible", "sealed"):                              # every ^0 row removed from eval, ids kept positional by dropping from the END is impossible,
        rows = _read(copy, "%s_A_eval.jsonl" % kind)                # so the forger empties the split instead
        _write(copy, "%s_A_eval.jsonl" % kind, [])
    _refused("EMPTY_SPLIT", lambda: q3_load.load_dataset(copy, pinned=False))


def test_a_forged_copy_cannot_carry_the_pin(copy):
    manifest = json.loads((copy / "manifest.json").read_text(encoding="utf-8"))
    manifest["family_labels"]["A"] = "DISCOVERY PROVEN"             # prose only; every data file untouched
    (copy / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _refused("MANIFEST_NOT_THE_PINNED_ONE", lambda: q3_load.load_dataset(copy))
    pins = json.loads(q3_load.PINS.read_text(encoding="utf-8"))
    assert pins["data_versions"][json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))["schema"]]["manifest_sha256"] == q3_load.manifest_sha(DATA)
    assert not (DATA / q3_load.PINS.name).exists() and q3_load.PINS.parent == HERE        # the pins live OUTSIDE the data folder


def test_data_bound_to_another_contract_is_refused(copy):
    manifest = json.loads((copy / "manifest.json").read_text(encoding="utf-8"))
    manifest["operation_contracts_digest"] = "e97b8aa60195563b9a073c727452e1ed321ed8a83248d1267e535c59662d6d01"      # what v0.2 still cites
    (copy / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _refused("CONTRACT_DIGEST_MISMATCH", lambda: q3_load.check_contract_binding(copy))
    for old in ("q3_v0_2", "q3_v0_3"):                              # kept on disk as reviewed artifacts; refused for use
        with pytest.raises(q3_load.Q3LoadError):
            q3_load.load_dataset(HERE / "data" / old)


# --- the exporter -----------------------------------------------------------------------------------------------------
def _export(*args):
    return subprocess.run([sys.executable, str(EXPORTER), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_check_mode_matches_the_pinned_report_and_writes_nothing():
    report = DATA / "sealed_view" / "EXPORT_REPORT.json"
    before = report.read_bytes()
    run = _export()
    assert run.returncode == 0 and "Q3_EXPORT_CHECK_PASS" in run.stdout and run.stdout.count("EXPORT_MATCH") == 12, run.stdout[-600:]
    assert report.read_bytes() == before
    committed = json.loads(before.decode("utf-8"))
    assert sum(f["records"] for f in committed["files"].values()) == 10421 and chr(92) not in before.decode("utf-8")
    assert committed["verification"]["C"].startswith("RECOMPUTED") and "NOT_RECOMPILED" in committed["verification"]["R"]


def test_check_mode_reports_drift_and_never_repairs(copy):
    report = copy / "sealed_view" / "EXPORT_REPORT.json"
    data = json.loads(report.read_text(encoding="utf-8"))
    data["files"]["behavior_pairs_A_eval.jsonl"]["sha256"] = "0" * 64
    report.write_text(json.dumps(data), encoding="utf-8")
    before = report.read_bytes()
    run = _export("--data", str(copy))
    assert run.returncode == 1 and "EXPORT_DRIFT behavior_pairs_A_eval.jsonl" in run.stdout and "not the pinned report" in run.stdout
    assert report.read_bytes() == before
    shutil.copy(DATA / "sealed_view" / "EXPORT_REPORT.json", report)                                  # a forged DERIVED file on disk
    (copy / "sealed_view" / "behavior_pairs_C_eval.jsonl").write_text('{"forged": true}\n', encoding="utf-8")
    run = _export("--data", str(copy))
    assert run.returncode == 1 and "EXPORT_DRIFT behavior_pairs_C_eval.jsonl" in run.stdout


def test_the_exporter_refuses_forged_and_superseded_data(copy):
    _forge(copy, "sealed_C_eval.jsonl", lambda rows: [dict(r, target=(r["target"] + 1) % 10) for r in rows])
    run = _export("--data", str(copy))
    assert run.returncode == 2 and "EXPORT_REFUSED:MANIFEST_NOT_THE_PINNED_ONE" in run.stdout          # the careful forger had to touch the manifest
    for old in ("q3_v0_2", "q3_v0_3"):
        run = _export("--data", str(HERE / "data" / old))
        assert run.returncode == 2 and "EXPORT_REFUSED" in run.stdout
    source = EXPORTER.read_text(encoding="utf-8")
    assert "VALIDATOR_MISSING" in source and "validator = None" not in source and "json.loads(report" not in source


# --- separation ---------------------------------------------------------------------------------------------------------
def test_no_learner_file_uses_an_evaluators_door():
    offenders = [p.name for p in HERE.rglob("learner*.py") if re.search(r"load_split|load_dataset|sealed_", p.read_text(encoding="utf-8"))]
    assert not offenders, "EVALUATOR_DOOR_USED_BY_A_LEARNER:%s" % offenders
