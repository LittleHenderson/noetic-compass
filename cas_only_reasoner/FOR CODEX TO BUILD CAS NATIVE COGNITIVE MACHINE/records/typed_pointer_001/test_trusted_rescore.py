"""T01 tamper suite -- every rejection the directive's Q0 names must FIRE, on a real receipt, with a real edit.

Each test copies the certified Helm 1.0 seed 20260918's four scoring/prediction files into a temp receipt,
builds a one-seed study and a fresh anchor for it, performs ONE named edit, rescores, and asserts the typed
REJECT code. The clean copy must pass first, or nothing below means anything; that one run also goes through
the command line (exit code 0). The committed readings for both studies are checked at the end: the rescore
must AGREE with the frozen grader on the label and on every seed's gained/broken counts.

Cost: loading the frozen course re-validates every public world for all 564 packets (minutes), so the suite
loads it ONCE and passes it to `rescore(..., material=...)`; every tampered run still rechecks all 1,128
predictions with the private checker (about a minute each). Budget roughly 15 minutes for the whole file.

Run:  python -m pytest records/typed_pointer_001/test_trusted_rescore.py -q
"""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import trusted_rescore as T  # noqa: E402

RESCORE = HERE / "trusted_rescore.py"
CERTIFIED_SEED = "20260918"
SOURCE_RECEIPT = HERE / ("receipt_helm1_certified_%s" % CERTIFIED_SEED) / "collected/results/artifacts"
FILES = ["course_p00_predictions.json", "course_p00_scoring.json", "course_p10_predictions.json", "course_p10_scoring.json"]


@pytest.fixture(scope="module")
def material():
    return T._load_frozen_and_checker()


@pytest.fixture(scope="module")
def sandbox(material):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="trusted_rescore_"))
    art = tmp / "receipt" / "collected/results/artifacts"
    art.mkdir(parents=True)
    for name in FILES:
        shutil.copy(SOURCE_RECEIPT / name, art / name)
    study = json.loads((HERE / "study_helm1_certified.json").read_text(encoding="utf-8"))
    study["jobs"] = [dict(j, receipt_dir=str(tmp / "receipt")) for j in study["jobs"] if str(j["model_seed"]) == CERTIFIED_SEED]
    (tmp / "study.json").write_text(json.dumps(study), encoding="utf-8")
    assert T.write_anchor(tmp / "study.json", tmp / "anchor.json", {}, material=material) == 0
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def run(tmp, material):
    """Rescore the sandbox in-process (the loaded material is reused) and return the reading."""
    out = tmp / "reading.json"
    if out.exists():
        out.unlink()
    T.rescore(tmp / "study.json", tmp / "anchor.json", {}, out, material=material)
    return json.loads(out.read_text(encoding="utf-8"))


