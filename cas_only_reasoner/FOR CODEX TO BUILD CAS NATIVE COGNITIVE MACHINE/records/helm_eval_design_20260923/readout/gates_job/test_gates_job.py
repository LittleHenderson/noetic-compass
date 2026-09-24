"""Tests for the gates job (readout item 7). CLAUDE_BUILT_CLAUDE_CHECKED.

The stated acceptance check: a laptop dry run (NO AWS call) builds the bundle, passes the custody filters, prints the
plan and the cap; mode 2 refuses without ITEM2_PASS. Plus the small pure-Python parts the machine and the reader use.
No AWS call anywhere: every launcher subprocess runs with `boto3` and `botocore` replaced by modules that raise on
import. No torch. No course load. The one heavy test streams about 420 MB of git objects into a bundle in a temp folder
(outside every git tree) and deletes it afterwards.

    python -m pytest test_gates_job.py -q -p no:cacheprovider
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import launch as L  # noqa: E402
import machine_gates as MG  # noqa: E402
import read_results as RR  # noqa: E402

GOOD_H1 = {"20260917": [11, 1], "20260918": [12, 0], "20260919": [7, 1]}


@pytest.fixture(scope="module")
def no_aws(tmp_path_factory):
    """An environment in which importing boto3 or botocore raises: any AWS call attempt fails the test loudly."""
    root = tmp_path_factory.mktemp("no_aws")
    for name in ("boto3", "botocore"):
        (root / name).mkdir()
        (root / name / "__init__.py").write_text("raise RuntimeError('AWS_CALL_ATTEMPTED: %s was imported')\n" % name)
    return dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1")


def run_launch(env, *args, timeout=900):
    return subprocess.run([sys.executable, "-B", str(HERE / "launch.py"), *args], capture_output=True, text=True,
                          env=env, timeout=timeout)


@pytest.fixture(scope="module")
def committed_reading():
    """The committed Helm 2.0 gate reading, read from git objects at the rescorer commit (about 200 KB)."""
    blobs = L.Blobs()
    try:
        return blobs.read(L.RESCORER_COMMIT, L.MODE1["expected_reading"])
    finally:
        blobs.close()


def item2_record(**change):
    """The shape readout/probe-v03/item2_reader.py prints (schema claude.item2-reading/0.3), reduced to what is checked."""
    rows = [{"model_seed": int(s), "checkpoint_relative_path": c, "verdict": "PRESENT_GRAPH_AND_DOMAIN", "problems": [],
             "checkpoint_sha256": "%064x" % (i + 1)} for i, (s, c) in enumerate((s, c) for s in L.SEEDS for c in L.A5_CHECKPOINTS)]
    record = {"schema": "claude.item2-reading/0.3", "outcome": "ITEM2_PASS", "mechanism_gate": "CLEARED",
              "historical_gate_on_repaired_arm": "MAY_RUN_FROZEN_EVALUATE_GATES", "entries": rows}
    record.update(change)
    return json.dumps(record).encode()


# ---- THE ACCEPTANCE CHECK ------------------------------------------------------------------------------------------
def test_mode1_dry_run_builds_the_bundle_passes_custody_and_prints_the_plan_and_the_cap(no_aws, tmp_path):
    folder = tmp_path / "bundle_mode1"
    proc = run_launch(no_aws, "--mode", "1", "--dry-run", "--bundle-dir", str(folder))
    print(proc.stdout[-6000:])
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    out = proc.stdout
    assert "AWS_CALL_ATTEMPTED" not in out + proc.stderr
    for words in ("CUSTODY: PASS", "PLAN (mode 1, Helm 2.0 study only)", "COST CAP", "cap $0.60", "allowance",
                  "retries   none", "DRY RUN: nothing uploaded, nothing launched, no AWS call"):
        assert words in out, words
    record = json.loads((folder / "dry_run_record.json").read_text(encoding="utf-8"))
    assert record["dry_run"] is True and record["mode"] == 1
    assert record["worst_case_usd_at_client_deadline"] <= L.COST_CAP_USD == record["cost_cap_usd"]
    assert record["sources"]["tree"] == L.RESCORER_COMMIT
    digest = hashlib.sha256()
    with open(folder / "bundle.tar.gz", "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    assert digest.hexdigest() == record["bundle_sha256"] and record["bundle_sha256"][:16] in out
    names, anchors = [], None
    with tarfile.open(folder / "bundle.tar.gz", mode="r|gz") as tar:          # one streaming pass
        for member in tar:
            names.append(member.name)
            if member.name == "anchors.json":
                anchors = json.loads(tar.extractfile(member).read())
    assert L.custody_refusals(names) == []
    assert names[-1] == "anchors.json" and sorted(anchors["files"]) == sorted(names[:-1])
    assert len(names) == record["files"] and record["raw_bytes"] <= L.MAX_BUNDLE_BYTES
    tree = {n[len("tree/"):] for n in names if n.startswith("tree/")}
    for rel in list(L.LF_PINS) + list(L.MODE1_LF_PINS) + sorted(L.DATA_FILES):
        assert rel in tree, rel
    assert "claude/machine_gates.py" in names
    weights = sorted(n for n in tree if n.endswith(".pt"))
    assert len(weights) == 30                                  # 5 per receipt: 3 Helm 2.0 + 3 Helm 1.0 (rescorer R1.7)
    assert not any(n.startswith(("records/helm_eval_design_20260923/", "records/typed_course_001/checks_002/private"))
                   for n in tree)
    for seed in L.SEEDS:
        assert "records/typed_pointer_001/receipt_%s/result.json" % seed in tree
        assert "records/typed_pointer_001/receipt_%s/collected/results/artifacts/protocol_material.json" % seed in tree
    script = (folder / "dry_run_machine_script.sh").read_text(encoding="utf-8")
    assert record["machine_script_bytes"] < 16000
    for words in ("instance_id=", "169.254.169.254", "X-aws-ec2-metadata-token", "shutdown -h +%d" % L.OS_POWER_OFF_MINUTES,
                  "sleep %d" % L.MAX_SECONDS, record["bundle_sha256"], "--historical-compatibility", "--write-anchor",
                  "HELM_RUN_SLOW_TESTS=1"):
        assert words in script, words
    shutil.rmtree(folder)


def test_mode2_refuses_without_item2_pass_before_building_anything(no_aws, tmp_path):
    folder = tmp_path / "bundle_mode2"
    for extra in ([], ["--receipts-commit", L.RESCORER_COMMIT]):
        proc = run_launch(no_aws, "--mode", "2", "--dry-run", "--bundle-dir", str(folder), *extra, timeout=120)
        assert proc.returncode == 2, proc.stdout + proc.stderr
        assert "LAUNCH_REFUSED: ITEM2_PASS_REQUIRED" in proc.stdout
        assert "G_LEARN_ON_NOT_READ" in proc.stdout
        assert not folder.exists()                              # refused before anything was built
    outside = tmp_path / "ITEM2_PASS.json"                     # a valid record that is not committed in this repository
    outside.write_bytes(item2_record())
    proc = run_launch(no_aws, "--mode", "2", "--dry-run", "--item2-pass", str(outside), "--bundle-dir", str(folder), timeout=120)
    assert proc.returncode == 2 and "LAUNCH_REFUSED: ITEM2_RECORD_NOT_COMMITTED" in proc.stdout, proc.stdout
    assert not folder.exists()


def test_the_item2_contract():
    assert L.validate_item2_record(item2_record())[1] == []
    cases = {
        "ITEM2_OUTCOME_NOT_PASS": item2_record(outcome="ITEM2_FAIL:20260917/final.pt=MISSING"),
        "ITEM2_READER_SAYS_G_LEARN_ON_NOT_READ": item2_record(historical_gate_on_repaired_arm="G_LEARN_ON_NOT_READ"),
        "ITEM2_SCHEMA_NOT_PROBE_V0_3": item2_record(schema="claude.item2-reading/0.2"),
        "ITEM2_ENTRIES_MISSING": item2_record(entries=None),
        "ITEM2_RECORD_NOT_JSON": b"ITEM2_PASS",
    }
    for code, data in cases.items():
        record, reasons = L.validate_item2_record(data)
        assert record is None and any(r.startswith(code) for r in reasons), (code, reasons)
    rows = json.loads(item2_record())["entries"]
    for change, code in ((lambda r: r[5].update(verdict="INVALID_NONDETERMINISTIC"), "ITEM2_CHECKPOINT_NOT_PRESENT"),
                         (lambda r: r[3].update(problems=["SWITCH_NOT_TRUE"]), "ITEM2_CHECKPOINT_NOT_PRESENT"),
                         (lambda r: r.pop(), "ITEM2_CHECKPOINTS_MISSING"),
                         (lambda r: r.append(dict(r[0])), "ITEM2_DUPLICATE_CHECKPOINT"),
                         (lambda r: r[0].update(checkpoint_relative_path="initial.pt"), "ITEM2_UNLISTED_CHECKPOINT"),
                         (lambda r: r[0].update(checkpoint_sha256="x"), "ITEM2_CHECKPOINT_SHA256_MISSING")):
        copy = json.loads(json.dumps(rows))
        change(copy)
        record, reasons = L.validate_item2_record(item2_record(entries=copy))
        assert record is None and any(r.startswith(code) for r in reasons), (code, reasons)


def test_custody_filter_names_every_forbidden_name():
    bad = ["tree/records/typed_course_001/checks_002/private_targets.json", "tree/x/sealed_A_eval.jsonl", "sealed/salt.hex",
           "tree/research/x/q3_eval.jsonl", "tree/records/helm_eval_design_20260923/hset2/PUBLIC_EXCLUDED_v1.json",
           "tree/records/helm_stage2_checker_20260923/PROTECTED_FILE_VERIFICATION.json", "tree/a/SEALED.json",
           "tree/a/__pycache__/x.pyc", "tree/../escape.py", "claude/transcript.json"]
    good = ["tree/records/typed_pointer_001/evaluate_gates.py", "tree/cncm/kernel.py", "claude/machine_gates.py", "anchors.json",
            "tree/records/typed_pointer_001/receipt_20260917/collected/results/artifacts/final.pt"]
    assert L.custody_refusals(bad + good) == bad


def test_cost_cap_and_machine_script():
    assert L.worst_case_usd() <= L.COST_CAP_USD < L.worst_case_usd(L.CLIENT_DEADLINE_MINUTES + 10)
    assert L.MAX_SECONDS / 60 < L.OS_POWER_OFF_MINUTES < L.CLIENT_DEADLINE_MINUTES
    template = (HERE / "job.sh.template").read_text(encoding="utf-8")
    long_links = {k: "https://example.invalid/" + k + "?" + "x" * 1700 for k in ("bundle", "results", "progress")}
    for mode in (1, 2):
        script = L.render(template, mode, long_links, "0" * 64, "1" * 40)
        assert len(script.encode("utf-8")) < 16000 and "__" not in script.replace("__pycache__", "")
        assert ('if [ "%d" = "1" ]' % mode) in script
    assert "wait \"$p\"" in template and "\n  wait\n" not in template   # never a bare wait: the timer loop never ends


# ---- the machine's program -----------------------------------------------------------------------------------------
def test_the_comparator_reproduces_the_committed_helm2_reading_and_catches_a_change(committed_reading):
    reading = json.loads(committed_reading)
    fresh = MG.canonical_bytes(reading)
    assert fresh == committed_reading and MG.sha256(fresh) == MG.MODE1_EXPECT["reading_sha256"]
    summary = MG.gate_summary(reading)
    assert {s: [r["b_wrong_to_right"], r["c_right_to_wrong"]] for s, r in summary["H1_G_LEARN_population"]["per_seed"].items()} == GOOD_H1
    assert [summary["H1_G_LEARN_population"]["per_seed"][s]["p_one_sided"] for s in L.SEEDS] == ["13/4096", "1/4096", "9/256"]
    assert summary["label"] == "NO_TRANSFER_TO_NEW_WORLDS" and summary["H2_G_LEARN_all_kinds"]["pass"] is True
    assert MG.mode1_verdict(MG.sha256(fresh), summary) == ("GATES_REPRODUCED", [])
    reading["seeds"]["20260919"]["G_LEARN_population"]["wrong_to_right"] = 8
    changed = MG.canonical_bytes(reading)
    verdict, reasons = MG.mode1_verdict(MG.sha256(changed), MG.gate_summary(reading))
    assert verdict == "GATES_NOT_REPRODUCED" and any(r.startswith("READING_SHA256_DIFFERS") for r in reasons)
    assert "H1_DIFFERS:20260919:8/1" in reasons


def test_study_mapping_changes_only_receipt_dir(tmp_path):
    for seed in L.SEEDS:
        (tmp_path / MG.R / ("receipt_%s" % seed)).mkdir(parents=True)
    study = {"schema": "s", "jobs": [{"model_seed": int(s), "job": "j%s" % s, "owner": {"path": "C:\\x\\owner.json"},
                                      "receipt_dir": "C:\\Users\\x\\records\\typed_pointer_001\\receipt_%s" % s} for s in L.SEEDS]}
    raw = json.dumps(study).encode()
    mapped, record = MG.map_study(raw, tmp_path)
    assert record["only_receipt_dir_changed"] and record["original_sha256"] == MG.sha256(raw)
    for job, seed in zip(mapped["jobs"], L.SEEDS):
        assert pathlib.Path(job["receipt_dir"]) == (tmp_path / MG.R / ("receipt_%s" % seed)).resolve()
        assert job["owner"] == {"path": "C:\\x\\owner.json"}
    shutil.rmtree(tmp_path / MG.R / "receipt_20260919")
    with pytest.raises(SystemExit):
        MG.map_study(raw, tmp_path)


def _write_mode1_outputs(out, codes, verdict="GATES_REPRODUCED"):
    out.mkdir(exist_ok=True)
    (out / "EXIT_CODES").write_text("".join("%s=%s\n" % kv for kv in codes.items()), encoding="utf-8")
    (out / "GATES_READING_SUMMARY.json").write_text(json.dumps({"verdict": verdict, "reasons": [], "summary": {}}), encoding="utf-8")
    for name, (field, value) in MG.MODE1_OUTPUTS.items():
        body = {field: value}
        if name.startswith("trusted_rescore_reading"):
            body["label_rederived"] = "NO_TRANSFER_TO_NEW_WORLDS"
        (out / name).write_text(json.dumps(body), encoding="utf-8")


def test_decide_passes_only_when_every_expectation_holds(tmp_path):
    good = dict(MG.EXPECTED_EXIT[1])
    _write_mode1_outputs(tmp_path / "a", good)
    assert MG.decide(1, tmp_path / "a") == 0
    result = json.loads((tmp_path / "a" / "GATES_JOB_RESULT.json").read_text(encoding="utf-8"))
    assert (result["overall"], result["rescorer_verdict"]) == ("ALL_PASS", "RESCORER_0_4_AWS_ACCEPTED")
    _write_mode1_outputs(tmp_path / "b", dict(good, test_historical_compatibility="1"))
    assert MG.decide(1, tmp_path / "b") == 1
    result = json.loads((tmp_path / "b" / "GATES_JOB_RESULT.json").read_text(encoding="utf-8"))
    assert result["overall"] == "FAILED" and result["rescorer_verdict"] == "RESCORER_0_4_NOT_ACCEPTED"
    assert result["gates_verdict"] == "GATES_REPRODUCED"
    _write_mode1_outputs(tmp_path / "c", good, verdict="GATES_NOT_REPRODUCED")
    assert MG.decide(1, tmp_path / "c") == 1
    _write_mode1_outputs(tmp_path / "d", dict(good, hist_reading="0"))      # exit 0 in historical mode is not acceptance
    assert MG.decide(1, tmp_path / "d") == 1


def test_anchor_check_finds_a_changed_missing_or_unlisted_file(tmp_path):
    (tmp_path / "tree").mkdir()
    (tmp_path / "tree" / "a.py").write_bytes(b"x = 1\n")
    anchors = {"files": {"tree/a.py": {"sha256": MG.sha256(b"x = 1\n")}}}
    (tmp_path / "anchors.json").write_text(json.dumps(anchors), encoding="utf-8")
    assert MG.check_anchors(tmp_path) == 0
    (tmp_path / "tree" / "b.py").write_bytes(b"")
    assert MG.check_anchors(tmp_path) == 1
    (tmp_path / "tree" / "b.py").unlink()
    (tmp_path / "tree" / "a.py").write_bytes(b"x = 2\n")
    assert MG.check_anchors(tmp_path) == 1


def test_the_laptop_reader_binds_results_to_the_launched_instance(tmp_path, committed_reading):
    iid, launched, ended = "i-0123456789abcdef0", "2026-09-25T02:00:00Z", "2026-09-25T02:55:00Z"
    (tmp_path / "launch_record_mode1.json").write_text(json.dumps(
        {"instance_id": iid, "launched_utc": launched, "bundle_sha256": "f" * 64}), encoding="utf-8")
    (tmp_path / "watch_record_mode1.json").write_text(json.dumps(
        {"mode": 1, "instance_id": iid, "launched_utc": launched, "watch_ended_utc": ended, "outcome": "RESULTS_RECEIVED",
         "files_downloaded": 30, "final_state": "terminated", "job_status": "done", "cost_upper_bound_usd": 0.33}), encoding="utf-8")
    res = tmp_path / "results_mode1"
    res.mkdir()
    (res / "STATUS").write_text("done\n", encoding="utf-8")
    (res / "job.log").write_text("JOB START 2026-09-25T02:01:10Z\nJOB FINISH 2026-09-25T02:50:00Z status=done\n", encoding="utf-8")
    (res / "env.txt").write_text("instance_id=%s\nbundle_sha256=%s\n" % (iid, "f" * 64), encoding="utf-8")
    (res / "GATES_JOB_RESULT.json").write_text(json.dumps({"mode": 1, "overall": "ALL_PASS"}), encoding="utf-8")
    (res / "gate_reading_fresh.json").write_bytes(committed_reading)
    assert RR.read(tmp_path, 1)["verdict"] == "JOB_ACCEPTED"
    (res / "env.txt").write_text("instance_id=i-0fffffffffffffff0\nbundle_sha256=%s\n" % ("f" * 64), encoding="utf-8")
    reading = RR.read(tmp_path, 1)
    assert reading["verdict"] == "JOB_NOT_ACCEPTED" and any(p.startswith("MACHINE_INSTANCE_ID") for p in reading["problems"])