def run_cli(tmp):
    """The same rescore through the command line: returns (exit code, reading)."""
    out = tmp / "reading_cli.json"
    proc = subprocess.run([sys.executable, str(RESCORE), "--study", str(tmp / "study.json"), "--anchor", str(tmp / "anchor.json"), "--out", str(out)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert out.is_file(), proc.stdout[-800:] + proc.stderr[-800:]
    return proc.returncode, json.loads(out.read_text(encoding="utf-8"))


def restore(tmp, name):
    shutil.copy(SOURCE_RECEIPT / name, tmp / "receipt/collected/results/artifacts" / name)


def art(tmp, name):
    return tmp / "receipt/collected/results/artifacts" / name


def reasons(reading):
    return [r.split(":")[0] for r in reading["reject_reasons"]]


# --- the clean copy must pass, or nothing below means anything --------------------------------
def test_clean_copy_rescores_ok_and_reproduces_the_certified_numbers(sandbox, material):
    code, r = run_cli(sandbox)          # the one command-line run: exit code 0 on RESCORE_OK
    assert code == 0, r["reject_reasons"]
    assert r["verdict"] == "RESCORE_OK", r["reject_reasons"]
    s = r["per_seed"][CERTIFIED_SEED]
    # the frozen grader's reading for this seed: wrong_to_right 12, right_to_wrong 0 (admission_helm1_certified/gate_reading.json)
    assert (s["gained"], s["broken"]) == (12, 0)
    assert s["frozen_18_after"] == s["frozen_18_before"] + 12
    assert all(s["phases"][ph]["rescored"] == 564 and s["phases"][ph]["disagreements"] == 0 for ph in ("course_p00", "course_p10"))
    assert r["custody"].startswith("EVALUATION_NOT_INDEPENDENT")


# --- altered scores ----------------------------------------------------------------------------
def test_altered_scoring_file_is_rejected(sandbox, material):
    path = art(sandbox, "course_p10_scoring.json")
    d = json.loads(path.read_text(encoding="utf-8"))
    for row in d["rows"][:20]:
        row["correct"] = not row["correct"]
    path.write_text(json.dumps(d), encoding="utf-8")
    try:
        r = run(sandbox, material)
        assert r["verdict"] == "REJECT" and "SCORING_FILE_DISAGREES_WITH_RESCORE" in reasons(r)
    finally:
        restore(sandbox, "course_p10_scoring.json")


def test_altered_scores_plus_rewritten_manifest_is_still_rejected(sandbox, material):
    path = art(sandbox, "course_p10_scoring.json")
    d = json.loads(path.read_text(encoding="utf-8"))
    for row in d["rows"][:20]:
        row["correct"] = not row["correct"]
    body = json.dumps(d).encode("utf-8")
    path.write_bytes(body)
    # a "successful" forgery from the manifest's point of view: the manifest now matches the tampered bytes
    manifest = [{"name": "course_p10_scoring.json", "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}]
    (sandbox / "receipt" / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    try:
        r = run(sandbox, material)
        assert r["verdict"] == "REJECT" and "SCORING_FILE_DISAGREES_WITH_RESCORE" in reasons(r)
    finally:
        restore(sandbox, "course_p10_scoring.json")


# --- evaluator substitution ----------------------------------------------------------------------
def test_evaluator_substitution_is_rejected(sandbox, material):
    anchor = sandbox / "anchor.json"
    a = json.loads(anchor.read_text(encoding="utf-8"))
    good = a["grader"]["sha256_lf"]
    a["grader"]["sha256_lf"] = "0" * 64
    anchor.write_text(json.dumps(a), encoding="utf-8")
    try:
        r = run(sandbox, material)
        assert r["verdict"] == "REJECT" and "EVALUATOR_IDENTITY" in reasons(r)
    finally:
        a["grader"]["sha256_lf"] = good
        anchor.write_text(json.dumps(a), encoding="utf-8")


# --- wrong split / phase --------------------------------------------------------------------------
def test_wrong_phase_predictions_are_rejected(sandbox, material):
    shutil.copy(art(sandbox, "course_p00_predictions.json"), art(sandbox, "course_p10_predictions.json"))
    try:
        r = run(sandbox, material)
        assert r["verdict"] == "REJECT" and "PREDICTIONS_IDENTITY" in reasons(r)
    finally:
        restore(sandbox, "course_p10_predictions.json")


# --- duplicates, missing, extra -------------------------------------------------------------------
def test_duplicate_prediction_ids_are_rejected(sandbox, material):
    path = art(sandbox, "course_p10_predictions.json")
    d = json.loads(path.read_text(encoding="utf-8"))
    d["predictions"].append(dict(d["predictions"][0]))
    path.write_text(json.dumps(d), encoding="utf-8")
    try:
        r = run(sandbox, material)
        assert r["verdict"] == "REJECT" and "DUPLICATE_IDS" in reasons(r)
    finally:
        restore(sandbox, "course_p10_predictions.json")


def test_missing_prediction_is_rejected(sandbox, material):
    path = art(sandbox, "course_p10_predictions.json")
    d = json.loads(path.read_text(encoding="utf-8"))
    d["predictions"].pop()
    path.write_text(json.dumps(d), encoding="utf-8")
    try:
        r = run(sandbox, material)
        assert r["verdict"] == "REJECT" and "MISSING_OR_EXTRA_PREDICTIONS" in reasons(r)
    finally:
        restore(sandbox, "course_p10_predictions.json")


# --- malformed and non-finite --------------------------------------------------------------------
def test_malformed_prediction_is_rejected(sandbox, material):
    path = art(sandbox, "course_p10_predictions.json")
    d = json.loads(path.read_text(encoding="utf-8"))
    d["predictions"][3]["answer"] = "this is not an answer"       # the checker raises AnswerContractError TYPED_ANSWER_FIELDS
    path.write_text(json.dumps(d), encoding="utf-8")
    try:
        r = run(sandbox, material)
        assert r["verdict"] == "REJECT" and "MALFORMED_PREDICTION" in reasons(r)
    finally:
        restore(sandbox, "course_p10_predictions.json")


def test_nonfinite_number_is_rejected(sandbox, material):
    path = art(sandbox, "course_p10_predictions.json")
    d = json.loads(path.read_text(encoding="utf-8"))
    d["predictions"][5]["scores"] = {"typed-slot-x": {"ABSENT": float("nan"), "PRESENT": 0.0}}
    path.write_text(json.dumps(d), encoding="utf-8")       # json emits NaN; the rescorer must catch it
    try:
        r = run(sandbox, material)
        assert r["verdict"] == "REJECT" and "NONFINITE_NUMBER" in reasons(r)
    finally:
        restore(sandbox, "course_p10_predictions.json")


# --- the committed readings must agree with the frozen grader ----------------------------------------
@pytest.mark.parametrize("name,expected_label", [("helm1_certified", "LEARNS_NEW_WORLDS"), ("helm2_experimental", "NO_TRANSFER_TO_NEW_WORLDS")])
def test_committed_reading_agrees_with_the_frozen_grader(name, expected_label):
    r = json.loads((HERE / ("trusted_rescore_reading_%s.json" % name)).read_text(encoding="utf-8"))
    assert r["verdict"] == "RESCORE_OK", r["reject_reasons"]
    assert r["label_rederived"] == expected_label
    c = r["comparison_with_frozen_grader"]
    assert c["frozen_reading_present"] and c["labels_agree"] is True and all(v["agree"] for v in c["per_seed"].values())
    for s in r["per_seed"].values():
        assert all(s["phases"][ph]["rescored"] == 564 and s["phases"][ph]["disagreements"] == 0 for ph in ("course_p00", "course_p10"))


def test_anchors_exist_and_declare_custody():
    for name in ("trust_anchor_helm1_certified.json", "trust_anchor_helm2_experimental_20208c92.json"):
        a = json.loads((HERE / name).read_text(encoding="utf-8"))
        assert a["custody"].startswith("EVALUATION_NOT_INDEPENDENT")
        assert a["grader"]["sha256_lf"] == hashlib.sha256((HERE / "evaluate_gates.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        assert a["population"]["digest"] == "4b1e3c1f0b8f8be339e281410dc830fac1834432e8d816d67dce58906e90036d"
